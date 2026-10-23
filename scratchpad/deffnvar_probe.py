#!/usr/bin/env python3
"""D-DEFFNVAR: what does a `DEF FN` put in the variable table?

Our own program: one DEF FN, then a variable, then it PRINTs the first 20 bytes from
VARTAB ($F6C2) and TXTTAB ($F676) -- interpreter DATA in RAM (the variable table),
read with PEEK on each machine; no ROM byte, no code.

    10 DEFINT A-Z:DEF FNA(X)=X+1:B=5
    20 V!=PEEK(&HF6C2)+256!*PEEK(&HF6C3)    (V! single: an address past 32767)
    30 FOR I=0 TO 19:PRINT RIGHT$("0"+HEX$(PEEK(V!+I)),2);:NEXT:PRINT
    40 PRINT "T";HEX$(PEEK(&HF676)+256*PEEK(&HF677))

    python3 -u scratchpad/deffnvar_probe.py
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

TAIL = ["20 V!=PEEK(&HF6C2)+256!*PEEK(&HF6C3)",
        '30 FOR I=0 TO 27:PRINT RIGHT$("0"+HEX$(PEEK(V!+I)),2);:NEXT:PRINT',
        '40 PRINT "T";HEX$(PEEK(&HF676)+256*PEEK(&HF677))',
        "RUN"]
# line 10 per case; every case ends with B=5, so B marks where the DEF FN entries stop
CASES = {"one":     "10 DEFINT A-Z:DEF FNA(X)=X+1:B=5",
         "two":     "10 DEFINT A-Z:DEF FNA(X,Y)=X+Y:B=5",
         "exists":  "10 DEFINT A-Z:Y=7:DEF FNA(X,Y)=X+Y:B=5",
         "noparm":  "10 DEFINT A-Z:DEF FNA=7:B=5",
         "string":  "10 DEFINT A-Z:DEF FNA$(X$)=X$:B=5",
         "aryform": "10 DEFINT A-Z:DEF FNA(C(1))=1:B=5",
         "dupform": "10 DEFINT A-Z:DEF FNA(X,X)=X:B=5",
         "suffix":  "10 DEFINT A-Z:DEF FNA(X!,Y#)=X!:B=5"}
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]   # the RAM rung authority, and zerobas


def main():
    for m in sys.argv[1:] or MACHINES:
        for name, l10 in CASES.items():
            scr = omsx_repl.run_cases(m, [("direct", [l10] + TAIL)], batch=False, boot=14.0,
                                      reset=("SCREEN 0:WIDTH 40", "NEW"), step=4.0,
                                      run_gap=10.0)[0]
            rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
            # 28 bytes print as 56 hex digits: the row and the start of the next
            flat = "".join(r.strip() for r in rows)
            import re
            m2 = re.search(r"[0-9A-F]{56}", flat)
            print(f"{m:30s} {name:7s} {m2.group(0) if m2 else 'NO READING'}", flush=True)


if __name__ == "__main__":
    main()
