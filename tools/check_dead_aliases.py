#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ALIASGATE — an unreferenced `equ` alias of a CODE LABEL is dead code.

🔴 THE HOLE THIS FILLS, AND WHY THE EXISTING SWEEP CANNOT. `check_dead_code`
models the ROM as SPANS between labels and asks which spans nothing reaches. An
`equ` emits NO BYTES, so an alias has no span and is invisible to it -- it is not
that the sweep gets the answer wrong, it is that the alias is not in its
universe. `dpl_link_err equ ctp_link_err` and `dpl_err_pop equ ctp_err_pop` sat
in `basic/cload.asm` with ZERO references after D-TRUNCLOAD replaced their call
sites, each under a header still claiming *"The NAME and every call site
survive"*, and every gate in the battery was green (TODO, D-DPLDEP).

WHAT COUNTS AS DEAD HERE, stated narrowly on purpose:
  * the definition is `NAME equ TARGET` where TARGET is a BARE IDENTIFIER;
  * TARGET is a CODE LABEL (it appears as `target:` somewhere in the sources),
    NOT a data/constant equate -- `FOPEN_SEL equ DISKOP_OP` aliases a RAM cell
    and is a different thing with different lifetime rules;
  * and NAME appears nowhere else in the sources outside comments.
An alias meeting all three is dead by exactly the argument `check_dead_code`
makes about an unreferenced routine.

🔴 COMMENTS ARE STRIPPED BEFORE COUNTING REFERENCES, AND THAT IS LOAD-BEARING,
NOT TIDINESS. The whole reason this defect survived is that `dpl_err_pop` is
*discussed at length* in a 12-line justification above `dpl_get_store` -- prose
arguing about where "the `jp c,dpl_err_pop`" should sit, for an instruction that
no longer exists. A reference counter that reads comments would find those
mentions, call the alias live, and certify exactly the state this gate exists to
catch. No gate reads prose; this one must not pretend to.

⚠️ REFERENCES ARE COUNTED TREE-WIDE, NOT PER BUILD. A name used only inside an
`IF DISK_BUILD` arm is alive in that ROM and dead in the other, and a per-build
count would report it as dead for one of them. Alive anywhere is alive.

USAGE: check_dead_aliases.py [--selftest]
"""
from __future__ import annotations
import glob
import os
import re
import sys

# ⚠️ IMPORTED FOR ITS SIDE EFFECT, and `temp-root-check` is what asked for it:
# this gate's selftest plants a fixture with `tempfile.mkdtemp()`, and a bare
# `tempfile` call escapes the `/tmp/zerobas` root. `probe_tmp` sets
# `tempfile.tempdir` once, at import, so every bare call below lands under the
# root and is cleaned up at exit -- the one-line fix the gate's own message
# names, rather than a hardcoded path that would have to be pinned forever.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "probes", "lib"))
import probe_tmp                                                  # noqa: E402,F401

TREES = ("basic/*.inc", "basic/*.asm", "sub/*.inc", "sub/*.asm",
         "disk/*.inc", "disk/*.asm")

# `NAME equ EXPR` -- EXPR captured up to a comment.
EQU = re.compile(r"^([A-Za-z_]\w*)\s+equ\s+([^;]+?)\s*(?:;.*)?$", re.IGNORECASE)
# a code label at line start
LABEL = re.compile(r"^([A-Za-z_]\w*):")
# an EXPR that is exactly one bare identifier
BARE = re.compile(r"^[A-Za-z_]\w*$")


def strip_comment(line: str) -> str:
    """Everything before the first `;`. See the header: counting a name that
    only appears in PROSE is how this defect stayed invisible."""
    return line.split(";", 1)[0]


def scan(files):
    """-> (aliases, labels, refs) over the given source files.

    aliases: name -> (target, file, line)
    labels:  set of code-label names
    refs:    name -> count of code (non-comment, non-defining) occurrences
    """
    aliases, labels, lines_by_file = {}, set(), {}
    for p in files:
        try:
            src = open(p).readlines()
        except OSError:
            continue
        lines_by_file[p] = src
        for i, ln in enumerate(src, 1):
            code = strip_comment(ln.rstrip("\n"))
            m = LABEL.match(code)
            if m:
                labels.add(m.group(1))
            m = EQU.match(code)
            if m and BARE.match(m.group(2)):
                aliases.setdefault(m.group(1), (m.group(2), p, i))

    refs = {n: 0 for n in aliases}
    for p, src in lines_by_file.items():
        for i, ln in enumerate(src, 1):
            code = strip_comment(ln.rstrip("\n"))
            for n in re.findall(r"[A-Za-z_]\w*", code):
                if n not in refs:
                    continue
                # the alias's own defining line is a definition, not a use
                if aliases[n][1] == p and aliases[n][2] == i:
                    continue
                refs[n] += 1
    return aliases, labels, refs


def dead(files):
    """-> sorted [(name, target, file, line)] of unreferenced CODE aliases."""
    aliases, labels, refs = scan(files)
    out = []
    for n, (target, p, i) in aliases.items():
        if target in labels and refs[n] == 0:
            out.append((n, target, p, i))
    return sorted(out), len(aliases), sum(1 for a in aliases.values()
                                          if a[0] in labels)


def selftest() -> int:
    import tempfile
    ok = {}
    d = tempfile.mkdtemp(prefix="aliasgate-")
    try:
        # 🔴 THE FIXTURE CARRIES ITS OWN NEGATIVE CONTROLS. An arm that only
        # ever sees a dead alias cannot show it distinguishes one.
        open(os.path.join(d, "f.asm"), "w").write(
            "real_label:\n"
            "                ret\n"
            "other_label:\n"
            "                ret\n"
            "DATA_CELL       equ     $E000\n"
            "; --- the four cases -------------------------------------------\n"
            "DEAD_ALIAS      equ     real_label\n"      # dead: no use
            "LIVE_ALIAS      equ     other_label\n"     # live: used below
            "DATA_ALIAS      equ     DATA_CELL\n"       # not a code label
            "PROSE_ALIAS     equ     real_label\n"      # only named in a COMMENT
            "                jp      LIVE_ALIAS\n"
            "                ; PROSE_ALIAS is discussed here and nowhere else,\n"
            "                ; exactly like D-NGRAM13's dpl_err_pop paragraph\n")
        got, n_alias, n_code = dead([os.path.join(d, "f.asm")])
        names = [g[0] for g in got]
        ok["A1 an unreferenced CODE alias is reported"] = "DEAD_ALIAS" in names
        ok["A2 NEGATIVE: an alias with a real call site is NOT reported"] = \
            "LIVE_ALIAS" not in names
        ok["A3 NEGATIVE: an alias of a DATA equate is NOT reported "
           "(different lifetime rules -- see the header)"] = \
            "DATA_ALIAS" not in names
        ok["A4 🔴 THE ARM THAT MATTERS: a name appearing ONLY in comments is "
           "still DEAD -- prose is not a reference, and prose is why the real "
           "one survived"] = "PROSE_ALIAS" in names
        ok["A5 the denominator is printed, not assumed"] = \
            n_alias >= 4 and n_code >= 3
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    # A6: the real tree must be scannable and the universe non-empty -- a gate
    # that finds nothing because it LOOKED at nothing is the failure mode this
    # project keeps re-learning.
    files = [f for pat in TREES for f in sorted(glob.glob(pat))]
    _got, n_alias, n_code = dead(files)
    ok["A6 the real tree yields a non-degenerate universe (a gate that scans "
       "nothing reports clean)"] = len(files) > 50 and n_alias > 5

    for k, v in ok.items():
        print(f"  SELFTEST: {'PASS' if v else 'FAIL'}  {k}")
    print(f"  SELFTEST: {sum(ok.values())}/{len(ok)} arms pass")
    return 0 if all(ok.values()) else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    files = [f for pat in TREES for f in sorted(glob.glob(pat))]
    got, n_alias, n_code = dead(files)
    print(f"dead-alias: {len(files)} source file(s), {n_alias} bare-identifier "
          f"`equ` alias(es), {n_code} of them aliasing a CODE label")
    if not got:
        print("  clean — every code-label alias has at least one call site")
        return 0
    print(f"🔴 {len(got)} UNREFERENCED CODE ALIAS(ES) — an `equ` emits no bytes, "
          f"so `check_dead_code` cannot see these:")
    for n, target, p, i in got:
        print(f"  {p}:{i}: `{n} equ {target}` — 0 references outside comments")
    print("  Delete the name, or re-point it at something that is used. "
          "⚠️ And read the prose around it: a dead alias usually has a "
          "justification paragraph that is stale in the same way.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
