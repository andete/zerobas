#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWPLAY scout: can a kwsweep row SEE an MML form? `PLAY` is 0/11 forms.

`PLAY(n)` -- the instrument `make play-acceptance` uses -- answers only "is this
voice sounding", so it can separate MULTI-VOICE from the rest and nothing else.
Ten of the eleven authored forms (tools/kwforms.py "PLAY") change the PITCH, the
VOLUME, the ENVELOPE or the DURATION of a note, and none of those is a voice
mask. This scout asks whether the PSG itself answers instead: the data-read port
is $A2 after latching the register on $A0 (docs/spec-basic-audio-play.md
"PSG I/O ports"), and the drain writes the PSG live from the timer interrupt.

  c0   THE CONTROL, and it is the FIRST thing to read. `SOUND 0,200` then read
       R0 back. If this is not 200 the read-back does not work and NOTHING else
       below is a verdict -- not even a divergence.
  c1   plain `C` at the default octave: R0/R1 = channel A tone period.
  c2   `O2C` -- two octaves down, so the period must be ~4x c1's.
  c3   `>C` -- the shift, one octave UP from the default, so ~half c1's.
  c4   `N40` -- the note-number form, which must land on its own period.
  c5   `V3C` -- R8 is channel A amplitude.
  c6   `R1` alone -- a REST: is the channel silent (R8=0) while it rests?
  c7   `S10M2000C` -- R13 envelope shape, R11/R12 envelope period, and R8 bit 4
       (=16) is "use the envelope instead of the amplitude".
  c8   DURATION, the only instrument left for `L` and `T`: play a very SHORT
       note and a very LONG one, wait the SAME wait, and read `PLAY(0)` after
       each. 0 then -1 is the reading; anything else means the wait does not sit
       between the two durations on this machine.
  c9   `T` the same way -- same note length, tempos 255 and 32.
  c10  `X<var>;` substring execution, with an octave inside it so its period
       cannot be confused with c1's.

⚠️ THE WAIT IS `FOR`, WHICH IS INTERPRETER SPEED, AND THE REFERENCE IS ~3x
FASTER. That is survivable ONLY because c8/c9 are RATIO tests: the wait has to
land between ~30 ms and ~2 s on BOTH machines, which is a wide gate. A row that
compared an ABSOLUTE frame count would not survive it.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

SETTLE = "FOR I=1 TO 200:NEXT"


def rd(regs: str) -> list[str]:
    """One numbered line PER register: each must stay inside the 34-char body
    budget `omsx_repl.as_stored` documents, and four of them joined does not."""
    return ["OUT&HA0,%s:PRINT INP(&HA2);" % r for r in regs.split(",")]


def prog(setup: str, regs: str) -> list[str]:
    """`ON ERROR` targets the LAST line, whose number is 10 x len(lines) --
    computed, never written down, because `regs` changes the line count."""
    body = [None, setup, SETTLE, 'PRINT"<";'] + rd(regs) + ['PRINT">":END',
            'PRINT"<E";ERR;">":END']
    body[0] = "ON ERROR GOTO %d" % (10 * len(body))
    return body


CASES = [
    ("c0_control",  prog("SOUND 0,200:SOUND 1,1", "0,1")),
    ("c1_note",     prog('PLAY"L1C"',             "0,1")),
    ("c2_octave",   prog('PLAY"O2L1C"',           "0,1")),
    ("c3_shift",    prog('PLAY"L1>C"',            "0,1")),
    ("c4_notenum",  prog('PLAY"L1N40"',           "0,1")),
    ("c5_volume",   prog('PLAY"V3L1C"',           "8")),
    ("c6_rest",     prog('PLAY"L1R"',             "7,8")),
    ("c7_env",      prog('PLAY"S10M2000L1C"',     "8,11,12,13")),
    ("c10_xexec",   prog('A$="O7L1C":PLAY"XA$;"', "0,1")),
]

# the two DURATION rows print their own reading, so they do not use `prog`
DUR = [
    ("c8_length", ["ON ERROR GOTO 90",
                   'PLAY"L64CDEFGAB"', SETTLE, "A=PLAY(0)",
                   'PLAY"L1CDEFGAB"', SETTLE, "B=PLAY(0)",
                   'PRINT"<";A;B;">":END',
                   'PRINT"<E";ERR;">":END']),
    ("c9_tempo", ["ON ERROR GOTO 90",
                  'PLAY"T255L64CDEFGAB"', SETTLE, "A=PLAY(0)",
                  'PLAY"T32L1CDEFGAB"', SETTLE, "B=PLAY(0)",
                  'PRINT"<";A;B;">":END',
                  'PRINT"<E";ERR;">":END']),
]


def main() -> int:
    cases = CASES + DUR
    for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in cases]
        raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=8.0)
        for (name, _), raw in zip(cases, raws):
            txt = " ".join("".join(raw or "").split())
            # \U0001f534 THE FENCE IS IN THE SOURCE TOO. `PRINT"<";` echoes as the
            # program is typed, so a scan from the LEFT finds the LISTING, not the
            # run. Everything that is a READING sits after the final `RUN`.
            r = txt.rfind("RUN")
            tail = txt[r + 3:] if r >= 0 else txt
            i = tail.find("<")
            j = tail.find(">", i + 1)
            cell = tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:40]
            print(f"  {name:12} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
