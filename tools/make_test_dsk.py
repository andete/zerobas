#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Generate a minimal 720 KB FAT12 .dsk for zerobas-disk integration testing.

The image is built from the Microsoft FAT specification + ECMA-107 geometry
(both allowed sources; see disk/PROVENANCE.md) — no disk-ROM bytes are copied.
It carries a couple of files with deterministic, easily-verified content so a
black-box read through the FDC -> FAT12 -> BDOS stack can be checked byte for
byte.

720 KB DSDD 3.5" geometry (matches disk/PROVENANCE.md §DPB):
    512 bytes/sector, 2 sectors/cluster, 1 reserved sector, 2 FATs,
    112 root entries, 1440 total sectors, media 0xF9, 3 sectors/FAT,
    9 sectors/track, 2 heads.
Sector map: 0 boot | 1-3 FAT1 | 4-6 FAT2 | 7-13 root dir | 14.. data
(cluster 2 == sector 14).

The primary test file TEST.BIN is exactly two clusters (2048 bytes = 16 records
of 128 bytes); record r is filled with the byte value r+1, so a sequential read
of record r must come back as 128 copies of (r+1). Two clusters + the 128-byte
BDOS record size exercise: per-sector refill (4 records/sector), a cluster-chain
hop (after record 8), and cluster-chain EOF (after record 16). HI.TXT is a small
second entry so the directory search has to pick the right one.

PROG.BIN is a REAL BSAVE binary for the disk BLOAD execute path. The on-disk
BSAVE binary-file format (MSX-BASIC file formats — MSX Wiki / MSX Resource
Center, an allowed public language reference) is a 7-byte header followed by the
raw machine code, with NO 10x$D0 block and NO filename in the body (the name is
the directory entry):

    byte 0      : $FE                 binary-file id
    bytes 1-2   : start address (LE)  where the data loads
    bytes 3-4   : end   address (LE)  last load address (inclusive)
    bytes 5-6   : exec  address (LE)  ,R jumps here
    bytes 7..   : the data bytes, loaded into [start..end] inclusive

This differs from the CASSETTE header (10x $D0 + 6-char filename + the same three
addresses); see disk/PROVENANCE.md / disk/TODO.md. PROG.BIN's payload is a tiny
hand-assembled blob that (a) writes a deterministic landmark to MARKER_ADDR so a
probe can confirm the bytes landed, then (b) self-loops at JR $ so a probe can
break there and confirm the ,R exec handoff fired. A deterministic data tail
after the code is trivially checkable byte-for-byte at [start..end].

    python3 tools/make_test_dsk.py [out.dsk]      # default: disk/test720.dsk
"""
from __future__ import annotations

import os
import struct
import sys

SECTOR = 512
SEC_PER_CLUS = 2
RESERVED = 1
NUM_FATS = 2
ROOT_ENTRIES = 112
TOTAL_SECTORS = 1440
MEDIA = 0xF9
SEC_PER_FAT = 3
SEC_PER_TRACK = 9
HEADS = 2

CLUSTER_BYTES = SECTOR * SEC_PER_CLUS
FIRST_FAT = RESERVED                                   # sector 1
FIRST_ROOT = RESERVED + NUM_FATS * SEC_PER_FAT         # sector 7
ROOT_SECS = (ROOT_ENTRIES * 32 + SECTOR - 1) // SECTOR # 7
FIRST_DATA = FIRST_ROOT + ROOT_SECS                    # sector 14


class Fat12Image:
    def __init__(self):
        self.data = bytearray(TOTAL_SECTORS * SECTOR)
        # 12-bit FAT entries, indexed by cluster; 0 and 1 are reserved.
        self.fat = [0] * (TOTAL_SECTORS // SEC_PER_CLUS + 16)
        self.fat[0] = 0xF00 | MEDIA          # cluster 0 = media descriptor
        self.fat[1] = 0xFFF                  # cluster 1 = end marker
        self.next_free = 2
        self.dir_index = 0
        self._write_boot_sector()

    def _write_boot_sector(self):
        b = self.data
        # Bytes 0-2: a jump opcode. The MSX disk ROM (MSX2 TH §3, boot procedure)
        # checks the FIRST byte of the transferred sector: "when the top of the
        # transferred sector is neither EBH nor E9H, DISK-BASIC is invoked." So
        # byte 0 MUST be $EB (or $E9) for the boot code at $C01E to be reached at
        # all. We keep $EB FE 90 (the same first three bytes this image has always
        # carried); bytes 1-2 ($FE 90) are the standard JMP-displacement + NOP
        # filler of the x86-style 3-byte jump field and are not executed by the
        # Z80 boot path (the disk ROM CALLs $C01E directly, not byte 0).
        b[0:3] = bytes([0xEB, 0xFE, 0x90])   # $EB => boot code IS reached (MSX2 TH §3)
        b[3:11] = b"ZEROBAS "                 # OEM name
        struct.pack_into("<H", b, 11, SECTOR)
        b[13] = SEC_PER_CLUS
        struct.pack_into("<H", b, 14, RESERVED)
        b[16] = NUM_FATS
        struct.pack_into("<H", b, 17, ROOT_ENTRIES)
        struct.pack_into("<H", b, 19, TOTAL_SECTORS)
        b[21] = MEDIA
        struct.pack_into("<H", b, 22, SEC_PER_FAT)
        struct.pack_into("<H", b, 24, SEC_PER_TRACK)
        struct.pack_into("<H", b, 26, HEADS)
        self._write_boot_code()              # $1E+ : the safe data-disk boot stub
        b[510], b[511] = 0x55, 0xAA          # boot signature

    def _write_boot_code(self):
        """Write OUR OWN minimal, cold-boot-SAFE boot stub at offset $1E.

        CONTRACT — sourced verbatim from the MSX2 Technical Handbook, Chapter 3
        (MSX-DOS), "boot procedure" (Konamiman's public English translation; an
        allowed source — see disk/PROVENANCE.md §Boot sector boot code):

          "Then, the contents of the boot sector (logical sector #0) is
           transferred to C000H to C0FFH. At this time, when 'DRIVE NOT READY' or
           'READ ERROR' occurs, or when the top of the transferred sector is
           neither EBH nor E9H, DISK-BASIC is invoked. The routine at C01EH is
           called with CY flag reset. Normally, since code 'RET NC' is written to
           this address, nothing is carried and the execution returns. Any boot
           program written here in assembly language is invoked automatically."

        Pinned facts from that text:
          * Load address : sector 0 -> $C000..$C0FF.
          * Entry offset : $C01E  (== sector offset $1E).
          * Reached by   : CALL (the ROM "calls" $C01EH), so the stub must RET to
                           hand control back -- NOT JP.
          * Entry state  : first call has CY (carry) RESET.
          * Documented default behaviour for a disk that should NOT seize the boot
            is exactly the instruction `RET NC` at $C01E: with CY reset on entry
            "nothing is carried and the execution returns", so the ROM falls
            through to DISK-BASIC / MSX BASIC. (On the later MSX-DOS call CY is
            SET, so `RET NC` would NOT return there -- but that second call only
            happens on a >=64K MSX-DOS-capable machine that found MSXDOS.SYS;
            this is a plain data disk with no system files, so the documented and
            observed handoff is the first, CY-reset call returning cleanly.)

        OWN-DESIGN STUB. This is not a lifted reference boot sector: the stub is
        the single documented "do nothing, return" instruction. For belt-and-
        braces safety we make the WHOLE boot-code area inert no matter how the
        ROM transfers control:

          $1E : D0        RET NC   ; the documented data-disk default (CY reset
                                   ;   on the first call => returns to BASIC).
          $1F : C9        RET      ; unconditional RET, so even if some ROM reaches
                                   ;   $C01F or enters with CY set, we still return
                                   ;   cleanly instead of running into garbage.
          $20.. : 00      NOP ...  ; rest of the boot-code area left $00; harmless
                                   ;   (never reached -- entry is $1E and we RET).

        Bytes 3-29 (OEM + BPB) and the FAT/dir geometry are untouched; only
        $1E..$1FD changes (the $55 $AA signature at $1FE/$1FF is set separately).
        """
        b = self.data
        b[0x1E] = 0xD0                        # RET NC  : documented data-disk default
        b[0x1F] = 0xC9                        # RET     : belt-and-braces unconditional return
        # $20..$1FD remain $00 (NOP); never executed because $1E returns.

    def _sector(self, n):
        return slice(n * SECTOR, (n + 1) * SECTOR)

    def add_file(self, name8, ext3, content):
        """Allocate a cluster chain, write data, add a root-dir entry."""
        assert self.dir_index < ROOT_ENTRIES, "root directory full"
        n_clusters = max(1, (len(content) + CLUSTER_BYTES - 1) // CLUSTER_BYTES)
        clusters = list(range(self.next_free, self.next_free + n_clusters))
        self.next_free += n_clusters
        # chain them, last -> end-of-chain
        for i, c in enumerate(clusters):
            self.fat[c] = clusters[i + 1] if i + 1 < len(clusters) else 0xFFF
        # write data, cluster by cluster
        padded = content + bytes(n_clusters * CLUSTER_BYTES - len(content))
        for i, c in enumerate(clusters):
            first_sec = FIRST_DATA + (c - 2) * SEC_PER_CLUS
            chunk = padded[i * CLUSTER_BYTES:(i + 1) * CLUSTER_BYTES]
            self.data[first_sec * SECTOR:first_sec * SECTOR + len(chunk)] = chunk
        # root-directory entry (Microsoft FAT spec §3.4)
        off = FIRST_ROOT * SECTOR + self.dir_index * 32
        e = self.data
        e[off:off + 8] = name8.encode("ascii").ljust(8)[:8].upper()
        e[off + 8:off + 11] = ext3.encode("ascii").ljust(3)[:3].upper()
        e[off + 11] = 0x20                    # attribute: archive
        struct.pack_into("<H", e, off + 26, clusters[0])   # first cluster
        struct.pack_into("<I", e, off + 28, len(content))  # file size
        self.dir_index += 1

    def _pack_fat(self):
        raw = bytearray(SEC_PER_FAT * SECTOR)
        for c in range(0, len(self.fat)):
            v = self.fat[c] & 0xFFF
            idx = c * 3 // 2
            if idx + 1 >= len(raw):
                break
            if c & 1:                         # odd: high nibble of idx, all idx+1
                raw[idx] = (raw[idx] & 0x0F) | ((v << 4) & 0xF0)
                raw[idx + 1] = (v >> 4) & 0xFF
            else:                             # even: all idx, low nibble of idx+1
                raw[idx] = v & 0xFF
                raw[idx + 1] = (raw[idx + 1] & 0xF0) | ((v >> 8) & 0x0F)
        return bytes(raw)

    def finish(self):
        fat = self._pack_fat()
        for copy in range(NUM_FATS):
            base = (FIRST_FAT + copy * SEC_PER_FAT) * SECTOR
            self.data[base:base + len(fat)] = fat
        return bytes(self.data)


# --- PROG.BIN: a real BSAVE binary for the disk BLOAD execute path ----------
# Payload contract (mirrored by disk-spec/tools/disk_probe_bload_disk.py):
#   start = exec = PROG_LOAD; the blob writes MARKER (one byte) to MARKER_ADDR,
#   then a deterministic data tail follows the code, then JR $ at PROG_LOAD+
#   LANDMARK_OFF is the break landmark for the ,R handoff. end = last data byte.
PROG_LOAD = 0xC000        # load + exec address (page-3 RAM, free of basic state)
MARKER_ADDR = 0xD000      # where the executed blob writes its landmark byte
MARKER_BYTE = 0x5A        # the landmark a probe asserts after the ,R handoff
LANDMARK_OFF = 16         # JR $ sits at PROG_LOAD + LANDMARK_OFF (fixed)
DATA_TAIL = bytes(range(32))   # 0,1,..,31 — trivially checkable data after code


def build_bsave_payload() -> tuple[int, int, int, bytes]:
    """Hand-assemble PROG.BIN's body (data only) + return (start, end, exec, data).

    Layout inside [start..end]:
      +0  : LD A,MARKER_BYTE ; LD (MARKER_ADDR),A   (executed code)
      ... : NOP padding to LANDMARK_OFF
      +LANDMARK_OFF : JR $                          (self-loop landmark)
      ... : DATA_TAIL                               (deterministic, checkable)
    """
    code = bytearray()
    code += bytes([0x3E, MARKER_BYTE])                        # LD A,MARKER_BYTE
    code += bytes([0x32, MARKER_ADDR & 0xFF, MARKER_ADDR >> 8])  # LD (nn),A
    assert len(code) <= LANDMARK_OFF, "code overflows the landmark offset"
    code += bytes(LANDMARK_OFF - len(code))                   # NOP pad
    code += bytes([0x18, 0xFE])                               # JR $  (landmark)
    body = bytes(code) + DATA_TAIL
    start = PROG_LOAD
    end = PROG_LOAD + len(body) - 1                           # inclusive
    exec_ = PROG_LOAD
    return start, end, exec_, body


def make_bsave_file(start: int, end: int, exec_: int, body: bytes) -> bytes:
    """Wrap a payload in the 7-byte on-disk BSAVE header (MSX-BASIC file formats)."""
    return struct.pack("<BHHH", 0xFE, start, end, exec_) + body


# --- PROG.BAS: a real on-disk TOKENISED BASIC program for the LOAD path ------
# A BASIC program SAVEd to disk in the default (tokenised, non-",A") form is a
# leading marker byte $FF (BASIC_DISK_ID) followed by the in-memory program image
# — the same line-link chain do_tape_prog / disk_prog_load read:
#     [link:2 LE][lineno:2 LE][tokens...][00]  per line, ending in a $0000 link.
# Source: MSX-BASIC file formats (MSX Wiki / MSX Resource Center, an allowed
# public language reference — the same class the $FE BSAVE marker came from).
# See basic/PROVENANCE.md §disk LOAD and basic/sysvars.inc BASIC_DISK_ID.
#
# This is a TEST FIXTURE, so its tokenised line body is built from this project's
# OWN oracle-confirmed token values (basic/sysvars.inc) — allowed for fixtures.
# The program is a single line that POKEs a landmark byte to a known RAM address,
# so a functional probe can confirm (a) the program loaded into the store (read
# TXTBASE and compare the relinked image) AND (b) for LOAD",R", that RUN executed
# it (the landmark byte appears at the target address).
#
#   10 POKE &HD002,123
#
# The body bytes are EXACTLY what zerobas's tokeniser crunches this line to (the
# fixture is verified byte-identical against a typed-in `10 POKE &HD002,123` whose
# stored image is dumped from RAM):
#   POKE_TOKEN $98 | ' ' $20 | &HD002 = HEX_TOKEN $0C + 02 D0 | ',' $2C |
#   123 = INT1_TOKEN $0F + 7B | line-terminator $00
#
# PROG2.BAS is the embedded-$00 REGRESSION fixture (`10 POKE &HD100,&H7B`): its
# body carries TWO embedded $00 operand bytes — the &HD100 address high-byte-low
# pairing `$0C 00 D1` (an interior $00 with a whole statement tail after it) and
# the &H7B value's high byte `$0C 7B 00`. The pre-fix streamed line-link reader
# stopped a line body at the FIRST $00, so it truncated this line mid-body; the
# length-driven reader (§disk LOAD) copies the exact computed body length, so the
# line round-trips byte-identical. PROG.BAS deliberately AVOIDS embedded $00 (it
# encodes 123 as the 1-byte INT1 form `$0F 7B`) so the two fixtures bracket the
# fix: PROG.BAS is the no-embedded-$00 baseline, PROG2.BAS the embedded-$00 case.
BAS_TXTBASE = 0x8001      # in-memory text base (TXTBASE; relink recomputes links)
BAS_MARKER_ADDR = 0xD002  # landmark RAM address the POKEd line writes to
BAS_MARKER_BYTE = 0x7B    # the landmark byte (123 decimal; distinct from BSAVE's $5A@$D000)
BAS2_MARKER_ADDR = 0xD100  # PROG2.BAS landmark (distinct from PROG.BAS / PROG.BIN)
BAS2_MARKER_BYTE = 0x7B    # &H7B low byte (the value the embedded-$00 POKE writes)
POKE_TOKEN = 0x98
HEX_TOKEN = 0x0C
INT1_TOKEN = 0x0F


def wrap_basic_line(body: bytes, lineno: int = 10,
                    txtbase: int = BAS_TXTBASE) -> bytes:
    """Wrap a single line body into the in-memory line-link image (no $FF marker).

    A real SAVEd file carries the saving machine's absolute link pointer as each
    line's link word; the loader's relink recomputes them, so the value is a
    don't-care EXCEPT it must be NON-ZERO (a $0000 link word is the program-end
    marker, so a $0000 first-line link would be read as "empty program"). We use
    the genuine in-memory link the saving machine would have written (txtbase +
    line length = address of the end-link), which is also exactly what relink
    recomputes. The per-line $00 terminator and the final $0000 end-link must be
    exact.
    """
    line_len = 4 + len(body)                                  # link(2)+lineno(2)+body
    link = txtbase + line_len                                 # non-zero placeholder
    line = struct.pack("<HH", link, lineno) + body            # link, lineno
    return line + struct.pack("<H", 0x0000)                   # final $0000 link


def prog_bas_body() -> bytes:
    """`10 POKE &HD002,123` — the baseline (NO embedded $00; 123 = 1-byte INT1)."""
    return bytes([
        POKE_TOKEN,                                            # POKE
        0x20,                                                  # ' ' (kept verbatim)
        HEX_TOKEN, BAS_MARKER_ADDR & 0xFF, BAS_MARKER_ADDR >> 8,  # &HD002 (LE)
        0x2C,                                                  # ',' (verbatim)
        INT1_TOKEN, BAS_MARKER_BYTE,                          # 123 (1-byte INT1)
        0x00,                                                  # line terminator
    ])


def prog2_bas_body() -> bytes:
    """`10 POKE &HD100,&H7B` — the embedded-$00 regression body.

    &HD100 = `$0C 00 D1` (interior $00, statement tail after) and &H7B =
    `$0C 7B 00` (value high-byte $00). The pre-fix reader stopped at the first
    interior $00 and truncated; the length-driven reader copies the whole body.
    """
    return bytes([
        POKE_TOKEN,                                            # POKE
        0x20,                                                  # ' ' (verbatim)
        HEX_TOKEN, BAS2_MARKER_ADDR & 0xFF, BAS2_MARKER_ADDR >> 8,  # &HD100 -> $0C 00 D1
        0x2C,                                                  # ',' (verbatim)
        HEX_TOKEN, BAS2_MARKER_BYTE, 0x00,                    # &H7B -> $0C 7B 00
        0x00,                                                  # line terminator
    ])


def make_basic_file(body: bytes | None = None) -> bytes:
    """A tokenised-BASIC disk file: $FF marker + the in-memory program image."""
    if body is None:
        body = prog_bas_body()
    return bytes([0xFF]) + wrap_basic_line(body)


def relinked_image(body: bytes | None = None) -> bytes:
    """The line-link image AS IT SHOULD LOOK in the store after relink, so a probe
    can compare TXTBASE bytes directly. relink sets each line's link to the
    address of the next line's link field (absolute, at BAS_TXTBASE)."""
    if body is None:
        body = prog_bas_body()
    prog = wrap_basic_line(body)
    # split off the trailing $0000 end-link; the single line is the rest
    line = prog[:-2]
    next_addr = BAS_TXTBASE + len(line)        # address of the $0000 end-link
    relinked = struct.pack("<H", next_addr) + line[2:]   # fix the link word
    return relinked + struct.pack("<H", 0x0000)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "disk", "test720.dsk")

    img = Fat12Image()
    # TEST.BIN: 16 records of 128 bytes; record r = 128 * byte(r+1).
    test_bin = bytearray()
    for r in range(16):
        test_bin += bytes([(r + 1) & 0xFF]) * 128
    img.add_file("TEST", "BIN", bytes(test_bin))
    img.add_file("HI", "TXT", b"Hello from zerobas-disk!\r\n")
    # PROG.BIN: a real BSAVE binary (added AFTER the others so the dir search must
    # skip TEST.BIN / HI.TXT to find it).
    start, end, exec_, body = build_bsave_payload()
    prog_bin = make_bsave_file(start, end, exec_, body)
    img.add_file("PROG", "BIN", prog_bin)
    # PROG.BAS: a real on-disk TOKENISED BASIC program for the LOAD"filename" path
    # (baseline: NO embedded $00 operand byte).
    prog_bas = make_basic_file()
    img.add_file("PROG", "BAS", prog_bas)
    # PROG2.BAS: the embedded-$00 LOAD regression fixture (`10 POKE &HD100,&H7B`).
    prog2_bas = make_basic_file(prog2_bas_body())
    img.add_file("PROG2", "BAS", prog2_bas)

    open(out, "wb").write(img.finish())
    print(f"wrote {out} ({TOTAL_SECTORS * SECTOR} bytes)")
    print(f"  TEST.BIN : {len(test_bin)} bytes, first cluster 2 "
          f"(sectors {FIRST_DATA}.. ); record r = 128 x byte(r+1)")
    print(f"  HI.TXT   : 26 bytes")
    print(f"  PROG.BIN : {len(prog_bin)} bytes BSAVE "
          f"(hdr $FE start=${start:04X} end=${end:04X} exec=${exec_:04X}); "
          f"writes ${MARKER_BYTE:02X}->${MARKER_ADDR:04X}, JR$ at "
          f"${start + LANDMARK_OFF:04X}; data tail {DATA_TAIL.hex()}")
    print(f"  PROG.BAS : {len(prog_bas)} bytes tokenised BASIC "
          f"(marker $FF + 1 line `10 POKE &H{BAS_MARKER_ADDR:04X},{BAS_MARKER_BYTE}`); "
          f"file {prog_bas.hex()}")
    print(f"             relinked store image @ ${BAS_TXTBASE:04X}: "
          f"{relinked_image().hex()}")
    print(f"  PROG2.BAS: {len(prog2_bas)} bytes tokenised BASIC, EMBEDDED-$00 "
          f"regression (marker $FF + 1 line `10 POKE &H{BAS2_MARKER_ADDR:04X},&H{BAS2_MARKER_BYTE:02X}`); "
          f"file {prog2_bas.hex()}")
    print(f"             relinked store image @ ${BAS_TXTBASE:04X}: "
          f"{relinked_image(prog2_bas_body()).hex()}")
    print(f"  geometry : firstFAT={FIRST_FAT} firstRoot={FIRST_ROOT} "
          f"rootSecs={ROOT_SECS} firstData={FIRST_DATA}")


if __name__ == "__main__":
    main()
