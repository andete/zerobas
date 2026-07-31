#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end functional probe: BLOAD"A:PROG.BIN"[,R] from a real FAT12 disk.

This exercises the full disk BLOAD execute path in basic/bload.asm on the combined
C-BIOS_MSX1_BASIC_DISK machine (zerobas-BASIC in slot 0 page 1, zerobas-disk in
slot 3-1) with disk/test720.dsk attached as drive A. The path:

  * cross-slot CALSLT into the disk ROM's bdos_entry (slot from the INIT scan's
    DISKSLOT, address from SYSTEM $F37D);
  * BDOS $1A Set-DTA -> a writable page-3 buffer (page 0 is BIOS ROM here, so the
    $0080 default would silently fail);
  * BDOS $0F Open of "A:PROG.BIN", $14 SeqRead streaming, $10 Close;
  * parse the 7-byte on-disk BSAVE header [$FE][start][end][exec] (LE) and load
    the data bytes into [start..end] inclusive;
  * the ,R exec handoff (jp to exec).

PROG.BIN (built by zerobas tools/make_test_dsk.py) is a real BSAVE binary:
  header  : $FE start=$C000 end=$C031 exec=$C000
  payload : LD A,$5A ; LD ($D000),A ; (NOP pad) ; JR $ at $C010 ; data 00..1F
So after BLOAD"A:PROG.BIN",R fires the handoff, the blob writes $5A to $D000 and
self-loops at $C010. We assert:
  (a) the data landed   -> [$C000..$C031] equals the BSAVE body bytes;
  (b) the ,R handoff ran -> $D000 == $5A and PC sits at the $C010 landmark.
And a separate plain BLOAD"A:PROG.BIN" (no ,R): the bytes load but the handoff
must NOT run -> $D000 stays at a pre-poisoned sentinel and BASIC returns to the
REPL (we confirm the load via the loaded bytes, and non-exec via the sentinel).

Strictly black-box: we type a line into the REPL and observe RAM / PC. No ROM is
read or disassembled. Sync on an event (the JR$ landmark for ,R); the plain case
has no landmark, so it syncs on time after the load is guaranteed complete.

Prerequisites:
  * openMSX, and the combined machine installed from the CURRENT zerobas tree
    (`python3 tools/install-openmsx-machine.py --disk-rom disk.rom`) so slot 0's
    zerobas IPS and slot 3-1's disk.rom reflect the build under test;
  * disk/test720.dsk regenerated from the current tree
    (`python3 tools/make_test_dsk.py`).

    python3 probes/disk/disk_probe_bload_disk.py
    python3 probes/disk/disk_probe_bload_disk.py --machine C-BIOS_MSX1_EU_BASIC_DISK
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
import signal
import subprocess
import shutil
import sys
import time

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
# The test image lives in this repo at disk/test720.dsk (the disk ROM's home).
# Allow an override via $ZEROBAS; default to the repo root.
ZEROBAS = os.environ.get(
    "ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

# PROG.BIN BSAVE payload (must match tools/make_test_dsk.py).
PROG_START = 0xC000
PROG_END = 0xC031          # inclusive
LANDMARK = 0xC010          # JR $ inside the blob (the ,R exec handoff landmark)
MARKER_ADDR = 0xD000
MARKER_BYTE = 0x5A
SENTINEL = 0xA5            # pre-poison MARKER_ADDR with this (!= MARKER_BYTE)
# Expected loaded body: LD A,5A ; LD (D000),A ; NOP*11 ; JR $ ; data 00..1F
EXP_BODY = (bytes([0x3E, MARKER_BYTE, 0x32, MARKER_ADDR & 0xFF, MARKER_ADDR >> 8])
            + bytes(0x10 - 5) + bytes([0x18, 0xFE]) + bytes(range(32)))
BODY_LEN = PROG_END - PROG_START + 1
assert len(EXP_BODY) == BODY_LEN, (len(EXP_BODY), BODY_LEN)


def _hexproc() -> str:
    return ("proc __hex {a l} { binary scan "
            "[debug read_block memory $a $l] H* h; return $h }\n")


def run_run_case(machine: str, out: str, timeout: float = 90.0) -> dict:
    """BLOAD"A:PROG.BIN",R : poison MARKER, type the line, break at the JR$
    landmark, capture PC + loaded region + MARKER. Sync on the landmark event."""
    tcl = f"""set throttle off
{_hexproc()}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "pc=[format %04X [reg PC]]"
  puts $f "body=[__hex 0x{PROG_START:04X} {BODY_LEN}]"
  puts $f "marker=[__hex 0x{MARKER_ADDR:04X} 1]"
  close $f; exit
}}
# Poison the exec-landmark target so a real ,R write is unambiguous.
after time 5 {{ debug write memory 0x{MARKER_ADDR:04X} 0x{SENTINEL:02X} }}
# Type the BLOAD line once the REPL is up; commit Enter separately (throttle off
# drops a trailing CR in the same burst -- see docs/dev-workflow.md).
after time 8  {{ type {{bload"a:prog.bin",r}} }}
after time 11 {{ type "\\r" }}
# Break when execution reaches the blob's JR$ landmark = the ,R handoff fired.
debug set_bp 0x{LANDMARK:04X} {{}} {{ cap }}
# Safety net: if the landmark never fires, still capture so we report a clean FAIL.
after time 40 {{ cap }}
"""
    return _run_tcl(machine, tcl, out, timeout)


def run_plain_case(machine: str, out: str, timeout: float = 90.0) -> dict:
    """BLOAD"A:PROG.BIN" (no ,R): poison MARKER, type the line, then capture on a
    time well after the load completes. The handoff must NOT fire, so there is no
    landmark to sync on -- MARKER must remain the sentinel and the bytes loaded."""
    tcl = f"""set throttle off
{_hexproc()}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "pc=[format %04X [reg PC]]"
  puts $f "body=[__hex 0x{PROG_START:04X} {BODY_LEN}]"
  puts $f "marker=[__hex 0x{MARKER_ADDR:04X} 1]"
  close $f; exit
}}
after time 5 {{ debug write memory 0x{MARKER_ADDR:04X} 0x{SENTINEL:02X} }}
after time 8  {{ type {{bload"a:prog.bin"}} }}
after time 11 {{ type "\\r" }}
# No exec handoff, so no landmark: capture on time after the load is complete.
after time 30 {{ cap }}
"""
    return _run_tcl(machine, tcl, out, timeout)


def _run_tcl(machine: str, tcl: str, out: str, timeout: float) -> dict:
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", DSK,
           "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
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
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    return d


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    if not os.path.exists(DSK):
        sys.exit(f"missing test image {DSK} (run tools/make_test_dsk.py)")

    ok = True

    # --- ,R case -----------------------------------------------------------
    d = run_run_case(args.machine, "/tmp/disk_bload_run.txt")
    pc = int(d.get("pc", "0000"), 16)
    body = bytes.fromhex(d.get("body", ""))
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0

    body_ok = body == EXP_BODY
    pc_ok = pc == LANDMARK
    marker_ok = marker == MARKER_BYTE
    run_ok = body_ok and pc_ok and marker_ok
    ok = ok and run_ok
    print("BLOAD\"A:PROG.BIN\",R")
    print(f"  [{'PASS' if body_ok else 'FAIL'}] data bytes [{PROG_START:04X}..{PROG_END:04X}] "
          f"{'match' if body_ok else 'DIFFER'} the BSAVE body")
    if not body_ok:
        print(f"        got {body.hex()}\n        exp {EXP_BODY.hex()}")
    print(f"  [{'PASS' if pc_ok else 'FAIL'}] ,R handoff: PC=${pc:04X} "
          f"(expect ${LANDMARK:04X} JR$ landmark)")
    print(f"  [{'PASS' if marker_ok else 'FAIL'}] exec ran: (${MARKER_ADDR:04X})=${marker:02X} "
          f"(expect ${MARKER_BYTE:02X}, sentinel was ${SENTINEL:02X})")

    # --- plain (no ,R) case ------------------------------------------------
    d = run_plain_case(args.machine, "/tmp/disk_bload_plain.txt")
    body = bytes.fromhex(d.get("body", ""))
    marker = bytes.fromhex(d.get("marker", "00"))[0] if d.get("marker") else 0
    body_ok = body == EXP_BODY
    noexec_ok = marker == SENTINEL
    plain_ok = body_ok and noexec_ok
    ok = ok and plain_ok
    print("\nBLOAD\"A:PROG.BIN\"  (no ,R)")
    print(f"  [{'PASS' if body_ok else 'FAIL'}] data bytes [{PROG_START:04X}..{PROG_END:04X}] "
          f"{'match' if body_ok else 'DIFFER'} the BSAVE body")
    if not body_ok:
        print(f"        got {body.hex()}\n        exp {EXP_BODY.hex()}")
    print(f"  [{'PASS' if noexec_ok else 'FAIL'}] NO exec: (${MARKER_ADDR:04X})=${marker:02X} "
          f"(expect untouched sentinel ${SENTINEL:02X})")

    print("\n" + ("ALL PASS -- disk BLOAD loads bytes; ,R execs, plain does not"
                  if ok else
                  "FAIL -- see per-check results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
