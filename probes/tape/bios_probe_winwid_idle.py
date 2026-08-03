#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

r"""Oracle probe: is WINWID ($FCA5) idle during a cassette WRITE session?

Closes a provenance gap for zerobas-tape. That patch caches the resolved write
baud in a byte it calls CASBAUD and parks it on the sysvar WINWID at $FCA5. WINWID
is documented as a cassette *READ* window-width variable (MSX2 Tech Handbook / MSX
Assembly Page sysvar map); zerobas-tape's safety claim is that $FCA5 is *idle
during a write*, so reusing it as a one-session baud cache collides with nothing.
That was asserted, not measured. This probe measures it.

Method (clean-room: the reference ROM is a BLACK BOX -- inputs in, watchpoint
hits out; no BIOS disassembly is read):

  1. Mint a self-authored write cart (probe_cart/z80probe scaffolding) that drives
     a representative full write session through the public BIOS entry points:
        TAPOON(long) + TAPOUT x16 header  + TAPOOF      (header block)
        TAPOON(short)+ TAPOUT x10 data    + TAPOOF      (data block)
     Two fixed code landmarks bracket the session: ARM (the instruction just
     before the first TAPOON) and DISARM (the instruction just after the last
     TAPOOF), whose addresses the builder reports back.
  2. Run it on the oracle machine (Philips VG-8020 by default) with openMSX debug
     watchpoints on $FCA5: one on write_mem, one on read_mem. An execution
     breakpoint at ARM zeroes the $FCA5 counters and opens the window; a
     breakpoint at DISARM closes it. So only accesses *inside the write session*
     are counted -- boot-time work-area init is excluded by construction. (Memory
     sentinels were tried first and rejected: the VG-8020 power-on RAM test writes
     patterns across all of RAM, so a write-sentinel fires many times during boot;
     execution landmarks only our cart reaches fire exactly once.)
  3. Assert: across the whole armed window the BIOS write path neither writes nor
     reads $FCA5. "Idle" = zero write hits AND zero read hits.

The ARM/DISARM breakpoint gating is the deterministic analogue of the
sentinel-POKE gating cas_baud_oracle.py uses: if the ARM/DISARM breakpoints did
not each fire exactly once, the window was never properly established and the
result is distrusted.

A non-idle result is an important NEGATIVE finding: it would mean the CASBAUD
placement collides with the system's own write path and must move. The probe then
prints the PCs at which $FCA5 was touched.

Usage:
    python3 probes/tape/bios_probe_winwid_idle.py [--machine Philips_VG_8020]
                                                  [--baud 1200|2400] [--keep]

Requires the oracle's system ROMs installed in openMSX (see docs/openmsx-harness.md).
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra
import z80probe as Z      # noqa: E402
import omsx_run           # noqa: E402  (reuse find_omsx for the $OPENMSX override)
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

WINWID = 0xFCA5           # the byte under test
TAPOON, TAPOUT, TAPOOF = 0x00EA, 0x00ED, 0x00F0

# A representative two-block BSAVE-style file (same shape as bios_probe_tapfile):
# a long-leader header block then a short-leader data block, so the armed window
# spans every distinct write-path activity (both leader types, two TAPOON spans).
FILENAME = [ord(c) for c in "WINWID"]              # 6 chars
HEADER = [0xD0] * 10 + FILENAME                    # 16 bytes
START, END, EXEC = 0x8000, 0x8003, 0x8000
PAYLOAD = [0xC9, 0x00, 0x11, 0x22]
DATA = [START & 0xFF, START >> 8, END & 0xFF, END >> 8,
        EXEC & 0xFF, EXEC >> 8] + PAYLOAD          # 10 bytes


def build_cart(baud: int, poison: bool = False) -> tuple[bytes, int, int]:
    """Return (rom, arm_pc, disarm_pc). The cart sets up the baud tables, then
    runs ARM -> full write session -> DISARM -> DONE landmark. ARM/DISARM are the
    code addresses the harness breakpoints to bracket the measured window.

    The payload is laid down starting at INIT, so a landmark's address is simply
    INIT + (bytes emitted so far) -- the address of the *next* instruction.

    With `poison`, a deliberate write+read of $FCA5 is injected just inside the
    window -- the instrument self-test: the probe MUST report those hits, else its
    watchpoints are blind and a clean "idle" reading would be meaningless."""
    c = Z.Cart()
    c.emit(Z.di())
    # Lay down CS120/CS240 and copy the chosen baud into the active slots, exactly
    # as a real BIOS + SCREEN ,,,baud would (bare C-BIOS leaves this blank). Done
    # before ARM so it never counts against the window.
    c.emit(Z.setup_cas_baud(baud))
    arm_pc = Z.INIT + len(c.code)                  # next instr = start of session
    if poison:
        c.emit(Z.ld_a(0x5A), Z.sta(WINWID))        # deliberate $FCA5 write...
        c.emit(Z.lda(WINWID))                       # ...and read, inside the window
    # header block: long leader
    c.emit(Z.ld_a(0xFF), Z.call(TAPOON))
    for b in HEADER:
        c.emit(Z.ld_a(b), Z.call(TAPOUT))
    c.emit(Z.call(TAPOOF))
    # data block: short leader
    c.emit(Z.ld_a(0x00), Z.call(TAPOON))
    for b in DATA:
        c.emit(Z.ld_a(b), Z.call(TAPOUT))
    c.emit(Z.call(TAPOOF))
    disarm_pc = Z.INIT + len(c.code)               # next instr = the JP DONE tail
    return c.build(), arm_pc, disarm_pc


def build_tcl(out_path: str, arm_pc: int, disarm_pc: int) -> str:
    """Watchpoint script: count $FCA5 read/write hits *inside* the ARM..DISARM
    window only, recording the PC of each, then capture at the DONE landmark.

    ARM/DISARM are execution breakpoints at cart code addresses only our payload
    reaches, so they fire exactly once -- no boot-time RAM-test noise."""
    return "\n".join([
        "# generated by bios_probe_winwid_idle.py -- $FCA5 write-idle watchpoints",
        "set throttle off",
        "set ::armed 0",
        "set ::arm_hits 0",
        "set ::disarm_hits 0",
        "set ::w_hits 0",
        "set ::r_hits 0",
        "set ::w_pc {}",
        "set ::r_pc {}",
        # ARM: open the window and zero the counters so boot-time work-area init
        # (which happens before this point) is excluded by construction.
        f"debug set_bp {arm_pc:#06x} {{}} {{"
        " set ::armed 1 ; incr ::arm_hits ;"
        " set ::w_hits 0 ; set ::r_hits 0 ; set ::w_pc {} ; set ::r_pc {} }",
        # DISARM: close the window (reached only after the last TAPOOF returns).
        f"debug set_bp {disarm_pc:#06x} {{}} {{"
        " set ::armed 0 ; incr ::disarm_hits }",
        # The bytes under test: only count while armed; record the offending PC.
        f"debug set_watchpoint write_mem {WINWID:#06x} {{}} {{"
        " if {$::armed} { incr ::w_hits ;"
        " lappend ::w_pc [format 0x%04X [reg PC]] } }",
        f"debug set_watchpoint read_mem {WINWID:#06x} {{}} {{"
        " if {$::armed} { incr ::r_hits ;"
        " lappend ::r_pc [format 0x%04X [reg PC]] } }",
        "proc __capture {} {",
        f"  set f [open {{{out_path}}} w]",
        '  puts $f "machine=[machine_info config_name]"',
        '  puts $f "arm_hits=$::arm_hits"',
        '  puts $f "disarm_hits=$::disarm_hits"',
        '  puts $f "fca5_write_hits=$::w_hits"',
        '  puts $f "fca5_read_hits=$::r_hits"',
        '  puts $f "fca5_write_pc=$::w_pc"',
        '  puts $f "fca5_read_pc=$::r_pc"',
        "  close $f",
        "  exit",
        "}",
        f"debug set_bp {Z.DONE:#06x} {{}} {{ __capture }}",
        "",
    ])


def run(machine: str, baud: int, keep: bool, poison: bool = False) -> dict[str, str]:
    rom, arm_pc, disarm_pc = build_cart(baud, poison=poison)
    rom_fd, rom_path = tempfile.mkstemp(suffix=".rom", prefix="winwid_")
    os.write(rom_fd, rom)
    os.close(rom_fd)
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="winwid_")
    os.close(out_fd)
    os.unlink(out_path)
    tcl = build_tcl(os.path.abspath(out_path), arm_pc, disarm_pc)
    tcl_fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="winwid_")
    os.write(tcl_fd, tcl.encode())
    os.close(tcl_fd)

    omsx = omsx_run.find_omsx(None)
    cmd = [omsx, "-machine", machine, "-cart", rom_path,
           "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    try:
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + 180.0
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            raise SystemExit(f"winwid_idle: TIMEOUT ({machine}); cart {rom_path}")
    finally:
        if keep:
            print(f"  (kept cart={rom_path} tcl={tcl_path})", file=sys.stderr)
        else:
            os.unlink(rom_path)
            os.unlink(tcl_path)

    if not os.path.exists(out_path):
        raise SystemExit("winwid_idle: openMSX wrote no capture "
                         "(DONE breakpoint never hit? bad machine?)")
    d: dict[str, str] = {}
    for line in open(out_path):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            d[k] = v
    if not keep:
        os.unlink(out_path)
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default="Philips_VG_8020",
                    help="oracle machine id (default Philips_VG_8020)")
    ap.add_argument("--baud", type=int, choices=(1200, 2400), default=1200,
                    help="write baud (copied into the active table, as SCREEN does)")
    ap.add_argument("--keep", action="store_true",
                    help="keep the generated cart/tcl/capture for inspection")
    ap.add_argument("--self-test", action="store_true",
                    help="inject a deliberate $FCA5 write+read into the window and "
                         "assert the probe catches it (validates the instrument)")
    args = ap.parse_args()

    if args.self_test:
        print(f"instrument self-test: poisoning the window with a $FCA5 write+read "
               f"on {args.machine}")
        d = run(args.machine, args.baud, args.keep, poison=True)
        w, r = int(d.get("fca5_write_hits", "0")), int(d.get("fca5_read_hits", "0"))
        print(f"  caught write hits: {w}   read hits: {r}")
        if w >= 1 and r >= 1:
            print("PASS: watchpoints fire on a real access -- a clean reading is "
                  "trustworthy.")
            return 0
        print("FAIL: poisoned access was NOT caught -- the watchpoints are blind.")
        return 1

    print(f"oracle: {args.machine}   baud: {args.baud}")
    print(f"probing WINWID (${WINWID:04X}) across a full TAPOON+TAPOUT+TAPOOF "
          "write session\n")
    d = run(args.machine, args.baud, args.keep)

    arm_hits = int(d.get("arm_hits", "0"))
    disarm_hits = int(d.get("disarm_hits", "0"))
    w_hits = int(d.get("fca5_write_hits", "0"))
    r_hits = int(d.get("fca5_read_hits", "0"))
    windowed = arm_hits == 1 and disarm_hits == 1

    print(f"  ARM hits:    {arm_hits}    DISARM hits: {disarm_hits}    "
          f"(window {'established' if windowed else 'NOT established -- distrust'})")
    print(f"  ${WINWID:04X} write hits (in window): {w_hits}")
    print(f"  ${WINWID:04X} read  hits (in window): {r_hits}")
    if w_hits:
        print(f"    write PCs: {d.get('fca5_write_pc', '')}")
    if r_hits:
        print(f"    read  PCs: {d.get('fca5_read_pc', '')}")

    if not windowed:
        print("\nDISTRUST: the ARM/DISARM window was not established; re-run.")
        return 2
    idle = (w_hits == 0 and r_hits == 0)
    if idle:
        print(f"\nIDLE confirmed: the {args.machine} write path neither writes "
              f"nor reads ${WINWID:04X} during a full cassette write session.")
        print("-> zerobas-tape may safely cache CASBAUD on WINWID.")
        return 0
    print(f"\nNOT IDLE: ${WINWID:04X} is touched during a write (see PCs above) -- "
          "the CASBAUD placement collides with the write path and must move.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
