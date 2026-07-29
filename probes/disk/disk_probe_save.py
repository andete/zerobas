#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end functional probe: SAVE / BSAVE to a real FAT12 disk, round-tripped.

This exercises the disk WRITE side of basic/save.asm (`do_bsave`, `do_save`, the
shared disk_write_begin / disk_putbyte / disk_write_end helper) on the combined
C-BIOS_MSX1_BASIC_DISK machine (zerobas-BASIC in slot 0 page 1, zerobas-disk in
slot 3-1) with a WRITABLE /tmp copy of disk/test720.dsk attached as drive A.

The write path:
  * cross-slot CALSLT into the disk ROM's bdos_entry;
  * BDOS $1A Set-DTA -> a writable page-3 buffer; $16 Create; $15 Sequential Write
    (one fixed 128-byte record from the DTA at a time -- disk_putbyte fills the
    record and flushes when it is full); $10 Close (flush partial + stamp dir size);
  * BSAVE writes [$FE][start][end][exec] + RAM[start..end] inclusive; SAVE writes
    [$FF] + the in-memory line-link program image.

Three round-trips, all written THEN read back by zerobas's own load side on the
SAME boot/disk, so each proves the file we wrote is the file we read:

  1. BSAVE -> BLOAD (data fidelity). Poison a known pattern into $C000..$C010,
     BSAVE it to "A:SV.BIN", overwrite that RAM region with a sentinel, then
     BLOAD"A:SV.BIN" (no ,R) -> the region must come back byte-identical to the
     saved pattern, proving the on-disk $FE header (start/end) + data are correct.

  2. BSAVE -> BLOAD,R (exec handoff). The saved blob is real Z80: LD A,$5A ;
     LD ($D000),A ; JR $ at $C010. After BLOAD"A:SV2.BIN",R the handoff jumps to
     exec (defaulted to start, since no ,exec arg) -> ($D000)=$5A and PC at the
     $C010 JR$ landmark. Proves the default exec address (= start) and the data.

  3. SAVE -> NEW -> RUN (program fidelity). Type `10 POKE &HD002,123`, SAVE it to
     "A:SV.BAS", NEW (wipe the store), then RUN"A:SV.BAS" -> the relinked store at
     $8001 matches the line-link image AND the program ran (($D002)=$7B). Proves
     the on-disk $FF tokenised-BASIC marker + the program image round-trip.

All three run in ONE openMSX session per round-trip, sequencing the typed lines
with `after time` events. Strictly black-box: we type REPL lines and observe RAM /
PC; no ROM is read or disassembled.

TEST DISK SAFETY. openMSX `-diska` writes back to the image, so this probe NEVER
touches the committed disk/test720.dsk -- it operates on a fresh /tmp copy made at
startup. The SV.BIN / SV2.BIN / SV.BAS files it creates are the only writes.

Prerequisites:
  * openMSX, and the combined machine installed from the CURRENT zerobas tree
    (`python3 tools/install-openmsx-machine.py --disk-rom disk.rom`) so slot 0's
    zerobas IPS and slot 3-1's disk.rom reflect the build under test;
  * disk/test720.dsk present (seed; copied to /tmp, never modified in place).

    python3 probes/disk/disk_probe_save.py
    python3 probes/disk/disk_probe_save.py --machine C-BIOS_MSX1_EU_BASIC_DISK
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
import tempfile
import time

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
ZEROBAS = os.environ.get(
    "ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SEED_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

# --- BSAVE data-fidelity fixture (round-trip 1) ----------------------------
BIN_START = 0xC000
BIN_END = 0xC010           # inclusive -> 17 bytes
# A deterministic, position-varying pattern (NOT all-equal, so a stuck/short
# write is visible). byte[i] = (0x5A ^ i) & 0xFF.
PATTERN = bytes(((0x5A ^ i) & 0xFF) for i in range(BIN_END - BIN_START + 1))
BIN_SENTINEL = 0xA5        # overwrite the region with this before BLOAD-back
# NB: a NONZERO sentinel is deliberate — if BLOAD is a no-op (e.g. its typed line got
# corrupted), the region keeps the sentinel; a 0x00 sentinel would masquerade as
# "loaded zeros" and mislead a reader into suspecting the ROM write path. See the
# leading-space hardening on the typed commands below and openmsx-probing-toolbox.md.

# --- BSAVE ,R exec fixture (round-trip 2) ----------------------------------
EXE_START = 0xC000
EXE_END = 0xC011           # inclusive (covers the 2-byte JR$ at $C010..$C011)
EXE_LANDMARK = 0xC010      # JR $ inside the blob (the ,R handoff landmark)
EXE_MARK_ADDR = 0xD000
EXE_MARK_BYTE = 0x5A
EXE_SENTINEL = 0xA5        # pre-poison EXE_MARK_ADDR (!= EXE_MARK_BYTE)
# LD A,$5A ; LD ($D000),A ; NOP pad to $C010 ; JR $   (data into [C000..C010])
EXE_BODY = (bytes([0x3E, EXE_MARK_BYTE, 0x32, EXE_MARK_ADDR & 0xFF, EXE_MARK_ADDR >> 8])
            + bytes((EXE_LANDMARK - EXE_START) - 5) + bytes([0x18, 0xFE]))
assert len(EXE_BODY) == EXE_END - EXE_START + 1, (len(EXE_BODY), EXE_END - EXE_START + 1)

# --- SAVE program-fidelity fixture (round-trip 3) --------------------------
TXTBASE = 0x8001
BAS_MARK_ADDR = 0xD002
BAS_MARK_BYTE = 0x7B       # 123
BAS_SENTINEL = 0xC4
POKE_TOKEN = 0x98
HEX_TOKEN = 0x0C
INT1_TOKEN = 0x0F
# `10 POKE &HD002,123` relinked store image (same shape as disk_probe_run_disk).
_BODY = bytes([POKE_TOKEN, 0x20,
               HEX_TOKEN, BAS_MARK_ADDR & 0xFF, BAS_MARK_ADDR >> 8,
               0x2C, INT1_TOKEN, BAS_MARK_BYTE, 0x00])
_LINE = struct.pack("<H", 0) + struct.pack("<H", 10) + _BODY
_NEXT = TXTBASE + len(_LINE)
EXP_IMAGE = struct.pack("<H", _NEXT) + _LINE[2:] + struct.pack("<H", 0)
IMG_LEN = len(EXP_IMAGE)


def _hexproc() -> str:
    return ("proc __hex {a l} { binary scan "
            "[debug read_block memory $a $l] H* h; return $h }\n")


def _writeblock(addr: int, data: bytes) -> str:
    """A TCL line that writes `data` to `addr` via debug write_block (hex)."""
    return f'debug write_block memory 0x{addr:04X} [binary decode hex {data.hex()}]'


def _run(machine: str, tcl: str, out: str, dsk: str, timeout: float = 120.0) -> dict:
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", dsk,
           "-command", "set renderer none", "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture from {machine} (machine missing? disk absent?)")
    d = {}
    for ln in open(out):
        k, _, v = ln.strip().partition("=")
        d[k] = v
    return d


def fresh_disk() -> str:
    """A /tmp writable copy of the seed image (never touch the committed one)."""
    fd, path = tempfile.mkstemp(suffix=".dsk", prefix="save_probe_")
    os.close(fd)
    shutil.copyfile(SEED_DSK, path)
    return path


# CONVENTION (2026-07-05): every `type {{ … }}` command below is deliberately prefixed
# with a LEADING SPACE. openMSX `type`-injection can double the first keypress inside a
# narrow machine-specific emutime window (~t=26-27 on C-BIOS_MSX1_BASIC_DISK with a disk
# mounted); a doubled leading space is harmless (`skip_spaces` eats it) whereas a doubled
# command letter (`bbload`) is a syntax error. This cost a full false-positive bug hunt —
# see disk/docs/openmsx-probing-toolbox.md §8 GOTCHA + tier2-review-queue.md 2026-07-05.
# (This whole type-injection probe is being superseded by a .bas-on-disk boot-auto-run test.)


# --- round-trip 1: BSAVE -> BLOAD (data fidelity) --------------------------
def rt_bsave_bload(machine: str, dsk: str) -> dict:
    out = "/tmp/save_rt1.txt"
    tcl = f"""set throttle off
{_hexproc()}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "region=[__hex 0x{BIN_START:04X} {len(PATTERN)}]"
  close $f; exit
}}
# t=6: lay down the known pattern in [C000..C010].
after time 6 {{ {_writeblock(BIN_START, PATTERN)} }}
# t=8: BSAVE the region to the disk.
after time 8  {{ type {{ bsave"a:sv.bin",&h{BIN_START:04x},&h{BIN_END:04x}}} }}
after time 11 {{ type "\\r" }}
# t=24: overwrite the RAM region with a sentinel so the reload is unambiguous.
# MUST be well after BSAVE finishes streaming RAM[start..end] -- BSAVE reads the
# source bytes lazily during the disk write, so an early wipe would race it and
# save the sentinel instead of the pattern.
after time 24 {{ {_writeblock(BIN_START, bytes([BIN_SENTINEL]) * len(PATTERN))} }}
# t=26: BLOAD it back (no ,R) into the same start address.
after time 26 {{ type {{ bload"a:sv.bin"}} }}
after time 29 {{ type "\\r" }}
after time 44 {{ cap }}
"""
    return _run(machine, tcl, out, dsk, timeout=140.0)


# --- round-trip 2: BSAVE -> BLOAD,R (exec handoff, default exec=start) ------
def rt_bsave_bload_r(machine: str, dsk: str) -> dict:
    out = "/tmp/save_rt2.txt"
    tcl = f"""set throttle off
{_hexproc()}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "pc=[format %04X [reg PC]]"
  puts $f "marker=[__hex 0x{EXE_MARK_ADDR:04X} 1]"
  close $f; exit
}}
# t=6: lay down the exec blob and poison the exec-marker target.
after time 6 {{ {_writeblock(EXE_START, EXE_BODY)} }}
after time 6 {{ debug write memory 0x{EXE_MARK_ADDR:04X} 0x{EXE_SENTINEL:02X} }}
# t=8: BSAVE with NO ,exec arg -> exec defaults to start ($C000).
after time 8  {{ type {{ bsave"a:sv2.bin",&h{EXE_START:04x},&h{EXE_END:04x}}} }}
after time 11 {{ type "\\r" }}
# t=24: wipe the blob from RAM so the reload must restore it (well after BSAVE
# has finished streaming RAM[start..end] -- see the rt1 note on the wipe race).
after time 24 {{ {_writeblock(EXE_START, bytes(len(EXE_BODY)))} }}
# also re-poison the exec marker so a stale value can't masquerade as a fresh exec.
after time 24 {{ debug write memory 0x{EXE_MARK_ADDR:04X} 0x{EXE_SENTINEL:02X} }}
# t=26: BLOAD,R -> reload + jump to exec.
after time 26 {{ type {{ bload"a:sv2.bin",r}} }}
after time 29 {{ type "\\r" }}
# break when execution reaches the blob's JR$ landmark = the ,R handoff fired.
debug set_bp 0x{EXE_LANDMARK:04X} {{}} {{ cap }}
after time 55 {{ cap }}
"""
    return _run(machine, tcl, out, dsk, timeout=140.0)


# --- round-trip 3: SAVE -> NEW -> RUN (program fidelity) -------------------
def rt_save_run(machine: str, dsk: str) -> dict:
    out = "/tmp/save_rt3.txt"
    tcl = f"""set throttle off
{_hexproc()}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "image=[__hex 0x{TXTBASE:04X} {IMG_LEN}]"
  puts $f "marker=[__hex 0x{BAS_MARK_ADDR:04X} 1]"
  close $f; exit
}}
# t=5: poison the run-marker target.
after time 5 {{ debug write memory 0x{BAS_MARK_ADDR:04X} 0x{BAS_SENTINEL:02X} }}
# t=8: type the one-line program into the store.
after time 8  {{ type {{ 10 poke &h{BAS_MARK_ADDR:04x},{BAS_MARK_BYTE}}} }}
after time 11 {{ type "\\r" }}
# t=14: SAVE the tokenised program to disk.
after time 14 {{ type {{ save"a:sv.bas"}} }}
after time 17 {{ type "\\r" }}
# t=22: NEW -> wipe the in-memory store, so RUN must reload it from disk.
after time 22 {{ type {{ new}} }}
after time 25 {{ type "\\r" }}
# t=30: RUN"A:SV.BAS" -> load the tokenised program AND run it.
after time 30 {{ type {{ run"a:sv.bas"}} }}
after time 33 {{ type "\\r" }}
after time 44 {{ cap }}
"""
    return _run(machine, tcl, out, dsk, timeout=140.0)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    if not os.path.exists(SEED_DSK):
        sys.exit(f"missing seed image {SEED_DSK} (run tools/make_test_dsk.py)")

    ok = True

    # --- 1: BSAVE -> BLOAD -------------------------------------------------
    dsk = fresh_disk()
    try:
        d = rt_bsave_bload(args.machine, dsk)
    finally:
        os.unlink(dsk)
    region = bytes.fromhex(d.get("region", ""))
    r1 = region == PATTERN
    ok = ok and r1
    print('BSAVE"A:SV.BIN",&HC000,&HC010  ->  BLOAD"A:SV.BIN"')
    print(f"  [{'PASS' if r1 else 'FAIL'}] [{BIN_START:04X}..{BIN_END:04X}] reloaded "
          f"{'byte-identical' if r1 else 'DIFFERS'} to the saved pattern")
    if not r1:
        print(f"        got {region.hex()}\n        exp {PATTERN.hex()}")

    # --- 2: BSAVE -> BLOAD,R ----------------------------------------------
    dsk = fresh_disk()
    try:
        d = rt_bsave_bload_r(args.machine, dsk)
    finally:
        os.unlink(dsk)
    pc = int(d.get("pc", "0000"), 16)
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0
    pc_ok = pc == EXE_LANDMARK
    mark_ok = marker == EXE_MARK_BYTE
    r2 = pc_ok and mark_ok
    ok = ok and r2
    print('\nBSAVE"A:SV2.BIN",&HC000,&HC010  ->  BLOAD"A:SV2.BIN",R')
    print(f"  [{'PASS' if pc_ok else 'FAIL'}] ,R handoff: PC=${pc:04X} "
          f"(expect ${EXE_LANDMARK:04X} JR$ landmark; exec defaulted to start)")
    print(f"  [{'PASS' if mark_ok else 'FAIL'}] exec ran: (${EXE_MARK_ADDR:04X})=${marker:02X} "
          f"(expect ${EXE_MARK_BYTE:02X}, sentinel was ${EXE_SENTINEL:02X})")

    # --- 3: SAVE -> NEW -> RUN --------------------------------------------
    dsk = fresh_disk()
    try:
        d = rt_save_run(args.machine, dsk)
    finally:
        os.unlink(dsk)
    image = bytes.fromhex(d.get("image", ""))
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0
    img_ok = image == EXP_IMAGE
    run_ok = marker == BAS_MARK_BYTE
    r3 = img_ok and run_ok
    ok = ok and r3
    print('\nSAVE"A:SV.BAS"  ->  NEW  ->  RUN"A:SV.BAS"')
    print(f"  [{'PASS' if img_ok else 'FAIL'}] store at ${TXTBASE:04X} "
          f"{'matches' if img_ok else 'DIFFERS from'} the relinked line-link image")
    if not img_ok:
        print(f"        got {image.hex()}\n        exp {EXP_IMAGE.hex()}")
    print(f"  [{'PASS' if run_ok else 'FAIL'}] reloaded program ran: "
          f"(${BAS_MARK_ADDR:04X})=${marker:02X} (expect ${BAS_MARK_BYTE:02X})")

    print("\n" + ("ALL PASS -- SAVE/BSAVE write files that round-trip through "
                  "BLOAD/LOAD/RUN" if ok else "FAIL -- see per-check results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
