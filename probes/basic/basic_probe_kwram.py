#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""kwram -- the T4 row type: each keyword's test program, its RAM use compared.

D-KWPROVEN's T4 (TODO §"WHAT PROVES A RUNG?"). Joost ruled T4 "matches the
reference's RAM usage", DERIVED from the whole-RAM-map comparison against the
VG-8020 (the CF-3300 for a disk-only keyword), with three goals: (a) the same
free memory, (b) the same addresses, (c) the same economy. The row type was
ruled 2026-09-30, all three recommendations taken:
  (a) FREE MEMORY   FRE(0) and FRE("") move by the SAME amount across the row
                    on both machines (a delta: the boot baselines differ by
                    design).
  (b) ADDRESSES     STRICT -- the SAME SET of documented work-area cells
                    ($F380.., the published MSX work area; the slot register
                    $FFFF is hardware, not a cell) is written, and each ENDS
                    with the same value.
  (c) ECONOMY       distinct cells written, zerobas / reference -- SHOWN,
                    never ticked (like T5's ratio).
  Undocumented cells in the reference's own workspace are REPORTED (the (c)
  count sees them) and kept out of the tick.
T4 ticks (tools/tier_table.py) when every authored FORM of the keyword has a row
whose (a) and (b) both pass.

🎯 THE INSTRUMENT IS D-RAMFOOT's (scratchpad/ramfoot_probe.py), unchanged in
method: a `write_mem` watchpoint over $E001..$FFFF counts only while a window
the program opens and closes itself is open (`POKE&HE000,201/202`), each window
tagged by the case's own index (`POKE&HE002,n`) so a lost window cannot shift
rows; stack pushes are CLASSIFIED by SP and never counted; an EMPTY window gives
the background and the interrupt's SIGNATURE is measured on a control, both
removed from every row. The rows are kwtime's (kwsweep's plain and disk-only
rows that declare a FORM), typed with explicit line numbers so nothing a row
names moves.

🔴 CONTROLS, and the run REFUSES without them:
  ctl  the empty window: the background (the closing POKE's own evaluation).
  pos  POSITIVE: `POKE&HE001,7` must record $E001, or the watchpoint is blind.
  isr  a window held across a tick: the interrupt's own cells.
  --negative  plants one documented-cell write (the cell's OWN value, so
       nothing changes but the set) on zerobas's side of every row; EVERY row's
       (b) must then FAIL, or (b) cannot see a divergence.
🔴 (a) CANNOT BE FAKED BY A ROW THAT CLEARS: a sentinel set before the window
must read back after it, or the row's (a) is UNRATED (CLEAR, MAXFILES, RUN wipe
the variables that carry the readings).
🔴 CLEAN ROOM: RAM addresses, RAM contents and SP only -- no ROM byte, no PC,
nothing single-stepped. The reference's RAM-resident code clusters (§8.5) are
not in this band on a diskless VG-8020; on the CF-3300 a cell inside one is
counted by address and never decoded.

    python3 probes/basic/basic_probe_kwram.py [--zb-machine M] [--only KEYS]
    python3 probes/basic/basic_probe_kwram.py --negative
    python3 probes/basic/basic_probe_kwram.py --selftest

Exit: 0 measured (a failing (a)/(b) is a FINDING that feeds the sheet); 2 the
instrument could not measure (a control failed, a variable clash, a degenerate
run).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "probes", "lib"))
sys.path.insert(0, _HERE)
import omsx_repl  # noqa: E402
import basic_probe_kwsweep as kw  # noqa: E402
import basic_probe_kwtime as kt  # noqa: E402

REF, DISK_REF = kt.REF, kt.DISK_REF
PIN = os.path.join(_ROOT, "build", "kwram.json")
MARK, OPEN, CLOSE, TAG = 0xE000, 201, 202, 0xE002
LO, HI = 0xE001, 0xFFFF
STD = 0xF380                    # the published MSX work area starts here
SLOTREG = 0xFFFF                # the secondary-slot register: hardware, not a cell
HTIMI = 0xFD9F
# the readings' carriers -- created BEFORE the window; K3 refuses a row using one
VARS = ("X7", "F7", "F8", "G7", "G8", "S7")
PLANT = "POKE&HF3B0,PEEK(&HF3B0)"   # --negative: a documented cell, its own value
GROUPS = (("plain", REF), ("disk", DISK_REF))

TCL = r'''
set ::w -1
set ::open 0
array set ::hit {}
array set ::sp0 {}
array set ::spmin {}
array set ::closed {}
array set ::val {}
array set ::tag {}
array set ::th {}
array set ::t0 {}
array set ::tt {}
array set ::many {}
debug set_watchpoint write_mem @MARK@ {} {
    if {$::wp_last_value == @OPEN@} {
        incr ::w
        set ::open 1
        set ::sp0($::w) [reg SP]
        set ::spmin($::w) [reg SP]
        set ::t0($::w) [machine_info time]
    } elseif {$::wp_last_value == @CLOSE@ && $::open} {
        set ::open 0
        set ::closed($::w) 1
        foreach k [array names ::hit "$::w,*"] {
            set a [lindex [split $k ,] 1]
            if {$a >= @STD@} { set ::val($k) [peek $a] }
        }
        __flush $::w
    }
}
# 🔴 EACH WINDOW IS WRITTEN ONCE, WHEN IT CLOSES, THEN FORGOTTEN. The first cut
# rewrote the WHOLE accumulated dump every emulated second (ramfoot_probe.py's
# shape, fine for its 19 cases): over a 660-case boot that cost grew with the run,
# and the harness's 1800 s wall watchdog killed the emulator with 419 captures
# missing. A window that never closes is never written -- which is exactly the
# UNRATED reading it should get.
proc __flush {w} {
    set f [open {@OUT@} a]
    puts $f "S $w $::sp0($w) $::spmin($w) 1"
    foreach k [array names ::hit "$w,*"] {
        set m 0
        if {[info exists ::many($k)]} { set m 1 }
        puts $f "H $k $::hit($k) $m $::tt($k)"
        if {[info exists ::val($k)]} { puts $f "V $k $::val($k)" }
    }
    if {[info exists ::th($w)]} { puts $f "I $w $::th($w)" }
    if {[info exists ::tag($w)]} { puts $f "T $w $::tag($w)" }
    close $f
    array unset ::hit "$w,*"
    array unset ::tt "$w,*"
    array unset ::many "$w,*"
    array unset ::val "$w,*"
}
debug set_bp @HTIMI@ {} { if {$::open} {
    lappend ::th($::w) [expr {[machine_info time] - $::t0($::w)}] } }
debug set_watchpoint write_mem {@LO@ @HI@} {} {
    if {!$::open} { return }
    if {$::wp_last_address == @TAGA@} { set ::tag($::w) $::wp_last_value }
    set sp [reg SP]
    if {$sp < $::spmin($::w)} { set ::spmin($::w) $sp }
    set k "$::w,$::wp_last_address"
    set t [expr {[machine_info time] - $::t0($::w)}]
    if {[info exists ::hit($k)]} { incr ::hit($k) } else { set ::hit($k) 1 ; set ::tt($k) {} }
    if {[llength $::tt($k)] < 32} { lappend ::tt($k) $t } else { set ::many($k) 1 }
}
'''


def prologue(out):
    t = TCL
    for k, v in (("@OUT@", out), ("@MARK@", str(MARK)), ("@OPEN@", str(OPEN)),
                 ("@CLOSE@", str(CLOSE)), ("@LO@", str(LO)), ("@HI@", str(HI)),
                 ("@TAGA@", str(TAG)), ("@HTIMI@", str(HTIMI)), ("@STD@", str(STD))):
        t = t.replace(k, v)
    return (t,)


def case_lines(body, idx, plant=None):
    """The row as explicitly numbered lines inside a TAGGED window.
    `body` is the row's packed statement list (or [] for the empty control).
    Lines 1-2 create the carriers and take the before-readings; 5-6 sync to the
    interrupt (kwtime's reason); 7 opens and tags the window; the row runs at
    10, 20, ...; the line after it closes the window and takes the after-
    readings; the next prints them, back on the text screen."""
    first = f"7 POKE&H{MARK:04X},{OPEN}:POKE&H{TAG:04X},{idx}"
    if plant:
        first += ":" + plant
    n = 10 * (len(body) + 1)
    return [omsx_repl.BREAK_PREFIX, "NEW", kt.RESET,
            "1 CLS:X7=0:F7=0:F8=0:G7=0:G8=0",
            '2 S7=77:F7=FRE(0):G7=FRE("")',
            "5 X7=TIME", "6 IF TIME=X7 THEN 6", first] + \
        [f"{10 * (i + 1)} {b}" for i, b in enumerate(body)] + \
        [f'{n} POKE&H{MARK:04X},{CLOSE}:F8=FRE(0)',
         f'{n + 1} G8=FRE(""):SCREEN0',
         f'{n + 2} PRINT CHR$(91);"K";F7-F8;',
         f'{n + 3} PRINT G7-G8;S7;CHR$(93)', "RUN"]


READING = re.compile(r"\[K\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\]")


def reading(cap):
    """-> (dfre0, dfrestr) from the screen, or None (no reading / variables wiped)."""
    m = READING.findall(cap or "")
    if not m:
        return None
    f, g, s = (int(x) for x in m[-1])
    return (f, g) if s == 77 else None


def parse(path):
    """-> {tag: {"sp0","spmin","closed","cells":{a:n},"times":{a:[t]|None},
    "vals":{a:v},"ticks":[t]}}"""
    out, vals = {}, {}
    for ln in open(path):
        p = ln.split()
        if not p:
            continue
        if p[0] == "S" and len(p) == 5:
            out.setdefault(int(p[1]), {"cells": {}}).update(
                sp0=int(p[2]), spmin=int(p[3]), closed=p[4] == "1")
        elif p[0] == "H" and len(p) >= 4:
            w, a = (int(x) for x in p[1].split(","))
            d = out.setdefault(w, {"cells": {}})
            d["cells"][a] = int(p[2])
            d.setdefault("times", {})[a] = (None if p[3] == "1"
                                            else [float(x) for x in p[4:]])
        elif p[0] == "V" and len(p) == 3:
            w, a = (int(x) for x in p[1].split(","))
            vals.setdefault(w, {})[a] = int(p[2])
        elif p[0] == "I" and len(p) >= 3:
            out.setdefault(int(p[1]), {"cells": {}})["ticks"] = [float(x) for x in p[2:]]
        elif p[0] == "T" and len(p) == 3:
            out.setdefault(int(p[1]), {"cells": {}})["tag"] = int(p[2])
    for w, v in vals.items():
        out.setdefault(w, {"cells": {}})["vals"] = v
    return {d["tag"]: d for d in out.values() if "tag" in d}


def split_stack(win):
    """-> the window's CELLS: a push inside [spmin, sp0+2) is not one, nor are
    the probe's own mark and tag cells (ramfoot_probe.py's rule)."""
    lo, hi = win.get("spmin", 0), win.get("sp0", 0) + 2
    return {a for a in win["cells"]
            if not (lo <= a < hi) and a not in (MARK, TAG)}


ISR_PRE, ISR_POST = 0.0003, 0.003


def isr_cells(win, cells):
    """ramfoot_probe.py's interrupt signature: cells EVERY write of which sits
    within 0.3 ms before .. 3 ms after an H.TIMI hit (per write, never a span)."""
    ticks, times = win.get("ticks", []), win.get("times", {})
    return {a for a in cells if times.get(a) and all(
        any(h - ISR_PRE <= t <= h + ISR_POST for h in ticks) for t in times[a])}


def std_part(cells, vals):
    """-> {addr: final value} for the DOCUMENTED cells among `cells`."""
    return {a: vals.get(a) for a in cells if a >= STD and a != SLOTREG}


def verdict(ref, zb):
    """ref / zb: {"cells": set, "std": {a: v}, "fre": (f, g) | None, "closed"}.
    -> {"a": PASS/FAIL/UNRATED, "b": PASS/FAIL/UNRATED, "c": ratio | None, ...}"""
    out = {}
    if not (ref["closed"] and zb["closed"]):
        return {"a": "UNRATED", "b": "UNRATED", "c": None, "why": "window not closed"}
    if ref["fre"] is None or zb["fre"] is None:
        out["a"] = "UNRATED"
    else:
        out["a"] = "PASS" if ref["fre"] == zb["fre"] else "FAIL"
    rs, zs = ref["std"], zb["std"]
    out["b"] = "PASS" if rs == zs else "FAIL"
    out["b_ref_only"] = sorted(set(rs) - set(zs))
    out["b_zb_only"] = sorted(set(zs) - set(rs))
    out["b_value"] = sorted(a for a in set(rs) & set(zs) if rs[a] != zs[a])
    nr, nz = len(ref["cells"]), len(zb["cells"])
    out["c"] = round(nz / nr, 2) if nr else None
    out["cells"] = (nr, nz)
    out["fre"] = (ref["fre"], zb["fre"])
    return out


def cache_key(machine, specs, rk):
    """The WHOLE group's key -- probe_refcache's all-or-nothing rule: under
    `batch=True` one boot serves the matrix, so a partial replay would change the
    composition of what still runs. Built from the machine's CONTENT (its ROM
    bytes: zerobas misses on every rebuild by construction), every typed line,
    the parameters, and this instrument's Tcl TEMPLATE -- not the per-run dump
    path inside the rendered prologue, which would make every key unique. A disk
    rig hands out a fresh temp COPY of the image per call, so the image is keyed
    by its content hash, not its path."""
    import probe_refcache as rc
    params = {k: v for k, v in rk.items() if k != "prologue"}
    if params.get("diska"):
        params["diska"] = "sha:" + rc._file_sha(params["diska"])
    params["kwram_tcl"] = TCL
    return rc.key_for(machine, specs, params)


CACHE = {"hit": 0, "miss": 0}


def measure(machine, bodies, extra, plant=None):
    """One batched boot: the three controls then every row -> per-case windows
    and screen captures.
    🗄️ REPLAYED FROM THE REFERENCE CACHE when this exact group was measured
    before (Joost 2026-09-30: *"reference is not going to change behavior all of a
    sudden, so once we know what memory reference uses, we don't need to measure
    that again, unless we do a different test"*). The windows ride in the stored
    `settle` dict; `ZEROBAS_REFCACHE=0` (the emulator gate tier) measures live."""
    import probe_refcache as rc
    # 🔴 THE INTERRUPT CONTROL SPANS THREE TICKS, NOT ONE: with a one-tick window
    # the keyboard rows (NEWKEY $FBE1..) and a repeat counter ($F3F7) showed up on
    # zerobas's side of a row only when a tick happened to land inside it -- the
    # same row read differently in two runs (kwram_first.out vs kwram_negative.out).
    # Cells the handler writes on only SOME ticks need more ticks to be seen.
    ctl = [[], ["POKE&HE001,7"], ["X7=TIME:FOR J7=1 TO 2:J7=1-(TIME<X7+3):NEXT"]]
    specs = [("direct", case_lines(b, i, plant if i >= 3 else None))
             for i, b in enumerate(ctl + bodies)]
    rk = dict(batch=True, capture="screen", boot=8.0)
    rk.update(extra or {})
    key = cache_key(machine, specs, rk) if rc.ENABLED else None
    if key:
        caps, so = rc.load(key)
        if caps is not None and so and "windows" in so and len(caps) == len(specs):
            CACHE["hit"] += 1
            return so["windows"], caps
    fd, out = tempfile.mkstemp(prefix="kwram-", suffix=".txt")
    os.close(fd)
    try:
        # the call below goes around run_cases's own cache on purpose: its key
        # would include the rendered prologue (a fresh path every run)
        caps = omsx_repl._run_cases_impl(machine, specs, reset=(),
                                         prologue=prologue(out), **rk)
        wins = parse(out)
    finally:
        os.unlink(out)
    CACHE["miss"] += 1
    if key and wins:
        rc.store(key, caps, machine, settle={"windows": wins})
    return wins, caps


def side(win, caps, i, bg, isr):
    if win is None:
        return {"closed": False, "cells": set(), "std": {}, "fre": None}
    cells = split_stack(win) - bg - isr
    return {"closed": bool(win.get("closed")), "cells": cells,
            "std": std_part(cells, win.get("vals", {})),
            "fre": reading(caps[i] if caps and i < len(caps) else None)}


def controls(res, caps, name):
    """-> (background, isr signature), or raise SystemExit(2)."""
    pos = res.get(1)
    if not pos or MARK + 1 not in pos["cells"]:
        print(f"kwram: REFUSING -- {name}: the positive control did not record $E001")
        raise SystemExit(2)
    if 0 not in res or 2 not in res or not res[2].get("ticks"):
        print(f"kwram: REFUSING -- {name}: a control window is missing "
              f"(background {0 in res}, interrupt {2 in res and bool(res[2].get('ticks'))})")
        raise SystemExit(2)
    bg = split_stack(res[0])
    return bg, isr_cells(res[2], split_stack(res[2]))


def rows_for(only):
    """kwtime's rows, minus the ERROR rows. 🔴 A `PROVES-T6:` or `PROVES-T3:` row
    exists to RAISE: its program stops before the window's closing line, so it
    can only ever read UNRATED -- the first full run was 590 of 836 UNRATED, and
    the unbroken stretch of them was exactly kwsweep's T6 batches. T4 is about
    what a WORKING statement uses; an error row says nothing about that."""
    notes = {r[0]: (r[4] if len(r) > 4 else "") for r in kw.SWEEP}

    def error_row(key):
        n = notes.get(key, "")
        return kw.row_t6_code(n) is not None or "PROVES-T3:" in kw._row_prefix_tags(n)
    rows = kt.select_rows(only)
    return [r for r in rows if kt.GROUP[r[0]] in dict(GROUPS)
            and not kt.RESP.get(r[0]) and not error_row(r[0])]


def clashes(rows):
    """K3: a row that uses one of the carriers would corrupt its own reading."""
    bad = []
    for key, line, _m, _w in rows:
        for v in VARS:
            if re.search(rf"(?<![A-Z0-9]){v}(?![A-Z0-9$%!#])", line.upper()):
                bad.append(key)
                break
    return bad


def run(zb_machine, only=None, plant=None):
    rows = rows_for(only)
    # 🔴 A TYPED LINE OVER 38 CHARACTERS IS NOT DELIVERED WHOLE (kwtime's rule), and
    # a row dropped for it is NAMED, never dropped quietly: the first cut of this
    # probe's own closing lines were 39+ characters and filtered out EVERY row,
    # printing an empty table with exit 0.
    long_rows = [r[0] for r in rows if any(len(l) > kt.MAX_TYPED for l in
                                           case_lines(omsx_repl.as_stored(r[1]), 0))]
    if long_rows:
        print(f"kwram: {len(long_rows)} row(s) NOT MEASURED -- a typed line over "
              f"{kt.MAX_TYPED} characters: {' '.join(long_rows)}")
    rows = [r for r in rows if r[0] not in long_rows]
    if not rows:
        print("kwram: REFUSING -- no row left to measure")
        raise SystemExit(2)
    bad = clashes(rows)
    if bad:
        print(f"kwram: REFUSING -- row(s) {bad} use a carrier variable {VARS}")
        raise SystemExit(2)
    result = {}
    for group, refm in GROUPS:
        grows = [r for r in rows if kt.GROUP[r[0]] == group]
        if not grows:
            continue
        for c0 in range(0, len(grows), CHUNK):
            chunk_rows(result, group, refm, zb_machine, grows[c0:c0 + CHUNK], plant)
    return result


# 🔴 A BOOT MEASURES AT MOST CHUNK ROWS, each chunk with its own three controls:
# one 660-case boot per machine ran past the harness's 1800 s wall watchdog.
# A chunk is also the cache's unit (probe_refcache's all-or-nothing is per call).
CHUNK = 40


def chunk_rows(result, group, refm, zb_machine, grows, plant):
        bodies = [omsx_repl.as_stored(r[1]) for r in grows]
        rres, rcaps = measure(refm, bodies, kt.group_kwargs(group, refm))
        zres, zcaps = measure(zb_machine, bodies, kt.group_kwargs(group, zb_machine), plant)
        rbg, risr = controls(rres, rcaps, f"{group} ref")
        zbg, zisr = controls(zres, zcaps, f"{group} zb")
        # 🔴 THE UNION OF BOTH INTERRUPT SIGNATURES, FROM BOTH SIDES. zerobas's
        # handler writes the upper keyboard rows ($FBE1..$FBE4) and $F3F7 only on
        # SOME ticks, so its own three-tick control can miss them -- and then
        # whether a row's window caught one depended on where a tick fell in the
        # BATCH: `str`/`let` showed them in a 10-row batch and not in a 3-row one
        # (kwram_isr.out). Both machines' interrupts own those cells; neither
        # machine's keyword does.
        isr = risr | zisr
        for j, (key, _l, _m, word) in enumerate(grows):
            i = j + 3
            r = side(rres.get(i), rcaps, i, rbg, isr)
            z = side(zres.get(i), zcaps, i, zbg, isr)
            v = verdict(r, z)
            v.update(keyword=word, form=kt.FORMS.get(key), group=group, ref_machine=refm)
            result[key] = v


def show(result):
    print(f"{'row':16} {'kw':10} {'(a)':8} {'(b)':8} {'(c)':>6}  detail")
    tally = {}
    for key, v in result.items():
        tally[(v["a"], v["b"])] = tally.get((v["a"], v["b"]), 0) + 1
        det = ""
        if v["b"] == "FAIL":
            det = (f"ref-only {' '.join(f'${a:04X}' for a in v['b_ref_only'][:6])}"
                   f"{'…' if len(v['b_ref_only']) > 6 else ''} | "
                   f"zb-only {' '.join(f'${a:04X}' for a in v['b_zb_only'][:6])}"
                   f"{'…' if len(v['b_zb_only']) > 6 else ''}"
                   + (f" | value {' '.join(f'${a:04X}' for a in v['b_value'][:4])}"
                      if v["b_value"] else ""))
        if v["a"] == "FAIL":
            det = f"FRE ref {v['fre'][0]} zb {v['fre'][1]}  " + det
        c = "-" if v.get("c") is None else f"{v['c']:.2f}x"
        print(f"{key:16} {str(v['keyword']):10} {v['a']:8} {v['b']:8} {c:>6}  {det}")
    print("kwram: " + " · ".join(f"a={a} b={b}: {n}" for (a, b), n in sorted(tally.items())))


def negative(zb_machine):
    """Plant one documented-cell write on zerobas's side of every row: (b) must
    FAIL everywhere, or (b) is blind."""
    only = {"let", "abs", "int", "len", "chr", "peek"}
    res = run(zb_machine, only=only, plant=PLANT)
    rated = {k: v for k, v in res.items() if v["b"] != "UNRATED"}
    ok = bool(rated) and all(v["b"] == "FAIL" and 0xF3B0 in v["b_zb_only"]
                             for v in rated.values())
    for k, v in sorted(rated.items()):
        print(f"  {k:10} (b) {v['b']:5} zb-only {' '.join(f'${a:04X}' for a in v['b_zb_only'])}")
    print("kwram --negative: " + ("GREEN -- a planted cell is caught" if ok else
                                  "RED -- (b) did not see the planted write"))
    return 0 if ok else 1


def selftest():
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(("  ok   " if cond else "  FAIL ") + name)
        ok &= bool(cond)

    base = {"closed": True, "cells": {0xF3A0, 0xE100}, "std": {0xF3A0: 5}, "fre": (10, 0)}
    same = verdict(base, dict(base))
    arm("R1 identical sides pass (a) and (b)", same["a"] == "PASS" and same["b"] == "PASS")
    arm("R2 NEGATIVE: an extra documented cell fails (b)",
        verdict(base, dict(base, std={0xF3A0: 5, 0xF3B0: 1}))["b"] == "FAIL")
    arm("R3 NEGATIVE: the same cell ending on another value fails (b)",
        verdict(base, dict(base, std={0xF3A0: 6}))["b"] == "FAIL")
    arm("R4 NEGATIVE: a different FRE delta fails (a)",
        verdict(base, dict(base, fre=(12, 0)))["a"] == "FAIL")
    arm("R5 a wiped sentinel is UNRATED, never PASS",
        verdict(base, dict(base, fre=None))["a"] == "UNRATED")
    arm("R6 an unclosed window rates nothing",
        verdict(base, dict(base, closed=False))["b"] == "UNRATED")
    arm("R7 (c) is the cell ratio", verdict(base, dict(base, cells={1, 2, 3, 4}))["c"] == 2.0)
    arm("R8 the slot register is not a documented cell",
        std_part({0xFFFF, 0xF380, 0xF37F}, {0xF380: 1}) == {0xF380: 1})
    arm("R9 reading parses and checks the sentinel",
        reading("x [K 12  0  77 ]") == (12, 0) and reading("[K 12 0 5 ]") is None)
    arm("R10 case_lines keeps the row's own numbering at 10, 20",
        case_lines(["A=1", "B=2"], 4)[8:10] == ["10 A=1", "20 B=2"]
        and case_lines(["A=1"], 4)[7] == "7 POKE&HE000,201:POKE&HE002,4")
    arm("R11 NEGATIVE: a carrier clash is found",
        clashes([("x", "S7=1", "stored", "LET")]) == ["x"]
        and clashes([("y", "S77=1", "stored", "LET")]) == [])
    fd, p = tempfile.mkstemp()
    os.write(fd, b"S 0 61440 61430 1\nH 0,62000 1 0 0.001\nV 0,62000 9\nT 0 3\n")
    os.close(fd)
    got = parse(p)
    os.unlink(p)
    arm("R12 parse re-keys by tag and carries values",
        list(got) == [3] and got[3]["vals"] == {62000: 9})
    print("kwram selftest: " + ("GREEN" if ok else "RED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zb-machine", default=os.environ.get(
        "ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
    ap.add_argument("--only", default="")
    ap.add_argument("--negative", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.negative:
        return negative(a.zb_machine)
    only = set(a.only.split(",")) - {""} or None
    fp = kw._rom_fingerprint()
    res = run(a.zb_machine, only)
    if kw._rom_fingerprint() != fp:
        print("kwram: REFUSING -- the ROM changed during the run")
        return 2
    show(res)
    print(f"kwram cache: {CACHE['hit']} group(s) replayed, {CACHE['miss']} measured")
    if only is None:
        os.makedirs(os.path.dirname(PIN), exist_ok=True)
        with open(PIN, "w") as f:
            json.dump({"rom_fingerprint": fp, "rows": res}, f, indent=1, sort_keys=True)
        print(f"pin: {len(res)} row(s) -> {PIN}")
    else:
        print("pin: NOT written -- an --only run measures a subset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
