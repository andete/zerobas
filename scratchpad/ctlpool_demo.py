#!/usr/bin/env python3
"""The session's closing demo: real MSX BASIC, run on both references and here.

D-CTLCROSS in a program a person would actually write -- a `NEXT` that belongs
to a `FOR` opened before the `GOSUB` it now sits inside. Every line is kept
short so no echo wraps and the screen tail is readable as-is.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

PROG = ["10 ONERRORGOTO200",
        "20 FORI=1TO1",
        "30 GOSUB100",
        '40 PRINT"BACK IN LOOP"',
        "50 GOTO300",
        '100 PRINT"IN SUB: NEXT I"',
        "110 NEXTI",
        '120 PRINT"NEXT MATCHED"',
        "130 RETURN",
        '200 PRINT"ERR";ERR;"IN";ERL',
        "210 RESUME300",
        '300 PRINT"DONE"']

SIDES = [("vg8020", "Philips_VG_8020", 8.0, ("NEW", "CLS")),
         ("cf3300", "National_CF-3300", 14.0, ("", "SCREEN 0", "NEW", "CLS")),
         ("zb", os.environ.get("ZEROBAS_BASIC_MACHINE",
                               "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW", "CLS"))]

for name, machine, boot, reset in SIDES:
    caps = omsx_repl.run_cases(machine, [("demo", list(reset) + PROG + ["RUN"])],
                               batch=False, reset=(), boot=boot, step=12.0,
                               cap_gap=8.0, timeout=300.0)
    # The capture is one string of 40-column SCREEN ROWS with no newlines --
    # split it back into rows and take everything after the `RUN` echo. (The
    # first cut used result_span_after_echo and read <no output> on all three:
    # an unnamed outcome reads as no outcome, and here it would have read as
    # "the demo does not work" rather than "the reader is wrong".)
    raw = "".join(caps[0] or "")
    rows = [raw[i:i + 40].rstrip() for i in range(0, len(raw), 40)]
    # ⚠️ THE PROMPT IS NOT `Ok` ON EVERY MACHINE. zerobas prompts `ZB`, so its
    # echo row reads `ZBRUN` and its terminator is `ZB` -- an exact match on
    # "RUN"/"Ok" found neither and printed "nothing was measured" for a run that
    # had measured the whole divergence. The prompt is part of the apparatus.
    stripped = [r.strip() for r in rows]
    idx = next((i for i, r in enumerate(stripped) if r.endswith("RUN")), None)
    if idx is None:
        rows = ["<no RUN echo -- nothing was measured>"]
    else:
        rows = rows[idx + 1:]
    print(f"\n=== {name} ({machine})")
    for line in rows:
        if not line.strip():
            continue
        if line.strip() in ("Ok", "ZB"):
            break
        print("   ", line.strip())
