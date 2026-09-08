#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TIERSCOPE — is the review tier's worklist actually scoped over all 133 handlers?

`docs/review-tier-worklist.md` opens with a claim nobody had checked:

    Denominator: 133 ex_/ev_f_ handlers; 48 have a same-named spec, 85 do not.
    The 85 are NOT 85 holes -- most are covered under ARC names.

It then lists 24 entries. Twenty-four entries against 133 handlers looks like a
hole, and after a night in which two entries that CLAIMED coverage turned out to
hide six and two divergences (D-RAWVAL, D-SAVETRAP), the claim is worth a
measurement rather than a reading.

This attributes every handler in `basic/` to the worklist three ways, weakest
last, because a raw label match badly overstates the gap -- the worklist groups in
prose ("field.asm / files.asm (close/files/kill/merge/name)"), so `ex_close` is
scoped without its label ever appearing:

  * LABEL -- the handler's own name occurs in the worklist
  * VERB  -- its BASIC verb occurs as a whole word
  * FILE  -- its source file is named

\U0001f534 AND WHAT THIS MEASURES IS SCOPING, NOT QUALITY. Named coverage can still
miss the axis that matters: `ex_out`/`ex_poke`/`ex_vpoke` were named, reviewed AND
recorded as a no-finding, and had six divergences in an argument position the
cited table could not express [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
A handler passing this sweep is IN SCOPE, not correct.

FALSIFICATION: `--selftest` asserts a handler the worklist names is reported
named, and that a handler absent from it is reported unattributed -- so "0
unattributed" cannot be a sweep that matched everything by accident.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
WORKLIST = "docs/review-tier-worklist.md"

# Handlers whose BASIC verb is not derivable from the label. Only entries that
# add information are listed; the rest fall back to the label's own tail.
VERB = {
    "ev_f_arr": "array", "ev_f_base": "BASE", "ev_f_csrlin": "CSRLIN",
    "ev_f_instr": "INSTR", "ev_f_varptr": "VARPTR", "ev_f_errfn": "ERR",
    "ex_mid_stmt": "MID$", "ex_deffn": "DEF FN", "ex_let_arr": "LET",
    "ex_let_arr_str": "LET", "ex_ff_stmt": "CALL",
}


def handlers():
    out = {}
    for f in sorted(os.listdir("basic")):
        if not f.endswith((".asm", ".inc")):
            continue
        for ln in open(os.path.join("basic", f), encoding="utf-8"):
            m = re.match(r'^(ex_[a-z0-9_]+|ev_f_[a-z0-9_]+):', ln)
            if m:
                out.setdefault(m.group(1), f)
    return out


def attribute(h, f, wl):
    """LABEL / VERB / FILE / None -- weakest last."""
    if h in wl:
        return "label"
    verb = VERB.get(h) or (h.split("_", 1)[1] if h.startswith("ex_") else h[5:])
    verb = verb.upper()
    if len(verb) >= 3 and re.search(r'\b' + re.escape(verb) + r'\b', wl.upper()):
        return "verb"
    if f in wl:
        return "file"
    return None


def selftest() -> int:
    wl = "an entry naming ex_poke and the FILES verb and basic/graphics.asm"
    fails = []
    if attribute("ex_poke", "poke.asm", wl) != "label":
        fails.append("a handler the worklist NAMES was not reported as named")
    if attribute("ex_files", "files.asm", wl) != "verb":
        fails.append("a handler whose VERB appears was not reported by verb")
    if attribute("ex_circle", "graphics.asm", wl) != "file":
        fails.append("a handler whose FILE appears was not reported by file")
    if attribute("ex_zzz", "nowhere.asm", wl) is not None:
        fails.append("an ABSENT handler was reported attributed -- the sweep "
                     "matches anything and '0 unattributed' means nothing")
    if fails:
        print("\U0001f534 SELFTEST FAILED")
        for x in fails:
            print("   ", x)
        return 2
    print("selftest: label/verb/file each attribute for their own reason, and a "
          "handler named nowhere comes back unattributed ✅")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    wl = open(WORKLIST, encoding="utf-8").read()
    hs = handlers()
    buckets = {}
    for h, f in sorted(hs.items()):
        buckets.setdefault(attribute(h, f, wl) or "NONE", []).append((h, f))
    print(f"handlers in basic/: {len(hs)}   worklist entries: "
          f"{wl.count(chr(10) + '- ')}")
    for k in ("label", "verb", "file", "NONE"):
        print(f"   {k:5s} {len(buckets.get(k, []))}")
    none = buckets.get("NONE", [])
    if none:
        print(f"\nunattributed by label, verb OR file ({len(none)}):")
        for h, f in none:
            print(f"   {h:22s} {f}")
    print("\n\U0001f534 THIS MEASURES SCOPING, NOT QUALITY. A handler attributed "
          "here is IN SCOPE, not correct -- the raw-I/O trio was named, reviewed "
          "and cleared, and had six divergences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
