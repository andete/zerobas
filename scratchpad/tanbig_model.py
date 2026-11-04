# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TANBIG: black-box model of the reference SIN/COS reduction, scored against tanbig_run.out / tanbig_bisect.out."""
from decimal import Decimal as D, getcontext, ROUND_HALF_UP
import math
getcontext().prec=40
def r14(x):
    if x==0: return x
    e=x.adjusted()
    q=D(1).scaleb(e-13)
    return x.quantize(q,rounding=ROUND_HALF_UP)
C=r14(D(1)/(2*D('3.14159265358979323846264338327950288')))
HP=r14(D('1.57079632679489661923132169163975144'))
def frac_sin(x):
    p=r14(x*C)
    f=p-int(p)
    return math.sin(float(f)*2*math.pi), f
ref={'1E10':(-.48725012572533,.87326245480993),'1E11':(.92977648588827,.36812455268468),
 '1E12':(-.58778525229247,.80901699437495),'1E13':(0,.95105651629516),'2E13':(0,.95105651629516),
 '3E13':(0,.95105651629516),'5E13':(0,.95105651629516),'7E13':(0,0),'1E14':(0,0),'1E15':(0,0),'1E38':(0,0)}
for k,(s,c) in ref.items():
    x=D(k)
    ms,fs=frac_sin(x); mc,fc=frac_sin(r14(x+HP))
    print(f"{k:5} sin {ms:+.14f} ref {s:+.14f} f={fs}  cos {mc:+.14f} ref {c:+.14f} f={fc}")
print("---")
for k,ref in (('1000',.82687954054849),('100',None),('10',None)):
    s,f=frac_sin(D(k)); print(k, f"{s:.14f}", ref, "true", f"{math.sin(float(k)):.14f}", f)
