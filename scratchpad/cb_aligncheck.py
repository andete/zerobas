"""Label-aligned comparison of two C-BIOS builds: every byte that differs outside the
edited routines must be a 16-bit operand pointing at its label's new address, or a jr
displacement (reported apart). usage: old.rom old.lst new.rom new.lst edited,labels"""
import sys
def syms(p):
    d={}
    for l in open(p):
        q=l.split()
        if len(q)>=3 and q[1]=='EQU' and q[0][:1].islower():
            try: d[q[0]]=int(q[2].rstrip('H'),16)
            except: pass
    return d
ro=open(sys.argv[1],'rb').read(); o=syms(sys.argv[2]); rn=open(sys.argv[3],'rb').read(); n=syms(sys.argv[4])
edited=set(sys.argv[5].split(','))
oinv={}
for k,v in o.items(): oinv.setdefault(v,[]).append(k)
def operand_ok(oa,na,j):
    for s in (j,j-1):
        if s<0: continue
        ot=ro[oa+s]|ro[oa+s+1]<<8; nt=rn[na+s]|rn[na+s+1]<<8
        if any(n.get(l)==nt for l in oinv.get(ot,[])): return True
    return False
jt=[hex(k) for k in range(0x160) if ro[k]!=rn[k] and not operand_ok(0,0,k)]
labs=sorted((v,k) for k,v in n.items() if k in o and 0x0160<=v<0x8000)
bad=[];checked=0
for i,(na,L) in enumerate(labs):
    nb=labs[i+1][0] if i+1<len(labs) else na
    ln=nb-na
    if ln<=0 or ln>600 or L in edited: continue
    oa=o[L]
    for j in range(ln):
        checked+=1
        if rn[na+j]!=ro[oa+j] and not operand_ok(oa,na,j): bad.append((L,hex(na+j)))
print('jump table unexplained:', jt)
print('compared', checked, 'code bytes outside the edited routines; unexplained:', bad[:20], len(bad))
