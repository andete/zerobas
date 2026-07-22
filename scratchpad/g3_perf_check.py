import os,sys,re,time
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
ZB=os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE","C-BIOS_MSX1_EU_REPACK_DISK")
# boot-per-case, generous: does the extreme-span LINE terminate and print K?
cases=[
 ("neg_span",  ["ON ERROR GOTO 40","SCREEN2:LINE(0,0)-(-32768,0),15",'SCREEN0:PRINT"K":END','SCREEN0:PRINT"E";ERR:END']),
 ("min_short", ["ON ERROR GOTO 40","SCREEN2:LINE(-32768,0)-(-32767,0),15",'SCREEN0:PRINT"K":END','SCREEN0:PRINT"E";ERR:END']),
]
for label,body in cases:
    t=time.time()
    out=omsx_repl.run_cases(ZB,[("stored",body)],batch=False,reset=("NEW","CLS"))[0]
    dt=time.time()-t
    txt=" ".join("".join(out).split()) if out else ""
    mk=re.search(r"\bK\b",txt);me=re.search(r"E\s*-?\d+",txt)
    print(f"  {label:10s} -> {('K' if mk and not me else (me.group(0) if me else 'None/?')):8}  {dt:.1f}s  raw={txt[:36]!r}")
