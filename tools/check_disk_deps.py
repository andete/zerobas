#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""check_disk_deps -- every make target that runs a probe needing the FAT12 test
image declares `$(DISK_TEST_DSK)` as a prerequisite.

`disk/test720.dsk` is GENERATED (`make test-dsk`), not tracked -- `git ls-files`
does not list it. A target that runs a probe needing it and does NOT depend on it
works only because some earlier target happened to build it. Four slices found one
each, one at a time (D-ARYSITE `inputary`, D-FILESIDE `namspc`, D-COLDROW
`stmtpend`, and this one), which is what a class looks like when nobody has
written its enumerator. 48 targets were missing it when this check was written.

⚠️ THE DENOMINATOR IS THE HARD PART, AND A TEXT MATCH GETS IT WRONG IN BOTH
DIRECTIONS. `diskbasic_probe_badfnum.py` names the image ONLY in its module
docstring -- a text match calls it a user for the wrong reason -- while its actual
need comes from `from diskbasic_probe_lof import run_case`, which a text match
cannot see at all. Two errors that happened to cancel. So the walk is:

  * a probe NEEDS the image if any string literal in its AST contains the image
    basename (docstrings included -- a probe that talks about the image in prose
    and reaches it through a helper is still a user), or
  * it imports, transitively, a module under probes/ that does.

⚠️ WHAT THIS CHECK IS NOT. It does not claim a missing image is caught at RUNTIME.
It is not: D-DISKDEP measured all sixteen candidates with the image moved aside and
every one refused (`omsx_preflight` rc 2, an own guard rc 2, or a `shutil.copy`
traceback), so today the runtime consequence is a refusal, not a silent agreement.
That is a property of today's probes, and the dependency is what makes the refusal
never happen in the first place. docs/spec-probe-diskdep.md.

    python3 tools/check_disk_deps.py            # gate: non-zero if any target lacks it
    python3 tools/check_disk_deps.py --list     # print every target + verdict
    python3 tools/check_disk_deps.py --selftest # calibrate against known positives
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
IMAGE = "test720.dsk"
DEP = "DISK_TEST_DSK"

TARGET_RE = re.compile(r'(?m)^([A-Za-z0-9_.-]+):([^\n]*)\n((?:\t[^\n]*\n)*)')
PROBE_RE = re.compile(r'probes/\S+\.py')


def _literals_name_image(path: str) -> bool:
    """True iff any string literal in this file's AST contains the basename.

    AST, not `in open(path).read()`: a `#` comment mentioning the image is prose
    ABOUT the tree, not a use of it, and must not enlarge the denominator.
    """
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and IMAGE in node.value:
            return True
    return False


def _local_imports(path: str) -> list[str]:
    """Modules imported by `path` that resolve to a .py file under probes/."""
    try:
        tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    except (OSError, SyntaxError):
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    out = []
    for n in names:
        stem = n.split(".")[-1]
        for root, _dirs, files in os.walk(os.path.join(REPO, "probes")):
            if stem + ".py" in files:
                out.append(os.path.join(root, stem + ".py"))
    return out


def probe_needs_image(path: str, _seen: set | None = None) -> str:
    """'' if not a user, else the REASON it is one."""
    _seen = _seen if _seen is not None else set()
    real = os.path.realpath(path)
    if real in _seen:
        return ""
    _seen.add(real)
    if _literals_name_image(path):
        return "names the image"
    for dep in _local_imports(path):
        why = probe_needs_image(dep, _seen)
        if why:
            return f"imports {os.path.basename(dep)} which {why}"
    return ""


def walk() -> list[tuple[str, str, str, str]]:
    """-> [(target, verdict, probe, reason)] for every image-using target."""
    mk = open(os.path.join(REPO, "Makefile"), encoding="utf-8").read()
    rows = []
    for tgt, deps, recipe in TARGET_RE.findall(mk):
        for rel in sorted(set(PROBE_RE.findall(recipe))):
            path = os.path.join(REPO, rel)
            if not os.path.exists(path):
                continue
            why = probe_needs_image(path)
            if why:
                verdict = "OK" if DEP in deps else "MISSING-DEP"
                rows.append((tgt, verdict, rel, why))
                break
    return rows


# --- denominator floor -------------------------------------------------------
# 🔴 A FLOOR OF ZERO IS NOT A FLOOR. An empty walk exiting 2 stops the 0/0-prints-
# ALL-CONVERGED shape and NOTHING ELSE: narrow the walk to a single target and the
# gate still reports "1 of 1 declare it -- clean". The count is the claim, so the
# count is pinned, and so is a membership sample spanning every way a target
# reaches the image ([[gateblind-round2-slice]], "ask whether a LOOP'S COUNT is
# pinned by anything at all").
#
# ⚠️ THE FLOOR IS A FLOOR, NOT AN EQUALITY. Adding a probe or a target must not
# redden this gate; only LOSING coverage may. Raise it when the real count grows
# well past it, and never lower it without saying which targets went away.
MIN_TARGETS = 60          # 65 at D-DISKDEP, 2026-08-21
WITNESSES = {
    # one target per ROUTE into the class, so a walk that goes blind in one route
    # cannot pass by still finding the others
    "readvar-acceptance",      # diska handed straight to openMSX (preflight's half)
    "lnblank-acceptance",      # copies through a local -- invisible to a name regex
    "badfnum-acceptance",      # a LATENT import route -- see B2, which is the
                               # only thing that exercises it
    "lptverb-acceptance",      # the <NO DISK FIXTURE> sentinel half
    "diskbasic-acceptance",    # the disk-side runner, dep already present
}


def denominator_fault(rows) -> str:
    """'' if the walk covered its subject, else why it did not."""
    if not rows:
        return ("no image-using target found at all -- the walk has gone blind "
                "(Makefile moved? probes/ renamed?)")
    if len(rows) < MIN_TARGETS:
        return (f"the walk found {len(rows)} image-using target(s), below the "
                f"pinned floor of {MIN_TARGETS}. Either coverage was lost or the "
                f"floor is stale -- say which, do not lower it silently")
    missing = WITNESSES - {t for t, _v, _p, _w in rows}
    if missing:
        return (f"the walk lost witness target(s) {sorted(missing)} -- each is a "
                f"DIFFERENT route into the class, so losing one is a blind spot, "
                f"not a headcount")
    return ""


# --- calibration -------------------------------------------------------------
# 🔴 A GREEN RUN IS NOT BELIEVED UNTIL THE CHECK HAS CAUGHT KNOWN POSITIVES.
# D-WALLDATE's first draft caught 0 of the 4 defects it was built for and reported
# CLEAN (2026-08-19). Each vector below is a defect this check exists to catch,
# applied to a COPY of the Makefile/probe text in memory, never to the tree.
SELFTEST = [
    ("dep stripped from a target",
     lambda mk: mk.replace("stmtpend-acceptance: repack-machine $(DISK_TEST_DSK)",
                           "stmtpend-acceptance: repack-machine"),
     "stmtpend-acceptance"),
    ("dep stripped from the OTHER half of a pair",
     lambda mk: mk.replace("dskmsg-characterize: repack-machine $(DISK_TEST_DSK)",
                           "dskmsg-characterize: repack-machine"),
     "dskmsg-characterize"),
    ("dep stripped from a disk-side target",
     lambda mk: mk.replace("diskbasic-acceptance: $(DISK_ROM) $(DISK_TEST_DSK) "
                           "repack-machine",
                           "diskbasic-acceptance: $(DISK_ROM) repack-machine"),
     "diskbasic-acceptance"),
    ("dep spelled as a literal path, which `make test-dsk` does not rebuild",
     lambda mk: mk.replace("namspc-acceptance: repack-machine $(DISK_TEST_DSK)",
                           "namspc-acceptance: repack-machine disk/test720.dsk"),
     "namspc-acceptance"),
]

# 🔴 AND VECTORS OF THE OTHER SENSE. The four above all move a target from OK to
# MISSING-DEP; none can catch a walk that stops SEEING targets, which is how this
# gate would go quiet rather than loud. B1 blinds the walk and expects exit 2.
#
# 🔴 B2 IS NOT A BLINDNESS VECTOR, AND THE DIFFERENCE IS THE FINDING. The import
# route has **zero live members**: every one of the 65 targets is reached by the
# literal test, `diskbasic_probe_badfnum.py` included, because that probe happens
# to name the image in its module DOCSTRING as well as reaching it through
# `from diskbasic_probe_lof import run_case`. So blinding the import walk changes
# nothing and a "vector" for it would pass vacuously -- the shape a knife wears
# when its subject is unreachable ([[a-shadowed-guard-has-no-knife]]). The route
# is LATENT, not dead: delete that one docstring sentence -- a plausible tidy-up
# -- and the import walk becomes the only thing keeping badfnum in the
# denominator. B2 therefore CONSTRUCTS that subject (blind the literal test for
# badfnum alone) and asserts the import route still finds it, i.e. it is a
# POSITIVE CONTROL for a route nothing else exercises.
BLIND_VECTORS = [
    ("B1  the AST literal test goes blind (denominator collapses)",
     lambda: setattr(sys.modules[__name__], "_literals_name_image",
                     lambda _p: False)),
]

BADFNUM = "diskbasic_probe_badfnum.py"


def import_route_control() -> str:
    """'' if the latent import route works, else why it does not."""
    real = _literals_name_image
    try:
        setattr(sys.modules[__name__], "_literals_name_image",
                lambda p: False if p.endswith(BADFNUM) else real(p))
        hits = [(t, w) for t, _v, p, w in walk() if p.endswith(BADFNUM)]
    finally:
        setattr(sys.modules[__name__], "_literals_name_image", real)
    if not hits:
        return (f"with {BADFNUM}'s literal mention removed the walk LOSES it "
                f"entirely -- the import route is not carrying it")
    if not all(w.startswith("imports") for _t, w in hits):
        return f"found for the wrong reason: {hits[0][1]!r}"
    return ""


def selftest() -> int:
    mk_path = os.path.join(REPO, "Makefile")
    original = open(mk_path, encoding="utf-8").read()
    base = {t for t, v, _p, _w in walk() if v == "MISSING-DEP"}
    caught = 0
    print(f"baseline MISSING-DEP set: {len(base)} target(s)")
    for name, mutate, want in SELFTEST:
        mutated = mutate(original)
        if mutated == original:
            print(f"  FAULT  {name}: the vector matched nothing — it has rotted")
            continue
        try:
            open(mk_path, "w", encoding="utf-8").write(mutated)
            found = {t for t, v, _p, _w in walk() if v == "MISSING-DEP"}
        finally:
            open(mk_path, "w", encoding="utf-8").write(original)
        hit = want in found - base
        caught += hit
        print(f"  {'caught' if hit else 'MISSED'}  {name} ({want})")
    blind = 0
    for name, mutate in BLIND_VECTORS:
        real_lit = _literals_name_image
        try:
            mutate()
            fault = denominator_fault(walk())
        finally:
            setattr(sys.modules[__name__], "_literals_name_image", real_lit)
        blind += bool(fault)
        print(f"  {'caught' if fault else 'MISSED'}  {name}")
    ctl = import_route_control()
    print(f"  {'ok    ' if not ctl else 'FAULT '}  B2  import-route positive "
          f"control{'' if not ctl else ': ' + ctl}")
    total = caught + blind + (not ctl)
    want = len(SELFTEST) + len(BLIND_VECTORS) + 1
    print(f"\nself-test {total}/{want} "
          f"({caught}/{len(SELFTEST)} findings, "
          f"{blind}/{len(BLIND_VECTORS)} blindness, "
          f"{int(not ctl)}/1 latent-route control)")
    return 0 if total == want else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print every target")
    ap.add_argument("--selftest", action="store_true",
                    help="calibrate against known positives")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rows = walk()
    fault = denominator_fault(rows)
    if fault:
        print(f"INSTRUMENT FAULT: {fault}")
        return 2
    bad = [r for r in rows if r[1] == "MISSING-DEP"]
    if args.list:
        for tgt, verdict, probe, why in sorted(rows):
            print(f"{verdict:12s} {tgt:28s} {probe}  ({why})")
        print()
    print(f"{len(rows)} make target(s) run a probe needing {IMAGE}; "
          f"{len(rows) - len(bad)} declare $({DEP}), {len(bad)} do not")
    for tgt, _v, probe, why in sorted(bad):
        print(f"  MISSING-DEP  {tgt}: runs {probe} ({why}) with no $({DEP})")
    if bad:
        print(f"\nFIX: add $({DEP}) to each target's prerequisites. "
              f"`disk/{IMAGE}` is generated, not tracked.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
