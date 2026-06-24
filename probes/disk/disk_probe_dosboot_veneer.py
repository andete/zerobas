#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Veneer-hypothesis probe: are the COMMAND.COM-load kernel entries CALL targets?

The unified-ROM plan (spec-diskrom-kernel.md §5) hosts the real MSXDOS.SYS +
COMMAND.COM by exposing the ~21 shared-kernel entry points at their canonical
page-1 addresses. The cheapest faithful way is a *trampoline veneer*: a small
`JP impl` at each canonical address, with the contract implemented in free ROM
space. That is only safe if every canonical entry is reached as a **CALL** (the
caller expects control to RETURN), never as a JP / fall-through tail-transfer.

This probe verifies that BLACK-BOX (no disassembly, no reading of proprietary
kernel bytes): for each canonical address it counts entries, records the first
caller (+ its region), and — by watching purely for control returning to the
caller's return address — counts how many invocations RETURN to their caller.

  entries == returns, for all 21  =>  every entry is a CALLed subroutine
                                      =>  the trampoline veneer is safe.

Run against the stock oracle:

    python3 probes/disk/disk_probe_dosboot_veneer.py --dos-disk /tmp/dos.dsk
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"

# The 21 canonical kernel entries reached during the COMMAND.COM load phase
# (spec §5.2). 16 collide with zerobas's active code, 5 sit in free space.
CANON = [
    0x41FD, 0x4558, 0x46C8, 0x47B2, 0x4919, 0x4935, 0x498C, 0x49B4, 0x4A39,
    0x4B59, 0x4BE5, 0x4C25, 0x4E4B, 0x4EDE, 0x4010, 0x5FE5, 0x607B, 0x75A5,
    0x77B8, 0x782B, 0x402D,
]


def run(machine: str, dsk: str, settle: float, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    canon_tcl = " ".join(f"0x{a:04X}" for a in CANON)
    tcl = f"""set throttle off
set renderer none
array set ::ent {{}}        ;# C(hex) -> entry count
array set ::ret {{}}        ;# C(hex) -> clean-return-confirmed (0/1)
array set ::caller {{}}     ;# C(hex) -> first caller ra (hex)
array set ::region {{}}     ;# C(hex) -> region of first caller
array set ::confirmed {{}}  ;# C(hex) -> 1 once a clean return is seen
array set ::cond {{}}       ;# id -> in-flight condition handle
set ::cid 0

proc region {{a}} {{
  if {{$a >= 0xC000}} {{ return kernel }}
  if {{$a >= 0x8000}} {{ return page2 }}
  if {{$a >= 0x4000}} {{ return rom-internal }}
  if {{$a >= 0x0100}} {{ return command.com }}
  return lowmem
}}

# An entry is a CALL target (veneer-safe) iff, after entry at SP=esp, control
# returns to its caller [esp] with the frame popped (PC==[esp] && SP==esp+2).
# That test is collision-free even when sibling entries share a caller, because
# it is qualified by this call's own esp. Arm it once, on the first invocation.
proc on_clean_ret {{C id}} {{
  set ::confirmed($C) 1
  if {{![info exists ::ret($C)]}} {{ set ::ret($C) 0 }}
  incr ::ret($C)
  if {{[info exists ::cond($id)]}} {{
    debug remove_condition $::cond($id)
    unset ::cond($id)
  }}
}}

proc on_entry {{C}} {{
  if {{![info exists ::ent($C)]}} {{ set ::ent($C) 0 }}
  incr ::ent($C)
  set sp [reg SP]
  set lo [expr {{int([debug read memory $sp]) & 0xFF}}]
  set hi [expr {{int([debug read memory [expr {{($sp + 1) & 0xFFFF}}]]) & 0xFF}}]
  set ra [expr {{$lo | ($hi << 8)}}]
  set rah [format %04X $ra]
  if {{![info exists ::caller($C)]}} {{
    set ::caller($C) $rah
    set ::region($C) [region $ra]
  }}
  if {{$::ent($C) == 1}} {{
    set retsp [expr {{($sp + 2) & 0xFFFF}}]
    incr ::cid
    set id $::cid
    set ::cond($id) [debug set_condition "\\[reg PC\\] == $ra && \\[reg SP\\] == $retsp" "on_clean_ret $C $id"]
  }}
}}

foreach c {{{canon_tcl}}} {{
  set ch [format %04X $c]
  debug set_bp $c {{}} "on_entry $ch"
}}

proc finish {{}} {{
  if {{[info exists ::done]}} return
  set ::done 1
  set f [open {{{out}}} w]
  foreach c {{{canon_tcl}}} {{
    set ch [format %04X $c]
    set e 0; if {{[info exists ::ent($ch)]}} {{ set e $::ent($ch) }}
    set r 0; if {{[info exists ::ret($ch)]}} {{ set r $::ret($ch) }}
    set ca ----; if {{[info exists ::caller($ch)]}} {{ set ca $::caller($ch) }}
    set rg -; if {{[info exists ::region($ch)]}} {{ set rg $::region($ch) }}
    puts $f "$ch ent=$e ret=$r caller=$ca region=$rg"
  }}
  close $f
  exit
}}

after time {settle:.1f} {{ finish }}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    print(f"=== veneer hypothesis: are the canonical entries CALLed? ({args.machine}) ===")
    rows = run(args.machine, args.dos_disk, args.settle, args.timeout)
    print("(ret=1 => first invocation cleanly returned to its caller: a CALL target)")
    unconfirmed = []
    for ln in rows:
        parts = dict(p.split("=", 1) for p in ln.split()[1:])
        e, r = int(parts["ent"]), int(parts["ret"])
        if e == 0:
            flag = "  (never reached this boot)"
        elif r >= 1:
            flag = "  CALLed -> veneer-safe"
        else:
            flag = "  <-- UNCONFIRMED (no clean RET to caller; investigate)"
            unconfirmed.append(ln.split()[0])
        print(f"  ${ln}{flag}")
    print()
    if not unconfirmed:
        print("VENEER-SAFE: every reached entry is a CALL target.")
    else:
        print(f"UNCONFIRMED entries (need a closer look): {', '.join(unconfirmed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
