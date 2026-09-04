#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""check_temp_root — every temp file this project writes lands under ONE root.

`probes/lib/probe_tmp.py` owns `/tmp/zerobas` and points `tempfile.tempdir` at
it, so "clean up everything this project wrote" is one `rm -rf`. That property
is worth exactly as much as its weakest new call site, which is why it is gated
statically rather than written down.

🔴 THIS IS THE FAILURE THIS TREE ALREADY HAD ONCE. `tests/_tmp.py` solved this
class for the unit tests and its lesson was never carried across to the probes --
the half that runs eight processes at a time -- which cost 2165 orphaned files,
1.1 GB, and a stochastic gate flake. A rule nobody enforces is a rule that holds
until the next person writes the obvious thing.

THREE RULES:

  1. A file that calls `tempfile.mkstemp/mkdtemp/NamedTemporaryFile/
     TemporaryDirectory` without an explicit `dir=` must REACH `probe_tmp` --
     directly, or through one of the lib chokepoints that imports it. Reaching
     it is what relocates the call.
  2. `tempfile.tempdir` may be assigned in `probe_tmp.py` and nowhere else. Two
     modules setting the root is two roots.
  3. Hardcoded `"/tmp/..."` literals are PINNED (temp-root-allow.txt). ⚠️ They
     may SHRINK, never grow. They are not automatically wrong -- eleven are
     `argparse` defaults, a documented output location someone may rely on --
     but a new one is a new thing outside the root, and must be a decision.

⚠️ AN ALLOWLIST THAT ONLY SUPPRESSES IS ROT (see the deadcode gate's own note).
This one is a CONTROL: an entry that no longer matches is an ERROR, so the file
cannot drift away from what it claims.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOW = os.path.join(ROOT, "tools", "temp-root-allow.txt")
TREES = ("probes", "tools", "tests")
OWNER = os.path.join("probes", "lib", "probe_tmp.py")

# importing any of these reaches probe_tmp (they import it at their top)
CHOKEPOINTS = ("probe_tmp", "omsx_repl", "omsx_run", "omsx_preflight",
               "probe_report")

BARE = re.compile(r"tempfile\.(mkstemp|mkdtemp|NamedTemporaryFile|"
                  r"TemporaryDirectory)\(([^)]*)\)", re.S)
LITERAL = re.compile(r"""["']/tmp/[^"']*["']""")
TEMPDIR_SET = re.compile(r"^\s*tempfile\.tempdir\s*=", re.M)


def sources() -> list[str]:
    out = []
    for t in TREES:
        for dirpath, _d, files in os.walk(os.path.join(ROOT, t)):
            if "__pycache__" in dirpath:
                continue
            for f in files:
                if f.endswith(".py"):
                    out.append(os.path.relpath(os.path.join(dirpath, f), ROOT))
    return sorted(out)


def code_only(src: str) -> str:
    """`src` with COMMENTS and STRING literals blanked out, same length so line
    numbers still line up.

    🔴 WHY THIS EXISTS. This checker matched the PROSE written to explain its own
    subject: a comment reading *"the first cut made a
    `tempfile.TemporaryDirectory()`"* was reported as a bare call, in a file that
    makes none. That is a class this project keeps meeting -- an instrument
    counting the words about the thing instead of the thing -- and the standing
    remedy is to anchor to the instruction form or strip comments. Stripping is
    exact here because the input is Python.

    ⚠️ STRINGS GO TOO, and that is deliberate: `"tempfile.mkdtemp()"` inside a
    literal is not a call either. ⚠️ AND A FILE THAT WILL NOT TOKENIZE FALLS BACK
    TO THE RAW TEXT -- a syntax error must not silently switch the scan off.
    """
    import io
    import tokenize
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src
    lines = src.splitlines(keepends=True)
    out = [list(l) for l in lines]
    for tok in toks:
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        (r1, c1), (r2, c2) = tok.start, tok.end
        for r in range(r1, r2 + 1):
            if r - 1 >= len(out):
                break
            row = out[r - 1]
            lo = c1 if r == r1 else 0
            hi = c2 if r == r2 else len(row)
            for c in range(lo, min(hi, len(row))):
                if row[c] != "\n":
                    row[c] = " "
    return "".join("".join(r) for r in out)


def selftest() -> int:
    fails = 0
    real = "import tempfile\nd = tempfile.mkdtemp()\n"
    prosed = "import tempfile\n# the first cut used tempfile.mkdtemp() here\nx = 1\n"
    strung = 'msg = "call tempfile.mkdtemp() instead"\n'
    def hits(src):
        c = code_only(src)
        return [m for m in BARE.finditer(c) if "dir=" not in m.group(2)]
    if len(hits(real)) != 1:
        print(f"  selftest: a REAL bare call was not seen ({len(hits(real))})"); fails += 1
    if hits(prosed):
        print("  selftest: a call named in a COMMENT was reported"); fails += 1
    if hits(strung):
        print("  selftest: a call named in a STRING was reported"); fails += 1
    # line numbers must survive the blanking, or every report points elsewhere
    padded = "x = 1\n" * 40 + real
    h = hits(padded)
    if not h or padded[:h[0].start()].count("\n") + 1 != 42:
        print("  selftest: blanking moved the reported line number"); fails += 1
    # a file that will not tokenize must still be scanned, not skipped
    if not hits("def f(:\n" + real):
        print("  selftest: an untokenizable file switched the scan OFF"); fails += 1
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def main() -> int:
    if "--selftest" in sys.argv:
        return 2 if selftest() else 0
    allow = set()
    if os.path.exists(ALLOW):
        allow = {l.strip() for l in open(ALLOW)
                 if l.strip() and not l.startswith("#")}

    bad, seen_allow = [], set()
    for rel in sources():
        s = open(os.path.join(ROOT, rel), errors="replace").read()
        # 🔴 ONLY THE CALL RULE GETS THE STRIPPED TEXT. Rule 3 hunts `/tmp/...`
        # STRING LITERALS, so handing it a string-blanked source deletes its
        # entire subject: the first cut applied code_only() to `s` itself and
        # every one of the 110 pinned literals went "stale", i.e. the check
        # reported the tree as clean by having stopped looking.
        code = code_only(s)

        # rule 2
        if TEMPDIR_SET.search(s) and rel != OWNER:
            bad.append((rel, "sets `tempfile.tempdir`; only "
                             f"{OWNER} may (two roots is no root)"))

        # rule 1
        bare = [m for m in BARE.finditer(code) if "dir=" not in m.group(2)]
        if bare and rel != OWNER:
            reaches = any(re.search(rf"^import {c}\b", s, re.M)
                          for c in CHOKEPOINTS)
            if not reaches:
                n = code[:bare[0].start()].count("\n") + 1
                bad.append((f"{rel}:{n}",
                            f"{len(bare)} bare `tempfile.*` call(s) but the file "
                            "reaches no chokepoint, so they escape the root -- "
                            "`import probe_tmp` (or a lib module that does)"))

        # rule 3
        for m in LITERAL.finditer(s):
            n = s[:m.start()].count("\n") + 1
            key = f"{rel}:{m.group(0)}"
            if key in allow:
                seen_allow.add(key)
            else:
                bad.append((f"{rel}:{n}",
                            f"hardcoded {m.group(0)} outside the root -- route it "
                            "through `probe_tmp.tmp()`, or pin it in "
                            "tools/temp-root-allow.txt with a reason"))

    stale = sorted(allow - seen_allow)
    print(f"check_temp_root — root {os.environ.get('ZEROBAS_TMP') or '/tmp/zerobas'}"
          f"   {len(sources())} source(s), {len(allow)} pinned literal(s)")
    for where, why in bad:
        print(f"  RED   {where}\n        {why}")
    for k in stale:
        print(f"  STALE {k}\n        pinned but no longer present -- an allowlist "
              f"entry that stops matching is rot; delete it")
    if bad or stale:
        print(f"\n{len(bad)} violation(s), {len(stale)} stale pin(s)")
        return 1
    print(f"ALL PASS — every bare tempfile call reaches the root; "
          f"{len(seen_allow)} pinned literal(s) all still present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
