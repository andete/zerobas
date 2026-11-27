#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
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
import glob
import hashlib
import json
import os
import re
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
# D-GATEKNIFESKIP (2026-11-17): the knives and the tape corpus read only the built ROM images
# (and their .sym) and their own harness. A pass is remembered by a hash of exactly those, and a
# commit whose build hashes the same skips them: the same bytes were already knifed. A docs /
# probe commit stacked on unpushed ROM commits re-ran ~3.5 min of knives for nothing.
KNIFE_STAMP = os.path.join(OUTDIR, "knife_inputs.json")
KNIFE_HARNESS = ("scratchpad/kwknife.py", "scratchpad/knife_guard.py", "tools/tier_table.py",
                 "probes/basic/basic_probe_kwsweep.py", "scratchpad/tapecorpus_run.py")


def knife_key(wt: str) -> str:
    """sha256 over the built ROMs, their .sym files and the knife / corpus harness, by path."""
    files = sorted(glob.glob(os.path.join(wt, "build", "*.rom"))
                   + glob.glob(os.path.join(wt, "build", "*.sym")))
    if not files:
        raise SystemExit("FAIL: knife_key: no built ROM in the worktree -- refusing to key a skip "
                         "on an empty build")
    h = hashlib.sha256()
    for f in files + [os.path.join(wt, x) for x in KNIFE_HARNESS]:
        h.update(os.path.relpath(f, wt).encode() + b"\0")
        h.update(open(f, "rb").read())
    return h.hexdigest()
LOCK = os.path.join(OUTDIR, "running.pid")
STATE = ("scratchpad/gate_last_green.json", "scratchpad/gate_pins")
SWEEP_PINS = ("build/sweeps-rom.txt", "build/kwsweep-verdicts.json", "build/kwtime.json", "build/kwram.json")
REWRITE_DIRS = ("machines", "extensions")
ROM_TREES = ("basic/", "sub/", "disk/", "tape/", "cbios-repack/")   # = pick_gates.ROM_TREES (D-TAPEPLAN)
# ⚖️ Joost 2026-11-27 (memory ruled-test-vs-build-balance): the tape corpus only when the MAIN ROM changed --
# a disk-ROM-only commit runs the knives, not the tape corpus
MAIN_ROM_TREES = ("basic/", "sub/", "tape/", "cbios-repack/")
EXCLUDED5 = ("bdos-acceptance", "bdos-cfhost-acceptance", "diskbasic-acceptance", "fat-error-acceptance",
             "input-devices-acceptance",
             "dskfmt-acceptance CHOICES=1,4",
             "fmtdos-acceptance CHOICES=1,4")   # D-DSKFMT: the two extremes (1 side x 40,
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


def _pin_written(raw):
    """a sweep pin's own `written` stamp ("YYYY-MM-DD HH:MM:SS", sortable), or None"""
    if not raw:
        return None
    m = re.search(rb'"written"\s*:\s*"([^"]+)"', raw)
    return m.group(1) if m else None


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
    # ⏱ D-STATICSLOW (2) (2026-11-22): the keyword-sweep pins and the ROM they were measured on survive the clean.
    # Wiped, run_gates found "no recorded ROM" every time and re-ran kwsweep in EVERY gate, docs-only ones too
    # (162 s in 77d3567a's). Kept, its D-PINSTALE check still re-measures whenever the built ROM is another.
    git("clean", "-q", "-fdx", "-e", "build/sweeps-rom.txt", "-e", "build/kwsweep-verdicts.json",
        "-e", "build/kwtime.json", "-e", "build/kwram.json", cwd=WT)
    share = os.path.join(WT, ".omsx-share")
    seed_share(share)
    copy_state(ROOT, WT)
    # The slow sweeps' pins, from THIS checkout when they are newer than the worktree's own (kept across its clean,
    # above): `make gates-sweeps` runs in the checkout, and a worktree that rendered docs/tier-status.md from its
    # older kwtime / kwram reds tiers-md-check on the very commit that stages the fresh render (2026-11-23).
    # The pin's own ROM record goes with it, so D-PINSTALE still re-measures when the built ROM is another.
    # NOT by mtime: run_gates restores the pins it kept across its own wipe with a plain write, so a STALE pin in
    # the worktree carries a recent mtime (the first version of this compared mtimes and copied nothing). The
    # sweeps run in the checkout, so its pin wins whenever the two differ -- unless both record when they were
    # written and the worktree's is the later.
    for rel in SWEEP_PINS:
        s_, d_ = os.path.join(ROOT, rel), os.path.join(WT, rel)
        if not os.path.isfile(s_):
            continue
        sb = open(s_, "rb").read()
        db = open(d_, "rb").read() if os.path.isfile(d_) else None
        if sb == db or (_pin_written(db) and _pin_written(sb) and _pin_written(db) > _pin_written(sb)):
            continue
        os.makedirs(os.path.dirname(d_), exist_ok=True)
        open(d_, "wb").write(sb)
    # ZEROBAS_TMP: the probes' shared temp root (probe_tmp) is the worktree's own, so a
    # probe run in the main checkout meanwhile cannot meet the gate's files there
    # OUTSIDE every checkout: refcache-check's arms tell a repo-built ROM from a
    # foreign one by path, and a temp root inside the worktree read as repo-built
    # (KS2 / KS6 red, the first gate run with it)
    tmp = os.path.join(tempfile.gettempdir(), "zerobas-gatewt")
    os.makedirs(tmp, exist_ok=True)
    env = dict(os.environ, OPENMSX_USER_DATA=share, ZEROBAS_GATE_BASE=parent,
               ZEROBAS_TMP=tmp, PYTHONUNBUFFERED="1",
               # 🔴 (2026-11-26): its EXCLUDED5 run here is outside run_gates, whose REFS mode does not reach it --
               # the default mode serves zerobas readings from the store (pick_gates had the same hole)
               ZEROBAS_REFCACHE=os.environ.get("ZEROBAS_REFCACHE") or "refs")
    fails = []

    # test-dsk: disk/test720.dsk and empty720.dsk are GENERATED and untracked, so a
    # cleaned worktree has none -- the knives' disk rows read NO-VERDICT without them
    # (the first ROM run of this tool, 2026-11-10: 21 cuts)
    if sh(["make", "-s", "repack-machine", "test-dsk"], env, "build + repack"):
        fails.append("build")
    changed = [f for f in git("diff", "--name-only", parent, sha).splitlines() if f]
    rom = any(f.startswith(ROM_TREES) for f in changed)
    main_rom = any(f.startswith(MAIN_ROM_TREES) for f in changed)
    key = knife_key(WT) if not fails and rom and not a.no_knives else None
    try:
        last = json.load(open(KNIFE_STAMP)) if key else {}
    except (OSError, ValueError):
        last = {}
    if key and last.get("key") == key:
        say(f"knives + tape corpus SKIPPED: the built ROMs and the knife / corpus harness are "
            f"byte-identical to the last passing run ({last.get('sha')}; D-GATEKNIFESKIP)")
        key = None
    ran_knives = bool(key)
    if key:
        for argv, what in ((["python3", "-u", "scratchpad/kwknife.py", "--all"], "knives"),
                           (["python3", "-u", "scratchpad/kwknife.py", "--allfn"], "fn knives")):
            if sh(argv, env, what):
                fails.append(what)
        if not main_rom:
            say("tape corpus SKIPPED: no main-ROM tree changed (Joost 2026-11-27: the tape corpus only then)")
        elif not env.get("TAPECORPUS_DIR"):
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
    if ran_knives and not fails:            # a pass is remembered only when it PASSED
        os.makedirs(OUTDIR, exist_ok=True)
        with open(KNIFE_STAMP, "w") as fh:
            json.dump({"key": key, "sha": short, "written": time.strftime("%Y-%m-%d %H:%M")}, fh)

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
