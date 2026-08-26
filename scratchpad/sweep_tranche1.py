#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 1 — re-run, do not re-read.

Every row here re-measures a claim a TODO.md item ASSERTS, on both references
and on zerobas, from the item's own text. No claim is inherited: an item that
says "zerobas raises X" is put to the machine even when the item is recent.

⚠️ EACH ROW CARRIES ITS OWN CONTROL where a green reading could mean two things.
The `[...]` bracket convention makes the reading a SPAN, so a row that never ran
reads as absent rather than as agreement.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

SIDES = {
    # 🔴 THE RESET MUST CLS. The first run of this probe used reset=("NEW",) and
    # every case inherited the PREVIOUS case's screen, so the [...] span reader
    # returned earlier cases' values -- T008 "read" a 9 that PAINT had printed two
    # cases earlier. An accumulating screen reads as a plausible value, which is
    # the worst way for an instrument to fail.
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=5.0,
                   reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=7.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, step=5.0, reset=("NEW", "CLS")),
}
COLS, ROWS = 40, 24

# (todo_id, label, mode, lines, what the ITEM claims)
CASES = [
    # --- T056: "zerobas does NOT implement the PLAY(n) FUNCTION; every PLAY(0)
    #     read raised `Missing operand`". Filed 2026-08-24. A D-PLAYOP block sits
    #     directly beneath it, closed 2026-08-26 — same seam or not is a
    #     MEASUREMENT, not a reading.
    ("T056", "play-fn", "direct", ['PRINT"[";PLAY(0);"]"'],
     "refs print -1/0; item says zb raises Missing operand"),
    ("T056", "play-fn.control", "direct", ['PRINT"[";1;"]"'],
     "the same PRINT shape with no PLAY -- proves the fixture prints at all"),

    # --- T064: "RUN <lineno> typed at the PROMPT ... dl_run still ignores the
    #     number" -> zb runs from the TOP (prints A then B), refs run from 20.
    ("T064", "run-lineno", "direct",
     ['10 PRINT"[A]"', '20 PRINT"[B]"', "RUN 20"],
     "refs print [B] only; item says zb prints [A][B]"),
    ("T064", "run-lineno.control", "direct",
     ['10 PRINT"[A]"', '20 PRINT"[B]"', "RUN"],
     "bare RUN -- both sides must print [A][B]; pins what 'from the top' looks like"),

    # --- T131: SCREEN-2 PAINT with C != B. Item: POINT(50,21) BELOW the wall
    #     reads 9 on both references and 4 here.
    ("T131", "paint-flood", "direct",
     ['SCREEN 2:LINE(0,20)-(255,20),7:PAINT(128,8),9,7:P=POINT(50,21):'
      'SCREEN 0:PRINT"[";P;"]"'],
     "item: refs 9, zb 4"),
    ("T131", "paint-flood.control", "direct",
     ['SCREEN 2:LINE(0,20)-(255,20),7:P=POINT(50,21):SCREEN 0:PRINT"[";P;"]"'],
     "same but NO PAINT -- pins the untouched colour below the wall"),

    # --- T008: KEY n,"str" unimplemented (D-KEYSTR scout, D-MISSOP3's r.keyok).
    ("T008", "key-str", "direct", ['KEY 1,"X"', 'PRINT"[OK]"'],
     "refs accept silently; item says the form is absent here"),

    # 🔴 `WAIT` WAS HERE AND IT HUNG BOTH REFERENCES. `WAIT 1,0` blocks until a
    # PORT condition is satisfied, so the reference sat in it forever -- and in a
    # BATCHED probe that voids every case AFTER it too (T123's rows came back
    # empty on both references for that reason alone, reading as "no output"
    # rather than as "the machine is still in the previous case"). A blocking
    # statement needs an ISOLATED, timeout-bounded row; it may not share a batch.
    # --- T123: the third trailing SCREEN argument's domain is UNMEASURED.
    ("T123", "screen-3rd", "direct", ['SCREEN 0,0,0', 'PRINT"[OK]"'],
     "in-domain third argument"),
    ("T123", "screen-3rd.hi", "direct", ['SCREEN 0,0,99', 'PRINT"[OK]"'],
     "out-of-domain third argument -- error or accepted?"),
]


def read_rows(scr):
    if scr is None:
        return None
    return [scr[r * COLS:(r + 1) * COLS].rstrip() for r in range(ROWS)
            if scr[r * COLS:(r + 1) * COLS].strip()]


def spans(scr):
    """Every [...] span on the screen, in order. A row that never ran has none."""
    rows = read_rows(scr)
    if rows is None:
        return None
    flat = " ".join(rows)
    out, i = [], 0
    while True:
        a = flat.find("[", i)
        if a < 0:
            break
        b = flat.find("]", a)
        if b < 0:
            break
        out.append(flat[a + 1:b].strip())
        i = b + 1
    return out


def main():
    res = {}
    for side, cfg in SIDES.items():
        res[side] = omsx_repl.run_cases(
            cfg["machine"], [(m, l) for _, _, m, l, _ in CASES],
            batch=True, reset=cfg["reset"], boot=cfg["boot"], step=cfg["step"],
            verify_delivery=False)
    for i, (tid, label, _, lines, claim) in enumerate(CASES):
        print(f"\n=== {tid} {label}")
        print(f"    claim: {claim}")
        for side in SIDES:
            sp = spans(res[side][i])
            rows = read_rows(res[side][i]) or []
            err = [r for r in rows if "rror" in r or "Missing" in r
                   or "Illegal" in r or "mismatch" in r]
            print(f"    {side:8s} spans={sp}"
                  + (f"   ERRORS={err}" if err else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
