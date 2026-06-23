#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box oracle: characterise disk-ROM entry $4030 (the MSX-DOS-1 boot
gap) on the genuine National CF-3300.

CONTEXT (zerobas Tier-2, disk/docs/provider-oracle-scope.md §8.11/§8.12). zerobas-disk
already gets a real MSX-DOS-1 disk to LOAD and EXECUTE MSXDOS.SYS byte-perfect off
our own `bdos_entry` (the $F37D-JP fix + BDOS $27). The last gap to `A>` is a single
disk-ROM entry past the six standard ones ($4010 DSKIO .. $401F MTOFF): MSXDOS.SYS's
resident init `CALL`s **$4030**, which our ROM does not implement. Its contract is in
no allowed *published* source (RE compilations name it "GETWRK"; we do NOT rely on that
-- we name it by address and describe only what we measure) -- so we characterise it
the way this project characterises every undocumented disk-ROM entry (GETDPB was nailed
byte-identical this way): as a **black-box oracle**.

WHAT THIS PROBE DOES. Boot the genuine National CF-3300 (its own BASIC + disk ROMs,
which you supply) from a real MSX-DOS 1 system disk, and trap the *working* boot's
own call to $4030:

  * a breakpoint at $4030 (qualified to HL in high RAM, where the disk work area
    lives -- the §8.11 observation was HL=$F1C9) fires on the real $4030 call;
  * on entry we snapshot the FULL input contract: every register (AF/BC/DE/HL/IX/IY/SP),
    the return address pulled off the stack, and a window of the disk work-area RAM
    (both a fixed $F100.. window and the 32 bytes HL points at);
  * we then arm a one-shot breakpoint at that return address and, on return, snapshot
    the output registers and the same RAM windows.

The Python side diffs entry-vs-exit registers and RAM to report, in clean-room terms,
*what $4030 does*: input register convention in, output register + work-area-RAM
effects out. That observed contract -- never the ROM's code -- is what we reimplement
in our own zerobas-disk $4030.

CLEAN-ROOM DISCIPLINE. Strictly black-box. We set CPU breakpoints and read **RAM**
($F1xx disk work area) and **registers** only. We never read, dump, or disassemble the
$4000-$7FFF disk-ROM code, nor MSXDOS.SYS. We observe behaviour (inputs in, outputs +
RAM deltas out); we do not lift code. (Locating the call during diagnosis is black-box
fault-finding; implementing $4030 from the observed input/output contract is the same
oracle method used for GETDPB/DSKIO/PHYDIO.)

DISK SAFETY. openMSX can write back to a mounted image; this probe boots only a
**/tmp copy** of the DOS disk, never the permanent/committed one.

Prerequisites:
  * openMSX with the genuine National CF-3300 ROMs installed (you provide ROMs you
    may use): cf-3300_basic-bios1.rom + cf-3300_disk.rom in systemroms.
  * a real MSX-DOS 1 system disk image (pass with --dos-disk).

    python3 probes/disk/disk_probe_dosboot_4030.py \\
        --dos-disk ~/Documents/msx/msx/disks/test.dsk
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

GETWRK = 0x4030     # the undocumented disk-ROM entry MSXDOS.SYS init calls (§8.11)
WORK_BASE = 0xF100  # disk work-area RAM window base (page 3 = always RAM)
WORK_LEN = 0x300    # 768 bytes -- covers the $F1xx/$F2xx/$F3xx disk work area


def run(dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::n 0
set ::armed 0
set ::retbp ""
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc peek16 {{a}} {{ binary scan [debug read_block memory $a 2] su v; return $v }}
proc regs {{}} {{
  return "af=[format %04X [reg AF]] bc=[format %04X [reg BC]] de=[format %04X [reg DE]] hl=[format %04X [reg HL]] ix=[format %04X [reg IX]] iy=[format %04X [reg IY]] sp=[format %04X [reg SP]]"
}}
proc on_ret {{}} {{
  set f [open {{{out}}} a]
  puts $f "exit=[regs]"
  puts $f "work_exit=[__hex 0x{WORK_BASE:04X} {WORK_LEN}]"
  puts $f "hl_window_exit=[__hex [reg HL] 32]"
  puts $f "ix_window_exit=[__hex [reg IX] 32]"
  close $f
  catch {{ debug remove_bp $::retbp }}
  exit
}}
proc on_entry {{}} {{
  incr ::n
  if {{$::armed}} return
  set ::armed 1
  set sp [reg SP]
  set ret [peek16 $sp]
  set f [open {{{out}}} w]
  puts $f "hit_index=$::n"
  puts $f "entry=[regs]"
  puts $f "ret_addr=[format %04X $ret]"
  puts $f "work_entry=[__hex 0x{WORK_BASE:04X} {WORK_LEN}]"
  puts $f "hl_window_entry=[__hex [reg HL] 32]"
  puts $f "ix_window_entry=[__hex [reg IX] 32]"
  close $f
  set ::retbp [debug set_bp $ret {{}} {{ on_ret }}]
}}
proc final {{}} {{
  if {{!$::armed}} {{
    set f [open {{{out}}} w]
    puts $f "no_qualifying_hit=1"
    puts $f "n4030_total=$::n"
    puts $f "pc=[format %04X [reg PC]]"
    close $f
  }}
  exit
}}
debug set_bp 0x{GETWRK:04X} {{[expr {{[reg HL] >= 0xF000}}]}} {{ on_entry }}
after time {settle:.1f} {{ final }}
"""
    open(tcl_path, "w").write(tcl)
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


def _parse_regs(s: str) -> dict:
    """'af=003F bc=0001 ...' -> {'af': 0x003F, ...}."""
    r = {}
    for tok in s.split():
        k, _, v = tok.partition("=")
        if v:
            r[k] = int(v, 16)
    return r


def _reg_diff(entry: dict, exit_: dict) -> list:
    out = []
    for k in ("af", "bc", "de", "hl", "ix", "iy", "sp"):
        if k in entry and k in exit_ and entry[k] != exit_[k]:
            out.append(f"  {k.upper()}: {entry[k]:04X} -> {exit_[k]:04X}")
    return out


def _ram_diff(entry_hex: str, exit_hex: str, base: int) -> list:
    if not entry_hex or not exit_hex or len(entry_hex) != len(exit_hex):
        return []
    a = bytes.fromhex(entry_hex)
    b = bytes.fromhex(exit_hex)
    runs = []
    i = 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and a[j] != b[j]:
                j += 1
            runs.append((base + i, a[i:j], b[i:j]))
            i = j
        else:
            i += 1
    return runs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="real MSX-DOS 1 system disk image")
    ap.add_argument("--settle", type=float, default=12.0, help="emulated seconds before give-up")
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()

    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        d = run(tmp, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(f"machine : {MACHINE}")
    print(f"entry   : $4030 (GETWRK candidate), qualified HL>=$F000\n")

    if d.get("no_qualifying_hit"):
        print("FAIL: $4030 was never reached with HL>=$F000 during boot+settle.")
        print(f"  total $4030 hits (any HL): {d.get('n4030_total')}")
        print(f"  PC at give-up: 0x{d.get('pc')}")
        print("  -> does the disk boot to MSX-DOS? raise --settle, or widen the HL filter.")
        return 1

    entry = _parse_regs(d.get("entry", ""))
    print(f"--- INPUT contract (at $4030 entry, hit #{d.get('hit_index')}) ---")
    print(f"  {d.get('entry')}")
    print(f"  return address (caller, off stack): ${d.get('ret_addr')}")
    print(f"  [HL=${entry.get('hl', 0):04X}] -> {d.get('hl_window_entry')}")
    print(f"  [IX=${entry.get('ix', 0):04X}] -> {d.get('ix_window_entry')}")

    if "exit" not in d:
        print("\nPARTIAL: entry captured, but $4030 did not return within settle "
              "(raise --settle). Input contract above still stands.")
        return 1

    exit_ = _parse_regs(d["exit"])
    print(f"\n--- OUTPUT contract (at return ${d.get('ret_addr')}) ---")
    print(f"  {d.get('exit')}")
    rd = _reg_diff(entry, exit_)
    print("  register deltas:")
    print("\n".join(rd) if rd else "    (none)")
    print(f"  [HL=${exit_.get('hl', 0):04X}] -> {d.get('hl_window_exit')}")
    print(f"  [IX=${exit_.get('ix', 0):04X}] -> {d.get('ix_window_exit')}")

    runs = _ram_diff(d.get("work_entry", ""), d.get("work_exit", ""), WORK_BASE)
    print(f"\n--- work-area RAM deltas (${WORK_BASE:04X}..${WORK_BASE+WORK_LEN-1:04X}) ---")
    if runs:
        for addr, a, b in runs:
            print(f"  ${addr:04X}: {a.hex()} -> {b.hex()}")
    else:
        print("  (no writes in this window -- GETWRK likely pure/return-only here)")

    print("\nOK: $4030 input/output contract captured (black-box; RAM+regs only). "
          "Next: reimplement this contract in zerobas-disk and re-trap the boot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
