#!/usr/bin/env python3
"""Fast gate battery -- build shared artifacts ONCE (serial), then fan out every
gate across J workers, SHARDING the tent-pole gates (lineerr-acceptance is ~46%
of the serial wall on its own: 210 boot-per-case rows x 3 machines).

WHY SAFE vs "never run make concurrently": the warm-up builds every shared
artifact (ROMs, reloc sym/rom, abi.inc, test dsk) first, so in the parallel phase
`make <gate>` finds all prereqs up to date and runs ONLY its probe -- no build/
writes, no race. Each probe boots its own openMSX with a unique temp Tcl + out
file, so the only shared write is ~/.openMSX/share/settings.xml on emulator exit;
we VALIDATE the whole run against the serial battery (same 38 verdicts + same ROM
hashes) rather than assume it away.

WHY SHARDING lineerr IS VERDICT-PRESERVING: it runs batch=False (boot-per-case),
so each case is an independent fresh boot with NO cross-row state -- partitioning
the 210 labels across parallel `--only` shards cannot change any per-row verdict.
The 4 positive CONTROLS are replicated into every shard so each keeps its
instrument-health check. The gate passes iff every shard passes.

Usage:  python3 scratchpad/fastgates.py [--jobs 8] [--lineerr-shards 8]
                                          [--isolate] [--only-fast]
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
OUT = "scratchpad/fastgates_logs"

WARM = ["repack-machine", "basic-reloc", "subrom-abi-check", "disk/test720.dsk"]

# every gate the serial battery runs, minus lineerr-acceptance (sharded below).
GATES = """basic-reloc subrom-abi-check subrom-closure-check unit-test deadcode
wall-assertion-check redundant-load-check rowshape-check injector-check
preflight-check latch-check diskdep-check switch-build-check kwsweep
deffn-selftest string-acceptance str-domain-acceptance strparen-acceptance
penderr-acceptance missing-acceptance error-acceptance error-trap-acceptance
onerr0-acceptance math-acceptance float-acceptance intarg-acceptance
logicops-acceptance screenerr-acceptance tmfp-acceptance stmtpend-acceptance
array-acceptance deffn-strict graphics-acceptance abort-acceptance
interval-trap-acceptance clearpool-acceptance""".split()

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd: list[str], log: str, env=None) -> int:
    with open(log, "w") as f:
        return subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, env=env)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def lineerr_shards(k: int) -> list[tuple[str, list[str]]]:
    sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
    sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
    import basic_probe_lineerr as m
    labels = [l for l, _, _, _ in m.CASES]
    ctrl = list(m.CONTROLS)
    # round-robin partition -> balances the two 12s SLOW_ROWS across shards.
    buckets: list[list[str]] = [[] for _ in range(k)]
    for i, lab in enumerate(labels):
        buckets[i % k].append(lab)
    shards = []
    for i, b in enumerate(buckets):
        only = sorted(set(b) | set(ctrl))
        shards.append((f"lineerr#{i+1}/{k}", only))
    return shards


def make_env_for(worker_slot: int, isolate: bool):
    if not isolate:
        return None
    base = os.path.join(ROOT, OUT, f"omsx_w{worker_slot}", "share")
    real = os.path.expanduser("~/.openMSX/share")
    if not os.path.isdir(base):
        os.makedirs(base, exist_ok=True)
        for name in os.listdir(real):
            if name == "settings.xml":
                continue
            link = os.path.join(base, name)
            if not os.path.lexists(link):
                os.symlink(os.path.join(real, name), link)
    env = dict(os.environ)
    env["OPENMSX_USER_DATA"] = base
    return env


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--lineerr-shards", type=int, default=8)
    ap.add_argument("--isolate", action="store_true")
    ap.add_argument("--exclude", default="",
                    help="comma list of gate names to skip (e.g. graphics-acceptance)")
    ap.add_argument("--no-build", action="store_true",
                    help="skip warm-up rebuild (reuse an intact build/)")
    ap.add_argument("--nice", type=int, default=0,
                    help="nice level for NON-solo units (0=off). Lets a solo, "
                         "contention-intolerant gate keep CPU priority.")
    ap.add_argument("--solo", default="",
                    help="comma list of gates run at NORMAL priority + FIRST "
                         "(e.g. graphics-acceptance), while the rest run niced")
    a = ap.parse_args()
    excl = set(x for x in a.exclude.split(",") if x)
    solo = set(x for x in a.solo.split(",") if x)

    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    if a.no_build:
        print("=== --no-build: reusing existing build/ ===", flush=True)
        twarm = 0.0
    else:
        os.system(f"rm -rf {OUT} build"); os.makedirs(OUT, exist_ok=True)
        print(f"=== warm-up (serial build of shared artifacts) ===", flush=True)
        wrc = sh(["make", *WARM], f"{OUT}/_warmup.log")
        twarm = time.time() - t0
        print(f"warm-up rc={wrc}  {twarm:.0f}s", flush=True)
        if wrc != 0:
            print("WARM-UP FAILED:"); os.system(f"tail -25 {OUT}/_warmup.log")
            return 1

    # build the unit list: plain gates + lineerr shards. Solo (contention-
    # intolerant) gates go FIRST at normal priority; the rest are niced.
    def wrap(name, argv):
        if a.nice > 0 and name not in solo and not name.startswith("_solo"):
            return ["nice", "-n", str(a.nice), *argv]
        return argv

    solo_units, rest_units = [], []
    for g in GATES:
        if g in excl:
            continue
        (solo_units if g in solo else rest_units).append((g, wrap(g, ["make", g])))
    if "lineerr-acceptance" not in excl:
        for name, only in lineerr_shards(a.lineerr_shards):
            argv = ["python3", "probes/basic/basic_probe_lineerr.py", "--gate",
                    "--only", ",".join(only)]
            rest_units.append((name, wrap(name, argv)))
    units = solo_units + rest_units   # solo first -> grabs a worker immediately

    # isolate unit-test's /tmp/zb_* build artifacts from any concurrent battery
    os.environ["ZB_TEST_TMP"] = os.path.abspath(os.path.join(OUT, "test_tmp"))
    print(f"=== parallel phase: {len(units)} units, J={a.jobs}, "
          f"lineerr in {a.lineerr_shards} shards, isolate={a.isolate} ===",
          flush=True)
    results = {}
    tpar0 = time.time()

    def run_unit(idx_name_argv):
        idx, (name, argv) = idx_name_argv
        slot = (idx % a.jobs) + 1
        env = make_env_for(slot, a.isolate)
        log = f"{OUT}/{name.replace('/', '_').replace('#', '_')}.log"
        s = time.time()
        rc = sh(argv, log, env=env)
        return name, rc, time.time() - s

    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for name, rc, dt in ex.map(run_unit, enumerate(units)):
            results[name] = (rc, dt)
            print(f"  rc={rc}  {dt:5.0f}s  {name}", flush=True)

    tpar = time.time() - tpar0
    ttot = time.time() - t0

    # lineerr passes iff all shards pass
    shard_rcs = [rc for n, (rc, _) in results.items() if n.startswith("lineerr#")]
    lineerr_ok = shard_rcs and all(rc == 0 for rc in shard_rcs)
    gate_fail = [n for n, (rc, _) in results.items()
                 if rc != 0 and not n.startswith("lineerr#")]
    print()
    print(f"=== TOTAL wall {ttot:.0f}s  (warm {twarm:.0f}s + parallel {tpar:.0f}s) ===")
    npass = sum(1 for n, (rc, _) in results.items()
                if rc == 0 and not n.startswith("lineerr#")) + (1 if lineerr_ok else 0)
    print(f"lineerr-acceptance (sharded): {'PASS' if lineerr_ok else 'FAIL'} "
          f"({len(shard_rcs)} shards)")
    print(f"GATES: {npass}/38 green")
    if gate_fail:
        print("RED:", " ".join(gate_fail))
    print("=== slowest units ===")
    for n, (rc, dt) in sorted(results.items(), key=lambda kv: -kv[1][1])[:6]:
        print(f"  {dt:5.0f}s  {n}  (rc={rc})")
    print("=== hashes ===")
    for p, h in zip(IMAGES, hashes()):
        print(f"  {h}  {p}")
    return 0 if (not gate_fail and lineerr_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
