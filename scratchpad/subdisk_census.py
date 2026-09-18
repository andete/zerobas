#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SUBDISK: how much of sub.rom exists ONLY for the disk? Measured, bracketed.

spec-diskcode-eviction.md §0.0 put sub.rom's disk-only tenants in scope and
priced them at "~4.8 KB". That figure was HAND CLASSIFICATION from label spans --
my reading, never a tool's -- and it is the last unmeasured quantity the eviction
plan rests on. Main's side was already derived (`carve_scout.py --census`:
2408 B total, 250 SHARED, 2158 PRIVATE); this is the other half.

METHOD -- a closure DIFFERENTIAL, not a file list. `check_dead_code.Spans`
resolves fall-through and shared-tail edges, so "what does the disk reach" is a
graph question it can already answer. Seed the clearly disk-only tenants, then
subtract what the other tenants reach: what is left is alive ONLY because of the
disk.

🔴 WHY IT IS A BRACKET AND NOT A NUMBER. `bload_tenant` and `save_tenant` serve
TAPE AND DISK. Counting them as disk over-states; excluding them subtracts the
FAT code their disk arms need, which under-states. So both are reported:

  LOW    disk-only after subtracting every other tenant INCLUDING the mixed two.
         A strict lower bound: anything bload/save also touch is excluded.
  HIGH   disk-only after subtracting only the UNMIXED tenants -- i.e. what goes
         if bload's and save's DISK ARMS leave too, which they would.

Picking one and calling it "the" figure is exactly the hand classification this
replaces.

⚠️ AND A TRAP IN THE SIZE MODEL, FOUND BY A SANITY CHECK. `Spans.size()` is
label-to-NEXT-LABEL, which includes PADDING. Summed over all of sub.rom it gives
62611 B for a 32768 B ROM -- 1.91x -- because a few spans in sub/sub.asm sit
before the page-boundary pads (`sub_p1_ping` alone measures 16203 B). Those spans
are excluded by name and the exclusion is REPORTED, never silent. The check that
caught it is kept as `--selftest`: if the whole-ROM sum ever falls within a
plausible ratio, the padding spans have changed and the exclusion list is stale.
"""
import sys, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import check_dead_code as cdc                                   # noqa: E402
import check_tenant_closure as ctc                              # noqa: E402

# Spans that precede a page-boundary pad: their label-to-next-label size is the
# PAD, not the routine. Excluded by name, and the exclusion is printed.
PAD_SPANS = {"sub_p1_ping", "sis_spin", "sil_no", "__MEAS_SUB_P0_END"}

DISK_ONLY = ("fatprim_tenant", "dirverb_tenant", "fcbname_tenant")
MIXED = ("bload_tenant", "save_tenant")          # tape AND disk
EXTRA_SEEDS = ("tokenise", "scan_stmt_end", "fp_sqrt", "fp_atan", "fp_exp",
               "fp_log", "fp_pow", "fp_sin", "fp_cos", "fp_tan", "fp_rnd",
               "ary_engine", "strheap_engine", "sub_p0_ping", "sub_p1_ping",
               "sub_int_selftest")


def build():
    s = cdc.Spans(os.path.join(REPO, "sub/sub.asm"), "sub")
    syms = ctc.load_syms(os.path.join(REPO, "build/sub.sym"))
    return s, syms


def live(s, seeds):
    _, l = s.dead(set(seeds) | {n for n in s.nodes if n.startswith(cdc.PROLOGUE)})
    return l


def total(s, syms, names):
    b, skipped, unknown = 0, [], 0
    for n in names:
        if n.startswith(cdc.PROLOGUE):
            continue
        if n in PAD_SPANS:
            skipped.append(n)
            continue
        z = s.size(n, syms)
        if z is None:
            unknown += 1
        else:
            b += z
    return b, skipped, unknown


def selftest():
    s, syms = build()
    tot = sum(z for n in s.nodes
              if not n.startswith(cdc.PROLOGUE)
              for z in [s.size(n, syms)] if z is not None)
    ratio = tot / 32768.0
    ok = ratio > 1.4
    print("%s S1 the whole-ROM span sum still OVER-counts (%.2fx) -- the padding "
          "spans are still there and PAD_SPANS is still needed"
          % ("PASS" if ok else "FAIL", ratio))
    if not ok:
        print("     a plausible ratio means the pads moved: re-derive PAD_SPANS "
              "before trusting any figure below.")
    seen = [n for n in PAD_SPANS if n in s.nodes]
    ok2 = len(seen) == len(PAD_SPANS)
    print("%s S2 every name in PAD_SPANS still exists (%d/%d)"
          % ("PASS" if ok2 else "FAIL", len(seen), len(PAD_SPANS)))
    return 0 if (ok and ok2) else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    s, syms = build()
    tenants = [n for n in s.nodes if n.endswith("_tenant")]
    allseeds = tenants + [n for n in EXTRA_SEEDS if n in s.nodes]
    disk = [n for n in DISK_ONLY if n in s.nodes]
    mixed = [n for n in MIXED if n in s.nodes]
    print("sub.rom: %d spans, %d tenants" % (len(s.nodes), len(tenants)))
    print("disk-only seeds: %s" % ", ".join(disk))
    print("mixed (tape AND disk): %s\n" % ", ".join(mixed))

    ld = live(s, disk)
    lo = live(s, [n for n in allseeds if n not in disk])
    lnm = live(s, [n for n in allseeds if n not in disk and n not in mixed])
    for lbl, st, note in (
            ("LOW ", ld - lo, "minus every other tenant, INCLUDING bload/save"),
            ("HIGH", ld - lnm, "minus the unmixed only -- bload/save disk arms go too")):
        b, skipped, unk = total(s, syms, st)
        print("  %s %5d B   %4d spans   %s" % (lbl, b, len(st), note))
        if skipped:
            print("         padding-spans excluded: %s" % ", ".join(skipped))
        if unk:
            print("         %d span(s) with no computable size" % unk)
    print("\nsub.rom's disk-only cost is BRACKETED, not a point. The eviction "
          "spec's\n'~4.8 KB' was hand classification; this is the measured range.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
