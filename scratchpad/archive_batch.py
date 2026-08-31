#!/usr/bin/env python3
r"""Run the UNREACHED probes of one directory, serially, and record what each does.

The archive question (Joost, 2026-08-31): a probe that proved a documented fact is
worth keeping ONLY IF IT STILL RUNS -- otherwise the fact is no longer re-provable.
This answers that per probe.

🔴 SERIALLY, AND WITH A PER-PROBE TIMEOUT. Six emulator probes run in PARALLEL on
2026-08-31 returned non-zero for ALL SIX and the reds were entirely contention
(D-PROBEREACH2 §7); run one at a time, the same six were five green. A probe that
hangs must also not stall the batch, so each gets its own deadline and is recorded
as TIMEOUT rather than silently killing the run.

usage: archive_batch.py <probes-subdir> [timeout-seconds]
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_probe_reach as C                                    # noqa: E402


def main():
    sub = sys.argv[1] if len(sys.argv) > 1 else "probes/disk"
    limit = float(sys.argv[2]) if len(sys.argv) > 2 else 240.0
    probes, invoked, imported, unreached = C.classify()
    todo = [m for m in unreached if probes[m].startswith(sub + "/")]
    print(f"# {len(todo)} unreached probe(s) under {sub}, serial, "
          f"{limit:.0f}s each, ZEROBAS_BASIC_MACHINE supplied")
    for i, m in enumerate(todo, 1):
        rel = probes[m]
        out = f"/tmp/zerobas/arch_{m}.out"
        t0 = time.time()
        with open(out, "w") as fh:
            try:
                # 🔴 THE MACHINE MUST BE SUPPLIED, OR THE BATCH ASKS THE WRONG
                # QUESTION. `probes/disk/` almost all refuse in 0.1 s with "no
                # zerobas machine: pass --machine ... there is no default, one
                # would silently pick the BUILD under test" -- the S1 rule
                # WORKING (docs/spec-lean-retire-s1-explicit-machine.md), not
                # rot. A bare run measures "does it have a default", which is
                # deliberately no; with the env set it measures what we want:
                # is the archived fact still re-provable?
                env = dict(os.environ)
                env.setdefault("ZEROBAS_BASIC_MACHINE",
                               "C-BIOS_MSX1_EU_REPACK_DISK")
                rc = subprocess.call([sys.executable, os.path.join(ROOT, rel)],
                                     stdout=fh, stderr=subprocess.STDOUT,
                                     cwd=ROOT, timeout=limit, env=env)
                state = f"rc={rc}"
            except subprocess.TimeoutExpired:
                state = "TIMEOUT"
        print(f"{i:3d}/{len(todo)}  {m:44s} {state:9s} {time.time()-t0:6.1f}s",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
