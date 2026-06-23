#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box oracle: characterise the disk-work-area JUMP TABLE at
$F368-$F37C that MSXDOS.SYS's resident init CALLs (the §8.17 gap).

CONTEXT (zerobas Tier-2, disk/docs/provider-oracle-scope.md §8.16/§8.17). After
set_ramad fixed page-0 RAM, the zerobas-disk boot reaches MSXDOS.SYS's init, which
then does `CALL $F368` -- a fixed disk-work-area jump table the real disk ROM builds
(stock: $F368→JP $DF57, $F36B→$DF59, $F36E→$DF70, $F371→$F327, $F374→$F32C,
$F377/$F37A→$0000, $F37D→SYSTEM/BDOS). We populate only RAMAD ($F341) and SYSTEM
($F37D); $F368-$F37C is $FF on ours, so `CALL $F368` slides through $FF (RST 38h).

This probe runs on the genuine National CF-3300 and characterises the table the way
this project characterises every undocumented disk-ROM surface (GETDPB, $4030): as a
BLACK-BOX ORACLE. Two modes:

  --profile (default): trap each of the 8 table slots, count calls, and snapshot the
    FIRST call's input registers + caller return address per slot. Tells us WHICH
    slots MSXDOS.SYS uses and their rough role (input register convention).

  --slot $F368 (deep): trap that one slot, snapshot the FULL input contract (all
    registers + the return address off the stack), arm a one-shot breakpoint at the
    return, and snapshot the output registers + carry. Diffs in/out to report what
    the routine does -- the contract we reimplement in our own $F368 table.

CLEAN-ROOM. Strictly black-box: CPU breakpoints + register/RAM reads on the running
reference boot. We observe the table entries' input/output behaviour; we never read,
dump, or disassemble the $DFxx resident-kernel code the entries jump to, nor
MSXDOS.SYS. (Reimplementing from an observed in/out contract is the GETDPB/$4030
discipline; the $DFxx bytes are never lifted.)

DISK SAFETY: boots only a /tmp copy of the DOS disk, never the permanent one.

Prerequisites:
  * openMSX with the genuine National CF-3300 ROMs installed (you provide them):
    cf-3300_basic-bios1.rom + cf-3300_disk.rom in systemroms.
  * a real MSX-DOS 1 system disk image (pass with --dos-disk).

    python3 probes/disk/disk_probe_dosboot_f368.py --dos-disk ~/Documents/msx/msx/disks/test.dsk
    python3 probes/disk/disk_probe_dosboot_f368.py --dos-disk ... --slot 0xF368
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
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
MACHINE = "National_CF-3300"

# The 8 jump-table slots (3 bytes each: JP nnnn) in the disk work area.
SLOTS = [0xF368, 0xF36B, 0xF36E, 0xF371, 0xF374, 0xF377, 0xF37A, 0xF37D]


def _regs_tcl() -> str:
    return ('return "af=[format %04X [reg AF]] bc=[format %04X [reg BC]] '
            'de=[format %04X [reg DE]] hl=[format %04X [reg HL]] '
            'ix=[format %04X [reg IX]] iy=[format %04X [reg IY]] '
            'sp=[format %04X [reg SP]]"')


def run_profile(dsk: str, settle: float, timeout: float) -> dict:
    """Count calls to each table slot + snapshot the first call's input per slot."""
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    bp_lines = []
    for s in SLOTS:
        bp_lines.append(
            f'debug set_bp 0x{s:04X} {{}} {{\n'
            f'  incr ::c{s:04X}\n'
            f'  if {{$::c{s:04X} == 1}} {{ set ::in{s:04X} "[regs] ret=[format %04X [peek16 [reg SP]]]" }}\n'
            f'}}')
    tcl = f"""set throttle off
set renderer none
proc regs {{}} {{ {_regs_tcl()} }}
proc peek16 {{a}} {{ binary scan [debug read_block memory $a 2] su v; return $v }}
{chr(10).join(f'set ::c{s:04X} 0; set ::in{s:04X} ""' for s in SLOTS)}
{chr(10).join(bp_lines)}
proc final {{}} {{
  set f [open {{{out}}} w]
{chr(10).join(f'  puts $f "c{s:04X}=$::c{s:04X}"' for s in SLOTS)}
{chr(10).join(f'  puts $f "in{s:04X}=$::in{s:04X}"' for s in SLOTS)}
  close $f
  exit
}}
after time {settle:.1f} {{ final }}
"""
    open(tcl_path, "w").write(tcl)
    return _launch(tcl_path, out, dsk, timeout)


def run_slot(dsk: str, slot: int, settle: float, timeout: float) -> dict:
    """Deep-trap one slot: full input contract + output contract on return."""
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::retbp ""
proc regs {{}} {{ {_regs_tcl()} }}
proc peek16 {{a}} {{ binary scan [debug read_block memory $a 2] su v; return $v }}
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc on_ret {{}} {{
  set f [open {{{out}}} a]
  puts $f "exit=[regs]"
  puts $f "carry_out=[expr {{[reg F] & 1}}]"
  puts $f "hl_window_exit=[__hex [reg HL] 16]"
  close $f
  catch {{ debug remove_bp $::retbp }}
  exit
}}
proc on_entry {{}} {{
  if {{$::armed}} return
  set ::armed 1
  set ret [peek16 [reg SP]]
  set f [open {{{out}}} w]
  puts $f "entry=[regs]"
  puts $f "carry_in=[expr {{[reg F] & 1}}]"
  puts $f "ret_addr=[format %04X $ret]"
  puts $f "hl_window_entry=[__hex [reg HL] 16]"
  puts $f "de_window_entry=[__hex [reg DE] 16]"
  puts $f "ix_window_entry=[__hex [reg IX] 16]"
  close $f
  set ::retbp [debug set_bp $ret {{}} {{ on_ret }}]
}}
proc final {{}} {{
  if {{!$::armed}} {{
    set f [open {{{out}}} w]; puts $f "no_hit=1"; puts $f "pc=[format %04X [reg PC]]"; close $f
  }}
  exit
}}
debug set_bp 0x{slot:04X} {{}} {{ on_entry }}
after time {settle:.1f} {{ final }}
"""
    open(tcl_path, "w").write(tcl)
    return _launch(tcl_path, out, dsk, timeout)


def _launch(tcl_path: str, out: str, dsk: str, timeout: float) -> dict:
    cmd = [OMSX, "-machine", MACHINE, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {MACHINE}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={MACHINE})")
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    os.unlink(out)
    os.unlink(tcl_path)
    return d


def _copy_run(dos_disk, fn, *a):
    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(dos_disk, tmp)
    try:
        return fn(tmp, *a)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--slot", type=lambda s: int(s, 0), default=None,
                    help="deep-trap one slot (e.g. 0xF368) instead of profiling all")
    ap.add_argument("--settle", type=float, default=12.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")

    print(f"machine : {MACHINE}")

    if args.slot is None:
        d = _copy_run(args.dos_disk, run_profile, args.settle, args.timeout)
        print(f"table   : $F368-$F37C call profile (which slots MSXDOS.SYS uses)\n")
        print("  slot    calls   first-call input")
        print("  " + "-" * 70)
        for s in SLOTS:
            c = d.get(f"c{s:04X}", "0")
            inp = d.get(f"in{s:04X}", "")
            tag = " (SYSTEM/BDOS)" if s == 0xF37D else ""
            print(f"  ${s:04X}{tag:14s} {c:>5}   {inp}")
        print("\nNext: --slot $F368 (the first one the boot calls) for its in/out contract.")
        return 0

    d = _copy_run(args.dos_disk, run_slot, args.slot, args.settle, args.timeout)
    print(f"slot    : ${args.slot:04X} (deep in/out contract)\n")
    if d.get("no_hit"):
        print(f"FAIL: ${args.slot:04X} was never called during boot+settle "
              f"(PC at give-up ${d.get('pc')}).")
        return 1
    print(f"--- INPUT (at ${args.slot:04X} entry) ---")
    print(f"  {d.get('entry')}  carry={d.get('carry_in')}")
    print(f"  return addr (caller): ${d.get('ret_addr')}")
    print(f"  [HL] -> {d.get('hl_window_entry')}")
    print(f"  [DE] -> {d.get('de_window_entry')}")
    print(f"  [IX] -> {d.get('ix_window_entry')}")
    if "exit" not in d:
        print("\nPARTIAL: entry captured but no return within settle (raise --settle).")
        return 1
    print(f"\n--- OUTPUT (at return ${d.get('ret_addr')}) ---")
    print(f"  {d.get('exit')}  carry={d.get('carry_out')}")
    print(f"  [HL] -> {d.get('hl_window_exit')}")
    print("\nblack-box; registers/RAM only -- no $DFxx kernel code read.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
