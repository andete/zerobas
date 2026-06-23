#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 a3 §8.35: characterise how the STOCK CF-3300 disk ROM services DSKIO
calls with transfer addresses inside page 1 ($4000-$7FFF).

Background (§8.34/§8.35): after the DI-guard livelock fix the boot advances to
MSXDOS.SYS driving the public $4010 DSKIO vector.  The first call asks to read
logical sector $020D into HL=$5290 — a page-1 address.  Our fdc_read_data
writes `ld (hl),a` directly; since page 1 = our disk ROM during the call the
write is discarded → LOST DATA → retry loop.

The stock CF-3300 boots to A> with that same disk, so it handles page-1 targets
correctly.  This probe measures HOW by running on the STOCK machine and tracking:

  Q1  Does the stock modify $FFFF (secondary slot register, page-1 sub-slot)
      during the DSKIO call?  Which sub-slot does it switch page 1 to, and when?
  Q2  Does data appear at the page-1 target ($5290+) during DSKIO execution, or
      is it a bounce-buffer / delayed copy approach?
  Q3  What is the call chain into $4010 for page-1 targets (who calls it, from
      where, with what HL)?

Method: boot STOCK National_CF-3300 + test.dsk, allow it to reach A>.
  - Breakpoint at $4010: when entry HL is in $4000-$7FFF log the DSKIO args,
    $FFFF state, and caller return address.
  - $FFFF write watchpoint: log every write (value + PC) in the window between
    DSKIO entry and the return to the caller.
  - Write watchpoint on a page-1 range ($4000-$7FFF): detect any writes that
    land in page 1 (= TPA RAM when page 1 is sub-slot 0), within the window.
  - One-shot breakpoint at the DSKIO caller's return address to capture exit
    state and close the window.

DISK SAFETY: boots only a /tmp copy of the DOS disk; never modifies the original.

    python3 probes/disk/disk_probe_dosboot_page1.py \\
        --dos-disk ~/Documents/msx/msx/disks/msxdos103-cmd111.dsk
"""
from __future__ import annotations

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

# Maximum page-1 DSKIO events to log (to bound output on a long boot).
MAX_EVENTS = 8


def run(machine: str, dsk: str, settle: float, timeout: float) -> str:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")

    tcl = f"""
set throttle off
set renderer none
set ::log {{}}
set ::p1_count 0
set ::in_p1_call 0
set ::ret_bp ""

proc rb {{a}} {{ debug read memory $a }}
proc rw {{a}} {{
    binary scan [debug read_block memory $a 2] su v
    return [expr {{$v & 0xFFFF}}]
}}
proc ffff_actual {{}} {{
    # $FFFF reads inverted on MSX expanded-slot machines; cpl to get the
    # written (actual sub-slot) value.
    return [expr {{[rb 0xFFFF] ^ 0xFF}}]
}}
proc ffff_page1_subslot {{}} {{
    # bits [3:2] of the written $FFFF value = page-1 sub-slot
    return [expr {{([ffff_actual] >> 2) & 3}}]
}}

# --- $FFFF write watchpoint (always active; action gated on flag) -----------
debug set_watchpoint write_mem 0xFFFF {{}} {{
    if {{$::in_p1_call}} {{
        # "debug read memory 0xFFFF" after write returns the inverted value, so
        # XOR $FF to get what was actually written.
        set written [expr {{[rb 0xFFFF] ^ 0xFF}}]
        set subslot1 [expr {{($written >> 2) & 3}}]
        lappend ::log [format \
            "  FFFF_write %02X (written=%02X p1_subslot=%d) PC=%04X" \
            [rb 0xFFFF] $written $subslot1 [reg PC]]
    }}
}}

# --- page-1 write watchpoint (always active; action gated on flag) ----------
# Fires on any write to $4000-$7FFF.  Use a single representative address that
# the MSXDOS boot is known to target ($5290 from the §8.35 diagnosis) plus a
# small window covering the first few sectors.
debug set_watchpoint write_mem 0x5290 {{}} {{
    if {{$::in_p1_call}} {{
        lappend ::log [format \
            "  P1_WRITE at 5290 PC=%04X HL=%04X" [reg PC] [reg HL]]
    }}
}}

# --- main DSKIO breakpoint ($4010) ------------------------------------------
debug set_bp 0x4010 {{}} {{
    set hl [reg HL]
    set h  [expr {{$hl >> 8}}]
    # Only care about page-1 transfer addresses ($40xx-$7Fxx)
    if {{$h < 0x40 || $h >= 0x80}} {{ return }}
    if {{$::p1_count >= {MAX_EVENTS}}} {{ return }}
    incr ::p1_count

    set sp     [reg SP]
    set caller [rw $sp]          ;# return address = who called $4010
    set ffff_r [rb 0xFFFF]       ;# read value (inverted)
    set ffff_w [expr {{$ffff_r ^ 0xFF}}]  ;# actual written sub-slots
    set p1_ss  [expr {{($ffff_w >> 2) & 3}}]
    lappend ::log [format \
        "DSKIO#%d HL=%04X A8_PRI=%02X FFFF_read=%02X p1_subslot=%d caller=%04X AF=%04X BC=%04X DE=%04X" \
        $::p1_count $hl \
        [ffff_actual] $ffff_r $p1_ss $caller \
        [reg AF] [reg BC] [reg DE]]

    # Mark window open
    set ::in_p1_call 1

    # One-shot BP at caller to close the window and log exit state
    if {{$caller != 0 && $::ret_bp eq ""}} {{
        set ::ret_bp [debug set_bp $caller {{}} {{
            set hl   [reg HL]
            set ffff_w2 [expr {{[rb 0xFFFF] ^ 0xFF}}]
            set p1_ss2  [expr {{($ffff_w2 >> 2) & 3}}]
            lappend ::log [format \
                "  DSKIO_ret HL=%04X FFFF_written=%02X p1_subslot=%d AF=%04X" \
                $hl $ffff_w2 $p1_ss2 [reg AF]]
            set ::in_p1_call 0
            debug remove_bp $::ret_bp
            set ::ret_bp ""
        }}]
    }}
}}

proc cap {{}} {{
    set f [open {{{out}}} w]
    puts $f "=== §8.35 page-1 DSKIO characterisation (stock National_CF-3300) ==="
    puts $f "    ($::p1_count page-1 DSKIO hits captured)"
    puts $f ""
    foreach e $::log {{ puts $f $e }}
    puts $f ""
    puts $f "=== final memory state ==="
    puts $f [format "FFFF_read=%02X (written=%02X p1_subslot=%d)" \
        [rb 0xFFFF] [expr {{[rb 0xFFFF]^0xFF}}] [ffff_page1_subslot]]
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
    text = open(out).read()
    os.unlink(out)
    os.unlink(tcl_path)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True,
                    help="DOS disk image (copied to /tmp; original untouched)")
    ap.add_argument("--settle", type=float, default=20.0,
                    help="settle time in seconds (allow boot to reach A>)")
    ap.add_argument("--timeout", type=float, default=90.0)
    args = ap.parse_args()

    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")

    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        text = run(STOCK_MACHINE, tmp, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(text)

    # Quick summary
    ffff_writes = [l for l in text.splitlines() if "FFFF_write" in l]
    p1_writes = [l for l in text.splitlines() if "P1_WRITE" in l]
    print("---- §8.35 summary ----")
    print(f"$FFFF writes during page-1 DSKIO calls: {len(ffff_writes)}")
    print(f"writes to $5290 (page-1 target) during calls: {len(p1_writes)}")
    if ffff_writes:
        print("→ STOCK remaps $FFFF (changes page-1 sub-slot) during the call")
    else:
        print("→ STOCK does NOT write $FFFF during the call (no page remapping observed)")
    if p1_writes:
        print("→ data lands at $5290 DURING the DSKIO call (direct write, no post-call copy)")
    else:
        print("→ no writes to $5290 during the call (bounce buffer or post-call copy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
