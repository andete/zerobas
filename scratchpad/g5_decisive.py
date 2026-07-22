import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
def run(label,setup,pts):
    q=":".join(f"{chr(65+i)}=POINT({x},{y})" for i,(x,y) in enumerate(pts))
    pr='SCREEN0:PRINT"R";'+";".join(chr(65+i) for i in range(len(pts)))+':END'
    lines=["COLOR15,1,1:SCREEN2:CLS"]+setup+[q,pr]
    o=omsx_repl.run_cases(REF,[("stored",lines)],batch=False,capture="screen",
                          step=35.0,cap_gap=8.0,timeout=180.0)[0]
    txt=" ".join((o or "").split())
    m=re.search(r"R((?:\s*-?\d+){%d})"%len(pts),txt)
    print(f"  {label:22s} {[p for p in pts]} = {m.group(1).split() if m else None}")
# thin box fill4 b15: interior, LEFT border(16,28), top border(28,16), outside(6,6), far(200,150)
run("thinbox_fill4_b15",["LINE(16,16)-(40,40),15,B","PAINT(28,28),4,15"],
    [(28,28),(16,28),(28,16),(6,6),(200,150)])
# arena clash-free fill4: interior, leftbar(19,31), outside(6,31), far(200,150)
run("arena_fill4_b15",["LINE(16,16)-(23,47),15,BF","LINE(40,16)-(47,47),15,BF",
    "LINE(24,16)-(39,17),15,BF","LINE(24,46)-(39,47),15,BF","PAINT(31,31),4,15"],
    [(31,31),(19,31),(6,31),(200,150)])
# box4 fill4 b4 (border=paint): interior, border(16,28), outside
run("box4_fill4_b4",["LINE(16,16)-(40,40),4,B","PAINT(28,28),4,4"],
    [(28,28),(16,28),(6,6),(200,150)])
