import sys,re,glob,os,json,subprocess,shutil,collections
"""D-DISKJR (2026-11-06): which disk.rom `jp`s can be `jr`, by region.
Labels every `jp label` / `jp cc,label` (driver.asm excluded: the FDC loops) and every
pinned `ds $XXXX - $` in a temp copy of disk/, assembles it, and counts the jumps whose
target is in jr reach, grouped by the pin that ends their region (a byte saved there
becomes room before that pin). Review the sites before converting: an entry VECTOR must
stay 3 B."""
import tempfile
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T=os.path.join(tempfile.gettempdir(),'djr')
shutil.rmtree(T,ignore_errors=True); shutil.copytree(R+'/disk',T)
JP=re.compile(r'^(\s+)jp\s+(?:(nz|z|nc|c)\s*,\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*(;.*)?$')
DS=re.compile(r'\s+ds\s+(\$[0-9A-Fa-f]+)\s*-\s*\$')
sites={}; pins={}; n=0
for f in sorted(glob.glob(T+'/*.asm')):
    base=os.path.basename(f); L=open(f).read().split('\n'); out=[]
    for i,l in enumerate(L):
        m=JP.match(l)
        if m and base!='driver.asm':
            n+=1; k=f'__JP{n}'; sites[k]=(base,i+1,m.group(3),l.strip()); out.append(k+':')
        d=DS.match(l)
        if d:
            n+=1; k=f'__DS{n}'; pins[k]=(base,i+1,int(d.group(1)[1:],16)); out.append(k+':')
        out.append(l)
    open(f,'w').write('\n'.join(out))
subprocess.run(['pasmo','-I',T,'--bin',T+'/disk.asm',T+'/t.rom',T+'/t.sym'],cwd=R,capture_output=True)
sym={}
for l in open(T+'/t.sym'):
    m=re.match(r'(\S+)\s+EQU\s+0?([0-9A-F]+)H',l)
    if m: sym[m.group(1)]=int(m.group(2),16)
pinaddr=sorted((sym[k],v[2],v[0],v[1]) for k,v in pins.items())
def region(a):
    for at,p,f,ln in pinaddr:
        if at>=a: return (p,f,ln)
    return None
reg=collections.Counter(); ex=collections.defaultdict(list)
for k,(f,ln,tgt,txt) in sites.items():
    a=sym.get(k); t=sym.get(tgt)
    if a is None or t is None: continue
    d=t-(a+2)
    if -128<=d<=127:
        r=region(a); reg[r]+=1; ex[r].append(f'{f}:{ln} {txt[:60]}')
tot=0
for r,c in sorted(reg.items(), key=lambda x:-x[1]):
    print(f"{c:3}  region ending at pin ${r[0]:04X} ({r[1]}:{r[2]})"); tot+=c
print("total",tot)
if len(sys.argv)>1:
    for r in reg:
        if r and r[0]==int(sys.argv[1],16):
            print("\n".join(ex[r]))
