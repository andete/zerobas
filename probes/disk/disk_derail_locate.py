#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Thin derail locator: bisect a failure predicate to the instruction that flips it.

This is the self-driving driver the token-budget discussion asked for. It runs the
WHOLE mechanical loop we used to do by hand-writing Tcl turn after turn — boot,
binary-search emulated time for when a predicate flips, report the LAST-GOOD /
FIRST-BAD instructions, and forward-trace across the boundary — in ONE openMSX boot
and emits a structured report. It draws no clean-room conclusions: it reports WHAT
the machine did and recognises only a few KNOWN mechanical patterns; anything else,
and the semantic "is this correct?" call, is escalated to the human/Opus.

Escalation contract — every run ends in exactly one verdict line:
    RESOLVED:        the predicate flip is located and matches a known pattern
    DECISION-NEEDED: located, but the cause/fix is a judgment call (the usual case)
    STUCK:           predicate never true at settle / no boundary found

The locator faithfully bisects whatever predicate it is given; CHOOSING the
predicate is the judgment. Built-in presets cover the recurring Tier-2 failure
shapes. Validated: `--preset paging-p1` re-derives the $E79B subslot-unmap root
cause hand-found 2026-06-25.

    python3 probes/disk/disk_derail_locate.py --preset paging-p1
    python3 probes/disk/disk_derail_locate.py --preset sp-rompage --settle 10
    python3 probes/disk/disk_derail_locate.py --predicate '[reg PC] == 0xDA23' --lo 5 --settle 9
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omsx_session import OmsxRun, OURS_MACHINE, STOCK_MACHINE  # noqa: E402

# name -> (predicate, default lo, default settle, human description)
PRESETS = {
    "sp-rompage": ("[reg SP] >= 0x4000 && [reg SP] <= 0x7fff", 7.0, 10.0,
                   "stack pointer points into the $4000-7FFF ROM page (corruption / storm)"),
    "paging-p1": ("[debug read memory 0x4251] != 0xC3", 7.5, 8.25,
                  "the disk ROM has left page 1 ($4251 no longer the $C3 int trampoline)"),
    "sp-lost": ("[reg SP] < 0x8000", 7.0, 10.0,
                "stack pointer dropped below $8000 (lost the high DOS stack)"),
}

# Tcl/disasm fragments that name a mechanical cause when they are the LAST-GOOD insn.
SLOT_WRITE = re.compile(r"(ld\s+\(#ffff\),a|out\s+\(#a8\),a)", re.I)


def classify(recs: list[dict]) -> tuple[str, list[str]]:
    """Return (verdict, report_lines). Recognises only KNOWN mechanical patterns."""
    by_tag = {}
    trace = []
    stack = None
    for r in recs:
        t = r.get("tag", "")
        if t.startswith("T") and t[1:].isdigit():
            trace.append(r)
        elif t == "STACK":
            stack = r
        else:
            by_tag.setdefault(t, r)

    lines: list[str] = []
    if "NO-FAILURE-AT-SETTLE" in by_tag:
        lines.append("predicate was FALSE at the settle time — no failure in window.")
        lines.append("→ widen --settle, lower --lo, or the predicate is wrong.")
        return "STUCK", lines
    if "ERROR" in by_tag:
        lines.append(f"openMSX/Tcl error: {by_tag['ERROR']}")
        return "STUCK", lines
    if "LAST-GOOD" not in by_tag or "FIRST-BAD" not in by_tag:
        lines.append("no clean boundary captured (records: "
                     + ",".join(sorted(by_tag)) + ")")
        return "STUCK", lines

    lg, fb = by_tag["LAST-GOOD"], by_tag["FIRST-BAD"]
    lines.append(f"FLIP located at t={lg['t']:.6f}s:")
    lines.append(f"  LAST-GOOD  ${lg['PC']:04X}  {lg.get('dis','?'):<16}"
                 f"  (A={lg['AF']>>8:02X} SP={lg['SP']:04X})")
    lines.append(f"  FIRST-BAD  ${fb['PC']:04X}  {fb.get('dis','?'):<16}"
                 f"  (SP={fb['SP']:04X})  ← predicate now true")
    if stack:
        pass  # stack words already in record but unparsed; trace tells the story

    # forward trace tail
    if trace:
        lines.append("  forward from the flip:")
        for r in trace[:12]:
            lines.append(f"    ${r['PC']:04X}  {r.get('dis','?'):<14}"
                         f" SP={r['SP']:04X} m4251={r.get('m4251',0):02X}")

    # known-pattern recognition (mechanical, not semantic)
    dis = lg.get("dis", "")
    if SLOT_WRITE.search(dis):
        lines.append("")
        lines.append(f"PATTERN: the flip was a SLOT/SUBSLOT write (`{dis.strip()}`) at "
                     f"${lg['PC']:04X} — a paging change unmapped the watched address.")
        lines.append("Mechanical chain is located. The semantic call — is this remap "
                     "correct, and what should keep the watched code mapped — is yours.")
        # offer the next mechanical predicate (auto-chain candidate, not executed)
        lines.append(f"NEXT (mechanical): trace who set the written value / why this "
                     f"remap runs — e.g. forward-trace from a bit before t={lg['t']:.4f}, "
                     f"or bisect a predicate on the routine entry that calls ${lg['PC']:04X}.")
        return "DECISION-NEEDED", lines

    # storm shape: trace oscillates between two PCs
    if len(trace) >= 4:
        pcs = [r["PC"] for r in trace[:6]]
        if len(set(pcs)) == 2:
            a, b = sorted(set(pcs))
            lines.append("")
            lines.append(f"PATTERN: tight 2-PC oscillation ${a:04X}⇄${b:04X} — a storm/spin, "
                         "which is DOWNSTREAM. Re-run with a predicate that targets the "
                         "ROOT state (e.g. --preset paging-p1), not this symptom.")
            return "DECISION-NEEDED", lines

    lines.append("")
    lines.append("Flip located but not a known pattern — evidence above; cause is a "
                 "judgment call.")
    return "DECISION-NEEDED", lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=sorted(PRESETS))
    ap.add_argument("--predicate", help="raw Tcl predicate (overrides --preset)")
    ap.add_argument("--lo", type=float)
    ap.add_argument("--settle", type=float)
    ap.add_argument("--trace", type=int, default=16)
    ap.add_argument("--diska", default="/tmp/dos.dsk")
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--machine")
    args = ap.parse_args()

    if args.predicate:
        predicate, lo, settle, desc = args.predicate, args.lo or 5.0, args.settle or 10.0, "custom"
    elif args.preset:
        predicate, dlo, dsettle, desc = PRESETS[args.preset]
        lo = args.lo if args.lo is not None else dlo
        settle = args.settle if args.settle is not None else dsettle
    else:
        ap.error("give --preset or --predicate")
    if not os.path.exists(args.diska):
        sys.exit(f"disk not found: {args.diska}")

    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    r = OmsxRun(machine=machine, diska=args.diska)
    print(f"=== derail locate on {machine} ===")
    print(f"  predicate: {predicate}   ({desc})")
    print(f"  window: bisect [{lo}, {settle}]s, trace {args.trace}")
    recs = r.bisect_locate(predicate, lo=lo, settle=settle, trace_n=args.trace)
    verdict, lines = classify(recs)
    for ln in lines:
        print("  " + ln)
    print(f"\n  VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
