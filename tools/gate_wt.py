#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEWT -- gate a COMMIT in a worktree of its own, so work goes on here meanwhile.

    python3 tools/gate_wt.py [--rev REV] [--tier plan|full|scoped|static] [--no-knives]

Why the old rule was "touch nothing in the repo while a gate runs": the installed
openMSX machines name THIS checkout's build/*.rom by absolute path, so a plain `make`
here changed what a running gate booted, and `make repack-machine` rewrote the shared
machine XMLs. openMSX reads `$OPENMSX_USER_DATA` as its user share dir (machines,
extensions, settings.xml, systemroms), so the gate worktree gets machines of its OWN
under the SAME names (tools/openmsx_paths.find_user_share and every site that uses it).

What a run does, in order (the log: scratchpad/gate_wt/<sha>.log, and its last line
is the verdict, `GATEWT <sha> GREEN` or `GATEWT <sha> RED: ...`):
  0. the base: the last PUSHED commit (`git merge-base REV @{upstream}`), so every
     unpushed commit up to REV is planned and knifed together;
  1. a detached worktree at REV beside this checkout (`../zerobas-gate`, or
     $ZEROBAS_GATE_WT), reset hard and `git clean -fdx`'d: a CLEAN build every time;
  2. a private share in it: the user share's `machines/` and `extensions/` COPIED with
     this checkout's path rewritten to the worktree's, `settings.xml` copied (the
     user's own is never written), everything else (systemroms, scripts, ...) linked;
  3. the gate state run_gates keeps under scratchpad/ (gate_last_green.json,
     gate_pins/) copied in;
  4. `make repack-machine test-dsk` there (the test disks are generated, untracked);
  5. a commit touching basic/ sub/ disk/: the knives (kwknife --all, --allfn) and the
     tape corpus ($TAPECORPUS_DIR, required), as the loop does before a commit. A TRACKED file they change (the
     knife pin) is reported and copied to scratchpad/gate_wt/<sha>.changed/: the
     battery then gates the tree WITH it, and the commit is amended with those exact
     bytes before the push;
  6. the gate: `plan` (default) is pick_gates --run with ZEROBAS_GATE_BASE = REV's
     base; `full` is run_gates --full plus the five excluded suites;
  7. on green, the gate state copied back (the full-green record is what later
     skips are proven against).

While this runs, this checkout may run emulator probes too (Joost, 2026-11-10: "I
thought we solved that restriction?"): the worktree has its own machines and, through
ZEROBAS_TMP, its own probe temp root. What can still collide is a suite with a
hard-coded /tmp name (beeptrace, playtrace, zpu ...) run in BOTH places at once --
so here, run probes and single suites, never the battery or a suite the gate is in
the middle of. Builds, unit tests and the static tools were always fine.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import openmsx_paths  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight  # noqa: E402

WT = os.path.abspath(os.environ.get("ZEROBAS_GATE_WT")
                     or os.path.join(os.path.dirname(ROOT), "zerobas-gate"))
OUTDIR = os.path.join(ROOT, "scratchpad", "gate_wt")
LOCK = os.path.join(OUTDIR, "running.pid")
STATE = ("scratchpad/gate_last_green.json", "scratchpad/gate_pins")
REWRITE_DIRS = ("machines", "extensions")
ROM_TREES = ("basic/", "sub/", "disk/")
EXCLUDED5 = ("bdos-acceptance", "diskbasic-acceptance", "fat-error-acceptance",
             "input-devices-acceptance", "lnblank-say-acceptance",
             "dskfmt-acceptance CHOICES=1,4")   # D-DSKFMT: the two extremes (1 side x 40,
                                                # 2 x 80); all four take ~15 min


def git(*args, cwd=ROOT, check=True):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def user_share_real() -> str:
    """The user's OWN share dir -- never the private one, even when run nested."""
    return os.path.join(openmsx_paths.find_user(), "share")


def seed_share(dst: str) -> None:
    src = user_share_real()
    os.makedirs(dst)
    old, new = ROOT + "/", WT + "/"
    for name in sorted(os.listdir(src)):
        s, d = os.path.join(src, name), os.path.join(dst, name)
        if name in REWRITE_DIRS and os.path.isdir(s):
            os.makedirs(d)
            for fn in sorted(os.listdir(s)):
                fs = os.path.join(s, fn)
                if not os.path.isfile(fs):
                    os.symlink(fs, os.path.join(d, fn))
                    continue
                with open(fs, "rb") as fh:
                    blob = fh.read()
                with open(os.path.join(d, fn), "wb") as fh:
                    fh.write(blob.replace(old.encode(), new.encode()))
        elif name == "settings.xml":
            shutil.copyfile(s, d)           # openMSX rewrites it on exit: a COPY
        else:
            os.symlink(s, d)


def stamp_only(old: str, new: str) -> bool:
    """True when two JSON texts differ in nothing but a top-level "written" stamp."""
    try:
        a, b = json.loads(old), json.loads(new)
    except ValueError:
        return False
    if isinstance(a, dict) and isinstance(b, dict):
        a.pop("written", None)
        b.pop("written", None)
    return a == b


def copy_state(src_root: str, dst_root: str) -> None:
    for rel in STATE:
        s, d = os.path.join(src_root, rel), os.path.join(dst_root, rel)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        elif os.path.isfile(s):
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--tier", choices=("plan", "full", "scoped", "static"), default="plan")
    ap.add_argument("--no-knives", action="store_true")
    a = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    if os.path.exists(LOCK):
        pid = int(open(LOCK).read().split()[0])
        try:
            os.kill(pid, 0)
            sys.exit(f"REFUSE: a gate_wt run is live (pid {pid}); one at a time")
        except ProcessLookupError:
            pass                            # stale lock
    with open(LOCK, "w") as fh:
        fh.write(f"{os.getpid()} {time.time():.0f}\n")
    try:
        return run(a)
    finally:
        os.remove(LOCK)


def run(a) -> int:
    sha = git("rev-parse", a.rev).strip()
    short = sha[:8]
    # the base is the last PUSHED commit: with two unpushed commits the parent alone
    # would plan (and knife) only the second one
    parent = git("merge-base", sha, "@{upstream}").strip()
    log_path = os.path.join(OUTDIR, f"{short}.log")
    log = open(log_path, "w", buffering=1)

    def say(msg):
        print(msg, flush=True)
        log.write(msg + "\n")

    def sh(argv, env, what):
        say(f"--- {what}: {' '.join(argv)}")
        t0 = time.time()
        r = subprocess.run(omsx_preflight.guarded(argv), cwd=WT, env=env, stdout=log,
                           stderr=subprocess.STDOUT)
        say(f"--- {what}: rc={r.returncode} ({time.time() - t0:.0f} s)")
        return r.returncode

    say(f"GATEWT {short}: worktree {WT}, tier {a.tier}")
    if not os.path.isdir(os.path.join(WT, ".git")) and not os.path.isfile(os.path.join(WT, ".git")):
        git("worktree", "add", "--detach", WT, sha)
    git("checkout", "-q", "--detach", "-f", sha, cwd=WT)
    git("reset", "-q", "--hard", sha, cwd=WT)
    git("clean", "-q", "-fdx", cwd=WT)
    share = os.path.join(WT, ".omsx-share")
    seed_share(share)
    copy_state(ROOT, WT)
    # ZEROBAS_TMP: the probes' shared temp root (probe_tmp) is the worktree's own, so a
    # probe run in the main checkout meanwhile cannot meet the gate's files there
    # OUTSIDE every checkout: refcache-check's arms tell a repo-built ROM from a
    # foreign one by path, and a temp root inside the worktree read as repo-built
    # (KS2 / KS6 red, the first gate run with it)
    tmp = os.path.join(tempfile.gettempdir(), "zerobas-gatewt")
    os.makedirs(tmp, exist_ok=True)
    env = dict(os.environ, OPENMSX_USER_DATA=share, ZEROBAS_GATE_BASE=parent,
               ZEROBAS_TMP=tmp, PYTHONUNBUFFERED="1")
    fails = []

    # test-dsk: disk/test720.dsk and empty720.dsk are GENERATED and untracked, so a
    # cleaned worktree has none -- the knives' disk rows read NO-VERDICT without them
    # (the first ROM run of this tool, 2026-11-10: 21 cuts)
    if sh(["make", "-s", "repack-machine", "test-dsk"], env, "build + repack"):
        fails.append("build")
    changed = [f for f in git("diff", "--name-only", parent, sha).splitlines() if f]
    rom = any(f.startswith(ROM_TREES) for f in changed)
    if not fails and rom and not a.no_knives:
        for argv, what in ((["python3", "-u", "scratchpad/kwknife.py", "--all"], "knives"),
                           (["python3", "-u", "scratchpad/kwknife.py", "--allfn"], "fn knives")):
            if sh(argv, env, what):
                fails.append(what)
        if not env.get("TAPECORPUS_DIR"):
            fails.append("tape corpus (TAPECORPUS_DIR unset)")
        elif sh(["python3", "-u", "scratchpad/tapecorpus_run.py"], env, "tape corpus"):
            fails.append("tape corpus")
        moved = [f for f in git("diff", "--name-only", cwd=WT).splitlines() if f]
        # a re-pin whose ONLY change is its "written" stamp is the same pin: restore it,
        # so the battery gates exactly the commit and nothing needs an amend
        for f in [m for m in moved if m.endswith(".json")]:
            if stamp_only(git("show", f"HEAD:{f}", cwd=WT), open(os.path.join(WT, f)).read()):
                git("checkout", "-q", "--", f, cwd=WT)
                moved.remove(f)
                say(f"(re-pinned {f}: only its \"written\" stamp moved -- restored)")
        if moved:
            keep = os.path.join(OUTDIR, f"{short}.changed")
            for f in moved:
                os.makedirs(os.path.dirname(os.path.join(keep, f)), exist_ok=True)
                shutil.copy2(os.path.join(WT, f), os.path.join(keep, f))
            say(f"TRACKED FILES MOVED by the knives / corpus (amend the commit with "
                f"{keep}/* before the push): {' '.join(moved)}")

    if not fails:
        if a.tier == "plan":
            if sh(["python3", "tools/pick_gates.py", "--run"], env, "gate (planned)"):
                fails.append("gate")
        elif a.tier == "full":
            if sh(["python3", "tools/run_gates.py", "--full"], env, "gate FULL"):
                fails.append("full battery")
            for t in EXCLUDED5:
                if sh(["make", "-s", *t.split()], env, t):
                    fails.append(t.split()[0])
        elif a.tier == "scoped":
            if sh(["make", "-s", "gates-scoped"], env, "gate SCOPED"):
                fails.append("gate")
        else:
            if sh(["python3", "tools/run_gates.py", "--static"], env, "gate STATIC"):
                fails.append("gate")

    if not fails:
        copy_state(WT, ROOT)
        say(f"GATEWT {short} GREEN")
        return 0
    say(f"GATEWT {short} RED: {', '.join(fails)} (log {log_path})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
