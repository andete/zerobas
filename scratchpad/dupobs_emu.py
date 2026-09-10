#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DUPOBS2 — the eleven canonicals `make unit-test` could not observe, scored
against the EMULATOR, cheapest suite first.

D-DUPOBS cut all 21 D-DUPSPAN2 canonicals to a bare `ret` and scored with
`make unit-test`: **10 of 21 observed, host-side, in ~13 minutes**. The remaining
eleven need an emulator, and the entry priced that at "~7 min each" on the
assumption that the whole battery is the scorer.

\U0001f3af IT DOES NOT HAVE TO BE, BECAUSE A RED IS CONCLUSIVE AND A GREEN IS NOT.
The moment ANY suite reddens, the site is observed and nothing further need run.
So the suites are tried CHEAPEST FIRST and the ladder stops at the first red --
measured costs from the last full battery:

    error-acceptance        12 s
    missing-acceptance      45 s
    penderr-acceptance      54 s
    error-trap-acceptance   68 s

⚠️ AND THE ASYMMETRY IS STATED IN THE VERDICT, NOT HIDDEN IN IT. A red says
"observed by <suite>" and is final. A green says only **"not observed by these
four"** -- NOT "not observed by the battery", which would need the whole thing.
Reporting the second as the first is exactly the over-claim this entry keeps
catching in its own earlier cuts.

\U0001f534 AN INERT CUT MANUFACTURES THE FINDING HERE. A green arm IS the result
("this site is unobserved"), so a cut that never reached the ROM produces the
very answer the run exists to report. Every arm hashes the images around the
build and reports `INERT (ROM unchanged)` as its own outcome -- the check
`knife-rom-guard-check` caught D-DUPOBS's runner shipping without.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import probe_tmp                                                  # noqa: E402
import knife_guard                                                # noqa: E402
import dupobs_knives as D                                         # noqa: E402

# The eleven `make unit-test` could not reach (D-DUPOBS, 2026-09-06).
UNOBSERVED = ["ctp_err_pop", "ctp_link_err", "ed_done", "elas_err", "ers_undef",
              "evmc_sqr_err", "gosub_stk_over", "nm_fail", "pl_typeerr",
              "sst_overflow", "tm_raise"]
LADDER = ["error-acceptance", "missing-acceptance", "penderr-acceptance",
          "error-trap-acceptance"]


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, cwd=ROOT, stdout=fh,
                               stderr=subprocess.STDOUT)


def main() -> int:
    only = sys.argv[1:] or UNOBSERVED
    bad = [c for c in only if c not in UNOBSERVED]
    if bad:
        print(f"\U0001f534 {bad} are not in the eleven this run is about; "
              f"refusing rather than silently scoring something else.")
        return 2
    print(f"D-DUPOBS2: {len(only)} canonical(s), ladder {LADDER}\n")
    res = {}
    for c in only:
        hit = D.find_label(c)
        if hit is None:
            print(f"  {c:16} \U0001f534 label not found in source")
            res[c] = "NO LABEL"
            continue
        path, idx = hit
        orig = open(path, encoding="utf-8", errors="replace").read()
        lines = orig.split("\n")
        lines.insert(idx + 1, "                ret                 ; K-DUPOBS2 CUT")
        try:
            open(path, "w", encoding="utf-8").write("\n".join(lines))
            before = knife_guard.hashes()
            if sh("make basic-reloc", probe_tmp.tmp(f"d2_{c}_build.log")):
                res[c] = "BUILD FAILED"
                print(f"  {c:16} BUILD FAILED")
                continue
            if not knife_guard.moved(before, knife_guard.hashes()):
                res[c] = "\U0001f534 INERT (ROM unchanged)"
                print(f"  {c:16} \U0001f534 INERT -- the cut never reached the ROM")
                continue
            verdict = "\U0001f534 not observed by the ladder"
            for suite in LADDER:
                rc = sh(f"caffeinate -i -s make {suite}",
                        probe_tmp.tmp(f"d2_{c}_{suite}.log"))
                if rc:
                    verdict = f"observed by {suite}"
                    break                 # a red is conclusive; stop the ladder
            res[c] = verdict
            print(f"  {c:16} {verdict}")
        finally:
            open(path, "w", encoding="utf-8").write(orig)
    sh("make basic-reloc", probe_tmp.tmp("d2_restore.log"))
    obs = [c for c, v in res.items() if v.startswith("observed")]
    print(f"\n=== {len(obs)}/{len(only)} newly OBSERVED by the ladder ===")
    print("  observed:     " + (", ".join(obs) or "none"))
    print("  still green:  " + (", ".join(c for c in res if c not in obs) or "none"))
    print("\n⚠️ 'still green' means NOT OBSERVED BY THESE FOUR SUITES. It does "
          "not mean unobserved by the battery -- that needs the whole battery, "
          "and saying otherwise would be the over-claim this entry keeps "
          "catching in its own earlier cuts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
