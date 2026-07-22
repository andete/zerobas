import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
# Serpentine comb inside a box: top teeth + bottom teeth interleaved -> the C==B
# fill must weave through every gap, fragmenting into many stacked spans.
def run(label,prog,step=40.0):
    o=omsx_repl.run_cases(REF,[("stored",prog)],batch=False,capture="screen",
                          step=step,cap_gap=8.0,timeout=200.0)[0]
    txt=" ".join((o or "").split())
    m=re.search(r"(DONE|ERR\s*-?\d+)",txt)
    print(f"  {label:20s} -> {m.group(0) if m else '?'}   raw={txt[:50]!r}")

# maze density sweep via STEP; ON ERROR -> line 900
def maze(step_x):
    return [
      "ON ERROR GOTO 90",
      "COLOR15,1,1:SCREEN2:CLS",
      "LINE(8,8)-(248,180),15,B",
      f"FORX=20TO240STEP{step_x}:LINE(X,8)-(X,150),15:NEXT",
      f"FORX={20+step_x//2}TO240STEP{step_x}:LINE(X,180)-(X,40),15:NEXT",
      "PAINT(12,12),15,15",
      'SCREEN0:PRINT"DONE":END',
      "","","",  # pad lines 8..? not used
    ]
# Build with explicit numbering so 90 is the handler.
def numbered(prog):
    body=[ln for ln in prog if ln!=""]
    num=[f"{10*(i+1)} {ln}" for i,ln in enumerate(body[:-1])]  # exclude handler placeholder
    # last real body line is the DONE; then handler at 90
    return None
# simpler: hand-number
def mk(step_x):
    lines=[
      '10 ON ERROR GOTO 90',
      '20 COLOR15,1,1:SCREEN2:CLS',
      '30 LINE(8,8)-(248,180),15,B',
      f'40 FORX=20TO240STEP{step_x}:LINE(X,8)-(X,150),15:NEXT',
      f'50 FORX={20+step_x//2}TO240STEP{step_x}:LINE(X,180)-(X,40),15:NEXT',
      '60 PAINT(12,12),15,15',
      '70 SCREEN0:PRINT"DONE":END',
      '90 SCREEN0:PRINT"ERR";ERR:END',
      'RUN']
    return lines
for sx in (16,8,6,4):
    run(f"maze_step{sx}", ("direct-marker",) and None) if False else None
    o=omsx_repl.run_cases(REF,[("direct",mk(sx))],batch=False,capture="screen",
                          step=40.0,cap_gap=8.0,timeout=220.0)[0]
    txt=" ".join((o or "").split())
    m=re.search(r"(DONE|ERR\s*-?\d+)",txt)
    print(f"  maze_step{sx:<2d} -> {m.group(0) if m else '?(timeout/empty)'}   raw={txt[:46]!r}")
