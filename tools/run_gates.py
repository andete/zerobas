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
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight              # noqa: E402  (path set above)
OUT = "scratchpad/gate_logs"

WARM = ["repack-machine", "basic-reloc", "subrom-abi-check", "disk/test720.dsk"]

# --- THE TWO TIERS (D-GATESKIP, docs/spec-gateskip.md) ----------------------
# 🎯 SPLIT BY WHAT A UNIT READS, NOT BY WHAT IT IS ABOUT. A STATIC unit reads
# tracked FILES; an EMULATOR unit boots a machine and reads the ROM. Measured
# 2026-08-28 over a full battery: 19 static units = 65 serial-seconds, 31
# emulator units = 2870. The entire cost of a battery is the emulator tier, and
# both of that day's real reds came out of the static one.
STATIC = """basic-reloc subrom-abi-check subrom-closure-check unit-test deadcode
wall-assertion-check redundant-load-check rowshape-check injector-check
temp-root-check todo-citation-check chokepoint-check wall-literal-check
preflight-check latch-check diskdep-check switch-build-check kwsweep
patch-freshness-check refcache-check knife-guard-check selftest-check
deffn-selftest""".split()

EMULATOR = """banner-acceptance string-acceptance str-domain-acceptance strparen-acceptance
penderr-acceptance missing-acceptance error-acceptance error-trap-acceptance
onerr0-acceptance math-acceptance float-acceptance intarg-acceptance
logicops-acceptance lineerr-acceptance screenerr-acceptance tmfp-acceptance
stmtpend-acceptance array-acceptance deffn-strict graphics-acceptance
abort-acceptance interval-trap-acceptance clearpool-acceptance""".split()

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
    return True, (f"ROMs and probe/test/tool sources byte-identical to the green "
                  f"full battery of {rec.get('when', '?')}")

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
MUTATORS = ["switch-build-check", "diskdep-check", "wall-literal-check"]


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


def main():
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

    print(f"=== {len(units)} units, J={jobs}"
          + (f", lineerr in {a.lineerr_shards} shards" if not a.serial else "")
          + f", nice={a.nice} solo={sorted(solo) or None} ===", flush=True)

    def run(idx_unit):
        idx, (name, argv) = idx_unit
        log = f"{OUT}/{name.replace('/', '_').replace('#', '_')}.log"
        s = time.time()
        rc = sh(argv, log)
        return name, rc, time.time() - s, (skipped_reason(log) if rc == 0 else None)

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
    print("hashes: " + " ".join(f"{h}" for h in hashes()))
    ok = not (red or not lineerr_ok)
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
