#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""System-variable SWEEP — the MSX work-area denominator ($F380..$FFFE).

WHY THIS EXISTS
===============
zerobas keeps the last error code at $E1C5 ("own choice -- just-freed RAM",
basic/sysvars.inc:847) and neither reads nor writes MSX's ERRFLG at $F414. That
was found 2026-08-01 BY ACCIDENT, while asking an unrelated question about
clearing ERR between probe cases:

                                vg8020  cf3300   zb
  POKE&HF414,0  then PRINT ERR      0       0     8    (no effect on zb)
  PEEK(&HF414)  after an error      8       8     0

$F414 appears NOWHERE in the repo -- the standard address was never considered,
and never rejected. That is not the finding. The finding is that there was no
LIST against which the question could have been asked, exactly as there was none
for the keyword surface until 162 reserved words became `make kwsweep`.

This probe is that list. Spec: docs/spec-basic-sysvar-denominator.md.

⚠️ THAT ROW IS NOW HISTORY: ERRFLG LIVES AT $F414. D-REHOME (2026-08-01,
docs/sysvar-rehoming-decisions.md) honoured it along with ERRLIN, ONELIN, ONEFLG
and DEFTBL, at zero ROM cost. The paragraph above is kept because it is why this
probe exists and because the -- now failing -- shape it describes is exactly what
the probe must keep being able to find. C-REPRO below still pins $F414 under
s1-err with refs=08/zb=00 and IS EXPECTED TO FAIL against a build that honours
it; see its own note. What the sweep measures did not change: it is still "does
a READ of that address return the same value", still on 279 named entries.

THE RE-HOMING TABLE (docs/spec-basic-sysvar-rehoming.md)
=======================================================
The census answers "is the published address honoured". It CANNOT answer "is the
published variable the SAME VARIABLE as the one zerobas keeps privately", because
every zerobas private cell is BELOW the swept span. PRIV_SEGS closes that: the
published and the private cell are read by ONE instrument in ONE capture. Four
PAIRED stimulus states (s6..s13) make each reading a DELTA rather than a value
comparison -- which is what turns a name match into a semantics test.

SCOPE (spec §2, signed off): "does a READ of that address return the same value".
NOT "does zerobas write what the reference writes" (unobservable except through
the read) and NOT "does zerobas depend on it internally" (a question about this
repo's own memory map, not a fidelity question). ⚠️ The cost is stated, not
hidden: a variable zerobas maintains CORRECTLY AT A DIFFERENT ADDRESS is
indistinguishable here from one it does not maintain at all. ERRFLG is exactly
that case, and what this probe reports -- a divergence at $F414 -- is what a
PROGRAM sees, which is the thing fidelity turns on.

THE INSTRUMENT, AND WHY IT IS NOT `PEEK`
========================================
omsx_repl's ("mem_abs", ...) capture lowers to one openMSX `debug read_block
memory`, so the WHOLE work area comes back in ONE capture per case with no BASIC
payload delivered for the read at all -- no tokeniser, no 38-char KEYBUF budget,
no display-width ceiling, no undeliverable characters. The `}` fake (a stable,
BOTH-references-agreeing `<CA> X{5}` from a payload containing neither brace)
cannot happen to a read_block.

🔴 But that makes the instrument a different one from the scope, so the gap is
PINNED, not assumed -- C-INSTR below reads the same addresses BOTH ways, and the
run is void if they disagree.

WHAT MAKES A VERDICT MEAN SOMETHING
===================================
Three of the six verdict classes exist only because a naive sweep would count
them as successes:

  VOLATILE   the byte differs between the two repeats of the SAME side. JIFFY,
             the keyboard scan state, the RND seed and the cursor-blink counters
             move with no stimulus at all, and one run cannot tell such a byte
             apart from a divergence. EACH SIDE IS ITS OWN CONTROL here -- this
             is why --repeat 2 is not optional.
  NO-ORACLE  stable on both references, but vg8020 != cf3300. The two are
             structurally different machines (the CF-3300 has a disk ROM that
             claims work-area RAM and hooks), so this bucket is large and
             LEGITIMATELY so. It means "not measurable by this method", which is
             NOT the same statement as "not required".
  INERT      the references do not move the byte under this stimulus, so an
             agreement here is agreement for the WRONG REASON -- a machine that
             never touches a byte agrees with one that does. `PRINT TAB(99999)`
             raised ERR 6 on both sides while the feature was ABSENT; a byte
             reading 00 everywhere is the same shape. INERT bytes are EXCLUDED
             from the honoured tally.

and the three that carry information:

  HONOURED   the references MOVE it under the stimulus and zerobas moves it the
             same way, from the same baseline.
  DIVERGE    the references move it and zerobas does not, or moves it
             differently.  <- the ERRFLG class
  EXTRA      zerobas moves it and the references do not -- zerobas scribbling in
             the published work area where the reference leaves it alone.

Every stimulus verdict is a DELTA against the s0-boot baseline ON THE SAME SIDE,
never an absolute value: a value like 0 means nothing without a row pinning what
"unset" looks like.

THE TWO SELF-CONTROLS
=====================
  C-INSTR  a handful of addresses read BOTH through PEEK from BASIC and through
           read_block, on all three sides, must agree -- and one of them is
           $F414 in the ERROR state, so the instrument is pinned on the very
           byte the finding turns on. Failure voids the run.
  C-REPRO  the sweep must INDEPENDENTLY re-find the filed $F414 row under
           s1-err: DIVERGE, refs 08, zb 00, from the same C-BIOS table as every
           other entry and with no special handling. A sweep that reports
           nothing is indistinguishable from a sweep that measures nothing; if
           C-REPRO does not fire, THE APPARATUS IS BROKEN, not the finding.

THE ECHO GUARD IS LOAD-BEARING IN A NEW WAY HERE
================================================
🔴 A memory dump cannot tell "the byte did not move" apart from "the stimulus
never arrived". A stimulus line that fails to deliver produces a capture
identical to the baseline on EVERY side -- a perfect, silent, three-way
agreement from a case that never ran, and it fails TOWARD "pass". So every
stimulus state is also run as a SCREEN pass, on every side INCLUDING zerobas,
and must show its own evidence (s1-err: an Undefined-line-number error;
s2-noerr: a clean prompt and no error). A state whose delivery cannot be
verified on a side yields NO READING on that side.

DENOMINATOR SOURCE (a GENERATOR ONLY -- every verdict comes from measurement)
============================================================================
~/projects/cbios/src/systemvars.asm from the pinned repack checkout
(cbios-repack/README.md, tag v0.29-3-gb5ad9cb). docs/allowed-sources.md:121
rates C-BIOS source B / Conditional, usable "for facts (published sysvar
addresses / memory map) only" -- an address table is that fact and nothing else.
Corroborating source of the same facts: the MSX Technical Data Book ch. 2
work-area table (allowed-sources.md:108). No reference-ROM disassembly on either
side. If C-BIOS names an address the references do not honour, THE REFERENCES
WIN and the report says so.

⚠️ The list is not the span. The sweep reads every byte of $F380..$FFFE, not the
279 named ones; names are an interpretation layer applied afterwards, so a
divergent byte with no name survives instead of being thrown away.

USAGE
    python3 probes/basic/basic_probe_sysvarsweep.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK
    ... --only s0-boot,s1-err       # a subset, by state key
    ... --repeat 2                  # DEFAULT and mandatory (see VOLATILE)
    ... --named-only                # report only the C-BIOS-named entries
"""
from __future__ import annotations
import argparse, os, re, shutil, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

# --- the swept span ----------------------------------------------------------
# $F380 is where the published MSX work area starts; C-BIOS's own table runs to
# $FFFA.
# ⚠️ $FFFF IS DELIBERATELY EXCLUDED, and not for tidiness: on a machine with an
# EXPANDED slot it is the secondary-slot-select register, not RAM. zerobas's
# repack machine expands slot 3 (zerobas-disk in 3-1, zerobas-sub in 3-2) and
# the VG-8020 does not, so including it would manufacture a guaranteed
# three-way divergence out of a hardware difference that is not a behaviour --
# the same shape as the link word basic_probe_lnblank.py:60 has to drop.
WORK_LO, WORK_HI = 0xF380, 0xFFFE
WORK_LEN = WORK_HI - WORK_LO + 1

SRC_DSK = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "disk", "test720.dsk")
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
CBIOS_SRC = os.path.expanduser(
    os.environ.get("CBIOS", "~/projects/cbios")) + "/src/systemvars.asm"

# side -> how to drive it. Lifted from basic_probe_lnblank.py:88 (same three
# sides, same cadences; the CF-3300's 4.5 s step is not a guess -- D-LOF measured
# it EATING keystrokes at shorter ones).
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5, diska=None),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5, diska=SRC_DSK),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5, diska=None),
}
REF_SIDES = ("vg8020", "cf3300")
ALL_SIDES = ("vg8020", "cf3300", "zb")   # narrowed by --sides (see main)

# --- the RE-HOMING class: published name, private address ---------------------
# (name, published addr, size, zerobas addr) -- docs/spec-basic-sysvar-
# rehoming.md §1. ERRFLG/ERRLIN were spelled ERRCODE/ERRLINE on the zerobas side
# until D-REHOME, which is exactly why name_collisions() could not see them: it
# matches on the NAME, so the pair that STARTED this whole item was invisible to
# the layer that found the other eight. They are still listed here BY HAND, and
# the hand-written list is what stays honest if a future variable is re-homed
# under yet another spelling.
# ✅ D-REHOME (2026-08-01) honoured five of the ten, so for those the "zerobas
# address" IS the published one and the row becomes a REGRESSION check: zerobas
# must keep tracking the reference at that cell. The five it did not honour keep
# their private address and their recorded reason
# (docs/sysvar-rehoming-decisions.md §3).
REHOMED = [
    ("VALTYP", 0xF663,  1, 0xE0C8, "REJECT-UNOBSERVABLE"),
    ("ERRFLG", 0xF414,  1, 0xF414, "HONOURED"),
    ("FRETOP", 0xF69B,  2, 0xE268, "REJECT-GROUP"),
    ("SAVTXT", 0xF6AF,  2, 0xE1CF, "REJECT-UNOBSERVABLE"),
    ("SAVSTK", 0xF6B1,  2, 0xE1C3, "DEFER"),
    ("ERRLIN", 0xF6B3,  2, 0xF6B3, "HONOURED"),
    ("ONELIN", 0xF6B9,  2, 0xF6B9, "HONOURED"),
    ("ONEFLG", 0xF6BB,  1, 0xF6BB, "HONOURED"),
    ("ARYTAB", 0xF6C4,  2, 0xE1C0, "REJECT-GROUP"),
    ("DEFTBL", 0xF6CA, 26, 0xF6CA, "HONOURED"),
    # ✅ D-DOTLINE (2026-08-02) — `DOT`, the line `.` names in LIST/DELETE.
    # 🎯 THE FIRST ENTRY HERE THAT WAS NEVER RE-HOMED, because it was never
    # anywhere else: the cell did not exist until this slice, so claiming the
    # published address cost ZERO ROM bytes and no VACATED twin. Every other row
    # above records a decision about a variable zerobas had already placed.
    # PUB-FREE was measured BEFORE the claim: zerobas' byte at $F6B5 read 0 in
    # all 24 states of the `clp` battery (basic_probe_lnblank.py) at HEAD
    # 40647bd, so nothing — zerobas or C-BIOS — held it.
    # ⚠️ This row is a REGRESSION check like the other four HONOURED ones, and
    # the SEMANTICS behind it live in the `clp` battery, not here: this sweep
    # asks "does the byte move with the reference", the `clp` rows ask "is the
    # byte what `.` RESOLVES", and only the pair is evidence. See
    # docs/spec-basic-dotline.md §3.
    ("DOT",    0xF6B5,  2, 0xF6B5, "HONOURED"),
]

# 🆕 C-VACATED. The cells the honoured five MOVED OUT OF. They are ordinary
# unused RAM now, and they must GO QUIET: a leftover writer at an old address is
# the classic half-completed relocation, and it is invisible to every other check
# here -- the published cell would look perfectly honoured while a stale store
# kept scribbling somewhere nobody reads. Captured and asserted, not assumed.
VACATED = [("ERRCODE", 0xE1C5, 1), ("ERRLINE", 0xE1C6, 2),
           ("ONELIN'", 0xE1C8, 2), ("ONEFLG'", 0xE1CA, 1),
           ("DEFTBL'", 0xF153, 26)]


def _merge_segs(spans, gap=16):
    """[(addr,len)] -> merged, sorted segments. Adjacent cells are coalesced so
    the capture is a handful of `debug read_block`s rather than one per cell."""
    out = []
    for a, ln in sorted(spans):
        if out and a - (out[-1][0] + out[-1][1]) <= gap:
            end = max(out[-1][0] + out[-1][1], a + ln)
            out[-1] = (out[-1][0], end - out[-1][0])
        else:
            out.append((a, ln))
    return out


# 🔴 THE EXISTING SWEEP CANNOT SEE ZEROBAS' SIDE OF THE RE-HOMING, AND THAT IS
# NOT A DETAIL. It reads $F380..$FFFE; EVERY zerobas private cell above is BELOW
# that span ($E0C8, $E1C0.., $E268, $F153). So the sweep can say "the published
# address is not honoured" and cannot say "and here is the same value, 1440 bytes
# lower" -- which is the difference between a divergence and a RE-HOMING, i.e.
# between a defect and a placement decision. These segments close that gap, and
# they are read by the SAME instrument in the SAME capture, so the published and
# the private cell are sampled at one emulated instant on each side.
# ⚠️ ONLY cells OUTSIDE the swept span belong here. Once D-REHOME honoured five
# addresses, their "private" address became a work-area one already covered by
# the main capture -- and _idx resolves those through the work span, so a segment
# for them would be read twice and indexed never. Filtering here keeps the
# capture honest rather than relying on _idx's ordering to paper over it.
PRIV_SEGS = _merge_segs(
    [(a, n) for a, n in
     [(z, n) for _s, _p, n, z, _st in REHOMED] + [(a, n) for _s, a, n in VACATED]
     if not (WORK_LO <= a <= WORK_HI)])
PRIV_LEN = sum(ln for _a, ln in PRIV_SEGS)
CAP_SEGS = [(WORK_LO, WORK_LEN)] + PRIV_SEGS


def _idx(addr):
    """Byte index of `addr` inside one capture (work span, then PRIV_SEGS)."""
    if WORK_LO <= addr <= WORK_HI:
        return addr - WORK_LO
    off = WORK_LEN
    for a, ln in PRIV_SEGS:
        if a <= addr < a + ln:
            return off + (addr - a)
        off += ln
    raise KeyError(f"${addr:04X} is in no captured segment")

# --- the common prefix -------------------------------------------------------
# ⚠️ EVERY STATE ON EVERY SIDE STARTS WITH ONE BARE CR, INCLUDING THE BASELINE.
# The CF-3300 needs it to answer the boot date prompt; the other two do not need
# it at all. Giving it to only the machine that needs it would mean the baseline
# had a line editor run on one side and not the others, and every byte the
# editor touches would then read as a reference disagreement. One CR everywhere
# is the closest the three machines get to the same starting state -- and where
# it still is not (the date prompt scrolls the CF-3300's screen and the others'
# it does not), the difference lands in NO-ORACLE, which is the conservative
# direction.
PREFIX = [""]

# Emulated seconds added to the BOOT delay per extra repeat -- the control that
# makes a clock-derived byte visible (see run_side).
#
# 🔴 IT IS `boot`, AND THE FIRST CUT JITTERED `cap_gap`, WHICH MOVES NOTHING.
# `cap_gap` is the gap AFTER a case's capture (omsx_repl._tcl schedules the
# capture at `t`, then does `t += cap_gap` for the NEXT case) -- and this probe
# runs boot-per-case, so there IS no next case and the knob was connected to the
# emulator's exit, not to the reading. Measured rather than argued: the same
# payload at cap_gap 2.5 and 4.2 returns JIFFY=$01D3 BOTH TIMES, while shifting
# `boot` by 1.7 s returns $0229 -- a delta of 85 ticks, exactly 1.7 s of the
# VG-8020's 50 Hz. A control that cannot move its own subject is not a control,
# and this one reported VOLATILE=0 across the entire work area while looking
# like it worked.
CAP_JITTER = 1.7

# --- the stimulus battery (spec §7) -----------------------------------------
# The load-bearing trio is s0/s1/s2. s3..s5 are EXPLORATORY breadth: whatever
# they find is a candidate, not a conclusion.
#
# `evidence` is what the SCREEN pass must show for that state's delivery to
# count on a side -- a callable over the joined screen text, so it can be one
# rule for three machines whose error WORDING differs by design (zerobas's is
# lowercase; a raw text match would fail every zerobas row and classify nothing).
STATES = [
    # key          lines                 role / evidence
    ("s0-boot",    [],                   "CONTROL: the 'unset' pin -- every "
                                         "other verdict is a delta from here"),
    ("s1-err",     ["GOTO 99999"],       "the filed stimulus (Undefined line "
                                         "number, ERR=8)"),
    ("s2-noerr",   ["A=1"],              "CONTROL: separates 'moved because of "
                                         "the ERROR' from 'moved because "
                                         "anything at all was typed'"),
    ("s3-def",     ["DEFINT A"],         "exploratory"),
    ("s4-var",     ['A=1:B$="X"'],       "exploratory"),
    ("s5-width",   ["WIDTH 32"],         "exploratory"),
    # --- the RE-HOMING battery (docs/spec-basic-sysvar-rehoming.md §5.2) ------
    # Four PAIRS. Each pair differs in exactly the property under test, so the
    # reading is a DELTA and not a value comparison -- which is what makes it a
    # SEMANTICS test. A shared name cannot answer "is this the same variable";
    # "does it move by 16 when 16 bytes of string are allocated" can.
    ("s6-armed",   ["10 ON ERROR GOTO 100", "20 STOP", "100 STOP", "RUN"],
                                         "CONTROL for s7-fired: the handler is "
                                         "ARMED and never FIRES. A variable that "
                                         "moves here too is not error state"),
    ("s7-fired",   ["10 ON ERROR GOTO 100", "20 GOTO 99999", "100 STOP", "RUN"],
                                         "the trap FIRES: ONEFLG/ERRFLG/ERRLIN "
                                         "live, and ERRLIN is a real line number "
                                         "(20) rather than direct mode"),
    ("s8-str4",    ['A$=STRING$(4,66):PRINT A$'],
                                         "CONTROL for s9-str20: 4 bytes of heap"),
    ("s9-str20",   ['A$=STRING$(20,67):PRINT A$'],
                                         "16 bytes MORE than s8. FRETOP moving "
                                         "by 16 == an allocation pointer; not "
                                         "moving == a boundary"),
    ("s10-defint", ['DEFINT A:PRINT"[";A;"]"'],
                                         "CONTROL for s11-defstr: DEFTBL['A'] "
                                         "declared NUMERIC"),
    ("s11-defstr", ['DEFSTR A:PRINT"[";A;"]"'],
                                         "DEFTBL['A'] declared STRING -- the "
                                         "published map encodes a FLOAT TYPE "
                                         "CODE (2/3/4/8), zerobas a 0/1 sentinel"),
    ("s12-scal1",  ['A=1:PRINT"[";A;"]"'],
                                         "CONTROL for s13-scal3: one scalar"),
    ("s13-scal3",  ['A=1:B=2:C=3:PRINT"[";C;"]"'],
                                         "two scalars MORE than s12 -- the "
                                         "ARYTAB/STREND pointer chain must step"),
]
STATE_LINES = {k: v for k, v, _r in STATES}
ROLE = {k: r for k, _v, r in STATES}
BASELINE = "s0-boot"


def _has_error(txt: str) -> bool:
    """An error was reported, in ANY of the three machines' wordings. zerobas
    prints lowercase by design (a documented divergence), so this matches on the
    stem only and never on capitalisation."""
    return "undefined line number" in txt.lower()


EVIDENCE = {
    # s0 types nothing but the prefix CR, so its only evidence is that the
    # machine reached a BASIC prompt at all -- which is a real check: a CF-3300
    # still sitting at its date prompt would otherwise be read as a baseline.
    "s0-boot":  lambda t: any(p in t for p in omsx_repl.PROMPTS),
    "s1-err":   _has_error,
    # 🟢 THE CONTROL'S EVIDENCE IS THE ABSENCE OF THE OTHER'S. A no-error state
    # that silently errored would be a stimulus mix-up, not a reading.
    "s2-noerr": lambda t: not _has_error(t),
    "s3-def":   lambda t: not _has_error(t),
    "s4-var":   lambda t: not _has_error(t),
    "s5-width": lambda t: not _has_error(t),
    # 🔴 THESE GUARDS ARE STRONGER THAN DELIVERY, AND DELIBERATELY SO. `break in
    # 20` vs `break in 100` names the BRANCH TAKEN, so a state that arrived
    # perfectly and did NOT trap is caught -- an ordinary "no error / an error"
    # guard would pass s6 and s7 on a machine that ran neither handler. Matched
    # lowercase because zerobas prints its messages lowercase by design
    # (basic/program.asm:682 `db "break",0`), and a raw text match would VOID
    # every zerobas row and classify nothing.
    "s6-armed":   lambda t: "break in 20" in t.lower(),
    "s7-fired":   lambda t: "break in 100" in t.lower(),
    # The string pair proves its own payload LENGTH reached the heap: a dropped
    # keystroke inside STRING$(20,67) yields a different run of Cs, not the same
    # screen. `BBBB` cannot come from the echo (which shows `STRING$(4,66)`).
    "s8-str4":    lambda t: "BBBB" in t,
    "s9-str20":   lambda t: "C" * 20 in t,
    # 🟢 DIAGNOSTIC, NOT MERELY DELIVERY: `[ 0 ]` vs `[]` IS the type decision
    # under test, printed. A state whose DEFTBL write silently did nothing shows
    # the other pair member's screen and is voided.
    "s10-defint": lambda t: "[ 0 ]" in t,
    "s11-defstr": lambda t: "[]" in t,
    "s12-scal1":  lambda t: "[ 1 ]" in t,
    "s13-scal3":  lambda t: "[ 3 ]" in t,
}

# --- C-INSTR: pin the instrument against a real PEEK -------------------------
# ⚠️ THE ADDRESSES ARE CHOSEN TO BE STABLE ACROSS THE `PRINT` ITSELF. CSRY
# ($F3DC) would be a natural pick and is WRONG here: PEEK reads it mid-PRINT
# while read_block reads it after the line finished, so the two would disagree
# for a reason that is not an instrument fault -- a false void.
# The state is s1-err, so $F414 is pinned in the ERROR state: the instrument is
# checked on the very byte the whole finding turns on, where the three sides are
# known to disagree, rather than on a byte that reads 0 everywhere.
#
# 🔴 AND C-INSTR RUNS ITS OWN MEMORY PASS RATHER THAN BORROWING s1-err's.
# The first cut compared PEEK here against the s1-err dump, and that comparison
# was WRONG BY CONSTRUCTION: the screen pass must set `SCREEN 0` (the CF-3300
# boots Disk BASIC in SCREEN 1, whose name table this scraper does not read) and
# the memory pass must NOT. `SCREEN 0` reloads LINLEN from LINL40, so on the
# CF-3300 the two passes would have read 39 and 29 -- an instrument FAILURE
# reported from a difference that is not one, voiding every run on that side.
# Comparing two passes over the IDENTICAL payload removes the question instead
# of arguing about which addresses a mode switch is safe for.
CINSTR_ADDRS = [0xF414, 0xF3B0, 0xF676, 0xF3E9]   # ERRFLG, LINLEN, TXTTAB, FORCLR
CINSTR_LINES = ["SCREEN 0", "CLS"] + STATE_LINES["s1-err"] + [
    'PRINT"[";' + ";".join(f"PEEK(&H{a:04X})" for a in CINSTR_ADDRS) + ';"]"']

# --- C-REPRO: the filed row, re-derived --------------------------------------
# 🔴 THE FIX INVERTED THIS CONTROL, AND DELETING IT WOULD HAVE BEEN THE WRONG
# ANSWER. C-REPRO was `verdict=DIVERGE, refs=08, zb=00`: the sweep had to
# independently re-find the filed $F414 row, because a sweep that reports nothing
# is indistinguishable from a sweep that measures nothing. D-REHOME then HONOURED
# $F414 -- so the row it was pinned to stopped existing, and the control would
# have failed the whole run for the best possible reason.
#
# The control's JOB is unchanged: assert a known-from-elsewhere answer about the
# one byte this arc turns on. What changed is the known answer. It is now
# HONOURED/08/08, and that is a STRICTLY STRONGER assertion than the old one --
# the old row passed whenever zerobas did nothing at all with $F414, and this one
# fails the moment the honouring regresses. It is the fix's own regression gate.
CREPRO = dict(addr=0xF414, state="s1-err", verdict="HONOURED",
              refs=0x08, zb=0x08)


# =============================================================================
# the denominator: parse C-BIOS's system-variable table
# =============================================================================
def load_table(path: str):
    """Return [(name, addr, disabled)] for every `NAME: equ $XXXX` in C-BIOS's
    systemvars.asm, including the three that are COMMENTED OUT (RDPRIM/WRPRIM/
    CLPRIM -- defined in main.asm instead). Those are kept because the question
    is what the ADDRESS is called in the published map, not what C-BIOS chose to
    do about it here.

    ⚠️ THIS IS A GENERATOR, NEVER A VERDICT (the `INTERVAL` failure mode). A name
    in this table is a label for a byte; whether that byte is honoured is
    decided downstream by measurement alone."""
    if not os.path.exists(path):
        raise SystemExit(
            f"sysvarsweep: no C-BIOS table at {path}\n"
            "  the denominator comes from the pinned repack checkout "
            "(cbios-repack/README.md); point CBIOS=<path> at it.")
    out = []
    for m in re.finditer(
            # ⚠️ THE TRAILING-COMMENT ALTERNATIVE IS NOT COSMETIC. Anchoring on a
            # bare end-of-line silently dropped the 10 entries C-BIOS annotates
            # inline -- among them JIFFY ($FC9E) -- and the extent derivation
            # then absorbed the hole into its neighbour, labelling the single
            # most VOLATILE byte in the whole work area "PADX+1". A wrong name on
            # a divergent byte is worse than no name.
            r'^(;?)([A-Za-z_][A-Za-z0-9_.]*): *equ +\$([0-9A-Fa-f]{4})'
            r'\s*(?:;.*)?$',
            open(path).read(), re.M):
        out.append((m.group(2), int(m.group(3), 16), m.group(1) == ";"))
    return sorted(out, key=lambda e: (e[1], e[0]))


def name_collisions(table, sysvars_inc):
    """Symbols that zerobas defines under a PUBLISHED NAME at a PRIVATE ADDRESS.

    Layer 0 of the denominator: it needs no emulator, no reference ROM and no
    stimulus, and it finds the same class the ERRFLG row did -- a standard
    variable re-homed into zerobas' own RAM window, keeping the standard name.
    Returns (matching, moved) as lists of (name, zb_addr, published_addr).

    ⚠️ TWO LIMITS, BOTH LOAD-BEARING, BECAUSE THIS IS THE LAYER MOST LIKELY TO BE
    MISREAD AS A VERDICT:
      * It matches on the NAME. The pair that started this whole item --
        zerobas' ERRCODE/ERRLINE against the published ERRFLG/ERRLIN -- is
        SPELLED DIFFERENTLY and is therefore INVISIBLE here. So this list is a
        LOWER BOUND on the class, never a census of it; the measured sweep is
        what closes it.
      * A shared name is not shared semantics. zerobas' SAVSTK is documented as
        an SP anchor for the trap unwind; whether that is what the published
        SAVSTK holds is a question this comparison does not ask and cannot
        answer. A row here says "the standard address was not used", not "the
        behaviour is wrong"."""
    cb = {n: a for n, a, _d in table}
    zb = {}
    for m in re.finditer(r'^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+\$([0-9A-Fa-f]{4})',
                         open(sysvars_inc).read(), re.M):
        zb.setdefault(m.group(1), int(m.group(2), 16))
    same, moved = [], []
    for n, a in sorted(zb.items(), key=lambda kv: kv[1]):
        if n in cb:
            (same if cb[n] == a else moved).append((n, a, cb[n]))
    return same, sorted(moved, key=lambda t: t[2])


def build_owner(table, cbios_src):
    """addr -> "BIOS" | "BASIC", by the mechanical test of spec §4: is the symbol
    referenced anywhere in C-BIOS *outside* systemvars.asm?

      BIOS   C-BIOS supplies it. zerobas does not, and must not -- a divergence
             here is a C-BIOS-vs-reference-BIOS difference BELOW the BASIC layer,
             the same class as the VDP R7 exclusion basic_probe_graphics.py:959
             already carries.
      BASIC  C-BIOS never touches it, so on a real MSX the BASIC ROM writes it
             and on zerobas ZEROBAS must, or nobody does. ERRFLG is here.

    ⚠️ A GENERATOR, NOT A VERDICT -- and the weakest link in the report, so it is
    labelled everywhere it appears. A whole-word source match cannot see an
    address written through a computed expression, and C-BIOS merely *mentioning*
    a symbol is not proof it maintains the byte the way the reference does. It
    sorts the findings; it never decides one."""
    d = os.path.dirname(cbios_src)
    other = ""
    for f in sorted(os.listdir(d)):
        if f.endswith(".asm") and f != os.path.basename(cbios_src):
            other += open(os.path.join(d, f), errors="ignore").read()
    return {a: ("BIOS" if re.search(r'\b' + re.escape(n) + r'\b', other)
                else "BASIC") for n, a, _dis in table}


def build_namer(table):
    """addr -> "NAME" or "NAME+n" or None. Extent is DERIVED from the next
    symbol's address (C-BIOS's table declares no sizes), so a multi-byte
    variable's tail bytes are named as offsets from its head. That derivation is
    an aid to READING the report and is never load-bearing: every verdict is
    per-byte and computed without it."""
    heads = sorted({a for _n, a, _d in table})
    byaddr = {}
    for n, a, d in table:
        byaddr.setdefault(a, []).append(n + ("(disabled)" if d else ""))
    names, head_of = {}, {}
    for i, a in enumerate(heads):
        end = heads[i + 1] if i + 1 < len(heads) else a + 1
        end = min(end, WORK_HI + 1)
        label = "/".join(byaddr[a])
        for off in range(end - a):
            names[a + off] = label if off == 0 else f"{label}+{off}"
            head_of[a + off] = a
    return names, head_of


# =============================================================================
# driving one side
# =============================================================================
def _tmpdisk(side, diska):
    """⚠️ NEVER hand openMSX the repo's own .dsk -- a probe that does is one bug
    away from mutating a committed artifact (basic_probe_lnblank.py:85)."""
    if not diska:
        return None
    t = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"svs_{side}_",
                                    delete=False).name
    shutil.copy(diska, t)
    return t


def run_side(side, keys, repeat, mode):
    """Deliver each state in `keys` to one machine and return {key: reading}.

    mode="mem"    -> reading is `bytes` of length WORK_LEN, or None
    mode="screen" -> reading is the joined screen text, or None

    ⚠️ BOOT-PER-CASE IS MANDATORY AND IS THE WHOLE POINT. This sweep measures
    what LEAKS BETWEEN cases: `reset` clears the program, it does NOT clear the
    error state, and basic_probe_lnblank.py:1404 records a control that AGREED
    FOR THE WRONG REASON when an err row shared a boot with the row before it.
    Here every case is an error-state case.
    ⚠️ batch=False makes run_cases IGNORE `reset` entirely, which is where the
    CF-3300's date-prompt CR and the screen pass's `SCREEN 0` live -- so both are
    prepended to the case itself. Isolating rows without carrying the setup
    forward once left the CF-3300 sitting at its date prompt being read through a
    40-column scraper.

    ⚠️ THE MEMORY PASS DELIBERATELY DOES NOT SET `SCREEN 0`. A RAM reading is
    screen-mode independent, so the memory pass observes each machine in ITS OWN
    boot mode and only the guard pass perturbs it. The CF-3300 boots Disk BASIC
    in SCREEN 1, whose name table this scraper does not read -- so the SCREEN
    pass needs the mode set and the MEMORY pass must not have it.

    ⚠️ REPEAT IS NOT OPTIONAL, AND HERE IT IS ALSO THE VOLATILITY CONTROL. On a
    reference pass a dropped keystroke in the ORACLE-LOCK direction is a false
    PASS forever. On THIS surface it does double duty: a byte whose two readings
    differ on the same side is VOLATILE and has no reading on any side.

    🔴 AND A PLAIN REPEAT CANNOT SEE THE VOLATILITY THAT MATTERS HERE, WHICH THE
    FIRST RUN PROVED BY REPORTING **ZERO** VOLATILE BYTES IN THE WHOLE WORK AREA
    -- JIFFY INCLUDED. openMSX is DETERMINISTIC: two runs of an identical
    timeline sample every clock-derived byte at the identical emulated instant,
    so JIFFY, the scan counters and the repeat counters read back BIT-IDENTICAL
    and a time-derived byte is indistinguishable from a semantic one. That is the
    same determinism that makes a harness race reproduce exactly
    ([[deterministic-mangle-is-still-a-mangle]]), pointed at a different target.
    `REPCNT` was the tell: it was reported as zerobas EXTRA-moving a byte the
    references leave alone (A6->7C), stable across both repeats, from a
    keyboard-repeat counter that is a pure function of elapsed time.
    So the repeats are JITTERED: each one samples at a different emulated
    capture delay, and any byte that moves under a shift of the sampling instant
    ALONE is time-derived and has no reading. This strictly strengthens the
    delivery guard rather than trading against it -- the payload timeline is
    untouched, only the moment of the read moves."""
    cfg = SIDES[side]
    tmp = _tmpdisk(side, cfg["diska"])
    pre = list(PREFIX) + (["SCREEN 0", "CLS"] if mode == "screen" else [])
    capture = "screen" if mode == "screen" else ("mem_abs", CAP_SEGS)
    specs = [("direct", pre + STATE_LINES[k]) for k in keys]

    runs = []
    for i in range(repeat):
        runs.append(omsx_repl.run_cases(
            cfg["machine"], specs, batch=False, capture=capture,
            boot=cfg["boot"] + i * CAP_JITTER, step=cfg["step"], diska=tmp))
    if tmp:
        os.unlink(tmp)

    out = {}
    for i, k in enumerate(keys):
        vals = [r[i] for r in runs]
        if any(v is None for v in vals):
            out[k] = None                      # NOCAPTURE -- apparatus failure
        elif mode == "screen":
            # ⚠️ THE GUARD DOES NOT DEMAND TWO IDENTICAL SCREENS, it demands the
            # evidence on EVERY repeat. Byte-identity is stricter than the
            # question and would void a side over furniture (a blinking cursor
            # cell, a scroll offset) -- a guard that fails on noise gets
            # loosened, and a loosened guard is the one that misses a real
            # delivery failure. Every repeat is returned; EVIDENCE judges all.
            out[k] = [" ".join(v[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
                               for r in range(omsx_repl.ROWS)) for v in vals]
        else:
            bs = [bytes.fromhex(v) for v in vals]
            # per-byte volatility: a byte differing across this side's own
            # repeats has no reading. Carried as a mask alongside the value.
            # ⚠️ THE LAST REPEAT IS KEPT TOO, so a VOLATILE row can SHOW its own
            # evidence. Reporting only repeat 0 printed the same value twice next
            # to the word VOLATILE -- a row that looks like a misclassification
            # is one a reader learns to skip, and this is the class the whole
            # jitter control exists to surface.
            vol = bytes(0 if all(b[j] == bs[0][j] for b in bs) else 1
                        for j in range(len(bs[0])))
            out[k] = (bs[0], vol, bs[-1])
    return out


def run_cinstr(side, repeat):
    """Read CINSTR_ADDRS BOTH ways on one side, over the IDENTICAL payload.
    Returns (peeked, blocked) as two lists of ints, or (None, None)."""
    cfg = SIDES[side]
    tmp = _tmpdisk(side, cfg["diska"])
    spec = [("direct", list(PREFIX) + CINSTR_LINES)]
    kw = dict(batch=False, boot=cfg["boot"], step=cfg["step"], diska=tmp)
    peeks, blocks = [], []
    for _ in range(repeat):
        raw = omsx_repl.run_cases(cfg["machine"], spec, capture="screen", **kw)[0]
        peeks.append(_bracket(raw))
        blk = omsx_repl.run_cases(cfg["machine"], spec,
                                  capture=("mem_abs", [(WORK_LO, WORK_LEN)]),
                                  **kw)[0]
        blocks.append(None if blk is None else
                      [bytes.fromhex(blk)[a - WORK_LO] for a in CINSTR_ADDRS])
    if tmp:
        os.unlink(tmp)
    stable = (len({repr(p) for p in peeks}) == 1
              and len({repr(b) for b in blocks}) == 1)
    if not stable or peeks[0] is None or blocks[0] is None:
        return None, None
    return peeks[0], blocks[0]


def _bracket(raw):
    """The `[ a b c d ]` span PRINTed by C-INSTR, as a list of ints.

    The bracket convention exists because a bare number on a screen cannot be
    told from furniture; a payload printing without its brackets has NO reading
    at all on any side, and those compare EQUAL (the say-row lesson).

    🔴 IT IS THE **LAST** BRACKET PAIR, AND THE FIRST CUT GOT THIS WRONG ON ALL
    THREE SIDES AT ONCE. The C-INSTR payload contains `"["` and `"]"` as literals,
    so its own ECHO puts a bracket pair on the screen ahead of the output:

        PRINT"[";PEEK(&HF414);PEEK(&HF3B0);PE      <- echo, wrapped
        EK(&HF676);PEEK(&HF3E9);"]"                <- echo, and its `]`
        [ 8  37  1  15 ]                           <- the actual reading

    A leftmost match spans from the echo's `[` to the echo's `]` and yields
    non-numeric text -> None -> "C-INSTR NO READING" on every side, which reads
    exactly like an instrument failure and is not one. `result_span_after_echo`
    is the library answer to this and cannot be used here either: it anchors on a
    row that EQUALS the command line, and this echo WRAPS across two rows.
    Anchoring on the last pair is correct and fails in the safe direction -- if
    the payload printed nothing, the last pair is the echo's, the parse fails,
    and the run is VOIDED rather than passed."""
    if raw is None:
        return None
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].rstrip()
            for r in range(omsx_repl.ROWS)]
    txt = " ".join(rows)
    i = txt.rfind("[")
    j = txt.find("]", i + 1) if i >= 0 else -1
    if i < 0 or j < 0:
        return None
    try:
        return [int(x) for x in txt[i + 1:j].split()]
    except ValueError:
        return None


# =============================================================================
# the verdict lattice (spec §6)
# =============================================================================
VERDICTS = ("VOLATILE", "NO-ORACLE", "DIVERGE", "EXTRA", "HONOURED", "INERT",
            "BASE-DIFF", "NOREAD")


# =============================================================================
# the RE-HOMING table (docs/spec-basic-sysvar-rehoming.md §5.3)
# =============================================================================
def _cells(mem, side, state, addr, size):
    """(base_bytes, cur_bytes, volatile) for one variable on one side, or None."""
    b, c = mem[side].get(BASELINE), mem[side].get(state)
    if b is None or c is None:
        return None
    j = _idx(addr)
    vol = any(b[1][j + k] or c[1][j + k] for k in range(size))
    return (bytes(b[0][j:j + size]), bytes(c[0][j:j + size]), vol)


def _delta(base, cur):
    """Signed movement of a 2-byte LE cell, baseline -> current."""
    d = (int.from_bytes(cur, "little") - int.from_bytes(base, "little")) & 0xFFFF
    return d - 0x10000 if d >= 0x8000 else d


def rehome_verdict(mem, state, pub, size, zba, sides):
    """Verdict for ONE re-homed variable under ONE stimulus.

    🔴 THE QUESTION IS NOT "does zerobas honour the address" -- the sweep already
    answers that, and answers it "no" for all ten. It is "is the PUBLISHED
    variable the SAME VARIABLE as the one zerobas keeps privately", which needs
    both cells read at once and cannot be answered by a name.

    Returns (verdict, detail-string)."""
    rp = {s: _cells(mem, s, state, pub, size) for s in REF_SIDES if s in sides}
    if any(v is None for v in rp.values()) or not rp:
        return "NOREAD", ""
    if any(v[2] for v in rp.values()):
        return "VOLATILE", ""
    vals = {(v[0], v[1]) for v in rp.values()}
    if len(vals) != 1:
        # 🔴 NO-ORACLE IS A VERDICT ABOUT THE COMPARISON, NOT ABOUT THE VARIABLE,
        # AND THE ORACLE-LOCK PASS PROVED IT ON FRETOP. The two references hold
        # DIFFERENT absolute values there ($F168 vs $DC5F) because their string
        # spaces begin in different places -- and they agree PERFECTLY on the
        # quantity that carries the meaning: both move -4 for a 4-byte string and
        # -20 for a 20-byte one. An absolute comparison of a POINTER into
        # machine-dependent RAM can only ever answer "the machines disagree",
        # which is true and is not what was asked.
        #
        # So a pointer-sized cell whose refs disagree absolutely gets a second
        # question: do they agree on the DELTA from the baseline? If they do,
        # there IS an oracle -- the movement -- and zerobas can be right or wrong
        # about it. This strictly ADDS readings; a cell that fails here falls
        # through to NO-ORACLE exactly as before.
        det = "  ".join(f"{s}={rp[s][0].hex()}->{rp[s][1].hex()}" for s in rp)
        if size != 2:
            return "NO-ORACLE", det
        deltas = {_delta(v[0], v[1]) for v in rp.values()}
        if len(deltas) != 1:
            return "NO-ORACLE", det
        rd = next(iter(deltas))
        det += f"   refsΔ={rd:+d}"
        if "zb" not in sides:
            return ("REF-DELTA" if rd else "REF-INERT"), det
        zv = _cells(mem, "zb", state, zba, size)
        if zv is None:
            return "NOREAD", det
        if zv[2]:
            return "VOLATILE", det
        zd = _delta(zv[0], zv[1])
        det += f"  zb@privΔ={zd:+d} ({zv[0].hex()}->{zv[1].hex()})"
        # 🔴 A KNIFE ON MY OWN FIX. The first cut of this branch returned
        # DIFF-DELTA for every one-sided movement, and SAVSTK is what showed it
        # up: the references never move it under any stimulus here (refsΔ=+0)
        # while zerobas writes a real SP anchor (zbΔ=-3349), and "DIFF-DELTA"
        # reads as "zerobas moves it WRONGLY" when the truth is "the references
        # do not move it here AT ALL, so there is nothing to be wrong about."
        # The absolute branch above has always said ZB-ONLY/REF-ONLY for exactly
        # this shape; the delta branch disagreed with it, and the two must not
        # answer the same question differently.
        if rd == 0 and zd == 0:
            return "INERT", det
        if rd == 0:
            return "ZB-ONLY", det
        if zd == 0:
            return "REF-ONLY", det
        return ("SAME-DELTA" if rd == zd else "DIFF-DELTA"), det
    rbase, rcur = next(iter(vals))
    ref_moved = rcur != rbase
    det = f"refs={rbase.hex()}->{rcur.hex()}"

    if "zb" not in sides:                      # oracle-lock pass: refs only
        return ("REF-MOVED" if ref_moved else "REF-INERT"), det

    zp, zv = _cells(mem, "zb", state, pub, size), _cells(mem, "zb", state, zba, size)
    if zp is None or zv is None:
        return "NOREAD", det
    if zp[2] or zv[2]:
        return "VOLATILE", det
    det += f"  zb@pub={zp[0].hex()}->{zp[1].hex()}  zb@priv={zv[0].hex()}->{zv[1].hex()}"
    priv_moved = zv[1] != zv[0]

    if not ref_moved and not priv_moved:
        # ⚠️ A NON-RESULT, NEVER A PASS. It says this stimulus does not exercise
        # this variable -- the INERT lesson, one layer up.
        return "INERT", det
    if ref_moved and not priv_moved:
        return "REF-ONLY", det
    if priv_moved and not ref_moved:
        return "ZB-ONLY", det
    return ("SAME-VAR" if rcur == zv[1] else "SAME-ROLE"), det


def classify(j, mem, state):
    """Verdict for byte index `j` in `state`. `mem[side][key] = (values, vol)`.

    Order matters: an unreadable byte must never fall through into a verdict
    that reads like a finding."""
    base, cur = {}, {}
    for s in ALL_SIDES:
        b, c = mem[s].get(BASELINE), mem[s].get(state)
        if b is None or c is None:
            return "NOREAD"
        if b[1][j] or c[1][j]:
            return "VOLATILE"
        base[s], cur[s] = b[0][j], c[0][j]

    r1, r2 = REF_SIDES
    if base[r1] != base[r2] or cur[r1] != cur[r2]:
        return "NO-ORACLE"
    rb, rc, zb, zc = base[r1], cur[r1], base["zb"], cur["zb"]

    if state == BASELINE:
        # At the baseline there is no movement to measure, so an agreement here
        # is the WEAKEST reading in the whole report and is labelled as such:
        # a machine that never touches a byte agrees with one that does.
        return "INERT" if zc == rc else "BASE-DIFF"

    ref_moved, zb_moved = rc != rb, zc != zb
    if ref_moved:
        return "HONOURED" if (zc == rc and zb == rb) else "DIVERGE"
    return "EXTRA" if zb_moved else "INERT"


# =============================================================================
# report
# =============================================================================
def main() -> int:
    global ALL_SIDES
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zb-machine", default=ZB_MACHINE)
    ap.add_argument("--cbios", default=CBIOS_SRC)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--only", help="comma-separated state keys")
    ap.add_argument("--named-only", action="store_true",
                    help="report only bytes C-BIOS's table names")
    ap.add_argument("--max-rows", type=int, default=60,
                    help="per-class cap on listed byte rows (0 = no cap)")
    ap.add_argument("--sides", default=",".join(ALL_SIDES),
                    help="comma-separated sides. 🔴 THIS IS THE ORACLE-LOCK "
                         "MECHANISM: --sides vg8020,cf3300 runs a NEW state on "
                         "the references ONLY, so what they do is written down "
                         "BEFORE zerobas is run on it. Without it that "
                         "discipline is a promise rather than a mechanism, and "
                         "a mangle in the oracle-lock direction is a false PASS "
                         "forever.")
    args = ap.parse_args()
    SIDES["zb"]["machine"] = args.zb_machine

    want_sides = tuple(s.strip() for s in args.sides.split(",") if s.strip())
    if any(s not in SIDES for s in want_sides) or not want_sides:
        return _fail(f"unknown side(s) in --sides {args.sides!r}")
    ALL_SIDES = tuple(s for s in ("vg8020", "cf3300", "zb") if s in want_sides)
    if not set(REF_SIDES) <= set(ALL_SIDES):
        # A run without both references has no oracle at all: every verdict in
        # the lattice is defined against "the two references agree".
        return _fail("--sides must include both references")
    refs_only = "zb" not in ALL_SIDES

    if args.repeat < 2:
        # ⚠️ NOT a style preference. With one run per side there is no volatility
        # control at all, and JIFFY/RND/scan bytes are then reported as
        # divergences -- a report whose loudest rows are all apparatus noise.
        return _fail("--repeat must be >= 2 (it IS the volatility control)")

    keys = [k for k, _l, _r in STATES]
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        bad = want - set(keys)
        if bad:
            return _fail(f"unknown state key(s): {sorted(bad)}")
        keys = [k for k in keys if k in want]
        if BASELINE not in keys:
            # Every verdict is a delta from the baseline; without it there is
            # nothing to be a delta FROM.
            keys = [BASELINE] + keys

    table = load_table(args.cbios)
    names, head_of = build_namer(table)
    owner_head = build_owner(table, args.cbios)
    owner = lambda a: owner_head.get(head_of.get(a), "?")  # noqa: E731
    print(f"MSX work-area sweep  ${WORK_LO:04X}..${WORK_HI:04X} "
          f"({WORK_LEN} B)   repeat={args.repeat}")
    print(f"  denominator: {len(table)} named entries from {args.cbios}")
    print(f"  states     : {', '.join(keys)}")
    print(f"  sides      : {', '.join(SIDES[s]['machine'] for s in ALL_SIDES)}")
    print(f"  private    : {', '.join(f'${a:04X}+{n}' for a, n in PRIV_SEGS)}"
          f"  ({PRIV_LEN} B of zerobas' OWN cells, read by the same instrument)")
    if refs_only:
        print("\n  🔒 ORACLE-LOCK PASS — references only. What they do is "
              "recorded BEFORE zerobas runs on these states.")
    print()

    # --- pass 0: STATIC — published name, private address (no emulator) -------
    sysinc = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "basic", "sysvars.inc")
    same, moved = name_collisions(table, sysinc)
    print("=== static: zerobas symbols sharing a PUBLISHED NAME ===")
    print(f"  {len(same)} at the published address, {len(moved)} RE-HOMED:")
    for n, z, c in moved:
        print(f"    {n:10} zerobas=${z:04X}   published=${c:04X}")
    print("  ⚠️ STILL a LOWER BOUND: this matches on the NAME. D-REHOME renamed "
          "ERRCODE/ERRLINE to the")
    print("     published ERRFLG/ERRLIN so THAT pair is now visible, but a "
          "variable re-homed under a")
    print("     different spelling would be just as invisible as those two "
          "were. See REHOMED above.\n")

    # --- pass 1: the ECHO GUARD, on every side, BEFORE any reading is trusted -
    print("=== echo guard (delivery) — a state that cannot be verified on a "
          "side yields NO READING there ===")
    voided = set()
    scr = {s: run_side(s, keys, args.repeat, "screen") for s in ALL_SIDES}
    for k in keys:
        marks = []
        for s in ALL_SIDES:
            t = scr[s][k]
            ok = t is not None and all(EVIDENCE[k](x) for x in t)
            marks.append(f"{s}={'OK' if ok else 'VOID'}")
            if not ok:
                voided.add((s, k))
        print(f"  {k:10} {'  '.join(marks)}")
    if voided:
        for s, k in sorted(voided):
            print(f"    VOID {s} {k}: {str(scr[s][k])[:200]!r}")
    print()

    # --- pass 2: C-INSTR ------------------------------------------------------
    print("=== C-INSTR — read_block vs PEEK, on the byte the finding turns on ===")
    mem = {s: run_side(s, keys, args.repeat, "mem") for s in ALL_SIDES}
    instr_fail = []
    for s in ALL_SIDES:
        peeked, got = run_cinstr(s, args.repeat)
        if peeked is None or got is None or len(peeked) != len(CINSTR_ADDRS):
            instr_fail.append(s)
            print(f"  {s:8} NO READING  peek={peeked} blk={got}")
            continue
        if got != peeked:
            instr_fail.append(s)
        print(f"  {s:8} {'OK  ' if got == peeked else 'FAIL'} "
              + "  ".join(f"${a:04X} peek={p} blk={g}"
                          for a, p, g in zip(CINSTR_ADDRS, peeked, got)))
    if instr_fail:
        return _fail("C-INSTR failed on " + ",".join(instr_fail)
                     + " — read_block does not agree with PEEK, so NO reading "
                       "in this run is trustworthy")
    print()

    # --- pass 2b: the RE-HOMING table -----------------------------------------
    # The report the DECISION is written from. Every other pass answers "is the
    # published address honoured" (no, for all ten); this one answers "is the
    # published variable the SAME VARIABLE as the private one", which is the
    # question a placement decision actually turns on.
    stimuli = [k for k in keys if k != BASELINE]
    print("=== the RE-HOMING table — published cell vs zerobas' PRIVATE cell ===")
    print("  SAME-VAR  = zb's private value EQUALS the refs' published value "
          "(same variable, wrong address)")
    print("  SAME-ROLE = both move, values differ (same job, different "
          "encoding/representation)")
    print("  REF-ONLY  = the refs move it, zb's private cell does NOT -> NOT the "
          "same variable")
    print("  INERT     = neither moves -> ⚠️ this stimulus does not test this "
          "variable (a NON-RESULT, never a pass)")
    print("  SAME-DELTA= the refs disagree on the ABSOLUTE value (a pointer into "
          "machine-dependent RAM) but")
    print("              agree on the MOVEMENT, and zerobas moves identically — "
          "a reading NO-ORACLE threw away\n")
    rehome = {}
    for name, pub, size, zba, status in REHOMED:
        print(f"  {name:7} pub=${pub:04X}+{size:<2} zb=${zba:04X}   {status}")
        for k in stimuli:
            if (any((s, k) in voided for s in ALL_SIDES)
                    or any((s, BASELINE) in voided for s in ALL_SIDES)):
                v, det = "NOREAD", ""
            else:
                v, det = rehome_verdict(mem, k, pub, size, zba, ALL_SIDES)
            rehome[(name, k)] = v
            print(f"      {k:11} {v:10} {det}")
        print()

    if refs_only:
        # 🔒 Nothing below this line can run without zerobas, and NOTHING here
        # may pretend to: C-REPRO, C-PRIV and C-REPRO-2 are all zerobas-vs-refs
        # statements. The oracle-lock pass ends by saying so rather than by
        # printing an empty section that reads like a pass.
        if voided:
            return _fail(f"{len(voided)} state/side deliveries could not be "
                         f"verified")
        print("ORACLE-LOCK PASS COMPLETE — the reference readings above are now "
              "pinned. Re-run with all three sides to classify zerobas.")
        return 0

    # --- pass 3: the census ---------------------------------------------------
    idx = [j for j in range(WORK_LEN)
           if not args.named_only or (WORK_LO + j) in names]
    rows = {}
    for k in keys:
        cls = {v: [] for v in VERDICTS}
        # A state is unreadable if ANY side's delivery could not be verified for
        # it OR for the baseline it is a delta from -- per state, not per byte.
        dead = any((s, k) in voided or (s, BASELINE) in voided for s in ALL_SIDES)
        for j in idx:
            cls["NOREAD" if dead else classify(j, mem, k)].append(j)
        rows[k] = cls

    def show(j, k, volatile=False):
        a = WORK_LO + j
        cell = []
        for s in ALL_SIDES:
            cur, base = mem[s].get(k), mem[s].get(BASELINE)
            if cur is None or base is None:
                cell.append(f"{s}=??")
            elif volatile:
                # the two REPEATS of this state, which is what the verdict is
                # about -- not the baseline->state delta, which is not.
                cell.append(f"{s}={cur[0][j]:02X}/{cur[2][j]:02X}")
            else:
                cell.append(f"{s}={base[0][j]:02X}->{cur[0][j]:02X}")
        return (f"    ${a:04X} {names.get(a, '-'):22} {owner(a):5} "
                + "  ".join(cell))

    for k in keys:
        cls = rows[k]
        tot = len(idx)
        print(f"=== {k}  ({ROLE[k]}) ===")
        print("    " + "  ".join(f"{v}={len(cls[v])}" for v in VERDICTS
                                 if cls[v]) + f"   (of {tot} B)")
        for v in ("BASE-DIFF", "DIVERGE", "EXTRA"):
            if cls[v]:
                # The ownership split is what says whose defect a row is. A BIOS
                # row is C-BIOS's; only a BASIC row is zerobas' to answer for.
                nb = sum(1 for j in cls[v] if owner(WORK_LO + j) == "BASIC")
                print(f"      {v}: {nb} BASIC-owned, {len(cls[v]) - nb} "
                      f"BIOS-owned/unnamed")
        # VOLATILE is listed at the baseline because the set of bytes that CANNOT
        # be read is part of the denominator, not an aside: it is what an
        # unjittered repeat silently reported as measurable.
        listed = (("DIVERGE", "EXTRA", "BASE-DIFF") if k != BASELINE
                  else ("VOLATILE", "BASE-DIFF"))
        for v in listed:
            if not cls[v]:
                continue
            print(f"  {v} ({len(cls[v])}):"
                  + ("   [per-side repeat-0/repeat-1 of THIS state]"
                     if v == "VOLATILE" else ""))
            lst = cls[v] if args.max_rows == 0 else cls[v][:args.max_rows]
            for j in lst:
                print(show(j, k, volatile=(v == "VOLATILE")))
            if len(lst) < len(cls[v]):
                # 🔴 NO SILENT CAPS: a bounded listing that does not say what it
                # dropped reads as "that was all of them".
                print(f"    ... {len(cls[v]) - len(lst)} more (--max-rows 0)")
        if k != BASELINE:
            live = len(cls["HONOURED"]) + len(cls["DIVERGE"])
            print(f"    of the {live} B the references MOVE under this stimulus, "
                  f"zerobas matches {len(cls['HONOURED'])}")
        print()

    # --- the NAMED view: the denominator as a reader can use it ---------------
    # A byte census answers "how much"; it does not answer "which variable", and
    # a 3199-row table is not a denominator anybody consults. Roll every byte up
    # to the C-BIOS symbol that owns it.
    #
    # 🔴 THE `err-only` COLUMN IS WHAT THE s2-noerr CONTROL BUYS. A variable that
    # diverges under `GOTO 99999` AND under `A=1` is not error state -- it is
    # something the reference touches on every direct-mode line. Without the
    # control every one of those would have been written up as an error-state
    # divergence, which is the filed finding's own shape generalised one step too
    # far.
    print("=== the NAMED view — divergent work-area variables, by symbol ===")
    stim = [k for k in keys if k != BASELINE]
    bysym = {}
    for k in keys:
        for v in ("DIVERGE", "BASE-DIFF"):
            for j in rows[k][v]:
                a = WORK_LO + j
                h = head_of.get(a)
                sym = names.get(h, f"${a:04X}") if h else f"${a:04X}"
                e = bysym.setdefault(sym.split("+")[0],
                                     dict(addr=h if h else a, states=set(),
                                          owner=owner(a), nb=0))
                e["states"].add(k)
                e["nb"] += 1
    if not bysym:
        print("  (none)")
    print(f"  {len(bysym)} named variables diverge in at least one state\n")
    print(f"  {'variable':16} {'addr':6} {'owner':6} {'states':34} err-only")
    for sym, e in sorted(bysym.items(), key=lambda kv: kv[1]["addr"]):
        st = e["states"]
        eo = ("yes" if ("s1-err" in st and "s2-noerr" not in st
                        and BASELINE not in st) else "-")
        print(f"  {sym:16} ${e['addr']:04X}  {e['owner']:6} "
              f"{','.join(k for k in keys if k in st):34} {eo}")
    nb = sum(1 for e in bysym.values() if e["owner"] == "BASIC")
    print(f"\n  {nb} BASIC-owned (zerobas' to answer for), "
          f"{len(bysym) - nb} BIOS-owned (C-BIOS's, below the BASIC layer)")
    eonly = [s for s, e in bysym.items()
             if "s1-err" in e["states"] and "s2-noerr" not in e["states"]
             and BASELINE not in e["states"]]
    print(f"  error-SPECIFIC (diverge under the error and NOT under the "
          f"no-error control): {len(eonly)} — {', '.join(sorted(eonly)) or '(none)'}")
    print()

    # --- pass 4: C-REPRO ------------------------------------------------------
    print("=== C-REPRO — does the sweep independently re-find the filed row? ===")
    j = CREPRO["addr"] - WORK_LO
    st = CREPRO["state"]
    if st not in keys:
        print(f"  SKIPPED ({st} not in this run) — C-REPRO cannot vouch for it")
        repro_ok = True
    else:
        v = classify(j, mem, st)
        got_r = mem["vg8020"][st][0][j]
        got_z = mem["zb"][st][0][j]
        repro_ok = (v == CREPRO["verdict"] and got_r == CREPRO["refs"]
                    and got_z == CREPRO["zb"])
        print(f"  ${CREPRO['addr']:04X} {names.get(CREPRO['addr'], '-')} "
              f"under {st}: {v}  refs={got_r:02X} zb={got_z:02X}   "
              f"(want {CREPRO['verdict']} refs={CREPRO['refs']:02X} "
              f"zb={CREPRO['zb']:02X})")
        print("  " + ("OK — the apparatus finds a known row it was not told about"
                      if repro_ok else
                      "FAIL — THE APPARATUS IS BROKEN, not the finding"))
    print()

    # --- C-PRIV: the private segments must be shown to be READ ----------------
    # 🔴 A NEW INSTRUMENT NEEDS ITS OWN POSITIVE CONTROL. A segment list that is
    # silently mis-ordered, short, or dropped renders every private cell as a
    # plausible constant -- and a constant is exactly what most of them look like
    # anyway, so the failure would be invisible. Pin it on a cell whose movement
    # is INDEPENDENTLY visible on the screen guard.
    #
    # 🔴 AND THIS CONTROL WAS PINNED ON A CELL ITS OWN FIX VACATED. The first cut
    # pinned DEFTBL['A'] at $F153 (s10-defint `[ 0 ]` vs s11-defstr `[]`) --
    # then D-REHOME moved DEFTBL to the published $F6CA, so $F153 became ordinary
    # unused RAM reading $FF in both states and C-PRIV failed, CORRECTLY, on the
    # post-fix build. That is the third control this fix inverted; C-REPRO and
    # C-REPRO-2 were re-aimed and this one was missed, because it was being
    # thought of as "the DEFTBL cell" rather than as "a cell that must still be
    # PRIVATE". A control pinned to a moving target has to be re-checked whenever
    # the target moves -- [[control-inverted-by-its-own-fix]], learned twice.
    #
    # ARYTAB $E1C0 is the right anchor precisely because it is a REJECT verdict:
    # it stays private by decision, so no future honouring can pull the rug out.
    # Its movement is corroborated on screen by `[ 1 ]` vs `[ 3 ]` -- the scalars
    # really were created -- and it is 2 bytes, so it exercises multi-byte
    # indexing into the private segments as well.
    priv_ok = True
    print("=== C-PRIV — can the private segments be shown to MOVE? ===")
    if not {"s12-scal1", "s13-scal3"} <= set(keys):
        print("  SKIPPED (s12-scal1/s13-scal3 not in this run) — C-PRIV "
              "cannot vouch for the private segments in this run")
    else:
        jd = _idx(0xE1C0)
        a = bytes(mem["zb"]["s12-scal1"][0][jd:jd + 2])
        b = bytes(mem["zb"]["s13-scal3"][0][jd:jd + 2])
        priv_ok = a != b
        print(f"  $E1C0 ARYTAB on zb: s12-scal1={a.hex()}  s13-scal3={b.hex()}"
              f"   {'OK — the segment is live' if priv_ok else 'FAIL'}")
        if not priv_ok:
            print("  A private cell that cannot be shown to move is not a "
                  "reading, and every SAME-VAR/REF-ONLY verdict above rests on "
                  "these segments.")
    print()

    # --- C-REPRO-2: both halves of the filed statement ------------------------
    # The coverage doc could only make ONE half of it ("$F414 diverges"); the
    # other half ("...and the value is at $E1C5") is what turns a divergence into
    # a RE-HOMING. If the new pass cannot re-derive both, the pass is broken.
    # 🔴 D-REHOME INVERTED THIS CONTROL TOO. It used to assert "ERRFLG is
    # SAME-VAR against $E1C5 and zerobas' $F414 must NOT move" -- the re-homing,
    # found from both ends. $F414 is now ERRFLG's real home, so the assertion is
    # the OTHER way round and is again strictly stronger: zerobas must TRACK the
    # references at the published cell under the run-mode trap.
    print("=== C-REPRO-2 — does the table confirm $F414 is now TRACKED? ===")
    if "s7-fired" not in keys:
        print("  SKIPPED (s7-fired not in this run)")
        repro2_ok = True
    else:
        v = rehome.get(("ERRFLG", "s7-fired"))
        jp = _idx(0xF414)
        zpub = mem["zb"]["s7-fired"][0][jp]
        zpub_b = mem["zb"][BASELINE][0][jp]
        repro2_ok = (v == "SAME-VAR" and zpub == 0x08 and zpub_b == 0x00)
        print(f"  ERRFLG under s7-fired: {v}   zb@$F414 "
              f"{zpub_b:02X}->{zpub:02X} (want 00->08, matching the refs)")
        print("  " + ("OK — zerobas tracks the published cell from a stored line"
                      if repro2_ok else
                      "FAIL — THE NEW PASS IS BROKEN, not the finding"))
    print()

    # --- C-VACATED: the addresses the honoured five moved OUT of --------------
    # 🔴 THE FAILURE MODE NOTHING ELSE HERE CAN SEE. A half-completed relocation
    # leaves a stale store at the old address: the published cell looks perfectly
    # honoured, the census is green, and a dead cell is being written by code
    # nobody knows still exists. The old homes must be INERT on every side in
    # every state -- asserted, not assumed.
    print("=== C-VACATED — did the old private cells go quiet? ===")
    vac_ok = True
    for nm, addr, size in VACATED:
        jv = _idx(addr)
        moved = []
        for k in keys:
            b, c = mem["zb"].get(BASELINE), mem["zb"].get(k)
            if b is None or c is None:
                continue
            if bytes(b[0][jv:jv + size]) != bytes(c[0][jv:jv + size]):
                moved.append(k)
        if moved:
            vac_ok = False
        print(f"  {nm:9} ${addr:04X}+{size:<2} "
              + ("QUIET" if not moved else f"🔴 STILL WRITTEN in {moved}"))
    print("  " + ("OK — no leftover writer at any vacated address" if vac_ok else
                  "FAIL — a relocation is only half done"))
    print()

    if not repro_ok:
        return _fail("C-REPRO did not fire")
    if not priv_ok:
        return _fail("C-PRIV did not fire — the private segments are not a "
                     "reading, so no re-homing verdict in this run is one")
    if not repro2_ok:
        return _fail("C-REPRO-2 did not fire")
    if not vac_ok:
        return _fail("C-VACATED failed — a vacated address is still being "
                     "written, so a relocation is only half done")
    if voided:
        return _fail(f"{len(voided)} state/side deliveries could not be verified")
    print("apparatus OK — this is a COVERAGE REPORT, not a pass/fail gate "
          "(nonzero exit means the APPARATUS failed).")
    return 0


def _fail(msg: str) -> int:
    print(f"\nAPPARATUS FAILURE: {msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
