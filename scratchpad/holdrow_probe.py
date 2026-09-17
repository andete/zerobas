#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-HOLDROW -- separate "row 8 is not reached" from "STICK does not read it".

D-JOYPLUG spent three cuts on a flat reading and each time the CONTROL caught it:
`STICK(0)` with arrow-UP held (row 8, bit $20) reads 0 on the VG-8020 as well as
here, so the instrument cannot move any `STICK`. The filed next step was NOT
another blind cut but this: start from a hold that is KNOWN to work and change
ONE thing at a time.

  * `k0` is the known-good configuration -- row 6 bit $20 is F1, exactly what the
    shipping `keykw_b` row holds, and F1's default macro types `color ` into the
    buffer. If THIS reads nothing the rig is broken and nothing else here means
    anything.
  * `k1` changes ONE thing: the same sampler, the same timing, but row 8 bit $20
    (arrow UP). `INKEY$` reads the KEY BUFFER, so a hit proves row 8 IS reached
    and moves the fault onto `STICK`; a miss localises it to the hold itself.
  * `k2` is `k1`'s reading taken through `STICK(0)` instead -- the row that has
    been flat all along, now with `k1` beside it to say why.
  * `k3` is a SECOND row-8 bit (SPACE, $01), so "row 8" and "bit 5" cannot hide
    behind each other.

🔴 BOTH MACHINES, because the last tick's lesson was that zerobas alone made a
flat reading look like a defect of ours.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")

# Accumulate INKEY$ until one character arrives or ~1 s of emulated time passes,
# then report its CODE -- a code, not a glyph, because a space is invisible.
SAMPLER = ['A$=""', "T=TIME", "A$=A$+INKEY$",
           'IF A$="" AND TIME-T<60 THEN 30',
           'IF A$="" THEN PRINT"<Jnone>":END',
           'PRINT"<J";ASC(A$);">":END']
STICK0 = ['PRINT"<J";STICK(0);">"']

CASES = [
    ("k0_f1_inkey",  SAMPLER, (6, 0x20)),   # KNOWN GOOD: F1 types its macro
    ("k1_up_inkey",  SAMPLER, (8, 0x20)),   # one change: row 8 bit 5 (UP)
    ("k2_up_stick",  STICK0,  (8, 0x20)),   # the flat row, beside k1
    ("k3_spc_inkey", SAMPLER, (8, 0x01)),   # a SECOND row-8 bit (SPACE)
    ("k4_none",      SAMPLER, None),        # nothing held -- must read none
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", body) for _, body, _ in CASES]
        holds = [h for _, _, h in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=10.0,
                                       holds=holds)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:160]}", flush=True)
            continue
        for (name, _, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("<J")
            j = txt.find(">", i + 1)
            cell = txt[i:j + 1] if i >= 0 and j > i else (
                "<Jnone>" if "<Jnone" in txt else "<no reading>")
            print(f"  {name:13} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
