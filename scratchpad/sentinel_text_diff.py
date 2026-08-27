#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Does capturing on the SENTINEL change what a TEXT readout says? Three machines.

`scratchpad/sentinel_screen_diff.py` answered this for the GRAPHICS family
(`_points`): raw differs by the prompt, the answer is identical, teeth fire —
but 3 cases on 2 machines, and every answer was a VRAM point sample.

🔴 **THE TEXT FAMILY IS THE RISKY HALF AND WAS NOT COVERED.** The measurement
recorded in `omsx_repl.py` is that a raw screen taken when the program signals
is missing the `Ok`/`ZB` prompt — 2 characters — and the conclusion drawn there
is a RULE, not a blanket permission: *"a readout that already strips the prompt
is unaffected, and one that TERMINATES at the prompt (`screen_tail`) may not be
converted."* This measures that rule instead of quoting it.

FOUR COLUMNS, and the third is the one that licenses anything:

  raw            expected to DIFFER (the prompt). Shown, not asserted — if it
                 ever came back identical the sentinel did not fire and the run
                 measured nothing.
  span           `result_span_after_echo`, which strips the prompt. THE CLAIM.
  tail           `screen_tail`, which TERMINATES at the prompt. Expected to be
                 the one that breaks; measuring it is the point.
  TEETH          two cases whose spans MUST differ, or a 0-DIFF tally is vacuous.

🎯 **AND ONE CASE NEVER REACHES ITS `POKE`.** An erroring program cannot signal,
so the fixed-time schedule must still fire as the FALLBACK and the answer must
still be right. That is the path the filed item calls *"no bound needed unless
there is a test or harness failure"*, and it is asserted here rather than
assumed.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SENTINEL = (0xE000, 255)
# 🔴 THE CF-3300 NEEDS ITS OWN RESET. The first run gave it ("NEW","CLS") like
# the others and every one of its spans came back None -- four rows of "same"
# that were agreeing on NOTHING, in a run that exited 0. Disk BASIC boots into a
# different screen state; every probe in probes/basic/ that drives it uses
# ("", "SCREEN 0", "NEW") and this one now does too.
SIDES = [("vg8020", "Philips_VG_8020", 8.0, 2.5, ("NEW", "CLS")),
         ("cf3300", "National_CF-3300", 14.0, 4.5, ("", "SCREEN 0", "NEW", "CLS")),
         ("zb", os.environ.get("ZEROBAS_BASIC_MACHINE",
                               "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, 2.5,
          ("NEW", "CLS"))]

# (label, body lines WITHOUT the poke, signals?)  -- the poke is appended below
CASES = [
    ("value",  ['10 A=6*7', '20 PRINT"[";A;"]"'],                     True),
    ("string", ['10 A$="ZB"', '20 PRINT"[";A$;"]"'],                  True),
    ("forloop", ['10 S=0', '20 FOR I=1 TO 10:S=S+I:NEXT',
                 '30 PRINT"[";S;"]"'],                                True),
    # 🎯 errors BEFORE the poke -> the sentinel can never fire. 🔴 ITS READOUT
    # CANNOT BE A SPAN: the program dies before printing one, so both sides
    # return None and "identical" is agreeing on nothing -- which is exactly how
    # the first run reported 3/3 FALLBACK on no evidence at all. The error case
    # is scored on its MESSAGE instead (see `err_text`).
    ("error",  ['10 PRINT"[";1/0;"]"'],                               False),
]


def prog(lines, signals, poke):
    out = list(lines)
    if poke and signals:
        out.append(f"{(len(lines)+1)*10} POKE &H{SENTINEL[0]:04X},{SENTINEL[1]}")
    out.append("RUN")
    return out


def err_text(raw):
    """The error message row, if any -- the only reading an aborted case has."""
    if raw is None:
        return None
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hits = [r for r in rows if "rror" in r or "Division" in r]
    return hits[-1] if hits else None


def run(machine, boot, step, reset, lines, use_sentinel):
    kw = dict(boot=boot, step=step, reset=reset)
    if use_sentinel:
        kw.update(sentinel=SENTINEL, sentinel_capture=True)
    raw = omsx_repl.run_cases(machine, [("c", lines)], **kw)
    return raw[0]


def main():
    rows, bad, blind = [], 0, []
    spans = {}
    for label, body, signals in CASES:
        for side, machine, boot, step, reset in SIDES:
            fixed = run(machine, boot, step, reset, prog(body, signals, False), False)
            sent = run(machine, boot, step, reset, prog(body, signals, True), True)
            f_raw, s_raw = fixed or "", sent or ""
            if signals:
                f_span = omsx_repl.result_span_after_echo(fixed, "RUN")
                s_span = omsx_repl.result_span_after_echo(sent, "RUN")
            else:                       # aborted case: score the MESSAGE
                f_span, s_span = err_text(fixed), err_text(sent)
            f_tail = omsx_repl.screen_tail(fixed, "RUN")
            s_tail = omsx_repl.screen_tail(sent, "RUN")
            spans[(label, side)] = f_span
            rows.append((label, side,
                         "same" if f_raw == s_raw else "differs",
                         "same" if f_span == s_span else "DIFF",
                         "same" if f_tail == s_tail else "DIFF",
                         f_span, s_span))
            if f_span != s_span:
                bad += 1
            if f_span is None:
                blind.append((label, side))
    print(f"{'case':9s} {'side':8s} {'raw':9s} {'span':6s} {'tail':6s}  fixed -> sentinel")
    for label, side, raw, span, tail, fs, ss in rows:
        print(f"{label:9s} {side:8s} {raw:9s} {span:6s} {tail:6s}  {fs!r} -> {ss!r}")

    t1, t2 = spans.get(("value", "zb")), spans.get(("string", "zb"))
    teeth = t1 != t2
    print(f"\n  TEETH (value vs string spans must differ): "
          f"{'✅ they do' if teeth else '🔴 THEY DO NOT'}  {t1!r} vs {t2!r}")
    if not teeth:
        print("  INSTRUMENT FAULT: the readout cannot separate two cases, so "
              "every 'same' above is vacuous.")
        return 2
    if blind:
        print(f"  🔴 {len(blind)} row(s) produced NO READING on the fixed side, "
              f"so their 'same' is agreeing on nothing: {blind}")
        print("  INSTRUMENT FAULT: fix the readout before believing the tally.")
        return 2
    err = [r for r in rows if r[0] == "error"]
    print(f"  FALLBACK (the erroring case never pokes, so the sentinel CANNOT "
          f"fire): {sum(1 for r in err if r[3] == 'same')}/{len(err)} error "
          f"messages identical -- the fixed-time schedule still fired and still "
          f"read the right thing")
    print(f"\n=== spans differing under sentinel capture: {bad} of {len(rows)} ===")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
