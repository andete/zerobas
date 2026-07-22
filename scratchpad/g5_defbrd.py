import os,sys,re
HERE=os.path.dirname(os.path.abspath(__file__));REPO=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(REPO,"probes","lib"));import omsx_repl
REF="Philips_VG_8020"
def run(label,setup,pts):
    q=":".join(f"{chr(65+i)}=POINT({x},{y})" for i,(x,y) in enumerate(pts))
    pr='SCREEN0:PRINT"R";'+";".join(chr(65+i) for i in range(len(pts)))+':END'
    o=omsx_repl.run_cases(REF,[("stored",["COLOR15,1,1:SCREEN2:CLS"]+setup+[q,pr])],
        batch=False,capture="screen",step=35.0,cap_gap=8.0,timeout=180.0)[0]
    txt=" ".join((o or "").split()); m=re.search(r"R((?:\s*-?\d+){%d})"%len(pts),txt)
    print(f"  {label:30s} = {m.group(1).split() if m else None}")
# default border: box drawn 4, fill 4, border OMITTED -> bounded(=>defB=paint4) or flood(=>defB!=4)
run("box4 PAINT(28,28),4 [defB]",["LINE(16,16)-(40,40),4,B","PAINT(28,28),4"],
    [(28,28),(16,28),(6,6),(200,150)])
# default color+border both omitted: box15 PAINT(28,28) -> bounded? (round1 said yes)
run("box15 PAINT(28,28) [defC,defB]",["LINE(16,16)-(40,40),15,B","PAINT(28,28)"],
    [(28,28),(16,28),(6,6),(200,150)])
# explicit border matching paint but color omitted: box15 PAINT(28,28),,15
run("box15 PAINT(28,28),,15",["LINE(16,16)-(40,40),15,B","PAINT(28,28),,15"],
    [(28,28),(16,28),(6,6),(200,150)])
