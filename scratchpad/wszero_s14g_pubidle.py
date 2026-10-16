import re,glob,os,subprocess
CB=os.environ.get('CBIOS_SRC', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'cbios', 'src'))
ZB=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
names=[]
for line in open(CB+'/systemvars.asm'):
    m=re.match(r'(\w+):\s+equ\s+\$([0-9A-Fa-f]+)',line)
    if m:
        v=int(m.group(2),16)
        if 0xF380<=v<=0xFFFF: names.append((v,m.group(1)))
names.sort()
syms={}
for f in ['basic-reloc.sym','sub.sym','sub2.sym','disk.sym']:
    for line in open(ZB+'/build/'+f):
        m=re.match(r'(\S+)\s+EQU\s+0*([0-9A-F]+)H',line)
        if m:
            v=int(m.group(2),16)
            if 0xF380<=v<=0xFFFF: syms.setdefault(v,set()).add(m.group(1))
cbsrc=''
for f in glob.glob(CB+'/*.asm'):
    if f.endswith('systemvars.asm'): continue
    cbsrc+=open(f,errors='replace').read()
# dedupe same address
seen=set(); uniq=[]
for v,n in names:
    if v in seen: continue
    seen.add(v); uniq.append((v,n))
for i,(v,n) in enumerate(uniq):
    nxt=uniq[i+1][0] if i+1<len(uniq) else 0x10000
    hit=[ (a,sorted(s)) for a,s in syms.items() if v<=a<nxt]
    # also syms that start below and might extend: ignored
    if hit: continue
    used=len(re.findall(r'\b'+n+r'\b',cbsrc))
    print(f'{v:04X} {n:8s} span {nxt-v:3d}  cbios_refs={used}')
