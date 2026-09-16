#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PLAYX scout -- what `X<var>;` ACTUALLY MEANS, before a byte is spent on it.

D-KWPLAY measured that `X<var>;` RUNS on both references and raises ERR 5 here,
and TODO.md's item then scouted WHERE a fix could live (main-side, because
`var_find_typed`/`str_eval` are main page 1 and the MML parser is a sub page-1
tenant that may not escape there). What nobody has measured is the SEMANTICS,
and an implementation cannot be written from "it runs":

  1. DOES THE OUTER STRING CONTINUE after the substring? That is the difference
     between a CALL (save the cursor, resume) and a JUMP (the rest is dead).
     Everything about the re-entrant shape depends on it.
  2. IS THE `;` REQUIRED, or is it a separator only when something follows?
  3. DOES PARSE STATE (octave, length) CROSS the boundary -- in, and back out?
     A substring that inherits O7 and leaks its own O4 back is one machine; a
     substring with its own scope is another.
  4. DOES IT NEST?  `A$="XB$;"`.
  5. Is the command case-insensitive (`x`)?
  6. What is a NUMERIC variable there -- and an UNDEFINED string?

⚠️ EVERY ROW IS A TONE-PERIOD READING WITH ITS OWN CONTROL. A row that reads 53
proves nothing unless the row that should read something ELSE does. The controls
are the same phrase written without `X`.
⏱ THE WAIT IS FRAMES (`TIME`), NOT A `FOR` LOOP -- the references are ~3x faster,
so the same iteration count is a shorter wall-clock wait there, which is exactly
what made D-KWPLAY's scout-1 duration rows disagree for a reason that was not
PLAY.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

# 🔴 ORDER AND ISOLATION ARE PART OF THE INSTRUMENT. Run 1 put the CF-3300
# SECOND and its boot-per-case delivery was mangled (a known D-KWPLAY failure on
# that machine) -- `run_cases` raised, and the VG-8020 column survived only
# because it had already printed while zerobas, the SUBJECT, never ran at all.
# An apparatus failure on one machine is not a reading on any machine, and it
# must not be able to cost the others: subject first, each column isolated.
MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020", "National_CF-3300")


def tone(*setup: str) -> list[str]:
    """`setup` lines, wait 30 FRAMES, then read PSG R0/R1 (channel A period).

    `<a b>` = sounding at that period; `<E n>` = the statement trapped ERR n."""
    body = list(setup) + [
        "T=TIME",
        "IF TIME-T<30 THEN %d",          # patched with its own line number
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
        assert len(l) <= 34, (len(l), l)     # the stored-line cap
    return lines


CASES = [
    # --- the baseline both machines already agree on -------------------------
    ("x0_ctl_o7c",  tone('PLAY"O7L1C"')),
    ("x1_sub",      tone('A$="O7L1C"', 'PLAY"XA$;"')),
    # --- 1. does the OUTER string continue after the substring? --------------
    ("x2_ctl_o4e",  tone('PLAY"O4L1E"')),
    ("x2_tail",     tone('A$="O7L64C"', 'PLAY"XA$;O4L1E"')),
    # --- 2. is the ';' required? ---------------------------------------------
    ("x3_nosemi",   tone('A$="O7L1C"', 'PLAY"XA$"')),
    # --- 3. does parse STATE cross the boundary, in and out? -----------------
    ("x4_ctl_o7d",  tone('PLAY"O7L1D"')),
    ("x4_ctl_o4d",  tone('PLAY"O4L1D"')),
    ("x4_stateout", tone('A$="O7L64C"', 'PLAY"XA$;L1D"')),
    ("x5_statein",  tone('A$="L64C"', 'PLAY"O7XA$;L1D"')),
    # --- 4. does it NEST? ----------------------------------------------------
    ("x6_nest",     tone('A$="XB$;"', 'B$="O7L1C"', 'PLAY"XA$;"')),
    # --- 5. lower case -------------------------------------------------------
    ("x7_lower",    tone('A$="O7L1C"', 'PLAY"xA$;"')),
    # --- 6. the wrong kinds of variable --------------------------------------
    ("x8_numvar",   tone('A=5', 'PLAY"XA;"')),
    ("x9_undef",    tone('PLAY"XZ$;O7L1C"')),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        how = "boot-per-case"
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=8.0)
        except Exception as exc:                      # noqa: BLE001
            # ⚠️ A FALLBACK IS A DIFFERENT INSTRUMENT, NOT A RETRY -- batch
            # shares one boot, so a case can inherit its predecessor's state.
            # Worth it only because every case ENDs and reads a live PSG
            # register, and because the alternative is no second reference at
            # all on the CF-3300, whose boot-per-case delivery is a known
            # D-KWPLAY apparatus failure. The column says how it was delivered.
            print(f"  ⚠️ boot-per-case MANGLED on {mach} "
                  f"({str(exc).splitlines()[0][:90]}); retrying in BATCH",
                  flush=True)
            how = "BATCH (boot-per-case mangled -- a weaker delivery)"
            try:
                raws = omsx_repl.run_cases(mach, specs, batch=True, cap_gap=8.0)
            except Exception as exc2:                 # noqa: BLE001
                # NOT a column of failures -- NO column. Say which.
                print(f"  🔴 APPARATUS FAILURE on {mach}, NOTHING MEASURED "
                      f"HERE: {str(exc2).splitlines()[0][:160]}", flush=True)
                continue
        print(f"  (delivery: {how})", flush=True)
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            r = txt.rfind("RUN")                 # the fence is in the LISTING too
            tail = txt[r + 3:] if r >= 0 else txt
            i = tail.find("<")
            j = tail.find(">", i + 1)
            cell = tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:40]
            print(f"  {name:13} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
