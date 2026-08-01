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
ALL_SIDES = ("vg8020", "cf3300", "zb")

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
]
STATE_LINES = {k: v for k, v, _r in STATES}
ROLE = {k: r for k, _v, r in STATES}
BASELINE = "s0-boot"


def _has_error(txt: str) -> bool:
    """An error was reported, in ANY of the three machines' wordings. zerobas
    prints lowercase by design (a documented divergence), so this matches on the
    stem only and never on capitalisation."""
    return "undefined line" in txt.lower()


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
CREPRO = dict(addr=0xF414, state="s1-err", refs=0x08, zb=0x00)


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
    capture = "screen" if mode == "screen" else ("mem_abs", [(WORK_LO, WORK_LEN)])
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
                        for j in range(WORK_LEN))
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
    args = ap.parse_args()
    SIDES["zb"]["machine"] = args.zb_machine

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
    print(f"  sides      : {', '.join(SIDES[s]['machine'] for s in ALL_SIDES)}\n")

    # --- pass 0: STATIC — published name, private address (no emulator) -------
    sysinc = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "basic", "sysvars.inc")
    same, moved = name_collisions(table, sysinc)
    print("=== static: zerobas symbols sharing a PUBLISHED NAME ===")
    print(f"  {len(same)} at the published address, {len(moved)} RE-HOMED:")
    for n, z, c in moved:
        print(f"    {n:10} zerobas=${z:04X}   published=${c:04X}")
    print("  ⚠️ a LOWER BOUND: matched on the NAME, so ERRCODE-vs-ERRFLG "
          "(different spellings) is invisible here\n")

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
        repro_ok = (v == "DIVERGE" and got_r == CREPRO["refs"]
                    and got_z == CREPRO["zb"])
        print(f"  ${CREPRO['addr']:04X} {names.get(CREPRO['addr'], '-')} "
              f"under {st}: {v}  refs={got_r:02X} zb={got_z:02X}   "
              f"(want DIVERGE refs={CREPRO['refs']:02X} zb={CREPRO['zb']:02X})")
        print("  " + ("OK — the apparatus finds a known row it was not told about"
                      if repro_ok else
                      "FAIL — THE APPARATUS IS BROKEN, not the finding"))
    print()

    if not repro_ok:
        return _fail("C-REPRO did not fire")
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
