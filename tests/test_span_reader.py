# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the span reader's `why` channel — four Nones, four reasons.

🔴 `result_span` RETURNS `None` FOR FOUR DIFFERENT SITUATIONS and a caller
cannot tell them apart: nothing captured, no `[` anywhere, a `[` with no `]`,
and (in `result_span_after_echo`) no echo row to search after. The consequence is
recorded in TODO.md by D-NAMBLANK: a payload that prints NO BRACKETS reads `None`
on EVERY side, and sides that all failed compare EQUAL and report *agrees*.
`basic_probe_lnblank.py`'s `dir-print` sat in exactly that state from the day it
was written.

🎯 The cure is the one this tree already uses for `_why_missing` and
D-PASMOSAY: hand back the evidence instead of throwing it away. `why` is an
out-parameter dict, the same idiom `run_cases` uses for `settle_out`, so every
existing caller is untouched -- the return contract does not change.

⚠️ THESE ARMS ARE HERE RATHER THAN IN `omsx_repl --selftest` ON PURPOSE. That
entry point takes a MACHINE and boots an emulator (`tools/check_selftests.py`
excuses it from the static gate for exactly that reason), so arms added there
would not be gated by anything cheap. This file runs under `make unit-test`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))

import omsx_repl  # noqa: E402

COLS = omsx_repl.COLS


def screen(*rows):
    """A capture is the SCREEN: one string, COLS to a row, no newlines."""
    return "".join(r.ljust(COLS)[:COLS] for r in rows)


def run():
    fails = 0

    def check(ok, label, detail=""):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:56}" + ("" if ok else f"  {detail}"))

    # --- result_span: one arm per reason, and the VALUE arm too --------------
    for label, raw, want_val, want_key in [
        ("a printed value reads back", "noise [ 7 ] more", " 7 ", "ok"),
        ("no '[' anywhere", "nothing printed here", None, "NO BRACKETS"),
        ("'[' with no ']'", "oops [ 7", None, "aborted mid-PRINT"),
        ("no capture at all", None, None, "no capture"),
    ]:
        why = {}
        got = omsx_repl.result_span(raw, why)
        r = why.get("reason", "")
        check(got == want_val and want_key.lower() in r.lower(),
              f"result_span: {label}", f"got {got!r} why={r!r}")

    # 🔴 THE ARM THAT MATTERS: the two failing shapes must not share a reason,
    # because "the payload cannot produce a reading" and "the machine aborted"
    # are the two things D-NAMBLANK found conflated.
    w1, w2 = {}, {}
    omsx_repl.result_span("nothing printed here", w1)
    omsx_repl.result_span("oops [ 7", w2)
    check(w1["reason"] != w2["reason"],
          "a bracketless payload and an abort give DIFFERENT reasons",
          f"{w1['reason']!r} vs {w2['reason']!r}")

    # --- result_span_after_echo: the reason only it can give -----------------
    cap = screen("Ok", "PRINT\"[\";7;\"]\"", "[ 7 ]", "Ok")
    why = {}
    got = omsx_repl.result_span_after_echo(cap, 'PRINT"[";7;"]"', why)
    check(got == " 7 " and why.get("reason") == "ok",
          "after_echo: reads the value printed below the echo",
          f"got {got!r} why={why.get('reason')!r}")

    why = {}
    got = omsx_repl.result_span_after_echo(cap, "SOMETHING ELSE", why)
    check(got is None and "echo row" in why.get("reason", ""),
          "after_echo: a missing echo row says so, as an INSTRUMENT result",
          f"got {got!r} why={why.get('reason')!r}")

    # 🟢 THE COMPATIBILITY ARM. Every existing caller passes no `why`, and
    # must keep working unchanged -- this is what makes the change additive.
    check(omsx_repl.result_span("x [ 9 ] y") == " 9 "
          and omsx_repl.result_span("no brackets") is None
          and omsx_repl.result_span_after_echo(cap, 'PRINT"[";7;"]"') == " 7 ",
          "callers that pass no `why` are completely unaffected")

    print()
    print("ALL PASS — every `None` from the span reader now names its reason"
          if not fails else f"{fails} CHECK(S) FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
