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
# Tempo baseline: frames-per-whole-note = BASE / T. T=120,L=4 (quarter) -> 30
# frames = 0.5 s at 60 Hz. BASE = 60 fps * 240 = 14400 (60 Hz baseline; Slice 3
# tunes for PAL/NTSC against the reference).
FRAME_BASE = 14400

# MML note numbering used by the parser: N = (octave-1)*12 + semitone, octave 1..8,
# semitone 0=C .. 11=B. 96 entries, index 0 = C1 .. 95 = B8.
NOTE_MIN, NOTE_MAX = 0, 95


def note_period(n):
    """note number 0..95 -> 12-bit PSG tone period (clamped to 1..4095)."""
    # frequency of note n: A4 (440 Hz) is octave 4, semitone 9 -> global index 3*12+9=45.
    semis_from_a4 = n - 45
    freq = 440.0 * (2.0 ** (semis_from_a4 / 12.0))
    tp = round(PSG_TONE_CLK / (16.0 * freq))
    return max(1, min(4095, tp))


def note_frames(tempo, length, dots=0, tie_frames=0):
    """(tempo 32..255, length 1..64, dots) -> interrupt-frame count (>=1).

    frames = BASE / (tempo*length), integer half-up; each dot adds half of the
    running value; a preceding tie adds tie_frames. Matches the asm exactly
    (integer arithmetic, no float round)."""
    tl = tempo * length
    fr = (FRAME_BASE + tl // 2) // tl          # half-up integer divide
    add = fr
    for _ in range(dots):
        add //= 2
        fr += add
    fr += tie_frames
    return max(1, fr)


def emit_period_table():
    """asm `dw` lines for the 96-entry NOTE_PERIOD table (paste into the tenant)."""
    out = []
    for base in range(0, 96, 8):
        vals = ", ".join(f"${note_period(base + i):04X}" for i in range(8))
        out.append(f"                dw      {vals}")
    return "\n".join(out)


if __name__ == "__main__":
    print("; NOTE_PERIOD: note number (octave-1)*12+semitone, 0=C1 .. 95=B8")
    print(emit_period_table())
