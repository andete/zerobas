import re,glob,os
HERE=os.path.dirname(os.path.abspath(__file__)); REPO=os.path.dirname(HERE); os.chdir(REPO)   # chokepoint ROOT rule: never a hardcoded path
subinc=set()
for p in glob.glob("sub/*.asm"):
    for m in re.finditer(r'include\s+"?([^"\s]+)"?', open(p).read()): subinc.add(os.path.basename(m.group(1)))
files=[p for p in sorted(glob.glob("basic/*.asm")+glob.glob("basic/*.inc")) if os.path.basename(p) not in subinc and not p.endswith(("sysvars.inc","kwtable.inc"))]
def norm(l):
    l=l.split(";")[0].strip(); return re.sub(r"\s+"," ",l) if l else None
def cmt(l):
    i=l.find(";"); return l[i:] if i>=0 else ""
RULES=[(("call ixsp_paren","jp nz,ev_f_empty"),"call    ixsp_paren_req"),
       (("call tgt_parse","jp nz,fp_runtime_error"),"call    tgt_parse_req"),
       (("ld hl,ARGA+FPNUM_DIG","call dig15_iszero"),"call    arga_dig_iszero"),
       (("ld (SH_OP),a","call call_strheap"),"call    sh_call_op")]
total=0
for p in files:
    L=open(p,errors="replace").read().split("\n"); out=[]; i=0; changed=False
    while i<len(L):
        hit=None
        for seq,rep in RULES:
            if norm(L[i])!=seq[0]: continue
            j=i+1
            while j<len(L) and norm(L[j]) is None: j+=1
            if j<len(L) and norm(L[j])==seq[1]: hit=(seq,rep,i,j); break
        if not hit: out.append(L[i]); i+=1; continue
        seq,rep,i0,j=hit; first=L[i0]; indent=re.match(r"\s*",first).group(0)
        out.append(f"{indent}{rep:<26}{(' '+cmt(first)) if cmt(first) else ''}".rstrip())
        for k in range(i0+1,j+1):
            if k==j:
                c=cmt(L[k]);
                if c: out.append(f"{indent}{'':<26} {c}".rstrip())
            else: out.append(L[k])
        print(f"  {p}:{i0+1}  {seq[0]} + {seq[1]}  ->  {rep.split()[1]}"); total+=1; changed=True; i=j+1
    if changed: open(p,"w").write("\n".join(out))
print("sites rewritten:", total)
def insert_before(p, anchor, block):
    s=open(p).read(); assert s.count(anchor)==1,(p,anchor); open(p,"w").write(s.replace(anchor,block+anchor)); print("helper into",p)
insert_before("basic/expr.asm","; --- ixsp_paren: ixsp, then \"is it `(`?\"",
"""; --- ixsp_paren_req / tgt_parse_req / arga_dig_iszero: D-PAIRCARVE2 ----------
; 💰 (2026-09-11) Three more sequences from a scan whose sizes were MEASURED by
; assembling each candidate with pasmo, not estimated:
;   call ixsp_paren + jp nz,ev_f_empty        8 sites, 6 B each
;   call tgt_parse  + jp nz,fp_runtime_error  6 sites, 6 B each
;   ld hl,ARGA+FPNUM_DIG + call dig15_iszero  7 sites, 6 B each
; ixsp_paren_req: `(` is REQUIRED -- Z returns as the pair did; NZ discards this
; helper's own return address (`inc sp` twice, evsp_close's precedent: no
; register, no flag) and jumps to ev_f_empty, whose deferred error then returns
; ONE FRAME FURTHER OUT exactly as the open-coded `jp` did. tgt_parse_req: the
; NZ exit is fp_runtime_error, which is `jr raise_error` -- an ABORT that resets
; SP -- so no frame fix is needed. arga_dig_iszero: dig15_iszero preserves HL,
; so the caller sees HL = ARGA+FPNUM_DIG and Z as before.
ixsp_paren_req:
                call    ixsp_paren
                ret     z
                inc     sp
                inc     sp
                jp      ev_f_empty
tgt_parse_req:
                call    tgt_parse
                ret     z
                jp      fp_runtime_error
arga_dig_iszero:
                ld      hl,ARGA+FPNUM_DIG
                jp      dig15_iszero

""")
insert_before("basic/str-engine.asm","; --- call_strheap: dispatch to the string-heap tenant (SUBROM_IDX_STRHEAP) -",
"""; --- sh_call_op: SH_OP := A, then call_strheap (D-PAIRCARVE2, 2026-09-11) -----
; 💰 The pair stood at SIX sites, 6 B each against 3 for a call. Same contract as
; call_strheap: clobbers A, IX; returns with the tenant's results in RAM.
sh_call_op:
                ld      (SH_OP),a
                jp      call_strheap

""")
print("ALL DONE")
