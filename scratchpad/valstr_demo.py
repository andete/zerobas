#!/usr/bin/env python3
"""D-VALFLT / D-STRFLT / D-PCTTRUNC / D-VALUNDER / D-ERLENTRY — the closing demo.

Real MSX BASIC on the SHIPPING ROM, three machines, one program per row.

The BEFORE column is a RECORDED reading, not a guess: every one of these rows
was measured on this tree before the fix, in scratchpad/val_probe.py's and
scratchpad/strflt_probe.py's baselines (kept at /tmp/zerobas/val_base4.out and
/tmp/zerobas/strflt_base.out during the run).

⚠️ THREE OF THESE ROWS ARE THE CRUNCH, NOT VAL, AND THAT IS THE POINT OF THE
SESSION. `PRINT 1.7%` and `PRINT 1E-70` are ordinary program lines; they were
wrong for every program, and they were found only because every VAL row was
given a LITERAL TWIN before the wiring was written.

Readout shape inherited from scratchpad/deffn_demo.py: every row puts its VALUE
inside brackets, so a row that produced nothing reads <NO OUTPUT> -- a missing
measurement, which is not agreement.

🔴 AND THE FIRST DRAFT SCORED 20/20 WITH THREE OF THOSE ROWS AGREEING FOR THE
WRONG REASON. `A=40000.5%`, `A=1E-70` and `A=1E-65` were written as ORDINARY
PROGRAM LINES -- and the crunch rejects those AT ENTRY, so line 20 was never
stored, `A` was never assigned, and `PRINT A` read an unassigned 0 on every
machine, before the fix and after it. Two rows were BLIND and the third's
`before` belonged to a different program shape entirely.
🎯 A TYPE-IN REJECT CANNOT BE READ THROUGH THE VALUE IT FAILED TO ASSIGN. The
two exponent rows now type the bad line BEHIND an intact program and read `ERR`,
which is the thing that actually differs (6 vs 0); the `%` row reads its wrap
through VAL, where the concatenated range check produced a VALUE (-25536) rather
than a refusal. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
"""
from __future__ import annotations
import os, re, sys
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

# label, what it exercises, program lines, the RECORDED pre-session zb reading
CASES = [
    # --- D-VALFLT: VAL calls the tokeniser's own scanner ---------------------
    ("val.frac",  "a fraction -- VAL was integer-only",
     ['PRINT"[";VAL("1.5");"]"'], "1"),
    ("val.exp",   "an exponent",
     ['PRINT"[";VAL("1E3");"]"'], "1"),
    ("val.space", "blanks INSIDE a number are skipped, so no copy can be bounded",
     ['PRINT"[";VAL("1 E 3");"]"'], "1"),
    ("val.sign",  "a blank between the sign and the digits",
     ['PRINT"[";VAL(" - 12");"]"'], "0"),
    ("val.wrap",  "🔴 A SILENT WRAP: past int16 the old parser rolled over",
     ['PRINT"[";VAL("40000");"]"'], "-25536"),
    ("val.ovf",   "and past the FLOAT range it must refuse",
     ['PRINT"[";VAL("1E99");"]"'], "1"),
    ("val.hex",   "🟢 the base literals keep their own scan -- unchanged",
     ['PRINT"[";VAL("&HFF");"]"'], "255"),
    # --- D-STRFLT: STR$ of a non-integer -------------------------------------
    ("str.frac",  "STR$ never looked at FACTYP",
     ['PRINT"[";STR$(1.5);"]"'], "1"),
    ("str.big",   "...so anything past int16 came back as the wrapped int",
     ['PRINT"[";STR$(1E9);"]"'], "0"),
    ("str.len",   "🔴 THE SPACE NO VALUE ROW COULD SEE: LEN(STR$(1.5)) is 4",
     ['PRINT"[";LEN(STR$(1.5));"]"'], "2"),
    ("str.fence", "...and the fence that shows WHICH space it is",
     ['PRINT"[<";STR$(1.5);">]"'], "< 1>"),
    ("str.trip",  "the round trip both halves have to agree on",
     ['PRINT"[";VAL(STR$(1.5));"]"'], "1"),
    # --- the crunch defects the twinning found -- ORDINARY PROGRAM LINES -----
    ("crn.pct",   "🔴 `%` CONCATENATED the fraction instead of truncating",
     ['PRINT"[";1.7%;"]"'], "17"),
    ("crn.pct25", "...on a half, where rounding and truncating differ",
     ['PRINT"[";2.5%;"]"'], "25"),
    ("crn.pctbig","...and its range check ran on the CONCATENATION: a WRAP",
     ['PRINT"[";VAL("40000.5%");"]"'], "-25536"),
    ("crn.under", "🔴 a silent 0 where both references STOP THE LINE (ERR 6)",
     ['70 X=1E-70', 'PRINT"[";ERR;"]"'], "0"),
    ("crn.e65",   "🟢 ...but 1E-65 really is 0 and raises NOTHING (the boundary)",
     ['70 X=1E-65', 'PRINT"[";ERR;"]"'], "0"),
    # --- D-ERLENTRY ----------------------------------------------------------
    ("erl.entry", "a line rejected at ENTRY leaves ERL = 65535, not 0",
     ['70 X=1E99', 'PRINT"[";ERL;"]"'], "0"),
    ("erl.badln", "...and so does an out-of-range line number (the other arm)",
     ['70000 X=1', 'PRINT"[";ERL;"]"'], "0"),
    ("erl.none",  "🟢 the control: no bad line typed at all",
     ['PRINT"[";ERL;"]"'], "0"),
]
BR = re.compile(r"\[([^\]]*)\]")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = BR.search(cap)
    return (" ".join(m.group(1).split()) or "<empty>") if m else "<NO OUTPUT>"


def main() -> int:
    step = float(os.environ.get("VALSTR_DEMO_STEP", "4.0"))
    agree = same = 0
    for label, what, prog, before in CASES:
        # the bad lines (`70 ...`, `70000 ...`) are TYPED, not renumbered: they
        # carry their own line number and are rejected at entry, which is the
        # whole subject of the erl.* rows.
        body = ["10 ON ERROR GOTO 900", "15 SCREEN 0"]
        typed, k = [], 0
        for ln in prog:
            if ln.split(" ", 1)[0].isdigit():
                typed.append(ln)
            else:
                body.append(f"{20+10*k} {ln}")
                k += 1
        body += ['890 END', '900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
        row = {}
        for sd, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + typed + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=step, cap_gap=10.0,
                timeout=300.0)
            row[sd] = face(caps[0])
        ok_refs = row["vg8020"] == row["cf3300"]
        ok_zb = row["zb"] == row["vg8020"]
        agree += ok_refs
        same += ok_zb
        print(f"  {label:11s} {'refs-agree' if ok_refs else 'REFS DIFFER':12s} "
              f"{'zb=same' if ok_zb else 'zb=DIFF':8s} "
              f"before={before!r:10s} vg={row['vg8020']!r} cf={row['cf3300']!r} "
              f"zb={row['zb']!r}   [{what}]", flush=True)
    print(f"\n  {same} of {len(CASES)} zerobas readings match the VG-8020; "
          f"{agree} of {len(CASES)} references agree with each other", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
