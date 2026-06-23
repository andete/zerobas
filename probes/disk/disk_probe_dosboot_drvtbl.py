#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 black-box oracle: characterise the $F348 DRVTBL (disk-driver table)
that MSXDOS.SYS reads 208x to dispatch into the disk ROM's driver (the §8.21 gap).

CONTEXT (zerobas Tier-2, disk/docs/provider-oracle-scope.md §8.21). After the
$F368 work-area jump table was built (§8.18) MSXDOS.SYS drives our disk driver and
reads the filesystem, but then derails (a corrupt jump, the "$8004 slide"). The
root cause traced to the $F348 DRVTBL: on the stock CF-3300 it is
  87 93 df 0e dd ... 95 ... 95 ...   (slot id $87 | HIMEM $DF93 | $4030 work $DD0E
                                      | driver-routine pointers into the $95xx
                                      disk-ROM kernel)
while OURS is unbuilt/garbage -> MSXDOS dispatches through garbage and derails.

This probe characterises the table the project way -- BLACK-BOX ORACLE -- in two
phases, so we learn the FIELD LAYOUT and the DRIVER CALLING CONVENTION before we
build our own $F348 in disk.asm (pointing its driver entries at OUR $4010-region
driver, never the stock $95xx kernel bytes):

  PHASE 1 (always): boot the stock, settle, dump $F348..+TABLE_LEN. Print the raw
    bytes and decode: slot id, HIMEM, $4030 work-area ptr, and every word whose
    high byte is $95 (candidate driver-routine pointers).

  PHASE 2 (default, or skip with --no-trap): for each DISTINCT $95xx pointer found,
    boot again and trap that address. Count calls and snapshot the FIRST call's
    input registers + caller return address. Tells us WHICH driver routines MSXDOS
    invokes and their input convention -- which we match to one of our known disk
    BIOS entries (DSKIO/DSKCHG/GETDPB/CHOICE/DSKFMT at $4010-$401F).

  --entry 0x95EF (deep): trap ONE driver pointer, snapshot the full input contract
    (all regs + carry + return addr + [HL]/[DE]/[IX] windows), arm a one-shot bp at
    the return, snapshot the output (regs + carry + [HL] window). The in/out
    contract we reimplement -- the DSKIO/GETDPB/$4030 discipline.

CLEAN-ROOM. Strictly black-box: CPU breakpoints + register/RAM reads on the running
reference boot. We trap the $95xx ENTRY ADDRESSES and observe register/flag in/out;
we never read, dump, or disassemble the $95xx kernel code, the DRVTBL-pointed
routines, or MSXDOS.SYS. (Reimplementing from an observed in/out contract is the
GETDPB/$4030 discipline; the $95xx/$DFxx kernel bytes are never lifted.)

DISK SAFETY: boots only a /tmp copy of the DOS disk, never the permanent one.

Prerequisites:
  * openMSX with the genuine National CF-3300 ROMs installed (you provide them):
    cf-3300_basic-bios1.rom + cf-3300_disk.rom in systemroms.
  * a real MSX-DOS 1 system disk image (pass with --dos-disk).

    python3 probes/disk/disk_probe_dosboot_drvtbl.py --dos-disk ~/Documents/msx/msx/disks/test.dsk
    python3 probes/disk/disk_probe_dosboot_drvtbl.py --dos-disk ... --entry 0x95EF
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

DRVTBL = 0xF348        # MSX-DOS 1 disk-driver table (per-drive), read by MSXDOS.SYS
TABLE_LEN = 16         # dump this many bytes for layout decode


def _regs_tcl() -> str:
    return ('return "af=[format %04X [reg AF]] bc=[format %04X [reg BC]] '
            'de=[format %04X [reg DE]] hl=[format %04X [reg HL]] '
            'ix=[format %04X [reg IX]] iy=[format %04X [reg IY]] '
            'sp=[format %04X [reg SP]]"')


def run_dump(dsk: str, settle: float, timeout: float) -> dict:
    """Boot, settle, dump the $F348 DRVTBL bytes (Phase 1)."""
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc final {{}} {{
  set f [open {{{out}}} w]
  puts $f "drvtbl=[__hex 0x{DRVTBL:04X} {TABLE_LEN}]"
  close $f
  exit
}}
after time {settle:.1f} {{ final }}
"""
    open(tcl_path, "w").write(tcl)
    return _launch(tcl_path, out, dsk, timeout)


def run_watch(dsk: str, settle: float, timeout: float) -> dict:
    """Read-watchpoint over $F348..+TABLE_LEN: per-offset read count + first
    reader PC. Reveals HOW MSXDOS consumes the table (which bytes matter)."""
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    wp_lines = []
    for off in range(TABLE_LEN):
        a = DRVTBL + off
        wp_lines.append(
            f'debug set_watchpoint read_mem 0x{a:04X} {{}} {{\n'
            f'  incr ::r{off}\n'
            f'  if {{$::r{off} == 1}} {{ set ::pc{off} [format %04X [reg PC]] }}\n'
            f'}}')
    tcl = f"""set throttle off
set renderer none
{chr(10).join(f'set ::r{off} 0; set ::pc{off} ""' for off in range(TABLE_LEN))}
{chr(10).join(wp_lines)}
proc final {{}} {{
  set f [open {{{out}}} w]
{chr(10).join(f'  puts $f "r{off}=$::r{off} $::pc{off}"' for off in range(TABLE_LEN))}
  close $f
  exit
}}
after time {settle:.1f} {{ final }}
"""
    open(tcl_path, "w").write(tcl)
    return _launch(tcl_path, out, dsk, timeout)


def run_writers(dsk: str, settle: float, timeout: float) -> dict:
    """Write-watchpoint over $F348..+TABLE_LEN: capture EVERY write (PC + value +
    offset), in order. Reveals WHO builds the DRVTBL (disk ROM INIT in page 1, or
    MSXDOS in TPA/high RAM) -- decides what we build in disk.asm."""
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::log {{}}
debug set_watchpoint write_mem {{0x{DRVTBL:04X} 0x{DRVTBL + TABLE_LEN - 1:04X}}} {{}} {{
  lappend ::log "[format %04X $::wp_last_address] pc=[format %04X [reg PC]] val=[format %02X $::wp_last_value]"
}}
proc final {{}} {{
  set f [open {{{out}}} w]
  puts $f "nwrites=[llength $::log]"
  set i 0
  foreach e $::log {{ puts $f "w$i=$e"; incr i }}
  close $f
  exit
}}
after time {settle:.1f} {{ final }}
"""
    open(tcl_path, "w").write(tcl)
    return _launch(tcl_path, out, dsk, timeout)


def run_profile(dsk: str, ptrs: list[int], settle: float, timeout: float) -> dict:
    """Trap each distinct $95xx driver pointer; count + first-call input (Phase 2)."""
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    bp_lines = []
    for p in ptrs:
        bp_lines.append(
            f'debug set_bp 0x{p:04X} {{}} {{\n'
            f'  incr ::c{p:04X}\n'
            f'  if {{$::c{p:04X} == 1}} {{ set ::in{p:04X} "[regs] ret=[format %04X [peek16 [reg SP]]]" }}\n'
            f'}}')
    tcl = f"""set throttle off
set renderer none
proc regs {{}} {{ {_regs_tcl()} }}
proc peek16 {{a}} {{ binary scan [debug read_block memory $a 2] su v; return $v }}
{chr(10).join(f'set ::c{p:04X} 0; set ::in{p:04X} ""' for p in ptrs)}
{chr(10).join(bp_lines)}
proc final {{}} {{
  set f [open {{{out}}} w]
{chr(10).join(f'  puts $f "c{p:04X}=$::c{p:04X}"' for p in ptrs)}
{chr(10).join(f'  puts $f "in{p:04X}=$::in{p:04X}"' for p in ptrs)}
  close $f
  exit
}}
after time {settle:.1f} {{ final }}
"""
    open(tcl_path, "w").write(tcl)
    return _launch(tcl_path, out, dsk, timeout)


def run_entry(dsk: str, entry: int, settle: float, timeout: float) -> dict:
    """Deep-trap one driver pointer: full input + output contract on return."""
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
debug set_bp 0x{entry:04X} {{}} {{ on_entry }}
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


def word_le(b: bytes, off: int) -> int:
    return b[off] | (b[off + 1] << 8)


def decode_pointers(tb: bytes) -> list[int]:
    """Aligned word fields after the 5-byte head (slot id + 2 words) that point
    into high RAM ($C000-$FFFF) = candidate driver-routine pointers."""
    ptrs = []
    for off in range(5, len(tb) - 1, 2):
        w = word_le(tb, off)
        if w >= 0xC000 and w not in ptrs:
            ptrs.append(w)
    return ptrs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--entry", type=lambda s: int(s, 0), default=None,
                    help="deep-trap one driver pointer (e.g. 0x95EF) instead of profiling")
    ap.add_argument("--no-trap", action="store_true",
                    help="Phase 1 only: dump + decode the table, no driver-entry traps")
    ap.add_argument("--watch", action="store_true",
                    help="read-watchpoint the table: per-offset read count + first reader PC")
    ap.add_argument("--writers", action="store_true",
                    help="write-watchpoint the table: who builds it (PC + value, in order)")
    ap.add_argument("--settle", type=float, default=12.0)
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")

    print(f"machine : {MACHINE}")

    # Deep single-entry mode: skip the dump, go straight to the in/out contract.
    if args.entry is not None:
        d = _copy_run(args.dos_disk, run_entry, args.entry, args.settle, args.timeout)
        print(f"entry   : ${args.entry:04X} (driver-pointer in/out contract)\n")
        if d.get("no_hit"):
            print(f"FAIL: ${args.entry:04X} never called during boot+settle "
                  f"(PC at give-up ${d.get('pc')}).")
            return 1
        print(f"--- INPUT (at ${args.entry:04X} entry) ---")
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
        print("\nblack-box; registers/RAM only -- no $95xx kernel code read.")
        return 0

    # Phase 1: dump + decode the table layout.
    d = _copy_run(args.dos_disk, run_dump, args.settle, args.timeout)
    hexs = d.get("drvtbl", "")
    tb = bytes.fromhex(hexs)
    print(f"DRVTBL  : ${DRVTBL:04X}  ({TABLE_LEN} bytes)\n")
    print("  raw   : " + " ".join(f"{x:02x}" for x in tb))
    if len(tb) >= 5:
        print(f"  decode: [+0] slot id   = ${tb[0]:02X}")
        print(f"          [+1] word     = ${word_le(tb, 1):04X}")
        print(f"          [+3] word     = ${word_le(tb, 3):04X}")
        # Aligned word fields after the 5-byte head (slot + 2 words).
        words = [(5 + 2 * i, word_le(tb, 5 + 2 * i))
                 for i in range((len(tb) - 5) // 2)]
        print("          [+5..] words  = " + ", ".join(
            f"[+{o}]=${w:04X}" for o, w in words))

    if args.writers:
        print(f"\n--- Write-watchpoint: who builds the DRVTBL? (PC + value, in order) ---\n")
        wr = _copy_run(args.dos_disk, run_writers, args.settle, args.timeout)
        n = int(wr.get("nwrites", "0"))
        print(f"  {n} write(s) to $F348..${DRVTBL + TABLE_LEN - 1:04X}")
        print("  " + "-" * 50)
        for i in range(n):
            e = wr.get(f"w{i}", "")
            print(f"  [{i:>3}] ${e}")
        if n == 0:
            print("  (none in window -- table built before settle start; lower nothing,"
                  " or widen the boot window earlier)")
        print("\nWriter PC tells us: page-1 ($4xxx-7xxx)=disk ROM INIT builds it;"
              " TPA/high RAM=MSXDOS builds it.")
        return 0

    if args.watch:
        print(f"\n--- Read-watchpoint: which table offsets does MSXDOS consume? ---\n")
        w = _copy_run(args.dos_disk, run_watch, args.settle, args.timeout)
        print("  off   addr     reads   first reader PC")
        print("  " + "-" * 50)
        for off in range(TABLE_LEN):
            cnt, _, pc = w.get(f"r{off}", "0 ").partition(" ")
            print(f"  +{off:<3} ${DRVTBL + off:04X}   {cnt:>5}   {('$' + pc) if pc else ''}")
        print("\nHigh-count offsets = the fields MSXDOS depends on (build those right).")
        return 0

    ptrs = decode_pointers(tb)
    print(f"          driver ptrs?  = {', '.join(f'${p:04X}' for p in ptrs) or '(none in high RAM)'}")

    if args.no_trap or not ptrs:
        if not ptrs:
            print("\nNo high-RAM pointers decoded -- widen TABLE_LEN or re-check layout.")
        return 0

    # Phase 2: trap each distinct driver pointer; which does MSXDOS call, and how?
    print(f"\n--- Phase 2: trap {len(ptrs)} driver pointer(s) (which MSXDOS invokes) ---\n")
    prof = _copy_run(args.dos_disk, run_profile, ptrs, args.settle, args.timeout)
    print("  ptr      calls   first-call input")
    print("  " + "-" * 70)
    for p in ptrs:
        c = prof.get(f"c{p:04X}", "0")
        inp = prof.get(f"in{p:04X}", "")
        print(f"  ${p:04X}   {c:>5}   {inp}")
    print("\nNext: --entry $<ptr> (a called one) for its full in/out contract,")
    print("then map it to our $4010-region driver entry and build $F348 in disk.asm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
