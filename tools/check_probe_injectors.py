#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""check_probe_injectors -- there is ONE type-ahead injector in this tree.

D-LASTINJ (docs/spec-probe-lastinj.md §3.4). D-LATCH proved that the obvious way
to inject a REPL line -- write the payload at KEYBUF, set GETPNT := KEYBUF,
PUTPNT := KEYBUF + n -- moves GETPNT BACKWARDS, and that a callback landing on
the one instruction boundary inside C-BIOS `chget` between `ld hl,(GETPNT)` and
`ld de,(PUTPNT)` then reads the fresh buffer from offset len(previous line).
`omsx_repl.key_proc()` writes at the CURRENT GETPNT and never moves it, which is
immune by construction rather than by alignment.

SIX FILES HAD COMPOSED THEIR OWN COPY of that body. Fixing the shared injector
did nothing for any of them, and nothing in the tree would have said so: D-ECHO
filed the class as a coverage limit, D-LATCH promoted it to a correctness limit,
and both times it was closed by hand, file by file, from a list nobody generated.
This is the generator.

    python3 tools/check_probe_injectors.py          # gate: non-zero if any copy
    python3 tools/check_probe_injectors.py --list   # print every file + verdict

THE RULE. A `.py` file under probes/, tools/ or tests/ COMPOSES an injector when
its STRING LITERALS emit `debug write memory` and the file also NAMES one of the
type-ahead cursors (GETPNT/PUTPNT, by identifier or by address). Both halves are
needed and neither is sufficient: plenty of probes poke RAM through Tcl, and
plenty describe the cursors. Only writing them is composing an injector.

⚠️ COMMENTS DO NOT COUNT, AND THAT IS THE POINT OF WALKING THE AST. A raw-text
grep flags every probe that merely explains the mechanism in prose -- and this
tree explains it often, at length. The subject is what the file EMITS.

⚠️ IT FAILS CLOSED. A file that cannot be parsed is an offender, not an
exemption [[guard-that-cannot-judge-must-say-so]]. The preflight guard this gate
is shaped after shipped FAILING OPEN and it took a slice to notice.

🔴 AND IT SCORES ITSELF ON EVERY RUN. Once the last copy is re-pointed this
checker has ZERO offenders in the tree, so a gutted classifier would report a
clean walk over a tree that has one -- exactly the way fixing the D-LATCH race
silenced the only live subject the two delivery oracles had
([[fixing-the-fault-silences-the-control]]). So the classifier is run against two
FROZEN bodies before the walk: the pre-D-LATCH injector verbatim, which MUST
classify as composing, and a call-site-only body, which MUST classify clean. The
self-test is two-sided on purpose -- "flag everything" fails it just as loudly as
"flag nothing" -- and a failure REFUSES TO JUDGE rather than reporting a tally.
"""
from __future__ import annotations

import argparse
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCAN_DIRS = ("probes", "tools", "tests")

# The Tcl primitive that actually moves a byte into the emulated machine.
WRITE = "debug write memory"
# The type-ahead read/write cursors, by identifier and by address. KEYBUF itself
# is NOT here: writing the buffer is harmless, moving the cursors is the fault.
CURSORS = ("GETPNT", "PUTPNT", "0xF3FA", "0xF3F8", "0xf3fa", "0xf3f8",
           "62458", "62456")

# Structural exemptions: files whose JOB is to hold an injector body. Three, each
# with a reason that is about the file's role, not its name.
EXEMPT = {
    "probes/lib/omsx_repl.py":
        "THE one injector -- key_proc() is what every probe must call",
    "probes/lib/latch_check.py":
        "holds the pre-D-LATCH body FROZEN as row A's subject; it must still "
        "mangle or `make latch-check` goes red",
    "tools/check_probe_injectors.py":
        "this file -- it holds the same frozen body as its own self-test",
    # 🔴 A GATE THAT DETECTS INJECTORS CLASSIFIES ITS OWN DETECTOR AS ONE.
    # This file emits no Tcl and boots nothing: the `debug write memory` in it
    # is the NEEDLE of a regex that asserts about `key_proc()`'s output, and it
    # names GETPNT/PUTPNT because those are the addresses it checks are not
    # written. Same shape as the echo guard's false-positive classes, found the
    # same way -- by running the corpus [[echo-guard-false-positives-found-by-corpus]].
    "tests/test_key_drain_guard.py":
        "host-side ASSERTIONS about key_proc()'s two rules (D-LATCH2); it "
        "names the cursors and the write in order to check them, and emits no "
        "Tcl at all",
}

# --- the self-test bodies, frozen ------------------------------------------
# FROZEN_FAULT is `disk_probe_getput.build_tcl`'s __inj as it stood at 76ea851,
# which is character-identical (after constant folding) to latch_check.OLD_KEY.
FROZEN_FAULT = '''
_GETPNT = 0xF3FA
_PUTPNT = 0xF3F8
def build_tcl():
    return ("proc __inj {s} {\\n"
            "  append s \\"\\\\r\\"\\n"
            "  set n [string length $s]\\n"
            f"  debug write memory [expr {{{_GETPNT}}}] 0\\n"
            f"  debug write memory {_PUTPNT} 0\\n"
            "}\\n")
'''
# FROZEN_CLEAN is the shape a re-pointed probe has: it CALLS the injector and
# names no cursor.
#
# 🔴 IT POKES RAM ON PURPOSE, AND THE FIRST VERSION DID NOT. Written without the
# `debug write memory` line it was clean for a TRIVIAL reason -- it emitted no
# write at all -- so a classifier that dropped the cursor half and flagged every
# file that writes memory PASSED the self-test anyway. The knife aimed at that
# side did not cut, which is the finding, not the classifier's innocence
# [[knife-found-defect-in-own-fix]]. A negative control has to be the thing that
# would actually be mis-flagged: a probe that writes emulated memory for an
# ordinary reason and leaves the type-ahead cursors alone. Many in this tree do.
FROZEN_CLEAN = '''
import omsx_repl
SCRMOD = 0xFCAF
def build_tcl():
    return ("set throttle off\\n"
            f"debug write memory {SCRMOD} 1\\n"
            + omsx_repl.key_proc()
            + "proc __inj {s} { append s \\"\\\\r\\"; __key $s }\\n")
'''


def _emitted_strings(tree: ast.AST) -> str:
    """Every string this module can EMIT, concatenated. Docstrings included --
    they are string literals too, and a docstring cannot emit Tcl, so including
    them only makes the classifier more eager, never less."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
    return "\n".join(out)


def _named(tree: ast.AST) -> set[str]:
    """Every identifier and attribute the module NAMES. This is what sees
    through an f-string (`{_GETPNT}`) and through a %-placeholder whose value
    comes from `R.GETPNT` -- neither of which appears as text in a literal."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def classify(src: str) -> tuple[str, str]:
    """-> (verdict, why). Verdicts: COMPOSES / CLEAN / UNPARSEABLE."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return "UNPARSEABLE", f"cannot parse ({e})"
    lits = _emitted_strings(tree)
    if WRITE not in lits:
        return "CLEAN", f"emits no {WRITE!r}"
    names = _named(tree)
    hits = sorted({c for c in CURSORS if c in lits or c in names}
                  | {n for n in names
                     if "getpnt" in n.lower() or "putpnt" in n.lower()})
    if not hits:
        return "CLEAN", f"emits {WRITE!r} but names no type-ahead cursor"
    return "COMPOSES", f"emits {WRITE!r} and names {', '.join(hits)}"


def self_test() -> list[str]:
    """Row A / row B. Returns the failures; empty means the classifier still
    recognises the fault AND still clears the fix."""
    bad = []
    v, why = classify(FROZEN_FAULT)
    if v != "COMPOSES":
        bad.append(f"the FROZEN pre-D-LATCH injector classifies {v} ({why}) -- "
                   f"this classifier no longer recognises the fault it exists "
                   f"for, so a clean walk would prove nothing")
    v, why = classify(FROZEN_CLEAN)
    if v != "CLEAN":
        bad.append(f"the FROZEN re-pointed body classifies {v} ({why}) -- this "
                   f"classifier flags the FIX, so every walk is noise")
    return bad


def walk() -> list[tuple[str, str, str]]:
    out = []
    for d in SCAN_DIRS:
        for root, _dirs, files in os.walk(os.path.join(REPO, d)):
            for fn in sorted(files):
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, REPO)
                with open(path, encoding="utf-8", errors="replace") as f:
                    verdict, why = classify(f.read())
                if rel in EXEMPT:
                    verdict, why = "EXEMPT", EXEMPT[rel]
                out.append((rel, verdict, why))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true",
                    help="print every scanned file and its verdict")
    args = ap.parse_args()

    failures = self_test()
    if failures:
        sys.stdout.flush()
        print("injector-check: CANNOT JUDGE -- the classifier failed its own "
              "frozen self-test:", file=sys.stderr)
        for m in failures:
            print(f"  {m}", file=sys.stderr)
        return 2
    print("injector-check: self-test PASS  (the frozen pre-D-LATCH body still "
          "classifies COMPOSES; the frozen re-pointed body still classifies CLEAN)")

    files = walk()
    offenders = [f for f in files if f[1] in ("COMPOSES", "UNPARSEABLE")]
    exempt = [f for f in files if f[1] == "EXEMPT"]

    if args.list:
        for rel, verdict, why in files:
            if verdict != "CLEAN" or args.list:
                print(f"  {verdict:<12} {rel}\n{'':16}{why}")

    print(f"\nfiles scanned                      : {len(files)}")
    print(f"  exempt (named, structural)       : {len(exempt)}")
    print(f"  compose their own injector       : "
          f"{sum(1 for f in offenders if f[1] == 'COMPOSES')}")
    print(f"  UNPARSEABLE (fails closed)       : "
          f"{sum(1 for f in offenders if f[1] == 'UNPARSEABLE')}")

    # ⚠️ 0 files scanned is not a clean tree, it is a broken walk.
    if not files:
        print("\nAPPARATUS FAILURE: this gate scanned NOTHING -- check SCAN_DIRS.",
              file=sys.stderr)
        return 2

    if offenders:
        sys.stdout.flush()
        print("\nFILES COMPOSING THEIR OWN TYPE-AHEAD INJECTOR -- each one ships "
              "the D-LATCH delivery race that `omsx_repl.key_proc()` no longer "
              "has, and no oracle covers them:", file=sys.stderr)
        for rel, verdict, why in offenders:
            print(f"  {verdict:<12} {rel}\n{'':16}{why}", file=sys.stderr)
        print("\nFIX: emit `omsx_repl.key_proc()` and call `__key`, instead of "
              "writing GETPNT/PUTPNT here (docs/spec-probe-lastinj.md §3.3).",
              file=sys.stderr)
        return 1

    print("\nALL PASS -- one injector in the tree, and it is the one "
          "`make latch-check` scores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
