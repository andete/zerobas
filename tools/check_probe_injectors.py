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

THE TWO RULES. A `.py` file under probes/, tools/ or tests/ offends when

  (a) it COMPOSES -- its STRING LITERALS emit `debug write memory` and the file
      also NAMES one of the type-ahead cursors (GETPNT/PUTPNT, by identifier or
      by address). Both halves are needed and neither is sufficient: plenty of
      probes poke RAM through Tcl, and plenty describe the cursors. Only writing
      them is composing an injector.

  (b) it HANDLES -- it names a FROZEN-BODY SYMBOL defined in another module.
      D-INJSINK (docs/spec-probe-injsink.md §2.2): `latch_check.OLD_KEY` IS the
      pre-D-LATCH injector, and `import latch_check; return latch_check.OLD_KEY`
      shipped the whole delivery race past rule (a) without a single literal of
      its own. Rule (b) is deliberately blunt -- the offence is REACHING for the
      body, not what you do with it afterwards -- because a use analysis fine
      enough to excuse a legitimate reader cannot see through `"".join(parts)`,
      which is how half the probes here build Tcl (spec §2.3).

⚠️ COMMENTS DO NOT COUNT, AND THAT IS THE POINT OF WALKING THE AST. A raw-text
grep flags every probe that merely explains the mechanism in prose -- and this
tree explains it often, at length. The subject is what the file EMITS.

⚠️ AND DOCSTRINGS DO COUNT, WHICH IS WHY THERE IS NO "EMITTED VS MATCHED AGAINST"
RULE HERE. D-LATCH2 filed that question. It was measured (spec §2.3): a
per-literal sink whitelist clears a regex needle but NOT the prose sentence next
to it, so it does not clear the file it was built for; and the all-uses rule that
would clear prose is defeated by one ordinary local call. An exemption is a
reviewed line in a file; a hole is not.

⚠️ IT FAILS CLOSED. A file that cannot be parsed is an offender, not an
exemption [[guard-that-cannot-judge-must-say-so]]. The preflight guard this gate
is shaped after shipped FAILING OPEN and it took a slice to notice.

🔴 AND IT SCORES ITSELF ON EVERY RUN. With no offenders left in the tree a gutted
classifier would report a clean walk over a tree that has one -- exactly the way
fixing the D-LATCH race silenced the only live subject the two delivery oracles
had ([[fixing-the-fault-silences-the-control]]). So FOUR frozen bodies are
classified before the walk, two per rule, and each pair is two-sided on purpose
so that "flag everything" fails as loudly as "flag nothing". A failure REFUSES TO
JUDGE rather than reporting a tally.

🔴 RULE (b)'s REGISTRY IS GENERATED, SO IT CAN GO EMPTY AND TAKE THE RULE WITH
IT. Three symbols that exist by construction are PINNED; their absence is
`CANNOT JUDGE`, not a clean walk -- the same reasoning as "0 files scanned is not
a clean tree, it is a broken walk".
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

# Structural exemptions. Each states its CLASS, and the class is what the next
# reader has to agree with -- not the file's name (D-INJSINK §3.4):
#
#   SHIPS    this file IS the one injector.
#   HOLDS    this file DEFINES a frozen fault body, kept as a control.
#   HANDLES  this file NAMES a frozen body defined elsewhere, to assert about
#            it. 🎯 A NARROW CLAIM, AND IT IS CHECKED: a HANDLES file must carry
#            no `debug write memory` literal of its own. Restate the injector's
#            vocabulary here and the exemption stops covering you.
#
# ⚠️ Adding an entry: state the class, the symbols it names, and why they cannot
# reach the machine. The gate checks the first half; the reviewer of the slice
# that adds it owns the second (spec §5).
EXEMPT = {
    "probes/lib/omsx_repl.py": (
        "SHIPS",
        "THE one injector -- key_proc() is what every probe must call"),
    "probes/lib/latch_check.py": (
        "HOLDS",
        "defines OLD_KEY (pre-D-LATCH) and GETPNT_KEY (pre-D-LATCH2) FROZEN as "
        "rows A/D's subjects; they must still mangle or `make latch-check` "
        "goes red"),
    "tools/check_probe_injectors.py": (
        "HOLDS",
        "this file -- it defines the frozen bodies of its own self-test"),
    "tests/test_key_drain_guard.py": (
        "HANDLES",
        "host-side ASSERTIONS about key_proc()'s two rules (D-LATCH2). It names "
        "latch_check.OLD_KEY and .GETPNT_KEY as R4's positive controls, passes "
        "them to a bool-returning predicate, emits no Tcl and boots nothing"),
}

# --- the self-test bodies, frozen ------------------------------------------
# Rule (a), row A. FROZEN_FAULT is `disk_probe_getput.build_tcl`'s __inj as it
# stood at 76ea851, character-identical (after constant folding) to
# latch_check.OLD_KEY.
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
# Rule (a), row B. FROZEN_CLEAN is the shape a re-pointed probe has: it CALLS the
# injector and names no cursor.
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
# Rule (b), row C. THE FROZEN FAULT, SHIPPED WITHOUT A LITERAL OF ITS OWN. This
# body passed rule (a) clean on the tree as it stood at 07e9c0a while emitting
# the pre-D-LATCH injector verbatim (D-INJSINK §2.2, H2). It is the POSITIVE that
# stops rule (b) from being decoration.
FROZEN_LAUNDER = '''
import latch_check
def build_tcl():
    return "set throttle off\\n" + latch_check.OLD_KEY
'''
# Rule (b), row D. The two-sided half: importing from the SAME module is not the
# offence, naming a FROZEN BODY is. Without this row "flag every importer" would
# pass -- and `probes/lib` is on sys.path for every probe in the tree.
FROZEN_IMPORT_OK = '''
import latch_check
def run():
    return latch_check.HIT
'''
# The registry the self-test judges against: fixed, so the four rows above mean
# the same thing whatever the tree looks like.
FROZEN_REGISTRY = {"latch_check": {"OLD_KEY": "probes/lib/latch_check.py",
                                   "GETPNT_KEY": "probes/lib/latch_check.py"}}

# 🔴 Registry symbols that exist BY CONSTRUCTION. A generated registry that comes
# back without these did not find the tree, and rule (b) would then pass every
# file silently.
PINNED = (("latch_check", "OLD_KEY"),
          ("latch_check", "GETPNT_KEY"),
          ("check_probe_injectors", "FROZEN_FAULT"))


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


def _frozen_bodies(tree: ast.AST) -> set[str]:
    """The module-level names this file binds to an expression whose STRING
    LITERALS carry a `debug write memory`. That is a frozen injector body by any
    other name -- and `latch_check.OLD_KEY` is bound by a triple-quoted template
    followed by `% dict(...)`, not by a bare constant, so this looks at the whole
    expression rather than at its type."""
    out = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if WRITE not in _emitted_strings(value):
            continue
        for t in targets:
            if isinstance(t, ast.Name):
                out.add(t.id)
    return out


def _foreign_frozen(tree: ast.AST, own_module: str,
                    registry: dict[str, dict[str, str]]) -> list[str]:
    """Frozen-body symbols this module names from ANOTHER module, resolved
    through its imports. Module identity is the basename: `probes/lib` is on
    sys.path for every probe, so `import latch_check` is how the tree spells it,
    and the walk measures the basenames collision-free (spec §2.4)."""
    alias: dict[str, str] = {}      # local module alias -> module basename
    frm: dict[str, tuple[str, str]] = {}   # local name -> (module, original)
    star: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                alias[(a.asname or a.name).split(".")[-1]] = \
                    a.name.split(".")[-1]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.split(".")[-1]
            for a in node.names:
                if a.name == "*":
                    star.add(mod)
                else:
                    frm[a.asname or a.name] = (mod, a.name)

    hits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            mod = alias.get(node.value.id)
            if mod and node.attr in registry.get(mod, {}):
                hits.add(f"{mod}.{node.attr}")
        elif isinstance(node, ast.Name) and node.id in frm:
            mod, orig = frm[node.id]
            if orig in registry.get(mod, {}):
                hits.add(f"{mod}.{orig}")
    # `import *` is eager on purpose: the names are not enumerable from here.
    for mod in star:
        for sym in registry.get(mod, {}):
            hits.add(f"{mod}.{sym} (via `import *`)")
    return sorted(h for h in hits if not h.startswith(own_module + "."))


def classify(src: str, registry: dict[str, dict[str, str]] | None = None,
             own_module: str = "") -> tuple[str, str]:
    """-> (verdict, why). COMPOSES / HANDLES / CLEAN / UNPARSEABLE.

    Rule (a) is checked first: a file that composes its own body is reported as
    composing it even if it also reaches for a frozen one."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return "UNPARSEABLE", f"cannot parse ({e})"
    lits = _emitted_strings(tree)
    if WRITE in lits:
        names = _named(tree)
        hits = sorted({c for c in CURSORS if c in lits or c in names}
                      | {n for n in names
                         if "getpnt" in n.lower() or "putpnt" in n.lower()})
        if hits:
            return "COMPOSES", f"emits {WRITE!r} and names {', '.join(hits)}"
        why_a = f"emits {WRITE!r} but names no type-ahead cursor"
    else:
        why_a = f"emits no {WRITE!r}"
    foreign = _foreign_frozen(tree, own_module, registry or {})
    if foreign:
        return "HANDLES", ("names the frozen injector body "
                           + ", ".join(foreign))
    return "CLEAN", why_a


def self_test() -> list[str]:
    """Rows A-D: two per rule, each pair two-sided. Returns the failures; empty
    means the classifier still recognises both faults AND still clears both
    fixes."""
    bad = []
    rows = (
        ("A", FROZEN_FAULT, "COMPOSES", "the FROZEN pre-D-LATCH injector",
         "this classifier no longer recognises the fault it exists for, so a "
         "clean walk would prove nothing"),
        ("B", FROZEN_CLEAN, "CLEAN", "the FROZEN re-pointed body",
         "this classifier flags the FIX, so every walk is noise"),
        ("C", FROZEN_LAUNDER, "HANDLES",
         "the FROZEN body shipped by import, with no literal of its own",
         "rule (b) is decoration: the pre-D-LATCH injector can be emitted "
         "verbatim past this gate (docs/spec-probe-injsink.md §2.2)"),
        ("D", FROZEN_IMPORT_OK, "CLEAN",
         "an ordinary import from the same module",
         "rule (b) flags every importer of probes/lib, so every walk is noise"),
    )
    for tag, body, want, what, hurt in rows:
        v, why = classify(body, FROZEN_REGISTRY, own_module="_selftest")
        if v != want:
            bad.append(f"row {tag}: {what} classifies {v} ({why}), want {want} "
                       f"-- {hurt}")
    return bad


def frozen_registry() -> dict[str, dict[str, str]]:
    """Every module-level frozen injector body in the tree, by module basename.
    GENERATED, the way this gate replaced a hand-maintained list in the first
    place [[lastinj-slice]]."""
    reg: dict[str, dict[str, str]] = {}
    for rel, src in _sources():
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue          # the walk reports it as UNPARSEABLE
        mod = os.path.basename(rel)[:-3]
        for name in _frozen_bodies(tree):
            reg.setdefault(mod, {})[name] = rel
    return reg


def _sources():
    for d in SCAN_DIRS:
        for root, _dirs, files in os.walk(os.path.join(REPO, d)):
            for fn in sorted(files):
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(root, fn)
                with open(path, encoding="utf-8", errors="replace") as f:
                    yield os.path.relpath(path, REPO), f.read()


def walk(registry) -> list[tuple[str, str, str]]:
    out = []
    for rel, src in _sources():
        verdict, why = classify(registry=registry, src=src,
                                own_module=os.path.basename(rel)[:-3])
        if rel in EXEMPT:
            cls, why_x = EXEMPT[rel]
            # 🎯 A HANDLES claim is NARROW, and here is where it is checked. The
            # exemption covers naming someone else's frozen body; it does not
            # cover composing one.
            if cls == "HANDLES" and verdict in ("COMPOSES", "UNPARSEABLE"):
                verdict = "BAD EXEMPTION"
                why = (f"claims HANDLES but {why} -- a HANDLES exemption covers "
                       f"naming someone else's frozen body, not composing one "
                       f"(spec §3.4)")
            else:
                verdict, why = f"EXEMPT/{cls}", why_x
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
    print("injector-check: self-test PASS  (rows A-D: the frozen pre-D-LATCH "
          "body COMPOSES, the re-pointed body is CLEAN, the imported frozen "
          "body HANDLES, an ordinary import is CLEAN)")

    registry = frozen_registry()
    missing = [f"{m}.{n}" for m, n in PINNED if n not in registry.get(m, {})]
    if missing:
        sys.stdout.flush()
        print("injector-check: CANNOT JUDGE -- the frozen-body registry is "
              "missing symbols that exist by construction, so rule (b) would "
              "pass every file silently:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 2
    n_sym = sum(len(v) for v in registry.values())
    print(f"injector-check: frozen-body registry: {n_sym} symbols across "
          f"{len(registry)} modules, all {len(PINNED)} pinned symbols present")

    files = walk(registry)
    offenders = [f for f in files
                 if f[1] in ("COMPOSES", "HANDLES", "UNPARSEABLE",
                             "BAD EXEMPTION")]
    exempt = [f for f in files if f[1].startswith("EXEMPT/")]

    if args.list:
        for rel, verdict, why in files:
            print(f"  {verdict:<14} {rel}\n{'':18}{why}")
        print("\n  frozen-body registry:")
        for mod in sorted(registry):
            for sym in sorted(registry[mod]):
                print(f"    {mod}.{sym:<14} <- {registry[mod][sym]}")

    print(f"\nfiles scanned                      : {len(files)}")
    print(f"  exempt (named, structural)       : {len(exempt)}")
    print(f"  compose their own injector       : "
          f"{sum(1 for f in offenders if f[1] == 'COMPOSES')}")
    print(f"  handle a frozen injector body    : "
          f"{sum(1 for f in offenders if f[1] == 'HANDLES')}")
    print(f"  UNPARSEABLE (fails closed)       : "
          f"{sum(1 for f in offenders if f[1] == 'UNPARSEABLE')}")
    print(f"  exemption claimed too wide       : "
          f"{sum(1 for f in offenders if f[1] == 'BAD EXEMPTION')}")

    # ⚠️ 0 files scanned is not a clean tree, it is a broken walk.
    if not files:
        print("\nAPPARATUS FAILURE: this gate scanned NOTHING -- check SCAN_DIRS.",
              file=sys.stderr)
        return 2

    if offenders:
        sys.stdout.flush()
        print("\nFILES THAT CAN PUT A TYPE-AHEAD INJECTOR INTO THE MACHINE "
              "WITHOUT GOING THROUGH `omsx_repl.key_proc()` -- each one ships "
              "the D-LATCH delivery race that key_proc no longer has, and no "
              "oracle covers them:", file=sys.stderr)
        for rel, verdict, why in offenders:
            print(f"  {verdict:<14} {rel}\n{'':18}{why}", file=sys.stderr)
        print("\nFIX: emit `omsx_repl.key_proc()` and call `__key`, instead of "
              "writing GETPNT/PUTPNT here or reaching for a frozen body "
              "(docs/spec-probe-lastinj.md §3.3, docs/spec-probe-injsink.md §3.3).",
              file=sys.stderr)
        return 1

    print("\nALL PASS -- one injector in the tree, and it is the one "
          "`make latch-check` scores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
