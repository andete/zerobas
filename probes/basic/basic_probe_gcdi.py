#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""gcdi-acceptance (D-GCDI): string work must not hold interrupts off.

Found by the program ladder (probes/programs/, L2_addr): zerobas ran its string
garbage collector -- reached from the string-heap tenant AND from the arrays
tenant's string-element store -- with interrupts disabled, so frame interrupts
were missed. The ladder's gap watch then found the math tenants (`^`, RND, ...)
doing the same; that half is NOT fixed (D-GCDI2) -- see sub/mathwrap.asm. TIME ran slow, and a key typed meanwhile was lost (a RETURN
vanished, two answers ran together). The VG-8020 kept every frame.

Each row runs a string-churning program under a JIFFY write watchpoint and
types a line during the churn:
  * `gaps` -- frame-to-frame intervals over 30 ms while the program ran, and
    the longest. PASS: no more such gaps than the VG-8020 (none) and none over
    50 ms. The COUNT is the binding half: the arrays knife lost a key with its
    longest gap at 35 ms -- 51 of them (scratchpad/gcdi_knife.out).
  * the typed line must arrive whole, as on the VG-8020 (the control).

Clean-room: typed keys and a tape in; the printer port and work-area RAM
(JIFFY, CURLIN, KEYBUF pointers) out. No reference ROM byte is read.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

LIMIT_S = 0.050
ROWS = {
    # scalar churn: the string-heap tenant (STRING$, concatenation, GC)
    "scalar": ('1 REM @ANSWERS THE QUICK BROWN FOX\n'
               '10 DIM S$(20):FOR I=1 TO 40:FOR J=1 TO 20:S$(J)=STRING$(8,64+J)+"X"'
               ':NEXT J,I\n'
               '20 LINE INPUT A$:LPRINT "CP 1 [";A$;"]";LEN(A$)\n'),
    # array-element stores with the space nearly full: the arrays tenant's
    # COPY_STR -> heap_alloc -> a whole GC per store
    "array": ('1 REM @ANSWERS JUMPS OVER THE LAZY DOG\n'
              '10 DIM N$(9):FOR I=1 TO 9:N$(I)=STRING$(19,64+I):NEXT\n'
              '20 FOR R=1 TO 40:FOR I=1 TO 8:N$(I)=N$(I+1):NEXT:N$(9)=N$(1):NEXT\n'
              '30 LINE INPUT A$:LPRINT "CP 1 [";A$;"]";LEN(A$);FRE("")\n'),
    # NO math row: math_wrap still holds DI (D-GCDI2, TODO.md) -- an `ei` there
    # starved PLAY (play-trace-acceptance di_safety) and was reverted.
}


def main():
    bad = 0
    for row, text in ROWS.items():
        ref = run_programs.run(run_programs.REF, f"gcdi_{row}", text, gaps=True, typing="type")
        print(f"{row:7} {run_programs.REF:30} {ref[0]}  {ref[1].strip()}")
        for m in run_programs.ZB:
            zb = run_programs.run(m, f"gcdi_{row}", text, gaps=True, typing="type")
            mx = float(zb[0].split("max=")[1].split()[0]) if "max=" in zb[0] else 99.0
            n = int(zb[0].split("gaps=")[1].split()[0]) if "gaps=" in zb[0] else 999
            n_ref = int(ref[0].split("gaps=")[1].split()[0]) if "gaps=" in ref[0] else 0
            ok = zb[1] == ref[1] and ref[1].strip() != "" and mx <= LIMIT_S and n <= n_ref
            bad += not ok
            print(f"{row:7} {m:30} {zb[0]}  {zb[1].strip()}  {'SAME' if ok else 'DIVERGES'}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: string work keeps the frame interrupt "
          f"(no more 30 ms gaps than the VG-8020, none over {LIMIT_S * 1000:.0f} ms) "
          f"and type-ahead arrives whole")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
