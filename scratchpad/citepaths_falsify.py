#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Falsification for tools/check_citation_paths.py (docs/spec-citation-paths-gate.md).

Every RED arm plants a citation that must be FOUND; every GREEN arm plants text
that must NOT be. 🔴 THE GREEN ARMS ARE THE LOAD-BEARING ONES: a checker whose
corpus contains the note describing its own exception will flag the exception,
which is how D-KNIFEGUARD's basename detector flagged the one file the TODO
sentence was listing as NOT in the class.

⚠️ RESTORE IS REGISTERED BESIDE THE READ, not at the end of the loop body: an
assertion firing mid-run must not leave a doc PLANTED
([[zerobas-gate-operating-rules]], D-KNIFEGUARD).
"""
import atexit
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "probes" / "lib"))
import probe_tmp                        # noqa: E402,F401

DOC = ROOT / "docs" / "spec-basic-evferr.md"      # any COMMITTED doc will do
CHECK = [sys.executable, str(ROOT / "tools" / "check_citation_paths.py")]

_original = DOC.read_bytes()
atexit.register(lambda: DOC.write_bytes(_original))


def run():
    p = subprocess.run(CHECK, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def plant(text):
    DOC.write_bytes(_original + b"\n\n" + text.encode())


def restore():
    DOC.write_bytes(_original)


def arm(label, text, want_rc, want_in=None, want_not_in=None):
    plant(text)
    rc, out = run()
    restore()
    ok = rc == want_rc
    if ok and want_in:
        ok = want_in in out
    if ok and want_not_in:
        ok = want_not_in not in out
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: rc={rc} (want {want_rc})")
    if not ok:
        print("    ---- output ----")
        print("    " + "\n    ".join(out.splitlines()[-25:]))
    return ok


def main():
    print("=== green control: the tree as it stands ===")
    rc, out = run()
    base_ok = rc == 0
    print(f"  {'PASS' if base_ok else 'FAIL'}  clean tree: rc={rc} (want 0)")
    if not base_ok:
        print(out)
        return 1

    results = [base_ok]
    print("=== RED arms: a citation that cannot resolve in a clone ===")
    # GONE — a path that is on no disk anywhere.
    results.append(arm("GONE", "See `scratchpad/zz_no_such_probe.py` for the run.",
                       1, want_in="GONE"))
    # IGNORED — on disk, but .gitignore excludes its whole class.
    sh = ROOT / "scratchpad" / "zz_falsify_driver.sh"
    sh.write_text("#!/bin/sh\ntrue\n")
    atexit.register(lambda: sh.unlink(missing_ok=True))
    results.append(arm("IGNORED", "Driver: `scratchpad/zz_falsify_driver.sh`.",
                       1, want_in="IGNORED"))
    sh.unlink(missing_ok=True)
    # UNTRACKED — on disk, trackable class, simply not committed.
    py = ROOT / "scratchpad" / "zz_falsify_probe.py"
    py.write_text("# falsification plant\n")
    atexit.register(lambda: py.unlink(missing_ok=True))
    results.append(arm("UNTRACKED", "Probe: `scratchpad/zz_falsify_probe.py`.",
                       1, want_in="UNTRACKED"))
    py.unlink(missing_ok=True)

    print("=== GREEN arms: the shapes that must NOT fire (load-bearing) ===")
    # THE fastgates SHAPE: prose naming a file that is not in the repo.
    results.append(arm("bare basename in prose",
                       "zz_no_such_probe.py is deliberately NOT in the class.", 0))
    # The placeholder every doc about this check has to be able to write.
    results.append(arm("placeholder path",
                       "for every scratchpad/<name>.py named by a committed doc", 0))
    # A directory reference, not a citation.
    results.append(arm("bare directory",
                       "`scratchpad/` has no sweep for this class yet.", 0))
    # A path under some OTHER directory.
    results.append(arm("other directory",
                       "The live scout is `tools/zz_no_such_scout.py` now.", 0))

    print("=== INSTRUMENT arms: the check must say it measured nothing ===")
    src = (ROOT / "tools" / "check_citation_paths.py").read_text()
    # 🔴 THE BLINDED COPIES MUST LIVE IN tools/, NOT A TEMP DIR. The subject
    # derives ROOT from `__file__`, so a copy under /tmp runs its git queries
    # against /tmp — and the first two arms PASSED anyway, because they exit on
    # the self-test before ever reaching git. Only the corpus arm failed, and
    # that is what exposed the other two as passing for the wrong reason.
    # tools/ is safe to plant in: the corpus is .md files, so the subject cannot
    # scan its own blinded copy.
    blind = ROOT / "tools"
    # (a) self-test table emptied -> exit 2, never a clean 0/0.
    b1 = blind / "zz_blinded_selftest.py"
    atexit.register(lambda: b1.unlink(missing_ok=True))
    b1.write_text(src.replace("VECTORS = [", "VECTORS = []\n_UNUSED = ["))
    p = subprocess.run([sys.executable, str(b1)], cwd=ROOT, capture_output=True, text=True)
    ok = p.returncode == 2 and "SELF-TEST" in p.stdout
    print(f"  {'PASS' if ok else 'FAIL'}  emptied self-test table: rc={p.returncode} (want 2)")
    results.append(ok)
    # (b) the RULE broken while the table stands -> exit 2, not a green tree.
    b2 = blind / "zz_blinded_rule.py"
    atexit.register(lambda: b2.unlink(missing_ok=True))
    b2.write_text(src.replace(r"r'\bscratchpad/([A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9]+)'",
                              r"r'\bNOTHING_MATCHES_THIS/(x)'"))
    p = subprocess.run([sys.executable, str(b2)], cwd=ROOT, capture_output=True, text=True)
    ok = p.returncode == 2 and "MISCLASSIFIED" in p.stdout
    print(f"  {'PASS' if ok else 'FAIL'}  rule broken: rc={p.returncode} (want 2)")
    results.append(ok)
    # (c) corpus collapsed -> exit 2, not "all resolve".
    b3 = blind / "zz_blinded_corpus.py"
    atexit.register(lambda: b3.unlink(missing_ok=True))
    b3.write_text(src.replace('return sorted(f for f in tracked_set() if f.endswith(".md"))',
                              'return sorted(f for f in tracked_set() if f.endswith(".md"))[:3]'))
    p = subprocess.run([sys.executable, str(b3)], cwd=ROOT, capture_output=True, text=True)
    ok = p.returncode == 2 and "CORPUS COLLAPSED" in p.stdout
    print(f"  {'PASS' if ok else 'FAIL'}  corpus collapsed: rc={p.returncode} (want 2)")
    results.append(ok)

    print("=== restored-tree control ===")
    rc, _ = run()
    ok = rc == 0 and DOC.read_bytes() == _original
    print(f"  {'PASS' if ok else 'FAIL'}  tree restored byte-exact and green: rc={rc}")
    results.append(ok)

    print(f"\n{sum(results)}/{len(results)} arms as predicted")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
