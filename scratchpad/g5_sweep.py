import os,sys,re,time
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
ARENA=["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
       "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF"]
def run(label,setup,to):
    lines=["COLOR15,1,1:SCREEN2:CLS"]+setup+['SCREEN0:PRINT"DONE":END']
    t0=time.time()
    try:
        o=omsx_repl.run_cases(REF,[("stored",lines)],batch=False,capture="screen",
                              step=2.5,cap_gap=3.0,timeout=to)[0]
        txt=" ".join((o or "").split())
        print(f"  {label:22s} -> {'DONE' if 'DONE' in txt else 'no-done'} ({time.time()-t0:.0f}s)")
    except SystemExit:
        print(f"  {label:22s} -> TIMEOUT(hang) ({time.time()-t0:.0f}s)")
for c in (15,14,1,4):
    run(f"arena_fill{c}", ARENA+[f"PAINT(31,31),{c},15"], 40)
# long-timeout: is fill4 EVER finishing?
run("arena_fill4_LONG", ARENA+["PAINT(31,31),4,15"], 200)
