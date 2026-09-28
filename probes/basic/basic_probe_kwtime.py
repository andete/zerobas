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
# 💽 D-KWTDISK (2026-09-24): THE DISK ROWS ARE TIMED AGAINST THE CF-3300. The
# VG-8020 has no drive, so a disk verb has no time there at all; the CF-3300 is
# the reference kwsweep already scores those rows against, and it is the rule
# Joost ruled for the RAM rung -- *"prefer the vg8020"*, disk-only cells take
# the CF-3300. Its boot is ~6 s longer than the VG's (kwsweep's MACH_BOOT).
DISK_REF = "National_CF-3300"
DISK_REF_BOOT = 14.0
# 🖨 D-KWTRIG (2026-09-24): the rigs a row may carry ALONE and still be timed.
# kwtime reads RAM marks, never the artefact, so a rig only has to be PRESENT:
# the printer plugged, a blank tape in the deck. ⚠️ `tape` (CLOAD) is left out
# ON PURPOSE: a CLOAD replaces the running program with the one it loads, so
# the end mark can never fire -- it would read UNTIMEABLE by construction after
# a 90 s leader per case, twice. `log`/hold/plug rows are not here yet.
TIMEABLE_RIGS = {("disk",): "disk", ("printer",): "printer", ("tapew",): "tapew"}
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
# 🔴 AND A RELATIVE FLOOR, because the absolute one was calibrated on SHORT rows.
# Measured 2026-09-24 with the interrupt-synced start: whole rows agree batch vs
# alone within 0.2%, but a no-op `WIDTH` costs a few ms of an 800-2200 ms row, so
# its keyword-alone ratio is a ratio of two noise-sized differences (widthkw_c
# read 3.93 batched, 3.32 alone). A difference must clear 1% of ITS OWN ROW on
# each side -- 5x the measured row jitter -- or the reading is `~`.
NOISE_REL = 0.01
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


def twin_bodies(line, word, nth=None):
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
    # ⏱ A ROW MAY DECLARE WHICH OCCURRENCE IS TIMED: `TIMED:<n>` in its note
    # (Joost, 2026-09-24: WIDTH is *"a classic case of two very different effects
    # of one keyword ... both need a time measurement"*). A row that SETS UP its
    # state with the keyword and then EXERCISES it -- `WIDTH 36:WIDTH 37` --
    # declares the exercise, and only that statement is deleted.
    # 🔴 THE DEFAULT STAYS "EVERY CARRYING STATEMENT", AND "THE LAST" WAS TRIED
    # AND MEASURED WRONG: in `vdp_d` the last `VDP` statement is the RESTORE of
    # R1 after `VDP(1)=V AND 223` cleared the interrupt enable, so the twin left
    # zerobas with VDP interrupts OFF and 107 later zerobas twins came back empty.
    # Neither "first" nor "last" names the form in general; a row says so.
    bodies = omsx_repl.as_stored(line)
    split = [split_stmts(b) for b in bodies]
    hits = [(bi, pi) for bi, parts in enumerate(split)
            for pi, p in enumerate(parts) if carries(p, word)]
    if not hits:
        return None
    if nth is not None:
        if not 1 <= nth <= len(hits):
            return None
        hits = [hits[nth - 1]]
    drop = set(hits)
    out = []
    for bi, parts in enumerate(split):
        keep = [p for pi, p in enumerate(parts) if (bi, pi) not in drop]
        out.append(":".join(keep) if keep else "REM")
    return out


def twin_line(line, word, nth=None):
    """The twin as ONE line, for display and the selftest (None = no twin)."""
    b = twin_bodies(line, word, nth)
    return None if b is None else ":".join(b)


def alone(r, z, rt, zt):
    """T5's reading: the keyword statement's own time, zb over ref -- or None when
    either side's difference is within interrupt noise or a twin did not run."""
    if None in (r, z, rt, zt):
        return None
    dr, dz = r - rt, z - zt
    if dr <= max(NOISE, NOISE_REL * r) or dz <= max(NOISE, NOISE_REL * z):
        return None
    return dz / dr


SYNCVAR = "X7"                 # the interrupt-sync variable -- K26 keeps it unused
RESET = "SCREEN0:WIDTH37"       # the per-case starting state (see case_lines)
FORMS: dict = {}               # row key -> its kwsweep FORM (T5 is per form)
TIMED: dict = {}               # row key -> the declared timed occurrence, or None
GROUP: dict = {}               # row key -> "plain" or "disk" (D-KWTDISK)


def select_rows(only=None):
    """kwsweep's PLAIN rows that declare a FORM -- the rows T1 counts.

    Plain = no rig (printer/tape/hold/plug), not an editor (`PROGRAM:`) row,
    not a `RESPOND:` row: those need machinery this shape does not drive, and a
    keyword whose only rows are rigged simply has no T2 reading yet.
    💽 A row whose ONLY rig is the disk IS selected (D-KWTDISK) -- mounting a
    fresh image is all it needs -- and is timed in its own group against
    DISK_REF. A disk row with a SECOND rig (`lfiles`: disk + printer) is not."""
    out = []
    for key, _crunch, line, mode, note in kw.SWEEP:
        rigs = kw._row_rigs(note)
        if line is None or (rigs and rigs not in TIMEABLE_RIGS) \
                or kw.row_program(note) or not kw.row_form(note):
            continue
        if only and key not in only:
            continue
        GROUP[key] = TIMEABLE_RIGS[rigs] if rigs else "plain"
        out.append((key, line, mode, row_keyword(_crunch, note)))
        FORMS[key] = kw.row_form(note)
        RESP[key] = kw.row_respond(note)   # D-KWT2RESP: typed in the burst
        m = re.search(r"(?<!\S)TIMED:(\d+)(?!\S)", note)
        TIMED[key] = int(m.group(1)) if m else None
    return out


# 🔴 A TYPED LINE OVER 38 CHARACTERS IS NOT DELIVERED WHOLE. kwsweep's stored mode
# gets past a long single statement through the harness's TXTTAB fallback; a
# typed, explicitly numbered line has no such path, and one mangled delivery
# poisons the whole batch. Such rows are left out and NAMED, never dropped quietly.
MAX_TYPED = 38


def too_long(rows):
    return [r[0] for r in rows
            if any(len(l) > MAX_TYPED for l in case_lines(r[1], resp=RESP.get(r[0])))]


# ⌨️ D-KWT2TA (Joost 2026-09-28: lifting level-1 keywords is the priority). A row
# that ENDS, STOPS, LISTS, RENUMs... the run never reaches its end-mark line, and
# CURLIN is a different event per machine for those paths (DIRECT_RETURNERS). So
# its SECOND pass types `RUN` + CR + the END mark in ONE KEYBUF burst: the mark
# line waits in the type-ahead buffer and runs only when the prompt asks for input
# again -- right after the command finished -- on BOTH machines, through the same
# BIOS buffer. Symmetric by construction; RAM marks only; no ROM address observed.
# Measured (scratchpad/kwt2_typeahead_run.out): LIST of 30 lines 1304/1329 ms vs of
# 3 lines 188/337 ms, so the reading IS the command's work (LIST does not eat the
# waiting line); the fixed prompt round-trip is ~30 ms VG-8020 / ~79 ms here,
# included on both sides.
TA_TAIL = f"RUN\rPOKE&H{MARK_ADDR:04X},{END}"
# ⌨️ D-KWT2RESP: a `RESPOND:` row (INPUT at the console, CONT after a STOP) waits
# for typed input, which kwtime could not give it. Its burst carries the response
# lines BETWEEN `RUN` and the mark: INPUT takes its answer from the buffer, the
# program reaches its own end-mark line, and the trailing mark is only a backstop.
RESP: dict = {}


def ta_tail(resp=None):
    """The type-ahead burst: RUN, then any response lines, then the END mark."""
    if not resp:
        return TA_TAIL
    return "\r".join(["RUN", *resp, f"POKE&H{MARK_ADDR:04X},{END}"])


def case_lines(line, pad=None, bodies=None, typeahead=False, resp=None):
    """The row as explicitly numbered lines, bracketed by the two marks.
    `bodies` (already packed) overrides `line` -- the twin's shape.
    `typeahead` ends it with TA_TAIL instead of a plain `RUN` (D-KWT2TA)."""
    body = omsx_repl.as_stored(line) if bodies is None else bodies
    # ⏱ SYNC THE START TO THE INTERRUPT (D-KWT5FORM, 2026-09-24). The start mark
    # used to land at an arbitrary phase of the 50 Hz interrupt, so a timed
    # stretch held one interrupt service more or less by chance: measured, the
    # same rows read up to ~10% apart alone vs in a batch on their keyword-alone
    # difference. Lines 5-6 wait for TIME to tick, so line 7's mark fires just
    # after an interrupt on BOTH machines. `SYNCVAR` is a name no kwsweep row
    # uses -- K26 re-checks that every run, because the first choice, `Q8`, was
    # used by FIVE rows -- created BEFORE the mark so its cost is not timed.
    first = f"7 POKE&H{MARK_ADDR:04X},{START}"
    if pad:                                   # --negative: slow THIS side only
        first += ":" + pad
    lines = [f"5 CLS:{SYNCVAR}=TIME", f"6 IF TIME={SYNCVAR} THEN 6", first] + \
        [f"{10 * (i + 1)} {b}" for i, b in enumerate(body)]
    lines.append(f"{10 * (len(body) + 1)} POKE&H{MARK_ADDR:04X},{END}")
    # 🔴 EVERY CASE OPENS WITH CTRL-STOP, THEN ITS OWN `NEW`. Measured: the twin
    # of `sprite_on` deletes `ON SPRITE GOSUB`/`SPRITE ON` and then waits forever
    # for a collision that can no longer fire -- and in a batched boot EVERY later
    # case was typed into that running program, so 113 twins came back empty,
    # PAINT's among them. A hang must cost its own reading and nothing else.
    # The harness's own inter-case reset is OFF (`reset=()`): it types BEFORE a
    # case's lines, i.e. into the buffer of whatever is still running.
    # 🔴 AND EVERY CASE STARTS FROM ONE STATE (D-KWT5FORM, 2026-09-24): measured,
    # the SAME twin program read 831.5 ms in one run and 787.1 ms in the next,
    # the only difference a NEIGHBOUR's twin -- screen mode and width leak from
    # case to case, and `NEW` resets neither. `SCREEN0:WIDTH37` puts both machines
    # in the same mode and width before the start mark, whatever came before.
    tail = ta_tail(resp) if (typeahead or resp) else "RUN"
    return [omsx_repl.BREAK_PREFIX, "NEW", RESET] + lines + [tail]


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


CURLIN_HI = 0xF41D             # CURLIN's high byte: $FF = direct mode (D-CURLIN)


def curlin_end(marks, watch):
    """Emulated seconds from this case's START mark to the first CURLIN := $FFFF
    AFTER it (the program has ended and BASIC is back in direct mode), or None.

    ⏱ D-KWUNTIME (2026-09-24): the end signal for the rows that END before
    their own end mark. Both machines publish CURLIN now (D-CURLIN). ⚠️ `RUN`
    itself runs as a DIRECT line, so a $FFFF lands just BEFORE the start mark --
    only a write after it counts, and before the next case's START."""
    starts = [t for t, v in marks if v == START]
    if not starts:
        return None
    t0 = starts[0]
    nxt = starts[1] if len(starts) > 1 else float("inf")
    ends = [t for t, _v in watch if t0 < t < nxt]
    return (ends[0] - t0) if ends else None


def resolve(pair, bias):
    """One case's time: the END MARK when it fired, else CURLIN's end corrected
    by this machine's measured bias. -> (seconds or None, "mark"|"curlin"|None)."""
    mark, curl = pair
    if mark is not None:
        return mark, "mark"
    if curl is not None and bias is not None:
        return curl - bias, "curlin"
    return None, None


def machine_bias(pairs):
    """-> (median, min, max) of CURLIN-end minus MARK-end over the cases that
    have BOTH -- the time each machine takes from a program's end to publishing
    $FFFF. MEASURED ASYMMETRIC: `abs` read +2.48 ms on the VG-8020 and +0.25 ms
    here, so an uncorrected CURLIN time would flatter zerobas."""
    d = sorted(c - m for m, c in pairs if m is not None and c is not None)
    if not d:
        return None, None, None
    return d[len(d) // 2], d[0], d[-1]


# 🔴 CURLIN'S END IS ONLY THE SAME EVENT ON BOTH MACHINES FOR AN `END` PATH.
# Measured 2026-09-24: rows that end in a Break or an error MESSAGE (stopkw 0.26,
# attrkw 0.29, onkw_b 0.28) or in a statement that returns to direct mode ITSELF
# (listkw 239x) read ratios no program can have -- the reference publishes $FFFF
# at a different point in those paths than zerobas does. So CURLIN is accepted
# only for a row that has an END statement, names none of these, and whose
# screen shows no "... in <line>" message on either side.
DIRECT_RETURNERS = ("LIST", "LLIST", "NEW", "STOP", "CONT", "RUN")
ERR_LINE = re.compile(r"\bin \d+\b")


def curlin_ok(line, caps):
    """May this row be timed from CURLIN? (see DIRECT_RETURNERS)"""
    up = re.sub(r'"[^"]*("|$)', '""', line.upper())
    words = set(re.findall(r"[A-Z]+", up))
    if "END" not in words or words & set(DIRECT_RETURNERS):
        return False
    return not any(c and ERR_LINE.search(c) for c in caps)


def group_kwargs(group, machine):
    """-> the extra run_cases kwargs a group needs on `machine`, built FRESH per
    call: the disk rig hands out a private copy of the test image each time, so
    the plain run and its twin both start from the image as shipped -- a row
    that KILLs or NAMEs a file cannot change what the next measurement sees."""
    if group == "plain":
        return {}
    extra = kw._rig_kwargs((group,))
    # the artefact is not read here -- only the marks -- so the rig's own
    # capture override and tape path are dropped; its `batch` is KEPT: the
    # tape-write rig needs a boot per case (a fresh tape each time).
    extra.pop("capture", None)
    extra.pop("_tape_path", None)
    if machine == DISK_REF:
        extra["boot"] = DISK_REF_BOOT
    return extra


def calibrate(machine, extra=None):
    """-> this machine's END-path bias: from the end mark to CURLIN := $FFFF when
    the program then runs `END`. LIVE every run, never a constant -- measured
    2026-09-24 at +0.40 ms (ref) / +0.30 ms (zb) over falling off the end."""
    lines = ([omsx_repl.BREAK_PREFIX, "NEW", RESET,
              f"5 CLS:{SYNCVAR}=TIME", f"6 IF TIME={SYNCVAR} THEN 6",
              f"7 POKE&H{MARK_ADDR:04X},{START}", "10 A=1",
              f"20 POKE&H{MARK_ADDR:04X},{END}:END", "RUN"])
    so: dict = {}
    rk = dict(batch=True, capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
              settle_out=so, watch_values=((CURLIN_HI, 0xFF),))
    rk.update(extra or {})
    omsx_repl.run_cases(machine, [("direct", lines)], reset=(), **rk)
    mk = so.get("marks", {}).get(0, [])
    w = [t for t, _v in so.get("watch", {}).get(0, {}).get(CURLIN_HI, [])]
    te = [t for t, v in mk if v == END]
    tf = [t for t in w if te and t > te[0]]
    return (tf[0] - te[0]) if te and tf else None


def measure(machine, rows, pad=None, twin=False, caps_out=None, extra=None,
            typeahead=False):
    """Time `rows` in one batched boot -> [(mark_seconds, curlin_seconds)].
    `twin=True` times each row's TWIN; a row with no twin gets (None, None)
    without being typed."""
    bods = [twin_bodies(r[1], r[3], TIMED.get(r[0])) if twin
            else omsx_repl.as_stored(r[1])
            for r in rows]
    idx = [i for i, b in enumerate(bods) if b is not None]
    if not idx:
        return [(None, None)] * len(rows)
    specs = [("direct", case_lines(None, pad, bods[i], typeahead, RESP.get(rows[i][0])))
             for i in idx]
    so: dict = {}
    rk = dict(batch=True, capture="screen", boot=8.0, sentinel=(MARK_ADDR, END),
              settle_out=so, watch_values=((CURLIN_HI, 0xFF),))
    rk.update(extra or {})
    caps = omsx_repl.run_cases(machine, specs, reset=(), **rk)
    if caps_out is not None:
        caps_out[:] = [None] * len(rows)
        for j, i in enumerate(idx):
            caps_out[i] = caps[j] if caps else None
    marks = so.get("marks", {})
    watch = so.get("watch", {})
    out = [(None, None)] * len(rows)
    for j, i in enumerate(idx):
        mk = marks.get(j, [])
        out[i] = (delta(mk), curlin_end(mk, watch.get(j, {}).get(CURLIN_HI, [])))
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
    ref = [p[0] for p in measure(REF, rows)]
    zb = [p[0] for p in measure(zb_machine, rows, pad="FOR Q9=1 TO 200:NEXT")]
    # 💽 D-KWTDISK: THE DISK GROUP GETS ITS OWN ARM, because it is a different
    # route -- another reference machine, a mounted image, its own kwargs -- and
    # a route that silently timed the wrong machine or nothing would still print
    # plausible ratios. `lof` is the shortest disk row (~1.2 s on the CF-3300),
    # so its pad is proportionate: ~14 s of delay loop puts zerobas's side near
    # 12x, where 200 iterations would not move a one-second row at all.
    # ⚠️ NOT MORE: 6000 iterations (~29 s) ran past the disk rig's 20 s capture
    # window and read HANG -- caught, but not the SLOW this arm asserts, and a
    # HANG would pass for a different reason.
    # 🔴 THE PAD IS PRICED IN ITERATIONS, SO IT MOVES WHEN NEXT DOES. It was
    # 3000 at ~4.9 ms each; D-FORFLOAT (2026-09-27) made a default-type loop
    # float arithmetic, ~7 ms a pass (`nextkw` 1.64x -> 2.37x the VG-8020), and
    # 3000 then read HANG. 2000 is the same ~14 s.
    drow = select_rows({"lof"})
    if len(drow) != 1 or GROUP.get("lof") != "disk":
        print("kwtime --negative: expected the disk control row `lof`")
        return 2
    rows = rows + drow
    ref += [p[0] for p in measure(DISK_REF, drow,
                                  extra=group_kwargs("disk", DISK_REF))]
    zb += [p[0] for p in measure(zb_machine, drow, pad="FOR Q9=1 TO 2000:NEXT",
                                 extra=group_kwargs("disk", zb_machine))]
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
    ta_lines = case_lines("LIST", typeahead=True)
    arm("K40 the type-ahead case ends RUN + CR + the END mark, in ONE line",
        ta_lines[-1] == f"RUN\rPOKE&H{MARK_ADDR:04X},{END}")
    arm("K41 NEGATIVE: without typeahead the case ends in a plain RUN",
        case_lines("LIST")[-1] == "RUN")
    arm("K43 a RESPOND row's burst carries the response between RUN and the mark",
        ta_tail(["HELLO"]) == f"RUN\rHELLO\rPOKE&H{MARK_ADDR:04X},{END}"
        and case_lines("INPUT A$", resp=["HELLO"])[-1].startswith("RUN\rHELLO\r"))
    arm("K44 NEGATIVE: a row with no response keeps the plain burst",
        ta_tail(None) == TA_TAIL)
    arm("K42 the type-ahead burst fits one KEYBUF injection",
        len(ta_lines[-1]) <= omsx_repl.MAX_DIRECT)
    ls = case_lines('A=0:GOSUB 20:PRINT"[G";A;"]":END:A=7:RETURN')
    arm("K10 the row keeps its own 10/20/30 numbering (GOSUB 20 still lands)",
        ls[6].startswith("10 ") and any(l.startswith("20 ") for l in ls))
    arm("K22 every case opens with Ctrl-STOP then NEW -- a hung case cannot "
        "poison the next", ls[0] == omsx_repl.BREAK_PREFIX and ls[1] == "NEW"
        and ls[2] == RESET)
    arm("K11 the start mark is line 5 and the end mark the last numbered line",
        ls[5].startswith("7 ") and "POKE&HE000,201" in ls[5]
        and ls[4] == f"6 IF TIME={SYNCVAR} THEN 6"
        and f",{END}" in ls[-2] and ls[-1] == "RUN")
    arm("K12 the fingerprint join ignores the git revision",
        rom_part("git=abc main=1 sub=2") == rom_part("git=def main=1 sub=2")
        and rom_part("git=abc main=1") != rom_part("git=abc main=9"))
    arm("K14 NEGATIVE: a 41-char statement is named as too long, not typed",
        too_long([("x", 'IF 0 THEN PRINT"[1i]" ELSE PRINT"[1h]"', "stored")]) == ["x"]
        and too_long([("y", 'PRINT"[";ABS(-5);"]"', "direct")]) == [])
    _used = [k for k, _c, l, _m, _n in kw.SWEEP
             if l and re.search(r"(?<![A-Z0-9])" + SYNCVAR, l.upper())]
    arm(f"K26 NEGATIVE: no kwsweep row uses the sync variable {SYNCVAR} "
        "(the first choice, Q8, was used by five)", not _used)
    arm("K28 a row that ENDS early is timed from CURLIN, minus the machine's bias",
        resolve((None, 0.0158), 0.0025) == (0.0158 - 0.0025, "curlin"))
    arm("K29 NEGATIVE: the end mark wins when it fired -- CURLIN is only the fallback",
        resolve((0.0094, 0.0119), 0.0025) == (0.0094, "mark"))
    arm("K30 NEGATIVE: a $FFFF BEFORE the start mark (RUN is a direct line) is ignored",
        curlin_end([(1.0, START)], [(0.9, 255), (1.2, 255)]) is not None
        and abs(curlin_end([(1.0, START)], [(0.9, 255), (1.2, 255)]) - 0.2) < 1e-9)
    arm("K31 the bias is the MEDIAN over cases with both signals, with its spread",
        machine_bias([(1.0, 1.002), (2.0, 2.003), (3.0, 3.0025), (None, 5.0)])[0]
        == machine_bias([(1.0, 1.002), (2.0, 2.003), (3.0, 3.0025)])[0])
    arm("K32 NEGATIVE: no case with both signals -> no bias, so no CURLIN time",
        resolve((None, 0.5), machine_bias([(None, 0.5)])[0]) == (None, None))
    arm("K33 an END-terminated row may use CURLIN",
        curlin_ok('A=0:GOSUB 20:PRINT"[G";A;"]":END:A=7:RETURN', ("[G 7]", "[G 7]")))
    arm("K34 NEGATIVE: LIST / STOP / NEW end their own way -- never CURLIN",
        not curlin_ok('PRINT"[A]":LIST', ("", "")) and not curlin_ok('A=1:STOP:END', ("", ""))
        and not curlin_ok('NEW:END', ("", "")))
    arm("K35 NEGATIVE: an error MESSAGE on either screen disqualifies the row",
        not curlin_ok('ERROR 7:END', ("Out of memory in 10", "")))
    arm("K36 NEGATIVE: END inside a string literal is not an END statement",
        not curlin_ok('PRINT"END"', ("", "")))
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
    arm("K23 a declared TIMED:2 deletes only the exercise -- the setup WIDTH stays",
        twin_line('WIDTH 36:WIDTH 37:PRINT"[W"', "WIDTH", 2) == 'WIDTH 36:PRINT"[W"')
    arm("K24 NEGATIVE: with no declaration EVERY carrying statement goes -- a "
        "restore is never the one left out (vdp_d)",
        "VDP" not in twin_line('V=VDP(1):VDP(1)=V AND 223:A=1:VDP(1)=V', "VDP")
        and "A=1" in twin_line('V=VDP(1):VDP(1)=V AND 223:A=1:VDP(1)=V', "VDP"))
    arm("K25 NEGATIVE: a TIMED:n past the last occurrence gives no twin, not a guess",
        twin_line('WIDTH 37:PRINT"[W"', "WIDTH", 3) is None)
    arm("K21 a line the deletion empties becomes REM, never an empty (deleting) line",
        twin_bodies("CLS", "CLS") == ["REM"])
    arm("K19 alone(): the keyword's own time is the DIFFERENCE, zb over ref",
        abs(alone(0.624, 0.294, 0.552, 0.167) - (0.127 / 0.072)) < 1e-9)
    arm("K27 NEGATIVE: a no-op's few ms on a LONG row is below the relative floor "
        "(widthkw_c: 2 ms of 800 ms) -> no reading",
        alone(0.800, 2.269, 0.798, 2.266) is None)
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
    res = {}
    tally: dict = {}
    n_alone = 0
    n_curlin = 0
    n_ta = [0]
    timed = 0
    biases = {}
    print(f"{'row':16} {'ref ms':>9} {'zb ms':>9} {'zb/ref':>7} {'alone':>6}  status")
    for group, refm in (("plain", REF), ("disk", DISK_REF),
                        ("printer", REF), ("tapew", REF)):
        grows = [r for r in rows if GROUP[r[0]] == group]
        if not grows:
            continue
        rcap, zcap = [], []
        ref = measure(refm, grows, caps_out=rcap,
                      extra=group_kwargs(group, refm))
        zb = measure(a.zb_machine, grows, caps_out=zcap,
                     extra=group_kwargs(group, a.zb_machine))
        ref_t = measure(refm, grows, twin=True,
                        extra=group_kwargs(group, refm))
        zb_t = measure(a.zb_machine, grows, twin=True,
                       extra=group_kwargs(group, a.zb_machine))
        rfall, zfall = machine_bias(ref), machine_bias(zb)
        rend = calibrate(refm, group_kwargs(group, refm))
        zend = calibrate(a.zb_machine, group_kwargs(group, a.zb_machine))
        biases[group] = {"ref_machine": refm,
                         "ref": {"fall_off": rfall, "end_path": rend},
                         "zb": {"fall_off": zfall, "end_path": zend}}
        for side, b, e in (("ref", rfall, rend), ("zb", zfall, zend)):
            print(f"kwtime: [{group}] {side} CURLIN bias -- fall-off "
                  + ("none" if b[0] is None else
                     f"{b[0] * 1e3:.3f} ms (spread {b[1] * 1e3:.3f}..{b[2] * 1e3:.3f})")
                  + " · END path " + ("none" if e is None else f"{e * 1e3:.3f} ms"))
        rb, zbb = (rend,), (zend,)
        for (key, _l, _m, word), rp, zp, rtp, ztp, rc_, zc_ in zip(
                grows, ref, zb, ref_t, zb_t, rcap, zcap):
            if not curlin_ok(_l, (rc_, zc_)):
                # CURLIN is not the same event here (see DIRECT_RETURNERS)
                rp, zp, rtp, ztp = ((p[0], None) for p in (rp, zp, rtp, ztp))
            r, rv = resolve(rp, rb[0])
            z, zv = resolve(zp, zbb[0])
            rt, _ = resolve(rtp, rb[0])
            zt, _ = resolve(ztp, zbb[0])
            if rv and zv and rv != zv:
                # one side reached its end mark and the other only ended: the two
                # machines took DIFFERENT PATHS through the same program -- a
                # behaviour difference, never a timing
                st, r, z, rt, zt = "PATH-DIFFERS", None, None, None, None
            else:
                st = status(r, z)
                n_curlin += rv == "curlin" and st == "OK"
            tally[st] = tally.get(st, 0) + 1
            ratio = z / r if r and z else None
            al = alone(r, z, rt, zt)
            n_alone += al is not None
            res[key] = {"ref": r, "zb": z, "ratio": ratio, "status": st,
                        "via": rv if rv == zv else None,
                        "word": word, "form": FORMS.get(key),
                        "twin_ref": rt, "twin_zb": zt, "alone": al,
                        "ref_machine": refm}
            print(f"{key:16} {r * 1e3 if r else float('nan'):9.3f} "
                  f"{z * 1e3 if z else float('nan'):9.3f} "
                  f"{(f'{ratio:.2f}' if ratio else '-'):>7} "
                  f"{(f'{al:.2f}' if al else '~'):>6}  {st}"
                  + ("" if group == "plain" else f"  [{group}: {refm}]"))
        timed += sum(1 for p in ref if p[0] is not None)
        # --- D-KWT2TA pass 2: the rows NEITHER side could end, re-timed by a
        # type-ahead end mark (see TA_TAIL). Marks only -- never CURLIN.
        ta = [r for r in grows if res.get(r[0], {}).get("status") == "UNTIMEABLE"]
        if ta:
            tr = measure(refm, ta, extra=group_kwargs(group, refm), typeahead=True)
            tz = measure(a.zb_machine, ta, extra=group_kwargs(group, a.zb_machine),
                         typeahead=True)
            for (key, _l, _m, word), rp, zp in zip(ta, tr, tz):
                r, z = rp[0], zp[0]
                st = status(r, z)
                tally["UNTIMEABLE"] -= 1
                tally[st] = tally.get(st, 0) + 1
                ratio = z / r if r and z else None
                res[key].update({"ref": r, "zb": z, "ratio": ratio, "status": st,
                                 "via": "typeahead" if st != "UNTIMEABLE" else None})
                print(f"{key:16} {r * 1e3 if r else float('nan'):9.3f} "
                      f"{z * 1e3 if z else float('nan'):9.3f} "
                      f"{(f'{ratio:.2f}' if ratio else '-'):>7} {'~':>6}  {st}"
                      "  [type-ahead end]")
                n_ta[0] += st == "OK"
    fp_after = kw._rom_fingerprint()
    print("\nkwtime: " + " · ".join(f"{k}={v}" for k, v in sorted(tally.items()))
          + f"  ({len(rows)} rows, bar {BAR:g}x; keyword-alone reading on {n_alone};"
          f" {n_curlin} timed via CURLIN, {n_ta[0]} via a type-ahead end)")
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
                       "rom_fingerprint": fp_after, "bar": BAR, "rows": res,
                       "curlin_bias": biases},
                      fh, indent=1, sort_keys=True)
        print(f"pin: {len(res)} timed row(s) -> {PIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
