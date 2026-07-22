import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
def mk(stepx, budget_line):
    # box; vertical walls every stepx from y=20..160 (channels open at the bottom
    # corridor y=162..178); fill from the bottom -> all channels stack at once.
    return ['10 ON ERROR GOTO 90',
      '20 COLOR15,1,1:SCREEN2:CLS',
      '30 LINE(8,8)-(248,180),15,B',
      f'40 FORX=20TO240STEP{stepx}:LINE(X,20)-(X,160),15:NEXT',
      '60 PAINT(126,170),15,15',
      '70 SCREEN0:PRINT"DONE":END',
      '90 SCREEN0:PRINT"ERR";ERR:END','RUN']
def run(label,stepx,step):
    o=omsx_repl.run_cases(REF,[("direct",mk(stepx,0))],batch=False,capture="screen",
                          step=step,cap_gap=8.0,timeout=260.0)[0]
    txt=" ".join((o or "").split())
    m=re.search(r"(DONE|ERR\s*-?\d+)",txt)
    print(f"  {label:16s} -> {m.group(0) if m else '?(empty)'}   raw={txt[:46]!r}")
run("comb_step8", 8, 60.0)
run("comb_step4", 4, 60.0)
run("comb_step3", 3, 90.0)
