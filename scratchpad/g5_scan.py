import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
# clash-free arena: thick (8px) L/R bars group-aligned; 2px top/bottom bars.
# interior x24..39 (groups 3&4, all-interior), y18..45.
ARENA=["COLOR15,1,1:SCREEN2:CLS",
  "LINE(16,16)-(23,47),15,BF",  # left bar x16-23
  "LINE(40,16)-(47,47),15,BF",  # right bar x40-47
  "LINE(24,16)-(39,17),15,BF",  # top bar y16-17
  "LINE(24,46)-(39,47),15,BF"]  # bottom bar y46-47
HS='H$="":FORX=14TO49:H$=H$+MID$("0123456789ABCDEF",POINT(X,31)+1,1):NEXT'
VS='V$="":FORY=14TO49:V$=V$+MID$("0123456789ABCDEF",POINT(31,Y)+1,1):NEXT'
PR='SCREEN0:PRINT"H"H$:PRINT"V"V$:END'
def run(label,extra):
    lines=ARENA+extra+[HS,VS,PR]
    try:
        o=omsx_repl.run_cases(REF,[("stored",lines)],batch=False,capture="screen",
                              step=2.5,cap_gap=3.0,timeout=90.0)[0]
    except SystemExit as e:
        print(f"{label}: TIMEOUT");return
    txt=o or ""
    h=re.search(r"H([0-9A-F]{36})",txt); v=re.search(r"V([0-9A-F]{36})",txt)
    print(f"{label}:")
    print(f"  Hy31 x14..49: {h.group(1) if h else '?'}")
    print(f"  Vx31 y14..49: {v.group(1) if v else '?'}")
run("arena_only",[])
run("fill9_b15",["PAINT(31,31),9,15"])
run("fill9_default_border",["PAINT(31,31),9"])   # border omitted -> ?
