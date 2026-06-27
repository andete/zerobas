#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""disk_probe_diff — ONE parameterized differential probe for the Tier-2 DOS-boot hunt.

Replaces the per-hypothesis "write a new disk_probe_dosboot_*.py" reflex (57 and
counting). Every one of those did the same shape — boot OURS + boot STOCK, anchor on
a shared event, capture {regs | memory | call-sequence}, diff — so this is that shape,
once, with flags. Built on omsx_session.OmsxRun (the validated boot/trace mechanism).

It encodes two method guardrails as MECHANISM, not discipline you have to remember:

  * ANCHOR + ALIGNMENT GUARD (win #1). Every capture is anchored on a shared logical
    event (the Nth time PC hits an address, or the Nth call to a target). Before it
    prints a diff, it PROVES both machines reached the SAME logical anchor. If one side
    looped / never reached occurrence N, the diff is flagged MISALIGNED and NOT
    presented as a real divergence — the exact mistake (mid-stream / mis-aligned-
    checkpoint snapshots) that funded ~half the Tier-2 reframes.

  * FALSIFY-FIRST friendly (win #2). `capture --expect` lets you assert what the diff
    SHOULD be and get a PASS/FAIL — so the cheap disproving experiment is a one-liner.

Modes
  callseq  Trace a sequence of calls (default: BDOS $0005 after COMMAND.COM $0100) on
           both machines and report the first divergent index. The bdosseq generalization.
  capture  Stop at the Nth occurrence of an address on both machines; diff regs and an
           optional memory range, with the alignment guard.

Examples
  # Reproduce the known n=3 BDOS divergence (trust check):
  python3 probes/disk/disk_probe_diff.py callseq --diska ~/Documents/msx/msx/disks/test.dsk

  # Diff regs+work-area at COMMAND.COM's $0100 entry (2nd $0100 hit):
  python3 probes/disk/disk_probe_diff.py capture --at 0x0100 --nth 2 \
      --mem 0xF100:0x300 --diska ~/Documents/msx/msx/disks/test.dsk

The DOS disk is COPIED to a tmp file before use (openMSX can write back to a .dsk —
[[test-disk-mutation-gotcha]]); the original is never touched. Pass --no-copy to override.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omsx_session import OmsxRun, OURS_MACHINE, STOCK_MACHINE  # noqa: E402

# MSX-DOS 1 BDOS function names (function number in C) — public ABI, no oracle bytes.
BDOS = {
    0x00: "TERM0", 0x01: "CONIN", 0x02: "CONOUT", 0x03: "AUXIN", 0x04: "AUXOUT",
    0x05: "LSTOUT", 0x06: "DIRIO", 0x07: "DIRIN", 0x08: "INNOE", 0x09: "STROUT",
    0x0A: "BUFIN", 0x0B: "CONST", 0x0C: "CPMVER", 0x0D: "DSKRST", 0x0E: "SELDSK",
    0x0F: "FOPEN", 0x10: "FCLOSE", 0x11: "SFIRST", 0x12: "SNEXT", 0x13: "FDEL",
    0x14: "RDSEQ", 0x15: "WRSEQ", 0x16: "FMAKE", 0x17: "FREN", 0x18: "LOGIN",
    0x19: "CURDRV", 0x1A: "SETDTA", 0x1B: "ALLOC", 0x21: "RDRND", 0x22: "WRRND",
    0x23: "FSIZE", 0x24: "SETRND", 0x25: "WRBLK", 0x26: "RDBLK", 0x27: "WRRNDV",
    0x28: "WRZER", 0x29: "GDATE", 0x2A: "SDATE", 0x2B: "GTIME", 0x2C: "STIME",
    0x2D: "VERIFY", 0x2E: "RDABS", 0x2F: "WRABS",
}


def _runner(machine: str, diska: str | None, symfile: str) -> OmsxRun:
    return OmsxRun(machine=machine, diska=diska, symfile=symfile)


# ---- mode: callseq -------------------------------------------------------------
def _callseq_arm(arm_addr: int, arm_cond: str, log_addr: int, maxhits: int) -> str:
    return f"""
set ::armed 0
set ::n 0
debug set_bp {arm_addr:#06x} {{}} {{
  if {{ {arm_cond} }} {{ set ::armed 1 }}
}}
debug set_bp {log_addr:#06x} {{}} {{
  if {{!$::armed}} return
  incr ::n
  set sp [reg SP]
  set ret [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
  emit [format "CALL n=%d C=%02X B=%02X DE=%04X HL=%04X ret=%04X t=%.6f" \\
    $::n [expr {{[reg BC]&0xFF}}] [expr {{([reg BC]>>8)&0xFF}}] [reg DE] [reg HL] $ret [machine_info time]]
  if {{$::n >= {maxhits}}} {{ exit }}
}}
"""


def _parse_call(line: str) -> dict | None:
    if not line.startswith("CALL "):
        return None
    rec: dict = {}
    for tk in line.split()[1:]:
        if "=" not in tk:
            continue
        k, v = tk.split("=", 1)
        rec[k] = float(v) if k == "t" else int(v, 16 if k in ("C", "B", "DE", "HL", "ret") else 10)
    rec["fn"] = BDOS.get(rec.get("C", -1), "??")
    return rec


def _fmt_call(r: dict) -> str:
    return (f"n={r['n']:<2} C={r['C']:02X} {r['fn']:<6} "
            f"B={r['B']:02X} DE={r['DE']:04X} HL={r['HL']:04X} ret={r['ret']:04X} t={r['t']:.4f}")


def mode_callseq(args) -> int:
    arm_cond = args.arm_cond or f"[debug read memory {args.arm_check_addr:#06x}] == {args.arm_check_val:#04x}"
    body = 'emit [format "DONE armed=%d n=%d" $::armed $::n]; exit'
    arm = _callseq_arm(args.at, arm_cond, args.log, args.maxhits)

    def seq_for(machine):
        raw = _runner(machine, args.diska, args.symfile).run_job_raw(
            body, settle=args.settle, timeout=args.timeout, arm=arm)
        return [c for c in (_parse_call(l) for l in raw) if c], raw

    print(f"=== callseq: calls to {args.log:#06x} after arm@{args.at:#06x} ({arm_cond}) ===")
    ours, _ = seq_for(OURS_MACHINE)
    stock, _ = seq_for(STOCK_MACHINE)
    print(f"  ours:  {len(ours)} calls    stock: {len(stock)} calls\n")

    # ALIGNMENT GUARD: walk the shared prefix; the divergence is meaningful only because
    # both sides matched up to it.
    keyset = ("C", "DE", "B", "ret")
    n = min(len(ours), len(stock))
    first_div = None
    for i in range(n):
        o, s = ours[i], stock[i]
        same = all(o[k] == s[k] for k in keyset)
        mark = "  " if same else ">>"
        print(f"{mark} [{i+1:>2}] STOCK {_fmt_call(s)}")
        print(f"{mark}      OURS  {_fmt_call(o)}")
        if not same and first_div is None:
            first_div = i + 1
    if first_div is None and len(ours) != len(stock):
        first_div = n + 1
    print()
    if first_div is None:
        print(f"ALIGNED, NO DIVERGENCE in {n} shared calls.")
    else:
        print(f"FIRST DIVERGENCE at call n={first_div} "
              f"(shared identical prefix = {first_div-1} calls).")
    return 0


# ---- mode: capture -------------------------------------------------------------
def _capture_arm(at_addr: int, nth: int, mem: tuple[int, int] | None) -> str:
    block = ""
    if mem:
        base, length = mem
        block = f"""
  set s "BLOCK_{base:04X}_"
  for {{set i 0}} {{$i < {length}}} {{incr i}} {{
    set s "$s[format %02X [debug read memory [expr {{({base} + $i) & 0xFFFF}}]]]"
  }}
  emit $s
"""
    return f"""
set ::cn 0
debug set_bp {at_addr:#06x} {{}} {{
  incr ::cn
  if {{$::cn < {nth}}} return
  emit [ctx ANCHOR]
{block}
  exit
}}
"""


def _regs_from(recs) -> dict | None:
    for r in recs:
        if r.get("tag") == "ANCHOR":
            return r
    return None


def _block_from(recs, base) -> list[int] | None:
    tag = f"BLOCK_{base:04X}_"
    for r in recs:
        if str(r.get("tag", "")).startswith(tag):
            hexpart = r["tag"].split("_", 2)[2]
            return [int(hexpart[i:i+2], 16) for i in range(0, len(hexpart), 2)]
    return None


def mode_capture(args) -> int:
    mem = None
    if args.mem:
        b, _, l = args.mem.partition(":")
        mem = (int(b, 0), int(l, 0))
    body = 'emit "NO-ANCHOR"; exit'
    arm = _capture_arm(args.at, args.nth, mem)

    def cap_for(machine):
        return _runner(machine, args.diska, args.symfile).run_job(
            body, settle=args.settle, timeout=args.timeout, arm=arm)

    print(f"=== capture: regs{'+mem' if mem else ''} at occurrence #{args.nth} of {args.at:#06x} ===")
    o_recs, s_recs = cap_for(OURS_MACHINE), cap_for(STOCK_MACHINE)
    o_regs, s_regs = _regs_from(o_recs), _regs_from(s_recs)

    # ALIGNMENT GUARD — refuse to diff captures that aren't at the same logical point.
    if o_regs is None or s_regs is None:
        print("\n*** MISALIGNED — diff NOT meaningful ***")
        print(f"  stock reached anchor: {'YES t=%.4f' % s_regs['t'] if s_regs else 'NO (looped / never hit occurrence #%d)' % args.nth}")
        print(f"  ours  reached anchor: {'YES t=%.4f' % o_regs['t'] if o_regs else 'NO (looped / never hit occurrence #%d)' % args.nth}")
        print("  A side that never reached the anchor means the comparison is between\n"
              "  different logical points. Fix the anchor (lower --nth, pick an event\n"
              "  both sides reach) before trusting any memory/reg diff. [win #1]")
        return 2

    dt = abs(o_regs["t"] - s_regs["t"])
    print(f"  ALIGNED: both hit occurrence #{args.nth}  (stock t={s_regs['t']:.4f}, ours t={o_regs['t']:.4f}, dt={dt:.4f})\n")
    print("  reg   STOCK  OURS")
    diffs = []
    for k in ("PC", "SP", "AF", "BC", "DE", "HL", "IX", "IY"):
        s, o = s_regs.get(k), o_regs.get(k)
        mark = "  " if s == o else ">>"
        if s != o:
            diffs.append(k)
        print(f"{mark}{k:<5} {s:04X}   {o:04X}")

    if mem:
        base = mem[0]
        ob, sb = _block_from(o_recs, base), _block_from(s_recs, base)
        if ob and sb:
            md = [(base + i, sb[i], ob[i]) for i in range(min(len(ob), len(sb))) if sb[i] != ob[i]]
            print(f"\n  memory {base:#06x}+{mem[1]}: {len(md)} of {min(len(ob),len(sb))} bytes differ")
            for addr, s, o in md[:48]:
                print(f"    {addr:04X}: stock={s:02X} ours={o:02X}")
            if len(md) > 48:
                print(f"    ... (+{len(md)-48} more)")

    print(f"\n  register diffs: {', '.join(diffs) if diffs else 'NONE'}")
    if args.expect:
        ok = (args.expect == "same" and not diffs) or (args.expect == "diff" and diffs)
        print(f"\n  EXPECT={args.expect} -> {'PASS' if ok else 'FAIL'}  [falsification check, win #2]")
        return 0 if ok else 1
    return 0


# ---- cli -----------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)

    def common(p):
        p.add_argument("--diska", help="DOS disk (copied to tmp unless --no-copy)")
        p.add_argument("--no-copy", action="store_true", help="use --diska in place (risks mutation)")
        p.add_argument("--symfile", default="build/disk.omsx.sym")
        p.add_argument("--settle", type=float, default=35.0)
        p.add_argument("--timeout", type=float, default=220.0)

    c = sub.add_parser("callseq", help="diff a call sequence; report first divergence")
    common(c)
    c.add_argument("--at", type=lambda x: int(x, 0), default=0x0100, help="arm address")
    c.add_argument("--arm-check-addr", type=lambda x: int(x, 0), default=0x0102)
    c.add_argument("--arm-check-val", type=lambda x: int(x, 0), default=0x05,
                   help="arm when [arm-check-addr]==this (default: COMMAND.COM @ $0100)")
    c.add_argument("--arm-cond", default=None, help="raw Tcl arm predicate (overrides --arm-check-*)")
    c.add_argument("--log", type=lambda x: int(x, 0), default=0x0005, help="address to log calls to")
    c.add_argument("--maxhits", type=int, default=40)

    p = sub.add_parser("capture", help="diff regs+mem at the Nth occurrence of an address")
    common(p)
    p.add_argument("--at", type=lambda x: int(x, 0), required=True, help="anchor address")
    p.add_argument("--nth", type=int, default=1, help="stop at this occurrence")
    p.add_argument("--mem", default=None, help="memory range BASE:LEN (e.g. 0xF100:0x300)")
    p.add_argument("--expect", choices=("same", "diff"), help="assert reg-diff outcome (PASS/FAIL)")

    args = ap.parse_args()

    tmp_disk = None
    if getattr(args, "diska", None):
        if not os.path.exists(args.diska):
            sys.exit(f"DOS disk not found: {args.diska}")
        if not args.no_copy:
            tmp_disk = tempfile.mktemp(suffix=".dsk")
            shutil.copy2(args.diska, tmp_disk)
            args.diska = tmp_disk
    try:
        return {"callseq": mode_callseq, "capture": mode_capture}[args.mode](args)
    finally:
        if tmp_disk and os.path.exists(tmp_disk):
            os.unlink(tmp_disk)


if __name__ == "__main__":
    raise SystemExit(main())
