# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Z80 instruction decoder: length, mnemonic, control flow, register/flag effects.

Core module: knows the Z80 only. Every register and flag is a *unit* (one bit in a
mask). Flags are per flag (S Z H PV N C); the undocumented bits 3/5 are ignored.
The shadow set (A' B'..L' and the shadow flags) are units too, so EXX and
EX AF,AF' are modelled as exact swaps rather than "touches everything".

An Instr carries:
  reads / writes  -- unit masks (SP is unit SP, outside REAL)
  copies          -- [(dst_unit, src_unit)] value moves (LD r,r' and the swaps);
                     their src/dst are NOT also in reads/writes
  kind            -- 'seq' 'jp' 'jr' 'djnz' 'call' 'rst' 'ret' 'reti' 'retn'
                     'jpind' 'halt'
  cond            -- None or 'nz' 'z' 'nc' 'c' 'po' 'pe' 'p' 'm'
  target          -- static target or None
  stack           -- None or ('push', pair) ('pop', pair) ('exsp', pair)
                     ('ldsp', src) ('adjsp', +-1) ; call/ret are implied by kind
  mem_r / mem_w   -- coarse memory effect
  io              -- None, ('in', port|None) or ('out', port|None)
  invalid         -- None or a reason string (a decode real code would not contain)
"""

# ---- units ---------------------------------------------------------------
UNIT_NAMES = ["A", "B", "C", "D", "E", "H", "L", "IXH", "IXL", "IYH", "IYL",
              "fS", "fZ", "fH", "fPV", "fN", "fC",
              "A'", "B'", "C'", "D'", "E'", "H'", "L'",
              "fS'", "fZ'", "fH'", "fPV'", "fN'", "fC'",
              "SP"]
U = {n: i for i, n in enumerate(UNIT_NAMES)}


def m(*names):
    r = 0
    for n in names:
        r |= 1 << U[n]
    return r


FS, FZ, FH, FPV, FN, FC = (m(x) for x in ("fS", "fZ", "fH", "fPV", "fN", "fC"))
ALLF = FS | FZ | FH | FPV | FN | FC
SP = m("SP")
REAL = (1 << 30) - 1           # every register/flag unit except SP
MAIN_REGS = m("A", "B", "C", "D", "E", "H", "L", "IXH", "IXL", "IYH", "IYL") | ALLF

PAIRS = {"BC": ("B", "C"), "DE": ("D", "E"), "HL": ("H", "L"),
         "IX": ("IXH", "IXL"), "IY": ("IYH", "IYL")}
FLAG_UNITS = ["fS", "fZ", "fH", "fPV", "fN", "fC"]


def pair_units(p):
    """Unit names of a register pair, high part first. AF -> A + the 6 flags."""
    if p == "AF":
        return ("A",), tuple(FLAG_UNITS)
    if p == "SP":
        return ("SP",), ()
    h, l = PAIRS[p]
    return (h,), (l,)


def pmask(p):
    hi, lo = pair_units(p)
    return m(*hi, *lo)


COND_FLAG = {"nz": FZ, "z": FZ, "nc": FC, "c": FC, "po": FPV, "pe": FPV, "p": FS, "m": FS}
CC = ["nz", "z", "nc", "c", "po", "pe", "p", "m"]


def fmt_units(mask, drop_sp=True):
    """Human form: pairs collapsed (HL, IX), flags as F or F(Z,C)."""
    out = []
    names = [n for i, n in enumerate(UNIT_NAMES) if mask >> i & 1]
    s = set(names)
    for p, (h, l) in list(PAIRS.items()):
        if h in s and l in s:
            out.append(p)
            s -= {h, l}
    for p, (h, l) in [("BC'", ("B'", "C'")), ("DE'", ("D'", "E'")), ("HL'", ("H'", "L'"))]:
        if h in s and l in s:
            out.append(p)
            s -= {h, l}
    for r in ["A", "B", "C", "D", "E", "H", "L", "IXH", "IXL", "IYH", "IYL",
              "A'", "B'", "C'", "D'", "E'", "H'", "L'"]:
        if r in s:
            out.append(r)
    fl = [f[1:] for f in FLAG_UNITS if f in s]
    if len(fl) == 6:
        out.append("F")
    elif fl:
        out.append("F(" + ",".join(fl) + ")")
    sfl = [f[1:-1] for f in FLAG_UNITS if f + "'" in s]
    if len(sfl) == 6:
        out.append("F'")
    elif sfl:
        out.append("F'(" + ",".join(sfl) + ")")
    if "SP" in s and not drop_sp:
        out.append("SP")
    return " ".join(out) if out else "-"


class Instr:
    __slots__ = ("addr", "length", "mnem", "kind", "cond", "target", "reads",
                 "writes", "copies", "stack", "mem_r", "mem_w", "io", "invalid")

    def __init__(self, addr):
        self.addr = addr
        self.length = 1
        self.mnem = "?"
        self.kind = "seq"
        self.cond = None
        self.target = None
        self.reads = 0
        self.writes = 0
        self.copies = []
        self.stack = None
        self.mem_r = False
        self.mem_w = False
        self.io = None
        self.invalid = None

    def __repr__(self):
        return f"{self.addr:04X}: {self.mnem}"

    @property
    def is_call(self):
        return self.kind in ("call", "rst")

    @property
    def falls_through(self):
        if self.kind in ("seq", "halt", "call", "rst", "djnz"):
            return True
        if self.kind in ("jp", "jr", "ret") and self.cond:
            return True
        return False


R8 = ["B", "C", "D", "E", "H", "L", "(HL)", "A"]
RP = ["BC", "DE", "HL", "SP"]
RP2 = ["BC", "DE", "HL", "AF"]
ALU = ["add a,", "adc a,", "sub ", "sbc a,", "and ", "xor ", "or ", "cp "]
ROT = ["rlc", "rrc", "rl", "rr", "sla", "sra", "sll", "srl"]


def decode(read, addr):
    """Decode one instruction. `read(a)` returns the byte at a (int) or None."""
    ins = Instr(addr)
    pos = [addr]
    missing = [False]

    def nb():
        b = read(pos[0] & 0xFFFF)
        pos[0] += 1
        if b is None:
            missing[0] = True
            return 0
        return b

    def nw():
        lo = nb()
        return lo | nb() << 8

    def sdisp():
        d = nb()
        return d - 256 if d >= 128 else d

    op = nb()
    idx = None
    if op in (0xDD, 0xFD):
        idx = "IX" if op == 0xDD else "IY"
        op = nb()
        if op in (0xDD, 0xFD, 0xED):
            ins.invalid = "prefix followed by prefix"
            ins.mnem = f"db ${0xDD if idx == 'IX' else 0xFD:02X}"
            ins.length = 1
            return ins
    used_idx = [False]
    disp = [None]

    def HLn():
        if idx:
            used_idx[0] = True
            return idx
        return "HL"

    def r8(i, plain_hl=False):
        """(unit-name or None, text); i==6 means memory (HL)/(IX+d)."""
        n = R8[i]
        if i == 6:
            if idx:
                used_idx[0] = True
                if disp[0] is None:
                    disp[0] = sdisp()
                return None, f"({idx.lower()}{disp[0]:+d})"
            return None, "(hl)"
        if idx and not plain_hl and n in ("H", "L"):
            used_idx[0] = True
            u = idx + n
            return u, u.lower()
        return n, n.lower()

    def r8_mem_reads(i):
        """Units read to form the address of r8 operand i (6 = memory)."""
        if i != 6:
            return 0
        return pmask(idx) if idx else pmask("HL")

    if op == 0xCB:
        if idx:
            used_idx[0] = True
            d = sdisp()
            op2 = nb()
            x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
            opnd = f"({idx.lower()}{d:+d})"
            ins.reads |= pmask(idx)
            ins.mem_r = True
            extra = ""
            if x == 0:
                ins.mnem = f"{ROT[y]} {opnd}"
                ins.writes |= ALLF
                if y in (2, 3):
                    ins.reads |= FC
                ins.mem_w = True
                if y == 6:
                    ins.invalid = "undocumented sll"
            elif x == 1:
                ins.mnem = f"bit {y},{opnd}"
                ins.writes |= FS | FZ | FH | FPV | FN
            else:
                ins.mnem = f"{'res' if x == 2 else 'set'} {y},{opnd}"
                ins.mem_w = True
            if x != 1 and z != 6:
                # undocumented: result also copied into plain r[z]
                ins.writes |= m(R8[z])
                extra = f",{R8[z].lower()}"
                ins.invalid = "undocumented DDCB register copy"
            ins.mnem += extra
        else:
            op2 = nb()
            x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
            u, t = r8(z)
            src = m(u) if u else 0
            ins.reads |= src | r8_mem_reads(z)
            if z == 6:
                ins.mem_r = True
            if x == 0:
                ins.mnem = f"{ROT[y]} {t}"
                ins.writes |= ALLF | src
                if y in (2, 3):
                    ins.reads |= FC
                if z == 6:
                    ins.mem_w = True
                if y == 6:
                    ins.invalid = "undocumented sll"
            elif x == 1:
                ins.mnem = f"bit {y},{t}"
                ins.writes |= FS | FZ | FH | FPV | FN
            else:
                ins.mnem = f"{'res' if x == 2 else 'set'} {y},{t}"
                ins.writes |= src
                if z == 6:
                    ins.mem_w = True
        ins.length = pos[0] - addr
        if missing[0]:
            ins.invalid = "runs off image"
        return ins

    if op == 0xED:
        op2 = nb()
        x, y, z = op2 >> 6, (op2 >> 3) & 7, op2 & 7
        p, q = y >> 1, y & 1
        if x == 1:
            if z == 0:
                ins.reads |= m("B", "C")
                ins.writes |= FS | FZ | FH | FPV | FN
                ins.io = ("in", None)
                if y == 6:
                    ins.mnem = "in (c)"
                    ins.invalid = "undocumented in (c)"
                else:
                    ins.writes |= m(R8[y])
                    ins.mnem = f"in {R8[y].lower()},(c)"
            elif z == 1:
                ins.reads |= m("B", "C")
                ins.io = ("out", None)
                if y == 6:
                    ins.mnem = "out (c),0"
                    ins.invalid = "undocumented out (c),0"
                else:
                    ins.reads |= m(R8[y])
                    ins.mnem = f"out (c),{R8[y].lower()}"
            elif z == 2:
                rp = RP[p]
                ins.reads |= m("H", "L") | (pmask(rp) if rp != "SP" else SP) | FC
                ins.writes |= m("H", "L") | ALLF
                ins.mnem = f"{'sbc' if q == 0 else 'adc'} hl,{rp.lower()}"
            elif z == 3:
                nn = nw()
                rp = RP[p]
                if q == 0:
                    ins.reads |= pmask(rp) if rp != "SP" else SP
                    ins.mem_w = True
                    ins.mnem = f"ld (${nn:04X}),{rp.lower()}"
                else:
                    ins.mem_r = True
                    ins.mnem = f"ld {rp.lower()},(${nn:04X})"
                    if rp == "SP":
                        ins.writes |= SP
                        ins.stack = ("ldsp", f"(${nn:04X})")
                    else:
                        ins.writes |= pmask(rp)
            elif z == 4:
                ins.mnem = "neg"
                ins.reads |= m("A")
                ins.writes |= m("A") | ALLF
                if y:
                    ins.invalid = "undocumented neg mirror"
            elif z == 5:
                ins.kind = "reti" if y == 1 else "retn"
                ins.mnem = ins.kind
                ins.reads |= SP
                ins.writes |= SP
                ins.mem_r = True
                if y not in (0, 1):
                    ins.invalid = "undocumented retn mirror"
            elif z == 6:
                ins.mnem = f"im {[0, 0, 1, 2][y & 3]}"
                if y not in (0, 2, 3):
                    ins.invalid = "undocumented im mirror"
            else:
                if y == 0:
                    ins.mnem, ins.reads = "ld i,a", m("A")
                elif y == 1:
                    ins.mnem, ins.reads = "ld r,a", m("A")
                elif y in (2, 3):
                    ins.mnem = "ld a,i" if y == 2 else "ld a,r"
                    ins.writes = m("A") | FS | FZ | FH | FPV | FN
                elif y in (4, 5):
                    ins.mnem = "rrd" if y == 4 else "rld"
                    ins.reads = m("A", "H", "L")
                    ins.writes = m("A") | FS | FZ | FH | FPV | FN
                    ins.mem_r = ins.mem_w = True
                else:
                    ins.mnem = f"db $ED,${op2:02X}"
                    ins.invalid = "undefined ED opcode"
        elif x == 2 and z <= 3 and y >= 4:
            base = [["ldi", "cpi", "ini", "outi"], ["ldd", "cpd", "ind", "outd"],
                    ["ldir", "cpir", "inir", "otir"], ["lddr", "cpdr", "indr", "otdr"]][y - 4][z]
            ins.mnem = base
            if z == 0:
                ins.reads = m("B", "C", "D", "E", "H", "L")
                ins.writes = m("B", "C", "D", "E", "H", "L") | FH | FPV | FN
                ins.mem_r = ins.mem_w = True
            elif z == 1:
                ins.reads = m("A", "B", "C", "H", "L")
                ins.writes = m("B", "C", "H", "L") | FS | FZ | FH | FPV | FN
                ins.mem_r = True
            elif z == 2:
                ins.reads = m("B", "C", "H", "L")
                ins.writes = m("B", "H", "L") | ALLF
                ins.mem_w = True
                ins.io = ("in", None)
            else:
                ins.reads = m("B", "C", "H", "L")
                ins.writes = m("B", "H", "L") | ALLF
                ins.mem_r = True
                ins.io = ("out", None)
        else:
            ins.mnem = f"db $ED,${op2:02X}"
            ins.invalid = "undefined ED opcode"
        ins.length = pos[0] - addr
        if missing[0]:
            ins.invalid = "runs off image"
        return ins

    # ---- unprefixed (possibly DD/FD-substituted) ------------------------
    x, y, z = op >> 6, (op >> 3) & 7, op & 7
    p, q = y >> 1, y & 1
    hl = HLn  # call lazily: only marks used_idx when the HL form is really used

    def rel():
        d = sdisp()
        return (pos[0] + d) & 0xFFFF

    if x == 0:
        if z == 0:
            if y == 0:
                ins.mnem = "nop"
            elif y == 1:
                ins.mnem = "ex af,af'"
                ins.copies = [(U["A"], U["A'"]), (U["A'"], U["A"])] + \
                    [(U[f], U[f + "'"]) for f in FLAG_UNITS] + [(U[f + "'"], U[f]) for f in FLAG_UNITS]
            elif y == 2:
                ins.target = rel()
                ins.kind = "djnz"
                ins.reads = ins.writes = m("B")
                ins.mnem = f"djnz ${ins.target:04X}"
            else:
                ins.target = rel()
                ins.kind = "jr"
                if y >= 4:
                    ins.cond = CC[y - 4]
                    ins.reads = COND_FLAG[ins.cond]
                    ins.mnem = f"jr {ins.cond},${ins.target:04X}"
                else:
                    ins.mnem = f"jr ${ins.target:04X}"
        elif z == 1:
            rp = RP[p]
            if rp == "HL":
                rp = hl()
            if q == 0:
                nn = nw()
                ins.mnem = f"ld {rp.lower()},${nn:04X}"
                if rp == "SP":
                    ins.writes = SP
                    ins.stack = ("ldsp", f"${nn:04X}")
                else:
                    ins.writes = pmask(rp)
            else:
                h = hl()
                ins.mnem = f"add {h.lower()},{rp.lower()}"
                ins.reads = pmask(h) | (SP if rp == "SP" else pmask(rp))
                ins.writes = pmask(h) | FH | FN | FC
        elif z == 2:
            if p in (0, 1):
                rp = "BC" if p == 0 else "DE"
                ins.reads = pmask(rp)
                if q == 0:
                    ins.mnem = f"ld ({rp.lower()}),a"
                    ins.reads |= m("A")
                    ins.mem_w = True
                else:
                    ins.mnem = f"ld a,({rp.lower()})"
                    ins.writes = m("A")
                    ins.mem_r = True
            else:
                nn = nw()
                if p == 2:
                    h = hl()
                    if q == 0:
                        ins.mnem = f"ld (${nn:04X}),{h.lower()}"
                        ins.reads = pmask(h)
                        ins.mem_w = True
                    else:
                        ins.mnem = f"ld {h.lower()},(${nn:04X})"
                        ins.writes = pmask(h)
                        ins.mem_r = True
                else:
                    if q == 0:
                        ins.mnem = f"ld (${nn:04X}),a"
                        ins.reads = m("A")
                        ins.mem_w = True
                    else:
                        ins.mnem = f"ld a,(${nn:04X})"
                        ins.writes = m("A")
                        ins.mem_r = True
        elif z == 3:
            rp = RP[p]
            if rp == "HL":
                rp = hl()
            ins.mnem = f"{'inc' if q == 0 else 'dec'} {rp.lower()}"
            if rp == "SP":
                ins.reads = ins.writes = SP
                ins.stack = ("adjsp", -1 if q == 0 else +1)   # change of DEPTH
            else:
                ins.reads = ins.writes = pmask(rp)
        elif z in (4, 5):
            u, t = r8(y)
            ins.mnem = f"{'inc' if z == 4 else 'dec'} {t}"
            ins.reads = (m(u) if u else 0) | r8_mem_reads(y)
            ins.writes = (m(u) if u else 0) | FS | FZ | FH | FPV | FN
            if y == 6:
                ins.mem_r = ins.mem_w = True
        elif z == 6:
            u, t = r8(y)
            n = nb()
            ins.mnem = f"ld {t},${n:02X}"
            ins.reads = r8_mem_reads(y)
            if u:
                ins.writes = m(u)
            else:
                ins.mem_w = True
        else:
            names = ["rlca", "rrca", "rla", "rra", "daa", "cpl", "scf", "ccf"]
            ins.mnem = names[y]
            if y < 4:
                ins.reads = m("A") | (FC if y in (2, 3) else 0)
                ins.writes = m("A") | FH | FN | FC
            elif y == 4:
                ins.reads = m("A") | FC | FH | FN
                ins.writes = m("A") | FS | FZ | FH | FPV | FC
            elif y == 5:
                ins.reads = m("A")
                ins.writes = m("A") | FH | FN
            elif y == 6:
                ins.writes = FH | FN | FC
            else:
                ins.reads = FC
                ins.writes = FH | FN | FC
    elif x == 1:
        if y == 6 and z == 6:
            ins.mnem = "halt"
            ins.kind = "halt"
        else:
            mem = (y == 6 or z == 6)
            du, dt = r8(y, plain_hl=mem)
            su, st = r8(z, plain_hl=mem)
            ins.mnem = f"ld {dt},{st}"
            ins.reads = r8_mem_reads(y) | r8_mem_reads(z)
            if du and su:
                ins.copies = [(U[du], U[su])]
            elif du:
                ins.writes = m(du)
                ins.mem_r = True
            else:
                ins.reads |= m(su)
                ins.mem_w = True
    elif x == 2:
        u, t = r8(z)
        ins.mnem = f"{ALU[y]}{t}"
        ins.reads = m("A") | (m(u) if u else 0) | r8_mem_reads(z) | (FC if y in (1, 3) else 0)
        ins.writes = ALLF | (m("A") if y != 7 else 0)
        if z == 6:
            ins.mem_r = True
        if y in (2, 5, 6) and z == 7 and False:
            pass
        if y == 5 and z == 7:      # xor a: no real read of A
            ins.reads &= ~m("A")
        if y == 2 and z == 7:      # sub a
            ins.reads &= ~m("A")
    else:
        if z == 0:
            ins.kind = "ret"
            ins.cond = CC[y]
            ins.reads = COND_FLAG[ins.cond] | SP
            ins.writes = SP
            ins.mem_r = True
            ins.mnem = f"ret {ins.cond}"
        elif z == 1:
            if q == 0:
                rp = RP2[p]
                if rp == "HL":
                    rp = hl()
                ins.mnem = f"pop {rp.lower()}"
                ins.reads = SP
                ins.writes = SP | pmask(rp)
                ins.stack = ("pop", rp)
                ins.mem_r = True
            elif p == 0:
                ins.kind = "ret"
                ins.mnem = "ret"
                ins.reads = ins.writes = SP
                ins.mem_r = True
            elif p == 1:
                ins.mnem = "exx"
                ins.copies = []
                for r in "BCDEHL":
                    ins.copies += [(U[r], U[r + "'"]), (U[r + "'"], U[r])]
            elif p == 2:
                h = hl()
                ins.kind = "jpind"
                ins.mnem = f"jp ({h.lower()})"
                ins.reads = pmask(h)
            else:
                h = hl()
                ins.mnem = f"ld sp,{h.lower()}"
                ins.reads = pmask(h)
                ins.writes = SP
                ins.stack = ("ldsp", h)
        elif z == 2:
            ins.target = nw()
            ins.kind = "jp"
            ins.cond = CC[y]
            ins.reads = COND_FLAG[ins.cond]
            ins.mnem = f"jp {ins.cond},${ins.target:04X}"
        elif z == 3:
            if y == 0:
                ins.target = nw()
                ins.kind = "jp"
                ins.mnem = f"jp ${ins.target:04X}"
            elif y == 2:
                n = nb()
                ins.mnem = f"out (${n:02X}),a"
                ins.reads = m("A")
                ins.io = ("out", n)
            elif y == 3:
                n = nb()
                ins.mnem = f"in a,(${n:02X})"
                ins.reads = m("A")       # A is the high address byte on the bus
                ins.writes = m("A")
                ins.io = ("in", n)
            elif y == 4:
                h = hl()
                ins.mnem = f"ex (sp),{h.lower()}"
                ins.reads = pmask(h) | SP
                ins.writes = pmask(h)
                ins.stack = ("exsp", h)
                ins.mem_r = ins.mem_w = True
            elif y == 5:
                ins.mnem = "ex de,hl"     # never IX/IY-substituted
                ins.copies = [(U["D"], U["H"]), (U["H"], U["D"]), (U["E"], U["L"]), (U["L"], U["E"])]
            elif y == 6:
                ins.mnem = "di"
            else:
                ins.mnem = "ei"
        elif z == 4:
            ins.target = nw()
            ins.kind = "call"
            ins.cond = CC[y]
            ins.reads = COND_FLAG[ins.cond] | SP
            ins.writes = SP
            ins.mem_w = True
            ins.mnem = f"call {ins.cond},${ins.target:04X}"
        elif z == 5:
            if q == 0:
                rp = RP2[p]
                if rp == "HL":
                    rp = hl()
                ins.mnem = f"push {rp.lower()}"
                ins.reads = SP | pmask(rp)
                ins.writes = SP
                ins.stack = ("push", rp)
                ins.mem_w = True
            else:
                ins.target = nw()
                ins.kind = "call"
                ins.reads = SP
                ins.writes = SP
                ins.mem_w = True
                ins.mnem = f"call ${ins.target:04X}"
        elif z == 6:
            n = nb()
            ins.mnem = f"{ALU[y]}${n:02X}"
            ins.reads = m("A") | (FC if y in (1, 3) else 0)
            ins.writes = ALLF | (m("A") if y != 7 else 0)
        else:
            ins.target = y * 8
            ins.kind = "rst"
            ins.reads = SP
            ins.writes = SP
            ins.mem_w = True
            ins.mnem = f"rst ${ins.target:02X}"
    if idx and not used_idx[0]:
        ins.invalid = "useless DD/FD prefix"
    ins.length = pos[0] - addr
    if missing[0]:
        ins.invalid = "runs off image"
    return ins
