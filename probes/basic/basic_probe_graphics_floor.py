#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Graphics G1 floor gate — proves the SCREEN-2 geometry engine's architecture.

docs/spec-basic-graphics-g1.md §7. Runs on the shipped merged machine
(C-BIOS_MSX1_EU_REPACK_DISK: merged repack main ROM in slot 0, zerobas-disk in
3-1, zerobas-sub in 3-2). On boot, init_ext_roms installs the RAM interrupt
trampoline (sub_int_install), so a page-0 tenant can already run EI.

The probe injects a stub at $C000 and redirects the CPU into it:

    di
    ld iy,$8B00          ; slot 3-2 ($8B); CALSLT reads the slot from IYh
    ld ix,$0028          ; page-0 entry index 8 = $0010 + 3*8 (SUBROM_IDX_GRAPHICS)
    call $001C           ; CALSLT -> graphics_selftest (GFX_OP=0)
    halt                 ; capture breakpoint

graphics_selftest (sub/graphics.asm) EI's, writes f(addr)=low^high to every cell
of an 8 KB VRAM block via the di-guarded direct-port primitives, reads the block
back, and publishes two results in page-3 RAM:

    GFX_DJ  ($C120) = JIFFY delta observed while drawing under EI  (>= 1 = interrupts serviced)
    GFX_BAD ($C121) = VRAM read-back mismatch count               (0 = no address-latch corruption)

PASS = delta >= 1 AND bad == 0: interrupts stayed live during the draw (music
would keep playing) and the di-guarded 2-byte VDP address latch kept every access
correct despite the ISR reading the status port (which resets the latch flip-flop)
every VBLANK. This is our own architectural proof, not a VG-8020 differential (the
reference uses its own routines; §11.6 already confirmed interrupts stay live on
real hardware — the behaviour we match).

--expect-fail inverts the verdict: it is the "teeth check" (spec §4) run against a
sub-ROM built WITHOUT the guard (pasmo --equ GFX_UNGUARDED=1, installed into the
machine first). There the racing ISR MUST corrupt the latch, so bad > 0 — proving
a PASS above is a real result, not a test that cannot fail.

Needs the merged machine installed (make repack-machine) and openMSX. Run:

    python3 probes/basic/basic_probe_graphics_floor.py
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
MACHINE = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# The CALSLT stub. Loaded at $C000; halt sentinel at $C00E. Index 8 lives at
# page-0 entry $0010 + 3*8 = $0028. Results are written by the tenant itself into
# GFX_DJ ($C120) / GFX_BAD ($C121), so the stub only needs to make the call.
STUB_ADDR = 0xC000
STUB_HALT = 0xC00E
GFX_DJ = 0xC120
GFX_BAD = 0xC121
GFX_OP = 0xE030   # G2: index 8 is now selector-dispatched; 0 = the floor self-test
STUB_BYTES = bytes([
    0xF3,                    # di
    0xFD, 0x21, 0x00, 0x8B,  # ld iy,$8B00                (slot 3-2)
    0xDD, 0x21, 0x28, 0x00,  # ld ix,$0028                (page-0 index 8)
    0xCD, 0x1C, 0x00,        # call $001C                 (CALSLT -> graphics_selftest)
    0x76,                    # halt                       (capture bp)
])
assert len(STUB_BYTES) == 13, f"stub size changed: {len(STUB_BYTES)}"


def run() -> tuple[int, int] | None:
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="gfx_floor_")
    os.close(out_fd)
    stub_hex = "".join(f"{b:02x}" for b in STUB_BYTES)
    lines = [
        "set throttle off",
        "proc __hex {addr} {",
        "  binary scan [debug read_block memory $addr 1] H* h; return $h",
        "}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
        f'  puts $f "dj=[__hex {GFX_DJ}] bad=[__hex {GFX_BAD}]"',
        "  close $f",
        "  exit",
        "}",
        # After boot (trampoline installed, REPL up), inject the stub, clear both
        # result cells, arm a bp at the stub's halt, and jump into the stub. The
        # self-test writes+reads 8 KB under EI (a few frames), so give the bp room.
        "after time 6.0 {",
        f"  debug write_block memory {STUB_ADDR} [binary format H* {{{stub_hex}}}]",
        f"  debug write memory {GFX_OP} 0x00",   # select the floor self-test (G2 selector)
        f"  debug write memory {GFX_DJ} 0x00",
        f"  debug write memory {GFX_BAD} 0xff",   # sentinel: a no-run leaves 0xff (a visible FAIL)
        f"  debug set_bp {STUB_HALT} {{}} {{ __cap }}",
        f"  reg PC {STUB_ADDR}",
        "}",
        # Safety net: capture anyway if the tenant never returns (hang).
        "after time 14.0 { __cap }",
    ]
    tcl = "\n".join(lines) + "\n"
    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="gfx_floor_")
    os.write(fd, tcl.encode())
    os.close(fd)

    cmd = [OMSX, "-machine", MACHINE, "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
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
    dj = bad = None
    for ln in open(out_path):
        ln = ln.strip()
        if ln.startswith("dj="):
            for tok in ln.split():
                k, v = tok.split("=", 1)
                if k == "dj":
                    dj = int(v, 16) if v else None
                elif k == "bad":
                    bad = int(v, 16) if v else None
    os.unlink(out_path)
    if dj is None or bad is None:
        return None
    return dj, bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-fail", action="store_true",
                    help="teeth check: assert the gate FAILs (bad>0) — for an "
                         "unguarded sub-ROM build (pasmo --equ GFX_UNGUARDED=1)")
    args = ap.parse_args()

    res = run()
    if res is None:
        print("graphics floor gate: FAIL (no capture)")
        return 1
    dj, bad = res
    live = dj >= 1
    clean = bad == 0
    print(f"page-0 graphics tenant under EI: JIFFY delta = {dj} "
          f"(expect >= 1, interrupts serviced mid-draw): {'PASS' if live else 'FAIL'}")
    print(f"di-guarded VDP latch: read-back mismatches = {bad} "
          f"(expect 0, no address-latch corruption): {'PASS' if clean else 'FAIL'}")
    print("-------------------")
    if args.expect_fail:
        # Teeth check: interrupts must still be live, but the stripped guard must
        # let the latch race corrupt the block -> bad > 0.
        ok = live and bad > 0
        print("graphics floor TEETH check (unguarded build, expect corruption):",
              "PASS" if ok else "FAIL")
        return 0 if ok else 1
    ok = live and clean
    print("graphics floor gate:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
