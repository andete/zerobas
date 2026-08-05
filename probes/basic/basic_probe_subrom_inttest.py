#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Interrupt-trampoline gate for zerobas-sub — a page-0 tenant that runs EI.

Proves the whole trampoline path end-to-end on the REAL merged machine
(C-BIOS_MSX1_EU_REPACK_DISK: merged repack main ROM in slot 0, zerobas-disk in
3-1, zerobas-sub in 3-2). On boot, init_ext_roms records the sub-ROM slot and
runs sub_int_install, which copies the RAM trampoline stub into SUB_INT_RAM and
records the two page-0 slot configs. So by the time we inject, the trampoline is
already live — this gate never sets it up itself, it exercises the shipped boot
path.

Then it injects a tiny stub into RAM ($C000) and redirects the CPU to it:

    di
    ld iy,$8B00          ; slot 3-2 ($8B), CALSLT reads the slot from IYh
    ld ix,$0049          ; page-0 entry index 3 = $0040 + 3*3 (SUBROM_IDX_INTTEST)
    call $001C           ; CALSLT -> sub_int_selftest
    ld a,($F14D)         ; SUB_INT_DELTA (JIFFY ticks the tenant saw under EI)
    ld ($C100),a         ; stash the result
    halt                 ; capture breakpoint

sub_int_selftest reads JIFFY, EI's, spins well past one 50/60 Hz frame, DI's, and
stores the JIFFY delta in SUB_INT_DELTA. While it spins with page 0 = sub-ROM, the
timer interrupt fires into the sub-ROM's own $0038 (`jp SUB_INT_RAM`), which maps
the BIOS back into page 0, runs the real ISR (JIFFY++), and returns. So a delta
>= 1 proves the trampoline serviced the interrupt through the paged-out BIOS. With
the trampoline broken the machine would instead execute garbage at sub-ROM $0038
and hang — the safety-net capture then yields delta 0 and the gate FAILs.

🔴 THE DELTA IS BOUNDED ON BOTH SIDES, AND THE UPPER BOUND IS NOT DECORATION.
This docstring used to claim "there is no storm-or-hang path that still reports
delta >= 1, so this single assertion is the whole proof". That is FALSE, measured:
D-P0BASE (docs/spec-rom-region-p0base.md §5.4 K4b) pointed this stub's CALSLT at
an address that is $FF PAD — the exact defect a page-0 entry-table move can
introduce — and the gate reported `delta = 255 ticks` and PASSED. Executing pad is
`rst 38h` over and over; the timer keeps ticking while the CPU never runs the
tenant at all, so a one-sided `>= 1` cannot tell "the trampoline worked" from
"the CPU spent longer than the tenant would have, somewhere else entirely".

The tenant's spin is FIXED-LENGTH (65536 iterations, ~1.7 M cycles), so its delta
cannot legitimately be large: measured 28, 28, 28 on three consecutive runs of the
merged machine (openMSX is deterministic), and ~23 at 50 Hz against ~28 at 60 Hz.
DELTA_MAX = 64 is a bit over 2x the measured value — generous room for a frame
rate change or a tweak to the spin, and nowhere near the 255 a runaway reads.

🔴 AND DELTA_MAX WAS STILL NOT ENOUGH — THE PRECONDITION IS. D-ROMJUDGE
(docs/spec-rom-gate-judge.md §2.4) ran this gate against an ENTIRELY $FF sub-ROM,
i.e. no zerobas code at all, and it reported `delta = 57 ticks` and PASSED, one day
after DELTA_MAX landed. 255 was the reading for a PARTIAL pad; with the whole image
pad the reading lands inside the band. A bound sized from one sample of one failure
mode cannot cover the others.

What separates them is already observable and was being thrown away: WHICH CAPTURE
PATH FIRED. On a healthy tree the stub reaches its `halt` and the breakpoint
captures (`path=bp`, delta 28). With the tenant unreachable the CPU never returns
and only the 12 s safety net captures (`path=net`, delta 57). "The tenant returned"
is a PRECONDITION of the delta meaning anything, so it is asserted first and the
delta is not consulted at all when it fails.

⚠️ The safety net's own comment used to claim the delta "stays 0" on that path. It
does not: executing $FF is `rst 38h` recursing forever, and the stack walks down
through the whole address space and overwrites the result cell. The 57 was a STACK
BYTE, not a timer reading — which is why zeroing $C100 before the run does not save
this, and why the readout cannot be trusted to be self-evidently broken.

Needs the merged machine installed (make repack-machine) and openMSX. Run:

    python3 probes/basic/basic_probe_subrom_inttest.py
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time

# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
# The shipped merged machine (tools/install-repack-machine.py --sub-rom); the
# Makefile gate depends on `repack-machine` so it is present. Overridable to match
# the repack-acceptance machine-remap convention.
MACHINE = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# The CALSLT stub. Loaded at $C000; halt sentinel at $C012; result (JIFFY delta)
# at $C100. Index 3 lives at page-0 entry $0040 + 3*3 = $0049.
STUB_ADDR = 0xC000
STUB_HALT = 0xC012
RES = 0xC100
STUB_BYTES = bytes([
    0xF3,                    # di
    0xFD, 0x21, 0x00, 0x8B,  # ld iy,$8B00                (slot 3-2)
    0xDD, 0x21, 0x49, 0x00,  # ld ix,$0049                (page-0 index 3)
    0xCD, 0x1C, 0x00,        # call $001C                 (CALSLT -> sub_int_selftest)
    0x3A, 0x4D, 0xF1,        # ld a,($F14D)               (SUB_INT_DELTA)
    0x32, 0x00, 0xC1,        # ld ($C100),a               (stash result)
    0x76,                    # halt                       (capture bp)
])
assert len(STUB_BYTES) == 19, f"stub size changed: {len(STUB_BYTES)}"

# Upper bound on the JIFFY delta. The tenant's spin is fixed-length, so a LARGE
# delta means the CALSLT never reached it -- see the module docstring. Measured 28.
DELTA_MAX = 64


def run() -> int | None:
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="subrom_int_")
    os.close(out_fd)
    stub_hex = "".join(f"{b:02x}" for b in STUB_BYTES)
    lines = [
        "set throttle off",
        "proc __hex {addr} {",
        "  binary scan [debug read_block memory $addr 1] H* h; return $h",
        "}",
        # `why` records WHICH path captured: bp = the stub reached its halt (the
        # tenant returned), net = the safety net fired (it did not). See the
        # docstring -- this is the precondition, not a diagnostic.
        "proc __cap {why} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
        f'  puts $f "delta=[__hex {RES}]"',
        '  puts $f "path=$why"',
        "  close $f",
        "  exit",
        "}",
        # After boot (init_ext_roms has installed the trampoline and the REPL is
        # up), inject the stub, clear the result cell, arm a breakpoint at the
        # stub's halt, and redirect the CPU into the stub. The self-test tenant
        # spins > one frame under EI before it returns, so give the bp room.
        "after time 6.0 {",
        f"  debug write_block memory {STUB_ADDR} [binary format H* {{{stub_hex}}}]",
        f"  debug write memory {RES} 0x00",
        f"  debug set_bp {STUB_HALT} {{}} {{ __cap bp }}",
        f"  reg PC {STUB_ADDR}",
        "}",
        # Safety net: a broken trampoline hangs (garbage at sub-ROM $0038), so
        # capture anyway rather than let the watchdog kill us -- but tagged `net`,
        # because the delta it reports is NOT a timer reading. Measured: a runaway
        # `rst 38h` walks the stack through the whole address space and lands a
        # stack byte in the result cell (57 on an all-$FF image, well inside the
        # 1..DELTA_MAX band). The tag is what makes that row red.
        "after time 12.0 { __cap net }",
    ]
    tcl = "\n".join(lines) + "\n"
    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="subrom_int_")
    os.write(fd, tcl.encode())
    os.close(fd)

    cmd = [OMSX, "-machine", MACHINE, "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    try:
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + 90
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            print("TIMEOUT")
            return None
    finally:
        os.unlink(tcl_path)

    if not os.path.exists(out_path):
        return None, None
    delta, path = None, None
    for ln in open(out_path):
        if ln.startswith("delta="):
            v = ln.strip().split("=", 1)[1]
            delta = int(v, 16) if v else None
        elif ln.startswith("path="):
            path = ln.strip().split("=", 1)[1] or None
    os.unlink(out_path)
    return delta, path


def main() -> int:
    delta, path = run()
    if delta is None:
        print("subrom interrupt gate: FAIL (no capture)")
        return 1

    # PRECONDITION, asserted before the delta is consulted at all: the stub must
    # have reached its own halt, i.e. the CALSLT returned. See the docstring --
    # the safety-net path reports a stack byte, not a JIFFY delta.
    returned = path == "bp"
    print(f"page-0 EI tenant returned to the stub: capture path = {path} "
          f"(expect bp, NOT the 12 s safety net): {'PASS' if returned else 'FAIL'}")
    if not returned:
        print(f"  ^ THE TENANT NEVER RETURNED: the CALSLT did not reach it and the "
              f"machine was still wedged when the safety net fired. The reported "
              f"delta ({delta}) is whatever a runaway `rst 38h` left in the result "
              f"cell, NOT a timer reading — do not read it as a near miss. Check "
              f"the page-0 entry address against sub/equates.inc "
              f"SUBROM_ENTRY_BASE_P0, and check build/sub.rom actually holds the "
              f"assembled image (tools/pad_rom.py's report).")

    in_band = 1 <= delta <= DELTA_MAX
    print(f"page-0 EI tenant: JIFFY delta = {delta} ticks "
          f"(expect 1..{DELTA_MAX}, serviced via the sub-ROM $0038 trampoline): "
          f"{'PASS' if in_band else 'FAIL'}")
    if delta > DELTA_MAX:
        print(f"  ^ TOO LARGE: the tenant's spin is fixed-length (~28 ticks). A "
              f"delta this big means the CALSLT did NOT reach it — check the "
              f"page-0 entry address against sub/equates.inc SUBROM_ENTRY_BASE_P0.")
    ok = returned and in_band
    print("-------------------")
    print("subrom interrupt-trampoline gate:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
