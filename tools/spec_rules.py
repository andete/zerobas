#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Executable page rules (docs/spec-method.md §3a): every behaviour rule a call's page states is
ALSO a check over the page's measured cases, and the page's rule tables are rendered from them.

A rules module (e.g. probes/bios/spec/chput_rules.py) defines:
    PAGE    the page, relative to the repo root (docs/bios/CHPUT.md)
    def cases() -> {"ref": [case, ...], "zb": [case, ...]}
                  each case a SimpleNamespace with `src` (its evidence group) and `id` (the page's
                  citation for it, e.g. "XCH 127", "X2 G2.22"); the two lists in the same order
    RULES   a list of Rule(id, section, text, select, expect):
              select(case) -> bool   the cases the rule speaks about (on the REFERENCE's data)
              expect(case) -> bool   what the rule says about each of them

The checker reports, per rule:
  - the REFERENCE: every selected case must satisfy it -- a failure means the SENTENCE is false;
  - zerobas: the same cases; a failure is a DIFFERENCE (the page's Differences come from these);
and, over all cases, FIELD-LEVEL coverage (round 4, 2026-11-17): the module's `OUTPUTS` names each case
group's recorded outputs (scalars and lists); while a rule's `expect` runs on a reference case, the case
records which outputs -- and which LIST ENTRIES -- it reads. An output entry no rule reads is UNCOVERED:
"measured but not stated". A case merely SELECTED by a rule that reads none of its behaviour (CHPUT's
"A unchanged" rule over every case) no longer counts; nor does a check that reads one entry of a list its
sentence talks about in full.

    python3 tools/spec_rules.py MODULE.py            report
    python3 tools/spec_rules.py MODULE.py --write    also render the page's rule tables
    python3 tools/spec_rules.py MODULE.py --check    fail on a false rule, or a stale page
The tables go between `<!-- RULES BEGIN -->` and `<!-- RULES END -->` on the page.
"""
import importlib.util
import os
import sys
from dataclasses import dataclass
from typing import Callable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEGIN, END = "<!-- RULES BEGIN -->", "<!-- RULES END -->"


@dataclass
class Rule:
    id: str
    section: str
    text: str
    select: Callable
    expect: Callable


def load(path):
    spec = importlib.util.spec_from_file_location("page_rules", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["page_rules"] = mod
    spec.loader.exec_module(mod)
    return mod


class _TList(list):
    """A list that marks the entries a check reads (indexing, iteration, comparison, `in`)."""
    def __init__(self, data, mark):
        super().__init__(data)
        self._mark = mark

    def __getitem__(self, i):
        if isinstance(i, slice):
            for j in range(*i.indices(len(self))):
                self._mark(j)
        else:
            self._mark(i % len(self))
        return list.__getitem__(self, i)

    def _all(self):
        for j in range(len(self)):
            self._mark(j)

    def __iter__(self):
        self._all()
        return list.__iter__(self)

    def __eq__(self, other):
        self._all()
        return list(self) == list(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __contains__(self, x):
        self._all()
        return list.__contains__(self, x)

    __hash__ = None


class _Tracked:
    """A case seen through a check: reading an OUTPUT field marks it (a list: per entry)."""
    def __init__(self, case, outputs, seen):
        object.__setattr__(self, "_c", case)
        object.__setattr__(self, "_o", outputs)
        object.__setattr__(self, "_s", seen)

    def __getattr__(self, name):
        v = getattr(self._c, name)
        if name not in self._o:
            return v
        if isinstance(v, list):
            return _TList(v, lambda j, n=name: self._s.add((n, j)))
        self._s.add((name, None))
        return v


def _slots(case, outputs):
    out = set()
    for f in outputs:
        v = getattr(case, f)
        if isinstance(v, list):
            out |= {(f, j) for j in range(len(v))}
        else:
            out.add((f, None))
    return out


def run(mod):
    cs = mod.cases()
    ref, zb = cs["ref"], cs["zb"]
    if len(ref) != len(zb) or not ref:
        sys.exit(f"FAIL: the reference and zerobas case lists differ in length ({len(ref)} / {len(zb)}) "
                 f"or are empty")
    outputs = getattr(mod, "OUTPUTS", None)
    if not outputs:
        sys.exit("FAIL: the rules module declares no OUTPUTS -- field-level coverage needs them")
    missing = sorted({c.src for c in ref} - set(outputs))
    if missing:
        sys.exit(f"FAIL: OUTPUTS names no outputs for case group(s) {missing}")
    ids_known = {r.id for r in mod.RULES}
    import re as _re
    for r in mod.RULES:                        # a rule's text may only name rules that exist
        for ref_id in _re.findall(r"\bR4?-[A-Z0-9][A-Za-z0-9-]*\b", r.text):
            if ref_id not in ids_known:
                sys.exit(f"FAIL: rule {r.id}'s text names {ref_id}, which is no rule (a stale reference)")
    seen = [set() for _ in ref]
    # UNREAD: {case id: (fields, reason)} -- outputs a page declares NOT evidence (the setup decides
    # them), rendered with the reason; they count as accounted for, never as covered
    unread = getattr(mod, "UNREAD", {})
    ids = {c.id: i for i, c in enumerate(ref)}
    declared = 0
    unread_diffs = []                        # declared NOT evidence, yet the machines differ there
    for cid, (fields, _why) in unread.items():
        if cid not in ids:
            sys.exit(f"FAIL: UNREAD names {cid}, which is no case")
        i = ids[cid]
        c = ref[i]
        sl = {x for x in _slots(c, outputs[c.src]) if x[0] in fields}
        seen[i] |= sl
        declared += len(sl)
        for f in fields:
            if getattr(ref[i], f) != getattr(zb[i], f):
                unread_diffs.append(f"{cid} {f}")
    out = []
    for r in mod.RULES:
        idx = [i for i, c in enumerate(ref) if r.select(c)]
        if not idx:
            sys.exit(f"FAIL: rule {r.id} selects no case -- a rule about nothing")
        ref_bad = [ref[i].id for i in idx if not r.expect(_Tracked(ref[i], outputs[ref[i].src], seen[i]))]
        zb_bad = [zb[i].id for i in idx if not r.expect(zb[i])]
        out.append((r, len(idx), ref_bad, zb_bad))
    total = 0
    uncovered = []                        # (case id, [field[entry] ...])
    for i, c in enumerate(ref):
        slots = _slots(c, outputs[c.src])
        total += len(slots)
        miss = slots - seen[i]
        if miss:
            uncovered.append((c.id, sorted(f if j is None else f"{f}[{j}]" for f, j in miss)))
    run.declared, run.unread_diffs = declared, unread_diffs
    return out, uncovered, total


def short(ids, n=6):
    return ", ".join(ids[:n]) + (f" … (+{len(ids) - n})" if len(ids) > n else "")


def uncov_text(uncovered, n):
    """'XCH 512: csrx, csry' ... grouped by the same missing fields"""
    groups = {}
    for cid, fields in uncovered:
        groups.setdefault(", ".join(fields), []).append(cid)
    parts = [f"{short(ids, 3)} ({len(ids)}): {fs}" for fs, ids in groups.items()]
    return "; ".join(parts[:n]) + (f"; … (+{len(parts) - n} more groups)" if len(parts) > n else "")


def render(mod, results, uncovered, total):
    L = [BEGIN,
         f"<!-- GENERATED by tools/spec_rules.py from {os.path.relpath(mod.__file__, ROOT)} -- do not "
         f"edit; `python3 tools/spec_rules.py {os.path.relpath(mod.__file__, ROOT)} --write` -->", ""]
    n_ok = sum(1 for _, _, rb, _ in results if not rb)
    n_unc = sum(len(f) for _, f in uncovered)
    dec = getattr(run, "declared", 0)
    L.append(f"**{len(results)} rules; {n_ok} hold on the reference. Of the {total} recorded outputs (each "
             f"case's cursor, cells, A, table entries ...): {total - n_unc - dec} read by a rule's check, {dec} "
             f"declared NOT evidence (below), {n_unc} unread.**")
    sec = None
    order = {s_: i for i, s_ in enumerate(sorted({r.section for r, *_ in results},
                                                   key=lambda t: (int(t.split(".")[0]) if t.split(".")[0].isdigit() else 99, t)))}
    results = sorted(results, key=lambda x: order[x[0].section])      # sections in order, rules kept in order
    for r, n, rb, zbb in results:
        if r.section != sec:
            sec = r.section
            L += ["", f"#### {sec}", "", "| rule | cases | reference | zerobas |", "|---|---|---|---|"]
        refs = "✓" if not rb else f"✗ FALSE on {len(rb)}: {short(rb)}"
        zbs = "✓" if not zbb else f"✗ {len(zbb)}: {short(zbb)}"
        L.append(f"| **{r.id}** {r.text} | {n} | {refs} | {zbs} |")
    if uncovered:
        L += ["", f"Measured but read by no rule's check: {uncov_text(uncovered, 12)}"]
    groups = {}
    for cid, (fields, why) in getattr(mod, "UNREAD", {}).items():
        groups.setdefault((", ".join(fields), why), []).append(cid)
    for (fields, why), cids in groups.items():
        L += ["", f"Declared NOT evidence ({len(cids)} cases: {short(cids, 4)}): {fields} — {why}"]
    L += ["", END]
    return "\n".join(L)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    mod = load(sys.argv[1])
    results, uncovered, total = run(mod)
    false = [(r.id, rb) for r, _, rb, _ in results if rb]
    for r, n, rb, zbb in results:
        print(f"{r.id:22} {n:5} cases  ref {'ok' if not rb else 'FALSE ' + short(rb, 4):40}  "
              f"zb {'ok' if not zbb else str(len(zbb)) + ' differ: ' + short(zbb, 3)}")
    n_unc = sum(len(f) for _, f in uncovered)
    print(f"\nuncovered outputs: {n_unc} of {total} in {len(uncovered)} cases"
          + (f"\n  {uncov_text(uncovered, 40)}" if uncovered else ""))
    page = os.path.join(ROOT, mod.PAGE)
    text = open(page, encoding="utf-8").read()
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        sys.exit(f"FAIL: {mod.PAGE} needs exactly one {BEGIN} ... {END} block")
    new = text[:text.index(BEGIN)] + render(mod, results, uncovered, total) + text[text.index(END) + len(END):]
    if "--write" in sys.argv:
        open(page, "w", encoding="utf-8").write(new)
        print(f"wrote {mod.PAGE}'s rule tables")
    if "--check" in sys.argv:
        if false:
            print(f"🔴 spec-rules: {len(false)} rule(s) FALSE on the reference's own data: "
                  + "; ".join(f"{i} ({short(b, 3)})" for i, b in false))
            return 1
        if run.unread_diffs:
            print(f"🔴 spec-rules: outputs declared NOT evidence DIFFER between the machines -- they are "
                  f"evidence after all, state a rule: {short(run.unread_diffs, 6)}")
            return 1
        if new != text:
            print(f"🔴 spec-rules: {mod.PAGE}'s rule tables are stale -- run with --write")
            return 1
        print(f"spec-rules: {mod.PAGE}: every rule holds on the reference, the page matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
