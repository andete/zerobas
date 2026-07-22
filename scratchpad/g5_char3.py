import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
STEP=35.0
def scanprog(setup, scans):
    # scans: list of (tag, xexpr-range as (var,'X'|'Y',fixed,lo,hi))
    lines=["COLOR15,1,1:SCREEN2:CLS"]+setup
    body=[]
    for i,(tag,axis,fixed,lo,hi) in enumerate(scans):
        if axis=='X':
            body.append(f'{tag}$="":FORI={lo}TO{hi}:{tag}$={tag}$+MID$("0123456789ABCDEF",POINT(I,{fixed})+1,1):NEXT')
        else:
            body.append(f'{tag}$="":FORI={lo}TO{hi}:{tag}$={tag}$+MID$("0123456789ABCDEF",POINT({fixed},I)+1,1):NEXT')
    lines+=body
    pr='SCREEN0:'+":".join(f'PRINT"{tag}"{tag}$' for tag,_,_,_,_ in scans)+':END'
    lines.append(pr)
    o=omsx_repl.run_cases(REF,[("stored",lines)],batch=False,capture="screen",
                          step=STEP,cap_gap=8.0,timeout=180.0)[0]
    txt=o or ""
    out={}
    for tag,_,_,lo,hi in scans:
        m=re.search(tag+r"([0-9A-F]+)",txt)
        out[tag]=m.group(1) if m else "?"
    return out

# A: clash-free arena fill4 -> extent + inclusivity
A=scanprog(["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
            "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF","PAINT(31,31),4,15"],
           [("H",'X',31,14,49),("V",'Y',31,14,49)])
print("A arena_fill4 (x/y 14..49):")
print("  H y31:",A["H"]); print("  V x31:",A["V"])

# B: thin box fill4 border15 -> LEAK? scan wide H at box mid + borders survive?
B=scanprog(["LINE(16,16)-(40,40),15,B","PAINT(28,28),4,15"],
           [("H",'X',28,4,60),("T",'Y',28,4,52)])
print("B thinbox_fill4_b15:")
print("  H y28 x4..60:",B["H"])
print("  T x28 y4..52:",B["T"])

# C: concave U (wall at x=28 from top)
C=scanprog(["LINE(16,16)-(40,40),15,B","LINE(28,16)-(28,32),15","PAINT(20,30),4,15"],
           [("H",'X',20,14,44),("L",'X',30,14,44)])
print("C concave (wall x28 y16..32), seed left (20,30):")
print("  H y20 x14..44:",C["H"])
print("  L y30 x14..44:",C["L"])

# D: default border (omit) in arena
D=scanprog(["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
            "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF","PAINT(31,31),4"],
           [("H",'X',31,14,49)])
print("D arena PAINT(31,31),4  [border omitted]:")
print("  H y31:",D["H"])
