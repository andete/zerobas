#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Run the acceptance-gate battery in PARALLEL -- build the shared artifacts once,
then fan the per-gate probes out across worker slots.

This is only safe because the harness is parallel-safe (the emulated-time watchdog
in probes/lib/omsx_repl.py and the temp-path isolation in tests/_tmp.py --
docs/spec-probe-emutime-watchdog.md); before those, heavy emulator gates flaked
under load. The warm-up builds every shared artifact (ROMs, reloc sym/rom, the
resident-ABI include, the test disk) FIRST, so in the parallel phase every gate's
FILE prerequisites are up to date and `make <gate>` runs only its probe -- no
build/ writes and no races over build artifacts, which is why this does not
violate "never run make concurrently with a battery".

🔴 WITH ONE MEASURED EXCEPTION, AND IT IS THE IMPORTANT ONE. `repack-machine` is
PHONY, so it re-runs unconditionally -- and **24 of the battery's targets name it
as a prerequisite**, so a single battery RE-PUBLISHES
`~/.openMSX/share/machines/*.xml` up to 24 times, concurrently, while every other
unit is reading it. This paragraph used to end "nothing rebuilds", which was
false for the one artifact that all 41 units share.

That is survivable for exactly one reason: `openmsx_paths.publish()` writes to a
sibling temp and `os.replace`s it, so a reader can never see a partial file
(D-MACHXML measured the non-atomic form at 412/1200 = 34.3 % of concurrent reads
TORN). It is also why that race was reproducible at all -- it is not a rare
window, it is two dozen publishes per run. Do not remove the atomicity, and do
not read "nothing rebuilds" as covering the machine config.

`graphics-acceptance` is the tent-pole -- a ~300s monolithic, un-shardable,
memory-bandwidth-sensitive render suite -- so by default it runs at NORMAL
priority while the rest run `nice`d, keeping it off the starved cores. The 210-row
`lineerr-acceptance` is sharded by --only across workers (verdict-preserving: it
boots per case, so its rows have no cross-row state; the positive controls are
replicated into every shard).

Usage:  make gates            (J from CPU count)
        python3 tools/run_gates.py --jobs 8 --lineerr-shards 8
        python3 tools/run_gates.py --serial          (fall back to one-at-a-time)
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight              # noqa: E402  (path set above)
import probe_tmp                   # noqa: E402  -- ROOT for the flake keeper
OUT = "scratchpad/gate_logs"

WARM = ["repack-machine", "basic-reloc", "subrom-abi-check", "disk/test720.dsk"]

# --- THE TWO TIERS (D-GATESKIP, docs/spec-gateskip.md) ----------------------
# 🎯 SPLIT BY WHAT A UNIT READS, NOT BY WHAT IT IS ABOUT. A STATIC unit reads
# tracked FILES; an EMULATOR unit boots a machine and reads the ROM. Measured
# 2026-08-28 over a full battery: 19 static units = 65 serial-seconds, 31
# emulator units = 2870. The entire cost of a battery is the emulator tier, and
# both of that day's real reds came out of the static one.
STATIC = """basic-reloc subrom-abi-check diskrom-abi-check subrom-closure-check unit-test deadcode
wall-assertion-check redundant-load-check rowshape-check injector-check
temp-root-check todo-citation-check chokepoint-check wall-literal-check
shared-body-check probe-reach-check battery-membership-check fixture-integrity-check
preflight-check latch-check diskdep-check switch-build-check kwsweep
patch-freshness-check refcache-check knife-guard-check knife-rom-guard-check
selftest-check
deffn-selftest""".split()

EMULATOR = """banner-acceptance string-acceptance str-domain-acceptance strparen-acceptance
penderr-acceptance missing-acceptance error-acceptance error-trap-acceptance
onerr0-acceptance math-acceptance float-acceptance intarg-acceptance
logicops-acceptance lineerr-acceptance screenerr-acceptance tmfp-acceptance
stmtpend-acceptance array-acceptance deffn-strict graphics-acceptance
abort-acceptance interval-trap-acceptance clearpool-acceptance
cursor-acceptance time-acceptance namspc-acceptance arrdim-acceptance
arylv-acceptance badfnum-acceptance beep-acceptance binfre-acceptance
cassave-acceptance castail-acceptance deffn-acceptance direct-ctrl-acceptance
dskmsg-acceptance editverb-acceptance fldary-acceptance fldwidth-acceptance
forvar-acceptance gicini-acceptance graphics-floor-acceptance ifsem-acceptance input-acceptance nodisk-acceptance
inputary-acceptance key-trap-acceptance linemax-acceptance lnblank-acceptance
locarg-acceptance lof-acceptance lptverb-acceptance lrvar-acceptance
lvfix-acceptance nxary-acceptance nxlist-acceptance play-acceptance
play-trace-acceptance readvar-acceptance runtail-acceptance sound-acceptance
sprite-trap-acceptance stop-trap-acceptance strig-trap-acceptance
subrom-acceptance tgtspc-acceptance width-acceptance""".split()

GATES = STATIC + EMULATOR

# 🔴 `build/disk.rom` WAS MISSING FROM THIS LIST UNTIL 2026-08-28, and nobody
# noticed while the hashes were only a printed footnote. D-GATESKIP turns them
# into the thing a skip is PROVED against, at which point a ROM the machine
# boots but the fingerprint does not cover is a hole you could drive a
# regression through: `~/.openMSX/share/machines/*.xml` names all four.
IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom",
          "build/disk.rom"]

LAST_GREEN = os.path.join(OUT, "..", "gate_last_green.json")

# What an EMULATOR unit reads BESIDES the ROM: its own code, the harness, and
# the Makefile recipe that launches it. If none of those moved and the ROM did
# not move, the unit cannot return a different verdict -- so skipping it is a
# PROOF, not a judgement about what a diff "can" affect. That distinction is the
# whole design: judgement about blast radius is exactly the reasoning that
# failed three times on 2026-08-26, each caught by a gate nobody expected.
FINGERPRINT_TREES = ("probes", "tests", "tools")
FINGERPRINT_FILES = ("Makefile",)


def source_fingerprint():
    h = hashlib.sha256()
    for root in FINGERPRINT_TREES:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in sorted(dirnames) if d != "__pycache__"]
            for fn in sorted(filenames):
                if fn.endswith((".py", ".tcl", ".sh")):
                    fp = os.path.join(dirpath, fn)
                    h.update(fp.encode())
                    with open(fp, "rb") as fh:
                        h.update(fh.read())
    for fp in FINGERPRINT_FILES:
        if os.path.exists(fp):
            with open(fp, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:16]


def inert_against_last_green():
    """-> (True, why) when the emulator tier provably cannot move.

    ⚠️ THE STORED RECORD IS ONLY EVER WRITTEN BY A **FULL, FULLY GREEN** RUN, so
    the proof always chains back to a battery that actually booted the machines.
    A skipped run never updates it -- otherwise a chain of skips would eventually
    be vouching for nothing but itself."""
    try:
        with open(LAST_GREEN) as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return False, "no green full battery on record"
    if rec.get("images") != hashes():
        return False, "ROM images differ from the last green battery"
    if rec.get("sources") != source_fingerprint():
        return False, "probes/tests/tools or the Makefile changed"
    stray = unfingerprinted_scripts()
    if stray:
        return False, ("an emulator recipe runs a script OUTSIDE the fingerprint: "
                       + " ".join(sorted(stray)[:4]))
    return True, (f"ROMs and probe/test/tool sources byte-identical to the green "
                  f"full battery of {rec.get('when', '?')}")


# 🔴 THE PROOF HAS A PREMISE, AND UNTIL 2026-08-29 NOTHING CHECKED IT.
# source_fingerprint() covers probes/tests/tools + the Makefile. That makes the
# skip a proof only while every script an EMULATOR unit actually RUNS lives in
# one of those trees -- wire a `scratchpad/` probe into an acceptance recipe and
# the tier can move with the fingerprint unchanged, which is a silent false
# green. `scratchpad/` is tracked here on purpose (knives, probes,
# characterisations), so this is a live hazard, not a hypothetical one.
# 🟢 As measured 2026-08-29 the premise HOLDS -- 0 of the 23 emulator recipes
# reference a script outside the fingerprint -- and it is now RE-DERIVED at every
# skip instead of being true on the day someone looked. ~0.03 s per target.
# [[apparatus-is-part-of-the-measurement]]
SCRIPT_REF = re.compile(r"([\w./-]+\.(?:py|tcl|sh))")


def _make_n(target):
    try:
        return subprocess.run(["make", "-n", target], cwd=ROOT,
                              capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def unfingerprinted_scripts(read_recipe=_make_n, exists=None):
    """-> the set of scripts an EMULATOR recipe runs from outside the fingerprint.

    `read_recipe`/`exists` are injected by the selftest so the arm can drive a
    SYNTHETIC recipe. 🔴 The alternative -- planting a stray reference in the real
    Makefile -- would make this the FOURTH gate that mutates a shared tracked file
    mid-battery, and that class already produces false 'real' verdicts under a
    parallel battery [[exit-safe-is-not-concurrency-safe]]."""
    if exists is None:
        exists = lambda ref: os.path.exists(os.path.join(ROOT, ref))
    stray = set()
    for target in EMULATOR:
        out = read_recipe(target)
        if out is None:
            # Cannot read the recipe -> cannot prove the premise -> do not skip.
            return {f"<make -n {target} failed>"}
        for ref in SCRIPT_REF.findall(out):
            ref = ref.lstrip("./")
            if not ref.startswith(FINGERPRINT_TREES) and exists(ref):
                stray.add(ref)
    return stray


def selftest():
    """🔴 The premise check must REFUSE a skip when an emulator recipe reaches
    outside the fingerprint -- and must not refuse when it does not."""
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and bool(cond)

    inside = "python3 probes/basic/foo_probe.py --gate\n"
    outside = "python3 scratchpad/foo_probe.py --gate\n"
    seen = lambda _ref: True

    arm("S1 a recipe wholly inside the fingerprint is clean",
        unfingerprinted_scripts(lambda t: inside, seen) == set())
    arm("S2 a scratchpad script in ONE recipe is caught",
        unfingerprinted_scripts(
            lambda t, f=EMULATOR[0]: outside if t == f else inside, seen)
        == {"scratchpad/foo_probe.py"})
    arm("S3 an unreadable recipe REFUSES the skip rather than passing it",
        unfingerprinted_scripts(lambda t: None, seen) != set())
    # 🔴 A matcher that finds nothing would make S1 pass for the wrong reason.
    arm("S4 positive control: the matcher does find the path it is given",
        SCRIPT_REF.findall(outside) == ["scratchpad/foo_probe.py"])
    # An untracked path is not a hazard -- it is not what the recipe runs.
    arm("S5 a reference to a NON-EXISTENT path is not reported",
        unfingerprinted_scripts(lambda t: outside, lambda _r: False) == set())

    arm("S6 the LIVE premise holds: no emulator recipe leaves the fingerprint",
        unfingerprinted_scripts() == set())

    # --- D-NOSLEEP: the wake assertion -------------------------------------
    held, why = hold_awake()
    if sys.platform == "darwin":
        import time as _t
        _t.sleep(0.4)                       # let caffeinate register
        a = subprocess.run(["pmset", "-g", "assertions"],
                           capture_output=True, text=True).stdout
        arm("S10 on macOS the assertion is ACTUALLY held, per pmset",
            held and "caffeinate" in a)
        # 🔴 The arm that matters: it must die with us, not leak. A caffeinate
        # bound to a DEAD pid must not still be asserting.
        pre = subprocess.run(["pgrep", "-f", f"caffeinate -i -s -w"],
                             capture_output=True, text=True).stdout.split()
        arm("S11 the assertion is bound to THIS pid, so it cannot outlive the run",
            any(str(os.getpid()) in
                subprocess.run(["ps", "-o", "args=", "-p", p],
                               capture_output=True, text=True).stdout
                for p in pre) if pre else False)
    else:
        arm("S10 off macOS hold_awake is a no-op and says so", not held and "macOS" in why)
    arm("S12 hold_awake never claims 'held' without saying why", bool(why))
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1

# 🔴 GATES THAT MUTATE A SHARED TRACKED FILE TO SELF-TEST, THEN RESTORE IT.
# Each one is EXIT-safe already (D-KNIFEGUARD: the original is held in memory and
# put back by try/finally AND atexit), but exit-safety is not the hazard here --
# a CONCURRENT READER is, and a 43-unit parallel battery is exactly that:
#
#   switch-build-check   mutates basic/sysvars.inc  (tools/check_switch_builds.py)
#   diskdep-check        mutates the MAKEFILE       (tools/check_disk_deps.py)
#   wall-literal-check   mutates tracked probe/tool sources (check_wall_literals.py)
#
# 2026-08-28 this cost a red `unit-test`: pasmo read basic/sysvars.inc mid-write
# and reported "Unexpected 'EQ' used as instruction on line 4216" -- the LABEL of
# a valid `equ` line, gone. The serial retry passed, so the battery called it a
# FLAKE. It was not. `unit-test` is deterministic and takes 22 s; it has no
# business flaking, and the retry masked a real race.
#
# Same class as the machine-XML race and the openMSX settings flake: a shared
# mutable file read in parallel. The `--solo` flag does NOT fix it -- solo only
# schedules a unit FIRST, it does not grant exclusivity. These run SERIALLY,
# before the pool starts. Cost: a few seconds of a ~430 s battery.
#
# 🔴 AND THE LIST NAMED THE WRONG UNITS (D-SELFMUT, 2026-09-01). Measured, one
# gate at a time, watching the mtimes of the tracked files each could touch:
#
#   switch-build-check   mutates NOTHING      ROMs stale after: none
#   diskdep-check        mutates NOTHING      ROMs stale after: none
#   wall-literal-check   mutates NOTHING      ROMs stale after: none
#   selftest-check       mutates basic/sysvars.inc, Makefile,
#                        probes/basic/basic_probe_clear.py
#                                             ROMs stale after: BOTH
#
# The three that were serialised do not plant, because the PLANTING lives behind
# `--selftest` and their recipes never pass it (`make wall-literal-check` runs
# `check_wall_literals.py` bare). The only unit that passes it is
# `selftest-check` -- `check_selftests.py` invokes every advertised `--selftest`,
# two of which plant into the real tree on purpose -- and it was in the PARALLEL
# POOL. The guard was aimed at the tools instead of at the CALLERS that arm them.
# 🎯 Same shape as the coverage rows whose geometry cannot reach their case: ask
# not "can this tool mutate" but "does THIS INVOCATION mutate".
#
# The three are kept: they cost ~5 s serial, their tools are one recipe edit away
# from planting, and removing them would trade a measured cost for an unmeasured
# risk. selftest-check is the one that was doing the damage, and it is ~44 s.
MUTATORS = ["switch-build-check", "diskdep-check", "wall-literal-check",
            "selftest-check"]

# Regenerated by a build or a gate, so DIRTY AFTER A BATTERY IS NORMAL for these
# and only these. The list is the class D-GENFRESH enumerated from make's own
# database (a tracked path that is also a Makefile target), which is exactly the
# set a battery may legitimately refresh under you.
REGENERATED = ["zerobas-main-eu.ips", "zerobas-main-eu.bps",
               "tape/zerobas-tape-msx1.ips", "tape/zerobas-tape-msx1.bps",
               "sub/basic-resident-abi.inc", "sub/math-coeffs.inc"]


def snapshot_tracked():
    """{path: (mtime, size)} for every tracked file a pool unit has no business
    touching. Returns None if git is unusable -- UNMEASURED, never "clean"."""
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    snap = {}
    for f in out.stdout.split("\n"):
        f = f.strip()
        if not f or f in REGENERATED:
            continue
        try:
            st = os.stat(f)
        except OSError:
            continue
        snap[f] = (st.st_mtime, st.st_size)
    return snap


def blame_windows(before, after, windows):
    """Which units were RUNNING when each changed file was written.

    🎯 THE MTIME IS A TIMESTAMP, WHICH IS WHY THIS CAN ATTRIBUTE AND NOT MERELY
    DETECT: the file itself records the instant of the write, so the candidates
    are the units whose [start, end] window contains it.
    ⚠️ UNDER PARALLELISM THAT IS A CANDIDATE SET, NOT A CULPRIT. Every unit
    running at that moment is named; with J=8 that is up to 8 names. It narrows
    a battery-wide "something wrote to the tree" down to the handful worth
    re-running alone, and it says so rather than pretending to a single answer.
    A restore that also restores the mtime is invisible here, and that limit is
    real -- it is the reason this checks mtime AND size rather than content."""
    out = []
    for f, (mt, sz) in sorted(after.items()):
        was = before.get(f)
        if was is None or was == (mt, sz):
            continue
        who = sorted(n for n, (s0, s1) in windows.items() if s0 <= mt <= s1)
        out.append((f, was, (mt, sz), who))
    for f in sorted(set(before) - set(after)):
        out.append((f, before[f], None, []))
    return out


def tracked_dirty():
    """Tracked files differing from HEAD, minus the ones a build regenerates."""
    out = subprocess.run(["git", "status", "--porcelain", "-uno"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return sorted(f for f in (l[3:].strip() for l in out.stdout.splitlines() if l.strip())
                  if f not in REGENERATED)


def sh(argv, log, env=None):
    # guarded() is a no-op passthrough here (argv is make/python3/nice, never a
    # -machine openMSX launch -- those live guarded inside the probes), but it is
    # what preflight-check requires of every spawn site (spec-probe-preflight).
    with open(log, "w") as f:
        return subprocess.call(omsx_preflight.guarded(argv),
                               stdout=f, stderr=subprocess.STDOUT, env=env)


# A unit may exit 0 while declaring it could not measure anything -- the shipped
# patch pair cannot be regenerated without a C-BIOS checkout, for instance. It
# says so with this sentinel and the tally counts it SKIPPED, never green: a
# check that silently passes when it cannot run is the 0/0-ALL-CONVERGED shape.
SKIP_SENTINEL = "GATE-SKIPPED:"


def skipped_reason(log):
    try:
        with open(log) as f:
            for line in f:
                if line.startswith(SKIP_SENTINEL):
                    return line[len(SKIP_SENTINEL):].strip()
    except OSError:
        pass
    return None


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def lineerr_shards(k):
    sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
    sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
    import basic_probe_lineerr as m
    labels = [l for l, _, _, _ in m.CASES]
    ctrl = list(m.CONTROLS)
    buckets = [[] for _ in range(k)]
    for i, lab in enumerate(labels):       # round-robin balances the slow rows
        buckets[i % k].append(lab)
    return [(f"lineerr#{i+1}/{k}", sorted(set(b) | set(ctrl)))
            for i, b in enumerate(buckets)]


# 🔴 D-NOSLEEP (2026-08-30): THE BATTERY HOLDS ITS OWN WAKE ASSERTION -- and
# since D-AWAKE (same day) it is NOT THE ONLY THING THAT DOES, and no longer owns
# the code. The record of the night it cost, and the reasoning, live with the
# implementation in `probes/lib/probe_awake.py`; that module is imported by
# `probes/lib/omsx_repl.py` so EVERY probe and knife runner holds one too, not
# just `make gates`.
# ⚠️ ONE DEFINITION, TWO CALLERS. This used to be a private copy here; a second
# copy in the probe lib would have been two places to fix the day the mechanism
# changes. The selftest arms below (S10/S11/S12) still exercise THIS name, so
# they now score the shared implementation.
from probe_awake import hold_awake  # noqa: E402  (probes/lib is on sys.path, l.55)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    awake, awake_why = hold_awake()
    ap = argparse.ArgumentParser()
    cpu = os.cpu_count() or 8
    ap.add_argument("--jobs", type=int, default=min(8, max(2, cpu)))
    ap.add_argument("--lineerr-shards", type=int, default=8)
    ap.add_argument("--nice", type=int, default=0,
                    help="nice level for non-solo units (0=off)")
    ap.add_argument("--solo", default="",
                    help="comma list of gates run at normal priority while the "
                         "rest are niced (needs --nice)")
    ap.add_argument("--no-retry", action="store_true",
                    help="do not re-run a red gate serially to tell a contention "
                         "flake from a real regression")
    ap.add_argument("--serial", action="store_true",
                    help="run gates one at a time (no parallelism)")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--static", action="store_true",
                    help="run ONLY the static tier (~20s) -- the fast loop for "
                         "iterating; never records a green battery")
    ap.add_argument("--full", action="store_true",
                    help="run the emulator tier even when it is provably inert")
    a = ap.parse_args()
    excl = set(x for x in a.exclude.split(",") if x)
    solo = set(x for x in a.solo.split(",") if x)
    jobs = 1 if a.serial else a.jobs

    os.system(f"rm -rf {OUT} build")
    os.makedirs(OUT, exist_ok=True)
    print(f"=== warm-up (serial build of shared artifacts) ===", flush=True)
    t0 = time.time()
    if sh(["make", *WARM], f"{OUT}/_warmup.log") != 0:
        print("WARM-UP FAILED:"); os.system(f"tail -25 {OUT}/_warmup.log")
        return 1
    twarm = time.time() - t0
    print(f"warm-up {twarm:.0f}s", flush=True)

    dirty_at_start = tracked_dirty()

    os.environ["ZB_TEST_TMP"] = os.path.abspath(os.path.join(OUT, "test_tmp"))

    # --- 🔴 THE BATTERY MEASURES; IT NEVER REPLAYS --------------------------
    # D-REFCACHE serves a stored reading when the machine bytes and the typed
    # lines are unchanged. That is right for ITERATING on a slice and wrong for
    # a GATE: with a warm store, `make graphics-acceptance` on an unchanged tree
    # serves all 315 rows from disk, boots nothing, and prints ALL PASS.
    # 🎯 I FOUND THIS BY DOING IT TO MYSELF -- a bisect run "passed" without
    # measuring anything, and only probe_signal's `REPLAYED` marker gave it
    # away. A gate that agrees because it was told the answer is the purest form
    # of a case agreeing for the wrong reason.
    # So the two mechanisms get DISJOINT jobs: the cache is for iteration, and
    # D-GATESKIP is what makes an unchanged tree cheap for the battery -- loudly,
    # with the skip named in the report. An explicit ZEROBAS_REFCACHE=verify (an
    # audit, which serves nothing and re-measures everything) is passed through.
    # [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
    _rc = os.environ.get("ZEROBAS_REFCACHE", "").strip().lower()
    if _rc in ("verify", "check"):
        # verify does the FULL emulator work with no cache relief, and at J=8
        # that starved the tent-pole into the stall watchdog. An audit is worth
        # more correct than fast.
        if jobs > 4:
            print(f"=== ZEROBAS_REFCACHE={_rc}: --jobs {jobs} -> 4 (verify "
                  f"re-measures every row; at J=8 the tent-pole starved) ===",
                  flush=True)
            jobs = 4
    else:
        os.environ["ZEROBAS_REFCACHE"] = "0"
        print("=== refcache OFF for every unit: a gate measures, it never "
              "replays (docs/spec-refcache.md §7) ===", flush=True)

    # --- D-GATESKIP: is the emulator tier provably unable to move? ----------
    skip_emu, skip_why = False, ""
    if a.static:
        skip_emu, skip_why = True, "--static: the emulator tier was NOT run"
    elif not a.full:
        skip_emu, skip_why = inert_against_last_green()
    if skip_emu:
        excl |= set(EMULATOR)
        print(f"=== SKIPPING {len(EMULATOR)} emulator target(s): {skip_why} ===",
              flush=True)
    else:
        print(f"=== emulator tier RUNS: "
              f"{inert_against_last_green()[1] if not a.full else 'forced by --full'} ===",
              flush=True)

    def wrap(name, argv):
        if a.nice > 0 and jobs > 1 and name not in solo:
            return ["nice", "-n", str(a.nice), *argv]
        return argv

    # --- the mutators, serially, with the pool not yet running -------------
    mut_results = []
    run_mut = [g for g in MUTATORS if g not in excl]
    if run_mut and not a.serial:
        print(f"=== {len(run_mut)} tree-mutating unit(s), SERIAL "
              f"(they rewrite a shared tracked file) ===", flush=True)
        for g in run_mut:
            t0 = time.time()
            rc = sh(["make", g], f"{OUT}/{g}.log")
            dt = time.time() - t0
            mut_results.append((g, rc, dt, None))
            print(f"  rc={rc:<3d} {dt:12.0f}s  {g}", flush=True)
        # 🔴 A RESTORED PLANT IS NOT A RESTORED TREE. The selftests put the
        # bytes back but the MTIME moves, so both repack ROMs are stale the
        # moment this phase ends -- and the pool's first units then race the
        # rebuild their own prerequisites trigger. Whichever probe reaches its
        # preflight inside that window refuses with "NOTHING WAS MEASURED",
        # scores rc=2, and passes on the serial retry: a REAL defect wearing a
        # flake's clothes, seen twice in one day on float-acceptance and earlier
        # on math-acceptance. Rebuilding here costs one relink, once.
        t0 = time.time()
        if sh(["make", *WARM], f"{OUT}/_refresh.log") != 0:
            print("POST-MUTATOR REFRESH FAILED:")
            os.system(f"tail -25 {OUT}/_refresh.log")
            return 1
        print(f"  (post-mutator refresh {time.time() - t0:.0f}s -- the plants "
              f"moved mtimes, so the pool would otherwise race a rebuild)",
              flush=True)

    solo_u, rest_u, bare = [], [], {}      # bare = un-niced argv for a serial retry
    for g in GATES:
        if g in excl:
            continue
        bare[g] = ["make", g]
        if g in run_mut:
            continue                        # already run, serially, above
        (solo_u if g in solo else rest_u).append((g, wrap(g, bare[g])))
    if "lineerr-acceptance" not in excl and not a.serial:
        rest_u[:] = [u for u in rest_u if u[0] != "lineerr-acceptance"]
        for name, only in lineerr_shards(a.lineerr_shards):
            bare[name] = ["python3", "probes/basic/basic_probe_lineerr.py",
                          "--gate", "--only", ",".join(only)]
            rest_u.append((name, wrap(name, bare[name])))
    units = solo_u + rest_u                # solo first -> grabs a worker at once

    # 🔴 THE TORN READ HAS NO WITNESS (D-SELFMUT residual). The stale-ROM half of
    # that race announces itself because a preflight refuses; a unit that writes
    # a tracked file while 40+ others read it surfaces only as an inexplicable
    # red somewhere else, or as a build that quietly used corrupted bytes.
    # Serialising the one known offender fixed today; nothing stopped the next
    # planting `--selftest` from landing in a POOL unit -- and MUTATORS had
    # already been wrong in BOTH directions at once, which is the argument
    # against a list maintained by hand. This measures instead.
    pool_before = snapshot_tracked()
    windows = {}

    print(f"=== {len(units)} units, J={jobs}"
          + (f", lineerr in {a.lineerr_shards} shards" if not a.serial else "")
          + f", nice={a.nice} solo={sorted(solo) or None} ===", flush=True)

    def run(idx_unit):
        idx, (name, argv) = idx_unit
        log = f"{OUT}/{name.replace('/', '_').replace('#', '_')}.log"
        s = time.time()
        rc = sh(argv, log)
        e = time.time()
        windows[name] = (s, e)
        return name, rc, e - s, (skipped_reason(log) if rc == 0 else None)

    results, skips = {}, {}
    for g, rc, dt, _ in mut_results:       # the serial phase counts in the tally
        results[g] = (rc, dt)
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        for name, rc, dt, skip in ex.map(run, enumerate(units)):
            results[name] = (rc, dt)
            if skip:
                skips[name] = skip
            print(f"  rc={rc}{'  SKIPPED' if skip else '        '}  {dt:5.0f}s  "
                  f"{name}", flush=True)

    # --- did any POOL unit write into the tracked tree? ----------------------
    pool_writes = []
    if pool_before is None:
        print("  ⚠️  pool tracked-write check UNMEASURED (git unusable)")
    else:
        after = snapshot_tracked()
        pool_writes = blame_windows(pool_before, after, windows) if after else []
        # ⚠️ MEASURED HERE, REPORTED IN THE SUMMARY. It has to be taken before
        # the serial retries run (they would write the tree themselves and
        # blur the windows); it has to be PRINTED after the verdict, or a
        # "N/N green" line lands underneath a red finding and reads as the
        # answer [[an-unnamed-outcome-reads-as-no-outcome]].

    # RETRY red units SERIALLY, in isolation (docs-spec-probe-emutime-watchdog):
    # heavy emulator gates can drop a capture under concurrency (a `ref=None` on a
    # random row) -- a contention FLAKE, not a regression. Re-run each red unit
    # alone: a real fault fails again (deterministic), a flake passes (stochastic),
    # so this never masks a bug. Serial, so at most a couple of tent-poles re-run.
    flaky = []
    if not a.no_retry and not a.serial:
        # a MUTATOR that goes red already ran alone, so its red cannot be a
        # contention flake -- retrying it would only launder a real failure.
        mut_names = {g for g, *_ in mut_results}
        reds = [n for n, (rc, _) in results.items()
                if rc != 0 and n not in mut_names]
        if reds:
            print(f"\n=== retrying {len(reds)} red unit(s) SERIALLY (flake vs "
                  f"real) ===", flush=True)
            for n in reds:
                rc = sh(bare[n], f"{OUT}/{n.replace('/', '_').replace('#', '_')}.retry.log")
                old = results[n][0]
                results[n] = (rc, results[n][1])
                # 🔴 PRESERVE THE EVIDENCE BEFORE THE NEXT BATTERY EATS IT
                # (D-FLAKEKEEP, 2026-09-02). `main()` opens with
                # `rm -rf {OUT}`, so a red unit's log -- the ONLY artifact that
                # can diagnose a stochastic failure -- survives just until the
                # next run. And a green retry is exactly what stops anyone
                # looking before then: badfnum-acceptance named its diverging
                # row correctly and the line was gone by the time it was wanted.
                # Kept under the sanctioned temp root, untracked, so neither the
                # wipe nor the pool-write detector touches it.
                keep = os.path.join(probe_tmp.ROOT, "gate_flakes",
                                    f"{time.strftime('%Y%m%d-%H%M%S')}-"
                                    f"{n.replace('/', '_').replace('#', '_')}")
                try:
                    os.makedirs(keep, exist_ok=True)
                    for suffix in ("", ".retry"):
                        src = f"{OUT}/{n.replace('/', '_').replace('#', '_')}{suffix}.log"
                        if os.path.exists(src):
                            shutil.copy(src, keep)
                except OSError:
                    pass
                verdict = "FLAKE (green on retry)" if rc == 0 else "REAL (still red)"
                if rc == 0:
                    flaky.append(n)
                print(f"  retry {n}: rc {old}->{rc}  {verdict}", flush=True)

    ttot = time.time() - t0
    shard_rc = [rc for n, (rc, _) in results.items() if n.startswith("lineerr#")]
    lineerr_ran = bool(shard_rc)
    lineerr_ok = (not shard_rc) or all(rc == 0 for rc in shard_rc)
    red = [n for n, (rc, _) in results.items()
           if rc != 0 and not n.startswith("lineerr#")]
    green = sum(1 for n, (rc, _) in results.items()
                if rc == 0 and not n.startswith("lineerr#")
                and n not in skips) + int(lineerr_ran and lineerr_ok)
    # 🔴 `+ int(lineerr_ok)` USED TO BE UNCONDITIONAL, AND THE FIRST `gates-fast`
    # RUN PRINTED "21/21 green" WITH A RED UNIT ON THE NEXT LINE. lineerr_ok is
    # VACUOUSLY true when no shard ran, so excluding the emulator tier minted a
    # phantom green that exactly covered the real red. A count that agrees for
    # the wrong reason is worse than no count.
    # [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
    total_gates = len([g for g in GATES if g not in excl])
    print(f"\n=== wall {ttot:.0f}s ({twarm:.0f}s build + "
          f"{ttot-twarm:.0f}s gates) ===")
    # 🔴 A PARTIAL BATTERY MUST NEVER PRINT WHAT A FULL ONE PRINTS. The whole
    # risk of D-GATESKIP is a skipped run being MISTAKEN for a complete one --
    # by a person scrolling back, or by me quoting it in a commit message. So
    # the word "green" is qualified the moment anything was skipped, and the
    # count of what did not run is on the same line as the count of what did.
    tier = "" if not skip_emu else f" [STATIC TIER ONLY]"
    print(f"GATES: {green}/{total_gates} green{tier}"
          + (f", {len(skips)} SKIPPED" if skips else "")
          + ("" if lineerr_ok else "  (lineerr shard FAILED)"))
    if skip_emu:
        print(f"  ⚠️  {len(EMULATOR)} EMULATOR TARGET(S) NOT RUN — {skip_why}")
        print(f"  ⚠️  this is NOT a full battery; `make gates-full` to force one")
    elif not awake:
        # 🔴 SAID OUT LOUD, because an assertion nobody reports is one nobody
        # notices missing -- and its absence disguises itself as contention.
        print(f"  ⚠️  RAN WITHOUT AN IDLE-SLEEP ASSERTION — {awake_why}"
              f"if this host can sleep, stalls and 0-4 s preflight refusals below "
              f"may be SUSPENSION, not contention (D-NOSLEEP)")
    for n, why in sorted(skips.items()):
        print(f"  SKIPPED {n}: {why}")
    # the arithmetic must agree with the verdict, and now it says so out loud
    if bool(red) == (green >= total_gates - len(skips)):
        print(f"🔴 GATE ACCOUNTING IS INCONSISTENT: green={green} "
              f"total={total_gates} skipped={len(skips)} red={red}")
    if red:
        print("RED:", " ".join(red))
    if flaky:
        print("recovered flakes (green on serial retry):", " ".join(flaky))
    if pool_writes:
        print(f"🔴 BATTERY FAILED ON A POOL WRITE: {len(pool_writes)} TRACKED "
              f"FILE(S) WERE WRITTEN DURING THE PARALLEL POOL. The gate tally "
              f"above is about the gates; this is about the tree they ran on — "
              f"40+ units read these while they changed, and a torn read has no "
              f"witness of its own.")
        for f, was, now, who in pool_writes:
            print(f"     {f}{' (DELETED)' if now is None else ''}")
            print(f"       running at the write: " + (", ".join(who) if who else
                  "(no unit window covers it — the serial phase, a retry, or "
                  "something outside the battery)"))
        print("     → re-run each named unit ALONE and diff the tree, then put "
              "the offender in MUTATORS. A legitimately regenerated path goes "
              "in REGENERATED, with its reason.")
    print("hashes: " + " ".join(f"{h}" for h in hashes()))
    # A unit that plants into the tree and does not restore it is invisible
    # otherwise: the NEXT battery inherits the plant as if it were the source.
    now_dirty = tracked_dirty()
    if now_dirty is None:
        print("  ⚠️  tracked-tree check UNMEASURED (git unusable)")
    elif set(now_dirty) - set(dirty_at_start or []):
        left = sorted(set(now_dirty) - set(dirty_at_start or []))
        print(f"🔴 THE BATTERY LEFT {len(left)} TRACKED FILE(S) DIRTY that were "
              f"clean when it started -- a plant that was not restored: "
              + " ".join(left))
    # 🔴 A POOL WRITE IS A FAILURE, NOT AN ADVISORY. An advisory nobody reads is
    # the shape `check_selftests.py` was built to end (a script red for months
    # with no one collecting its exit code). If a write turns out to be
    # legitimate it goes in REGENERATED with its reason, the way EXPECT_ARG
    # entries do -- the list cannot quietly grow.
    ok = not (red or not lineerr_ok or pool_writes)
    # --- record the proof, and ONLY from a full, fully green, unexcluded run --
    # ⚠️ A SKIPPED RUN NEVER WRITES THIS. If it did, a chain of skips would end
    # up vouching for nothing but the first link, and the proof would decay into
    # a habit. Every skip traces to a battery that really booted the machines.
    if ok and not skip_emu and not skips and not excl:
        try:
            with open(LAST_GREEN, "w") as fh:
                json.dump({"images": hashes(), "sources": source_fingerprint(),
                           "when": time.strftime("%Y-%m-%d %H:%M:%S")}, fh)
            print(f"recorded: this full green battery is now the baseline a "
                  f"future skip must prove itself against")
        except OSError as e:
            print(f"⚠️  could not record the green baseline: {e}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
