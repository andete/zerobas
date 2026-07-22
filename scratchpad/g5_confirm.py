import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
ARENA=["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
       "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF"]
def run(label,setup,pts):
    q=":".join(f"{chr(65+i)}=POINT({x},{y})" for i,(x,y) in enumerate(pts))
    pr='SCREEN0:PRINT"R";'+";".join(chr(65+i) for i in range(len(pts)))+':END'
    lines=["COLOR15,1,1:SCREEN2:CLS"]+setup+[q,pr]
    o=omsx_repl.run_cases(REF,[("stored",lines)],batch=False,capture="screen",
                          step=35.0,cap_gap=8.0,timeout=180.0)[0]
    txt=" ".join((o or "").split())
    m=re.search(r"R((?:\s*-?\d+){%d})"%len(pts),txt)
    print(f"  {label:26s} = {m.group(1).split() if m else None}")
# prove arena encloses: fill15 bounded -> outside stays 1
run("arena_fill15_b15 [encl?]",ARENA+["PAINT(31,31),15,15"],[(31,31),(19,31),(6,31),(200,150)])
# same arena floods with fill4
run("arena_fill4_b15  [flood]",ARENA+["PAINT(31,31),4,15"],[(31,31),(19,31),(6,31),(200,150)])
# seed already == border colour: no-op? (blank screen bg1, border1, fill7)
run("seed_on_border(b1,f7)",["PAINT(100,100),7,1"],[(100,100),(6,6)])
# seed on a drawn border pixel
run("seed_on_15px(f7,b15)",["LINE(16,16)-(40,40),15,B","PAINT(16,16),7,15"],[(16,16),(28,28),(6,6)])
