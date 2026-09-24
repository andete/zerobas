#!/usr/bin/env python3
r"""kwtime — the T2/T5 row type: each keyword's test program, TIMED on both sides.

D-KWPROVEN (TODO §"WHAT PROVES A RUNG?"). Joost, 2026-09-24:
  T2  "reasonable time" = the keyword's test program completes within **10x the
      VG-8020's time** ("use 10x, it will be slow, but it finishes").
  T5  "on-par speed"    = *"Track the ratio, set no bar yet"* -- the ratio is
      SHOWN and never ticked.
So the two rungs are ONE measurement: zerobas / VG-8020 for the same program,
with completion as the watchdog. This probe takes it; `tools/tier_table.py`
reads the pin it writes (`build/kwtime.json`) and joins it with kwsweep's.

🕐 THE CLOCK IS THE PROGRAM-WRITTEN MARK (docs/spec-probe-mark.md), NOT `TIME`.
`TIME` counts 1/50 s, so a short row would be a ratio of two small integers;
the mark reads the EMULATED instant of a RAM write, which is deterministic --
measured bit-identical across two runs of the prototype on 2026-09-24 -- and
needs no ROM knowledge on either machine. So there is no "too short to time"
rule to write: nothing here is quantised. What a short row IS dominated by is the
marks' own cost (an empty program measured 1.3 ms ref / 3.3 ms zb), and the
report says so per row rather than hiding it.

🔴 A MARK MUST NOT MOVE THE ROW'S OWN LINE NUMBERS. 34 plain rows name a line
(`GOTO 40`, `ON ERROR GOTO 20`, `RESTORE 50`) in the 10/20/30 numbering the
harness gives a stored program. So the case is typed with EXPLICIT numbers --
kwsweep's own `RESPOND:` shape -- with the start mark on line 5 (before 10) and
the end mark one line past the row's last. Nothing the row names moves.
🔴 AND THE ROW'S TEXT IS NOT CHANGED, which is why this is a SEPARATE suite and
not a mark added to kwsweep's rows: a mark is BASIC text, and a row whose
reading is an ADDRESS (`VARPTR`, `FRE`) would move by the mark's length
(spec-probe-mark.md rule 3). T1's rows stay exactly as they were.

📋 STATUS OF A ROW:
  OK          both sides reach the end mark; zb/ref <= 10
  SLOW        both reach it; zb/ref > 10                       -> T2 NOT proven
  HANG        the reference reaches it and zerobas does not     -> T2 NOT proven
  UNTIMEABLE  neither reaches it -- the row ENDs, errors or RUNs away before its
              last line, so this SHAPE cannot time it; not a verdict on speed
  REF-ONLY-MISSING  zerobas reaches it and the reference does not -- no ratio
A `CLS` precedes the start mark: without it a batched run's accumulated screen
makes `PRINT` scroll, and zerobas's scroll is slower -- measured, batched deltas
drifted +1.7..3.4 ms from boot-per-case until the `CLS` went in, after which they
agree to within one interrupt's service time (~0.25 ms).

    python3 probes/basic/basic_probe_kwtime.py [--zb-machine M] [--only KEYS]
    python3 probes/basic/basic_probe_kwtime.py --negative   # live NEGATIVE control
    python3 probes/basic/basic_probe_kwtime.py --selftest   # pure arms, no emulator

Exit: 0 measured (SLOW/HANG rows are FINDINGS, reported, not gate failures --
they feed the sheet); 2 the instrument could not measure (degenerate run, ROM
changed mid-run, a row that writes the mark values).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path[:0] = [os.path.join(_ROOT, "probes", "lib"), _HERE]

import probe_tmp  # noqa: F401,E402  -- one temp root for every tempfile user
import omsx_repl  # noqa: E402
import basic_probe_kwsweep as kw  # noqa: E402

REF = "Philips_VG_8020"
MARK_ADDR = 0xE000
START, END = 201, 202        # values no kwsweep row writes (peek_b writes 66 here)
BAR = 10.0                   # Joost 2026-09-24: "use 10x"
PIN = os.path.join(_ROOT, "build", "kwtime.json")
# 🔴 A DEGENERATE RUN IS REFUSED, NOT PINNED -- the kwcover SUITE_FLOOR lesson. A
# boot that went wrong times nothing on EITHER side, and a pin of zero OK rows
# would read as "no keyword completes in reasonable time" on the sheet.
REF_FLOOR = 100
MARK_LITERALS = [f"{a},{v}" for a in ("&HE000", "-8192") for v in (START, END)]


def select_rows(only=None):
    """kwsweep's PLAIN rows that declare a FORM -- the rows T1 counts.

    Plain = no rig (disk/printer/tape/hold/plug), not an editor (`PROGRAM:`) row,
    not a `RESPOND:` row: those need machinery this shape does not drive, and a
    keyword whose only rows are rigged simply has no T2 reading yet."""
    out = []
    for key, _crunch, line, mode, note in kw.SWEEP:
        if line is None or kw._row_rigs(note) or kw.row_program(note) \
                or kw.row_respond(note) or not kw.row_form(note):
            continue
        if only and key not in only:
            continue
        out.append((key, line, mode))
    return out


# 🔴 A TYPED LINE OVER 38 CHARACTERS IS NOT DELIVERED WHOLE. kwsweep's stored mode
# gets past a long single statement through the harness's TXTTAB fallback; a
# typed, explicitly numbered line has no such path, and one mangled delivery
# poisons the whole batch. Such rows are left out and NAMED, never dropped quietly.
MAX_TYPED = 38


def too_long(rows):
    return [k for k, line, _m in rows
            if any(len(l) > MAX_TYPED for l in case_lines(line))]


def case_lines(line, pad=None):
    """The row as explicitly numbered lines, bracketed by the two marks."""
    body = omsx_repl.as_stored(line)
    first = f"5 CLS:POKE&H{MARK_ADDR:04X},{START}"
    if pad:                                   # --negative: slow THIS side only
        first += ":" + pad
    lines = [first] + [f"{10 * (i + 1)} {b}" for i, b in enumerate(body)]
    lines.append(f"{10 * (len(body) + 1)} POKE&H{MARK_ADDR:04X},{END}")
    return lines + ["RUN"]


def delta(marks):
    """Emulated seconds from this case's START mark to its END mark, or None.

    In a batched boot every case arms its own watchpoint and none is removed, so
    case i's log also holds LATER cases' writes. Take the first START, then the
    first END after it -- but only if it comes before the NEXT START, or a case
    that never finished would borrow the next case's END."""
    starts = [t for t, v in marks if v == START]
    if not starts:
        return None
    t0 = starts[0]
    nxt = starts[1] if len(starts) > 1 else float("inf")
    ends = [t for t, v in marks if v == END and t0 < t < nxt]
    return (ends[0] - t0) if ends else None


def status(ref, zb):
    if ref is None and zb is None:
        return "UNTIMEABLE"
    if zb is None:
        return "HANG"
    if ref is None:
        return "REF-ONLY-MISSING"
    return "OK" if zb / ref <= BAR else "SLOW"


def measure(machine, rows, pad=None):
    specs = [("direct", case_lines(line, pad)) for _k, line, _m in rows]
    so: dict = {}
    omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW", "CLS"),
                        capture="screen", boot=8.0,
                        sentinel=(MARK_ADDR, END), settle_out=so)
    marks = so.get("marks", {})
    return [delta(marks.get(i, [])) for i in range(len(rows))]


def rom_part(fp):
    """The ROM hashes of a fingerprint, without the git revision -- two pins from
    one battery share ROMs; a commit in between must not make them disagree."""
    return " ".join(p for p in (fp or "").split() if not p.startswith("git="))


def negative(zb_machine):
    """LIVE NEGATIVE CONTROL: the same rows, zerobas's side padded with a delay
    loop inside the timed window. Every one MUST come back SLOW -- if any reads
    OK, the ratio or the bar is not doing what the sheet will claim."""
    rows = select_rows({"abs", "mid", "sgn"})
    if len(rows) != 3:
        print(f"kwtime --negative: expected 3 control rows, found {len(rows)}")
        return 2
    ref = measure(REF, rows)
    zb = measure(zb_machine, rows, pad="FOR Q9=1 TO 200:NEXT")
    bad = 0
    for (key, _l, _m), r, z in zip(rows, ref, zb):
        st = status(r, z)
        ratio = f"{z / r:.1f}x" if r and z else "-"
        ok = st == "SLOW"
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {key:6} padded zb/ref {ratio:>7}  -> {st}")
    print("kwtime --negative:", "GREEN -- a slowed side is caught" if not bad
          else f"RED -- {bad} padded row(s) were NOT caught")
    return 0 if not bad else 1


def selftest():
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and cond
    arm("K1 a START then END gives the delta", delta([(1.0, START), (1.5, END)]) == 0.5)
    arm("K2 no END is None", delta([(1.0, START)]) is None)
    arm("K3 NEGATIVE: an END after the NEXT case's START is not borrowed",
        delta([(1.0, START), (2.0, START), (2.5, END)]) is None)
    arm("K4 other values at the address are ignored (peek_b writes 66)",
        abs(delta([(1.0, START), (1.2, 66), (1.4, END)]) - 0.4) < 1e-9)
    arm("K5 ratio <= 10 is OK", status(1.0, 9.9) == "OK")
    arm("K6 NEGATIVE: ratio 20 is SLOW, not OK", status(1.0, 20.0) == "SLOW")
    arm("K7 exactly 10x is OK (\"within 10x\")", status(1.0, 10.0) == "OK")
    arm("K8 reference finishes, zerobas does not: HANG", status(1.0, None) == "HANG")
    arm("K9 neither finishes: UNTIMEABLE, not HANG", status(None, None) == "UNTIMEABLE")
    ls = case_lines('A=0:GOSUB 20:PRINT"[G";A;"]":END:A=7:RETURN')
    arm("K10 the row keeps its own 10/20/30 numbering (GOSUB 20 still lands)",
        ls[1].startswith("10 ") and any(l.startswith("20 ") for l in ls))
    arm("K11 the start mark is line 5 and the end mark the last numbered line",
        ls[0].startswith("5 ") and "POKE&HE000,201" in ls[0]
        and f",{END}" in ls[-2] and ls[-1] == "RUN")
    arm("K12 the fingerprint join ignores the git revision",
        rom_part("git=abc main=1 sub=2") == rom_part("git=def main=1 sub=2")
        and rom_part("git=abc main=1") != rom_part("git=abc main=9"))
    arm("K14 NEGATIVE: a 41-char statement is named as too long, not typed",
        too_long([("x", 'IF 0 THEN PRINT"[1i]" ELSE PRINT"[1h]"', "stored")]) == ["x"]
        and too_long([("y", 'PRINT"[";ABS(-5);"]"', "direct")]) == [])
    arm("K13 no selected row writes a mark value itself",
        not [k for k, l, _ in select_rows() if any(m in l for m in MARK_LITERALS)])
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 2


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
    rows = select_rows(only)
    long_rows = too_long(rows)
    rows = [r for r in rows if r[0] not in long_rows]
    if long_rows:
        print(f"kwtime: {len(long_rows)} row(s) NOT TIMED -- a statement over "
              f"{MAX_TYPED} typed characters: {' '.join(long_rows)}")
    clash = [k for k, l, _ in rows if any(m in l for m in MARK_LITERALS)]
    if clash:
        print(f"kwtime: REFUSING -- row(s) {clash} write a mark value themselves")
        return 2
    fp_before = kw._rom_fingerprint()
    ref = measure(REF, rows)
    zb = measure(a.zb_machine, rows)
    fp_after = kw._rom_fingerprint()
    res = {}
    tally: dict = {}
    print(f"{'row':16} {'ref ms':>9} {'zb ms':>9} {'zb/ref':>7}  status")
    for (key, _l, _m), r, z in zip(rows, ref, zb):
        st = status(r, z)
        tally[st] = tally.get(st, 0) + 1
        ratio = z / r if r and z else None
        res[key] = {"ref": r, "zb": z, "ratio": ratio, "status": st}
        print(f"{key:16} {r * 1e3 if r else float('nan'):9.3f} "
              f"{z * 1e3 if z else float('nan'):9.3f} "
              f"{(f'{ratio:.2f}' if ratio else '-'):>7}  {st}")
    timed = sum(1 for r in ref if r is not None)
    print("\nkwtime: " + " · ".join(f"{k}={v}" for k, v in sorted(tally.items()))
          + f"  ({len(rows)} rows, bar {BAR:g}x)")
    if only is None and timed < REF_FLOOR:
        print(f"kwtime: APPARATUS FAILURE -- only {timed} row(s) timed on the "
              f"reference (floor {REF_FLOOR}); refusing to pin a degenerate run")
        return 2
    if fp_before != fp_after:
        print("kwtime: the ROMs CHANGED during the run -- NOT pinned")
        return 2
    if only is None:
        import time as _t
        os.makedirs(os.path.dirname(PIN), exist_ok=True)
        with open(PIN, "w", encoding="utf-8") as fh:
            json.dump({"written": _t.strftime("%Y-%m-%d %H:%M:%S"),
                       "rom_fingerprint": fp_after, "bar": BAR, "rows": res},
                      fh, indent=1, sort_keys=True)
        print(f"pin: {len(res)} timed row(s) -> {PIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
