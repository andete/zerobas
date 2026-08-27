#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Falsify the TAPE arm of patch-freshness by planting, in a throwaway clone.

The tape pair was filed as *"unguarded by the same rule"*, and the extension is
only worth what its RED arms are worth. Four arms, in a `git clone --local` so
the working tree is never the subject:

  GREEN   untouched clone            -> rc 0, "fresh in the tree and at HEAD"
  RED-A   tape/tape.asm changed, pair NOT regenerated
                                     -> rc 1, "STALE IN YOUR TREE"
  RED-B   source change COMMITTED with the pair regenerated but NOT carried
                                     -> rc 1, "STALE IN THE LAST COMMIT"
  GREEN-B source change and pair committed together
                                     -> rc 0

🎯 THE TAPE ARM RUNS WITHOUT A C-BIOS SOURCE CHECKOUT — that is the whole reason
it is separate. `--only tape` is used so a missing checkout skips the MAIN half
without taking this one down with it, which is the property the extension adds.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "probes" / "lib"))
import probe_tmp                                                  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CLONE = Path(probe_tmp.tmp("tapefresh-clone"))
# a comment-only line would not move a byte; this changes an emitted value.
ANCHOR = "tape_end:"


def sh(argv, cwd=CLONE, **kw):
    return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, **kw)


def git(*args, cwd=CLONE):
    p = sh(["git", *args], cwd=cwd)
    if p.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{p.stderr}")
    return p


def check():
    p = sh([sys.executable, "tools/check_patch_freshness.py", "--only", "tape"])
    return p.returncode, p.stdout + p.stderr


def arm(label, want_rc, want_in):
    rc, out = check()
    ok = rc == want_rc and want_in in out
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: rc={rc} (want {want_rc}), "
          f"{'found' if want_in in out else 'MISSING'} {want_in!r}")
    if not ok:
        print("    " + "\n    ".join(out.splitlines()[-10:]))
    return ok


def main():
    shutil.rmtree(CLONE, ignore_errors=True)
    CLONE.parent.mkdir(parents=True, exist_ok=True)
    p = sh(["git", "clone", "--quiet", "--local", "--no-hardlinks",
            str(REPO), str(CLONE)], cwd=REPO)
    if p.returncode != 0:
        sys.exit(f"clone failed:\n{p.stderr}")
    git("config", "user.email", "falsify@example.invalid")
    git("config", "user.name", "falsify")
    # 🔴 `git clone --local` TAKES HEAD, NOT THE WORKING TREE. The first run of
    # this harness reported 0/4 with `unrecognized arguments: --only tape` --
    # it was falsifying the COMMITTED checker, i.e. the one without the change
    # under test. Copy the working-tree tools in so the subject is the code as
    # it stands. (It failed loudly rather than passing, which is the only reason
    # this was cheap to find.)
    for rel in ("tools/check_patch_freshness.py", "tools/build_patches.py"):
        shutil.copyfile(REPO / rel, CLONE / rel)
    # ...and COMMIT them. Leaving the copies uncommitted made the clone dirty,
    # and `tools/build_patches.py` is a PREREQUISITE of the tape pair -- so the
    # "sources are clean" precondition was false and RED-B correctly DEFERRED
    # instead of firing. The harness's own fix had suppressed the arm it exists
    # to test.
    git("add", *[r for r in ("tools/check_patch_freshness.py",
                             "tools/build_patches.py")])
    git("commit", "-q", "-m", "falsify: the checker under test, as it stands")

    ok = [arm("GREEN  untouched clone", 0, "fresh in the tree and at HEAD")]

    asm = CLONE / "tape" / "tape.asm"
    src = asm.read_text()
    if ANCHOR not in src:
        sys.exit(f"INSTRUMENT: anchor {ANCHOR!r} not in tape/tape.asm — the "
                 f"plant would not cut, so a red arm could pass by not firing.")
    # one extra emitted byte before the end label: the patch body must move.
    asm.write_text(src.replace(ANCHOR, "                db 0\n" + ANCHOR, 1))
    ok.append(arm("RED-A  source edited, pair not rebuilt", 1, "STALE IN YOUR TREE"))

    r = sh([sys.executable, "tools/build_patches.py", "--tape"])
    if r.returncode != 0:
        sys.exit(f"INSTRUMENT: regeneration in the clone failed:\n"
                 f"{r.stdout[-1500:]}{r.stderr[-1500:]}")
    git("add", "tape/tape.asm")
    git("commit", "-q", "-m", "plant: source moved, pair NOT carried")
    ok.append(arm("RED-B  committed without the pair", 1, "STALE IN THE LAST COMMIT"))

    git("add", "tape/zerobas-tape-msx1.ips", "tape/zerobas-tape-msx1.bps")
    git("commit", "-q", "-m", "plant: carry the pair")
    ok.append(arm("GREEN  pair carried with the source", 0,
                  "fresh in the tree and at HEAD"))

    print(f"\n{sum(ok)}/{len(ok)} arms as expected")
    shutil.rmtree(CLONE, ignore_errors=True)
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
