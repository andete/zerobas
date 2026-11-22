#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TESTAUDIT (BIOS suites), phase 1: does spec-live see every cbios-repack patch biosregs-acceptance sees?

For each patch in tools/build_repacked_cbios.py's PATCHES: apply them all, then REVERSE that one (`git apply -R`
after the loop -- dropping it from the list broke the later patches' context: lftq-bc's first try), re-pin
REPACKED_SHA1 to what the build reports, rebuild through knife_guard (the ROM must MOVE), run biosregs-acceptance; when it reddens a row, run
spec-live over every BIOS page and record its REGRESSION lines. A biosregs row reddened by a drop that spec-live
ALSO sees is a retirement CANDIDATE for that behaviour; a drop biosregs sees and spec-live does not is a hole in
the pages (keep the row, or extend the page). A patch whose removal breaks the build (a later patch depends on
it) is SKIP, not a result. The tree is restored after every cut and rebuilt CLEAN at the end; the restored ROM
hashes must equal the baseline's.

    python3 -u scratchpad/biosregs_audit.py [PATCH-NAME ...]      -> scratchpad/biosregs_audit.jsonl
"""
import glob
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard  # noqa: E402

SRC = "tools/build_repacked_cbios.py"
OUT = "scratchpad/biosregs_audit.jsonl"
LOGS = "/tmp/zerobas/biosregs_audit"
BIOS_MODULES = sorted(m for m in glob.glob("probes/bios/spec/*_rules.py")
                      if 'PAGE = "docs/bios/' in open(m).read())


LOOP = """            for patch in PATCHES:
                run(["git", "-C", work, "apply", patch])
"""
# -C1: with full context 26 of 39 reverse on the patched tree, with one line 28; the other 11 (graphics-cursor,
# initio, scalxy-flags, ...) do not reverse even with none -- later patches rewrote their lines: SKIP, cut by hand
REVERSE = """            run(["git", "-C", work, "apply", "-R", "-C1", os.path.join(REPO, "cbios-repack", "{p}")])
"""


def patches(text):
    return re.findall(r'^    os\.path\.join\(REPO, "cbios-repack", "([\w.-]+\.patch)"\),\n', text, re.M)


def run(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)


def main(argv):
    os.makedirs(LOGS, exist_ok=True)
    orig = open(SRC).read()
    names = argv or patches(orig)
    base = knife_guard.hashes()
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["patch"] for l in open(OUT) if l.strip()}
    try:
        for p in names:
            if p in done:
                continue
            line = f'    os.path.join(REPO, "cbios-repack", "{p}"),\n'
            if orig.count(line) != 1 or orig.count(LOOP) != 1:
                print(f"{p}: REFUSED, anchor count {orig.count(line)} / loop {orig.count(LOOP)}", flush=True)
                continue
            rec = {"patch": p}
            cut = orig.replace(LOOP, LOOP + REVERSE.format(p=p))
            open(SRC, "w").write(cut)
            moved, after, rc = knife_guard.build(f"{LOGS}/{p}.build1.log", base)
            m = re.search(r"repacked ROM sha1 ([0-9a-f]{40})", open(f"{LOGS}/{p}.build1.log").read())
            if rc and m:                                    # the pin: re-pin to what this cut builds
                pinned = re.sub(r'REPACKED_SHA1 = "[0-9a-f]{40}"', f'REPACKED_SHA1 = "{m.group(1)}"',
                                cut, count=1)
                open(SRC, "w").write(pinned)
                moved, after, rc = knife_guard.build(f"{LOGS}/{p}.build2.log", base)
            if rc or not moved:
                rec.update(verdict="SKIP", why="build failed" if rc else "the ROM did not move")
            else:
                run(["python3", "-u", "probes/basic/basic_probe_biosregs.py"], f"{LOGS}/{p}.biosregs.log")
                red = [l.split()[1] for l in open(f"{LOGS}/{p}.biosregs.log") if l.startswith("ROW")
                       and l.rstrip().endswith("DIVERGES")]
                rec["biosregs_red"] = red
                if red:
                    run(["python3", "-u", "tools/spec_live.py", *BIOS_MODULES], f"{LOGS}/{p}.speclive.log")
                    rec["speclive"] = [l.strip() for l in open(f"{LOGS}/{p}.speclive.log")
                                       if "REGRESSION" in l or l.startswith("FAIL ")]
                rec["verdict"] = ("BIOSREGS-BLIND" if not red else
                                  "BOTH" if rec.get("speclive") else "PAGES-BLIND")
            open(SRC, "w").write(orig)
            with open(OUT, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            print(f"{p}: {rec['verdict']} biosregs {len(rec.get('biosregs_red', []))} red, "
                  f"spec-live {len(rec.get('speclive', []))} line(s)", flush=True)
    finally:
        open(SRC, "w").write(orig)
        moved, after, rc = knife_guard.build(f"{LOGS}/restore.log", None, clean=True)
        print(f"RESTORE: rc {rc}, hashes {'= baseline' if after == base else 'DIFFER: ' + after + ' vs ' + base}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
