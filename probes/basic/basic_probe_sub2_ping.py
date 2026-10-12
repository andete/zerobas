#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SUB2 (b) gate: BOTH sub ROMs present, placed and page-selective, on BOTH
repack machines -- before main spends a byte on reaching the second one.

`make sub2-acceptance`. Boots each shipped machine (C-BIOS_MSX1_EU_REPACK_DISK
and _NODISK, the two `make repack-machine` writes) to the BASIC prompt, then
injects a stub into RAM ($C000) and redirects the CPU into it. Under DI it does
four CALSLTs, one per island, each after clearing SUB_PING ($F105):

    slot $8B (3-2) ix=$0040 -> zerobas-sub   page-0 ping writes $C0 -> $C100
    slot $8B (3-2) ix=$4010 -> zerobas-sub   page-1 ping writes $C1 -> $C101
    slot $8F (3-3) ix=$0040 -> zerobas-sub2  page-0 ping writes $C2 -> $C102
    slot $8F (3-3) ix=$4010 -> zerobas-sub2  page-1 ping writes $C3 -> $C103

and halts on a breakpoint. Four DISTINCT tags, so each row tells "reached the
right island" from "reached the other ROM". "Reached nothing" is louder than
a $00: a CALSLT into an EMPTY 3-3 never returns -- the runaway overwrites RAM,
and every row, SUBSLOT included, reads $FF (knife K-2B1, scratchpad/
sub2b_knife.py; I had predicted the cell would stay $00). It also reads SUBSLOT
($F106), which discovery (init_ext_roms, by the "ZB" marker) must still set to
$8B: sub2 carries "Z2" precisely so that a second ROM cannot capture it --
and it would: marked "ZB", discovery records 3-3, $8F (knife K-2B2).

D-SUB2 (c) adds MAIN's side: SUBSLOT2 ($F14B) must read $8F (try_sub_slot
records the "Z2" ROM there), and a fifth call goes through main's own
`subrom2_call` (its address read from build/basic-reloc.sym) with ix=$4010 --
it must reach ROM 2's page-1 ping ($C3 -> $C104) on its own slot lookup.

A 12 s safety net captures anyway if a CALSLT hangs, so the gate FAILS cleanly.
Clean room: own ROMs, RAM cells, CALSLT (a published BIOS entry).

Prediction (first run, 2026-10-12): C0 C1 C2 C3 and SUBSLOT $8B on both.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "C-BIOS_MSX1_EU_REPACK_NODISK")
SUB_PING, SUBSLOT, SUBSLOT2 = 0xF105, 0xF106, 0xF14B
MAIN_CELL = 0xC104
STUB = 0xC000
CALLS = ((0x8B, 0x0040, 0xC100, 0xC0, "3-2 page 0 (zerobas-sub) "),
         (0x8B, 0x4010, 0xC101, 0xC1, "3-2 page 1 (zerobas-sub) "),
         (0x8F, 0x0040, 0xC102, 0xC2, "3-3 page 0 (zerobas-sub2)"),
         (0x8F, 0x4010, 0xC103, 0xC3, "3-3 page 1 (zerobas-sub2)"))


def main_sym(name: str) -> int:
    """An address from the build's .sym (the merged ROM's BASIC is that image)."""
    for ln in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        f = ln.split()
        if len(f) >= 3 and f[0] == name and f[1].upper() == "EQU":
            return int(f[2].rstrip("Hh"), 16)
    sys.exit(f"{name} not in build/basic-reloc.sym -- build first (make basic-reloc)")


def stub() -> tuple[bytes, int]:
    b = bytearray([0xF3])                                   # di
    for slot, ix, cell, _, _ in CALLS:
        b += bytes([0xAF, 0x32, SUB_PING & 0xFF, SUB_PING >> 8,   # xor a / ld (SUB_PING),a
                    0xFD, 0x21, 0x00, slot,                       # ld iy,slot<<8
                    0xDD, 0x21, ix & 0xFF, ix >> 8,               # ld ix,entry
                    0xCD, 0x1C, 0x00,                             # call CALSLT
                    0x3A, SUB_PING & 0xFF, SUB_PING >> 8,         # ld a,(SUB_PING)
                    0x32, cell & 0xFF, cell >> 8])                # ld (cell),a
    sr2 = main_sym("subrom2_call")
    b += bytes([0xAF, 0x32, SUB_PING & 0xFF, SUB_PING >> 8,       # xor a / ld (SUB_PING),a
                0xDD, 0x21, 0x10, 0x40,                           # ld ix,$4010
                0xCD, sr2 & 0xFF, sr2 >> 8,                       # call subrom2_call
                0xF3,                                             # di (it EIs on return)
                0x3A, SUB_PING & 0xFF, SUB_PING >> 8,             # ld a,(SUB_PING)
                0x32, MAIN_CELL & 0xFF, MAIN_CELL >> 8])          # ld (MAIN_CELL),a
    halt = STUB + len(b)
    b.append(0x76)                                          # halt (the capture bp)
    return bytes(b), halt


def run(machine: str) -> dict | None:
    code, halt = stub()
    fd, out = tempfile.mkstemp(suffix=".txt", prefix="sub2ping_")
    os.close(fd)
    os.unlink(out)
    cells = [c for _, _, c, _, _ in CALLS] + [SUBSLOT, SUBSLOT2, MAIN_CELL]
    lines = [
        "set throttle off",
        "proc __hex {addr} { binary scan [debug read_block memory $addr 1] H* h; return $h }",
        "proc __cap {} {",
        f"  set f [open {{{out}}} w]",
        *[f'  puts $f "{c:04x}=[__hex {c}]"' for c in cells],
        "  close $f",
        "  exit",
        "}",
        "after time 8.0 {",
        f"  debug write_block memory {STUB} [binary format H* {{{code.hex()}}}]",
        *[f"  debug write memory {c} 0x00" for _, _, c, _, _ in CALLS + ((0, 0, MAIN_CELL, 0, ""),)],
        f"  debug set_bp {halt} {{}} {{ __cap }}",
        f"  reg PC {STUB}",
        "}",
        "after time 12.0 { __cap }",
    ]
    fd, tcl = tempfile.mkstemp(suffix=".tcl", prefix="sub2ping_")
    os.write(fd, ("\n".join(lines) + "\n").encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine, "-command",
           "set renderer none; set sound_driver null", "-script", tcl]
    try:
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + 90
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            return None
    finally:
        os.unlink(tcl)
    if not os.path.exists(out):
        return None
    res = {}
    for ln in open(out):
        k, _, v = ln.strip().partition("=")
        res[int(k, 16)] = int(v, 16) if v else None
    os.unlink(out)
    return res


def main() -> int:
    ok = True
    for m in MACHINES:
        res = run(m)
        if res is None:
            print(f"{m}: FAIL -- no capture (openMSX did not run the stub)")
            ok = False
            continue
        for slot, ix, cell, want, what in CALLS:
            got = res.get(cell)
            good = got == want
            ok &= good
            print(f"{m:30s} {what} CALSLT ${slot:02X}:${ix:04X} -> "
                  f"SUB_PING ${got:02X} (expect ${want:02X}): {'PASS' if good else 'FAIL'}")
        sl = res.get(SUBSLOT)
        good = sl == 0x8B
        ok &= good
        print(f"{m:30s} discovery: SUBSLOT ${sl:02X} (expect $8B, ROM 1 in 3-2): "
              f"{'PASS' if good else 'FAIL'}")
        s2 = res.get(SUBSLOT2)
        good = s2 == 0x8F
        ok &= good
        print(f"{m:30s} discovery: SUBSLOT2 ${s2:02X} (expect $8F, ROM 2 in 3-3): "
              f"{'PASS' if good else 'FAIL'}")
        mc = res.get(MAIN_CELL)
        good = mc == 0xC3
        ok &= good
        print(f"{m:30s} main's subrom2_call ix=$4010 -> SUB_PING ${mc:02X} "
              f"(expect $C3): {'PASS' if good else 'FAIL'}")
    print("-------------------")
    print("sub2 ping gate:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
