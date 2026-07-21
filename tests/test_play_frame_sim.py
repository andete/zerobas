#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Emulator-free fast layer for the PLAY live servicer (audio Slice 3).

The openMSX gate (probes/basic/basic_probe_playtrace.py) proves play_service on real
hardware; this locks the same drain ALGORITHM without an emulator. It runs the parser
tenant on the host Z80 harness (reusing test_play_parse), then a Python model of
play_service -- the exact counter/fetch/rest/env/END logic of basic/playsvc.asm --
drains the resulting queues one frame at a time. We assert the per-frame PSG timeline
collapses to the note sequence mml_ref predicts, and that the servicer invariants hold:
a note occupies exactly `dur` VBLANKs with no gap, a rest keeps the prior tone period
(only the amplitude drops), OP_END silences the channel, and envelope notes carry amp
$10|volume. A regression in the drain model fails here in milliseconds.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import mml_ref  # noqa: E402
import test_play_parse as tp  # noqa: E402


def drain_sim(packets):
    """Model of play_service for one voice. `packets` = decode_queue output. Returns
    the per-frame (tone_period, amp5) timeline until the queue ends (amp 0 at END)."""
    cursor = 0
    counter = 0
    cur_tp = 0          # last tone period, persists across rests (period 0 packets)
    cur_amp = 0
    timeline = []
    done = False
    for _frame in range(100000):   # guard
        if not done and counter == 0:
            # fetch packet(s) this frame until a NOTE sets the counter, or END
            while True:
                pk = packets[cursor]
                if pk[0] == "END":
                    cur_amp = 0            # silence the channel
                    done = True
                    break
                if pk[0] == "ENV":
                    cursor += 1            # env consumes no frame -> keep fetching
                    continue
                # NOTE (op, period, amp, dur)
                _, per, amp, dur = pk
                if per != 0:               # rest = period 0 -> leave the tone regs
                    cur_tp = per
                cur_amp = amp
                counter = dur
                cursor += 1
                break
        if done:
            timeline.append((cur_tp, cur_amp))   # one silent frame marks the end
            break
        timeline.append((cur_tp, cur_amp))
        counter -= 1
    return timeline


def segments(timeline):
    """Collapse a per-frame timeline into (tone_period, amp, run_length) segments."""
    segs = []
    for s in timeline:
        if segs and segs[-1][0] == s:
            segs[-1] = (s, segs[-1][1] + 1)
        else:
            segs.append((s, 1))
    return [(tp, amp, n) for (tp, amp), n in segs]


FAILS = 0


def check(label, got, want):
    global FAILS
    ok = got == want
    FAILS += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {label:48} -> {got!r}"
          + ("" if ok else f"\n      want {want!r}"))


def voice_segments(mml):
    m, st = tp.parse([mml.encode()])
    assert st == 0, f"parse status {st} for {mml!r}"
    return segments(drain_sim(tp.decode_queue(m, 0)))


def run():
    tp.build()
    P = mml_ref.note_period
    F = mml_ref.note_frames
    C4, D4, E4 = 36, 38, 40   # note numbers (octave 4)

    # scale: three quarter notes, each dur = 25 @ T120, amp = volume 8
    check("O4L4CDE scale",
          voice_segments("O4L4CDE"),
          [(P(C4), 8, F(120, 4)), (P(D4), 8, F(120, 4)), (P(E4), 8, F(120, 4)),
           (P(E4), 0, 1)])

    # rest: the rest KEEPS the prior tone period, only amp drops to 0 (§2 gate-critical)
    check("O4L4CRC rest keeps period",
          voice_segments("O4L4CRC"),
          [(P(C4), 8, F(120, 4)), (P(C4), 0, F(120, 4)), (P(C4), 8, F(120, 4)),
           (P(C4), 0, 1)])

    # dotted quarter = 38 frames (ceil(base/2) added), then a plain quarter
    check("O4L4C.D dotted",
          voice_segments("O4L4C.D"),
          [(P(C4), 8, F(120, 4, 1)), (P(D4), 8, F(120, 4)), (P(D4), 0, 1)])

    # envelope note carries amp $18 = $10 | volume 8; period from the table
    check("O4L4S8M2000C envelope amp",
          voice_segments("O4L4S8M2000C"),
          [(P(C4), 0x18, F(120, 4)), (P(C4), 0, 1)])

    # tempo change: T240 quarter = 12 frames
    check("T240 quarter dur",
          voice_segments("T240O4L4C"),
          [(P(C4), 8, F(240, 4)), (P(C4), 0, 1)])

    print("\n" + (f"{FAILS} FAILED" if FAILS else
                  "ALL PASS — the play_service drain model is faithful"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(run())
