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
    0x28: "WRZER", 0x2A: "GDATE", 0x2B: "SDATE", 0x2C: "GTIME", 0x2D: "STIME",
    0x2E: "VERIFY", 0x2F: "RDABS", 0x30: "WRABS",
}


def _runner(machine: str, diska: str | None, symfile: str) -> OmsxRun:
    return OmsxRun(machine=machine, diska=diska, symfile=symfile)


# ---- mode: callseq -------------------------------------------------------------
def _poke_bp(poke_at: int, poke_nth: int,
             pokes: list[tuple[int, int]] | None,
             poke_regs: list[tuple[str, int]] | None) -> str:
    """A one-shot poke breakpoint: at the poke_nth hit of poke_at (after armed),
    inject memory writes and/or register overrides into OURS, then disarm itself.
    The falsify-first primitive — 'if this value were right, does ours converge?'"""
    if not pokes and not poke_regs:
        return ""
    mem_tcl = "".join(f"\n    debug write memory {a:#06x} {v:#04x}" for a, v in (pokes or []))
    reg_tcl = "".join(f"\n    reg {r} {v:#06x}" for r, v in (poke_regs or []))
    return f"""
set ::pn 0
set ::poked 0
debug set_bp {poke_at:#06x} {{}} {{
  if {{!$::armed || $::poked}} return
  incr ::pn
  if {{$::pn < {poke_nth}}} return
  set ::poked 1{mem_tcl}{reg_tcl}
  emit [format "POKE applied at {poke_at:#06x} #%d t=%.6f" $::pn [machine_info time]]
}}
"""


def _callseq_arm(arm_addr: int, arm_cond: str, log_addr: int, maxhits: int,
                 poke: str = "") -> str:
    return f"""
set ::armed 0
set ::n 0
set ::poked 0
debug set_bp {arm_addr:#06x} {{}} {{
  if {{ {arm_cond} }} {{ set ::armed 1 }}
}}
{poke}
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
    body = 'emit [format "DONE armed=%d n=%d poked=%d" $::armed $::n [expr {$::poked + 0}]]; exit'
    pokes = []
    for p in (args.poke or []):
        a, _, v = p.partition(":")
        pokes.append((int(a, 0), int(v, 0)))
    poke_regs = []
    for p in (args.poke_reg or []):
        r, _, v = p.partition(":")
        poke_regs.append((r.upper(), int(v, 0)))
    # falsify-first pokes go into OURS only; stock stays the oracle.
    poke_tcl = _poke_bp(args.poke_at, args.poke_nth, pokes, poke_regs)
    arm_ours = _callseq_arm(args.at, arm_cond, args.log, args.maxhits, poke_tcl)
    arm_stock = _callseq_arm(args.at, arm_cond, args.log, args.maxhits)

    def seq_for(machine):
        arm = arm_ours if machine == OURS_MACHINE else arm_stock
        raw = _runner(machine, args.diska, args.symfile).run_job_raw(
            body, settle=args.settle, timeout=args.timeout, arm=arm)
        return [c for c in (_parse_call(l) for l in raw) if c], raw

    tag = f" [POKE @{args.poke_at:#06x}: {pokes+poke_regs}]" if (pokes or poke_regs) else ""
    print(f"=== callseq: calls to {args.log:#06x} after arm@{args.at:#06x} ({arm_cond}){tag} ===")
    ours, ours_raw = seq_for(OURS_MACHINE)
    stock, _ = seq_for(STOCK_MACHINE)
    if pokes or poke_regs:
        applied = any("POKE applied" in l for l in ours_raw)
        print(f"  poke {'APPLIED' if applied else '** NOT APPLIED (anchor never hit while armed) **'} on ours")
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
    # TAIL: when one side ran longer (the other blocked at a console-input wait, or
    # one derailed), the shared-prefix loop above can't show what the longer side did
    # past the split. Dump that tail so a spinning-ours vs blocked-stock split is
    # visible (e.g. is ours just re-polling BUFIN, or derailing into other calls?).
    longer, who = (ours, "OURS") if len(ours) > len(stock) else (stock, "STOCK")
    if len(ours) != len(stock):
        print(f"--- {who}-only tail (other side stopped at n={n}; "
              f"blocked at a wait or fewer calls) ---")
        for i in range(n, len(longer)):
            print(f"   [{i+1:>2}] {who:<5} {_fmt_call(longer[i])}")
        print()
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


# ---- mode: trace ---------------------------------------------------------------
def _trace_arm(arm_addr: int, arm_cond: str, at_addr: int, nth: int, steps: int,
               pokes: list[tuple[int, int]] | None = None) -> str:
    poke_tcl = "".join(
        f"\n  debug write memory {a:#06x} {v:#04x}" for a, v in (pokes or []))
    return f"""
set ::armed 0
set ::cn 0
set ::tn 0
set ::tracing 0
debug set_bp {arm_addr:#06x} {{}} {{
  if {{ {arm_cond} }} {{ set ::armed 1 }}
}}
debug set_bp {at_addr:#06x} {{}} {{
  if {{!$::armed || $::tracing}} return
  incr ::cn
  if {{$::cn < {nth}}} return
  set ::tracing 1{poke_tcl}
  debug condition create -command {{
    incr ::tn
    emit [ctx [format "T%03d" $::tn]]
    if {{$::tn >= {steps}}} {{ exit }}
  }}
}}
"""


def _trace_seq(recs) -> list[dict]:
    return [r for r in recs if str(r.get("tag", "")).startswith("T")]


def _find_resync(ours, stock, i, j, window=80):
    """From a fork at (ours[i], stock[j]), find the nearest re-convergence: the
    (i+a, j+b) with smallest a+b where the PCs match again. Returns (ni, nj, pc) or
    None. Lets PC-diffing skip a by-design relocation detour (ours' $E7xx hook vs
    stock's $Dxxx hook) and resume at the common return point."""
    for d in range(1, 2 * window + 1):
        for a in range(0, min(d, window) + 1):
            b = d - a
            if b < 0 or b > window:
                continue
            if i + a >= len(ours) or j + b >= len(stock):
                continue
            if ours[i + a].get("PC") == stock[j + b].get("PC"):
                return (i + a, j + b, ours[i + a].get("PC"))
    return None


def _resync_walk(ours, stock):
    """Walk both PC streams, recording each fork and where it re-converges. Returns a
    list of dicts: {'fork_o','fork_s','pc_o','pc_s', 'resync_pc','resync_o','resync_s'}
    (resync_* None if it never re-converges within the window = a real divergence)."""
    i = j = 0
    events = []
    while i < len(ours) and j < len(stock):
        if ours[i].get("PC") == stock[j].get("PC"):
            i += 1
            j += 1
            continue
        ev = {"fork_o": i, "fork_s": j,
              "pc_o": ours[i].get("PC"), "pc_s": stock[j].get("PC")}
        rs = _find_resync(ours, stock, i, j)
        if rs is None:
            ev["resync_pc"] = None
            events.append(ev)
            break
        ni, nj, pc = rs
        ev.update(resync_pc=pc, resync_o=ni, resync_s=nj)
        events.append(ev)
        i, j = ni, nj
    return events


def mode_trace(args) -> int:
    arm_cond = args.arm_cond or f"[debug read memory {args.arm_check_addr:#06x}] == {args.arm_check_val:#04x}"
    body = 'emit [format "DONE armed=%d tracing=%d tn=%d" $::armed $::tracing $::tn]; exit'
    pokes = []
    for p in (args.poke or []):
        a, _, v = p.partition(":")
        pokes.append((int(a, 0), int(v, 0)))
    arm_plain = _trace_arm(args.at, arm_cond, args.anchor, args.nth, args.steps)
    arm_poked = _trace_arm(args.at, arm_cond, args.anchor, args.nth, args.steps, pokes)

    def trace_for(machine):
        # pokes are injected into OURS only (the unit under test); stock stays the oracle.
        arm = arm_poked if (pokes and machine == OURS_MACHINE) else arm_plain
        recs = _runner(machine, args.diska, args.symfile).run_job(
            body, settle=args.settle, timeout=args.timeout, arm=arm)
        return _trace_seq(recs)

    print(f"=== trace: {args.steps} instrs from occurrence #{args.nth} of {args.anchor:#06x} "
          f"(arm@{args.at:#06x}: {arm_cond}) ===")
    ours, stock = trace_for(OURS_MACHINE), trace_for(STOCK_MACHINE)
    print(f"  ours: {len(ours)} instrs   stock: {len(stock)} instrs")

    # ALIGNMENT GUARD: both traces must start at the same PC (the anchor instruction).
    if not ours or not stock:
        print("\n*** MISALIGNED — a side never reached the anchor (looped / wrong --nth). [win #1]")
        return 2
    if ours[0].get("PC") != stock[0].get("PC"):
        print(f"\n*** MISALIGNED — traces start at different PC "
              f"(stock {stock[0]['PC']:04X}, ours {ours[0]['PC']:04X}); not the same logical point. [win #1]")
        return 2

    if args.resync:
        # Re-convergence walk: report every fork and whether it rejoins (relocation
        # detour) or is a real divergence — skips by-design $E7xx-vs-$Dxxx hooks.
        events = _resync_walk(ours, stock)
        if not events:
            print(f"\n  ALIGNED, NO PC DIVERGENCE in {min(len(ours),len(stock))} instrs.")
            return 0
        print(f"\n  re-convergence walk ({len(events)} fork(s)):\n")
        real = None
        for k, ev in enumerate(events, 1):
            so, ss = stock[ev["fork_s"]], ours[ev["fork_o"]]
            caller = stock[ev["fork_s"] - 1] if ev["fork_s"] else so
            print(f"  fork {k}: at {caller['PC']:04X} {str(caller.get('dis',''))[:24]:<24} "
                  f"-> stock {ev['pc_s']:04X} / ours {ev['pc_o']:04X}")
            if ev["resync_pc"] is None:
                print(f"          NO re-convergence within window -> REAL DIVERGENCE (blocker).")
                real = ev
                break
            print(f"          re-converges at {ev['resync_pc']:04X} "
                  f"(detour: stock {ev['resync_s']-ev['fork_s']} instrs, "
                  f"ours {ev['resync_o']-ev['fork_o']} instrs) -> benign relocation")
        if real is None:
            print(f"\n  all forks re-converged: ours and stock are behaviorally equivalent\n"
                  f"  across {min(len(ours),len(stock))} traced instrs (only by-design\n"
                  f"  relocation differs). The next real blocker is beyond --steps={args.steps}.")
        else:
            cps = stock[real["fork_s"] - 1] if real["fork_s"] else stock[real["fork_s"]]
            print(f"\n  -> REAL blocker: caller {cps['PC']:04X} {cps.get('dis','')}; "
                  f"stock->{real['pc_s']:04X} ours->{real['pc_o']:04X}. Inspect what it reads.")
        return 0

    n = min(len(ours), len(stock))
    fork = next((i for i in range(n) if ours[i].get("PC") != stock[i].get("PC")), None)
    if fork is None:
        print(f"\n  ALIGNED, NO PC DIVERGENCE in {n} instrs "
              f"(the fork is later, or data-only — widen --steps or diff regs).")
        return 0

    lo = max(0, fork - 6)
    print(f"\n  first PC divergence at trace step {fork+1} (shared prefix = {fork} instrs):\n")
    print("  step  STOCK PC  dis                          | OURS PC  dis")
    for i in range(lo, min(fork + 2, n)):
        s, o = stock[i], ours[i]
        mark = ">>" if s.get("PC") != o.get("PC") else "  "
        print(f"{mark}{i+1:>4}  {s['PC']:04X}     {str(s.get('dis',''))[:26]:<26} | "
              f"{o['PC']:04X}    {str(o.get('dis',''))[:26]}")
    sb = stock[fork - 1] if fork else stock[0]
    print(f"\n  branch instruction (last common step {fork}): {sb['PC']:04X}  {sb.get('dis','')}")
    print(f"  flags/regs there — stock AF={sb.get('AF',0):04X}  ours AF={ours[fork-1].get('AF',0):04X}")
    print("  -> inspect what that instruction (and the few before it) READ; that memory is\n"
          "     the divergent cell. Next: capture --at <reader PC> --mem <cell>. [win #2]")
    return 0


# ---- mode: screen --------------------------------------------------------------
def _screen_body() -> str:
    # Read SCRMOD ($FCAF) + LINLEN ($F3B0), then the VDP name table. SCREEN 0 (text 40)
    # name table = VRAM $0000, 40x24; SCREEN 1 = $1800, 32x24. Renders printable ASCII,
    # '.' for control/non-printable. Direct observation of the console — what's on screen.
    return r"""
set scrmod [debug read memory 0xFCAF]
set linlen [debug read memory 0xF3B0]
set r2 [debug read "VDP regs" 2]
set base [expr {($r2 & 0x7F) << 10}]
emit [format "MODE scrmod=%02X linlen=%02X r2=%02X namebase=%04X" $scrmod $linlen $r2 $base]
set cols [expr {$scrmod == 1 ? 32 : 40}]
for {set row 0} {$row < 24} {incr row} {
  set s ""
  for {set c 0} {$c < $cols} {incr c} {
    set b [debug read "VRAM" [expr {$base + $row*$cols + $c}]]
    if {$b >= 32 && $b < 127} { set s "$s[format %c $b]" } else { set s "$s." }
  }
  emit [format "ROW%02d |%s|" $row $s]
}
# Raw hex of the first 3 name-table rows (reveals char-code transforms vs ASCII).
for {set row 0} {$row < 3} {incr row} {
  set h ""
  for {set c 0} {$c < $cols} {incr c} {
    set h "$h[format %02X [debug read {VRAM} [expr {$base + $row*$cols + $c}]]]"
  }
  emit [format "HEX%02d %s" $row $h]
}
# Locate the banner anywhere in VRAM 0..0x3FFF: scan for "MSX" (4D 53 58).
for {set a 0} {$a < 0x4000} {incr a} {
  if {[debug read "VRAM" $a] == 0x4D &&
      [debug read "VRAM" [expr {$a+1}]] == 0x53 &&
      [debug read "VRAM" [expr {$a+2}]] == 0x58} {
    emit [format "FOUND-MSX at VRAM %04X" $a]
  }
}
exit
"""


def mode_screen(args) -> int:
    machines = [STOCK_MACHINE, OURS_MACHINE]
    if args.machine == "ours":
        machines = [OURS_MACHINE]
    elif args.machine == "stock":
        machines = [STOCK_MACHINE]
    for m in machines:
        raw = _runner(m, args.diska, args.symfile).run_job_raw(
            _screen_body(), settle=args.settle, timeout=args.timeout)
        who = "OURS " if m == OURS_MACHINE else "STOCK"
        mode = next((l for l in raw if l.startswith("MODE")), "MODE ?")
        print(f"=== screen: {who} ({m})  [{mode}]  settle={args.settle}s ===")
        rows = [l for l in raw if l.startswith("ROW")]
        if not rows:
            print("  (no screen rows captured — boot may not have settled)")
        for l in rows:
            print("  " + l)
        extra = [l for l in raw if l.startswith(("HEX", "FOUND"))]
        for l in extra:
            print("  " + l)
        print()
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
    c.add_argument("--poke", action="append", metavar="ADDR:VAL",
                   help="inject mem write into OURS at --poke-at (falsify-first); repeatable")
    c.add_argument("--poke-reg", action="append", metavar="REG:VAL",
                   help="override a register in OURS at --poke-at (e.g. BC:0x0101); repeatable")
    c.add_argument("--poke-at", type=lambda x: int(x, 0), default=0x0100,
                   help="address at which to apply pokes (default $0100)")
    c.add_argument("--poke-nth", type=int, default=1, help="apply at this hit of --poke-at (after armed)")

    p = sub.add_parser("capture", help="diff regs+mem at the Nth occurrence of an address")
    common(p)
    p.add_argument("--at", type=lambda x: int(x, 0), required=True, help="anchor address")
    p.add_argument("--nth", type=int, default=1, help="stop at this occurrence")
    p.add_argument("--mem", default=None, help="memory range BASE:LEN (e.g. 0xF100:0x300)")
    p.add_argument("--expect", choices=("same", "diff"), help="assert reg-diff outcome (PASS/FAIL)")

    t = sub.add_parser("trace", help="forward instruction trace from an anchor; report first PC fork")
    common(t)
    t.add_argument("--at", type=lambda x: int(x, 0), default=0x0100, help="arm address")
    t.add_argument("--arm-check-addr", type=lambda x: int(x, 0), default=0x0102)
    t.add_argument("--arm-check-val", type=lambda x: int(x, 0), default=0x05)
    t.add_argument("--arm-cond", default=None, help="raw Tcl arm predicate (overrides --arm-check-*)")
    t.add_argument("--anchor", type=lambda x: int(x, 0), required=True,
                   help="start tracing at the Nth occurrence of this addr after arm")
    t.add_argument("--nth", type=int, default=1)
    t.add_argument("--steps", type=int, default=120, help="instructions to trace")
    t.add_argument("--poke", action="append", metavar="ADDR:VAL",
                   help="inject mem write into OURS at the anchor (falsify-first); repeatable")
    t.add_argument("--resync", action="store_true",
                   help="re-convergence walk: skip benign relocation detours, find the next REAL fork")

    s = sub.add_parser("screen", help="render the VDP text screen (VRAM name table) as text")
    common(s)
    s.add_argument("--machine", choices=("both", "ours", "stock"), default="both",
                   help="which machine(s) to dump (default both)")

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
        return {"callseq": mode_callseq, "capture": mode_capture,
                "trace": mode_trace, "screen": mode_screen}[args.mode](args)
    finally:
        if tmp_disk and os.path.exists(tmp_disk):
            os.unlink(tmp_disk)


if __name__ == "__main__":
    raise SystemExit(main())
