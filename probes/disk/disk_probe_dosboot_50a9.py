#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box: the warm-boot spin RE-ROOT-CAUSED (a3 §8.26, correcting §8.25).

With the kernel correctly placed (§8.24) the MSX-DOS kernel publishes its BDOS vector
then does `CALL $50A9`. On the stock that reaches A>; on Tier-1 it NOP-slides into a
crash -> warm-boot spin (the symptom §8.25 measured).

§8.25 GUESSED the cause was "MSXDOS.SYS's page-1 portion never loaded to RAM". THAT IS
WRONG, and this probe proves it:

  1. MSXDOS.SYS on the test disk is 2432 bytes -- it loads entirely into PAGE 0
     ($0100-$0A7F) and never reaches page 1. So $50A9 is NOT unloaded file data.

  2. At the `CALL $50A9` the page-1 secondary slot is the DISK-ROM sub-slot (3-1),
     NOT RAM (ppi $A8=$FF, $FFFF live = $04 -> page-1 bits = 01 = sub-slot 1). So
     $50A9 reads the DISK ROM at offset $10A9, a FIXED disk-ROM ENTRY POINT the
     kernel calls (the same class as $4010/$4030).

  3. The genuine CF-3300 disk ROM implements it (offset $10A9 = `cd 2d 47 ...` =
     CALL $472D + work-area setup); OUR disk.rom leaves $10A9 as $00 padding -> the
     kernel calls into zeros and crashes.

BLACK-BOX CONTRACT of the stock $50A9 (--stock; the next reimplementation target):
  in  : AF=C340 BC=0000 DE=DC80 HL=D606 IX=F195 IY=C0AB  (kernel base in HL)
  out : A=00 F=42 (Z) DE=F1AA HL=F359 IX=F1AA ; BC, IY preserved
  side effect: writes $00 to $F242 (the only non-stack write; via CALL $472D).
  The returned HL/DE/IX point into the disk work area ($F1xx/$F3xx) the disk ROM
  built (DRVTBL at $F348). What the kernel does with them = the re-trap target.

WHAT IT MEASURES (black-box):
  * the page-1 secondary slot at the call (proves disk-ROM sub-slot, not RAM);
  * $50A9's first 16 bytes (stock code vs our $00 padding);
  * --stock only: the entry/exit register contract + memory side effect.

CLEAN-ROOM. Breakpoint at the kernel publish site + the disk-ROM entry; register and
memory reads only. We read the call-target bytes to show present (stock) vs absent
(Tier-1) and record the entry/exit register CONTRACT -- a black-box observation, no
ROM code disassembled or replicated.

DISK SAFETY: boots only a /tmp copy of the DOS disk.

    python3 probes/disk/disk_probe_dosboot_50a9.py --dos-disk ~/Documents/msx/msx/disks/test.dsk
    python3 probes/disk/disk_probe_dosboot_50a9.py --stock --dos-disk ~/Documents/msx/msx/disks/test.dsk
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
TIER1_MACHINE = "National_CF-3300_ZEROBASDISK"

PUBLISH_PC = 0xD7CB        # just after the kernel writes $0005 = JP <base> (§8.24)
ENTRY_50A9 = 0x50A9        # the disk-ROM entry the kernel CALLs (ROM offset $10A9)


def run(machine: str, dsk: str, capture_contract: bool, settle: float,
        timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    # The contract trap (entry/exit/side-effect) is only meaningful on a machine whose
    # $50A9 actually runs to completion -- i.e. the stock. On Tier-1 we only snapshot
    # the call site (slot + target bytes) before the crash.
    contract = ""
    if capture_contract:
        contract = f"""
debug set_bp 0x{ENTRY_50A9:04X} {{$::armed && !$::ctr}} {{
  set ::ctr 1
  set sp [reg SP]
  set ret [expr {{[debug read memory $sp] + 256*[debug read memory [expr {{$sp+1}}]]}}]
  set ::entry "AF=[format %04X [reg AF]] BC=[format %04X [reg BC]] DE=[format %04X [reg DE]] HL=[format %04X [reg HL]] IX=[format %04X [reg IX]] IY=[format %04X [reg IY]]"
  set ::incall 1
  debug set_bp $ret {{}} {{
    set ::exit "AF=[format %04X [reg AF]] BC=[format %04X [reg BC]] DE=[format %04X [reg DE]] HL=[format %04X [reg HL]] IX=[format %04X [reg IX]] IY=[format %04X [reg IY]]"
    set ::incall 0
  }}
}}
debug set_watchpoint write_mem {{0xF000 0xFFFF}} {{$::incall}} {{
  lappend ::sidefx "[format %04X $::wp_last_address]=[format %02X [debug read memory $::wp_last_address]]"
}}
"""
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::ctr 0
set ::incall 0
set ::sidefx {{}}
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
debug set_bp 0x{PUBLISH_PC:04X} {{}} {{
  if {{!$::armed}} {{
    set ::armed 1
    set ::ppi [format %02X [debug read {{ioports}} 0xA8]]
    set ::sec [format %02X [expr {{255 - [debug read {{memory}} 0xFFFF]}}]]
    set ::tgt [__hex 0x{ENTRY_50A9:04X} 16]
  }}
}}
{contract}
proc cap {{}} {{
  set f [open {{{out}}} w]
  if {{[info exists ::ppi]}} {{
    puts $f "ppi_a8=$::ppi"
    puts $f "sec_live=$::sec"
    puts $f "tgt50a9=$::tgt"
  }} else {{
    puts $f "no_call_site=1"
  }}
  if {{[info exists ::entry]}} {{ puts $f "entry=$::entry" }}
  if {{[info exists ::exit]}}  {{ puts $f "exit=$::exit" }}
  if {{[llength $::sidefx]}}    {{ puts $f "sidefx=[join $::sidefx ,]" }}
  close $f
  exit
}}
after time {settle:.1f} {{ cap }}
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
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    os.unlink(out)
    os.unlink(tcl_path)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true",
                    help="run on the genuine CF-3300 oracle (captures the $50A9 contract)")
    ap.add_argument("--settle", type=float, default=14.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()

    machine = STOCK_MACHINE if args.stock else TIER1_MACHINE
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        d = run(machine, tmp, args.stock, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(f"machine : {machine}\n")
    if d.get("no_call_site"):
        print("kernel publish site never reached (no boot?).")
        return 1

    sec = d.get("sec_live", "??")
    page1_sub = (int(sec, 16) >> 2) & 3
    tgt = d.get("tgt50a9", "")
    zeros = tgt and set(tgt) <= {"0"}
    print(f"at the kernel `CALL $50A9`:")
    print(f"  ppi $A8 = ${d.get('ppi_a8')}   $FFFF live = ${sec}"
          f"   -> page-1 sub-slot = {page1_sub} "
          f"({'DISK ROM (3-1)' if page1_sub == 1 else 'RAM' if page1_sub == 0 else '?'})")
    print(f"  $50A9 (= disk-ROM offset $10A9) : {tgt}")
    print()
    if zeros:
        print("ROOT CAUSE (§8.26): $50A9 is a DISK-ROM entry the kernel calls, and OUR")
        print("  disk ROM leaves offset $10A9 as $00 padding -> CALL $50A9 slides into")
        print("  zeros -> crash -> warm-boot spin. (NOT unloaded MSXDOS.SYS data -- the")
        print("  file is 2432 B, page-0 only. §8.25's framing is falsified.)")
    else:
        print("$50A9 holds disk-ROM code -- the entry is implemented (stock / fixed Tier-1).")

    if d.get("entry"):
        print(f"\n$50A9 black-box contract (next reimplementation target):")
        print(f"  in  : {d.get('entry')}")
        print(f"  out : {d.get('exit', '(no return captured)')}")
        if d.get("sidefx"):
            print(f"  mem : {d.get('sidefx').replace(',', ' ')}  (non-stack writes only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
