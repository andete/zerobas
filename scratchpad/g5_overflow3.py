import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
def mk(himem,stepx):
    return ['10 ON ERROR GOTO 90',
      f'20 CLEAR 50,&H{himem:04X}',
      '30 COLOR15,1,1:SCREEN2:CLS',
      '40 LINE(8,8)-(248,180),15,B',
      f'50 FORX=20TO240STEP{stepx}:LINE(X,20)-(X,160),15:NEXT',
      '60 PAINT(126,170),15,15',
      '70 SCREEN0:PRINT"DONE":END',
      '90 SCREEN0:PRINT"ERR";ERR:END','RUN']
def run(himem,stepx):
    o=omsx_repl.run_cases(REF,[("direct",mk(himem,stepx))],batch=False,capture="screen",
                          step=60.0,cap_gap=8.0,timeout=200.0)[0]
    txt=" ".join((o or "").split())
    m=re.search(r"(DONE|ERR\s*-?\d+)",txt)
    print(f"  himem=${himem:04X} step{stepx} -> {m.group(0) if m else '?(empty)'}   raw={txt[:44]!r}")
for hm in (0x9000,0x8C00,0x8800,0x8500):
    run(hm,3)
