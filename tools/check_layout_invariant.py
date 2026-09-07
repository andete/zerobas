#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LAYOUTINV — the invariant a LAYOUT PASS is allowed to preserve.

## Why this exists

The ROM partition was reached by evicting things one at a time as they stopped
fitting, never by choosing boundaries with the whole call graph in view. A layout
pass would fix that -- but "the battery is still green" is a weak thing to rest a
wholesale re-placement on, and the part that would NOT survive a rebuild is the
commentary: why `sid_cas` must not `fch_select`, why the KEY band is reversed,
why `ev_f_err` must not be shared while `penderr_de0` may. Most of that was
learned by getting it wrong once, and no gate reads prose.

So the pass is a REFACTOR, not a rewrite: keep every routine body and every
comment, change only PLACEMENT and LINKAGE. That turns into a machine-checkable
property, which is what this checks:

    for every routine, the ORDERED SEQUENCE of its instructions is unchanged;
    only its address, and the form of its branches, may move.

That is strictly stronger than a green battery. A battery samples behaviour; this
asserts the code is the same code.

## What counts as a change, and what does not

  MOVED    same instruction sequence, different address        allowed
  FORM     same sequence, a branch changed jp<->jr             allowed, listed
  CHANGED  the instruction sequence differs                    🔴 REFUSED
  ADDED / REMOVED  a routine appeared or vanished              🔴 REFUSED

Branch FORM is normalised out of the fingerprint on purpose: moving a routine
changes what `jr` can reach, so `jp`<->`jr` substitution is a CONSEQUENCE of
placement rather than a change of code. It is reported separately because it is
also the one edit that changes the byte count, so it must never be silent.

## ⚠️ What this does NOT prove

  * It is blind to DATA. `db`/`dw` tables are not instructions and are not
    fingerprinted; a layout pass that moves a jump table must argue that
    separately.
  * A main<->sub move is NOT a placement change. Crossing that boundary turns a
    `call` into `subrom_call` marshalling, with its own clobber rules -- a real
    semantic change. Such moves are reported as NON-MECHANICAL and refused, so
    they have to be taken deliberately and one at a time.
  * Identical instructions can still break: D-PUBTAIL's tail was byte-identical
    and carried a STACK PROTOCOL that a fingerprint cannot see. This bounds the
    blast radius of a layout pass; it does not license one.

## Use

    python3 tools/check_layout_invariant.py --record    # before the pass
    python3 tools/check_layout_invariant.py             # after each step
    python3 tools/check_layout_invariant.py --selftest
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import ngram_sweep                                                # noqa: E402

BASELINE = os.path.join(ROOT, "tools", "layout-invariant-baseline.json")
BRANCH = re.compile(r"^(jp|jr)\s+(.*)$")


def normalise(key: str) -> tuple[str, str | None]:
    """-> (fingerprint key, branch form or None).

    `jp X` and `jr X` fingerprint identically as `br X`; the form is returned
    separately so a change of form is visible without being a body change."""
    m = BRANCH.match(key)
    if not m:
        return key, None
    return f"br {m.group(2)}", m.group(1)


def routines() -> dict:
    """label -> {file, region, seq (fingerprint), forms}. A routine runs from its
    label to the next label in the same file."""
    out, cur, rel = {}, None, None
    for rec in ngram_sweep.parse():
        kind = rec[0]
        if kind == "LABEL":
            _, rel, _n, lab = rec[0], rec[1], rec[2], rec[3]
            cur = lab
            out.setdefault(cur, {"file": rel, "seq": [], "forms": []})
        elif kind == "I" and cur is not None:
            k, form = normalise(rec[3])
            out[cur]["seq"].append(k)
            if form:
                out[cur]["forms"].append(form)
    for lab, d in out.items():
        d["region"] = "sub" if d["file"].startswith("sub/") else "main"
        d["fp"] = hashlib.sha1("\n".join(d["seq"]).encode()).hexdigest()[:12]
        d["n"] = len(d["seq"])
        del d["seq"]
    return out


def compare(base: dict, now: dict):
    changed, added, removed, form, crossed, moved = [], [], [], [], [], []
    for lab, b in base.items():
        n = now.get(lab)
        if n is None:
            removed.append(lab); continue
        if n["fp"] != b["fp"]:
            changed.append((lab, b, n)); continue
        if n["forms"] != b["forms"]:
            form.append((lab, b["forms"].count("jr"), n["forms"].count("jr")))
        if n["region"] != b["region"]:
            crossed.append((lab, b["region"], n["region"]))
        elif n["file"] != b["file"]:
            moved.append((lab, b["file"], n["file"]))
    for lab in now:
        if lab not in base:
            added.append(lab)
    return changed, added, removed, form, crossed, moved


def main(argv) -> int:
    now = routines()
    if "--record" in argv:
        with open(BASELINE, "w") as fh:
            json.dump(now, fh, indent=1, sort_keys=True)
        print(f"recorded {len(now)} routine(s) -> "
              f"{os.path.relpath(BASELINE, ROOT)}")
        return 0
    if not os.path.exists(BASELINE):
        print("no baseline recorded — this checker is a LAYOUT-PASS tool and is "
              "vacuous without one.\n  python3 tools/check_layout_invariant.py "
              "--record")
        return 0
    base = json.load(open(BASELINE))
    changed, added, removed, form, crossed, moved = compare(base, now)

    print(f"routines: {len(base)} baseline, {len(now)} now")
    print(f"  moved (same body, different file) : {len(moved)}")
    print(f"  branch-form only (jp<->jr)        : {len(form)}")
    for lab, a, b in form[:20]:
        print(f"      {lab:28s} jr {a} -> {b}")
    bad = 0
    if crossed:
        bad += len(crossed)
        print(f"\n🔴 {len(crossed)} routine(s) CROSSED THE main/sub BOUNDARY — that "
              f"is not a placement change: it turns a `call` into subrom_call "
              f"marshalling, with its own clobber rules.")
        for lab, a, b in crossed:
            print(f"      {lab:28s} {a} -> {b}")
    if changed:
        bad += len(changed)
        print(f"\n🔴 {len(changed)} routine(s) CHANGED — a layout pass may move code, "
              f"not rewrite it.")
        for lab, b, n in changed[:20]:
            print(f"      {lab:28s} {b['n']} insn -> {n['n']} insn  "
                  f"({b['file']} -> {n['file']})")
    if added or removed:
        bad += len(added) + len(removed)
        print(f"\n🔴 {len(added)} added, {len(removed)} removed")
        for lab in (added + removed)[:20]:
            print(f"      {lab}")
    if not bad:
        print("\nOK: every routine kept its instruction sequence; only addresses "
              "and branch forms moved.")
    return 2 if bad else 0


def selftest() -> int:
    """🔬 THE ARMS ARE THE FOUR VERDICTS, because a checker that only ever says OK
    is indistinguishable from one that reads nothing."""
    base = {
        "a": {"file": "basic/x.asm", "region": "main", "fp": "aaa", "n": 3,
              "forms": ["jp"]},
        "b": {"file": "basic/x.asm", "region": "main", "fp": "bbb", "n": 2,
              "forms": []},
        "c": {"file": "basic/x.asm", "region": "main", "fp": "ccc", "n": 1,
              "forms": []},
        "d": {"file": "basic/y.asm", "region": "main", "fp": "ddd", "n": 1,
              "forms": []},
    }
    now = {
        "a": {"file": "basic/z.asm", "region": "main", "fp": "aaa", "n": 3,
              "forms": ["jr"]},                       # moved + form change
        "b": {"file": "basic/x.asm", "region": "main", "fp": "XXX", "n": 4,
              "forms": []},                           # CHANGED
        "d": {"file": "sub/y.asm", "region": "sub", "fp": "ddd", "n": 1,
              "forms": []},                           # crossed
        "e": {"file": "basic/x.asm", "region": "main", "fp": "eee", "n": 1,
              "forms": []},                           # added
    }                                                 # c removed
    changed, added, removed, form, crossed, moved = compare(base, now)
    arms = [("moved", [l for l, _, _ in moved] == ["a"]),
            ("form", [l for l, _, _ in form] == ["a"]),
            ("changed", [l for l, _, _ in changed] == ["b"]),
            ("crossed", [l for l, _, _ in crossed] == ["d"]),
            ("added", added == ["e"]),
            ("removed", removed == ["c"])]
    bad = [n for n, ok in arms if not ok]
    for n, ok in arms:
        print(f"  {'ok  ' if ok else 'FAIL'} {n}")
    print(f"selftest: {len(arms) - len(bad)}/{len(arms)} arms green")
    return len(bad)


if __name__ == "__main__":
    raise SystemExit(selftest() if "--selftest" in sys.argv
                     else main(sys.argv[1:]))
