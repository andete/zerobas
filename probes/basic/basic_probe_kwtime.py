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
sys.path.insert(0, os.path.join(_ROOT, "tools"))
import tier_table  # noqa: E402  -- stmt_subject: which keyword a row is ABOUT
import re  # noqa: E402

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


# ⏱ T5 = THE KEYWORD ALONE (Joost, 2026-09-24, option (c): "whole program for
# T2, keyword alone for T5"). Each row gets a TWIN in which every top-level
# statement that carries the row's keyword is replaced by a no-op assignment
# PADDED WITH SPACES TO THE SAME LENGTH -- equal length is what keeps
# `as_stored`'s packing, and therefore every line number the row names, intact.
# T5 = (zb row - zb twin) / (ref row - ref twin).
# ⚠️ For a FUNCTION (`ABS` inside `PRINT`) the carrying statement is the whole
# PRINT, so the reading includes that statement's own cost: it is the keyword's
# STATEMENT alone, and the sheet says so rather than claiming more.
# 🎯 The control that motivated it: `SCREEN2:SCREEN0` is 552 ms on the VG-8020 and
# 167 ms here, so the PAINT row reads 0.47 while PAINT alone measured 1.76.
NOISE = 0.0005            # 2x one interrupt's service time (~0.25 ms, measured)
_KWSET = None


def row_keyword(crunch, note):
    """The keyword a row is ABOUT, the way tier_table scores it -- a composite
    (`ON ERROR GOTO`) contributes its FIRST word, which is the token to find."""
    global _KWSET
    if _KWSET is None:
        _KWSET = set(tier_table.keywords())
    subj = tier_table.stmt_subject(crunch or "", _KWSET, kw.row_subject(note))
    return subj.split()[0] if subj else None


def split_stmts(line):
    """Top-level statements; a `:` inside a string literal is not a separator."""
    out, cur, in_str = [], [], False
    for ch in line:
        if ch == '"':
            in_str = not in_str
        if ch == ":" and not in_str:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def carries(stmt, word):
    """Does `stmt` contain the keyword as a TOKEN, outside string literals?
    `OR` must not match inside `COLOR`, nor `ON` inside `SCREEN0`'s neighbours."""
    bare = re.sub(r'"[^"]*("|$)', '""', stmt.upper())
    pat = r"(?<![A-Z])" + re.escape(word)
    if word[-1].isalpha():
        pat += r"(?![A-Z])"
    return re.search(pat, bare) is not None


def twin_bodies(line, word):
    """The row's PACKED body lines with every statement carrying the keyword
    DELETED -- or None when nothing carries it (a twin identical to the row
    measures nothing).

    🔴 DELETE, DO NOT REPLACE. The first cut swapped the statement for a padded
    `Z9=0` to keep `as_stored`'s packing, and that no-op was not one: CREATING a
    variable measured 3.0 ms on the VG-8020 and 6.8 ms here, so the twin carried
    extra work heavier on zerobas's side and `abs` read 0.38 alone (its PRINT is
    8.0 vs 8.6 ms). Working on the ALREADY-PACKED lines makes padding unnecessary:
    no line is re-packed, so every number the row names holds. A line left empty
    becomes `REM` -- an empty numbered line would DELETE the line."""
    if not word:
        return None
    out, hit = [], False
    for body in omsx_repl.as_stored(line):
        parts = split_stmts(body)
        keep = [p for p in parts if not carries(p, word)]
        hit = hit or len(keep) != len(parts)
        out.append(":".join(keep) if keep else "REM")
    return out if hit else None


def twin_line(line, word):
    """The twin as ONE line, for display and the selftest (None = no twin)."""
    b = twin_bodies(line, word)
    return None if b is None else ":".join(b)


def alone(r, z, rt, zt):
    """T5's reading: the keyword statement's own time, zb over ref -- or None when
    either side's difference is within interrupt noise or a twin did not run."""
    if None in (r, z, rt, zt):
        return None
    dr, dz = r - rt, z - zt
    if dr <= NOISE or dz <= NOISE:
        return None
    return dz / dr


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
        out.append((key, line, mode, row_keyword(_crunch, note)))
    return out


# 🔴 A TYPED LINE OVER 38 CHARACTERS IS NOT DELIVERED WHOLE. kwsweep's stored mode
# gets past a long single statement through the harness's TXTTAB fallback; a
# typed, explicitly numbered line has no such path, and one mangled delivery
# poisons the whole batch. Such rows are left out and NAMED, never dropped quietly.
MAX_TYPED = 38


def too_long(rows):
    return [r[0] for r in rows
            if any(len(l) > MAX_TYPED for l in case_lines(r[1]))]


def case_lines(line, pad=None, bodies=None):
    """The row as explicitly numbered lines, bracketed by the two marks.
    `bodies` (already packed) overrides `line` -- the twin's shape."""
    body = omsx_repl.as_stored(line) if bodies is None else bodies
    first = f"5 CLS:POKE&H{MARK_ADDR:04X},{START}"
    if pad:                                   # --negative: slow THIS side only
        first += ":" + pad
    lines = [first] + [f"{10 * (i + 1)} {b}" for i, b in enumerate(body)]
    lines.append(f"{10 * (len(body) + 1)} POKE&H{MARK_ADDR:04X},{END}")
    # 🔴 EVERY CASE OPENS WITH CTRL-STOP, THEN ITS OWN `NEW`. Measured: the twin
    # of `sprite_on` deletes `ON SPRITE GOSUB`/`SPRITE ON` and then waits forever
    # for a collision that can no longer fire -- and in a batched boot EVERY later
    # case was typed into that running program, so 113 twins came back empty,
    # PAINT's among them. A hang must cost its own reading and nothing else.
    # The harness's own inter-case reset is OFF (`reset=()`): it types BEFORE a
    # case's lines, i.e. into the buffer of whatever is still running.
    return [omsx_repl.BREAK_PREFIX, "NEW"] + lines + ["RUN"]


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


def measure(machine, rows, pad=None, twin=False):
    """Time `rows` in one batched boot. `twin=True` times each row's TWIN; a row
    with no twin gets None without being typed."""
    bods = [twin_bodies(r[1], r[3]) if twin else omsx_repl.as_stored(r[1])
            for r in rows]
    idx = [i for i, b in enumerate(bods) if b is not None]
    if not idx:
        return [None] * len(rows)
    specs = [("direct", case_lines(None, pad, bods[i])) for i in idx]
    so: dict = {}
    omsx_repl.run_cases(machine, specs, batch=True, reset=(),
                        capture="screen", boot=8.0,
                        sentinel=(MARK_ADDR, END), settle_out=so)
    marks = so.get("marks", {})
    out = [None] * len(rows)
    for j, i in enumerate(idx):
        out[i] = delta(marks.get(j, []))
    return out


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
    for (key, _l, _m, _w), r, z in zip(rows, ref, zb):
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
        ls[3].startswith("10 ") and any(l.startswith("20 ") for l in ls))
    arm("K22 every case opens with Ctrl-STOP then NEW -- a hung case cannot "
        "poison the next", ls[0] == omsx_repl.BREAK_PREFIX and ls[1] == "NEW")
    arm("K11 the start mark is line 5 and the end mark the last numbered line",
        ls[2].startswith("5 ") and "POKE&HE000,201" in ls[2]
        and f",{END}" in ls[-2] and ls[-1] == "RUN")
    arm("K12 the fingerprint join ignores the git revision",
        rom_part("git=abc main=1 sub=2") == rom_part("git=def main=1 sub=2")
        and rom_part("git=abc main=1") != rom_part("git=abc main=9"))
    arm("K14 NEGATIVE: a 41-char statement is named as too long, not typed",
        too_long([("x", 'IF 0 THEN PRINT"[1i]" ELSE PRINT"[1h]"', "stored")]) == ["x"]
        and too_long([("y", 'PRINT"[";ABS(-5);"]"', "direct")]) == [])
    arm("K13 no selected row writes a mark value itself",
        not [r[0] for r in select_rows() if any(m in r[1] for m in MARK_LITERALS)])
    tw = twin_line('SCREEN2:LINE(10,10)-(20,20),15,B:PAINT(15,15),15:SCREEN0', "PAINT")
    arm("K15 the twin DELETES only the keyword's statement and creates nothing",
        tw is not None and "PAINT" not in tw and "LINE(10,10)" in tw
        and "SCREEN0" in tw and "Z9" not in tw)
    arm("K16 NEGATIVE: a twin that removes nothing is None, not a copy of the row",
        twin_line('PRINT"[";ABS(-5);"]"', "SQR") is None)
    arm("K17 NEGATIVE: OR is not found inside COLOR, nor a keyword inside a string",
        not carries("COLOR 15", "OR") and not carries('PRINT"OR"', "OR")
        and carries("A=5 OR 3", "OR"))
    _g = 'A=0:GOSUB 20:PRINT"[G";A;"]":END:A=7:RETURN:REM ZZZZZZZZZZZZZZZZZZZZ'
    arm("K18 the twin keeps every line number (no re-pack): GOSUB 20 still lands",
        [l.split()[0] for l in case_lines(None, bodies=twin_bodies(_g, "GOSUB"))]
        == [l.split()[0] for l in case_lines(_g)])
    arm("K21 a line the deletion empties becomes REM, never an empty (deleting) line",
        twin_bodies("CLS", "CLS") == ["REM"])
    arm("K19 alone(): the keyword's own time is the DIFFERENCE, zb over ref",
        abs(alone(0.624, 0.294, 0.552, 0.167) - (0.127 / 0.072)) < 1e-9)
    arm("K20 NEGATIVE: a difference inside interrupt noise gives no reading",
        alone(0.010, 0.012, 0.0099, 0.0118) is None and alone(None, 1, 1, 1) is None)
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
    clash = [r[0] for r in rows if any(m in r[1] for m in MARK_LITERALS)]
    if clash:
        print(f"kwtime: REFUSING -- row(s) {clash} write a mark value themselves")
        return 2
    fp_before = kw._rom_fingerprint()
    ref = measure(REF, rows)
    zb = measure(a.zb_machine, rows)
    ref_t = measure(REF, rows, twin=True)
    zb_t = measure(a.zb_machine, rows, twin=True)
    fp_after = kw._rom_fingerprint()
    res = {}
    tally: dict = {}
    print(f"{'row':16} {'ref ms':>9} {'zb ms':>9} {'zb/ref':>7} {'alone':>6}  status")
    n_alone = 0
    for (key, _l, _m, word), r, z, rt, zt in zip(rows, ref, zb, ref_t, zb_t):
        st = status(r, z)
        tally[st] = tally.get(st, 0) + 1
        ratio = z / r if r and z else None
        al = alone(r, z, rt, zt)
        n_alone += al is not None
        res[key] = {"ref": r, "zb": z, "ratio": ratio, "status": st,
                    "word": word, "twin_ref": rt, "twin_zb": zt, "alone": al}
        print(f"{key:16} {r * 1e3 if r else float('nan'):9.3f} "
              f"{z * 1e3 if z else float('nan'):9.3f} "
              f"{(f'{ratio:.2f}' if ratio else '-'):>7} "
              f"{(f'{al:.2f}' if al else '~'):>6}  {st}")
    timed = sum(1 for r in ref if r is not None)
    print("\nkwtime: " + " · ".join(f"{k}={v}" for k, v in sorted(tally.items()))
          + f"  ({len(rows)} rows, bar {BAR:g}x; keyword-alone reading on {n_alone})")
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
