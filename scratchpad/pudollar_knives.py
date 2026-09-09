#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PUDOLLAR knives — `$$` makes THREE claims, and they must fail separately.

docs/spec-basic-pudollar.md. Eight rows went green together, which is equally
consistent with one of the three changes doing all the work:

  1. the PAIR counts two columns toward the field width (`ptf_num_fill`)
  2. a `$` is EMITTED, and counted into the CONTENT length (`pu_emit_tenant`)
  3. it sits AFTER a leading sign, not before it (`pet_dol_sign`)

  K-PD1  the pair stops counting toward the width
  K-PD2  the emitted character becomes a space (claim 2, minimally)
  K-PD3  the `$` is emitted BEFORE the sign instead of after (claim 3)

\U0001f3af THE ASYMMETRY IS THE EVIDENCE, and it is `s.full` and `s.ovf`. Both
are already OVERFLOWING -- `$$###` with 12345, `$$#` with 1234 -- so narrowing
the field by two cannot change them: they read `%$...` either way. Killing the
`$` itself does change them, because the character is part of what overflows. So
K-PD1 must move NEITHER and K-PD2 must move BOTH, and if the two arms moved the
same rows, claims 1 and 2 would be indistinguishable and one of them unproven.
K-PD3 then moves exactly the two rows that HAVE a sign, and nothing else.

⚠️ THE PREDICTIONS INCLUDE `x.dollar` AND `s.stardol`, which are
NO-ORACLE rows the gate never scores. They are still rows in the survey table,
so a knife sees them move -- and D-PUSTAR's round 1 read FAIL on both arms for
exactly this reason: the arms were right and the prediction was short
([[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]]).

Hashes both ROMs; refuses a probe run with no verdict line.
"""
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402

ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")

# Every row carrying a RECOGNISED `$$`, which is the widest any arm can move.
DOLLAR_ROWS = {"s.wide", "s.full", "s.neg", "s.dec", "s.ovf", "s.comma",
               "s.plus", "x.dollar", "s.stardol"}

ARMS = {
    # Claim 1. The `jr z` is left pointing at the label that now follows it
    # immediately -- inert, and cheaper than re-flowing the branch.
    "K-PD1": ("basic/pu-render.inc",
              "                inc     b\n                inc     b\nptf_num_nodol:",
              "ptf_num_nodol:",
              DOLLAR_ROWS - {"s.full", "s.ovf"}),
    # Claim 2, minimally: the character still occupies its column, so this is
    # the EMISSION alone and not the length accounting.
    "K-PD2": ("sub/printusing.asm",
              "pet_dol:\n                ld      a,'$'",
              "pet_dol:\n                ld      a,' '",
              DOLLAR_ROWS),
    # Claim 3: skip the sign hand-off, so the `$` lands in front of the sign.
    "K-PD3": ("sub/printusing.asm",
              "                cp      '-'\n                jr      z,pet_dol_sign\n"
              "                cp      '+'\n                jr      nz,pet_dol",
              "                jr      pet_dol",
              {"s.neg", "s.plus"}),
}

PROBE = "probes/basic/basic_probe_pusing.py"


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        h.update(open(r, "rb").read() if os.path.exists(r) else b"ABSENT")
    return h.hexdigest()[:12]


def rows(path):
    """{row: zb value}; None if the run produced no table."""
    txt = open(path).read()
    if "references agree on" not in txt:
        return None
    out = {}
    for line in txt.splitlines():
        m = re.match(r"^(\S+)\s+('.*?')\s+('.*?')\s+('.*?')\s", line)
        if m:
            out[m.group(1)] = m.group(4)
    return out or None


def clean_roms():
    for r in ROMS:
        if os.path.exists(r):
            os.remove(r)


def main():
    clean_roms()
    sh("make repack-machine", probe_tmp.tmp("pd_build_base.out"))
    base_hash = rom_hash()
    sh(f"caffeinate -i -s python3 {PROBE} vg8020,cf3300,zb",
       probe_tmp.tmp("pd_base.out"))
    base = rows(probe_tmp.tmp("pd_base.out"))
    if base is None:
        print("\U0001f534 BASE RUN UNREADABLE -- refusing to run any arm")
        return 2
    missing = sorted(DOLLAR_ROWS - set(base))
    if missing:
        print(f"\U0001f534 BASE TABLE IS MISSING {missing} -- the predictions "
              f"name rows this run does not have, so no arm can be scored.")
        return 2
    print(f"base ROMs {base_hash}   {len(base)} rows read\n")
    ok = True
    for lab, (f, find, repl, want) in ARMS.items():
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: PLANT SITE NOT FOUND in {f} -- arm skipped, NOT green")
            ok = False
            continue
        open(f, "w").write(orig.replace(find, repl, 1))
        clean_roms()
        try:
            rc = sh("make repack-machine", probe_tmp.tmp(f"pd_{lab}_build.out"))
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED")
                ok = False
                continue
            sh(f"caffeinate -i -s python3 {PROBE} vg8020,cf3300,zb",
               probe_tmp.tmp(f"pd_{lab}.out"))
            got = rows(probe_tmp.tmp(f"pd_{lab}.out"))
            if got is None:
                print(f"{lab}: roms={h} \U0001f534 UNREADABLE run -- NOT scored")
                ok = False
                continue
            moved = {k for k in base if got.get(k) != base[k]}
            verdict = "PASS" if moved == want else "FAIL"
            ok = ok and verdict == "PASS"
            print(f"{lab}: roms={h}  moved={sorted(moved) or '<none>'}\n"
                  f"       want={sorted(want)}  {verdict}")
            if moved != want:
                print(f"       unexpected={sorted(moved - want) or '<none>'}  "
                      f"missed={sorted(want - moved) or '<none>'}")
        finally:
            open(f, "w").write(orig)
            clean_roms()
    sh("make repack-machine", probe_tmp.tmp("pd_restore.out"))
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
