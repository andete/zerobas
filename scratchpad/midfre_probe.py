"""Isolate: A$ after a MID$()= and a FRE("") read DDDD on the VG-8020, AQCD on
zerobas (s16sh's first cut, also on HEAD's ROM). Which step makes the difference?"""
import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl

P = {
    "midonly": ['A$="AB"+"CD":MID$(A$,2,1)="Q":PRINT"[A";A$;"]"'],
    "midfre": ['A$="AB"+"CD":MID$(A$,2,1)="Q":X=FRE(""):PRINT"[A";A$;"]"'],
    "cpyfre": ['A$="AB"+"CD":F$=A$:MID$(A$,2,1)="Q":X=FRE(""):PRINT"[A";A$;F$;"]"'],
    "s16like": ['A$="AB"+"CD":B$=LEFT$(A$,3)+MID$(A$,2,2):MID$(A$,2,1)="Q":F$=A$:X=FRE(""):PRINT"[A";A$;F$;"]"'],
    "litfre": ['A$="ABCD":MID$(A$,2,1)="Q":X=FRE(""):PRINT"[A";A$;"]"'],
}
for name in sys.argv[1:] or list(P):
    for m in ("C-BIOS_MSX1_EU_REPACK_NODISK", "Philips_VG_8020"):
        scr = omsx_repl.run_cases(m, [("direct", ["NEW", "CLEAR 200"] + P[name])], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=10.0)[0]
        r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
        keep = [x.strip() for x in r if x.strip().startswith("[A") or "rror" in x]
        print(f"{name:8} {m:30} {' | '.join(keep) or '<nothing matched>'}", flush=True)
