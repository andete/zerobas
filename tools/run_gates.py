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
prerequisites are up to date and `make <gate>` runs only its probe -- no build/
writes, no races (which is why this does not violate "never run make concurrently
with a battery": nothing rebuilds).

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

GATES = """basic-reloc subrom-abi-check subrom-closure-check unit-test deadcode
wall-assertion-check redundant-load-check rowshape-check injector-check
temp-root-check todo-citation-check
preflight-check latch-check diskdep-check switch-build-check kwsweep
patch-freshness-check
deffn-selftest string-acceptance str-domain-acceptance strparen-acceptance
penderr-acceptance missing-acceptance error-acceptance error-trap-acceptance
onerr0-acceptance math-acceptance float-acceptance intarg-acceptance
logicops-acceptance lineerr-acceptance screenerr-acceptance tmfp-acceptance
stmtpend-acceptance array-acceptance deffn-strict graphics-acceptance
abort-acceptance interval-trap-acceptance clearpool-acceptance""".split()

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


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

    def wrap(name, argv):
        if a.nice > 0 and jobs > 1 and name not in solo:
            return ["nice", "-n", str(a.nice), *argv]
        return argv

    solo_u, rest_u, bare = [], [], {}      # bare = un-niced argv for a serial retry
    for g in GATES:
        if g in excl:
            continue
        bare[g] = ["make", g]
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
        reds = [n for n, (rc, _) in results.items() if rc != 0]
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
    lineerr_ok = (not shard_rc) or all(rc == 0 for rc in shard_rc)
    red = [n for n, (rc, _) in results.items()
           if rc != 0 and not n.startswith("lineerr#")]
    green = sum(1 for n, (rc, _) in results.items()
                if rc == 0 and not n.startswith("lineerr#")
                and n not in skips) + int(lineerr_ok)
    total_gates = len([g for g in GATES if g not in excl])
    print(f"\n=== wall {ttot:.0f}s ({twarm:.0f}s build + "
          f"{ttot-twarm:.0f}s gates) ===")
    print(f"GATES: {green}/{total_gates} green"
          + (f", {len(skips)} SKIPPED" if skips else "")
          + ("" if lineerr_ok else "  (lineerr shard FAILED)"))
    for n, why in sorted(skips.items()):
        print(f"  SKIPPED {n}: {why}")
    if red:
        print("RED:", " ".join(red))
    if flaky:
        print("recovered flakes (green on serial retry):", " ".join(flaky))
    print("hashes: " + " ".join(f"{h}" for h in hashes()))
    return 1 if (red or not lineerr_ok) else 0


if __name__ == "__main__":
    sys.exit(main())
