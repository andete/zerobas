#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""BLOAD"CAS:",R oracle probe — Phase 1 first-light tracer bullet.

Builds a tiny self-authored binary blob, wraps it in a .cas BSAVE image,
boots a real MSX-BASIC (Philips VG-8020) in openMSX, keyboard-injects
BLOAD"CAS:",R, and captures memory + sysvars to prove the full pipeline:
  tokenise → execute BLOAD → cassette load → ,R handoff → blob runs.

The blob writes "JONG" to 0xE000 and halts at a fixed landmark. If the
capture shows the marker at 0xE000 and the breakpoint fired, the handoff
worked — oracle-confirmed, no disassembly needed.

See the clean-room firewall (CONTRIBUTING.md) for provenance rules.
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import os
import subprocess
import sys
import tempfile

# ---- paths relative to repo root ----

from z80probe import ld_a, sta  # noqa: E402
from cas_encode import build_cas  # noqa: E402
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

# ---- blob parameters ----
LOAD_ADDR = 0xC000
MARKER_ADDR = 0xE000
MARKER = b"JONG"
LANDMARK = LOAD_ADDR + 100  # JR $ at a fixed offset inside the blob

# ---- sysvar addresses (source: MSX2 Technical Handbook / msx_symbols.py) ----
TXTTAB = 0xF676
VARTAB = 0xF6C2
ARYTAB = 0xF6C4
STREND = 0xF6C6
SAVEND = 0xF87D  # end address after BLOAD
FILNM2 = 0xF871  # filename buffer (11 bytes)

MACHINE = "Philips_VG_8020"
OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")


def build_blob() -> bytes:
    """Hand-assemble a tiny blob: write JONG to MARKER_ADDR, then JR $ at LANDMARK."""
    code: list[int] = []
    for i, ch in enumerate(MARKER):
        code += ld_a(ch)
        code += sta(MARKER_ADDR + i)
    # Pad to reach LANDMARK offset, then JR $ (0x18, 0xFE)
    pad_needed = (LANDMARK - LOAD_ADDR) - len(code)
    if pad_needed < 0:
        raise ValueError(f"blob code ({len(code)} bytes) overflows LANDMARK offset "
                         f"({LANDMARK - LOAD_ADDR})")
    code += [0x00] * pad_needed  # NOP padding
    code += [0x18, 0xFE]         # JR $  — the landmark the harness breaks on
    return bytes(code)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help=f"openMSX machine id (default {MACHINE})")
    ap.add_argument("--cart", help="insert a BASIC cartridge ROM (implementation "
                    "mode). The same BLOAD line is typed either way: into the "
                    "machine's built-in BASIC (oracle) or into the cart's REPL "
                    "prompt (zerobas).")
    ap.add_argument("--repl", action="store_true",
                    help="force zerobas-REPL typing (separate Enter, longer waits). "
                    "Implied by --cart AND by any --machine other than the oracle "
                    "default, since every other machine we run boots zerobas.")
    args = ap.parse_args()
    # REPL typing is needed whenever the BASIC being driven is zerobas rather than
    # the oracle's built-in BASIC: zerobas reaches its prompt later (boot scan +
    # header) and drops keys sent before INIT runs EI.
    #
    # This used to be `args.repl or bool(args.cart)`, which silently mis-typed on
    # any zerobas machine that carries BASIC in ROM instead of on a cart -- notably
    # C-BIOS_MSX1_EU_REPACK_DISK. The run then TIMED OUT waiting for a breakpoint
    # that could never fire, and the timeout was briefly mis-read as "this machine
    # has no working cassette device" (it has: tools/build_mainrom.py overlays the
    # zerobas-tape completions at $00E2-$00F6 + $09EE into the merged ROM). A
    # control run reproducing the SAME failure on an older build made the wrong
    # explanation look confirmed -- a control that fails must be FIXED, not
    # interpreted. Default it off the machine id so the trap cannot recur.
    repl = args.repl or bool(args.cart) or args.machine != MACHINE

    blob = build_blob()
    cas = build_cas("BLOAD", LOAD_ADDR, LOAD_ADDR, blob)

    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="bload_probe_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="bload_cap_")
    os.close(out_fd)

    blob_len = len(blob)
    cmd = [
        sys.executable, OMSX_RUN,
        "--machine", args.machine,
        "--cassette", cas_path,
    ]
    if args.cart:
        cmd += ["--cart", args.cart]
    # Type the BLOAD line: into the built-in reference BASIC (oracle) or the
    # zerobas REPL (cartridge, or patched into page 1).
    if repl:
        # zerobas's REPL reads via CHGET. Two robustness points:
        #   * Its boot+header reaches the prompt later than the built-in BASIC,
        #     and keys sent before INIT runs EI are lost — so wait longer.
        #   * Under `set throttle off` a trailing Enter in the same burst is
        #     often missed (keys inject faster than the ISR scans). Sending the
        #     Enter as a separate, later injection commits the line reliably.
        cmd += ["--type", 'bload"cas:",r', "--type-delay", "8",
                "--type", "\r", "--type-delay", "12"]
    else:
        cmd += ["--type", 'bload"cas:",r\r', "--type-delay", "5"]
    cmd += [
        "--bp", hex(LANDMARK),
        "--reg", "PC", "--reg", "A", "--reg", "SP",
        "--mem", f"memory:0x{MARKER_ADDR:04X}:{len(MARKER)}",
        "--mem", f"memory:0x{LOAD_ADDR:04X}:{blob_len}",
        "--mem", f"memory:0x{TXTTAB:04X}:2",
        "--mem", f"memory:0x{VARTAB:04X}:2",
        "--mem", f"memory:0x{ARYTAB:04X}:2",
        "--mem", f"memory:0x{STREND:04X}:2",
        "--mem", f"memory:0x{SAVEND:04X}:2",
        "--mem", f"memory:0x{FILNM2:04X}:11",
        "--out", out_path,
        "--timeout", "120",
    ]

    print(f"blob: {blob_len} bytes at 0x{LOAD_ADDR:04X}, "
          f"landmark 0x{LANDMARK:04X}")
    print(f"cas:  {cas_path} ({len(cas)} bytes)")
    print(f"running: {' '.join(cmd)}\n")

    rc = subprocess.call(omsx_preflight.guarded(cmd))
    if rc != 0:
        print(f"\nomsx_run exited with code {rc}", file=sys.stderr)
        return rc

    print()
    with open(out_path) as f:
        capture = f.read()
    print(capture)

    # Quick assertions
    ok = True
    if f"mem.memory:0x{MARKER_ADDR:04X}:{len(MARKER)}=" in capture:
        marker_hex = MARKER.hex()
        if marker_hex in capture:
            print(f"PASS  marker JONG at 0x{MARKER_ADDR:04X}")
        else:
            print(f"FAIL  marker at 0x{MARKER_ADDR:04X} not JONG")
            ok = False
    else:
        print(f"FAIL  marker dump not found in capture")
        ok = False

    expected_pc = f"reg.PC=0x{LANDMARK:04X}"
    if expected_pc in capture:
        print(f"PASS  PC at landmark 0x{LANDMARK:04X} (,R handoff worked)")
    else:
        print(f"FAIL  PC not at landmark (,R handoff did not fire)")
        print(f"      expected: {expected_pc}")
        ok = False

    # Cleanup temp files
    os.unlink(cas_path)
    os.unlink(out_path)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
