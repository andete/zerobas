#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""gcdi-acceptance (D-GCDI): string work must not hold interrupts off.

Found by the program ladder (probes/programs/, L2_addr): zerobas ran its string
garbage collector -- reached from the string-heap tenant AND from the arrays
tenant's string-element store -- with interrupts disabled, so frame interrupts
were missed. The ladder's gap watch then found the math tenants (`^`, RND, ...)
doing the same (D-GCDI2, fixed 2026-10-29 with htimi_guard serving the frame). TIME ran slow, and a key typed meanwhile was lost (a RETURN
vanished, two answers ran together). The VG-8020 kept every frame. D-LATEINT
(2026-10-29) added `dimshift` (the arrays tenant's block moves) and `raise` (an
error raised inside a sub2 statement left the ON ERROR handler under DI).

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
    # READ's DATA scan (the readdata tenant, D-GCDI3): RESTORE before every READ
    # makes each one walk 60 REM lines to the DATA at the end, ~90 ms in DI before
    "read": ('1 REM @ANSWERS HOW VEXINGLY QUICK DAFT ZEBRAS\n'
             '10 FOR K=1 TO 25:RESTORE:READ A,B$:NEXT\n'
             '20 LINE INPUT A$:LPRINT "CP 1 [";A$;"]";LEN(A$);A;B$\n'
             '30 END\n'
             + "".join(f"{100 + i} REM {'FILLER TEXT ' * 3}\n" for i in range(60))
             + '900 DATA 42,FOUND\n'),
    # CIRCLE's arc arithmetic (circleparse_tenant, page 1, D-GCDI4): ~41 ms in DI
    "circle": ('1 REM @ANSWERS SPHINX OF BLACK QUARTZ JUDGE MY VOW\n'
               '10 SCREEN 2:FOR K=1 TO 30:CIRCLE (128,96),20+K,15,K/10,K/5:NEXT:SCREEN 0\n'
               '20 LINE INPUT A$:LPRINT "CP 1 [";A$;"]";LEN(A$)\n'),
    # PLAY's MML parser (play_parse_tenant, page 1, D-GCDI5): three voices of 20
    # notes; L4_sprite's two short voices held DI ~40 ms
    "play": ('1 REM @ANSWERS WALTZ BAD NYMPH FOR QUICK JIGS VEX\n'
             '10 A$="T255L64O4CDEFGABO5CDEFGABO4CDEFGA":B$="T255L64O3"+MID$(A$,10)\n'
             '20 FOR K=1 TO 4:PLAY A$,B$,A$:NEXT\n'
             '30 LINE INPUT C$:LPRINT "CP 1 [";C$;"]";LEN(C$)\n'),
    # the math tenants (math_wrap, D-GCDI2): `^` by a negative power and RND, each
    # one long sub-ROM call -- a single `^` held DI for 165 ms in L1_loan
    "math": ('1 REM @ANSWERS PACK MY BOX WITH JUGS\n'
             '10 FOR K=1 TO 40:X=1.00625^-K:Y=RND(1)*K:NEXT\n'
             '20 LINE INPUT A$:LPRINT "CP 1 [";A$;"]";LEN(A$)\n'),
    # the arrays tenant's block moves (D-LATEINT): a new scalar shifting 9.6 KB of
    # arrays up, DIM's zero-fill of 5.6 KB, ERASE sliding 4.8 KB down -- each a
    # single LDDR / fill / LDIR that ran under DI. ~20 KB: the DISK target fits it
    "dimshift": ('1 REM @ANSWERS GRUMPY WIZARDS MAKE TOXIC BREW\n'
                 '10 DIM B(600),D(600):Q0=1:Q1=1:Q2=1:Q3=1:Q4=1:Q5=1:Q6=1:Q7=1:Q8=1:Q9=1\n'
                 '20 FOR K=1 TO 4:DIM A(700),C(600):ERASE A:ERASE C:NEXT\n'
                 '30 LINE INPUT A$:LPRINT "CP 1 [";A$;"]";LEN(A$);Q9;FRE(0)>0\n'),
    # an error raised through sub2's p0cb abandons its CALSLT, so sr_slot's `ei`
    # never ran and the ON ERROR handler went on under DI until its first variable
    # (D-LATEINT, the ladder's L4_errors). `OPEN "NUL:"` is 56 in sub2 on the
    # diskless target only (on DISK the disk path raises it, and was always clean);
    # the handler's variable-free stretch is longer than a frame
    "raise": ('1 REM @ANSWERS THE FIVE BOXING WIZARDS JUMP\n'
              '10 ON ERROR GOTO 100:FOR K=1 TO 6:OPEN "NUL:" FOR INPUT AS #1:NEXT\n'
              '20 LINE INPUT A$:LPRINT "CP 1 [";A$;"]";LEN(A$)\n'
              '30 END\n'
              '100 ' + ':'.join(['LPRINT "AT";ERL'] * 8) + ':RESUME NEXT\n'),
}


def main():
    bad = 0
    for row, text in ROWS.items():
        ref = run_programs.run(run_programs.REF, f"gcdi_{row}", text, gaps=True, typing="type")
        one = lambda lpt: " | ".join(ln.strip() for ln in lpt.strip().splitlines())  # one line per row (raise's log has several)
        print(f"{row:7} {run_programs.REF:30} {ref[0]}  {one(ref[1])}")
        for m in run_programs.ZB:
            zb = run_programs.run(m, f"gcdi_{row}", text, gaps=True, typing="type")
            mx = float(zb[0].split("max=")[1].split()[0]) if "max=" in zb[0] else 99.0
            n = int(zb[0].split("gaps=")[1].split()[0]) if "gaps=" in zb[0] else 999
            n_ref = int(ref[0].split("gaps=")[1].split()[0]) if "gaps=" in ref[0] else 0
            ok = zb[1] == ref[1] and ref[1].strip() != "" and mx <= LIMIT_S and n <= n_ref
            bad += not ok
            print(f"{row:7} {m:30} {zb[0]}  {one(zb[1])}  {'SAME' if ok else 'DIVERGES'}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: string work keeps the frame interrupt "
          f"(no more 30 ms gaps than the VG-8020, none over {LIMIT_S * 1000:.0f} ms) "
          f"and type-ahead arrives whole")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
