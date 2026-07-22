import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF=os.environ.get("ZEROBAS_REF_MACHINE","Philips_VG_8020")
CASES=[
 ("comma_c_B",   "SCREEN2:LINE(1,1)-(9,9),15,B"),
 ("comma_comma_B","SCREEN2:LINE(1,1)-(9,9),,B"),
 ("single_B",    "SCREEN2:LINE(1,1)-(9,9),B"),      # single comma before B
 ("single_BF",   "SCREEN2:LINE(1,1)-(9,9),BF"),
 ("Bvar_color",  "SCREEN2:B=7:LINE(1,1)-(9,9),B"),  # is B a colour var or box flag?
]
specs=[("stored",["ON ERROR GOTO 40",act,'SCREEN0:PRINT"K":END','SCREEN0:PRINT"E";ERR:END']) for _,act in CASES]
outs=omsx_repl.run_cases(REF,specs,batch=True,reset=("NEW","CLS"))
for (label,_),out in zip(CASES,outs):
    txt=" ".join("".join(out).split()) if out else ""
    mk=re.search(r"\bK\b",txt);me=re.search(r"E\s*-?\d+",txt)
    print(f"  {label:14s} -> {('K' if mk and not me else (me.group(0).replace(' ','') if me else '?')):8}  raw={txt[:40]!r}")
