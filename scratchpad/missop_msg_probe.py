#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-MISSOPMSG — the entry's premise is falsified; this reads what actually prints.

The `SAVE`/`LOAD`/`BLOAD`-with-no-argument item says *"zerobas has no `Missing
operand` message at all"* and therefore that only the WORDING is outstanding.
That sentence was true when it was filed (2026-08-21) and is **not true today**:
[`sub/errmsg.asm`](sub/errmsg.asm):231 carries

    em_missing_operand: db  "Missing operand",0             ; ERR 24

reached by `sub/circleparse.asm`'s `cpt_err24`, which landed after the filing.
🔴 **AND TWO LIVE READINGS DISAGREE ABOUT WHAT THAT MEANS.**

  * `scratchpad/missop_err_probe.py` (D-MISSOPERR, 2026-09-04) reads **ERR 24**
    for bare `SAVE`/`LOAD`/`BLOAD` on all three machines, and the TODO entry
    concluded from it that "the disposition really is closed".
  * `probes/basic/basic_probe_namspc.py`'s DEFERRED note says those same three
    rows read `Missing operand` on the CF-3300 and **`Syntax error` here**.

Both cannot be right about the same build. A code and a message are different
questions and the entry answered only the first
[[a-justification-parenthesis-is-an-unrun-claim]].

## What this reads

`screen_tail` — the literal rows the machine prints — for three questions kept
apart on purpose, because collapsing them is how the contradiction survived:

  q.<verb>   what the three FILED verbs print
  d.err24    what `ERROR 24` prints, which asks the MESSAGE TABLE and nothing
             else: if this reads `Missing operand` here, the table is wired and
             any `Syntax error` above is about which code the VERB raises
  d.err2     CONTROL: `ERROR 2`, a message all three certainly have, so a row
             reading `Syntax error` cannot be the instrument defaulting
  c.ok       CONTROL: no error at all — must print nothing

⚠️ A `<NO TAIL>` is an instrument result, never a machine one: it means the echo
row was not found, and it is reported as itself rather than folded into "no
message" [[an-unnamed-outcome-reads-as-no-outcome]].
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW",)),
}
CASES = [
    ("q.save",   "SAVE",     "the filed row n.savebare"),
    ("q.load",   "LOAD",     "the filed row n.loadbare"),
    ("q.bload",  "BLOAD",    "the filed row n.bloadbare"),
    ("q.let",    "A$=",      "D-MISS-1's LET mirror"),
    ("q.letop",  "A$=+",     "the mirror that reads ERR 2 here against 24 there"),
    ("d.err24",  "ERROR 24", "🎯 the MESSAGE TABLE alone -- no verb involved"),
    ("d.err2",   "ERROR 2",  "CONTROL: a message all three certainly have"),
    ("c.ok",     "A=1",      "CONTROL: no error -- must print nothing"),
]


def run(side, stmt):
    machine, boot, reset = SIDES[side]
    raw = omsx_repl.run_cases(machine, [("direct", list(reset) + [stmt])],
                              batch=False, reset=(), boot=boot, step=6.0,
                              cap_gap=10.0, timeout=300.0)[0]
    t = omsx_repl.screen_tail(raw, stmt)
    if t is None:
        return "<NO TAIL>"
    return " ".join(t.split()) or "<EMPTY>"


def main():
    w = 9
    print(f"\n{'row':<{w}} {'vg8020':<22} {'cf3300':<22} {'zb':<22}  statement")
    for lab, st, why in CASES:
        v = [run(s, st) for s in ("vg8020", "cf3300", "zb")]
        tag = "refs agree" if v[0] == v[1] else "🔴 REFS SPLIT"
        zb = "" if v[1] == v[2] else "  🔴 zb DIFF"
        print(f"{lab:<{w}} {v[0]:<22} {v[1]:<22} {v[2]:<22}  {st:<9} {tag}{zb}  {why}")
    print("\nread d.err24 FIRST: it separates 'the table lacks the message' from "
          "'the verb raises a different code'.")


if __name__ == "__main__":
    raise SystemExit(main())
