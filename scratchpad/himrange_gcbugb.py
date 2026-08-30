#!/usr/bin/env python3
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl as R
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
lines = ['CLEAR 400,50000','V=0:A$=STRING$(60,66)','V=VARPTR(A$):POKEV+6,200',
         'POKEV+7,&HE0:POKEV+8,&HBA','P$=STRING$(250,67)','W=PEEK(V+6)',
         'PRINT"[";LEN(P$);W;"]"']
zr = R.run_cases(ZB, [("direct", lines)], batch=True, reset=("NEW","CLS"),
                 step=150.0, boot=8.0)[0]
print("span:", repr(R.result_span(zr)))
print("want: ' 250  250 '")
