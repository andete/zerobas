#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Differential BDOS-FCB oracle: zerobas-disk vs real MSX-DOS 1.

zerobas's `bdos_entry` (disk/disk.asm) is a CP/M-compatible FCB BDOS — Open
($0F), Sequential Read ($14), Close ($10), Set-DTA ($1A). The National CF-3300's
own disk ROM runs Disk BASIC, which exposes NO such FCB BDOS, so the DSKIO probe
(disk_probe_dskio.py) cannot reach this layer. The only reference that exposes
the exact API is MSX-DOS. This probe differs the two:

  * reference -- real MSX-DOS 1 (booted from a user-supplied DOS system disk on
                 openMSX's `National_CF-3300`). Its BDOS at $0005 is driven by a
                 small `.COM` we add to the disk and auto-run via AUTOEXEC.BAT.
  * zerobas   -- our clean-room `bdos_entry`, reached across slots with CALSLT
                 ($001C) via DISKSLOT + the SYSTEM vector ($F37D), on a
                 `*_BASIC_DISK` machine.

Both read the SAME file (ORACLE.BIN, injected into a throwaway copy of the DOS
disk) through Open -> 17x Sequential Read -> Close, and we compare the Open
result, every 128-byte record + its result code, the EOF code, and the Close
result byte-for-byte.

SCOPE — FULL differential (see disk/PROVENANCE.md / disk/TODO.md). Two files:

  * NARROW case  — ORACLE.BIN, exactly two clusters (2048 B = 16 records), clean
    cluster-boundary EOF. Diffs delivered data + A-codes.
  * PART A       — ORACLE2.BIN, 1500 bytes: NOT a 128-byte-record multiple and
    NOT a cluster multiple, so the last record is partial (92 real bytes) and EOF
    does not land on a cluster boundary. Diffs every delivered record (incl. the
    partial) + every A-code byte-for-byte. This is the real fidelity fix: it
    exercises bdos_seqread's FAT_FILESIZE bounding and the partial-record padding.
    ORACLE OBSERVATION (this probe, captured on real MSX-DOS 1.03): the partial
    final record is 92 real bytes + 36 bytes of $00 (MSX-DOS actively ZERO-fills
    the tail — confirmed by pre-filling the DTA with $FF; it is not Ctrl-Z/$1A and
    not stale data), returned with code $00; the FOLLOWING read returns $01 (EOF).
  * PART B       — FCB-field mutations. Captures the 37-byte FCB on BOTH machines
    after Open / after 2 SeqReads / after Close and reports a per-field
    comparison, split into MATCHED fields (drive, 8.3 name — what a reasonable FCB
    caller reads, which zerobas keeps identical) and DOCUMENTED INTENTIONAL
    DIVERGENCE fields (extent +12, current-record +32, record-count +15, alloc
    map +16..31 — MSX-DOS-internal bookkeeping no zerobas caller reads). PASS/FAIL
    hinges on Part A data+codes + the matched FCB fields; the divergence fields
    are reported, never failed.

CLEAN-ROOM DISCIPLINE. MSX-DOS is used ONLY as a black box: we observe BDOS
return values and the bytes it delivers (which are our own ORACLE.BIN). MSXDOS.SYS
and COMMAND.COM are never read, dumped, or disassembled; the proprietary system
files live only in a /tmp working copy of the user's disk and are never
committed. ORACLE.COM / ORACLE.BIN / AUTOEXEC.BAT / the zerobas-side stub are all
this project's own clean code.

Prerequisites:
  * openMSX with the CF-3300 ROMs installed (you provide ROMs you may use).
  * zerobas-disk's `*_BASIC_DISK` machine installed
    (`python3 tools/install-openmsx-machine.py --disk-rom disk.rom`).
  * a PLAIN MSX-DOS 1 system disk that boots to the `A>` prompt (MSXDOS.SYS +
    COMMAND.COM, NOT a game/menu disk that auto-runs something else). Pass it
    with --dos-disk.

    python3 probes/disk/disk_probe_bdos.py --dos-disk /path/to/msxdos.dsk
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import shutil
import signal
import struct
import subprocess
import sys
import time
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"

# ORACLE.BIN: 16 records of 128 bytes; record r is 128 copies of (r+1). Exactly
# two clusters on a standard FAT12 disk (1024 B/cluster) -> a cluster-chain hop
# and a clean cluster-boundary EOF (narrow scope; see module docstring).
N_RECORDS = 16


def oracle_bin() -> bytes:
    b = bytearray()
    for r in range(N_RECORDS):
        b += bytes([(r + 1) & 0xFF]) * 128
    return bytes(b)


# --- reference: ORACLE.COM (org $0100), auto-run by AUTOEXEC.BAT under MSX-DOS --
# Opens ORACLE.BIN, Set-DTA $0100-page buffer, 17x Sequential Read into REC,
# Close, self-loop at `done`. Buffers in page-0 RAM ($2000+): under MSX-DOS page 1
# is the swapped disk ROM, so page-0 RAM is the safe home. COMMAND.COM loads and
# launches it in a CLEAN BDOS state (hijacking PC mid-prompt would re-enter the
# non-reentrant console-input BDOS call and never return). Assembled with pasmo;
# the embedded FCB names ORACLE.BIN.
ORACLE_COM_HEX = (
    "1165010e0fcd05003220291180290e1acd0500af3223291165010e14cd05003222293a23295f160021"
    "0029193a222977b720253a23296f26002929292929292911002019eb218029018000edb03a23293c32"
    "2329fe1138bf1165010e10cd050032212918fe004f5241434c45202042494e0000000000000000000000"
    "00000000000000000000000000")
COM_REC = 0x2000
COM_RESCODES = 0x2900
COM_OPENRES = 0x2920
COM_CLOSERES = 0x2921
COM_DONE = 0x0163

# --- zerobas side: stub injected at $C000, calls bdos_entry across slots --------
# callbdos = the production bdos_call dance (DISKSLOT $E0E7 -> IYh, bdos_entry from
# the SYSTEM JP vector at $F37E -> IX, CALSLT $001C). INIT now publishes $F37D as an
# executable `JP bdos_entry` (C3 <addr>) for the MSX-DOS boot, so the entry address
# is the JP target read from $F37E, not a bare word at $F37D. Page-3 buffers, clear
# of bdos_entry's scratch
# ($E2A0 SECTOR_BUF / $E4xx) and zerobas state. Probe pre-loads the FCB at $CA30.
OURS_STUB_HEX = (
    "f31130ca0e0fcd66c03220ca1180ca0e1acd66c0af3223ca1130ca0e14cd66c03222ca3a23ca5f1600"
    "2100ca193a22ca77b720253a23ca6f2600292929292929291100c219eb2180ca018000edb03a23ca3c"
    "3223cafe1138bf1130ca0e10cd66c03221ca18fe3ae7e03201cbfd2a00cbdd2a7ef3c31c00")
OURS_STUB = 0xC000
OURS_FCB = 0xCA30
OURS_REC = 0xC200
OURS_RESCODES = 0xCA00
OURS_OPENRES = 0xCA20
OURS_CLOSERES = 0xCA21
OURS_DONE = 0xC064

# 37-byte FCB: drive 0 (default) + "ORACLE  BIN" (8.3, space-padded) + zeros.
FCB = bytes([0]) + b"ORACLE  ".ljust(8) + b"BIN" + bytes(25)

# ============================================================================
# PART A — sub-record EOF bounding (the FULL differential, non-cluster-multiple).
# ORACLE2.BIN is 1500 bytes: not a 128-byte-record multiple and not a cluster
# multiple, so the LAST record is partial (92 real bytes) and EOF does NOT land
# on a cluster boundary. This exercises bdos_seqread's FAT_FILESIZE bounding +
# the observed MSX-DOS partial-record padding. Both machines do
# Open -> 13x SeqRead -> Close and we diff every record (incl. the partial) +
# every A-code byte-for-byte.
SIZE2 = 1500
N_RECORDS2 = 13                          # 12 records (last partial) + 1 EOF read


def oracle2_bin() -> bytes:
    # Deterministic, position-varying: byte i = (i*7 + 3) & 0xFF. Position-varying
    # (unlike ORACLE.BIN's per-record constant) so a misplaced byte in the partial
    # record is caught, and so the zero-pad tail is distinguishable from real data.
    return bytes([(i * 7 + 3) & 0xFF for i in range(SIZE2)])


# ORACLE2.COM (org $0100): Set-DTA, Open ORACLE2.BIN, 13x SeqRead recording each
# A-code + the 128-byte record, three FCB snapshots (after Open / after 2 reads /
# after Close), Close, set GUARD=$A5, self-loop. No register assumed preserved
# across BDOS. The GUARD byte is the breakpoint condition: page-0 address $0186
# is also executed by COMMAND.COM/DOS BEFORE the COM loads, so we only capture
# once GUARD shows the buffers are fully written. Buffers are non-overlapping.
ORACLE2_COM_HEX = (
    "1100240e1acd0500118d010e0fcd050032b201218d01110021012500edb0218020228901210028228b013e0d"
    "328801118d010e14cd05002a89017723228901210024ed5b8b01018000edb0ed538b013a88013d328801fe0b"
    "200b218d01114021012500edb03a8801b720c4118d010e10cd050032b301218d01118021012500edb03ea532"
    "ff2018fe0000000000004f5241434c45322042494e000000000000000000000000000000000000000000000000")
COM2_DONE = 0x0186
COM2_OPENRES = 0x01B2
COM2_CLOSERES = 0x01B3
COM2_CODES = 0x2080
COM2_STORE = 0x2800
COM2_FCBSNAP1 = 0x2100
COM2_FCBSNAP2 = 0x2140
COM2_FCBSNAP3 = 0x2180
COM2_GUARD = 0x20FF

# OURS2 stub (org $C000): the same sequence reaching bdos_entry via callbdos
# (CALSLT). Page-3 buffers clear of bdos_entry scratch ($E2A0/$E4xx). Probe
# pre-loads the FCB at $CA40.
OURS2_STUB_HEX = (
    "f31100c20e1acd90c01140ca0e0fcd90c0328ec02140ca1100c9012500edb02100ca228ac02100cc228cc03e"
    "0d3289c01140ca0e14cd90c02a8ac07723228ac02100c2ed5b8cc0018000edb0ed538cc03a89c03d3289c0fe"
    "0b200b2140ca1130c9012500edb03a89c0b720c41140ca0e10cd90c0328fc02140ca1160c9012500edb03ea5"
    "32ffc918fe000000000000003ae7e03201cbfd2a00cbdd2a7ef3c31c00")
OURS2_STUB = 0xC000
OURS2_DONE = 0xC087
OURS2_OPENRES = 0xC08E
OURS2_CLOSERES = 0xC08F
OURS2_CODES = 0xCA00
OURS2_STORE = 0xCC00
OURS2_FCB = 0xCA40
OURS2_FCBSNAP1 = 0xC900
OURS2_FCBSNAP2 = 0xC930
OURS2_FCBSNAP3 = 0xC960
OURS2_GUARD = 0xC9FF

# 37-byte FCB for ORACLE2.BIN.
FCB2 = bytes([0]) + b"ORACLE2 ".ljust(8) + b"BIN" + bytes(25)


def fat12_add(img: bytearray, name8: str, ext3: str, content: bytes) -> None:
    """Add a file to an existing FAT12 image (in place): allocate a cluster
    chain from the free list, write the data, append a root-dir entry. Geometry
    is read from the BPB so it works on any standard FAT12 disk."""
    bps = struct.unpack_from("<H", img, 11)[0]
    spc = img[13]
    resv = struct.unpack_from("<H", img, 14)[0]
    nfat = img[16]
    rootent = struct.unpack_from("<H", img, 17)[0]
    spf = struct.unpack_from("<H", img, 22)[0]
    first_fat = resv
    first_root = resv + nfat * spf
    root_secs = (rootent * 32 + bps - 1) // bps
    first_data = first_root + root_secs
    clus_bytes = bps * spc
    fat_off = first_fat * bps
    total_clusters = (len(img) // bps - first_data) // spc + 2

    def get(c):
        idx = c * 3 // 2
        b = img[fat_off + idx] | (img[fat_off + idx + 1] << 8)
        return (b >> 4) if (c & 1) else (b & 0xFFF)

    def setf(c, v):
        idx = c * 3 // 2
        cur = img[fat_off + idx] | (img[fat_off + idx + 1] << 8)
        if c & 1:
            cur = (cur & 0x000F) | ((v & 0xFFF) << 4)
        else:
            cur = (cur & 0xF000) | (v & 0xFFF)
        img[fat_off + idx] = cur & 0xFF
        img[fat_off + idx + 1] = (cur >> 8) & 0xFF

    n = max(1, (len(content) + clus_bytes - 1) // clus_bytes)
    free = [c for c in range(2, total_clusters) if get(c) == 0][:n]
    if len(free) != n:
        sys.exit(f"not enough free clusters for {name8}.{ext3}")
    for i, c in enumerate(free):
        setf(c, free[i + 1] if i + 1 < n else 0xFFF)
    padded = content + bytes(n * clus_bytes - len(content))
    for i, c in enumerate(free):
        s = first_data + (c - 2) * spc
        img[s * bps:s * bps + clus_bytes] = padded[i * clus_bytes:(i + 1) * clus_bytes]
    fat_bytes = img[fat_off:fat_off + spf * bps]
    for k in range(nfat):
        b = (first_fat + k * spf) * bps
        img[b:b + len(fat_bytes)] = fat_bytes
    for i in range(rootent):
        off = first_root * bps + i * 32
        if img[off] in (0x00, 0xE5):
            img[off:off + 8] = name8.encode().ljust(8)[:8].upper()
            img[off + 8:off + 11] = ext3.encode().ljust(3)[:3].upper()
            img[off + 11] = 0x20
            for j in range(12, 26):
                img[off + j] = 0
            struct.pack_into("<H", img, off + 26, free[0])
            struct.pack_into("<I", img, off + 28, len(content))
            return
    sys.exit("root directory full")


def build_dos_disk(dos_src: str, out: str) -> None:
    """Copy the user's DOS disk and inject ORACLE.BIN + ORACLE.COM + AUTOEXEC.BAT
    (which auto-runs ORACLE.COM at boot, so no keyboard input is needed).
    Narrow case (2048-byte cluster-multiple ORACLE.BIN)."""
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "ORACLE", "BIN", oracle_bin())
    fat12_add(img, "ORACLE", "COM", bytes.fromhex(ORACLE_COM_HEX))
    fat12_add(img, "AUTOEXEC", "BAT", b"ORACLE\r\n")
    open(out, "wb").write(img)


def build_dos_disk2(dos_src: str, out: str) -> None:
    """Full-differential disk: 1500-byte ORACLE2.BIN + ORACLE2.COM + AUTOEXEC
    that auto-runs ORACLE2. (A separate boot disk from the narrow case because
    AUTOEXEC.BAT runs a single .COM; the ours-side stub injects itself by CALSLT,
    so it just needs ORACLE2.BIN present on this same image.)"""
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "ORACLE2", "BIN", oracle2_bin())
    fat12_add(img, "ORACLE2", "COM", bytes.fromhex(ORACLE2_COM_HEX))
    fat12_add(img, "AUTOEXEC", "BAT", b"ORACLE2\r\n")
    open(out, "wb").write(img)


def _run(machine: str, dsk: str, tcl: str, out: str, timeout: float) -> dict:
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", dsk,
           "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture from {machine} (machine/ROMs/disk missing?)")
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    return d


def _capture_proc(rec, rescodes, openres, closeres, out) -> str:
    recs = "\n".join(
        f'  puts $f "rec{r}=[__hex [expr {{0x{rec:04X}+{r}*128}}] 128]"'
        for r in range(N_RECORDS))
    return f"""proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "open=[__hex 0x{openres:04X} 1]"
  puts $f "close=[__hex 0x{closeres:04X} 1]"
  puts $f "codes=[__hex 0x{rescodes:04X} 17]"
{recs}
  close $f; exit
}}"""


def run_ref(machine: str, dsk: str, out: str) -> dict:
    """Boot MSX-DOS; AUTOEXEC.BAT runs ORACLE.COM; break on its self-loop."""
    cap = _capture_proc(COM_REC, COM_RESCODES, COM_OPENRES, COM_CLOSERES, out)
    tcl = f"""set throttle off
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
{cap}
after time 8  {{ debug set_bp 0x{COM_DONE:04X} {{}} {{ cap }} }}
after time 55 {{ cap }}
"""
    return _run(machine, dsk, tcl, out, timeout=70)


def run_ours(machine: str, dsk: str, out: str) -> dict:
    """Boot the combined machine; inject the CALSLT stub; break on its self-loop."""
    cap = _capture_proc(OURS_REC, OURS_RESCODES, OURS_OPENRES, OURS_CLOSERES, out)
    tcl = f"""set throttle off
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
{cap}
proc go {{}} {{
  debug write_block memory 0x{OURS_FCB:04X} [binary format H* {FCB.hex()}]
  debug write_block memory 0x{OURS_STUB:04X} [binary format H* {OURS_STUB_HEX}]
  reg PC 0x{OURS_STUB:04X}
  debug set_bp 0x{OURS_DONE:04X} {{}} {{ cap }}
}}
after time 11 {{ go }}
after time 40 {{ cap }}
"""
    return _run(machine, dsk, tcl, out, timeout=55)


# ---------------------------------------------------------------------------
# PART A + B capture: 1500-byte file, 13 codes, 13 records, 3 FCB snapshots.

def _capture_proc2(codes, store, openres, closeres,
                   snap1, snap2, snap3, out) -> str:
    recs = "\n".join(
        f'  puts $f "rec{r}=[__hex [expr {{0x{store:04X}+{r}*128}}] 128]"'
        for r in range(N_RECORDS2))
    return f"""proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "open=[__hex 0x{openres:04X} 1]"
  puts $f "close=[__hex 0x{closeres:04X} 1]"
  puts $f "codes=[__hex 0x{codes:04X} {N_RECORDS2}]"
  puts $f "fcb1=[__hex 0x{snap1:04X} 37]"
  puts $f "fcb2=[__hex 0x{snap2:04X} 37]"
  puts $f "fcb3=[__hex 0x{snap3:04X} 37]"
{recs}
  close $f; exit
}}"""


def run_ref2(machine: str, dsk: str, out: str) -> dict:
    """Boot MSX-DOS; AUTOEXEC runs ORACLE2.COM; break on its self-loop."""
    cap = _capture_proc2(COM2_CODES, COM2_STORE, COM2_OPENRES, COM2_CLOSERES,
                         COM2_FCBSNAP1, COM2_FCBSNAP2, COM2_FCBSNAP3, out)
    # GUARD-conditioned breakpoint: $0186 is also executed by DOS/COMMAND.COM
    # before the COM loads, so only capture once the COM has set GUARD=$A5.
    tcl = f"""set throttle off
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
{cap}
after time 8  {{ debug set_bp 0x{COM2_DONE:04X} {{[__hex 0x{COM2_GUARD:04X} 1] eq "a5"}} {{ cap }} }}
after time 55 {{ cap }}
"""
    return _run(machine, dsk, tcl, out, timeout=70)


def run_ours2(machine: str, dsk: str, out: str) -> dict:
    """Boot the combined machine; inject the CALSLT stub; break on its self-loop."""
    cap = _capture_proc2(OURS2_CODES, OURS2_STORE, OURS2_OPENRES, OURS2_CLOSERES,
                         OURS2_FCBSNAP1, OURS2_FCBSNAP2, OURS2_FCBSNAP3, out)
    tcl = f"""set throttle off
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
{cap}
proc go {{}} {{
  debug write_block memory 0x{OURS2_FCB:04X} [binary format H* {FCB2.hex()}]
  debug write_block memory 0x{OURS2_STUB:04X} [binary format H* {OURS2_STUB_HEX}]
  reg PC 0x{OURS2_STUB:04X}
  debug set_bp 0x{OURS2_DONE:04X} {{[__hex 0x{OURS2_GUARD:04X} 1] eq "a5"}} {{ cap }}
}}
after time 11 {{ go }}
after time 40 {{ cap }}
"""
    return _run(machine, dsk, tcl, out, timeout=55)


# ---------------------------------------------------------------------------
# FCB field map (MSX2 TH / CP/M FCB layout — see disk/PROVENANCE.md §FCB layout).
# offset -> (name, length). We compare these between ref (MSX-DOS) and ours,
# splitting them into MATCHED (fields a general FCB caller would read, that
# bdos_entry chooses to track) and DOCUMENTED INTENTIONAL DIVERGENCE (MSX-DOS
# internal bookkeeping no zerobas caller reads — the probe reports, never fails).
FCB_FIELDS = [
    (0,  1,  "drive"),
    (1,  11, "name8.3"),
    (12, 1,  "extent"),
    (13, 2,  "S1/S2"),
    (15, 1,  "rec_count"),
    (16, 16, "alloc_map"),
    (32, 1,  "cur_record"),
    (33, 3,  "rand_record"),
]
# Fields zerobas's bdos_entry advances to match a reasonable FCB caller.
FCB_MATCHED = {"drive", "name8.3"}
# Everything else is MSX-DOS-internal bookkeeping no zerobas caller (BLOAD/LOAD/
# RUN read only A + DTA) consults -> documented intentional divergence.


def _fcb_slice(hexstr: str, off: int, ln: int) -> str:
    return hexstr[off * 2:(off + ln) * 2]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True,
                    help="a plain MSX-DOS 1 system disk that boots to A> "
                         "(MSXDOS.SYS + COMMAND.COM; not a game/menu disk)")
    ap.add_argument("--our-machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    args = ap.parse_args()
    if not args.our_machine:
        sys.exit("no zerobas machine: pass --our-machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    work = "/tmp/zerobas_bdos_dos.dsk"
    build_dos_disk(args.dos_disk, work)

    ref = run_ref(args.ref_machine, work, "/tmp/disk_probe_bdos_ref.txt")
    ours = run_ours(args.our_machine, work, "/tmp/disk_probe_bdos_ours.txt")

    want_records = [oracle_bin()[r * 128:(r + 1) * 128].hex() for r in range(N_RECORDS)]
    want_codes = "00" * N_RECORDS + "01"          # 16 records delivered, then EOF

    ok = True

    def check(label, good):
        nonlocal ok
        ok = ok and good
        print(f"  [{'PASS' if good else 'FAIL'}] {label}")

    print(f"Open:  ref={ref['open']} ours={ours['open']} (expect 00)")
    check("Open result identical and success",
          ref["open"] == ours["open"] == "00")
    print(f"codes: ref={ref['codes']}")
    print(f"       ours={ours['codes']}")
    check("result codes identical (16x $00 record, then $01 EOF)",
          ref["codes"] == ours["codes"] == want_codes)
    recs_ok = True
    for r in range(N_RECORDS):
        if not (ref[f"rec{r}"] == ours[f"rec{r}"] == want_records[r]):
            recs_ok = False
            print(f"    rec{r}: ref={ref[f'rec{r}'][:8]}.. ours={ours[f'rec{r}'][:8]}.. "
                  f"want={want_records[r][:8]}..")
    check(f"all {N_RECORDS} records byte-identical (ref == ours == ORACLE.BIN)", recs_ok)
    print(f"Close: ref={ref['close']} ours={ours['close']} (expect 00)")
    check("Close result identical and success",
          ref["close"] == ours["close"] == "00")

    # ===================================================================
    # PART A — sub-record EOF bounding (1500-byte file; FULL differential).
    print("\n=== PART A: sub-record EOF (ORACLE2.BIN = 1500 bytes) ===")
    work2 = "/tmp/zerobas_bdos_dos2.dsk"
    build_dos_disk2(args.dos_disk, work2)
    ref2 = run_ref2(args.ref_machine, work2, "/tmp/disk_probe_bdos_ref2.txt")
    ours2 = run_ours2(args.our_machine, work2, "/tmp/disk_probe_bdos_ours2.txt")

    data2 = oracle2_bin()
    # Expected per-record bytes: real file bytes, then $00 zero-fill to 128
    # (ORACLE OBSERVATION of MSX-DOS 1: partial record zero-padded; see module
    #  docstring + disk/PROVENANCE.md §BDOS interface).
    want2_records = []
    for r in range(N_RECORDS2):
        start = r * 128
        real = max(0, min(128, SIZE2 - start))
        rec = data2[start:start + real] + bytes(128 - real)
        want2_records.append(rec.hex())
    # 12 records delivered ($00), then EOF ($01); the EOF read's record bytes are
    # don't-care (no record delivered), so we do NOT diff rec12's contents.
    want2_codes = "00" * 12 + "01"

    print(f"Open:  ref={ref2['open']} ours={ours2['open']} (expect 00)")
    check("A: Open result identical and success",
          ref2["open"] == ours2["open"] == "00")
    print(f"codes: ref ={ref2['codes']}")
    print(f"       ours={ours2['codes']}  (want {want2_codes})")
    check("A: result codes identical (12x $00, then $01 EOF)",
          ref2["codes"] == ours2["codes"] == want2_codes)

    # Diff the 12 DELIVERED records byte-for-byte, incl. the partial record 11.
    recs2_ok = True
    for r in range(12):
        if not (ref2[f"rec{r}"] == ours2[f"rec{r}"] == want2_records[r]):
            recs2_ok = False
            print(f"    rec{r}: ref={ref2[f'rec{r}']} \n          ours={ours2[f'rec{r}']}"
                  f"\n          want={want2_records[r]}")
    check("A: 12 delivered records byte-identical (incl. 92B partial + 36B $00 pad)",
          recs2_ok)
    # The observed pad byte, reported explicitly.
    partial = ref2["rec11"]
    pad_hex = partial[92 * 2:]
    pad_set = set(pad_hex)
    print(f"  partial record 11: 92 real bytes + {(128-92)} pad bytes; "
          f"MSX-DOS pad value = ${'00' if pad_set == {'0'} else '??'} "
          f"(oracle: {'zero-fill confirmed' if pad_set == {'0'} else pad_hex})")

    # ===================================================================
    # PART B — FCB-field mutations (OBSERVE + classify; report, never fail on
    # the documented-divergence fields). Compare ref vs ours at three points.
    print("\n=== PART B: FCB-field comparison (matched vs intentional divergence) ===")
    print("  legend: '=' ref==ours, 'x' differ;  [MATCH] field zerobas tracks, "
          "[DIVERGE] documented intentional divergence")
    snap_labels = [("fcb1", "after Open"), ("fcb2", "after 2 SeqReads"),
                   ("fcb3", "after Close")]
    matched_ok = True
    for key, when in snap_labels:
        print(f"  --- {when} ---")
        rhex, ohex = ref2[key], ours2[key]
        for off, ln, name in FCB_FIELDS:
            rv = _fcb_slice(rhex, off, ln)
            ov = _fcb_slice(ohex, off, ln)
            same = rv == ov
            tag = "[MATCH]  " if name in FCB_MATCHED else "[DIVERGE]"
            mark = "=" if same else "x"
            print(f"    {tag} +{off:<2} {name:<11} {mark}  ref={rv} ours={ov}")
            if name in FCB_MATCHED and not same:
                matched_ok = False
    check("B: all MATCHED FCB fields (drive, name) identical ref==ours", matched_ok)
    print("  NOTE: [DIVERGE] fields (extent +12, cur_record +32, rec_count +15,\n"
          "        alloc_map +16..31, S1/S2 +13..14) are MSX-DOS-internal FCB\n"
          "        bookkeeping. zerobas keeps file position in the FAT iterator +\n"
          "        BDOS_RECIDX/BDOS_BYTESLEFT, and its only callers (BLOAD/LOAD/RUN)\n"
          "        read just A + the DTA — never FCB fields — so these are a\n"
          "        DOCUMENTED INTENTIONAL DIVERGENCE, not a failure (disk/\n"
          "        PROVENANCE.md §BDOS interface).")

    print("\n" + (
        "ALL PASS — zerobas bdos_entry: narrow + sub-record EOF byte-identical to\n"
        "           MSX-DOS 1 (data + A-codes); matched FCB fields identical; FCB\n"
        "           bookkeeping divergences documented & intentional"
        if ok else "FAIL — see mismatches above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
