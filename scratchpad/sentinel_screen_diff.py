#!/usr/bin/env python3
"""Does capturing on the SENTINEL change what a SCREEN readout says?

The `capture="screen"` refusal was lifted on the user's decision (2026-08-25).
The measurement behind it stands -- a RAW screen taken when the program signals
is missing the `Ok`/`ZB` prompt, 2 characters, on all three machines -- but the
readouts already strip exactly that. This is the differential that has to carry
the change, and it is deliberately built to be able to FAIL:

  * RAW column      -- expected to differ by the prompt. Shown, not asserted.
                       If it ever came back identical, the sentinel did not fire
                       and the run is measuring nothing.
  * ANSWER column   -- the probe's OWN readout (`_answer`/`_points`). THIS is the
                       claim: adoption is only justified where this is identical.
  * TEETH           -- two cases whose answers MUST differ. A 0-DIFF tally over
                       rows that cannot disagree is vacuous
                       [[a-case-that-agrees-can-agree-for-the-wrong-reason]].

⚠️ Adoption needs the case to POKE the sentinel itself, so every program here
gets one appended before its END -- which is the real cost of the change and is
why this measures the shape probes would actually ship.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                   # noqa: E402
import basic_probe_graphics as g                                   # noqa: E402

MARK = 0xE000
SIDES = [("ref", g.REF), ("zb", g.ZB)]

# (label, setup lines, POINT sample list) -- PHASE H's own shape.
CASES = [
    ("flood",        ["PAINT(128,96),15"], [(128, 96), (129, 96)]),
    ("box_bounded",  ["LINE(20,20)-(60,60),7,B", "PAINT(30,30),7,7"],
     [(30, 30), (10, 10)]),
    ("circle_fill",  ["CIRCLE(128,96),40,15", "PAINT(128,96),15"],
     [(128, 96), (10, 10)]),
]


def prog(setup, pts, poke: bool):
    """paint_points_prog, plus the sentinel POKE the case must make itself."""
    lines = g.paint_points_prog(setup, pts)
    if poke:
        # after the readout is PRINTed, before END: the screen is final here.
        lines[-1] = lines[-1].replace(":END", f":POKE&H{MARK:04X},255:END")
    return lines


def run(machine, lines, pts, sentinel):
    kw = dict(batch=False, run_gap=g.PAINT_STEP, cap_gap=g.PAINT_CAP_GAP,
              timeout=g.PAINT_TIMEOUT)
    if sentinel:
        kw.update(sentinel=(MARK, 255), sentinel_capture=True)
    raw = omsx_repl.run_cases(machine, [("stored", lines)], **kw)[0]
    return raw, g._points(raw, len(pts))


def main():
    print(f"{'case':<14} {'side':<5} {'raw':<10} {'answer':<10} verdict")
    bad = 0
    answers = {}
    for label, setup, pts in CASES:
        for side, machine in SIDES:
            a_raw, a_ans = run(machine, prog(setup, pts, False), pts, False)
            b_raw, b_ans = run(machine, prog(setup, pts, True), pts, True)
            raw_same = (a_raw or "") == (b_raw or "")
            ans_same = a_ans == b_ans and a_ans is not None
            bad += not ans_same
            answers[(label, side)] = a_ans
            print(f"{label:<14} {side:<5} "
                  f"{'same' if raw_same else 'differs':<10} "
                  f"{'same' if ans_same else 'DIFFERS':<10} "
                  f"{'✅' if ans_same else '🔴'}  fixed={a_ans} sentinel={b_ans}")
            if raw_same:
                print("    ⚠️ RAW IDENTICAL -- the sentinel may not have fired; "
                      "this row proves nothing")
    # TEETH: the readout must be able to tell these cases apart at all.
    t1, t2 = answers.get(("flood", "zb")), answers.get(("box_bounded", "zb"))
    teeth = t1 is not None and t2 is not None and t1 != t2
    print(f"\n  TEETH (flood vs box_bounded must differ): "
          f"{'✅ they do' if teeth else '🔴 VACUOUS -- these rows cannot disagree'}"
          f"  {t1} vs {t2}")
    print(f"\n=== answers differing under sentinel capture: {bad} ===")
    return 1 if (bad or not teeth) else 0


if __name__ == "__main__":
    raise SystemExit(main())
