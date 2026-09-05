#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ALPHAGATE — a probe that classifies error text must be able to say "I can't".

🔴 A HAND-WRITTEN ERROR-MESSAGE ALPHABET IS A BLIND SPOT (TODO.md, filed
2026-09-02 by D-LSETTM). A classifier walks a literal list; anything absent falls
through to `<NO OUTPUT>`, which routes the row to *"without a reference"* — **a
sentence about the MACHINE for a fault in the PROBE**. `Missing operand` was
missing from three separate alphabets and had to be added by hand each time,
each time after rows had already been reported as unscored while both machines
printed a perfectly good message.

🎯 "ADD THE NEXT NAME" IS NOT THE FIX, and this gate does not ask for a complete
alphabet — a probe legitimately names only the faces its own rows can produce,
and the REFERENCES can print messages zerobas has no string for at all
(`Disk offline`). What it requires is the property that makes an omission LOUD:

    a classifier that iterates an error alphabet and falls back to a sentinel
    must have an UNREADABLE arm — non-empty text it cannot name comes back as
    `<UNREADABLE: ...>`, carrying the text, deliberately NOT a sentinel, so the
    gate scores it RED instead of routing it to "no reference".

## The advisory half, and why it is not red

`probes/lib/errmsg_alphabet.py` derives what this ROM can print, from
`sub/errmsg.asm` plus the escape-encoded main-ROM strings. Comparing each
probe's literals against it finds the OTHER half of the class: four probes once
said `Field overflow` where the ROM says **`FIELD overflow`** — a message they
DID name, spelled so it could never match.

⚠️ MEASURED 2026-09-05, THAT CLASS IS EMPTY. The sweep raised 58 hits and 57 of
them were the case-folding IDIOM (`"type mismatch" in txt.lower()`), filtered out
below. The one that survives is `basic_probe_fldwidth.py`'s `File not open`,
which is **correct**: it matches case-insensitively on purpose, because
`File not OPEN` (zerobas) vs `File not open` (reference) is D-MSGEXACT's own
surface and scoring it inside every ERR 59 row would put a separately-owned
divergence everywhere. `basic_probe_str_cmp.py` carries the same design for
ERR 13. So spelling drift is REPORTED, never failed: a rule that reddened those
would be measuring the tree's documented design as a defect.
"""
from __future__ import annotations

import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- one temp root
import errmsg_alphabet                 # noqa: E402

SENTINELS = ("<NO OUTPUT>", "<NO CAPTURE>")
ALPHABET_NAMES = ("ERRORS", "_ERRORS", "MESSAGES")


def _classifiers(tree):
    """Functions that walk an error alphabet AND can return a bare sentinel."""
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        if not names & set(ALPHABET_NAMES):
            continue
        if not any(isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
                   and n.value.value in SENTINELS for n in ast.walk(fn)):
            continue
        yield fn


def check(paths=None, quiet=False):
    if paths is None:
        paths = sorted(glob.glob(os.path.join(ROOT, "probes", "**", "*.py"),
                                 recursive=True))
    bad, seen, drift = [], 0, []
    lower = {m.lower(): m for m in errmsg_alphabet.MESSAGES}
    for p in paths:
        src = open(p, encoding="utf-8", errors="replace").read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        rel = os.path.relpath(p, ROOT)
        for fn in _classifiers(tree):
            seen += 1
            if "UNREADABLE" not in ast.dump(fn):
                bad.append(f"  {rel}:{fn.lineno}  {fn.name}() falls back to a "
                           f"sentinel with no UNREADABLE arm")
        if rel == os.path.join("probes", "lib", "errmsg_alphabet.py"):
            continue          # the derivation itself; its arms quote wrong
                              # spellings ON PURPOSE
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
                continue
            v = n.value
            # \U0001f534 AN ALL-LOWERCASE LITERAL IS THE CASE-FOLDING IDIOM, NOT DRIFT.
            # 55 of the first run's 58 hits were `"type mismatch" in txt.lower()`
            # and friends. An advisory that loud is one nobody reads, which is
            # how an instrument fails by producing a plausible table
            # [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
            # `tools/check_needle_case.py` polices the mirror image -- a
            # CAPITALISED string written into a case-folded table -- so the two
            # gates share one model of what lowercase means here.
            if v == v.lower():
                continue
            if v not in errmsg_alphabet.MESSAGES and v.lower() in lower:
                drift.append(f"  {rel}:{n.lineno}  {v!r} — the ROM says "
                             f"{lower[v.lower()]!r}")
    if not quiet:
        print(f"error-alphabet: {len(errmsg_alphabet.MESSAGES)} message(s) "
              f"derived from the ROM source; {seen} classifier(s) checked")
        if drift:
            print(f"⚠️  {len(drift)} literal(s) differ from the ROM only by "
                  f"case — ADVISORY, some are deliberate (D-MSGEXACT):")
            print("\n".join(sorted(set(drift))))
    if bad:
        print("\U0001f534 A CLASSIFIER THAT CANNOT SAY \"I CAN'T NAME THIS\" REPORTS "
              "A PROBE FAULT AS A MACHINE SILENCE:")
        print("\n".join(bad))
        return 1
    return 0


# --- selftest ---------------------------------------------------------------
ARMS = [
    ("a classifier with an UNREADABLE arm passes",
     'ERRORS = ("Syntax error",)\n'
     'def face(t):\n'
     '    for e in ERRORS:\n'
     '        if e in t: return f"<{e}>"\n'
     '    if t.strip(): return f"<UNREADABLE: {t}>"\n'
     '    return "<NO OUTPUT>"\n', 0),
    ("a classifier that falls straight to the sentinel fails",
     'ERRORS = ("Syntax error",)\n'
     'def face(t):\n'
     '    for e in ERRORS:\n'
     '        if e in t: return f"<{e}>"\n'
     '    return "<NO OUTPUT>"\n', 1),
    ("a function that never touches the alphabet is not a classifier",
     'def tokens(t):\n    return "<NO OUTPUT>"\n', 0),
    ("a classifier that cannot return a sentinel at all is not in scope",
     'ERRORS = ("Syntax error",)\n'
     'def face(t):\n'
     '    for e in ERRORS:\n'
     '        if e in t: return f"<{e}>"\n'
     '    return t\n', 0),
    # 🔴 THE ADVISORY MUST NOT BE RED. Reddening it would score two DELIBERATE
    # case-insensitive probes (D-MSGEXACT's own surface) as defects.
    ("a case-drifted literal is advisory, not a failure",
     'ERRORS = ("Field overflow",)\n'
     'def face(t):\n'
     '    for e in ERRORS:\n'
     '        if e in t: return f"<{e}>"\n'
     '    if t.strip(): return f"<UNREADABLE: {t}>"\n'
     '    return "<NO OUTPUT>"\n', 0),
    ("the _ERRORS spelling is a classifier too",
     '_ERRORS = ("Syntax error",)\n'
     'def face(t):\n'
     '    for e in _ERRORS:\n'
     '        if e in t: return f"<{e}>"\n'
     '    return "<NO CAPTURE>"\n', 1),
]


def selftest():
    import tempfile
    d = tempfile.mkdtemp(prefix="alphagate_")
    fails = 0
    for i, (name, body, want) in enumerate(ARMS):
        p = os.path.join(d, f"arm{i}.py")
        open(p, "w", encoding="utf-8").write(body)
        got = check([p], quiet=True)
        ok = got == want
        fails += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}  (want rc={want}, got {got})")
    rc = errmsg_alphabet_selftest()
    print(f"{len(ARMS) - fails}/{len(ARMS)} selftest arms pass")
    return 1 if (fails or rc) else 0


def errmsg_alphabet_selftest():
    """The derivation has its own known-answer arms; run them from here too, so
    a broken alphabet cannot make this gate green by naming nothing."""
    import subprocess
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "probes", "lib", "errmsg_alphabet.py"),
                        "--selftest"], capture_output=True, text=True)
    print("  " + (r.stdout.strip().replace("\n", "\n  ") or "(no output)"))
    return r.returncode


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(check())
