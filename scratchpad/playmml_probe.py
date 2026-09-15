#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWPLAY scout 2 -- three questions scratchpad/playpsg_probe.py raised.

Scout 1 proved the instrument: `OUT&HA0,r` then `INP(&HA2)` reads the PSG back
LIVE while music plays, and the control (`SOUND 0,200` -> 200) agreed on both
machines. R0/R1 (tone), R7 (mixer), R11/R12 (envelope period) then agreed
EXACTLY between the reference and this tree. Three things did not:

  A. R8 AND R13 DISAGREE IN THEIR HIGH BITS ONLY. `V3` reads 3 here and 131
     (=$83) on the VG-8020; `S10` reads 10 here and 218 (=$DA) there. The LOW
     nibble is right in both cases, so the question is whether those high bits
     are STABLE (a read-back width difference -- mask and move on) or NOISE (a
     race against the drain, which writes the PSG from the interrupt -- in which
     case no volume/envelope row can be trusted on either machine). d0..d3 read
     the same register THREE TIMES in one run: three equal readings say stable,
     three different ones say racing.

  B. `>` AND `X<var>;` RAISE ERR 5 ON THE REFERENCE AND WORK HERE. Both are
     authored as forms in tools/kwforms.py from docs/spec-basic-audio-play.md
     2.2. If the VG-8020 refuses them they are NOT MSX1 MML, the PLAY bar is
     overstated, and this tree ACCEPTS TWO COMMANDS THE REFERENCE REJECTS --
     the opposite direction from a missing feature, and a defect either way.
     d4..d9 vary the spelling (spaces, `<` as well as `>`, a two-letter variable)
     so the verdict is about the COMMAND and not about one way of typing it, and
     the CF-3300 answers alongside so one reference is not the whole claim.

  C. THE DURATION ROWS MEASURED THE `FOR` LOOP. `L64` had finished here and was
     still sounding on the reference -- which is ~3x faster, so the same 200
     iterations are a SHORTER wait there. d10/d11 wait 40 FRAMES via `TIME`
     instead, which is the same wall-clock on any machine, and separate `L`
     from `T` by holding the other one fixed.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK",)   # the VG-8020 column is in scout 2 run 1;
# 🔴 THE CF-3300 IS NOT HERE: boot-per-case delivery to it was MANGLED ("machine
# stored <none>"), which is an APPARATUS failure and not a reading. `make kwsweep`
# reaches that machine through its own boot path, so the rows will answer there.


def thrice(setup: str, reg: str) -> list[str]:
    """10..80: run `setup`, settle, then read ONE register three times."""
    return ["ON ERROR GOTO 80",
            setup,
            "FOR I=1 TO 200:NEXT",
            'PRINT"<";',
            "OUT&HA0,%s:PRINT INP(&HA2);" % reg,
            "OUT&HA0,%s:PRINT INP(&HA2);" % reg,
            "OUT&HA0,%s:PRINT INP(&HA2);" % reg,
            'PRINT">":END',
            'PRINT"<E";ERR;">":END']
    # NOTE: nine lines, so the trap is line 90 -- fixed below.


def thrice_fixed(setup: str, reg: str) -> list[str]:
    b = thrice(setup, reg)
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b


def tone(setup: str) -> list[str]:
    """Does this MML run at all, and to what tone period?  `<E n >` = trapped."""
    b = ["ON ERROR GOTO 0",
         setup,
         "FOR I=1 TO 200:NEXT",
         'PRINT"<";',
         "OUT&HA0,0:PRINT INP(&HA2);",
         "OUT&HA0,1:PRINT INP(&HA2);",
         'PRINT">":END',
         'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b


def dur(first: str, second: str) -> list[str]:
    """Play a SHORT phrase, wait 40 FRAMES, read `PLAY(0)`; then a LONG one.

    \U0001f534 THE WAIT IS FRAMES, NOT ITERATIONS. `TIME` advances 60 times a
    second on every MSX, so the same 40 counts the same two-thirds of a second
    on the reference and here; a `FOR` loop does not, and that is exactly what
    made scout 1's duration rows disagree for a reason that was not PLAY."""
    return ["ON ERROR GOTO 100",
            first,
            "T=TIME",
            "IF TIME-T<40 THEN 40",
            "A=PLAY(0)",
            second,
            "T=TIME",
            "IF TIME-T<40 THEN 80",
            'B=PLAY(0):PRINT"<";A;B;">":END',
            'PRINT"<E";ERR;">":END']


CASES = [
    # A -- is the high-bit disagreement stable or racing?
    ("d0_vol3x",   thrice_fixed('PLAY"V3L1C"',        "8")),
    ("d1_env3x",   thrice_fixed('PLAY"S10M2000L1C"', "13")),
    ("d2_vol15",   thrice_fixed('PLAY"V15L1C"',       "8")),
    ("d3_r8plain", thrice_fixed('PLAY"L1C"',          "8")),
    # B -- are `>`/`<` and `X<var>;` MSX1 MML at all?
    ("d4_gt",      tone('PLAY"L1>C"')),
    ("d5_gt_sp",   tone('PLAY"L1 > C"')),
    ("d6_lt",      tone('PLAY"O5L1<C"')),
    ("d7_x1",      tone('A$="O7L1C":PLAY"XA$;"')),
    ("d8_x_sp",    tone('A$="O7L1C":PLAY"X A$;"')),
    ("d9_x2",      tone('AB$="O7L1C":PLAY"XAB$;"')),
    # C -- duration, waited in FRAMES
    ("d10_length", dur('PLAY"L64CDEFGAB"', 'PLAY"L2CDEFGAB"')),
    ("d11_tempo",  dur('PLAY"T255L16CDEFGAB"', 'PLAY"T32L16CDEFGAB"')),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=8.0)
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            r = txt.rfind("RUN")                 # the fence is in the LISTING too
            tail = txt[r + 3:] if r >= 0 else txt
            i = tail.find("<")
            j = tail.find(">", i + 1)
            cell = tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:40]
            print(f"  {name:11} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
