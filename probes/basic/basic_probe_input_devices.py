#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Input-devices acceptance -- the VG-8020 DIFFERENTIAL for STICK / STRIG
(docs/spec-basic-input-devices.md §8, slice I1).

Three phases, each run on BOTH the Philips VG-8020 reference and the merged
zerobas machine (C-BIOS_MSX1_EU_REPACK_DISK), asserting identical results:

  PHASE A -- grammar and the error surface. Every shape from spec §3 plus the §4
    coercion discriminators, as trapped `ON ERROR` cases comparing the error
    NUMBER. The coercion rows are chosen so round-half-up and truncate-toward-zero
    give DIFFERENT verdicts (STRIG(4.9) is legal only under truncation), so this
    phase would fail if the rounding rule regressed -- it is not a smoke test.

  PHASE B -- idle values. Every legal index of both functions with nothing
    plugged. Cheap, and it pins the two facts a reader would guess wrong (STRIG
    is 0/-1, not 0/255; STICK's domain stops at 2 while STRIG's runs to 4).

  PHASE C -- LIVE key matrix. THE TEETH. Phases A/B pass just as well against a
    function that returns a constant 0, because nothing is plugged in and idle IS
    0. This phase holds a key-matrix bit down across a sampling RUN and compares
    what STICK(0)/STRIG(0) actually READ. It needs omsx_repl's `holds=`
    key-matrix support (added with this slice): the KEYBUF injection every other
    phase uses writes decoded characters into the ROM's buffer and bypasses the
    matrix entirely, so a matrix-scanning routine reads idle no matter what the
    driver types.

    Row 8 carries { bit0 space, bit4 left, bit5 up, bit6 down, bit7 right }; the
    expected direction codes (1 up, 3 right, 5 down, 7 left, opposing pair -> 0)
    are asserted against the REFERENCE, not against a hard-coded table -- the
    literals in EXPECT are documentation, and a mismatch there is reported
    separately from a machine-vs-machine divergence.

Needs the merged machine installed (make repack-machine) + openMSX.

    make input-devices-acceptance
        # or: python3 probes/basic/basic_probe_input_devices.py
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")


def trapped(body: str, tag: str) -> list[str]:
    """A stored program that prints `tag` + the answer, or `tag`+"E"+ERR when the
    statement raises. Bodies only -- omsx_repl numbers the lines 10/20/30/40."""
    return ["ON ERROR GOTO 40", body, "END", f'PRINT"{tag}";"E";ERR:END']


def answer(raw: str | None, tag: str) -> str | None:
    """The tag and the numeric answer following it (digits / spaces / minus / E),
    stopping at other text so the trailing prompt is ignored.

    Scoped to the text AFTER the last `RUN` echo. Without that scoping the search
    hits the tag inside the ECHOED SOURCE LINE (`PRINT"A";STICK(3)` contains an
    `A` followed by no digits), every case "matches" as the bare tag, and the
    whole suite passes while proving nothing -- which is exactly what the first
    run of this probe did. The same artifact bit the G8 close-out; keep the
    anchor."""
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    idx = txt.rfind("RUN")
    if idx < 0:
        return None
    # LAST non-bare match, not the first: an aborting case prints the tag from the
    # statement that then failed AND the tag again from the trap handler, so the
    # screen reads e.g. "AAE 5" -- the first match is the bare "A".
    hits = [re.sub(r"\s+", " ", m).strip()
            for m in re.findall(re.escape(tag) + r"(?:E)?[ \d\-]*", txt[idx + 3:])]
    rich = [h for h in hits if h != tag]
    if rich:
        return rich[-1]
    return f"{tag}<no-output>" if hits else None


# --- PHASE A: grammar + error surface -------------------------------------
# label, statement, tag. "E n" in the outcome = trapped error n.
GRAMMAR = [
    ("stick_3",      'PRINT"A";STICK(3)', "A"),            # ERR 5 domain
    ("stick_neg",    'PRINT"B";STICK(-1)', "B"),           # ERR 5
    ("strig_5",      'PRINT"C";STRIG(5)', "C"),            # ERR 5
    ("strig_neg",    'PRINT"D";STRIG(-1)', "D"),           # ERR 5
    ("stick_32767",  'PRINT"E";STICK(32767)', "E"),        # ERR 5 (in int16)
    ("stick_m32768", 'PRINT"F";STICK(-32768)', "F"),       # ERR 5 (in int16)
    ("stick_32768",  'PRINT"G";STICK(32768)', "G"),        # ERR 6 overflow
    ("stick_40000",  'PRINT"H";STICK(40000)', "H"),        # ERR 6
    ("stick_str",    'PRINT"I";STICK("X")', "I"),          # ERR 13 type mismatch
    ("bare_stick",   'PRINT"J";STICK', "J"),               # ERR 2
    ("stick_noparen",'PRINT"K";STICK 0', "K"),             # ERR 2
    ("unclosed",     'PRINT"L";STICK(0', "L"),             # ERR 2
    ("empty_arg",    'PRINT"M";STICK()', "M"),             # ERR 2
    ("two_args",     'PRINT"N";STICK(0,1)', "N"),          # ERR 2
    ("stmt_pos",     'STICK(0):PRINT"O";1', "O"),          # ERR 2
    ("let_bare",     'A=STICK:PRINT"P";A', "P"),           # ERR 2
    # --- coercion discriminators (spec §4): truncate, not round --------------
    ("trunc_2p6",    'PRINT"Q";STICK(2.6)', "Q"),          # trunc 2 -> 0; round 3 -> ERR 5
    ("trunc_4p9",    'PRINT"R";STRIG(4.9)', "R"),          # trunc 4 -> 0; round 5 -> ERR 5
    ("trunc_neg",    'PRINT"S";STICK(-0.6)', "S"),         # trunc 0 -> 0; round -1 -> ERR 5
    ("trunc_p9",     'PRINT"T";STICK(.9)', "T"),           # -> 0
    # nesting / expression arguments
    ("nested",       'PRINT"U";STICK(STRIG(0)+1)', "U"),
    ("expr_arg",     'A=1:PRINT"V";STICK(A*2)', "V"),
    # --- PDL / PAD error surface (spec §9.4: the ERR 5 / ERR 6 edges) ---------
    ("pdl_0",        'PRINT"a";PDL(0)', "a"),               # ERR 5 (domain starts at 1)
    ("pdl_13",       'PRINT"b";PDL(13)', "b"),              # ERR 5
    ("pdl_32768",    'PRINT"c";PDL(32768)', "c"),           # ERR 6 overflow
    ("pdl_str",      'PRINT"d";PDL("X")', "d"),             # ERR 13 type mismatch
    ("bare_pdl",     'PRINT"e";PDL', "e"),                  # ERR 2
    ("pdl_trunc",    'PRINT"f";PDL(1.9)', "f"),             # trunc 1 -> legal
    ("pad_8",        'PRINT"g";PAD(8)', "g"),               # ERR 5 (BASIC subset ends at 7)
    ("pad_neg",      'PRINT"h";PAD(-1)', "h"),              # ERR 5
    ("pad_32768",    'PRINT"i";PAD(32768)', "i"),           # ERR 6
    ("bare_pad",     'PRINT"j";PAD', "j"),                  # ERR 2
    ("pad_trunc",    'PRINT"k";PAD(7.9)', "k"),             # trunc 7 -> legal
]

# --- PHASE B: idle values (nothing plugged) -------------------------------
IDLE = [
    ("stick_all", 'PRINT"A";STICK(0);STICK(1);STICK(2)', "A"),
    ("strig_all", 'PRINT"B";STRIG(0);STRIG(1);STRIG(2);STRIG(3);STRIG(4)', "B"),
    # PDL idle = 255 (count cap), PAD idle = 0 (nothing to convert / not touched).
    # Short representative slices per index kind, kept under the 40-col wrap.
    ("pdl_idle",  'PRINT"C":FORI=1TO12:PRINTPDL(I):NEXT', "C"),
    ("pad_idle",  'PRINT"D":FORI=0TO7:PRINTPAD(I):NEXT', "D"),
]

# --- PHASE C: live key matrix (the teeth) ---------------------------------
# A sampling loop latches any nonzero seen while the bit is held. label, row,
# mask, and the DOCUMENTED expectation (spec §5.1) -- checked separately from
# the machine-vs-machine comparison.
SAMPLER = [
    "A=0:C=0",
    "FOR I=1 TO 60",
    "B=STICK(0):IF B<>0 THEN A=B",
    "D=STRIG(0):IF D<>0 THEN C=D",
    "NEXT",
    'PRINT"Z";A;C',
]
MATRIX = [   # label, (row, mask) or None, expected "Z stick strig"
    ("idle",     None,       "Z 0 0"),
    ("space",    (8, 0x01),  "Z 0 -1"),
    ("left",     (8, 0x10),  "Z 7 0"),
    ("up",       (8, 0x20),  "Z 1 0"),
    ("down",     (8, 0x40),  "Z 5 0"),
    ("right",    (8, 0x80),  "Z 3 0"),
    ("up_down",  (8, 0x60),  "Z 0 0"),   # opposing pair cancels
]


# --- PHASE D: PDL values with devices plugged (THE TEETH) -----------------
# spec §9.4. The whole 1..12 matrix under four plug configurations, differential
# against the VG-8020. A constant PDL cannot fake this: a plugged openMSX paddle
# reads 128 (which also pins the count RATE, not just the polarity), a touchpad
# pulls two indices to 0, and everything else idles at 255. The documented table
# (char record §2) is carried as a NOTE, checked separately from ref==zb.
# A FOR loop, NOT one long PRINT with 12 PDL(): omsx_repl injects each line through
# the 40-byte KEYBUF type-ahead buffer, and a ~90+ char line overflows it and
# corrupts unpredictably (confirmed to bite STICK and PEEK too, so it is a harness
# limit, not an interpreter bug -- a real user typing that line is fine). The loop
# keeps the injected line short while still reading the whole 1..12 matrix.
# ONE value per line (no trailing `;`): 12 packed values overflow the 40-column
# screen and a number straddling the wrap ("255" -> "25\n5") reads back as two
# tokens, and the wrap column differs by machine -- a false diff. A value per line
# never straddles.
PDL_BODY = 'PRINT"P":FORI=1TO12:PRINTPDL(I):NEXT'
PDL_CONFIGS = [   # cfg label, plug prologue, documented flattened line (char §2)
    ("paddleA",   ("plug joyporta paddle",),
     "P 128 255 255 255 255 255 255 255 255 255 255 255"),
    ("paddleB",   ("plug joyportb paddle",),
     "P 255 128 255 255 255 255 255 255 255 255 255 255"),
    ("touchpadA", ("plug joyporta touchpad",),
     "P 255 255 0 255 0 255 255 255 255 255 255 255"),
    ("touchpadB", ("plug joyportb touchpad",),
     "P 255 255 255 0 255 0 255 255 255 255 255 255"),
]

# --- PHASE E: PAD values with arkanoidpad plugged (ALSO TEETH) -------------
# spec §9.4. The 0..7 matrix under arkanoidpad in port A and B, differential
# against the VG-8020. Distinct outcomes -- sense -1, X/Y 255, button 0 -- so a
# constant-0 PAD fails immediately. One non-clean reference behaviour the
# differential still holds us to (tape.asm GTPAD's latch): device 1's X/Y (PAD
# 5,6) are ungated so they read 255 even with port 2 empty -- which is why
# arkanoidA below is NOT a clean 0..3 / 4..7 mirror.
# ⚠️ These rows are UNDRIVEN devices, and every one agreed both before and after
# D-PADTRACE (2026-09-27) replaced D-I-7's guessed protocol (X and Y read the same
# unaddressed frame, clocked on /CS) with the traced one: an undriven panel
# converts to the same bytes however it is clocked. What moved is only visible
# with a pen ON the pad -- scratchpad/rigfw_window_probe.py, windowed, with the
# rig (scratchpad/rigfw_window_touchpad_zb_after_run.out).
PAD_BODY = 'PRINT"Q":FORI=0TO7:PRINTPAD(I):NEXT'
PAD_CONFIGS = [   # cfg label, plug prologue, measured VG-8020 flattened line
    ("arkanoidA", ("plug joyporta arkanoidpad",), "Q -1 255 255 0 0 255 255 0"),
    ("arkanoidB", ("plug joyportb arkanoidpad",), "Q 0 0 0 0 -1 255 255 0"),
]


def run_plug_phase(name: str, blurb: str, body: str, tag: str, configs) -> int:
    """One config per boot (prologue = a `plug` line), the same single value-
    matrix case on both machines, differential compared. The documented line is a
    NOTE only -- ref==zb is the gate."""
    fails = 0
    print(f"=== PHASE {name}: {blurb} ===")
    for cfg, prologue, doc in configs:
        specs = [("stored", trapped(body, tag))]
        ref = omsx_repl.run_cases(REF, specs, reset=("NEW", "CLS"),
                                  prologue=prologue)
        zb = omsx_repl.run_cases(ZB, specs, reset=("NEW", "CLS"),
                                 prologue=prologue)
        ra, za = answer(ref[0], tag), answer(zb[0], tag)
        ok = ra is not None and ra == za
        note = ""
        if ok and doc is not None and ra is not None:
            docn = " ".join(doc.split())
            if ra != docn:
                note = f"  (NOTE: both differ from documented {docn!r})"
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {cfg:11} ref={ra!r} zb={za!r}{note}")
    return fails


def run_phase(name: str, cases, blurb: str) -> int:
    specs = [("stored", trapped(body, tag)) for _, body, tag in cases]
    ref = omsx_repl.run_cases(REF, specs, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, reset=("NEW", "CLS"))
    fails = 0
    print(f"=== PHASE {name}: {blurb} ===")
    for (label, _body, tag), r, z in zip(cases, ref, zb):
        ra, za = answer(r, tag), answer(z, tag)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:14} ref={ra!r} zb={za!r}")
    return fails


def phase_c() -> int:
    specs = [("stored", SAMPLER)] * len(MATRIX)
    holds = [h for _, h, _ in MATRIX]
    # Timing is the whole difficulty of this phase, in BOTH directions: the loop
    # must still be sampling when the key goes down 0.3 s after RUN, AND must have
    # printed before the capture -- on two machines of different speed. Measured
    # here: a STICK/STRIG sampling iteration is expensive (two BIOS calls, each
    # scanning the matrix), so the loop runs at only ~10 iterations/emulated-second
    # -- 1500 and 400 and even 150 iterations outrun the un-held case's window on
    # zerobas, while 60 completes on both and still runs many seconds, i.e. far
    # longer than the 0.3 s before the press. The
    # un-held `idle` case is the tight one -- it gets no hold_secs added to its
    # timeline -- so cap_gap alone has to cover the loop for it, and zerobas needs
    # appreciably longer than the reference to run the same 150 iterations.
    # boot-per-case (batch=False): a held matrix bit is exactly the kind of state
    # that can leak into the next case's line entry, and this phase is the one
    # phase whose result must not be explainable by cross-case contamination.
    kw = dict(reset=("NEW", "CLS"), holds=holds, hold_secs=8.0, cap_gap=25.0,
              batch=False)
    ref = omsx_repl.run_cases(REF, specs, **kw)
    zb = omsx_repl.run_cases(ZB, specs, **kw)
    fails = 0
    print("=== PHASE C: LIVE key matrix -- STICK(0)/STRIG(0) actually read ===")
    for (label, hold, want), r, z in zip(MATRIX, ref, zb):
        ra, za = answer(r, "Z"), answer(z, "Z")
        ok = ra is not None and ra == za
        note = ""
        if ok and ra != want:
            note = f"  (NOTE: both differ from the documented {want!r})"
        fails += not ok
        held = f"row{hold[0]} ${hold[1]:02x}" if hold else "nothing held"
        print(f"  {'PASS' if ok else 'FAIL'} {label:9} {held:13} "
              f"ref={ra!r} zb={za!r}{note}")
    return fails


def main() -> int:
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].upper()
    fails = 0
    total = 0
    if only in (None, "A"):
        fails += run_phase("A", GRAMMAR, "grammar + error surface + coercion")
        total += len(GRAMMAR)
    if only in (None, "B"):
        fails += run_phase("B", IDLE, "idle values, nothing plugged")
        total += len(IDLE)
    if only in (None, "C"):
        fails += phase_c()
        total += len(MATRIX)
    if only in (None, "D"):
        fails += run_plug_phase("D", "PDL values, devices plugged (teeth)",
                                PDL_BODY, "P", PDL_CONFIGS)
        total += len(PDL_CONFIGS)
    if only in (None, "E"):
        fails += run_plug_phase("E", "PAD values, arkanoidpad plugged (teeth)",
                                PAD_BODY, "Q", PAD_CONFIGS)
        total += len(PAD_CONFIGS)
    print()
    if fails:
        print(f"FAIL: {fails}/{total} input-device cases diverge from the VG-8020")
        return 1
    print(f"ALL PASS ({total} cases) — STICK/STRIG/PDL/PAD match the VG-8020")
    return 0


if __name__ == "__main__":
    sys.exit(main())
