import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
ARENA=["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
       "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF"]
def run(label,setup):
    lines=["ON ERROR GOTO 90","COLOR15,1,1:SCREEN2:CLS"]+setup+\
          ['SCREEN0:PRINT"DONE":END']+["","","","",  # pad so 90 is free
           ]
    # build with explicit line numbers to place handler at 90
    prog=["ON ERROR GOTO 90","COLOR15,1,1:SCREEN2:CLS"]+setup+['SCREEN0:PRINT"DONE":END']
    numbered=[f"{10*(i+1)} {ln}" for i,ln in enumerate(prog)]
    numbered.append('90 SCREEN0:PRINT"ERR";ERR;"@";ERL:END')
    o=omsx_repl.run_cases(REF,[("direct",numbered+["RUN"])],batch=False,
                          capture="screen",step=2.0,cap_gap=3.0,timeout=60.0)[0]
    txt=" ".join((o or "").split())
    print(f"  {label:16s} -> {txt[:60]!r}")
run("fill4",  ARENA+["PAINT(31,31),4,15"])
run("fill9",  ARENA+["PAINT(31,31),9,15"])
run("fill14", ARENA+["PAINT(31,31),14,15"])
run("fill1",  ARENA+["PAINT(31,31),1,15"])
