import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
def run(label,setup):
    lines=["COLOR15,1,1:SCREEN2:CLS"]+setup+['SCREEN0:PRINT"DONE":END']
    try:
        o=omsx_repl.run_cases(REF,[("stored",lines)],batch=False,capture="screen",
                              step=2.5,cap_gap=3.0,timeout=90.0)[0]
        txt=" ".join((o or "").split())
        print(f"  {label:24s} -> {'DONE' if 'DONE' in txt else 'no-done'}  raw={txt[:30]!r}")
    except SystemExit:
        print(f"  {label:24s} -> TIMEOUT(hang)")
run("arena_fill15", ["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
    "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF","PAINT(31,31),15,15"])
run("arena_fill9",  ["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
    "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF","PAINT(31,31),9,15"])
run("blank_fill9_bdef", ["PAINT(100,100),9"])
run("blank_fill9_b1",   ["PAINT(100,100),9,1"])
run("smallbox_fill9",   ["LINE(20,20)-(60,60),15,B","PAINT(40,40),9,15"])
