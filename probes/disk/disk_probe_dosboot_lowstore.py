#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box oracle + differential: how does MSXDOS.SYS bring up its page-0
environment after $4030, and where does the zerobas-disk boot diverge? (the
§8.16 derail-diagnosis tool.)

CONTEXT (zerobas Tier-2, disk/docs/provider-oracle-scope.md §8.13-8.16). zerobas-disk
implements $4030 (returns a work-area pointer) and MSXDOS.SYS consumes it, but the
Tier-1 boot derailed at $0038. §8.15 GUESSED the lever was the $4030 work-area
LAYOUT (lay our resident vectors at an offset inside it). This probe REFUTED that
and found the real lever:

  * On the genuine CF-3300, MSXDOS.SYS makes ZERO writes to $0000-$003F after
    $4030, and its $0038 interrupt vector points at a fixed page-0 handler
    ($0C3C), NOT into the $4030 work area -- so the work-area-offset theory was
    wrong.
  * The Tier-1 vs stock DIFFERENTIAL of page-0 low storage is decisive: the stock
    has a full JP-vector set (page 0 = RAM); the derailing Tier-1 boot had page 0
    = all $FF (an unmapped slot) and wedged executing $FF = RST 38h.
  * The lever is RAMAD0-3 ($F341-4): MSXDOS.SYS reads it (84x on the stock, after
    $4030) to re-page RAM into page 0. The disk ROM's INIT owns RAMAD (the base
    BIOS sets only EXPTBL); ours did not set it -> empty slot -> $FF -> wedge.
    set_ramad now fills it, and page-0 RAM maps (next gap: the interrupt storm).

WHAT IT MEASURES (black-box; --tier1 captures the derail, default = stock oracle):
  * $4030 returned work-area base (captured on return, not entry HL);
  * writes into $0000-$003F after $4030 + the JP vectors present at settle;
  * RAMAD0-3 at $4030-return (clean, disk-ROM-set) and read-count after $4030;
  * settle PC / [PC] / SP / stack (the derail signature) + EXPTBL / DRVTBL.

CLEAN-ROOM. Strictly black-box: a CPU breakpoint at $4030, RAM read/write
watchpoints, register + RAM reads on the running reference boot. We observe which
cells MSXDOS.SYS reads/writes and to what targets (the system-RAM contract); we
never read, dump, or disassemble the disk-ROM or MSXDOS.SYS code.

DISK SAFETY: boots only a /tmp copy of the DOS disk, never the permanent one.

Prerequisites:
  * openMSX with the genuine National CF-3300 ROMs installed (you provide them):
    cf-3300_basic-bios1.rom + cf-3300_disk.rom in systemroms; for --tier1 also the
    National_CF-3300_ZEROBASDISK machine (tools/install-openmsx-machine.py).
  * a real MSX-DOS 1 system disk image (pass with --dos-disk).

    python3 probes/disk/disk_probe_dosboot_lowstore.py \\
        --dos-disk ~/Documents/msx/msx/disks/test.dsk          # stock oracle
    python3 probes/disk/disk_probe_dosboot_lowstore.py --tier1 \\
        --dos-disk ~/Documents/msx/msx/disks/test.dsk          # zerobas-disk derail
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
STOCK_MACHINE = "National_CF-3300"             # genuine disk ROM (oracle baseline)
TIER1_MACHINE = "National_CF-3300_ZEROBASDISK"  # real CF-3300 BIOS + zerobas-disk

GETWRK = 0x4030     # disk-ROM entry MSXDOS.SYS init calls for the work-area base
LOW_BASE = 0x0000   # page-0 low storage -- where MSXDOS.SYS lays its JP/RST vectors
LOW_LEN = 0x40      # $0000-$003F covers warm-boot/$0005 BDOS/$0038 interrupt vectors


def run(machine: str, dsk: str, settle: float, timeout: float, hl_min: int) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::armed 0
set ::base ""
set ::entryhl ""
set ::writes {{}}
set ::ramadrd 0
set ::ramadpc {{}}
set ::ramad_atret ""
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc peek16 {{a}} {{ binary scan [debug read_block memory $a 2] su v; return $v }}
proc on_ret {{}} {{
  # capture the RETURNED work-area base (HL on $4030's return), not the entry HL.
  set ::base [format %04X [reg HL]]
  # RAMAD0-3 at this instant = the disk-ROM-INIT-set values, BEFORE MSXDOS runs
  # and (in the derail case) corrupts RAM. This is the clean layout to replicate.
  set ::ramad_atret [__hex 0xF341 4]
  catch {{ debug remove_bp $::retbp }}
}}
proc on_entry {{}} {{
  if {{$::armed}} return
  set ::armed 1
  set ::entryhl [format %04X [reg HL]]
  set ret [peek16 [reg SP]]
  set ::retbp [debug set_bp $ret {{}} {{ on_ret }}]
  # from now on, log every write into page-0 low storage -- the vectors
  # MSXDOS.SYS installs once it has the work-area base.
  debug set_watchpoint write_mem {{0x{LOW_BASE:04X} 0x{LOW_BASE + LOW_LEN - 1:04X}}} {{}} {{
    lappend ::writes "[format %04X $::address]:[format %02X [reg A]]@[format %04X [reg PC]]"
  }}
  # and log every READ of RAMAD0-3 ($F341-4) -- does MSXDOS.SYS's post-$4030
  # init consult the per-page RAM-slot table to re-page page 0? (the lever test)
  debug set_watchpoint read_mem {{0xF341 0xF344}} {{}} {{
    incr ::ramadrd
    if {{[llength $::ramadpc] < 8}} {{
      lappend ::ramadpc "[format %04X $::address]@[format %04X [reg PC]]"
    }}
  }}
}}
proc final {{}} {{
  set f [open {{{out}}} w]
  if {{!$::armed}} {{
    puts $f "no_qualifying_hit=1"
    puts $f "pc=[format %04X [reg PC]]"
  }} else {{
    puts $f "entryhl=$::entryhl"
    puts $f "base=$::base"
    puts $f "low=[__hex 0x{LOW_BASE:04X} {LOW_LEN}]"
    puts $f "writes=[join $::writes ,]"
    puts $f "pc=[format %04X [reg PC]]"
    puts $f "sp=[format %04X [reg SP]]"
    puts $f "stack=[__hex [reg SP] 48]"
    puts $f "pcmem=[__hex [reg PC] 8]"
    puts $f "ramad=[__hex 0xF341 4]"
    puts $f "exptbl=[__hex 0xFCC1 4]"
    puts $f "drvtbl=[__hex 0xF348 16]"
    puts $f "ramad_atret=$::ramad_atret"
    puts $f "ramadrd=$::ramadrd"
    puts $f "ramadpc=[join $::ramadpc ,]"
  }}
  close $f
  exit
}}
debug set_bp 0x{GETWRK:04X} {{[expr {{[reg HL] >= 0x{hl_min:04X}}}]}} {{ on_entry }}
after time {settle:.1f} {{ final }}
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


# The MSX low-storage inter-slot / interrupt vectors sit at fixed RST-aligned
# slots. $0000 is `DI; JP nnnn` (so the JP target is at $0001); the rest are
# `JP nnnn` at the RST boundaries. $0038 is the maskable-interrupt entry.
VEC_SLOTS = {
    0x00: "reset/DI;JP", 0x08: "RST08", 0x0C: "RST08+", 0x10: "RST10",
    0x14: "RST10+", 0x18: "RST18", 0x1C: "RST18+", 0x20: "RST20",
    0x24: "RST20+", 0x28: "RST28", 0x30: "RST30/CALLF", 0x38: "interrupt",
}


def _decode_vectors(low_hex: str) -> list:
    """Decode the `JP nnnn` at each known low-storage slot. Slot $0000 begins
    with DI ($F3) so its JP operand is at $0001; all others are JP at the slot.
    Returns (slot, target) for slots that actually hold a JP ($C3)."""
    b = bytes.fromhex(low_hex)
    found = []
    for slot in sorted(VEC_SLOTS):
        jp = slot + 1 if slot == 0x00 else slot
        if jp + 2 < len(b) and b[jp] == 0xC3:
            tgt = b[jp + 1] | (b[jp + 2] << 8)
            found.append((slot, tgt))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True, help="real MSX-DOS 1 system disk image")
    ap.add_argument("--settle", type=float, default=14.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--tier1", action="store_true",
                    help="run on the zerobas-disk Tier-1 machine (captures the derail) "
                         "instead of the genuine CF-3300 oracle baseline")
    ap.add_argument("--machine", default=None, help="override the openMSX machine name")
    ap.add_argument("--hl-min", type=lambda s: int(s, 0), default=None,
                    help="only trap $4030 when HL>=this (default $F000 stock / $0000 tier1)")
    args = ap.parse_args()

    machine = args.machine or (TIER1_MACHINE if args.tier1 else STOCK_MACHINE)
    hl_min = args.hl_min if args.hl_min is not None else (0x0000 if args.tier1 else 0xF000)

    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        d = run(machine, tmp, args.settle, args.timeout, hl_min)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(f"machine : {machine}")
    print(f"entry   : $4030 -> work-area base; watch page-0 vectors MSXDOS.SYS installs\n")

    if d.get("no_qualifying_hit"):
        print("FAIL: $4030 never reached with HL>=$F000 during boot+settle.")
        print(f"  PC at give-up: 0x{d.get('pc')}  (does the disk boot to MSX-DOS?)")
        return 1

    entryhl = int(d.get("entryhl", "0") or "0", 16)
    base = int(d.get("base", "0") or "0", 16)
    print(f"$4030 input HL (work-area-1?)  : ${entryhl:04X}")
    print(f"$4030 RETURNED work-area base  : ${base:04X}\n")

    # --- the writes MSXDOS.SYS made into low storage, in order ---
    writes = [w for w in d.get("writes", "").split(",") if w]
    print(f"--- writes into $0000-$003F after $4030 returned ({len(writes)}) ---")
    if writes:
        for w in writes[:48]:
            print(f"  {w}")
        if len(writes) > 48:
            print(f"  ... (+{len(writes) - 48} more)")
    else:
        print("  (NONE -- MSXDOS.SYS does NOT rewrite low storage post-$4030; the")
        print("   page-0 vectors are installed earlier, independent of the work area.)")

    # --- decode the JP vectors present at settle ---
    print(f"\n--- low storage $0000-$003F at settle ---")
    print(f"  {d.get('low')}")
    vecs = _decode_vectors(d.get("low", ""))
    print(f"\n--- decoded low-storage JP vectors ---")
    for slot, tgt in vecs:
        in_wa = base and base <= tgt < base + 0x300
        note = "  <- inside $4030 work area" if in_wa else ""
        print(f"  $00{slot:02X} {VEC_SLOTS[slot]:12s} JP ${tgt:04X}{note}")

    # --- where did it settle, and what is the stack? (derail diagnosis) ---
    pc = d.get("pc", "")
    print(f"\n--- settle state ---")
    print(f"  PC=${pc}  [PC]->{d.get('pcmem', '')}   SP=${d.get('sp', '')}")
    print(f"  stack@SP : {d.get('stack', '')}")

    # --- BIOS work-area cells MSXDOS.SYS uses to re-page page-0 RAM ---
    print(f"\n--- BIOS work area (slot tables) ---")
    print(f"  RAMAD0-3 @$4030-ret : {d.get('ramad_atret', '')}   (clean disk-ROM-set value)")
    print(f"  RAMAD0-3 $F341 : {d.get('ramad', '')}   (per-page RAM slot; at settle)")
    print(f"  EXPTBL   $FCC1 : {d.get('exptbl', '')}")
    print(f"  $F348 (DRVTBL) : {d.get('drvtbl', '')}")
    ramadrd = int(d.get("ramadrd", "0") or "0")
    print(f"  RAMAD reads after $4030 : {ramadrd}"
          + (f"   PCs: {d.get('ramadpc', '')}" if ramadrd else "  (MSXDOS does NOT read RAMAD here)"))

    int_vec = next((tgt for slot, tgt in vecs if slot == 0x38), None)
    print()
    if int_vec is not None:
        in_wa = base and base <= int_vec < base + 0x300
        print(f"KEY: $0038 interrupt -> ${int_vec:04X}.")
        if in_wa:
            print(f"  (inside the $4030 work area: the resident int handler lives there.)")
        else:
            print(f"  NOT in the work area -- it is a fixed page-0/BIOS-range handler.")
            print(f"  So the work-area layout is NOT the $0038 lever; the derail must be")
            print(f"  differential (compare this low storage + stack vs the Tier-1 boot).")
    else:
        print("note: no JP at $0038 -- inspect the dump above.")
    print("\n(black-box; RAM writes + register/RAM reads only -- no ROM/MSXDOS code read.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
