#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Locate the CAS-in (cassette read) input bit empirically.

Before the read path (TAPION/TAPIN) can be written we must know *which* port bit
the cassette read signal arrives on. The two documented candidates on MSX1 are:

  * PPI Port B  ($A9) bit 7   -- keyboard-status register
  * PSG register 14 bit 7     -- AY-3-8910 general-purpose I/O port A

This cart turns the motor on (so an inserted tape plays), then takes 256 tightly
spaced samples of *each* candidate into the result buffer:

  0xE000..0xE0FF : PPI Port B ($A9), masked to bit 7 ($00 or $80)
  0xE100..0xE1FF : PSG R14,          masked to bit 7 ($00 or $80)

With a known FSK recording inserted (e.g. our own write-path WAV, whose leader is
a continuous ~2400 Hz tone), the bit carrying the signal shows many transitions;
a static bit shows none. The host side counts transitions and reports the winner.
This is black-box observation only -- no reference disassembly involved.

  python3 probes/tape/bios_probe_casin.py --out casin.rom
  python3 probes/lib/omsx_run.py --machine C-BIOS_MSX1_EU_TAPE --cart casin.rom \
      --cassette ours.wav --bp 0x7FF0 --mem memory:0xE000:512 --out cap.txt
  python3 probes/tape/bios_probe_casin.py --analyze cap.txt
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse, os, sys
import z80probe as Z  # noqa: E402

STMOTR = 0x00F3
KBD_STAT = 0xA9          # PPI Port B
PSG_ADDR = 0xA0          # PSG register-latch (write)
PSG_READ = 0xA2          # PSG data read
NSAMP = 256


def _sample_loop(base: int, read_seq: list[int]) -> list[int]:
    """Emit: HL=base; B=NSAMP(0=256); loop { read_seq -> A; AND $80; (HL)=A; INC HL; DJNZ }."""
    code: list[int] = []
    code += Z.ld_hl(base)
    code += Z.ld_b(NSAMP & 0xFF)          # 0 -> 256 iterations via DJNZ
    loop = code  # marker; we compute the JR target by length
    body = list(read_seq) + [0xE6, 0x80] + [0x77, 0x23]   # AND $80; LD (HL),A; INC HL
    # DJNZ back over body+djnz: displacement = -(len(body)+2)
    disp = (-(len(body) + 2)) & 0xFF
    code += body + [0x10, disp]           # DJNZ
    return code


def build() -> bytes:
    c = Z.Cart()
    c.emit(Z.di())
    c.emit(Z.ld_a(1), Z.call(STMOTR))     # motor on -> inserted tape plays
    # Settle so the player is definitely DELIVERING, not merely running.
    # 🔴 THIS WAS 0x4000 (~119 ms) AND THAT IS TOO SHORT (D-CASINSETTLE,
    # 2026-08-31). openMSX's cassette player needs roughly half an emulated
    # second after motor-on before signal reaches the port, so the shipped
    # window sampled the silence and the probe printed BOTH candidates static
    # -- the refutation of its own documented finding -- and still exited 0.
    # Measured on one WAV, one machine, in one sitting: 0x0100 static,
    # 0x4000 static, 2x0xFFFF (~0.9 s) 23 transitions on R14. The GREEN
    # CONTROL is bios_probe_tapraw.py, which never saw this because it blocks
    # on edges instead of counting down, and read ~14-iteration half-periods
    # off the very same WAV in the very same sitting.
    for _ in range(2):
        c.emit(Z.ld_bc(0xFFFF))
        c.emit([0x0B, 0x78, 0xB1, 0x20, 0xFB])  # settle: DEC BC; LD A,B; OR C; JR NZ
    # candidate 1: PPI Port B ($A9) bit 7
    c.emit(_sample_loop(0xE000, Z.in_a(KBD_STAT)))
    # candidate 2: PSG R14 bit 7  (latch reg 14, read data port)
    psg_read = Z.ld_a(14) + Z.out_a(PSG_ADDR) + Z.in_a(PSG_READ)
    c.emit(_sample_loop(0xE100, psg_read))
    return c.build()


def analyze(path: str) -> int:
    raw = None
    with open(path) as f:
        for line in f:
            if line.startswith("mem.memory:0xE000:512="):
                raw = line.strip().split("=", 1)[1]
    if not raw:
        print("no mem.memory:0xE000:512= line found in", path, file=sys.stderr)
        return 2
    data = bytes.fromhex(raw)
    if len(data) < 512:
        print(f"short capture: {len(data)} bytes", file=sys.stderr)
        return 2
    live = 0
    for name, off in (("PPI Port B $A9 bit7", 0), ("PSG R14 bit7", 256)):
        bits = [(data[off + i] >> 7) & 1 for i in range(NSAMP)]
        trans = sum(1 for i in range(1, NSAMP) if bits[i] != bits[i - 1])
        ones = sum(bits)
        carries = trans > 8
        live += carries
        verdict = "  <-- CARRIES SIGNAL" if carries else "  (static)"
        print(f"{name:24s}: {trans:3d} transitions, {ones:3d}/{NSAMP} high{verdict}")
    # 🔴 A NULL READING IS AN APPARATUS FAILURE, NOT A FINDING. If NEITHER
    # candidate moves, no signal reached the sampler at all: the tape is not
    # inserted, the motor did not start, or -- the case that actually happened
    # -- the settle window closed before the player began delivering. Printing
    # "both static" and exiting 0 states the OPPOSITE of what this probe was
    # written to establish, in the same calm voice as the real answer. Refuse.
    if not live:
        print("\n🔴 NEITHER candidate carries signal -- NOTHING WAS MEASURED.\n"
              "   Check: a tape is inserted (--cassette), the motor starts, and\n"
              "   the settle window outlasts the player's start-up (~0.5 s).\n"
              "   Cross-check with bios_probe_tapraw.py, which blocks on edges.",
              file=sys.stderr)
        return 2
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="write the probe cart ROM")
    ap.add_argument("--analyze", metavar="CAP",
                    help="analyze an omsx_run.py capture (mem.memory:0xE000:512=...)")
    args = ap.parse_args()
    if args.analyze:
        return analyze(args.analyze)
    if not args.out:
        ap.error("need --out or --analyze")
    with open(args.out, "wb") as f:
        f.write(build())
    print(f"wrote {args.out}: motor on, 256 samples each of PPI-B and PSG-R14 "
          f"at 0x{Z.RESULT:04X}/0x{Z.RESULT+256:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
