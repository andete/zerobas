#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TRAPSTATE — the discriminating instrument the KEY/STRIG/STOP item asked for:
read the trap STATE, not the fire count.

## What is open

`SPRITE` diverges in the `CLEAR, still SERVICING` cell (1 vs 250); `KEY`, `STOP`
and `STRIG` agree at 1/1. The item's own caution is that agreement there is
BOUNDED: those three fire per EDGE, so their 2x2 can only see a wrong state that
survives to the second tap, and it closes with

    "A discriminating instrument for that would have to observe the trap STATE,
     not the fire count."

## Why this is one-sided, and why that is the right shape

zerobas's trap table is `ZTRAP` at $E1D1, **own-design layout, quarantined in
PROVENANCE.md** -- deliberately NOT the reference's `TRPTBL` address or bit
layout. So a cross-machine state comparison does not exist to be built: there is
no byte on the reference that means the same thing. What CAN be asked, and is
what actually decides the item, is an INTERNAL question:

    does zerobas leave the same state after CLEAR for all of these verbs?

If the three "agreeing" verbs land in the same state SPRITE must be in (ON, so
it re-fires with no new event), then their 1s are the event source hiding a
shared defect. If they land in SERVICING, the verbs genuinely differ and
"the index is a parameter, so all five behave alike" is refuted at the level of
state rather than of counts.

## The control is the whole reading

A state byte after `CLEAR` says nothing on its own -- it has to be compared with
the same byte WITHOUT the `CLEAR`. Both cases leave the trap SERVICING; the only
difference is the statement under test. A verb whose two cases read the same
value is one `CLEAR` did not touch.

## Encoding

`run()` exposes exactly five cells, so the two readings are packed:

    $D004 (aux) = ZTRAP[idx] state byte -- bits 1-0: 00 OFF, 01 ON, 10 STOP,
                  11 SERVICING; bit 7 = PENDING
    $D001 (who) = TRAPENA * 16 + TRAPSVC, both small counts

⚠️ SPRITE IS NOT READ HERE, AND ITS STATE IS INFERRED RATHER THAN MEASURED. Its
replay STARVES -- the re-enabled trap fires once per frame and the program never
reaches a reporting line, which is why its own 2x2 shows unwritten mechanism
cells. "SPRITE is left ON" follows from 250 fires with no new event, which no
other state produces; it is not a byte anyone has read.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import basic_probe_key_trap as K                                  # noqa: E402
import basic_probe_stop_trap as S                                 # noqa: E402
import basic_probe_strig_trap as G                                # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

ZTRAP, TRAPENA, TRAPSVC = 0xE1D1, 0xE20B, 0xE20C
ENTSZ = 3
# 🔴 KEY 1 IS ENTRY 17, NOT 8. The KEY band is laid out REVERSED -- KEY 10 at
# ZTI_KEY1, KEY 1 at ZTI_KEY1+9 (basic/keytrap.asm:121, basic/program.asm:2924,
# and the three `ld a,ZTI_KEY1+9` sites). basic/sysvars.inc said "KEY n -> 7+n"
# and was the wrong half of a two-file disagreement; this probe found it by
# flagging e17 as unexpected, and the ENTRY was right
# [[two-sections-of-one-doc-disagreed]].
IDX = {"STOP": 1, "SPRITE": 2, "STRIG": 3, "KEY": 17}

STATE = {0: "OFF", 1: "ON", 2: "STOP(user)", 3: "SERVICING"}


def decode(b: int) -> str:
    """`b` is the packed AUX: idx*8 + state + 4 if PENDING, or 255 for none."""
    if b == 255:
        return "no live entry"
    return (f"e{b >> 3}:{STATE.get(b & 3, '?')}"
            + ("+PENDING" if b & 4 else ""))


def read_lines(verb: str) -> list[str]:
    """Splice the readings in AFTER the CLEAR and BEFORE any second window -- the
    reference point is `CLEAR` has run and nothing else has.

    🔴 THIS SCANS FOR THE LIVE ENTRY INSTEAD OF INDEXING THE ONE IT EXPECTS, and
    the first cut did not. Reading `ZTRAP + 3*ZTI_KEY1` gave **0 (OFF) while
    TRAPSVC said 1** -- a table with one SERVICING entry and no entry in state
    SERVICING, which is not a machine state but an address that missed. A wrong
    address decodes to `OFF`, the most plausible-looking answer there is
    [[a-readout-blind-to-its-own-subject]]. The scan cannot miss that way: it
    reports WHICH entry it found, so a disagreement with `IDX[verb]` is visible
    rather than silently absorbed.

    AUX packing: idx*8 + state_bits + 4 if PENDING; 255 = no non-zero entry.

    🔬 `--direct` REPLACES THE SCAN WITH A PEEK AT THE EXPECTED ADDRESS, and it
    exists because the scan reported "no live entry" for STRIG in all three
    cases while TRAPENA/TRAPSVC tracked correctly -- including `returned`, where
    ENA=1 asserts exactly one entry is ON. Reading basic/program.asm:2862 says
    that entry IS written (`add a,ZTI_STRIG0` / `ztrap_entry` / state store), so
    the disagreement is between the ROM and THIS INSTRUMENT, and naming a ROM
    mechanism before falsifying the instrument is the mistake this repo keeps
    catching [[a-mechanism-inferred-from-one-observation]].
    """
    if "--direct" in sys.argv:
        a = ZTRAP + ENTSZ * IDX[verb]
        return [f"55 A={IDX[verb]}*8+(PEEK(&H{a:04X})AND3)",
                f"56 IF(PEEK(&H{a:04X})AND128)<>0THENA=A+4",
                "57 POKE&HD004,A",
                f"58 POKE&HD001,PEEK(&H{TRAPENA:04X})*16+PEEK(&H{TRAPSVC:04X})",
                "59 POKE&HD003,1:END"]
    return [f"55 A=255:FORZ=0TO17:B=PEEK(&H{ZTRAP:04X}+{ENTSZ}*Z)",
            "56 IFB<>0ANDA=255THENA=Z*8+(BAND3)-4*((BAND128)<>0)",
            "57 NEXT:POKE&HD004,A",
            f"58 POKE&HD001,PEEK(&H{TRAPENA:04X})*16+PEEK(&H{TRAPSVC:04X})",
            "59 POKE&HD003,1:END"]


def prog_key(do_clear: bool, always_return: bool = False) -> list[str]:
    return [K.ONERR,
            "5 CLEAR200,&HCFFF:POKE&HD000,0:POKE&HD001,0",
            "6 POKE&HD002,0:POKE&HD003,0:POKE&HD004,0",
            "10 ON KEY GOSUB 100",
            "20 KEY(1) ON",
            "30 FORI=1TO20000:NEXT",
            "40 REM state left SERVICING",
            ("50 CLEAR" if do_clear else "50 REM no clear -- the CONTROL"),
            ] + read_lines("KEY") + [
            "100 POKE&HD000,PEEK(&HD000)+1",
            ] + ([] if always_return else ["105 IFPEEK(&HD000)=1THEN40"]) + [
            "108 RETURN", K.ERRH]


def prog_stop(do_clear: bool) -> list[str]:
    return [S.CLR,
            "10 ON STOP GOSUB 100",
            "20 STOP ON",
            S.RANOK,
            "30 FORI=1TO4000:NEXT",
            "40 REM state left SERVICING",
            ("50 CLEAR" if do_clear else "50 REM no clear -- the CONTROL"),
            ] + read_lines("STOP") + [
            "100 POKE&HD000,PEEK(&HD000)+1",
            "105 IFPEEK(&HD000)=1THEN40",
            "108 RETURN"]


def prog_strig(do_clear: bool, always_return: bool = False) -> list[str]:
    return [G.ONERR,
            "5 CLEAR200,&HCFFF:POKE&HD000,0:POKE&HD001,0",
            "6 POKE&HD002,0:POKE&HD003,0",
            "10 ON STRIG GOSUB 100",
            "20 STRIG(0) ON",
            "30 FORI=1TO9000:NEXT",
            "40 REM state left SERVICING",
            ("50 CLEAR" if do_clear else "50 REM no clear -- the CONTROL"),
            ] + read_lines("STRIG") + [
            "100 POKE&HD000,PEEK(&HD000)+1",
            ] + ([] if always_return else ["105 IFPEEK(&HD000)=1THEN40"]) + [
            "108 RETURN", G.ERRH]


# 🎯 ONE TAP EACH, NOT TWO. The 2x2 runners fire a SECOND tap at 3.0 s because
# their reading IS whether the second one re-fires the trap. Here the reading is
# taken at line 55, immediately after the `CLEAR` and before any second window,
# so a second tap could only arrive after the capture -- or worse, land during
# it. Each verb's FIRST tap is inherited verbatim from its own probe module:
# K.tap() for F1, strig's kdown/kup pair for the SPACE trigger, and stop's
# (down, up) press tuple for Ctrl-STOP.
# ⚠️ STOP IS OUT OF SCOPE FOR THIS INSTRUMENT, AND THE REASON IS THE CHANNEL, not
# the verb. basic_probe_stop_trap's capture reads exactly FLAG/RAN/DONE -- no AUX,
# no WHO -- and its DONE is set by an INJECTED direct POKE rather than by the
# program, so there is nowhere to put a state byte and nothing to gate it on.
# Carrying STOP would mean widening a shared probe module that four gates depend
# on, which is a larger change than this reading is worth. Named here rather than
# quietly dropped [[an-unnamed-outcome-reads-as-no-outcome]].
VERBS = [
    ("KEY",   prog_key,   lambda p: K.run(ZB, p, K.tap(1, 1.0), boot=8.0, step=4.0)),
    ("STRIG", prog_strig, lambda p: G.run(ZB, p, [(1.0, G.kdown()), (1.15, G.kup())],
                                          boot=8.0, step=3.0)),
]


def main() -> int:
    # 🎯 THE THIRD CASE IS A NEGATIVE CONTROL ON THE COUNTER, and the run that
    # forced it read `TRAPSVC=1` on STRIG with NO entry in a non-zero state --
    # a counter and a table disagreeing. Without a case where nothing is
    # servicing, `SVC=1` cannot be told from "SVC always reads 1 here"
    # [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. `returned` runs the
    # same program with a handler that RETURNs, so the trap leaves SERVICING by
    # the ordinary path and the counter MUST come back to 0.
    CASES = (("CLEAR", True, False), ("control", False, False),
             ("returned", False, True))
    rows, broken = [], []
    for verb, mk, runner in VERBS:
        for case, do_clear, always_ret in CASES:
            r = runner(mk(do_clear, always_ret))
            rows.append((verb, case, r))
            if not r or r.get("done") != 1 or r.get("err") != 0:
                broken.append((verb, case))

    # 🔴 A MISSING KEY IS NOT A VALUE. Every STRIG row of the first three runs
    # read "no live entry" because basic_probe_strig_trap's capture emitted no
    # `aux` and `r.get("aux", 255)` supplied the sentinel -- the DEFAULT became
    # the data, decoded to something plausible, and a consistency check then
    # reported "counter and table DISAGREE" off it. It surfaced only in
    # `--direct`, where 255 is UNREACHABLE (the packing there is idx*8+state,
    # at most 31), so an impossible value proved the channel absent rather than
    # the machine odd.
    blind = [(v, c) for v, c, r in rows if r and "aux" not in r]
    if blind:
        print(f"\n🔴 INSTRUMENT BLIND: {blind} came back with no `aux` key -- "
              f"that probe module's capture does not emit the cell this reading "
              f"lives in. Refused rather than defaulted.")
        return 2
    print(f"\n{'verb':6s} {'case':9s} {'fires':>5s} {'ZTRAP':>6s} "
          f"{'decoded':>16s} {'ENA':>4s} {'SVC':>4s}")
    for verb, case, r in rows:
        if not r:
            print(f"{verb:6s} {case:9s} <NO CAPTURE>")
            continue
        who, aux = r.get("who", 0), r.get("aux", 255)
        print(f"{verb:6s} {case:9s} {r.get('cnt', -1):>5d} {aux:>6d} "
              f"{decode(aux):>16s} {who >> 4:>4d} {who & 15:>4d}"
              f"   {'(expected e%d)' % IDX[verb] if aux != 255 and (aux >> 3) != IDX[verb] else ''}")

    if broken:
        # 🔴 A STATE BYTE FROM A PROGRAM THAT DID NOT FINISH IS NOT A READING --
        # it is whatever the cell held when the capture fired, and `0` decodes
        # to the plausible-looking "OFF" [[an-unnamed-outcome-reads-as-no-outcome]].
        print(f"\n🔴 INSTRUMENT FAULT: {broken} did not reach done with err==0. "
              f"Every state byte above is void, INCLUDING the ones that decoded "
              f"to something sensible.")
        return 2

    print()
    got = {(v, c): r for v, c, r in rows}
    # 🔴 THE COUNTER/TABLE CONSISTENCY CHECK. TRAPSVC is "count of live SERVICING
    # entries"; a non-zero count with no SERVICING entry in the table is not a
    # machine state, it is two bookkeepers disagreeing.
    for verb, case, r in rows:
        if not r:
            continue
        svc, aux = r.get("who", 0) & 15, r.get("aux", 255)
        live_svc = aux != 255 and (aux & 3) == 3
        if (svc > 0) != live_svc:
            print(f"  ⚠️ {verb} {case}: TRAPSVC={svc} but the table shows "
                  f"{decode(aux)} -- counter and table DISAGREE")
    verdict = []
    for verb, _mk, _run in VERBS:
        a, b = got[(verb, "CLEAR")], got[(verb, "control")]
        same = a.get("aux") == b.get("aux")
        verdict.append((verb, a.get("aux"), b.get("aux"), same))
        print(f"  {verb:6s} CLEAR={decode(a.get('aux', 255))!r:>20} "
              f"control={decode(b.get('aux', 255))!r:>20}"
              + ("   (CLEAR changed nothing)" if same else
                 "   <-- CLEAR MOVED THE STATE"))
    moved = [v for v, _x, _y, s in verdict if not s]
    print(f"\n=== CLEAR moved the trap state on: {moved or 'none of the three'} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
