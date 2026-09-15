# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Shared MML oracle for the audio Slice-2a parser (docs/spec-basic-audio-play-slice2a.md).

SINGLE SOURCE OF TRUTH for the two own-design numeric mappings the parser bakes:
  * note number -> 12-bit PSG tone period  (note_period)
  * (tempo, length) -> interrupt-frame count  (note_frames)

The tenant asm (sub/playparse.asm) embeds a 96-entry period table + the same
integer frame formula; this module GENERATES that table (emit_period_table) so the
asm and the host decoder (tests/test_play_parse.py) can never drift, and computes
the exact expected packet bytes the decoder asserts against.

Provenance: the note-frequency relation (equal temperament, A4=440) and the PSG
tone-period relation TP = f_psg/(16*f) are public (AY-3-8910 datasheet / MSX PSG
docs). The BASE=14400 tempo constant and the rounding are OWN-DESIGN (a documented
deviation; the exact constant that matches the VG-8020 music speed is tuned in
Slice 3's frame-trace differential). No stock-ROM disassembly.
"""

# PSG tone clock: MSX master 3.579545 MHz / 2 = 1.7897725 MHz, tone = clk/(16*TP).
PSG_TONE_CLK = 3579545 / 2.0
# Tempo baseline: frames = BASE // (T*L), floor. Empirically pinned against the
# VG-8020 (docs/audio-slice3-characterization.md §1): quarter @ T120 = 25 frames,
# verified exact on 8 T/L points. BASE = 240 * 50 = 12000 -> on PAL/50 Hz tempo T
# equals BPM (quarter @ T120 = 0.5 s). The frame *count* is Hz-independent (the ISR
# counts VBLANKs), so no NTSC branch. Corrects the earlier 14400 half-up guess on
# BOTH axes: constant 14400->12000 AND rounding half-up->floor.
FRAME_BASE = 12000

# MML note numbering used by the parser: N = (octave-1)*12 + semitone, octave 1..8,
# semitone 0=C .. 11=B. 97 entries, index 0 = C1 .. 95 = B8, and 96 = C9.
# 🔴 ENTRY 96 IS REACHED ONLY BY `N96`. The MML `N n` command is ONE-BASED
# against this same array -- `N1` is index 1 (C#1), `N96` is index 96 -- so it runs a
# semitone above the letter-note range, and its top note needs a row the letters
# never ask for. Measured on both references 2026-09-15 (D-KWPLAY).
NOTE_MIN, NOTE_MAX = 0, 96


# The VG-8020's actual 96-note PSG tone-period table, BLACK-BOX MEASURED per-VBLANK
# (docs/audio-slice3-characterization.md; probes/lib/psgtrace.py). This is the
# ground truth the asm table + host decoder must match: the reference does NOT equal
# round(PSG_TONE_CLK/(16*f)) on the equal-tempered frequency (9 of 96 differ by 1 --
# e.g. B4 measures 227 where the exact formula rounds to 226; 226.49 rounds UP on the
# reference, which no single round/floor/ceil reproduces). Measuring the values is
# clean-provenance (black-box PSG observation, NOT stock-ROM disassembly, exactly like
# the frame-tempo constant). Index n = (octave-1)*12 + semitone, 0 = C1 .. 95 = B8.
REF_PERIODS = [
    3421, 3228, 3047, 2876, 2715, 2562, 2419, 2283, 2155, 2034, 1920, 1812,   # O1
    1711, 1614, 1524, 1438, 1358, 1281, 1210, 1142, 1078, 1017,  960,  906,   # O2
     855,  807,  762,  719,  679,  641,  605,  571,  539,  509,  480,  453,   # O3
     428,  404,  381,  360,  339,  320,  302,  285,  269,  254,  240,  227,   # O4
     214,  202,  190,  180,  170,  160,  151,  143,  135,  127,  120,  113,   # O5
     107,  101,   95,   90,   85,   80,   76,   71,   67,   64,   60,   57,   # O6
      53,   50,   48,   45,   42,   40,   38,   36,   34,   32,   30,   28,   # O7
      27,   25,   24,   22,   21,   20,   19,   18,   17,   16,   15,   14,   # O8
      13,                                                                      # C9
]


def note_period(n):
    """note number 0..96 -> 12-bit PSG tone period, the VG-8020-measured value."""
    return REF_PERIODS[max(0, min(NOTE_MAX, n))]


def note_frames(tempo, length, dots=0, tie_frames=0):
    """(tempo 32..255, length 1..64, dots) -> interrupt-frame count (>=1).

    frames = BASE // (tempo*length), floor. Dots (VG-8020-pinned, §1): the FIRST
    dot adds ceil(base/2); each subsequent dot adds floor of the running addend
    (base=25 -> +13 -> +6: L4.=38, L4..=44; base=12 -> +6: L8.=18). Matches the asm
    exactly (integer arithmetic); the asm realises 'ceil first, floor after' with a
    single `inc de` before the halving loop."""
    tl = tempo * length
    fr = FRAME_BASE // tl                       # floor divide
    if dots:
        add = (fr + 1) // 2                      # first dot: ceil(base/2)
        fr += add
        for _ in range(dots - 1):
            add //= 2                            # subsequent dots: floor of running addend
            fr += add
    fr += tie_frames
    return max(1, fr)


def emit_period_table():
    """asm `dw` lines for the 97-entry NOTE_PERIOD table (paste into the tenant).

    The last row is RAGGED -- 97 is not a multiple of 8 -- because entry 96 (C9)
    exists for `N96` alone; see REF_PERIODS."""
    out, n = [], len(REF_PERIODS)
    for base in range(0, n, 8):
        vals = ", ".join(f"${note_period(base + i):04X}"
                         for i in range(min(8, n - base)))
        out.append(f"                dw      {vals}")
    return "\n".join(out)


if __name__ == "__main__":
    print("; NOTE_PERIOD: note number (octave-1)*12+semitone, 0=C1 .. 95=B8")
    print(emit_period_table())
