#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Keyword-completeness SWEEP — the MSX1 BASIC reserved-word denominator.

WHY THIS EXISTS
===============
zerobas has twice discovered a missing keyword *by accident*, and both had the
same silent shape — the word parses as an ordinary VARIABLE, so nothing errors
and the program just computes the wrong answer:

  * `TIME`  — found as collateral during the T3 KEY slice (20e04b4). `TIME`
    parses as the variable `TI`, reads 0 forever, and `IF TIME-T<400 GOTO`
    becomes an infinite loop.
  * `TAB(`  — found 2026-07-26 while auditing coverage. Worse: it was recorded
    as "already faithful (NO work)" in docs/spec-basic-df2-2-intarg-coercion.md
    §1.2 because `PRINT TAB(99999)` raises ERR 6 on BOTH sides. It does so for
    the WRONG REASON — zerobas has no `TAB(`, so `TAB` is an ARRAY and the
    subscript bound-check produces the same error code. The probe agreed; the
    feature is absent.

This probe closes that discovery channel by measuring the WHOLE reserved-word
set at once, so "complete MSX1 BASIC" finally has an honest denominator.

TWO LAYERS, BECAUSE ONE IS NOT ENOUGH
=====================================
The `INTERVAL` retraction (60e0ab6) is the standing lesson: a crunch probe
answers a TOKENISATION question, not a SUPPORT question. `INTERVAL` is absent
from every MSX1 keyword table — it is not a keyword at all, it is the
reserved-word compound `INT`+"ER"+`VAL` — and it works perfectly on the
VG-8020. "Absent from the keyword table" != "absent from the language."

The `TAB(` case is the mirror-image trap: identical OBSERVED BEHAVIOUR on one
probe, for structurally different reasons.

So every word is measured twice, and the two layers are reported separately:

  Layer 1 CRUNCH  — store `1 <body>` (tokenised into the program area, never
                    executed) and diff the token bytes ref vs zerobas. Reuses
                    basic_probe_crunch's stored-line capture wholesale.
  Layer 2 SUPPORT — EXECUTE a usage chosen so that "parses as a variable/array"
                    yields a VISIBLY DIFFERENT answer than real support, then
                    compare the OUTCOME CLASS (value vs which error) rather than
                    raw text — zerobas's error wording is lowercase by design
                    (a documented divergence), so a raw text diff would flag
                    every case and classify nothing.

Layer 2 is the load-bearing one. Layer 1 alone would have mis-called both
`INTERVAL` (absent token, works) and `TAB(` (present-looking, absent feature).

READING THE VERDICT
===================
  SUPPORTED    both sides produce the same outcome class and the same text
  DIVERGENT    both sides run it, but the answers differ  <- a faithfulness bug
  MISSING      the reference runs it, zerobas errors       <- a coverage gap
  SILENT-GAP   BOTH sides "succeed" but zerobas's answer betrays a
               variable/array parse (the TIME / TAB( shape)  <- the worst kind
  EXTRA        zerobas runs it, the reference errors
  SKIPPED      not safely executable in a batch (see SKIP_EXEC) — crunch only

Clean-room: this only *compares observed outputs*. No disassembly; the reference
ROM is a black box. The candidate word list is a generator only — every verdict
comes from measurement. See the clean-room firewall (CONTRIBUTING.md).

USAGE
    python3 probes/basic/basic_probe_kwsweep.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK
    ... --only tab,spc,locate      # a subset, by word key
    ... --layer crunch|support     # one layer only
    ... --boot-per-case            # isolation escape hatch
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import hashlib
import subprocess

import omsx_repl  # typing-free KEYBUF-injection REPL driver
import probe_report  # 🔴 D-KWFOOT: I3 -- every exit path that prints
                      # rows ends with a POSITIVE statement of what it measured

MACHINE = "Philips_VG_8020"
# A DISK-EQUIPPED reference, for the rows whose verbs live in Disk BASIC.
#
# This exists because the first full run tripped its own control group: `mki`
# (MKI$, which zerobas implements correctly) came back as the reference raising
# `Illegal function call` while zerobas printed the right answer. The language was
# never the asymmetry — the MACHINES were. The default reference is a DISKLESS
# VG-8020, while the zerobas side is C-BIOS_MSX1_EU_REPACK_**DISK**, so every
# MK$/CV/Disk-BASIC row was comparing "no disk ROM" against "disk ROM" and
# attributing the difference to zerobas. Rows tagged NEEDS-DISK: get their
# reference capture from this machine instead.
#
# STATUS 2026-07-26: this machine does NOT yet yield a readable SCREEN-0 capture
# under omsx_repl — a trivial `PRINT 1+1` comes back as VRAM pattern garbage, so
# it is presumably still in the boot/logo video mode when the capture fires, or
# needs a longer boot than the shared default. Until that is chased down, the
# NEEDS-DISK rows report NO-ORACLE rather than a verdict: the probe declines to
# answer instead of answering from the wrong machine. Chasing it is cheap and
# worthwhile, but the MK/CV family it gates is ALREADY tracked as deferred in
# TODO.md, so it blocks no finding in this sweep.
DISK_MACHINE = "National_CF-3300"
TXTTAB = 0xF676   # sysvar: 2-byte LE pointer to the BASIC text base (both machines)

# Widest direct-mode exec line whose prompt echo still fits ONE SCREEN-0 row, so
# omsx_repl.screen_tail can find it. Anything wider must use mode="stored" (whose
# echoed command is the short "RUN"). Enforced at startup — see main().
MAX_DIRECT_ECHO = 38

# The MSX1 BASIC reserved-word set. CANDIDATE GENERATOR ONLY — this list decides
# what gets measured, never what the answer is. Sourced from the published
# keyword/token tables (MSX Technical Data Book; MSX2 Technical Handbook Table
# 2.20 — both allowed-sources.md tier B), which is the same provenance the
# existing kwtable.inc token locks already cite.
#
# Each row: (key, crunch_body, exec_line, exec_mode, note)
#   crunch_body — stored as `1 <body>`; never executed
#   exec_line   — the Layer-2 usage; None => crunch-only (also list in SKIP_EXEC)
#   exec_mode   — "direct" (typed at the prompt) or "stored" (numbered + RUN)
#
# The exec_line for a SUSPECTED-MISSING word is designed against the failure mode
# in this file's header: it must distinguish real support from a variable/array
# parse. `PRINT TAB(99999)` is the counter-example of how NOT to write one.

SWEEP: list[tuple[str, str, str | None, str, str]] = [

    # ---------------------------------------------------------------- controls
    # Known-shipped words. They are the CONTROL GROUP: if one of these comes back
    # anything but SUPPORTED, the apparatus is lying and no other row is
    # trustworthy. (The T3 KEY lesson: distrust a baseline that cannot produce a
    # non-zero answer.)
    ("abs",     "a=abs(-5)",          'PRINT"[";ABS(-5);"]"',            "direct", "control"),
    ("int",     "a=int(1.7)",         'PRINT"[";INT(1.7);"]"',           "direct", "control"),
    ("len",     'a=len("ab")',        'PRINT"[";LEN("ab");"]"',          "direct", "control"),
    ("chr",     "a$=chr$(65)",        'PRINT"[";CHR$(65);"]"',           "direct", "control"),
    ("mid",     'a$=mid$("hi",1,1)',  'PRINT"[";MID$("hi",2,1);"]"',     "direct", "control"),
    ("instr",   'a=instr("ab","b")',  'PRINT"[";INSTR("ab","b");"]"',    "direct", "control"),
    ("hex",     "a$=hex$(255)",       'PRINT"[";HEX$(255);"]"',          "direct", "control"),
    ("sqr",     "a=sqr(9)",           'PRINT"[";SQR(9);"]"',             "direct", "control"),
    ("peek",    "a=peek(0)",          'PRINT"[";PEEK(0)>=0;"]"',         "direct", "control"),
    ("varptr",  "a=varptr(b)",        'B=1:PRINT"[";VARPTR(B)>0;"]"',    "direct", "control"),
    ("stick",   "a=stick(0)",         'PRINT"[";STICK(0);"]"',           "direct", "control"),
    ("erase",   "erase a",            'DIM Q(2):ERASE Q:PRINT"[ok]"',    "direct", "control"),
    ("swapctl", "a=1",                'A=1:PRINT"[";A;"]"',              "direct", "control (bare assign)"),

    # ------------------------------------------------- D-KWDRAIN coverage rows
    # 🎯 JOOST'S STANDING ORDER (2026-09-11): *"get rid of the 'no known gap'
    # items in the table, so we have more known tier-ed work."* A "no known gap"
    # keyword is NOT one that is fine -- it is one nobody has attributed evidence
    # to, and with TIER 2 and TIER 3 empty the binding constraint stopped being
    # "fix the next defect" and became "find out what is actually broken".
    # These rows carry the CHEAPEST-CONTEXT verbs: pure functions and operators,
    # one differential each, no device and no file state. Each exec line prints a
    # value the reference must match, so the row SCORES rather than merely
    # exercising [[exercised-is-not-verified]].
    # 🔴 NOT "control": a control that comes back unsupported means the APPARATUS
    # is lying and voids the run. These are the words under test, so an
    # unsupported one here has to read as a FINDING instead.
    # ⚠️ Fractional rows (ATN, EXP, CDBL(1)/3) are deliberate -- formatting and
    # precision are exactly where a clean-room mathpack diverges, and a row that
    # only ever prints 0 or 1 cannot see it.
    ("asc",     'a=asc("A")',         'PRINT"[";ASC("A");"]"',         "direct", "D-KWDRAIN"),
    ("cint",    'a=cint(1.7)',        'PRINT"[";CINT(1.7);"]"',        "direct", "D-KWDRAIN"),
    ("cdbl",    'a=cdbl(1)',          'PRINT"[";CDBL(1)/3;"]"',        "direct", "D-KWDRAIN"),
    ("csng",    'a=csng(1.5)',        'PRINT"[";CSNG(1.5);"]"',        "direct", "D-KWDRAIN"),
    ("fix",     'a=fix(-1.7)',        'PRINT"[";FIX(-1.7);"]"',        "direct", "D-KWDRAIN"),
    ("sgn",     'a=sgn(-3)',          'PRINT"[";SGN(-3);"]"',          "direct", "D-KWDRAIN"),
    ("sin",     'a=sin(0)',           'PRINT"[";SIN(0);"]"',           "direct", "D-KWDRAIN"),
    ("cos",     'a=cos(0)',           'PRINT"[";COS(0);"]"',           "direct", "D-KWDRAIN"),
    ("tan",     'a=tan(0)',           'PRINT"[";TAN(0);"]"',           "direct", "D-KWDRAIN"),
    ("atn",     'a=atn(1)',           'PRINT"[";INT(ATN(1)*1000);"]"', "direct", "D-KWDRAIN"),
    ("exp",     'a=exp(1)',           'PRINT"[";INT(EXP(1)*1000);"]"', "direct", "D-KWDRAIN"),
    ("log",     'a=log(1)',           'PRINT"[";LOG(1);"]"',           "direct", "D-KWDRAIN"),
    ("mod",     'a=7 mod 3',          'PRINT"[";7 MOD 3;"]"',          "direct", "D-KWDRAIN"),
    ("notop",   'a=not 0',            'PRINT"[";NOT 0;"]"',            "direct", "D-KWDRAIN"),
    ("andop",   'a=5 and 3',          'PRINT"[";5 AND 3;"]"',          "direct", "D-KWDRAIN"),
    ("orop",    'a=5 or 3',           'PRINT"[";5 OR 3;"]"',           "direct", "D-KWDRAIN"),
    ("xorop",   'a=5 xor 3',          'PRINT"[";5 XOR 3;"]"',          "direct", "D-KWDRAIN"),
    ("oct",     'a$=oct$(8)',         'PRINT"[";OCT$(8);"]"',          "direct", "D-KWDRAIN"),
    ("left",    'a$=left$("abc",2)',  'PRINT"[";LEFT$("abc",2);"]"',   "direct", "D-KWDRAIN"),
    ("right",   'a$=right$("abc",2)', 'PRINT"[";RIGHT$("abc",2);"]"',  "direct", "D-KWDRAIN"),
    ("str",     'a$=str$(5)',         'PRINT"[";STR$(5);"]"',          "direct", "D-KWDRAIN"),
    ("stringf", 'a$=string$(3,"x")',  'PRINT"[";STRING$(3,"x");"]"',   "direct", "D-KWDRAIN"),
    ("space",   'a$=space$(3)',       'PRINT"[";LEN(SPACE$(3));"]"',   "direct", "D-KWDRAIN"),
    # 🔴 CSRLIN GETS A SECOND ROW, AND THE FIRST ONE IS WHY. The original
    # `csrlin` row is scored WEAK, and `tools/tier_table.py` EXCLUDES weak rows
    # from evidence -- so CSRLIN's DIVERGENT verdict (ref `[ 4 ]` vs zb `[ 3 ]`)
    # counts as nothing and the keyword reads as "no known gap", i.e. a measured
    # divergence that the attribution table cannot see
    # [[an-unnamed-outcome-reads-as-no-outcome]]. That divergence is an ARTIFACT
    # of absolute cursor geometry against the echoed prompt, not a defect: the
    # weak row's own note records CSRLIN measured CORRECT on 2026-09-07
    # (D-WAITGAP -- LOCATE 0,5 -> 5, 0,10 -> 10) and all three sides answering 2
    # to CLS:PRINT:PRINT. So this row reads the DELTA across two PRINTs, which is
    # what the three machines agree on, and which a stub still fails: an absent
    # CSRLIN parses as a variable and gives 0-0 = 0, not 2.
    ("csrlind", 'a=csrlin',           'A=CSRLIN:PRINT:PRINT"[";CSRLIN-A;"]"', "direct", "D-KWDRAIN"),
    ("let",     'let a=5',            'LET A=5:PRINT"[";A;"]"',        "direct", "D-KWDRAIN"),
    ("rem",     'rem x',              'PRINT"[";1;"]":REM z',          "direct", "D-KWDRAIN"),

    # ------------------------------------------------ D-KWDRAIN batch 2 (2026-09-12)
    # 🔴 THE SYNTAX PARTICLES NEEDED A TRICK, AND IT IS LEGITIMATE. `tier_table.py`
    # credits a row to the FIRST keyword token in its CRUNCH body, and THEN / ELSE /
    # TO / STEP / OFF / USING can never be first in valid BASIC -- so on the obvious
    # spelling they could never be attributed at all, however well they work. The
    # crunch body is CRUNCHED AND NEVER EXECUTED (see the header contract), so these
    # rows put the particle first in the crunch -- which is exactly what Layer 1 is
    # for, checking that the word tokenises -- while the exec line drives it in real
    # syntax. `then a=1` crunches; `IF 2>1 THEN PRINT"[3]"` is what runs.
    # ⚠️ RND IS SCORED FOR EXISTENCE AND RANGE, NOT FOR ITS SEQUENCE. `RND(1)<1` is
    # true on any conforming implementation and false on a stub (an absent RND parses
    # as a variable, making `RND(1)` a subscript). Whether zerobas's PRNG SEQUENCE
    # matches the reference's is a separate question this row does not ask, and
    # filing it as answered here would be the "agrees for the wrong reason" trap.
    ("rnd",     'a=rnd(1)',           'PRINT"[";RND(1)<1;"]"',                "direct", "D-KWDRAIN"),
    ("cvi",      'a=cvi("ab")',        'PRINT"[";CVI(MKI$(7));"]"',              "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 7. 🔴 TAGGED AFTER THE FACT: "
     "written untagged it came back EXTRA -- ref `Illegal function call` vs zb "
     "`[ 7 ]` -- which is EXACTLY the mis-attribution this file's header "
     "describes, a diskless VG-8020 measured against zerobas's disk-equipped "
     "build and the difference blamed on zerobas. The rest of the MK/CV family "
     "was already tagged; this row simply had not been."),
    ("using",   'using "##"',         'PRINT USING"##";7',                    "direct", "D-KWDRAIN"),
    ("then",    'then a=1',           'IF 2>1 THEN PRINT"[3]"',               "direct", "D-KWDRAIN"),
    ("elsekw",  'else a=1',           'IF 0 THEN PRINT 1 ELSE PRINT"[8]"',    "direct", "D-KWDRAIN"),
    ("tokw",    'to 5',               'FOR I=1 TO 3:NEXT:PRINT"[";I;"]"',     "direct", "D-KWDRAIN"),
    ("stepkw",  'step 2',             'FOR I=1TO5STEP2:NEXT:PRINT"[";I;"]"',  "direct", "D-KWDRAIN"),
    ("offkw",   'off',                'INTERVAL OFF:PRINT"[9]"',              "direct", "D-KWDRAIN"),
    ("ifkw",    'if 1 then a=2',      'IF 3>2 THEN PRINT"[4]"',               "direct", "D-KWDRAIN"),
    ("nextkw",  'next i',             'FOR I=1 TO 2:NEXT:PRINT"[";I;"]"',     "direct", "D-KWDRAIN"),
    ("clearkw", 'clear 100',          'CLEAR 100:PRINT"[5]"',                 "direct", "D-KWDRAIN"),
    ("dimkw",   'dim a(2)',           'DIM D(2):D(1)=5:PRINT"[";D(1);"]"',    "direct", "D-KWDRAIN"),

    # ------------------------------------------------ D-KWDRAIN batch 3 (2026-09-12)
    # The raw-I/O and sound words. Every exec here is chosen to leave the SCREEN
    # ALONE: this sweep anchors its capture on the echoed command, and the `locate`
    # row above is the standing proof that a feature which moves or clears the
    # display destroys the probe's own anchor. So no CLS, no SCREEN, no COLOR and no
    # WIDTH in this batch -- those need their own handling, not a hopeful row.
    # ⚠️ THE WRITES ARE DELIBERATELY AIMED AT HARMLESS TARGETS: VRAM 0 is the glyph
    # for character 0, `OUT &HA0` selects a PSG register without writing one,
    # `SOUND 7,255` is the mixer with every channel OFF, `WAIT &HA9,0` masks to zero
    # so the condition is true immediately and cannot hang, and the POKE goes to
    # -8192 ($E000), inside zerobas's own RAM rather than the work area.
    # 🎯 EACH ONE READS BACK WHAT IT WROTE where it can (VPOKE/VPEEK, POKE/PEEK), so
    # a stub that silently accepts the statement still fails the row.
    ("beep",    'beep',               'BEEP:PRINT"[6]"',                      "direct", "D-KWDRAIN"),
    ("sound",   'sound 7,255',        'SOUND 7,255:PRINT"[7]"',               "direct", "D-KWDRAIN"),
    ("vpeek",   'a=vpeek(0)',         'VPOKE 0,7:PRINT"[";VPEEK(0);"]"',      "direct", "D-KWDRAIN"),
    ("vpoke",   'vpoke 0,1',          'VPOKE 0,9:PRINT"[";VPEEK(0);"]"',      "direct", "D-KWDRAIN"),
    ("vdpkw",   'a=vdp(1)',           'PRINT"[";VDP(1)>0;"]"',                "direct", "D-KWDRAIN"),
    # 🔴 `>0`, NOT `>=0`, AND THAT IS A FIX TO MY OWN ROW. The first cut asked
    # `INP(&HA8)>=0`, which an ABSENT INP passes too: the word would parse as an
    # undefined array, `INP(&HA8)` would be element 0, and `0>=0` is TRUE.
    # Measured (scratchpad/kwdrain_boolcheck.py): INP(&HA8) reads 240, the stub
    # shape ZZQ(0)>=0 reads -1 -- identical to the real answer. `>0` separates
    # them, because the stub gives 0. The VALUE itself cannot be asserted: &HA8
    # is the primary slot register and its content is a machine-layout fact, so
    # zerobas and the VG-8020 may legitimately differ. `vdpkw` was checked the
    # same way and is sound as written: VDP(1) reads 240 against the stub's 0.
    ("inpkw",   'a=inp(168)',         'PRINT"[";INP(&HA8)>0 ;"]"',            "direct", "D-KWDRAIN"),
    ("outkw",   'out 160,7',          'OUT &HA0,7:PRINT"[8]"',                "direct", "D-KWDRAIN"),
    # 🔴 `WAIT` HAS NO ROW HERE, AND THE FIRST ATTEMPT IS WHY. `WAIT port,mask
    # [,xor]` blocks until ((INP(port) XOR xor) AND mask) <> 0, so a mask of 0 can
    # NEVER be satisfied: the row `WAIT &HA9,0:PRINT"[9]"` -- written believing
    # mask 0 meant "already true" -- blocks for ever BY DEFINITION, and zerobas
    # returning no output was it behaving CORRECTLY. Attributing WAIT needs a port
    # whose condition is satisfiable without blocking, and the obvious candidate
    # (the VDP status port, whose bit 7 sets every frame) is read-to-clear and
    # would disturb the BIOS interrupt handler. Left unattributed on purpose --
    # "no known gap" is the honest state for it until a safe row exists.
    ("pokekw",  'poke 0,1',           'POKE-8192,7:PRINT"[";PEEK(-8192);"]"', "direct", "D-KWDRAIN"),

    # ---------------------------------------------- D-KWDRAIN step 4a (2026-09-12)
    # 🔴 A CORRECTION TO WHAT BATCH 3 FILED. I wrote that the display verbs "cannot
    # take a kwsweep row at all" because they destroy the echo this sweep anchors
    # on. That was the ANCHOR's limit, not the words': `marker_tail` above captures
    # from a unique per-row marker instead, which is what the arrays and deffn
    # suites have always done with `CLS:PRINT"[";...`. So the words come back in
    # reach, and the claim is retracted where it was made.
    ("widthkw", 'width 37',    'WIDTH 37:PRINT"[W";PEEK(-3152);"]"',  "direct",
     "NOECHO:[W WIDTH reformats the screen and takes the echo with it; the row reads LINLEN ($F3B0 = -3152) back, so a WIDTH that parses and does nothing still fails. absent => syntax error => no marker at all."),
    # 🔴 `KEY` HAS NO ROW, AND THE ATTEMPT THAT PASSED IS WHY. A `keykw` row
    # reading CRTCNT ($F3B1) after `KEY OFF` came back SUPPORTED / match on both
    # machines -- and it was BLIND. Measured directly
    # (scratchpad/kwdrain_keyblind.py): CRTCNT reads 24 with KEY OFF and 24
    # WITHOUT it, on zerobas AND on the VG-8020, so a KEY that parsed and did
    # nothing would have passed the row identically. A green verdict is not
    # evidence that the readback MOVES [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    # The honest readback is the function-key buffer, but FNKSTR is not declared
    # in basic/sysvars.inc and the standard $F87F would be an unverified
    # constant. KEY stays unattributed until one of those is settled.

    # ---------------------------------------------- D-KWDRAIN step 4c (2026-09-12)
    # The graphics verbs, reachable at last. Two things had to combine: the
    # echo-free capture above (SCREEN 0/2 destroys the echo), and doing the READBACK
    # BEFORE returning to text mode -- a SCREEN 2 screen cannot be read as 40-column
    # text at all, so the row draws, reads POINT into a variable, goes back to
    # SCREEN 0 and only then prints its marker.
    # 🎯 THE READBACK IS MEASURED FIRST, as the standard now requires
    # (scratchpad/kwdrain_gfxcheck.py, both machines agreeing): POINT reads 4 on a
    # blank SCREEN 2, 15 after `PSET ,15`, and 4 again after PRESET. So each row
    # below moves when its own verb stops working, rather than passing on a value
    # that was already there.
    # ⚠️ PSET AND POINT ARE COUPLED and the rows say so: POINT can only read what
    # something drew, so `pointkw` moves if EITHER breaks. It is still worth a row --
    # a POINT that parses as an array reads 0, which neither 4 nor 15 can be.
    # ---------------------------------------------- D-KWDRAIN step 4d (2026-09-12)
    # 🎯 EVERY READBACK BELOW WAS MEASURED BEFORE THE ROW WAS WRITTEN
    # (scratchpad/kwdrain_gfx2.py, both machines agreeing), and the measurement
    # changed two of them:
    #   CIRCLE  rim POINT(60,50) = 15 while the CENTRE reads 4 -- so the row sees a
    #           real circle and not a filled blob.
    #   DRAW    POINT(14,10) = 15 after `C15R5` from (10,10); blank is 4.
    #   BASE    BASE(2) = 2048 and BASE(10) = 6144 -- but 🔴 BASE(0) IS 0, which is
    #           exactly what a stub returns, so the obvious argument would have made
    #           a BLIND row. The row uses BASE(2).
    # 🟢 SPRITE'S NO-OUTPUT WAS DIAGNOSED, NOT GUESSED AT
    # (scratchpad/kwdrain_spritechk.py): `SPRITE$(0)=...` raises ILLEGAL FUNCTION
    # CALL in SCREEN 0 -- sprites need a graphics screen -- which is why the first
    # form printed nothing at all. In SCREEN 2 the round-trip works: ASC reads back
    # 255 and LEN reads 8. The row below therefore writes the pattern to VRAM and
    # reads it back through SPRITE$, so it moves if either half stops working.
    ("circlekw",  'circle(50,50),10', 
     'SCREEN2:CIRCLE(50,50),10,15:A=POINT(60,50):SCREEN0:PRINT"[Q";A;"]"', "stored",
     "NOECHO:[Q rim pixel is 15, centre is 4 -- a filled or absent circle fails"),
    ("drawkw",    'draw"c15r5"',      
     'SCREEN2:PSET(10,10),15:DRAW"C15R5":A=POINT(14,10):SCREEN0:PRINT"[D";A;"]"', "stored",
     "NOECHO:[D reads 4 pixels right of the start: blank is 4, drawn is 15"),
    # 🔴 THE CRUNCH IS `sprite on`, NOT `sprite$(0)=...`, AND THE FIRST CUT TAUGHT
    # ME WHY. tier_table's WORD regex keeps a trailing `$` (so STR$ and MID$ match),
    # which makes `sprite$(0)="x"` tokenise to SPRITE$ -- and the kwtable keyword is
    # SPRITE. The row reported SUPPORTED and credited NOTHING: four rows went in and
    # the evidence count rose by three. `sprite on` names SPRITE first and is real
    # BASIC besides.
    ("spritekw",  'sprite on',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):A=ASC(SPRITE$(0)):SCREEN0:PRINT"[Z";A;"]"',
     "stored",
     "NOECHO:[Z writes the pattern to VRAM and reads it back: 255 round-trips, "
     "a stub reads 0 and SCREEN 0 raises Illegal function call"),
    ("basekw",    'a=base(2)',         'PRINT"[";BASE(2);"]"',               "direct", "D-KWDRAIN"),

    # ---------------------------------------------- D-KWDRAIN step 4e (2026-09-12)
    # 🎯 THE MULTI-LINE WORDS, AND THEY WERE NEVER BLOCKED EITHER. `as_stored`
    # SPLITS a `:`-joined line into numbered lines 10/20/... , packing statements
    # greedily into <=34-char bodies -- so a "one-line" exec is already a
    # multi-line program, and GOSUB/RETURN/READ/RESTORE only needed the line
    # numbers to be worked out rather than guessed. Verified by printing the
    # packing before writing a row, and by running it (scratchpad/
    # kwdrain_multiline.py, both machines): `A=0:GOSUB 20:...:END:A=7:RETURN`
    # packs to `10 A=0:GOSUB 20:PRINT...:END` / `20 A=7:RETURN` and answers 7.
    # 🔴 THE CONTROL IS WHAT MAKES THE RESTORE ROW MEAN ANYTHING: a single
    # `READ Q` answers 3, and the row answers 6 -- so the second READ really did
    # re-read the same DATA, which is only true if RESTORE reset the pointer.
    # ⚠️ `ON` IS NOT HERE: its two-target form packs badly -- the greedy packer
    # swallows both subroutines into line 20 -- and padding statements to force a
    # boundary would make the row about the packer instead of the keyword.

    # ---------------------------------------------- D-KWDRAIN step 4f (2026-09-12)
    # The error-handling cluster, four keywords off ONE program: line 10 arms the
    # handler and raises, line 20 reports. Measured on both machines before the rows
    # were written (scratchpad/kwdrain_errhand.py): ERR reads 7 and ERL reads 10, so
    # the row carries the CODE and the LINE, not just "something was trapped".
    # 🎯 RESUME NEEDED ITS OWN PROGRAM, and the packer decided its shape: the greedy
    # split puts the handler alone on line 30 as `RESUME NEXT`, which resumes at the
    # statement after the one that raised -- the PRINT on line 20. So the row prints
    # at all ONLY because RESUME returned control; drop RESUME and the program ends
    # in the handler with nothing on screen.
    # ⚠️ DEFINT's row asserts 1, NOT 1.7: a DEFINT that parses and does nothing would
    # still print 1.7, so the row sees the COERCION rather than the parse.

    # ---------------------------------------------- D-KWDRAIN step 4g (2026-09-12)
    # 🎯 TWO WORDS THAT SEPARATE THROUGH AN ERROR, WHICH IS STILL A DIFFERENTIAL.
    # Measured on both machines first (scratchpad/kwdrain_misc1.py):
    #   MAX bare      -> Syntax error on a real machine, `0` on a stub (an unknown
    #                    word is just a variable), so the row proves MAX is TOKENISED
    #                    rather than parsed as a name.
    #   STRIG(5)      -> Illegal function call (the valid range is 0..4), while an
    #                    undefined array STRIG(5) auto-dims and answers 0.
    # ⚠️ AND THREE THAT DO NOT SEPARATE, left unattributed rather than papered over:
    #   LPOS(0) reads 0 and a stub reads 0; LPRINT produced NO OUTPUT AT ALL on both
    #   machines (no printer attached), so neither can be scored from here; and
    #   LEN(INKEY$) is 0 with no key pressed, which is exactly what a stub returns.
    #   INKEY$ needs injected keystrokes, not a cleverer expression.

    # ---------------------------------------------- D-KWDRAIN step 4h (2026-09-12)
    # More words that separate through an ERROR, each measured on both machines
    # first (scratchpad/kwdrain_misc2.py). ATTR$ is the interesting one: bare use
    # raises ILLEGAL FUNCTION CALL rather than a Syntax error, which settles the
    # open question of whether it is an MSX1 BASIC token at all -- it is.
    # 🔴 `NEW` GOT NO ROW BECAUSE IT GOT AN ITEM: `10 NEW` + RUN is
    # `Syntax error in 10` here and `Ok` on the VG-8020, with `CLEAR` in the same
    # position accepted on both. That is filed as a TIER 1 defect in TODO.md, which
    # attributes the keyword far better than a permanently-divergent row would.
    # ⚠️ PDL IS STILL OUT: PDL(13) raises Illegal function call, but the STUB shape
    # also errors there (subscript out of range), so the two separate only by error
    # PHRASE. PDL(0) should separate cleanly -- measure it before writing the row.
    ("padkw",     'a=pad(0)',    'PRINT"[";PAD(9);"]"',     "direct",
     "D-KWDRAIN: 9 is outside PAD's range -> Illegal function call; an undefined array auto-dims to 10 and answers 0"),
    ("attrkw",    'a$=attr$',    'PRINT"[";ATTR$;"]"',      "direct",
     "D-KWDRAIN: bare ATTR$ raises Illegal function call -- so the word IS a token here; an undefined string variable prints empty instead"),
    ("stopkw",    'stop',        'PRINT"[T1]":STOP',        "stored",
     "D-KWDRAIN: prints then Break in 10 on both machines; without STOP there is no Break"),
    ("maxkw",     'max',               'PRINT"[";MAX;"]"',                     "direct",
     "D-KWDRAIN: bare MAX is a Syntax error on a real machine; a stub prints 0"),
    ("strigkw",   'a=strig(0)',        'PRINT"[";STRIG(5);"]"',                "direct",
     "D-KWDRAIN: 5 is out of STRIG's 0..4 range -> Illegal function call; an "
     "undefined array auto-dims and answers 0"),
    ("onkw",      'on error goto 20', 
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: ON in its ON ERROR form"),
    ("errorkw",   'error 7',          
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: ERROR 7 is what raises it"),
    ("errkw",     'a=err',            
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: ERR reads 7, the code raised"),
    ("erlkw",     'a=erl',            
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: ERL reads 10, the line that raised"),
    ("resumekw",  'resume next',      
     'ON ERROR GOTO 30:ERROR 7:PRINT"[U";A;"]":END:A=5:RESUME NEXT', "stored", "D-KWDRAIN: the handler RESUMEs NEXT and control reaches the PRINT; without it nothing prints"),
    ("defintkw",  'defint a',         
     'DEFINT A:A=1.7:PRINT"[";A;"]"',                           "direct", "D-KWDRAIN: 1, not 1.7 -- a DEFINT that parses and does nothing still prints 1.7"),

    # ---------------------------------------------- D-KWDRAIN step 4i (2026-09-12)
    # 🔴 NEW GETS A ROW *BECAUSE ITS DEFECT WAS FIXED*, which is not as odd as it
    # sounds. Attribution comes from OPEN items, so the moment D-NEWSTMT closed, the
    # keyword fell straight back into "no known gap" -- the table cannot tell
    # "investigated and now correct" from "nobody ever looked". A row is what holds
    # the ground a fix won.
    # The exec is the defect's own shape: before the fix it printed [A] and then
    # `Syntax error in 10`; now it prints [A] and stops, like the reference.
    ("newkw",     'new',
     'PRINT"[A]":NEW',                                       "stored",
     "D-KWDRAIN: the D-NEWSTMT shape -- [A] then a clean stop; before the fix "
     "this row would have carried `Syntax error in 10` on the zb side"),
    ("gosubkw",   'gosub 20',     
     'A=0:GOSUB 20:PRINT"[G";A;"]":END:A=7:RETURN',         "stored", "D-KWDRAIN: the subroutine sets A=7; no GOSUB, no output"),
    ("returnkw",  'return',       
     'A=0:GOSUB 20:PRINT"[H";A;"]":END:A=7:RETURN',         "stored", "D-KWDRAIN: A is 7 only because RETURN came back to the PRINT"),
    ("endkw",     'end',          
     'A=0:GOSUB 20:PRINT"[J";A;"]":END:A=7:RETURN',         "stored", "D-KWDRAIN: END keeps the subroutine from being fallen into"),
    ("readkw",    'read q',       
     'READ Q:RESTORE:READ R:PRINT"[E";Q+R;"]":END:DATA 3',  "stored", "D-KWDRAIN: reads 3 from the DATA on the second line"),
    ("restorekw", 'restore',      
     'READ Q:RESTORE:READ R:PRINT"[F";Q+R;"]":END:DATA 3',  "stored", "D-KWDRAIN: 6 needs the pointer RESET: without RESTORE the second READ runs out of DATA"),
    ("psetkw",   'pset(1,1)',      
     'SCREEN2:PSET(1,1),15:A=POINT(1,1):SCREEN0:PRINT"[S";A;"]"',   "stored",
     "NOECHO:[S PSET draws, POINT reads it back: 4 blank vs 15 drawn"),
    ("presetkw", 'preset(1,1)',    
     'SCREEN2:PSET(1,1),15:PRESET(1,1):A=POINT(1,1):SCREEN0:PRINT"[R";A;"]"', "stored",
     "NOECHO:[R PRESET must UNDO the PSET: 15 if it does nothing, 4 if it works"),
    ("pointkw",  'a=point(1,1)',   
     'SCREEN2:PSET(1,1),15:A=POINT(1,1):SCREEN0:PRINT"[T";A;"]"',   "stored",
     "NOECHO:[T POINT as the subject: a stub parses as an array and reads 0, not 15"),
    ("linekw",   'line(1,1)-(5,1)',
     'SCREEN2:LINE(1,1)-(5,1),15:A=POINT(3,1):SCREEN0:PRINT"[L";A;"]"', "stored",
     "NOECHO:[L reads a pixel in the MIDDLE of the span, so an endpoint-only LINE fails too"),
    ("colorkw",  'color 7',    'COLOR 7:PRINT"[O";PEEK(-3095);"]"',              "direct",
     "NOECHO:[O COLOR repaints the whole screen, echo included. Reads FORCLR "
     "($F3E9 = -3095) back, and uses 7 rather than the DEFAULT 15 on purpose: "
     "a COLOR that parsed and did nothing would leave 15 there and the row "
     "would pass on the default. absent => syntax error, no marker."),
    # ⚠️ `SCREEN` AND `KEY` ARE NOT HERE YET, each for a stated reason rather
    # than an oversight. SCREEN: the only value that discriminates is a mode
    # CHANGE, and `SCREEN 1` is 32 columns while this capture parses a 40-column
    # screen -- the row would break the reader it depends on. KEY: the natural
    # readback is the function-key buffer, whose address (FNKSTR) is NOT in
    # basic/sysvars.inc, and guessing the standard $F87F would be building on an
    # unverified constant. Both need a measurement first.
    ("clskw",    'cls',        'CLS:PRINT"[C";CSRLIN;"]"',            "direct",
     "NOECHO:[C CLS erases the echo by definition -- the exact row the old "
     "echo-anchored capture could never hold. 🔴 AND IT READS CSRLIN BACK ON "
     "PURPOSE: the first cut printed a bare [C1], which a CLS that PARSED AND "
     "DID NOTHING would have printed just as happily -- scoring the parse and "
     "calling it the behaviour. After a real CLS the cursor is home, so the "
     "row reads 0; leave the screen alone and it reads wherever the echo left "
     "it. absent => syntax error, no marker at all."),

    # -------------------------------------------------- suspected MISSING words
    # Console / cursor. All three fail the same way if absent: the word parses as
    # a numeric variable (0) or an array, so the probe must make 0 the WRONG
    # answer rather than a plausible one.
    # COLUMN ONLY, not `LOCATE 10,0`. The first design used row 0 — and on the
    # reference the feature under test then MOVED THE CURSOR ONTO THE ECHOED
    # COMMAND and overprinted it, so screen_tail could not find the echo and the
    # reference row came back ?noecho/UNREADABLE. The probe was destroying its own
    # anchor. `LOCATE 10` keeps output on the current row, just indented.
    ("locate",  "locate 10,0",
     'LOCATE 10:PRINT"[X]"',                         "direct",
     "absent => `LOCATE 10` is a bare word + juxtaposition => syntax error; "
     "real => `[X]` indented to column 10"),
    ("csrlin",  "a=csrlin",
     # ⚠️ THIS ROW'S "DIVERGENT" IS A PROBE ARTIFACT, NOT A FAITHFULNESS BUG,
     # and it cannot be pinned here. CSRLIN is a POSITION, so with no leading
     # CLS the row reports wherever the boot banner and the batch's own
     # scrolling left the cursor. Measured: unpinned it reads ref 4 vs zb 3 in
     # this batch and ref 9 vs zb 7 in a differently scrolled one -- the
     # REFERENCE disagreeing with itself is the proof that the row is reading
     # ambient state. Prefix `CLS:` and both machines answer 2, with or without
     # a WIDTH pin.
     #
     # But CLS cannot be used HERE: this probe's readout anchors on the typed
     # ECHO, and CLS erases it -- the row then reads '' on both sides and
     # classifies UNREADABLE, which is strictly worse than a divergence you can
     # explain (tried, 2026-07-27). The two requirements are incompatible for
     # this one row, so it stays unpinned and stays explained.
     #
     # CSRLIN itself is CORRECT and properly gated elsewhere: cursor-acceptance
     # 67/67 covers it at a pinned WIDTH 40 + CLS across six cases
     # (docs/cursor-vg8020-characterization.md §2). Treat this row as evidence
     # that CSRLIN is PRESENT, never as evidence about its value.
     #
     # 🟢 SO IT IS NOW SCORED **WEAK**, WHICH IS WHAT THE PARAGRAPH ABOVE HAS
     # BEEN ARGUING FOR WITHOUT USING THE WORD (D-WAITGAP, 2026-09-07). A row
     # that is evidence of PRESENCE and never of VALUE is this probe's own
     # definition of WEAK, and `time` already uses it. The cost of leaving it
     # DIVERGENT was not cosmetic: the sweep read `DIVERGENT=1` permanently, so
     # the headline could not move if CSRLIN ever really broke, and a count that
     # is always 1 teaches its readers to skip it.
     'PRINT:PRINT:PRINT"[";CSRLIN;"]"',              "direct",
     "WEAK: absent => variable CSRLIN reads 0; real => the (non-zero) cursor "
     "row -- but the VALUE is ambient scroll state, so only the non-zero-ness "
     "is a reading. Scored WEAK for the reason the block above gives, and "
     "measured 2026-09-07 (D-WAITGAP, scratchpad/csrlin_probe.py): on THIS row "
     "the two REFERENCES disagree with EACH OTHER -- vg8020 11, cf3300 8, zb 10 "
     "-- in one batch, so it cannot score anything by construction. Anchored "
     "with CLS all three agree everywhere (CLS 0/0/0, CLS:PRINT 1/1/1, "
     "CLS:PRINT:PRINT 2/2/2) and CSRLIN is correct: LOCATE 0,5 -> 5, 0,10 -> 10, "
     "0,0 -> 0 on all three, which is the decisive form because a set row admits "
     "no scroll history."),
    ("pos",     "a=pos(0)",
     'PRINT"    ";:PRINT"[";POS(0);"]"',             "direct",
     "absent => array POS(0) auto-dims to 0; real => the (non-zero) column"),

    # The two PRINT-item pseudo-functions. THE `TAB(` TRAP: with TAB absent,
    # `PRINT TAB(5);"X"` prints ` 0 X` (array element 0 then X) instead of
    # padding to column 5 — so compare the TEXT, and never a bare error code.
    ("tab",     'print tab(5);"x"',
     'PRINT"[";TAB(5);"X]"',                         "direct",
     "absent => array TAB(5)=0 prints ` 0 `; real => pad to column 5"),
    ("spc",     'print spc(5);"x"',
     'PRINT"[";SPC(5);"X]"',                         "direct",
     "absent => array SPC(5)=0 prints ` 0 `; real => 5 spaces"),

    # Program / editor management.
    ("swap",    "swap a,b",
     'A=1:B=2:SWAP A,B:PRINT"[";A;B;"]"',            "direct",
     "absent => syntax error; real => ` 2  1 `"),
    ("fre",     "a=fre(0)",
     'PRINT"[";FRE(0)>1000;"]"',                     "direct",
     "absent => array FRE(0)=0 => `0` (false); real => -1 (true)"),
    ("tron",    "tron",
     "TRON:TROFF:PRINT\"[ok]\"",                     "direct",
     "absent => syntax error; real => accepted (trace toggled off again)"),
    ("troff",   "troff",
     'TROFF:PRINT"[ok]"',                            "direct",
     "absent => syntax error"),
    ("renum",   "renum",
     None,                                           "direct",
     "renumbers the stored program; harmless but needs a program to be visible"),
    ("delete",  "delete 10",
     None,                                           "direct",
     "deletes stored lines — would eat the batch's own program"),
    ("auto",    "auto",
     None,                                           "direct",
     "INTERACTIVE: enters auto-line-number mode and swallows all following input"),

    # D-DEFTYPETOK (2026-08-19): DEFSNG/DEFDBL/DEFSTR now have whole-word
    # kwtable.inc rows and single-byte tokens of their own ($AD/$AE/$AB, beside
    # DEFINT's $AC from D-DEFINTTOK), so they TOKENISE and reach ex_deftype
    # (basic/usr.asm) as one byte each. The DEF_TOKEN + literal ASCII mechanism
    # they used to arrive by is gone, and so is ex_def_type (merged into
    # ex_deftype). Until then they were the one family where "absent from the
    # keyword table" was expected AND support was expected — the INTERVAL
    # shape, in-tree, flagged by this probe's own coverage audit as a blind spot.
    # They are ordinary tokenising rows now; the three cases below are kept
    # because they gate the BEHAVIOUR, which is what they always gated.
    ("defsng",  "defsng a",
     'DEFSNG A:A=1.5:PRINT"[";A;"]"',                "direct", "control"),
    ("defdbl",  "defdbl a",
     'DEFDBL A:A=1.5:PRINT"[";A;"]"',                "direct", "control"),
    ("defstr",  "defstr a",
     'DEFSTR A:A="x":PRINT"[";A;"]"',                "direct", "control"),

    # User-defined functions.
    # STORED, not direct: the reference answers `Illegal direct` to a direct-mode
    # DEF FN — measured, first run of this sweep. So the direct form tests the
    # direct-mode restriction, not the feature.
    ("deffn",   "def fna(x)=x+1",
     'DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"',           "stored",
     "absent => syntax error; real => 3"),

    # The two missing logical operators.
    ("eqv",     "a=5 eqv 3",
     'PRINT"[";5 EQV 3;"]"',                         "direct",
     "absent => juxtaposition syntax error; real => -7"),
    ("imp",     "a=5 imp 3",
     'PRINT"[";5 IMP 3;"]"',                         "direct",
     "absent => juxtaposition syntax error; real => -5"),

    # Printer surface. The LPTOUT device layer ships (zerobas-tape page-0 patch),
    # so a divergence here is statement-surface only. Printer is UNPLUGGED in the
    # harness by default and LSTOUT is NOT hang-safe unplugged (openmsx-printer-
    # pluggable), so these are crunch-only — executing LPRINT could wedge the run.
    ("lprint",  'lprint"x"',   None, "direct", "LSTOUT not hang-safe with no printer plugged"),
    ("llist",   "llist",       None, "direct", "same LSTOUT hazard"),
    ("lpos",    "a=lpos(0)",   None, "direct", "same LSTOUT hazard"),

    # Cassette / misc statements.
    ("motor",   "motor on",
     'MOTOR OFF:PRINT"[ok]"',                        "direct",
     "absent => syntax error; MOTOR OFF is the safe direction"),
    # KEPT DELIBERATELY, AND KEPT WEAK. This row is the TAB( mistake reproduced
    # on purpose: `TIME>=T` is `0>=0` on a machine with no TIME at all, so BOTH
    # sides answer -1 and the row reports SUPPORTED for a feature that does not
    # exist. It is the in-tree demonstration that a passing differential case
    # proves nothing unless the absent-feature parse gives a DIFFERENT answer.
    # WEAK: rows are excluded from the tally and flagged in the report.
    ("time",    "time=0",
     'T=TIME:PRINT"[";TIME>=T;"]"',                  "direct",
     "WEAK: absent => variable TI, always 0, and `0>=0` is STILL true, so this "
     "row passes on a machine with no TIME. The `timetick` row is the real test."),
    # STORED mode, not direct: the line is 46 chars, so its prompt echo wraps
    # across two 40-column rows and screen_tail's echo match fails -> ?noecho ->
    # UNREADABLE. In stored mode the echoed command is just "RUN". (Caught by the
    # MAX_DIRECT_ECHO guard below, which exists so this cannot recur silently.)
    ("timetick", "a=time",
     'T=TIME:FOR I=1 TO 400:NEXT:PRINT"[";TIME>T;"]"', "stored",
     "THE discriminator: a real TIME advances across a delay loop; the variable "
     "`TI` does not. This is the row that catches the silent gap."),

    # INTERVAL — the retraction case. It is NOT a keyword on either side (it is
    # INT+"ER"+VAL), so CRUNCH is expected to MATCH while SUPPORT is expected to
    # differ. Any probe design that reports this row as "fine" is broken.
    ("interval", "interval on",
     None,                                           "direct",
     "needs a stored ON INTERVAL=n GOSUB program + a timed window; covered by "
     "probes/basic/basic_probe_interval_trap.py (T5 slice), not duplicated here"),

    # Random-access float conversions (the MKI$/CVI integer pair ships).
    # MKI$ is the FAMILY CONTROL: the first run had the reference answering
    # `Illegal function call` to `LEN(MKS$(1))`, which could mean either "MKS$
    # needs Disk BASIC on this diskless VG-8020" or "my expression is wrong".
    # MKI$ is implemented on BOTH sides, so it separates those two readings.
    ("mki",     'a$=mki$(1)',   'PRINT"[";LEN(MKI$(1));"]"',  "direct",
     "NEEDS-DISK: " "control for the MK/CV family — MKI$ ships in zerobas"),
    ("mks",     'a$=mks$(1)',   'PRINT"[";LEN(MKS$(1));"]"',  "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 4"),
    ("mkd",     'a$=mkd$(1)',   'PRINT"[";LEN(MKD$(1));"]"',  "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 8"),
    ("cvs",     'a=cvs("abcd")', 'PRINT"[";CVS(MKS$(1));"]"', "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 1"),
    ("cvd",     'a=cvd("abcdefgh")', 'PRINT"[";CVD(MKD$(1));"]"', "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 1"),

    # Disk-BASIC surface. Sector I/O and the destructive/interactive ones are
    # crunch-only ON PURPOSE — see SKIP_EXEC.
    ("dski",    'a$=dski$(0,0)', None, "direct", "NEEDS-DISK: " "raw sector READ — needs a disk, out of scope here"),
    ("dsko",    "dsko$0,0",      None, "direct", "NEEDS-DISK: " "raw sector WRITE — DESTRUCTIVE, never executed"),
    ("copy",    'copy"a:x"to"a:y"', None, "direct", "NEEDS-DISK: " "file copy — needs a disk fixture"),
    ("set",     'set password',  None, "direct", "NEEDS-DISK: " "Disk-BASIC SET — needs a disk fixture"),
    ("attr",    'a$=attr$(0)',   None, "direct", "NEEDS-DISK: " "MSX-DOS2-era; measured for the record"),
    ("ipl",     "ipl",           None, "direct", "NEEDS-DISK: " "boot-sector write — DESTRUCTIVE, never executed"),
    ("cmd",     'cmd"x"',        None, "direct", "vendor hook; unknown side effects"),
    ("lfiles",  "lfiles",        None, "direct", "NEEDS-DISK: " "printer-bound (LSTOUT hazard); tracked in TODO"),
    ("loc",     "a=loc(1)",      None, "direct", "NEEDS-DISK: " "needs an open channel; tracked in TODO §File-position"),
    ("bin",     "a$=bin$(5)",
     'PRINT"[";BIN$(5);"]"',                         "direct",
     "absent => syntax error; real => 101"),

    # WAIT: `WAIT p,a` spins until ((INP(p) XOR x) AND a) <> 0 — with the wrong
    # operand it NEVER RETURNS and wedges the whole batch. Crunch-only.
    ("wait",    "wait 0,0",      None, "direct", "can spin forever — never executed in a batch"),

    # Keyboard INPUT$(n) — blocks for n keypresses. Crunch-only; the channel form
    # INPUT$(n,#f) already ships.
    ("inputdol", 'a$=input$(1)', None, "direct", "BLOCKS waiting for a keypress"),
]

# Rows deliberately not executed, with the reason surfaced in the report. Named
# explicitly so a reader can audit the exclusions instead of inferring them from
# a silent absence (no-silent-caps).
SKIP_EXEC = {k for k, _, ex, _, _ in SWEEP if ex is None}

# --------------------------------------------------------------------------
# --- CRUNCH_DIFF_PINNED: the keywords zerobas does not tokenise ------------
# 🔴 UNTIL 2026-09-07 THE CRUNCH LAYER SCORED NOTHING AT ALL. `main()`
# returned 0 unless the ROMs moved mid-run or the CONTROL GROUP failed, so this
# file — collected by `make gates`, green in the 114/114 battery of that morning
# — printed EIGHT words the reference tokenises and zerobas does not, and exited
# 0. Layer 1's states are SAME/DIFF; `MISSING` is a LAYER 2 state, and all eight
# are crunch-only rows that Layer 2 never runs. **A word absent from
# `kwtable.inc` that is also crunch-only was structurally incapable of being
# scored** [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
#
# 🎯 AND THE "NO-ORACLE" REASONING DOES NOT REACH THIS LAYER. The rows are
# tagged NEEDS-DISK because their SUPPORT oracle is a disk-equipped reference;
# the probe declines to attribute a support difference to zerobas. Tokenising
# needs no disk. The reference's bytes are right there, the difference is
# unambiguous (a single token vs the raw ASCII of a variable name), and it IS
# attributable.
#
# The values are ORACLE-SOURCED — read out of the reference's own program area by
# this probe's Layer 1, the same provenance as every token in kwtable.inc.
# 🟢 ATTR$ ($E9) LEFT THIS SET on 2026-09-08 too (D-ATTRFN) — the same class, but
# a FUNCTION, so its handler is an `ev_f` arm and not a stmt_table row. Measured on
# four sides: `PRINT ATTR$` / `A$=ATTR$` / `A$=ATTR$(0)` are ERR 5 and `ATTR$="Z"`
# is ERR 2, both references agreeing, and zerobas now matches all four.
# 🟢 SET ($D2), IPL ($D5) and CMD ($D7) LEFT THIS SET on 2026-09-08 (D-DONOTHING3):
# zerobas now crunches all three and dispatches them to `gb_illegal`, so they read
# SAME. A pinned row that stops diverging is a STALE PIN and this probe returns 5
# on one, which is what removing them here answers.
# 🔴 AND THEY WERE NEVER DISK-BASIC WORDS. This block sat under a Disk-BASIC
# heading and the fix was filed as needing a disk-equipped oracle; measured, the
# DISKLESS VG-8020 answers ERR 5 to `SET`, `IPL`, `CMD` AND to `SET=1` -- so all
# three are reserved in plain MSX BASIC and the VG-8020 is a perfectly good oracle
# for them (scratchpad/donothing_probe.py, four sides).
CRUNCH_DIFF_PINNED = {
}
# 🎯 `LFILES` IS THE CONTROL THAT MAKES THIS A LIST AND NOT A CLASS: it is
# a Disk-BASIC word too, it IS in kwtable.inc, and it crunches SAME. So "zerobas
# omits Disk BASIC's keywords" is not the finding — these eight specific words
# are.


# 🔴 EVERY ENTRY MUST STAY LOWERCASE. `classify` below does `low = tail.lower()`
# and then `phrase in low`, so a capitalised entry can NEVER match -- it does not
# fail loudly, it silently reclassifies that row from `error:<phrase>` to
# `value`, which reads as "the keyword ran and printed something".
# ⚠️ D-MSGEXACT nearly broke exactly this. A tree-wide sweep that capitalised
# message literals hit seven of these, because they LOOK like the message
# expectations it was updating. They are not: this is a CLASSIFIER vocabulary,
# not an assertion, and it is deliberately case-insensitive.
# The original reason for lowercasing -- zerobas's own lowercase wording being a
# documented divergence -- is GONE (D-MSGEXACT made every message the
# reference's verbatim text). The lowercasing stays anyway: the CLASS is the
# comparable thing here, and a classifier that is insensitive to case cannot be
# broken by a future wording change.
ERROR_WORDS = (
    "syntax error", "type mismatch", "overflow", "illegal function call",
    "out of memory", "undefined line", "subscript out of range",
    "division by zero", "redimensioned array", "missing operand",
    "illegal direct", "nexus", "bad file", "file not found", "disk offline",
    "device i/o error", "not found", "error",   # bare "error" LAST: catch-all
)


def tokens(raw: str | None) -> bytes | None:
    """Body tokens from a stored_line capture — the bytes after the 4-byte
    header (link + line number). None when the line was never stored (a crunch
    that errored on entry leaves the program empty)."""
    if not raw:
        return None
    b = bytes.fromhex(raw)
    return b[4:] if len(b) >= 5 else None


def marker_tail(raw: str | None, marker: str) -> str | None:
    """Rows from the one carrying `marker` to the closing prompt, '|'-joined.

    🔴 THE ECHO-FREE CAPTURE, AND WHY IT HAS TO EXIST (D-KWDRAIN step 4a).
    `screen_tail` anchors on the ECHOED COMMAND, which is why every row in this
    sweep had to leave the display alone: `CLS`, `SCREEN`, `WIDTH` and `COLOR`
    erase or move the echo, so the capture reported ?noecho and the word could
    never be attributed at all. I filed that as "these words cannot take a
    kwsweep row" -- WRONG: it was this probe's choice of anchor, not a limit.
    Other suites (arrays, deffn) have always run `CLS:PRINT"[";...` and read the
    bracketed marker straight off the screen.
    ⚠️ THE MARKER MUST BE UNIQUE PER ROW. Without the echo there is nothing to
    prove the text came from THIS case rather than surviving from the last one,
    so each NOECHO row prints its own tag and this function matches that tag --
    a stale screen then reads as ?nomarker, which is a refusal, not a pass.
    """
    if raw is None:
        return None
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    # 🔴 THE **LAST** MATCHING ROW, NOT THE FIRST, AND THAT COST A ROW TO LEARN.
    # The exec line prints the marker, so the marker text is also inside the
    # ECHOED COMMAND. On a machine whose echo SURVIVES the row's own feature
    # (`WIDTH 37` reformats but does not clear on the reference) a first-match
    # anchored on the echo and captured the command plus the answer, while the
    # side whose echo was gone captured the answer alone -- and the row came back
    # DIVERGENT with BOTH sides having printed `[W 37 ]`. The output always
    # follows the echo, so the last match is the answer on both.
    idx = next((i for i in range(len(rows) - 1, -1, -1) if marker in rows[i]), None)
    if idx is None:
        return None
    out: list[str] = []
    for r in rows[idx:]:
        if r in omsx_repl.PROMPTS:
            break
        out.append(r)
    while out and out[-1] == "":
        out.pop()
    return "|".join(out)


def classify(raw: str | None, cmdline: str,
             marker: str | None = None) -> tuple[str, str]:
    """(outcome_class, text) for one executed case.

    class is "value" (ran, printed something), "error:<phrase>", or "?<reason>".
    Comparing the CLASS first is what makes the sweep readable across zerobas's
    lowercase error wording.

    `marker` selects the echo-free capture for rows whose own feature destroys
    the echo -- see marker_tail."""
    if marker is not None:
        tail = marker_tail(raw, marker)
        if tail is None:
            return ("?nomarker", "")
    else:
        tail = omsx_repl.screen_tail(raw, cmdline)
        if tail is None:
            return ("?noecho", "")
    low = tail.lower()
    for phrase in ERROR_WORDS:
        if phrase in low:
            return (f"error:{phrase}", tail)
    return ("value", tail)


def verdict(ref_cls: str, ref_txt: str, zb_cls: str, zb_txt: str,
            crunch_state: str | None) -> str:
    """The six-way call described in the module header.

    `crunch_state` ("SAME"/"DIFF"/None) is what separates SILENT-GAP from a
    plain DIVERGENT: when NEITHER side errors, the answers still differ, AND
    zerobas failed to tokenise the word, the word is being parsed as an ordinary
    variable/array — the TIME / TAB( shape, the failure mode this whole probe
    exists to catch. That inference needs BOTH layers, which is why the support
    pass runs after the crunch pass rather than standalone."""
    if ref_cls.startswith("?") or zb_cls.startswith("?"):
        return "UNREADABLE"
    ref_err = ref_cls.startswith("error")
    zb_err = zb_cls.startswith("error")
    # A DIFF crunch is a DEFINITIVE fact: zerobas did not tokenise the word, so
    # whatever it did instead was a variable/array parse. When it then declines to
    # error, that is a silent wrong answer NO MATTER what the reference did —
    # including when the reference itself refused the case (MKS$/MKD$ on a
    # diskless VG-8020). Checking this before the ref-vs-zb comparison stops such
    # rows being labelled "EXTRA", which would read as zerobas having a feature it
    # provably lacks.
    # AGREEMENT WINS FIRST. An earlier revision tested the DIFF-crunch rule before
    # comparing the outputs, and promptly called DEFSNG/DEFDBL/DEFSTR "SILENT-GAP"
    # while printing two IDENTICAL answers — at the time those three had no
    # kwtable entry by design (they reached the then-ex_def_type as DEF_TOKEN +
    # literal ASCII) and worked fine. A no-entry word that produces the right
    # answer is the INTERVAL shape, not a gap, so identical observable behaviour
    # must be decided before tokenisation is allowed to weigh in at all.
    # ⚠️ THE ORDERING RULE OUTLIVED ITS EXAMPLE: those three got rows and
    # tokens of their own in D-DEFTYPETOK (2026-08-19) and no longer exercise this
    # path. INTERVAL still does, and the rule is kept for the CLASS, not the
    # instance — any word supported without a kwtable entry lands here.
    if not ref_err and not zb_err and ref_txt.strip() == zb_txt.strip():
        return "SUPPORTED"
    if crunch_state == "DIFF" and not zb_err:
        return "SILENT-GAP"
    if not ref_err and zb_err:
        return "MISSING"
    if ref_err and not zb_err:
        return "EXTRA"
    if ref_err and zb_err:
        # both refuse it — same class = faithful refusal, different = divergent
        return "SUPPORTED" if ref_cls == zb_cls else "DIVERGENT"
    return "SILENT-GAP" if crunch_state == "DIFF" else "DIVERGENT"


def _rom_fingerprint() -> str:
    """Hash the ROMs the repack machine actually loads, so a report can never be
    silently attributed to a different build. The machine XML points straight at
    build/*.rom in the project tree, so a concurrent `make` in another session
    changes the measurement target mid-flight — this is the tripwire for that."""
    root = _os.path.dirname(_os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))))
    parts = []
    for name in ("zerobas-main-eu.rom", "sub.rom", "disk.rom"):
        p = _os.path.join(root, "build", name)
        try:
            with open(p, "rb") as fh:
                parts.append(f"{name}={hashlib.sha256(fh.read()).hexdigest()[:12]}")
        except OSError:
            parts.append(f"{name}=<missing>")
    try:
        rev = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        rev = "?"
    return f"git={rev} " + " ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help="reference machine (built-in BASIC oracle; default VG-8020)")
    ap.add_argument("--disk-machine", dest="disk_machine", default=DISK_MACHINE,
                    help="disk-equipped reference for NEEDS-DISK rows (default "
                         f"{DISK_MACHINE}); the default VG-8020 has no disk ROM, "
                         "so Disk-BASIC verbs would compare machines, not languages")
    ap.add_argument("--zb-machine", dest="zb_machine", required=True,
                    help="repack machine with BASIC baked into slot 0")
    ap.add_argument("--only", help="comma-separated word keys to run")
    ap.add_argument("--layer", choices=("crunch", "support", "both"), default="both")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot (rule out leakage)")
    args = ap.parse_args()

    # A direct-mode line wider than one SCREEN-0 row wraps, so screen_tail can
    # never match its echo and the case silently reports ?noecho -> UNREADABLE.
    # That is a probe defect masquerading as a measurement, so fail loudly at
    # startup rather than emitting an unreadable row (the T3 KEY lesson: the
    # apparatus is part of the measurement).
    too_long = [(k, len(ex)) for k, _, ex, mode, _ in SWEEP
                if ex is not None and mode == "direct" and len(ex) > MAX_DIRECT_ECHO]
    if too_long:
        print("probe defect — direct-mode exec lines exceed one screen row "
              f"({MAX_DIRECT_ECHO} cols); use mode='stored' for these:")
        for k, n in too_long:
            print(f"    {k:9} {n} chars")
        # 🔴 D-KWFOOT: THIS EXIT PRINTS A DIFFERENT TABLE ENTIRELY, and without a
        # footer a runner holding a kwsweep baseline sees ZERO rows and cannot
        # tell "the probe measured nothing" from "I failed to parse it". The
        # abort is CORRECT; what was missing is it SAYING SO.
        print(probe_report.footer(
            len(too_long), 0,
            "probe defect, nothing measured: the listed words' direct-mode exec "
            "lines exceed one screen row, so their echo can never match"))
        return 2

    rows = SWEEP
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if r[0] in want]
        missing = want - {r[0] for r in rows}
        if missing:
            print(f"unknown word keys: {', '.join(sorted(missing))}")
            print(probe_report.footer(
                0, 0, "nothing measured: --only named word keys this sweep does "
                      "not have"))
            return 2
    batch = not args.boot_per_case

    fp_before = _rom_fingerprint()
    print(f"build under measurement: {fp_before}\n")

    results: dict[str, dict] = {k: {} for k, *_ in rows}

    # Route each row's REFERENCE capture to a machine that can actually run it.
    # A Disk-BASIC verb on a diskless reference measures the absence of a disk
    # ROM, not the absence of a language feature — see DISK_MACHINE.
    def ref_machine_for(note: str) -> str:
        return args.disk_machine if note.startswith("NEEDS-DISK:") else args.machine

    # 🔴 D-KWORACLE (2026-09-03): THE SECOND REFERENCE WAS NEVER BOOTED IN TIME,
    # AND ALL FIVE OF ITS WITH-ORACLE ROWS CAME BACK EMPTY. `run_cases` defaults
    # to `boot=8.0`, which is right for the VG-8020 and ~6 s SHORT for the
    # CF-3300; and the CF-3300 boots into a screen mode the scrape cannot read
    # until a `SCREEN 0`. So every NEEDS-DISK row was typed into an unbooted
    # machine: layer 2 got `ref ''` -> NO-ORACLE, and layer 1 read TXTTAB before
    # the line was there -> `<not stored>` -> ABSENT, which called even `MKI$`
    # absent from the reference's own keyword table.
    #
    # 🎯 THE FAMILY CONTROL IS WHAT MADE IT VISIBLE. `mki` is in the row set
    # precisely because MKI$/CVI ship on BOTH sides; when the control reports no
    # oracle, nothing else in the family can be believed. It did, and the summary
    # line -- `NO-ORACLE=5`, with no MISSING count -- reads like a clean bill of
    # health if you do not look at which five.
    #
    # The values here are the SAME ones basic_probe_deffn.SIDES already carries
    # for these machines; the two tables disagreeing is what let this sit.
    MACH_BOOT = {"National_CF-3300": 14.0}
    MACH_RESET_PRE = {"National_CF-3300": ("", "SCREEN 0")}

    def ref_capture(specs, sel_rows, **kw):
        """Capture `specs` on the reference, splitting the batch by which
        reference machine each row needs, then re-interleaving in row order."""
        out: list[str | None] = [None] * len(specs)
        for mach in sorted({ref_machine_for(r[4]) for r in sel_rows}):
            idx = [i for i, r in enumerate(sel_rows) if ref_machine_for(r[4]) == mach]
            mkw = dict(kw)
            mkw["boot"] = MACH_BOOT.get(mach, 8.0)
            pre = MACH_RESET_PRE.get(mach, ())
            if pre:
                mkw["reset"] = pre + tuple(kw.get("reset", ()))
            got = omsx_repl.run_cases(mach, [specs[i] for i in idx], batch=batch, **mkw)
            for i, g in zip(idx, got):
                out[i] = g
        return out

    # ---- Layer 1: CRUNCH ---------------------------------------------------
    if args.layer in ("crunch", "both"):
        specs = [("direct", [f"1 {body}"]) for _, body, _, _, _ in rows]
        ref_raws = ref_capture(specs, rows, reset=("NEW",),
                               capture=("stored_line", TXTTAB))
        zb_raws = omsx_repl.run_cases(args.zb_machine, specs, batch=batch,
                                      reset=("NEW",),
                                      capture=("stored_line", TXTTAB))
        for (key, body, _, _, _), rr, zr in zip(rows, ref_raws, zb_raws):
            ref, zb = tokens(rr), tokens(zr)
            results[key]["crunch"] = (
                "SAME" if (ref is not None and ref == zb) else "DIFF",
                " ".join(f"{b:02X}" for b in ref) if ref else "<not stored>",
                " ".join(f"{b:02X}" for b in zb) if zb else "<not stored>",
                body,
            )

    # ---- Layer 2: SUPPORT --------------------------------------------------
    if args.layer in ("support", "both"):
        ex_rows = [r for r in rows if r[2] is not None]
        if ex_rows:
            specs = []
            for _, _, line, mode, _ in ex_rows:
                specs.append((mode, omsx_repl.as_stored(line) if mode == "stored"
                              else [line]))
            ref_raws = ref_capture(specs, ex_rows,
                                   reset=("NEW", "CLS"), capture="screen")
            zb_raws = omsx_repl.run_cases(args.zb_machine, specs, batch=batch,
                                          reset=("NEW", "CLS"), capture="screen")
            for (key, _, line, mode, rnote), rr, zr in zip(ex_rows, ref_raws, zb_raws):
                cmd = "RUN" if mode == "stored" else line
                # NOECHO:<tag> -- this row's own feature erases or moves the
                # echoed command, so it is captured by its unique marker instead
                # (see marker_tail). Everything else keeps the echo anchor.
                mk = (rnote.split(":", 2)[1].split()[0]
                      if rnote.startswith("NOECHO:") else None)
                rc, rt = classify(rr, cmd, mk)
                zc, zt = classify(zr, cmd, mk)
                cs = results[key].get("crunch", (None,))[0]
                note = next(n for k, _, _, _, n in rows if k == key)
                if note.startswith("NEEDS-DISK:") and rc.startswith("?"):
                    # The oracle for this row is the disk-equipped reference, and
                    # it produced nothing readable. Refuse to compare rather than
                    # silently fall back to the diskless default and call the
                    # resulting machine difference a language difference.
                    v = "NO-ORACLE"
                else:
                    v = verdict(rc, rt, zc, zt, cs)
                results[key]["support"] = (v, rc, rt, zc, zt, line)

    fp_after = _rom_fingerprint()

    # ---- report ------------------------------------------------------------
    print("=" * 78)
    print("LAYER 1 — CRUNCH (tokenisation only; NOT a support answer)")
    print("=" * 78)
    for key, *_ in rows:
        c = results[key].get("crunch")
        if not c:
            continue
        state, ref, zb, body = c
        print(f"{state:5}  {key:9} {body}")
        if state == "DIFF":
            print(f"           ref: {ref}")
            print(f"           zb : {zb}")

    print()
    print("=" * 78)
    print("LAYER 2 — SUPPORT (the load-bearing layer)")
    print("=" * 78)
    order = {"SILENT-GAP": 0, "MISSING": 1, "DIVERGENT": 2, "EXTRA": 3,
             "UNREADABLE": 4, "NO-ORACLE": 5, "SUPPORTED": 6}
    executed = [(key, results[key]["support"]) for key, *_ in rows
                if "support" in results[key]]
    notes = {k: n for k, _, _, _, n in rows}
    for key, s in sorted(executed, key=lambda kv: order.get(kv[1][0], 9)):
        v, rc, rt, zc, zt, line = s
        weak = notes[key].startswith("WEAK:")
        print(f"{v:10}{'  ! WEAK' if weak else '  '}  {key:9} {line}")
        print(f"            ref  [{rc}] {rt!r}")
        if v != "SUPPORTED" or weak:
            print(f"            zb   [{zc}] {zt!r}")
        if weak:
            print(f"            {notes[key]}")

    # ---- the combined view: absence (layer 1) + consequence (layer 2) --------
    # Neither layer is readable alone. Layer 1 says whether zerobas TOKENISES the
    # word; layer 2 says what a program actually observes. INTERVAL is why: SAME
    # crunch, no support. TAB( is why: value on both sides, no support.
    if args.layer == "both":
        print()
        print("=" * 78)
        print("COMBINED — tokenised? x observable consequence")
        print("=" * 78)
        print(f"{'word':10} {'crunch':7} {'support':11} consequence")
        print("-" * 78)
        for key, *_ in rows:
            c = results[key].get("crunch")
            s = results[key].get("support")
            cs = c[0] if c else "-"
            tok = {"SAME": "present", "DIFF": "ABSENT", "-": "-"}[cs]
            if s:
                sv = s[0]
                cons = f"ref {s[2]!r} vs zb {s[4]!r}" if sv != "SUPPORTED" else "match"
            else:
                sv, cons = "not-run", "crunch-only — support UNKNOWN"
            print(f"{key:10} {tok:7} {sv:11} {cons}")

    skipped = [(k, n) for k, _, ex, _, n in rows if ex is None]
    if skipped:
        print()
        print("=" * 78)
        print(f"NOT EXECUTED — {len(skipped)} words, crunch-only. Reasons below; these "
              "are\nCOVERAGE HOLES IN THIS PROBE, not evidence of support.")
        print("=" * 78)
        for k, n in skipped:
            print(f"  {k:9} {n}")

    # ---- summary + the apparatus tripwire ----------------------------------
    # WEAK rows are excluded from the tally: counting a known-false SUPPORTED
    # would overstate coverage, which is the exact error this probe was built to
    # stop making.
    tally: dict[str, int] = {}
    for key, s in executed:
        tally["WEAK(excluded)" if notes[key].startswith("WEAK:") else s[0]] = \
            tally.get("WEAK(excluded)" if notes[key].startswith("WEAK:") else s[0], 0) + 1
    print()
    print("=" * 78)
    print("SUMMARY  " + "  ".join(f"{k}={v}" for k, v in
                                  sorted(tally.items(), key=lambda kv: order.get(kv[0], 9))))
    print(f"         executed {len(executed)} / {len(rows)} words; "
          f"{len(skipped)} crunch-only")
    print("=" * 78)
    print(probe_report.footer(
        len(rows), len(executed),
        f"{len(skipped)} crunch-only word(s) carry no support reading and are "
        f"printed but not scored"))

    # ---- D-TIERS (2026-09-10): a machine-readable pin for `make tiers` --------
    # Every row here IS a keyword, so this run is the first per-keyword
    # evidence the tier table can read without running an emulator. Written
    # to build/ (regenerated, never tracked) and ONLY when the ROMs held still
    # for the whole run -- a discarded report must not leave a pin behind.
    if fp_before == fp_after:
        import json
        import time as _time
        stmt = {key: st for key, st, *_ in rows}
        pin = {"written": _time.strftime("%Y-%m-%d %H:%M:%S"),
               "rom_fingerprint": fp_after,
               "rows": {key: {"verdict": s[0],
                              "weak": notes[key].startswith("WEAK:"),
                              "stmt": stmt[key]}
                        for key, s in executed}}
        _root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        pin_path = _os.path.join(_root, "build", "kwsweep-verdicts.json")
        try:
            _os.makedirs(_os.path.dirname(pin_path), exist_ok=True)
            with open(pin_path, "w", encoding="utf-8") as fh:
                json.dump(pin, fh, indent=1, sort_keys=True)
            print(f"pin: {len(pin['rows'])} row verdict(s) -> {pin_path}")
        except OSError as e:
            print(f"pin: NOT written ({e}) -- `make tiers` will show no kwsweep evidence")

    if fp_before != fp_after:
        print("\n*** APPARATUS WARNING — the ROMs changed DURING this run:")
        print(f"      before: {fp_before}")
        print(f"      after : {fp_after}")
        print("    Another session rebuilt the tree. DISCARD this report and re-run.")
        print(probe_report.footer(
            len(executed), 0,
            "DISCARDED: the ROMs changed during the run, so every row above was "
            "taken from more than one machine"))
        return 3

    # NEEDS-DISK rows cannot be controls: their oracle is the disk-equipped
    # reference, which is not yet readable (see DISK_MACHINE).
    controls = [k for k, _, ex, _, n in rows
                if ex is not None and n.startswith("control")]
    bad = [k for k in controls
           if results[k].get("support", ("?",))[0] != "SUPPORTED"]
    if bad:
        print(f"\n*** CONTROL GROUP FAILED: {', '.join(bad)}")
        print("    The apparatus is not measuring what it claims. Every other row "
              "in this\n    report is untrustworthy until this is explained.")
        print(probe_report.footer(
            len(executed), 0,
            f"NOT SCORED: the control group failed ({', '.join(bad)}), so the "
            f"apparatus is not measuring what it claims"))
        return 4

    # --- the crunch pin: a MISSING keyword has no other way to be scored ----
    if args.layer in ("crunch", "both"):
        diffs = {k for k in results
                 if results[k].get("crunch", (None,))[0] == "DIFF"}
        new_d = sorted(diffs - set(CRUNCH_DIFF_PINNED))
        gone = sorted(set(CRUNCH_DIFF_PINNED) - diffs)
        print("\n=== CRUNCH PIN — words the reference tokenises and zerobas "
              "does not ===")
        for k in sorted(CRUNCH_DIFF_PINNED):
            mark = "still DIFF" if k in diffs else "\U0001f7e2 NO LONGER DIFF"
            print(f"    {k:9s} {CRUNCH_DIFF_PINNED[k]:44s} {mark}")
        if new_d:
            print(f"\n*** \U0001f534 {len(new_d)} UNPINNED CRUNCH DIFF(S): "
                  f"{', '.join(new_d)}")
            print("    The reference tokenises these and zerobas does not, so "
                  "zerobas is\n    MISSING the keyword and parses it as an "
                  "ordinary VARIABLE -- the silent\n    shape this whole probe "
                  "exists to catch (TIME, TAB(). Implement it, or\n    pin it in "
                  "CRUNCH_DIFF_PINNED with its oracle-measured token and a why.")
            return 5
        if gone:
            print(f"\n*** \U0001f534 {len(gone)} PIN(S) NO LONGER DIVERGE: "
                  f"{', '.join(gone)}")
            print("    Good news, and it must be BOOKED: drop them from "
                  "CRUNCH_DIFF_PINNED,\n    or a stale pin hides the next real "
                  "one.")
            return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
