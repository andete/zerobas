#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FACEPIN knives — does each new face pin actually go RED on drift?

TODO.md's "A FILED *FACE* ROTS WITHOUT THE ROW CEASING TO DIVERGE" names the
failure precisely: `filed_row_sweep` calls a row that still diverges -- but now
to a DIFFERENT face -- `known`, and it reads green. Five instances are recorded,
every one found by hand.

D-FACEPRICE priced the remedy at 50 rows across 11 probes and found the template
already exists three times (`basic_probe_nodisk.PINNED`,
`basic_probe_asciidigit`'s, and D-DEFERPIN's `probe_report.Deferral`). This
slice pins the first 14 rows across four probes.

\U0001f534 A PIN THAT CANNOT REDDEN IS DECORATION, and it would read exactly like
a correct one on every green run [[a-knife-can-be-inert-because-the-build-did-not-happen]].
So each probe gets ONE pinned face mutated, and must exit non-zero AND name the
row. The mutation is to the PIN, not to the machine: the question is whether the
comparison is live, and a ROM change would take minutes and prove less.

⚠️ AND THE CONTROL IS THE SECOND RUN. Every probe is run again after restoring,
and must return to rc=0 -- otherwise a red could be the probe breaking rather
than the pin biting.
"""
import io
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (probe, literal to find, what to replace it with, the row it belongs to)
# \U0001f534 EXPLICIT find/replace, NOT a clever substitution chain. The first cut
# derived the mutant by chaining `.replace('"0','"9')` etc., which is fine until a
# probe pins a face that happens to contain one of those fragments -- and
# `dupopen` pins `"zb": "OK"` SIX TIMES, so a bare literal would not even be
# unique. Each arm now names exactly what it corrupts, and the runner refuses a
# literal that is not unique in the file.
ARMS = [
    ("scratchpad/open2_probe.py",
     '"e.same2": {"cf3300": "<File already open>", "zb": "OK"}',
     '"e.same2": {"cf3300": "<File already open>", "zb": "MUTANT"}', "e.same2"),
    ("scratchpad/deffn_alias_probe.py",
     '"o.alias":     {"vg8020": "503", "cf3300": "503", "zb": "505"}',
     '"o.alias":     {"vg8020": "503", "cf3300": "503", "zb": "999"}', "o.alias"),
    ("scratchpad/keystr_probe.py",
     '"k.slot1":  {"vg8020": "0 90 81 88 0"',
     '"k.slot1":  {"vg8020": "9 90 81 88 0"', "k.slot1"),
    ("scratchpad/keylist_probe.py",
     '"d.n1":    {"vg8020": "0"', '"d.n1":    {"vg8020": "9"', "d.n1"),
    ("scratchpad/dupopen_probe.py",
     '"s.same":     {"cf3300": "<File already open>", "zb": "OK"}',
     '"s.same":     {"cf3300": "<File already open>", "zb": "MUTANT"}', "s.same"),
    ("scratchpad/dskibytes_probe.py",
     '"w.sec0":  "0 0 0 0 0 0 0 0"', '"w.sec0":  "9 0 0 0 0 0 0 0"', "w.sec0"),
]


def run(path):
    r = subprocess.run(["caffeinate", "-i", "-s", sys.executable, path],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout


def main() -> int:
    ok = True
    for path, literal, mutant, row in ARMS:
        full = os.path.join(ROOT, path)
        src = io.open(full, encoding="utf-8").read()
        if src.count(literal) != 1:
            print(f"\U0001f534 {path}: plant literal not unique "
                  f"({src.count(literal)} hit(s)) -- arm SKIPPED, not green")
            ok = False
            continue
        bak = full + ".bak"
        shutil.copyfile(full, bak)
        try:
            io.open(full, "w", encoding="utf-8").write(
                src.replace(literal, mutant, 1))
            rc, out = run(path)
            named = row in out and "PINNED FACE DRIFT" in out
            # \U0001f534 rc must be exactly 2, not merely non-zero.
            # `dskibytes_probe` ALREADY exits 1 on its own DIFF verdict (3/3 rows
            # differ by design), so "non-zero" would pass that arm without the
            # pin ever firing -- a green that means nothing.
            good = rc == 2 and named
            ok = ok and good
            print(f"{'PASS' if good else '\U0001f534 FAIL'}  {os.path.basename(path):26s} "
                  f"mutated pin -> rc={rc} (want 2), names {row}: {named}")
        finally:
            shutil.copyfile(bak, full)
            os.remove(bak)
        rc2, out2 = run(path)
        # The control is "no DRIFT reported", not "rc==0": dskibytes_probe's
        # own verdict is a legitimate rc=1 with every pin intact.
        if "PINNED FACE DRIFT" in out2:
            print(f"\U0001f534 {path}: STILL reports drift after restore "
                  f"(rc={rc2}) -- the red above may be the probe, not the pin")
            ok = False
    print("\n" + ("\U0001f7e2 ALL SIX PINS HAVE TEETH" if ok
                  else "\U0001f534 AT LEAST ONE PIN IS INERT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
