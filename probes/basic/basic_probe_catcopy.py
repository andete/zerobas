#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""catcopy-acceptance (D-CATCOPY): INSTR does not copy an operand it only reads.

Found by the program ladder's calendar (probes/programs/L2_calendar.bas, run
without CLEAR): word-wrapping a note with `INSTR(P,T$+" "," ")` ran out of the
default 200-byte string space a month earlier than on the VG-8020. INSTR copied
BOTH its string arguments, even a concatenation that was already an owned temp,
and even a plain variable. The VG-8020 copies neither.

Two programs, each LPRINTing every result and FRE(""), with ON ERROR noting
any error 14 and resuming:
  * temp -- `T$+" "` as INSTR's first argument with 104 bytes free (and, as
    controls, the same concatenation under LEN, LEFT$, ASC and an assignment);
  * var  -- a 122-character T$ searched with 78 bytes free, as the first
    argument, with a start position, and against a variable / LEFT$ second one.
The printer logs must equal the VG-8020's on both zerobas targets.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

ROWS = {"temp": "scratchpad/catcopy_temp.bas", "var": "scratchpad/catcopy_var.bas"}


def main():
    bad = 0
    for row, path in ROWS.items():
        text = open(os.path.join(REPO, path)).read()
        ref = run_programs.run(run_programs.REF, f"catcopy_{row}", text)
        print(f"{row:5} {run_programs.REF:30} {ref[0]}  {ref[1].strip()!r}")
        for m in run_programs.ZB:
            zb = run_programs.run(m, f"catcopy_{row}", text)
            ok = zb[1] == ref[1] and ref[1].strip() != ""
            bad += not ok
            print(f"{row:5} {m:30} {zb[0]}  {'SAME' if ok else 'DIVERGES'}")
            if not ok:
                print(f"      zb: {zb[1].strip()!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: INSTR reads its operands without copying "
          f"a temp or a variable, as the VG-8020 does")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
