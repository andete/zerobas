import os, sys, re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
Q="A=POINT(28,28):B=POINT(16,28):C=POINT(28,16):D=POINT(10,10)"
PR='SCREEN0:PRINT"R";A;B;C;D:END'
CASES=[
 ("sanity_pset",["PSET(28,28),9"]),
 ("boxonly",["LINE(16,16)-(40,40),15,B"]),
 ("fill15_b15",["LINE(16,16)-(40,40),15,B","PAINT(28,28),15,15"]),
 ("fill9_b15",["LINE(16,16)-(40,40),15,B","PAINT(28,28),9,15"]),
]
for label,setup in CASES:
    lines=["COLOR15,1,1:SCREEN2:CLS"]+setup+[Q,PR]
    try:
        o=omsx_repl.run_cases(REF,[("stored",lines)],batch=False,capture="screen",
                              step=3.0,cap_gap=3.0,timeout=120.0)[0]
    except SystemExit as e:
        print(f"  {label:12s} TIMEOUT/{e}"); continue
    txt=" ".join((o or "").split())
    m=re.search(r"R\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)",txt)
    print(f"  {label:12s} int/lbrd/top/out = {m.groups() if m else None}   raw={txt[:44]!r}")
