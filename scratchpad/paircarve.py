import re,glob,os,sys
REPO="/Users/joost/projects/zerobas"; os.chdir(REPO)
subinc=set()
for p in glob.glob("sub/*.asm"):
    for m in re.finditer(r'include\s+"?([^"\s]+)"?', open(p).read()): subinc.add(os.path.basename(m.group(1)))
files=[p for p in sorted(glob.glob("basic/*.asm")+glob.glob("basic/*.inc")) if os.path.basename(p) not in subinc and not p.endswith(("sysvars.inc","kwtable.inc"))]
def norm(l):
    l=l.split(";")[0].strip()
    return re.sub(r"\s+"," ",l) if l else None
def cmt(l):
    i=l.find(";"); return l[i:] if i>=0 else ""
# (sequence of instructions) -> replacement instruction
RULES=[ (("call inc_skip","cp '('"), "call    inc_skip_paren"),
        (("call ixsp","cp '('"), "call    ixsp_paren"),
        (("ld a,2","ld (FACTYP),a"), "call    set_factyp2"),
        (("ld a,(FACTYP)","cp 2"), "call    factyp_is2"),
        (("ld (DISKOP_OP),a","ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM","call subrom_call"), "call    fatprim_op"),
        (("ld (DISKOP_OP),a","ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_DIRVERB","call subrom_call"), "call    dirverb_op"),
]
total=0
for p in files:
    L=open(p,errors="replace").read().split("\n"); changed=False; i=0; out=[]
    while i<len(L):
        hit=None
        for seq,rep in RULES:
            if norm(L[i])!=seq[0]: continue
            idx=[i]; j=i
            ok=True
            for want in seq[1:]:
                j+=1
                while j<len(L) and norm(L[j]) is None: j+=1
                if j>=len(L) or norm(L[j])!=want: ok=False; break
                idx.append(j)
            if ok: hit=(seq,rep,idx); break
        if not hit: out.append(L[i]); i+=1; continue
        seq,rep,idx=hit
        # the first line becomes the call; keep its comment; keep the others' comments as comment-only lines
        first=L[idx[0]]; indent=re.match(r"\s*",first).group(0)
        out.append(f"{indent}{rep:<26}{(' '+cmt(first)) if cmt(first) else ''}".rstrip())
        for k in range(idx[0]+1, idx[-1]+1):
            if k in idx:
                c=cmt(L[k])
                if c: out.append(f"{indent}{'':<26} {c}".rstrip())
            else: out.append(L[k])
        print(f"  {p}:{idx[0]+1}  {' + '.join(seq)}  ->  {rep.split()[1]}"); total+=1
        i=idx[-1]+1; changed=True
    if changed: open(p,"w").write("\n".join(out))
print("sites rewritten:", total)

def insert_before(p, anchor, block):
    s=open(p).read(); assert s.count(anchor)==1, (p,anchor); open(p,"w").write(s.replace(anchor, block+anchor)); print("helper into", p)
insert_before("basic/interp.asm", "; --- skip_comma: skip_spaces, then \"is it a comma?\"", 
"""; --- inc_skip_paren: inc_skip, then "is it `(`?" -- Z iff '(' is next ----------
; 💰 D-PAIRCARVE (2026-09-11): the pair stood at TEN sites, 5 B each against 3 for
; a call: 10 x 2 saved less this 6-byte body = 14 B. Same flags contract as
; skip_comma: A = the byte, Z iff it is '(' -- every caller branches on NZ.
inc_skip_paren:
                call    inc_skip
                cp      '('
                ret
""")
insert_before("basic/expr.asm", "; --- ixsp: step the evaluator cursor, then skip blanks",
"""; --- ixsp_paren: ixsp, then "is it `(`?" -- Z iff '(' is next ----------------
; 💰 D-PAIRCARVE (2026-09-11): NINE live sites went straight from `call ixsp` to
; `cp '('` (ixsp's own header counted them); 5 B each against 3 for a call:
; 9 x 2 saved less this 6-byte body = 12 B. A and the flags are exactly what the
; open-coded pair left.
ixsp_paren:
                call    ixsp
                cp      '('
                ret

; --- set_factyp2 / factyp_is2: the two FACTYP idioms as calls ------------------
; 💰 D-PAIRCARVE (2026-09-11): `ld a,2` + `ld (FACTYP),a` stood at EIGHT sites and
; `ld a,(FACTYP)` + `cp 2` at EIGHT more, 5 B each against 3 for a call:
; 16 x 2 saved less two 5/6-byte bodies = 21 B. set_factyp2 returns with A = 2,
; as the pair did; factyp_is2 returns A = FACTYP and Z iff it is 2.
set_factyp2:
                ld      a,2
                ld      (FACTYP),a
                ret
factyp_is2:
                ld      a,(FACTYP)
                cp      2
                ret

""")
insert_before("basic/files.asm", "ex_files:\n",
"""; --- dirverb_op: run dirverb-tenant op A ------------------------------------
; 💰 D-PAIRCARVE (2026-09-11): the `ld (DISKOP_OP),a` / `ld ix,...DIRVERB` /
; `call subrom_call` triple stood at two clean sites (KILL, NAME), 10 B each; a
; call is 3. The FILES site keeps a `push hl` between the store and the call and
; stays open-coded. Returns what subrom_call returns: CF=1 iff the sub-ROM is
; absent. Clobbers IX, as subrom_call does.
dirverb_op:
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_DIRVERB
                jp      subrom_call

""")
# fatprim_op: append to fat.asm
s=open("basic/fat.asm").read().rstrip("\n")+"""

; --- fatprim_op: run fatprim-tenant op A ------------------------------------
; 💰 D-PAIRCARVE (2026-09-11): the `ld (DISKOP_OP),a` / `ld ix,...FATPRIM` /
; `call subrom_call` triple stood at THREE sites above, 10 B each against 3 for a
; call: 3 x 7 saved less this 10-byte body = 11 B. Returns what subrom_call
; returns: CF=1 iff the sub-ROM is absent. Clobbers IX, as subrom_call does.
fatprim_op:
                ld      (DISKOP_OP),a
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM
                jp      subrom_call
"""
open("basic/fat.asm","w").write(s); print("helper into basic/fat.asm")
# ev_ff_dskf: the open-coded gate becomes chan_gate
p="basic/expr.asm"; s=open(p).read()
old="""                push    ix
                ld      hl,H_DSKF
                ld      de,dskf_back
                push    de
                or      a
                jp      (hl)
dskf_back:
                pop     ix
                jp      nc,ev_f_ifc         ; no disk ROM -> Illegal function call
"""
new="""                ; 💰 D-PAIRCARVE (2026-09-11): this used to open-code the hook
                ; call (the same 11 B chan_gate now shares), then `jp nc,ev_f_ifc`.
                ; chan_gate raises ERR 5 itself when nobody claimed the hook --
                ; the same `Illegal function call` the nodisk gate's `v.dskf` row
                ; pins, raised at once rather than deferred -- so the diskless
                ; refusal is unchanged and the IX guard shrinks to one pair.
                push    ix
                ld      hl,H_DSKF
                call    chan_gate           ; no disk ROM -> Illegal function call
                pop     ix
"""
assert s.count(old)==1; s=s.replace(old,new); open(p,"w").write(s); print("ev_ff_dskf rewritten")
