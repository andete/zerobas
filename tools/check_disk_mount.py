#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKMOUNT — a scratch probe that types a DRIVE verb must mount a disk.

TODO.md, filed 2026-08-22: booting `C-BIOS_MSX1_EU_REPACK_DISK` without `diska=`
made `OPEN"TS.TXT"FOR OUTPUT AS #1` answer **ERR 59** -- which is exactly what a
channel-ceiling violation looks like. **The apparatus fault reads as a language
rule**, and a probe that hits it reports a BASIC finding that does not exist.

\U0001f3af THE LIBRARY HALF IS ALREADY BUILT: `probe_sides.diska()` hands the
image only to machines that have a drive, and `require_disk()` refuses outright
for a probe whose rows are meaningless without one. What was never done is the
DENOMINATOR -- nobody counted how many scratch probes still type a disk verb at
a machine with no image mounted.

\U0001f534 AND A NAIVE SCAN WOULD BE WRONG, WHICH IS THE DESIGN. Not every
`OPEN"` needs a drive: `LPT:`, `CRT:`, `CAS:` and `GRP:` are DEVICE channels,
`LOAD"CAS:"`/`SAVE"CAS:"` are tape, and a probe that only ever mentions those is
correct with no disk at all. Counting them would inflate the finding and claim
apparatus debt that does not exist
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].

So a file is REPORTED only when BOTH hold:
  * some string literal in it types a verb that reaches the DRIVE, after the
    device and cassette forms are excluded; and
  * no `diska` appears anywhere in the file.

\U0001f534 AND THE FIRST CUT WAS TEXTUAL, WHICH PUT PROSE IN THE FINDING. It read
every non-comment line, so `fatverb_knives`, `filesguard_knife`, `ngram12_knives`
and others matched on the word `FILES` or `LOAD"file"` **inside their own
docstrings**, and `bareform_probe` matched a PYTHON LIST of keyword names. 29
hits, most of them sentences. The scan now parses with `ast` and tests only
string literals that are NOT docstrings -- the strings a probe could actually
type at a machine.

\U0001f7e2 AND A NO-MOUNT IS SOMETIMES CORRECT. `nodisk_probe` types `DSKF(0)`
at the DISKLESS target on purpose: the absence of a drive IS its subject. Files
whose text names the diskless machine are reported separately rather than
counted as debt.

\U0001f534 AND THE SECOND CUT WAS STILL WRONG, IN THE WAY IT HAD ALREADY WARNED
ABOUT. Seven probes typed `OPEN"TS.DAT"AS #1 LEN=128` with no `diska` anywhere
in the file -- and they mount correctly, through `basic_probe_fldwidth`, whose
`"dsk"` row tag selects a config that hands `run_cases` a writable copy. The
scan now FOLLOWS IMPORTS: a file counts as mounting if it, or any tracked module
it imports, mentions `diska`. Reading one hit is what found this; the caveat was
already written and I still had to go and look
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].

⚠️ STILL A SHORTLIST, NOT A VERDICT. Every hit prints the literal that triggered
it, because the next false positive will be a shape this docstring has not
imagined either.
"""
from __future__ import annotations

import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(ROOT, "scratchpad")
# ⚠️ Imported for its side effect: it points `tempfile` at the /tmp/zerobas root,
# which `temp-root-check` requires of every bare tempfile call below.
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402,F401

# Verbs that reach the drive. `OPEN`/`LOAD`/`SAVE`/`BLOAD`/`BSAVE` are handled
# separately because their DEVICE forms must be excluded first.
DRIVE_VERBS = re.compile(
    r"\b(FILES|LFILES|KILL|NAME\s+\"|COPY\s+\"|DSKI\$|DSKO\$|DSKF)\b")
FILE_OPEN = re.compile(r"\b(OPEN|LOAD|SAVE|BLOAD|BSAVE|MERGE|RUN)\s*\"([^\"]*)\"")
DEVICE = re.compile(r"^(LPT|CRT|CAS|GRP|COM)\s*:", re.I)


# \U0001f534 THE THREE KNOWN-BENIGN HITS, EACH WITH THE REASON READ OUT OF THE
# FILE. The set may shrink freely; it grows only in a visible diff carrying a
# sentence, which is the same discipline as the other pinned sets in tools/.
ALLOW = {
    "filesguard2_knife.py":
        "the literal is the knife's own VERDICT MESSAGE ('...every plain LFILES "
        "control held...'), printed to stdout and never typed at a machine",
    "strtm_probe.py":
        "`KILL 5` is a Type-mismatch row (t.kill, expecting 'bail-missed') -- a "
        "NUMERIC argument raises before any drive access, so no image is needed",
    "tierscope_sweep.py":
        "prose in a non-docstring string ('an entry naming ex_poke and the FILES "
        "verb'), describing the tier scope rather than driving a machine",
}


def needs_drive(line: str) -> str | None:
    m = DRIVE_VERBS.search(line)
    if m:
        return m.group(1)
    for verb, arg in FILE_OPEN.findall(line):
        if DEVICE.match(arg.strip()):
            continue          # a device or cassette channel -- no drive needed
        if not arg.strip():
            continue          # `RUN ""` and friends: not a filename
        return f'{verb}"{arg[:20]}"'
    return None


SEARCH_DIRS = ("scratchpad", os.path.join("probes", "basic"),
               os.path.join("probes", "lib"))


def imported_modules(src: str):
    """Module names this file imports, in any of the three probe directories."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def mounts(src: str, seen=None) -> bool:
    """True if this file -- or anything it imports -- hands over a `diska`.

    ONE level of import is followed, and that is a stated limit rather than an
    oversight: the frameworks in this tree mount directly, and chasing the whole
    graph would make a shortlist into a static analyser.
    """
    if "diska" in src:
        return True
    for mod in imported_modules(src):
        for d in SEARCH_DIRS:
            cand = os.path.join(ROOT, d, mod + ".py")
            if os.path.exists(cand):
                try:
                    if "diska" in open(cand, errors="replace").read():
                        return True
                except OSError:
                    pass
    return False


def typed_strings(src: str):
    """Every string literal in the file EXCEPT docstrings.

    A docstring is prose about the probe; a literal anywhere else is something
    the probe may hand to the machine. Distinguishing them is the whole
    difference between a denominator and a word count.
    """
    tree = ast.parse(src)
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docs.add(id(body[0].value))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docs):
            yield node.value


def scan(scratch=SCRATCH, floor=50) -> int:
    files = sorted(f for f in os.listdir(scratch) if f.endswith(".py"))
    if len(files) < floor:
        print(f"\U0001f534 REFUSING: only {len(files)} scratch .py found; the "
              f"corpus is hundreds. The scan broke, and an empty finding would "
              f"read as good news.")
        return 2
    hits, mounted, clean, excused = [], 0, 0, []
    for name in files:
        path = os.path.join(scratch, name)
        try:
            src = open(path, errors="replace").read()
        except OSError:
            continue
        trig = None
        try:
            lits = list(typed_strings(src))
        except SyntaxError:
            continue
        for lit in lits:
            t = needs_drive(lit)
            if t:
                trig = (t, lit.strip()[:96].replace("\n", " "))
                break
        if not trig:
            clean += 1
            continue
        if mounts(src):
            mounted += 1
            continue
        if name in ALLOW:
            excused.append(name)
            continue
        hits.append((name, trig, "nodisk" in src.lower()))

    # \U0001f534 ONLY THE REAL CORPUS CAN MAKE AN EXCUSE STALE. Scanning any
    # other directory trivially fails to trip all three, so a blanket
    # `set(ALLOW) - set(excused)` reported them all stale -- which is how the
    # selftest's own S4/S5 arms went red against a temp corpus. The excuses name
    # files in scratchpad/; nowhere else has an opinion about them.
    stale = (sorted(set(ALLOW) - set(excused))
             if os.path.abspath(scratch) == os.path.abspath(SCRATCH) else [])
    print(f"disk-mount: {len(files)} scratch .py — no drive verb {clean}, "
          f"drive verb AND mounts {mounted}, excused {len(excused)}, "
          f"\U0001f534 unmounted {len(hits)}")
    deliberate = [h for h in hits if h[2]]
    debt = [h for h in hits if not h[2]]
    for name, (verb, ln), _ in debt:
        print(f"  {name}")
        print(f"      typed literal {verb}   {ln}")
    if deliberate:
        print(f"\n  \U0001f7e2 {len(deliberate)} more name the DISKLESS target, "
              f"where having no drive is the subject rather than an omission:")
        for name, (verb, _), _ in deliberate:
            print(f"     {name}  ({verb})")
    hits = debt
    if not hits:
        print("  none — every scratch probe that types a drive verb mounts an "
              "image, or is excused with a reason.")
    if stale:
        print(f"\U0001f534 {len(stale)} STALE excuse(s) — the file no longer "
              f"trips the scan, so the entry hides nothing and should go: "
              + " ".join(stale))
    print("\n⚠️  TEXTUAL SHORTLIST, NOT A VERDICT: a hit may be a verb "
          "inside a docstring, or a probe that mounts through a helper not "
          "spelled `diska`. Read the line before believing it.")
    return 1 if (hits or stale) else 0





def selftest() -> int:
    """\U0001f534 PLANT BOTH DIRECTIONS. A gate whose corpus has been clean since
    the day it was written would print the same confident zero if its matcher
    had rotted to `return None` [[a-knife-can-be-inert-because-the-build-did-not-happen]]."""
    import tempfile
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else '\U0001f534 FAIL'}  {name}")
        ok = ok and bool(cond)

    arm("S1 the live scratchpad is clean", scan() == 0)
    with tempfile.TemporaryDirectory() as d:
        for i in range(60):                      # clear the degenerate floor
            open(os.path.join(d, f"filler{i}.py"), "w").write("X = 1\n")
        arm("S2 a corpus with no drive verb is green", scan(d) == 0)
        open(os.path.join(d, "offender_probe.py"), "w").write(
            'CASES = [("r.one", \'OPEN"TS.DAT"AS #1 LEN=128\')]\n')
        arm("S3 a probe that types OPEN\"TS.DAT\" with no mount goes RED",
            scan(d) == 1)
        # ...and the same file WITH a mount is green again: this is what proves
        # the arm keys on the mounting and not merely on the verb.
        open(os.path.join(d, "offender_probe.py"), "a").write(
            'kw = {"diska": "copy.dsk"}\n')
        arm("S4 ...and adding a diska= makes it green (the control)", scan(d) == 0)
        # A device channel must NOT trip it -- that is the false-positive class
        # this scan exists to avoid.
        open(os.path.join(d, "device_probe.py"), "w").write(
            'CASES = [("r.lpt", \'OPEN"LPT:" FOR OUTPUT AS #1\')]\n')
        arm("S5 a DEVICE channel (LPT:) is not a drive verb", scan(d) == 0)
    print("selftest:", "GREEN" if ok else "\U0001f534 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(scan())
