#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PLAYX2 -- the three questions `docs/spec-basic-audio-play.md` §7.5 leaves
open, which must be answered BEFORE a byte is spent on `X<var>;`.

  1. THE NESTING DEPTH CEILING. D-PLAYX measured ONE level (`A$="XB$;"`). Each
     level is 3 B of RAM in the design's source-cursor stack, so the ceiling is
     not a curiosity -- it is the size of a table. Chains of 3, 4, 5 and 6 are
     built here; the first one that raises names the limit.
  2. DOES THE SUBSTRING INHERIT THE OUTER STATE? D-PLAYX's row that looked like
     it could not separate inheritance from the outer state merely SURVIVING --
     the substring never changed the octave, and the reading was taken from the
     TAIL. This asks it properly: the outer sets `O7`, the substring plays a note
     with NO octave of its own, and the reading is the SUBSTRING's note. Both
     controls (`O7` and the default `O4`) are present, because a row that reads
     53 proves nothing unless the row that should read something else does.
  3. THE NAME-AND-TERMINATOR CORNERS. `XA;` with a STRING `A$` in scope is the
     interesting one: MSX names carry their type in the sigil, so does `XA;`
     look for `A` (numeric -> ERR 13, already measured for `A=5`) or find `A$`?

⏱ The wait is FRAMES, not a `FOR` loop -- the references are ~3x faster.
⚠️ THE CF-3300 IS DELIBERATELY ABSENT. Its boot-per-case delivery is mangled for
this rig (a known D-KWPLAY apparatus failure) and the harness refuses with a HARD
EXIT, which an `except Exception` cannot catch. Two sides, said out loud.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def tone(*setup: str) -> list[str]:
    """`setup` lines, wait 30 FRAMES, then read PSG R0/R1 (channel A period)."""
    body = list(setup) + [
        "T=TIME",
        "IF TIME-T<30 THEN %d",
        'PRINT"<";',
        "OUT&HA0,0:PRINT INP(&HA2);",
        "OUT&HA0,1:PRINT INP(&HA2);",
        'PRINT">":END',
        'PRINT"<E";ERR;">":END',
    ]
    lines = ["ON ERROR GOTO %d" % (10 * (len(body) + 1))] + body
    for i, l in enumerate(lines):
        if "%d" in l:
            lines[i] = l % (10 * (i + 1))
    for l in lines:
        assert len(l) <= 34, (len(l), l)
    return lines


CASES = [
    # --- controls: the two octaves every row below is read against ------------
    ("y0_ctl_o7c",  tone('PLAY"O7L1C"')),
    ("y1_ctl_o4c",  tone('PLAY"O4L1C"')),

    # --- 1. how deep does it nest? -------------------------------------------
    ("y2_depth2",   tone('A$="XB$;":B$="O7L1C"', 'PLAY"XA$;"')),
    ("y3_depth3",   tone('A$="XB$;":B$="XC$;"', 'C$="O7L1C"', 'PLAY"XA$;"')),
    ("y4_depth4",   tone('A$="XB$;":B$="XC$;":C$="XD$;"',
                         'D$="O7L1C"', 'PLAY"XA$;"')),
    ("y5_depth5",   tone('A$="XB$;":B$="XC$;":C$="XD$;"',
                         'D$="XE$;":E$="O7L1C"', 'PLAY"XA$;"')),
    ("y6_depth6",   tone('A$="XB$;":B$="XC$;":C$="XD$;"',
                         'D$="XE$;":E$="XF$;"', 'F$="O7L1C"', 'PLAY"XA$;"')),

    # --- 2. does the substring INHERIT the outer state? ----------------------
    # The substring has NO octave of its own, so its note is O7 if it inherited
    # and O4 (the default) if it did not. This is the row the first pass could
    # not separate.
    ("y7_inherit",  tone('A$="L1C"', 'PLAY"O7XA$;"')),
    # The twin: the outer sets nothing, so a DEFAULT-octave reading here is not
    # evidence of anything -- it is the baseline the row above is read against.
    ("y8_inh_base", tone('A$="L1C"', 'PLAY"XA$;"')),

    # --- 3. the name and terminator corners ----------------------------------
    # `XA;` with a STRING A$ in scope: does the sigil-less name find A$?
    ("y9_nosigil",  tone('A$="O7L1C"', 'PLAY"XA;"')),
    # a `;` that IS there, on a variable that is not
    ("ya_undef",    tone('PLAY"XZ$;"')),
    # a substring that is itself EMPTY, with the outer carrying the note
    ("yb_empty",    tone('A$=""', 'PLAY"XA$;O7L1C"')),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=8.0)
        except Exception as exc:                      # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}, NOTHING MEASURED HERE: "
                  f"{str(exc).splitlines()[0][:160]}", flush=True)
            continue
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            r = txt.rfind("RUN")
            tail = txt[r + 3:] if r >= 0 else txt
            i = tail.find("<")
            j = tail.find(">", i + 1)
            cell = tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:40]
            print(f"  {name:13} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
