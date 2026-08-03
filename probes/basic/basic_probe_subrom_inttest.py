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
    ld ix,$0019          ; page-0 entry index 3 = $0010 + 3*3 (SUBROM_IDX_INTTEST)
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
and hang — the safety-net capture then yields delta 0 and the gate FAILs. There is
no storm-or-hang path that still reports delta >= 1, so this single assertion is
the whole proof.

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
# at $C100. Index 3 lives at page-0 entry $0010 + 3*3 = $0019.
STUB_ADDR = 0xC000
STUB_HALT = 0xC012
RES = 0xC100
STUB_BYTES = bytes([
    0xF3,                    # di
    0xFD, 0x21, 0x00, 0x8B,  # ld iy,$8B00                (slot 3-2)
    0xDD, 0x21, 0x19, 0x00,  # ld ix,$0019                (page-0 index 3)
    0xCD, 0x1C, 0x00,        # call $001C                 (CALSLT -> sub_int_selftest)
    0x3A, 0x4D, 0xF1,        # ld a,($F14D)               (SUB_INT_DELTA)
    0x32, 0x00, 0xC1,        # ld ($C100),a               (stash result)
    0x76,                    # halt                       (capture bp)
])
assert len(STUB_BYTES) == 19, f"stub size changed: {len(STUB_BYTES)}"


def run() -> int | None:
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="subrom_int_")
    os.close(out_fd)
    stub_hex = "".join(f"{b:02x}" for b in STUB_BYTES)
    lines = [
        "set throttle off",
        "proc __hex {addr} {",
        "  binary scan [debug read_block memory $addr 1] H* h; return $h",
        "}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
        f'  puts $f "delta=[__hex {RES}]"',
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
        f"  debug set_bp {STUB_HALT} {{}} {{ __cap }}",
        f"  reg PC {STUB_ADDR}",
        "}",
        # Safety net: a broken trampoline hangs (garbage at sub-ROM $0038), so
        # capture anyway (delta stays 0) rather than let the watchdog kill us.
        "after time 12.0 { __cap }",
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
        return None
    delta = None
    for ln in open(out_path):
        if ln.startswith("delta="):
            v = ln.strip().split("=", 1)[1]
            delta = int(v, 16) if v else None
    os.unlink(out_path)
    return delta


def main() -> int:
    delta = run()
    if delta is None:
        print("subrom interrupt gate: FAIL (no capture)")
        return 1
    ok = delta >= 1
    print(f"page-0 EI tenant: JIFFY delta = {delta} ticks "
          f"(expect >= 1, serviced via the sub-ROM $0038 trampoline): "
          f"{'PASS' if ok else 'FAIL'}")
    print("-------------------")
    print("subrom interrupt-trampoline gate:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
