#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DEFERPIN gate — every DEFERRED row's value is a face PIN, never free prose.

🔴 A FILED *FACE* ROTS WITHOUT THE ROW CEASING TO DIVERGE, AND NOTHING DETECTED
THAT (TODO.md, filed 2026-09-04 after three hand-found instances). Two more
landed on 2026-09-05:

  * `basic_probe_namspc.py` deferred three bare-verb rows with the reason
    *"`Missing operand` on the CF-3300, `Syntax error` here"* — while all three
    machines had come to print `Missing operand`. The note carried its OWN ⚠️
    saying the reason must not go stale, written one round earlier. **A warning
    is not a check.**
  * `basic_probe_fldwidth.py`'s `r.len100` said *"`Syntax error` here"* where the
    machine reads `Illegal function call`; D-RECLENDOM had corrected the TODO
    ENTRY a day earlier and the probe kept the old wording. **Correcting the
    filing does not correct the probe, and nothing connects them.**

🎯 `tools/filed_row_sweep`-style adjudication CANNOT see this class, by its own
design: it asks *known / unfiled / no-longer-diverging*, and a row that still
diverges but diverges to a DIFFERENT FACE is `known`.

So the face lives in the probe, beside the measurement, as
`probe_report.Deferral(reason, side=face, ...)`, which goes red on drift in
EITHER direction — the shape `basic_probe_nodisk.py`'s `PINNED` dict already has.
This gate is what stops the next deferral being added as a bare string again: it
is a STATIC read of the source, so it costs no emulator time and cannot be
skipped by a row not running.

## The rule

Every value assigned into a module-level `DEFERRED` mapping — as a dict literal,
or by `DEFERRED[label] = ...`, including inside a loop — must be a call to
`Deferral(...)` / `probe_report.Deferral(...)`. A bare string, an f-string or a
concatenation of them is a NOTE, and a note is what rotted five times.
"""
from __future__ import annotations

import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- one temp root
TREES = ("probes/basic", "probes/lib")


def _is_pin(node) -> bool:
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if isinstance(f, ast.Name):
        return f.id == "Deferral"
    return isinstance(f, ast.Attribute) and f.attr == "Deferral"


def offences(path):
    """(line, what) for every DEFERRED value that is not a Deferral(...)."""
    src = open(path, encoding="utf-8", errors="replace").read()
    if "DEFERRED" not in src:
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [(e.lineno or 0, f"does not parse: {e.msg}")]
    out = []
    for node in ast.walk(tree):
        # DEFERRED = {...} / DEFERRED: T = {...}
        tgts = []
        if isinstance(node, ast.Assign):
            tgts = node.targets
        elif isinstance(node, ast.AnnAssign):
            tgts = [node.target]
        else:
            continue
        val = node.value
        for tg in tgts:
            if isinstance(tg, ast.Name) and tg.id == "DEFERRED":
                if isinstance(val, ast.Dict):
                    for k, v in zip(val.keys, val.values):
                        if not _is_pin(v):
                            lab = getattr(k, "value", "?")
                            out.append((getattr(v, "lineno", node.lineno),
                                        f"DEFERRED[{lab!r}] is not a Deferral(...)"))
                elif val is not None and not isinstance(val, (ast.Call, ast.Name)):
                    out.append((node.lineno, "DEFERRED is assigned something "
                                             "this gate cannot read"))
            elif (isinstance(tg, ast.Subscript)
                  and isinstance(tg.value, ast.Name)
                  and tg.value.id == "DEFERRED"):
                if not _is_pin(val):
                    out.append((node.lineno,
                                "DEFERRED[...] = a value that is not a Deferral(...)"))
    return out


def check(paths=None, quiet=False):
    if paths is None:
        paths = []
        for t in TREES:
            paths += sorted(glob.glob(os.path.join(ROOT, t, "*.py")))
    seen = bad = 0
    rows = []
    for p in paths:
        offs = offences(p)
        rel = os.path.relpath(p, ROOT)
        if "DEFERRED" in open(p, encoding="utf-8", errors="replace").read():
            seen += 1
        for line, why in offs:
            bad += 1
            rows.append(f"  {rel}:{line}  {why}")
    if not quiet:
        print(f"deferral-pin: {seen} file(s) mention DEFERRED; "
              f"{bad} unpinned value(s)")
    if rows and not quiet:
        print("\U0001f534 A DEFERRAL WITHOUT A PINNED FACE IS A NOTE, AND A NOTE "
              "ROTS SILENTLY — use probe_report.Deferral(reason, side=face, ...):")
        print("\n".join(rows))
    if rows:
        return 1
    return 0


# --- selftest ---------------------------------------------------------------
ARMS = [
    ("a dict of Deferral(...) passes",
     "DEFERRED = {'a': probe_report.Deferral('why', zb='<X>')}\n", 0),
    ("a bare string in the dict fails",
     "DEFERRED = {'a': 'why'}\n", 1),
    ("an implicit concatenation is still a string, and still fails",
     "DEFERRED = {'a': 'why '\n            'continued'}\n", 1),
    ("a subscript assignment must be a pin too",
     "DEFERRED = {}\nfor x in ('a',):\n    DEFERRED[x] = 'why'\n", 1),
    ("a subscript assignment that IS a pin passes",
     "DEFERRED = {}\nfor x in ('a',):\n    DEFERRED[x] = Deferral('why', zb='<X>')\n", 0),
    ("a file with no DEFERRED at all is not an offence",
     "PINNED = {'a': 'why'}\n", 0),
    ("an unqualified Deferral(...) passes",
     "DEFERRED = {'a': Deferral('why', zb='<X>')}\n", 0),
]


def selftest():
    import tempfile
    fails = 0
    d = tempfile.mkdtemp(prefix="deferpin_")
    for i, (name, body, want) in enumerate(ARMS):
        p = os.path.join(d, f"arm{i}.py")
        open(p, "w", encoding="utf-8").write(body)
        got = check([p], quiet=True)
        ok = got == want
        fails += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}  (want rc={want}, got {got})")
    print(f"{len(ARMS) - fails}/{len(ARMS)} selftest arms pass")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(check())
