import os,sys,re,time
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
ARENA=["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
       "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF"]
def run(label,setup,step,cap):
    lines=["COLOR15,1,1:SCREEN2:CLS"]+setup+['SCREEN0:PRINT"DONE":END']
    t0=time.time()
    try:
        o=omsx_repl.run_cases(REF,[("stored",lines)],batch=False,capture="screen",
                              step=step,cap_gap=cap,timeout=180.0)[0]
        txt=" ".join((o or "").split())
        print(f"  {label:24s} step={step} -> {'DONE' if 'DONE' in txt else 'NO-DONE'} ({time.time()-t0:.0f}s wall) raw={txt[:24]!r}")
    except SystemExit:
        print(f"  {label:24s} step={step} -> TIMEOUT ({time.time()-t0:.0f}s wall)")
run("arena_fill4_bigbudget", ARENA+["PAINT(31,31),4,15"], 30.0, 10.0)
run("smallbox_fill4_bigbud", ["LINE(20,20)-(60,60),15,B","PAINT(40,40),4,15"], 30.0, 10.0)
