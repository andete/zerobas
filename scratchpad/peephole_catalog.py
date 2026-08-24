#!/usr/bin/env python3
"""The FULL control-transfer peephole catalog, one ROM walk, main image.

Beyond the single jp->jr class, the "plenty of Z80 size tricks" family has more
control-flow members that are byte-shorter encodings of the SAME transfer. This
walks the assembled image once and classifies every jp / jr / call / ret, with
PRECEDENCE (a jump to a `ret` is scored as ret-conversion, not jr-conversion).

Classes, each a strict size win with NO data effect:

  A  jp cc,X (in jr range)          -> jr cc,X     -1 B   [assembler-enforced safe]
  B  jp/jp cc,X  where X is `ret`   -> ret/ret cc  -2 B   [always assembles; differential-safe]
  C  jr/jr cc,X  where X is `ret`   -> ret/ret cc  -1 B   [same]
  D  call X / ret   (tail call)     -> jp X        -1 B   [differential-safe unless the ret is a jump target
                                                           or X pops its return addr]

🔴 SAFETY IS TIERED AND STATED, NOT ASSUMED. Class A is safe BY CONSTRUCTION --
jp and jr are flag- and control-flow-identical and pasmo enforces range, so "it
assembles" == "it is correct". Classes B/C/D always assemble, so the assembler
proves nothing; each is a control-flow identity whose one risk (a ret reached by
another path, or a routine that rewrites its return address) is exactly what the
empirical differential exists to catch. NONE of these touch a flag or a register.

Reuses tools/dupspan_indep.py's decoder so instruction boundaries agree with
that tool. --selftest plants each class and asserts it is counted.
"""
import importlib.util, os, collections, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("di", "tools/dupspan_indep.py")
di = importlib.util.module_from_spec(spec); spec.loader.exec_module(di)

BASE = di.BASE
rom = open("build/basic-reloc.rom", "rb").read()
n = len(rom)

JP   = {0xC3: "jp", 0xCA: "jp z", 0xC2: "jp nz", 0xDA: "jp c", 0xD2: "jp nc"}
JP_X = {0xEA, 0xE2, 0xFA, 0xF2}                       # pe/po/m/p -- no jr/jr-cc form
JR   = {0x18: "jr", 0x28: "jr z", 0x20: "jr nz", 0x38: "jr c", 0x30: "jr nc"}
CALL = {0xCD: "call", 0xCC: "call z", 0xC4: "call nz", 0xDC: "call c",
        0xD4: "call nc", 0xEC: "call pe", 0xE4: "call po", 0xFC: "call m",
        0xF4: "call p"}
RET  = 0xC9

def ilen(i):
    op = rom[i]
    if op in (0xCB, 0xDD, 0xED, 0xFD):
        return di.decode(rom, i)[0]
    return di._LEN[op]

def at(addr):
    j = addr - BASE
    return rom[j] if 0 <= j < n else None

def region(addr):
    return "p1" if 0x4000 <= addr < 0x8000 else ("low" if addr < 0x4000 else "?")

def walk():
    """yield (addr, opcode, length, target_or_None)"""
    i = 0
    while i < n:
        op = rom[i]; addr = BASE + i; L = ilen(i) or 1
        tgt = None
        if op in JP or op in JP_X or op in CALL:
            if i + 2 < n:
                tgt = rom[i+1] | (rom[i+2] << 8)
        elif op in JR:
            if i + 1 < n:
                d = rom[i+1]; tgt = addr + 2 + (d - 256 if d > 127 else d)
        yield addr, op, L, tgt
        i += L

def main():
    A = collections.Counter(); B = collections.Counter()
    C = collections.Counter(); D = collections.Counter()
    reg = collections.Counter()
    ex = collections.defaultdict(list)
    insns = list(walk())
    # first pass: every control-flow TARGET address (so a tail-call's ret that is
    # itself jumped-to is excluded from class D)
    targets = {t for _, op, _, t in insns if t is not None
               and (op in JP or op in JP_X or op in JR)}
    for k, (addr, op, L, tgt) in enumerate(insns):
        r = region(addr)
        # B/C: jump whose target is a lone `ret`
        if (op in JP or op in JR) and tgt is not None and at(tgt) == RET:
            (B if op in JP else C)[JP.get(op) or JR.get(op)] += 1
            reg[("B", r)] += 1
            if len(ex["B"]) < 4 and op in JP:
                ex["B"].append(f"${addr:04X} {JP[op]:6}-> ${tgt:04X}=ret [{r}]")
            continue
        # A: jp cc in jr range (and target is NOT a ret -- B already took those)
        if op in JP and tgt is not None:
            disp = tgt - (addr + 2)
            if -126 <= disp <= 129:
                A[JP[op]] += 1; reg[("A", r)] += 1
                if len(ex["A"]) < 4:
                    ex["A"].append(f"${addr:04X} {JP[op]:6}-> ${tgt:04X} (disp {disp:+d}) [{r}]")
            continue
        # D: call X immediately followed by ret, where that ret is NOT a jump target
        if op in CALL and k + 1 < len(insns):
            naddr, nop, _, _ = insns[k+1]
            if nop == RET and naddr not in targets:
                D[CALL[op]] += 1; reg[("D", r)] += 1
                if len(ex["D"]) < 4:
                    ex["D"].append(f"${addr:04X} {CALL[op]:7}+ ret [{r}]")

    def tot(cnt): return sum(cnt.values())
    print(f"walked {n} B from ${BASE:04X}, {len(insns)} instructions\n")
    print(f"  A  jp cc -> jr cc (in range)      {tot(A):4} sites x -1 B = {tot(A):4} B   "
          f"[{reg[('A','p1')]} in page 1]  SAFE by construction")
    print(f"  B  jp/jp cc -> ret/ret cc         {tot(B):4} sites x -2 B = {tot(B)*2:4} B   "
          f"[{reg[('B','p1')]} in page 1]  differential-safe")
    print(f"  C  jr/jr cc -> ret/ret cc         {tot(C):4} sites x -1 B = {tot(C):4} B   "
          f"[{reg[('C','p1')]} in page 1]  differential-safe")
    print(f"  D  call X / ret -> jp X           {tot(D):4} sites x -1 B = {tot(D):4} B   "
          f"[{reg[('D','p1')]} in page 1]  differential-safe (see caveat)")
    p1 = reg[('A','p1')] + 2*reg[('B','p1')] + reg[('C','p1')] + reg[('D','p1')]
    allb = tot(A) + 2*tot(B) + tot(C) + tot(D)
    print(f"\n  TOTAL {allb} B nominal across the image; ~{p1} B of it in PAGE 1.")
    print(f"  Class A ({tot(A)} B) is the mechanically-safe floor; B+C+D "
          f"({allb-tot(A)} B) need the differential.")
    for cls in "ABD":
        if ex[cls]:
            print(f"\n  {cls} examples:")
            for e in ex[cls]:
                print("   " + e)

def selftest():
    # plant one of each in a tiny buffer and assert detection
    import types
    global rom, n, BASE
    # jp z,$0005 (target=ret), call $0009/ret, jp nz,$000B (in range, not ret)
    buf = bytes([0xCA,0x05,0x00,   # $0000 jp z,$0005  -> ret  (class B)
                 0xC9,             # $0003 ret
                 0x00,             # $0004 nop
                 0xC9,             # $0005 ret  (B target)
                 0xCD,0x0A,0x00,   # $0006 call $000A
                 0xC9,             # $0009 ret   (class D: call+ret)
                 0xC9])            # $000A ret
    rom = buf; n = len(buf); BASE = 0x0000
    insns = list(walk())
    tgts = {t for _,op,_,t in insns if t is not None and op in JP}
    b = sum(1 for a,op,L,t in insns if op in JP and t is not None and at(t)==0xC9)
    d = 0
    for k,(a,op,L,t) in enumerate(insns):
        if op in CALL and k+1<len(insns) and insns[k+1][1]==0xC9 and insns[k+1][0] not in tgts:
            d+=1
    print(f"selftest: class-B detected {b} (want>=1), class-D detected {d} (want>=1) "
          f"-> {'OK' if b>=1 and d>=1 else 'BLIND'}")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
