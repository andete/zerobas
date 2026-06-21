# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""A small, embeddable Z80 CPU core for host-side unit testing.

This is NOT a machine emulator: there is no VDP/PSG/slots/interrupts/timing —
just the Z80 instruction set executing against a flat 64 KB memory array, with
hooks so a test harness can trap BIOS / dependency entry points (see msxtest.py).

Scope: the documented opcode set zerobas's routines actually use. Every opcode
zerobas reaches is implemented; an unimplemented opcode raises with the PC and
byte, so a new test that hits a gap fails loudly and points at the exact opcode
to add (no silent miscompute). Flags follow the standard Z80 rules for the
arithmetic/logical/shift ops the firmware depends on; the undocumented bits 3/5
are approximated from the result (no firmware path here branches on them).

For a production suite this can be swapped for a battle-tested core behind the
same .reg/.mem interface — the harness does not depend on this implementation.
"""

S, Z, Y, H, X, PV, N, C = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01

PARITY = [0] * 256
for _i in range(256):
    PARITY[_i] = PV if bin(_i).count("1") % 2 == 0 else 0


class Z80:
    def __init__(self, mem):
        self.m = mem                       # 64 KB bytearray (shared with harness)
        self.a = self.f = 0
        self.b = self.c = self.d = self.e = self.h = self.l = 0
        self.ix = self.iy = 0
        self.sp = 0xF380
        self.pc = 0
        self.halted = False
        # Port I/O hooks. A unit test that exercises OUT/IN (e.g. the OUT
        # statement) wires these to record or supply port traffic; by default a
        # read returns the bus-idle $FF and a write is dropped. (port,val).
        self.io_out = lambda port, val: None
        self.io_in = lambda port: 0xFF

    # --- 16-bit register pairs -------------------------------------------
    def _gp(n):  # generate a bc/de/hl property from its two byte fields
        hi, lo = n
        def g(self):
            return (getattr(self, hi) << 8) | getattr(self, lo)
        def s(self, v):
            setattr(self, hi, (v >> 8) & 0xFF)
            setattr(self, lo, v & 0xFF)
        return property(g, s)
    bc = _gp(("b", "c")); de = _gp(("d", "e")); hl = _gp(("h", "l"))

    @property
    def af(self):
        return (self.a << 8) | self.f

    @af.setter
    def af(self, v):
        self.a = (v >> 8) & 0xFF
        self.f = v & 0xFF

    # --- memory / fetch ---------------------------------------------------
    def rb(self, a):
        return self.m[a & 0xFFFF]

    def wb(self, a, v):
        self.m[a & 0xFFFF] = v & 0xFF

    def rw(self, a):
        return self.rb(a) | (self.rb(a + 1) << 8)

    def ww(self, a, v):
        self.wb(a, v); self.wb(a + 1, v >> 8)

    def fetch(self):
        v = self.rb(self.pc); self.pc = (self.pc + 1) & 0xFFFF; return v

    def fetch2(self):
        v = self.rw(self.pc); self.pc = (self.pc + 2) & 0xFFFF; return v

    def push(self, v):
        self.sp = (self.sp - 2) & 0xFFFF; self.ww(self.sp, v)

    def pop(self):
        v = self.rw(self.sp); self.sp = (self.sp + 2) & 0xFFFF; return v

    # --- flag helpers -----------------------------------------------------
    def _szyx(self, r):
        return (r & (S | Y | X)) | (Z if r == 0 else 0)

    def add8(self, a, b, carry=0):
        r = a + b + carry
        rr = r & 0xFF
        f = self._szyx(rr)
        f |= H if ((a & 0xF) + (b & 0xF) + carry) & 0x10 else 0
        f |= C if r & 0x100 else 0
        f |= PV if (~(a ^ b) & (a ^ rr)) & 0x80 else 0
        self.f = f; return rr

    def sub8(self, a, b, carry=0, store=True):
        r = a - b - carry
        rr = r & 0xFF
        f = self._szyx(rr) | N
        f |= H if ((a & 0xF) - (b & 0xF) - carry) & 0x10 else 0
        f |= C if r & 0x100 else 0
        f |= PV if ((a ^ b) & (a ^ rr)) & 0x80 else 0
        self.f = f; return rr

    def logic(self, r, hflag):
        self.f = self._szyx(r) | PARITY[r] | hflag

    def inc8(self, v):
        r = (v + 1) & 0xFF
        f = (self.f & C) | self._szyx(r)
        f |= H if (v & 0xF) == 0xF else 0
        f |= PV if v == 0x7F else 0
        self.f = f; return r

    def dec8(self, v):
        r = (v - 1) & 0xFF
        f = (self.f & C) | self._szyx(r) | N
        f |= H if (v & 0xF) == 0 else 0
        f |= PV if v == 0x80 else 0
        self.f = f; return r

    def add16(self, a, b):
        r = a + b
        f = (self.f & (S | Z | PV))
        f |= H if ((a & 0xFFF) + (b & 0xFFF)) & 0x1000 else 0
        f |= C if r & 0x10000 else 0
        f |= (r >> 8) & (Y | X)
        self.f = f; return r & 0xFFFF

    def adc16(self, a, b):
        c = self.f & C
        r = a + b + c
        rr = r & 0xFFFF
        f = (S if rr & 0x8000 else 0) | (Z if rr == 0 else 0)
        f |= H if ((a & 0xFFF) + (b & 0xFFF) + c) & 0x1000 else 0
        f |= C if r & 0x10000 else 0
        f |= PV if (~(a ^ b) & (a ^ rr)) & 0x8000 else 0
        f |= (rr >> 8) & (Y | X)
        self.f = f; return rr

    def sbc16(self, a, b):
        c = self.f & C
        r = a - b - c
        rr = r & 0xFFFF
        f = (S if rr & 0x8000 else 0) | (Z if rr == 0 else 0) | N
        f |= H if ((a & 0xFFF) - (b & 0xFFF) - c) & 0x1000 else 0
        f |= C if r & 0x10000 else 0
        f |= PV if ((a ^ b) & (a ^ rr)) & 0x8000 else 0
        f |= (rr >> 8) & (Y | X)
        self.f = f; return rr

    # --- 8-bit register access by 3-bit code (B C D E H L (HL) A) ---------
    _R = ("b", "c", "d", "e", "h", "l", None, "a")

    def get_r(self, code, idx=None, disp=0):
        if code == 6:                      # (HL), or (IX+d)/(IY+d) under a prefix
            base = self.hl if idx is None else getattr(self, idx)
            return self.rb((base + disp) & 0xFFFF)
        return getattr(self, self._R[code])

    def set_r(self, code, val, idx=None, disp=0):
        if code == 6:
            base = self.hl if idx is None else getattr(self, idx)
            self.wb((base + disp) & 0xFFFF, val)
        else:
            setattr(self, self._R[code], val & 0xFF)

    def cond(self, code):  # NZ Z NC C PO PE P M
        f = self.f
        return [not f & Z, f & Z, not f & C, f & C,
                not f & PV, f & PV, not f & S, f & S][code]

    # --- one instruction --------------------------------------------------
    def step(self):
        op = self.fetch()
        if op == 0xCB:
            return self._cb()
        if op == 0xED:
            return self._ed()
        if op == 0xDD:
            return self._idx("ix")
        if op == 0xFD:
            return self._idx("iy")
        self._main(op)

    def _main(self, op, idx=None, disp=0):
        # 0x40-0x7F: LD r,r'  (0x76 = HALT)
        if 0x40 <= op <= 0x7F:
            if op == 0x76:
                self.halted = True; return
            dst, src = (op >> 3) & 7, op & 7
            # with an index prefix only the (HL) slot uses (idx+d); a reg/reg
            # move keeps plain registers
            self.set_r(dst, self.get_r(src, idx, disp), idx, disp)
            return
        # 0x80-0xBF: ALU A,r'
        if 0x80 <= op <= 0xBF:
            self._alu((op >> 3) & 7, self.get_r(op & 7, idx, disp)); return

        h = op & 0xF0
        lo = op & 0x0F
        if op == 0x00:                         # NOP
            return
        if op == 0x08:                         # EX AF,AF' (no shadow set needed)
            return
        if op == 0xEB:                         # EX DE,HL
            self.de, self.hl = self.hl, self.de; return
        if op == 0xE3:                         # EX (SP),HL/idx
            t = self.rw(self.sp)
            if idx:
                self.ww(self.sp, getattr(self, idx)); setattr(self, idx, t)
            else:
                self.ww(self.sp, self.hl); self.hl = t
            return
        # LD rr,nn
        if op in (0x01, 0x11, 0x21, 0x31):
            v = self.fetch2()
            if op == 0x21 and idx: setattr(self, idx, v)
            else: [self.__setattr__(k, v) for k in (["bc","de","hl","sp"][op >> 4],)]
            return
        # INC/DEC rr
        if op in (0x03, 0x13, 0x23, 0x33):
            k = ["bc", "de", "hl", "sp"][op >> 4]
            if op == 0x23 and idx: setattr(self, idx, (getattr(self, idx) + 1) & 0xFFFF)
            else: setattr(self, k, (getattr(self, k) + 1) & 0xFFFF)
            return
        if op in (0x0B, 0x1B, 0x2B, 0x3B):
            k = ["bc", "de", "hl", "sp"][op >> 4]
            if op == 0x2B and idx: setattr(self, idx, (getattr(self, idx) - 1) & 0xFFFF)
            else: setattr(self, k, (getattr(self, k) - 1) & 0xFFFF)
            return
        # ADD HL,rr / ADD idx,rr
        if op in (0x09, 0x19, 0x29, 0x39):
            src = ["bc", "de", "hl", "sp"][op >> 4]
            if idx:
                a = getattr(self, idx)
                b = a if op == 0x29 else getattr(self, src)
                setattr(self, idx, self.add16(a, b))
            else:
                self.hl = self.add16(self.hl, getattr(self, src))
            return
        # INC/DEC r
        if op & 0xC7 == 0x04:
            r = (op >> 3) & 7
            self.set_r(r, self.inc8(self.get_r(r, idx, disp)), idx, disp); return
        if op & 0xC7 == 0x05:
            r = (op >> 3) & 7
            self.set_r(r, self.dec8(self.get_r(r, idx, disp)), idx, disp); return
        # LD r,n
        if op & 0xC7 == 0x06:
            r = (op >> 3) & 7
            n = self.fetch()
            self.set_r(r, n, idx, disp); return
        # accumulator/memory loads
        if op == 0x0A: self.a = self.rb(self.bc); return
        if op == 0x1A: self.a = self.rb(self.de); return
        if op == 0x02: self.wb(self.bc, self.a); return
        if op == 0x12: self.wb(self.de, self.a); return
        if op == 0x3A: self.a = self.rb(self.fetch2()); return
        if op == 0x32: self.wb(self.fetch2(), self.a); return
        if op == 0x2A:
            v = self.rw(self.fetch2())
            if idx: setattr(self, idx, v)
            else: self.hl = v
            return
        if op == 0x22:
            self.ww(self.fetch2(), getattr(self, idx) if idx else self.hl); return
        # rotates on A
        if op == 0x07:                         # RLCA
            self.a = ((self.a << 1) | (self.a >> 7)) & 0xFF
            self.f = (self.f & (S|Z|PV)) | (self.a & (Y|X)) | (C if self.a & 1 else 0); return
        if op == 0x0F:                         # RRCA
            c = self.a & 1
            self.a = ((self.a >> 1) | (c << 7)) & 0xFF
            self.f = (self.f & (S|Z|PV)) | (self.a & (Y|X)) | (C if c else 0); return
        if op == 0x17:                         # RLA
            c = self.f & C
            nc = self.a >> 7
            self.a = ((self.a << 1) | c) & 0xFF
            self.f = (self.f & (S|Z|PV)) | (self.a & (Y|X)) | (C if nc else 0); return
        if op == 0x1F:                         # RRA
            c = self.f & C
            nc = self.a & 1
            self.a = ((self.a >> 1) | (c << 7)) & 0xFF
            self.f = (self.f & (S|Z|PV)) | (self.a & (Y|X)) | (C if nc else 0); return
        if op == 0x2F:                         # CPL
            self.a ^= 0xFF
            self.f = (self.f & (S|Z|PV|C)) | H | N | (self.a & (Y|X)); return
        if op == 0x37:                         # SCF
            self.f = (self.f & (S|Z|PV)) | (self.a & (Y|X)) | C; return
        if op == 0x3F:                         # CCF
            c = self.f & C
            self.f = (self.f & (S|Z|PV)) | (self.a & (Y|X)) | (H if c else 0) | (0 if c else C); return
        # relative jumps
        if op == 0x18: d = self._sb(); self.pc = (self.pc + d) & 0xFFFF; return
        if op == 0x10:                         # DJNZ
            d = self._sb(); self.b = (self.b - 1) & 0xFF
            if self.b: self.pc = (self.pc + d) & 0xFFFF
            return
        if op in (0x20, 0x28, 0x30, 0x38):
            d = self._sb()
            if self.cond((op >> 3) & 3): self.pc = (self.pc + d) & 0xFFFF
            return
        # absolute jumps / calls / returns
        if op == 0xC3: self.pc = self.fetch2(); return
        if op == 0xE9: self.pc = getattr(self, idx) if idx else self.hl; return
        if op & 0xC7 == 0xC2:                  # JP cc,nn
            t = self.fetch2()
            if self.cond((op >> 3) & 7): self.pc = t
            return
        if op == 0xCD: t = self.fetch2(); self.push(self.pc); self.pc = t; return
        if op & 0xC7 == 0xC4:                  # CALL cc,nn
            t = self.fetch2()
            if self.cond((op >> 3) & 7): self.push(self.pc); self.pc = t
            return
        if op == 0xC9: self.pc = self.pop(); return
        if op & 0xC7 == 0xC0:                  # RET cc
            if self.cond((op >> 3) & 7): self.pc = self.pop()
            return
        if op & 0xC7 == 0xC7:                  # RST
            self.push(self.pc); self.pc = op & 0x38; return
        # push / pop
        if op in (0xC5, 0xD5, 0xE5, 0xF5):
            pr = ["bc", "de", "hl", "af"][(op >> 4) - 0xC]
            self.push(getattr(self, idx) if (op == 0xE5 and idx) else getattr(self, pr)); return
        if op in (0xC1, 0xD1, 0xE1, 0xF1):
            v = self.pop()
            if op == 0xE1 and idx: setattr(self, idx, v)
            else: setattr(self, ["bc", "de", "hl", "af"][(op >> 4) - 0xC], v)
            return
        # immediate ALU  (ADD/ADC/SUB/SBC/AND/XOR/OR/CP A,n)
        if op in (0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE):
            self._alu((op >> 3) & 7, self.fetch()); return
        if op == 0xF9:                         # LD SP,HL/idx
            self.sp = getattr(self, idx) if idx else self.hl; return
        if op in (0xF3, 0xFB):                 # DI / EI (no interrupts modelled)
            return
        if op == 0xD3:                         # OUT (n),A  — port = n (A on hi bus)
            self.io_out(self.fetch(), self.a); return
        if op == 0xDB:                         # IN A,(n)
            self.a = self.io_in(self.fetch()) & 0xFF; return
        raise NotImplementedError(
            f"opcode {op:#04x} at PC {self.pc - 1:#06x}"
            + ("" if idx is None else f" (index {idx})"))

    def _alu(self, kind, v):
        a = self.a
        if kind == 0: self.a = self.add8(a, v)
        elif kind == 1: self.a = self.add8(a, v, self.f & C)
        elif kind == 2: self.a = self.sub8(a, v)
        elif kind == 3: self.a = self.sub8(a, v, self.f & C)
        elif kind == 4: self.a = a & v; self.logic(self.a, H)
        elif kind == 5: self.a = a ^ v; self.logic(self.a, 0)
        elif kind == 6: self.a = a | v; self.logic(self.a, 0)
        elif kind == 7: self.sub8(a, v)        # CP: flags only

    def _sb(self):                             # signed displacement byte
        d = self.fetch()
        return d - 256 if d >= 128 else d

    # --- CB-prefixed rotates/shifts/bit ops -------------------------------
    def _cb(self, idx=None, disp=0):
        op = self.fetch()
        r = op & 7
        v = self.get_r(r, idx, disp)
        kind = (op >> 3) & 7
        sel = op >> 6
        if sel == 0:                           # rotate/shift group
            if kind == 0:   c = v >> 7; v = ((v << 1) | c) & 0xFF           # RLC
            elif kind == 1: c = v & 1; v = ((v >> 1) | (c << 7)) & 0xFF     # RRC
            elif kind == 2: c = v >> 7; v = ((v << 1) | (self.f & C)) & 0xFF  # RL
            elif kind == 3: c = v & 1; v = ((v >> 1) | ((self.f & C) << 7)) & 0xFF  # RR
            elif kind == 4: c = v >> 7; v = (v << 1) & 0xFF                 # SLA
            elif kind == 5: c = v & 1; v = ((v >> 1) | (v & 0x80)) & 0xFF   # SRA
            elif kind == 6: c = v >> 7; v = ((v << 1) | 1) & 0xFF          # SLL
            else:           c = v & 1; v = (v >> 1) & 0xFF                 # SRL
            self.f = self._szyx(v) | PARITY[v] | (C if c else 0)
            self.set_r(r, v, idx, disp); return
        if sel == 1:                           # BIT
            bit = v & (1 << kind)
            self.f = (self.f & C) | H | (Z | PV if not bit else 0) | (bit & S)
            self.f |= (v & (Y | X)) if idx is None else 0
            return
        if sel == 2:                           # RES
            self.set_r(r, v & ~(1 << kind), idx, disp); return
        self.set_r(r, v | (1 << kind), idx, disp)   # SET

    # --- ED-prefixed (16-bit memory loads, sbc/adc hl, block ops) ---------
    def _ed(self):
        op = self.fetch()
        if op in (0x43, 0x53, 0x63, 0x73):     # LD (nn),rr
            self.ww(self.fetch2(), getattr(self, ["bc", "de", "hl", "sp"][(op >> 4) - 4])); return
        if op in (0x4B, 0x5B, 0x6B, 0x7B):     # LD rr,(nn)
            setattr(self, ["bc", "de", "hl", "sp"][(op >> 4) - 4], self.rw(self.fetch2())); return
        if op in (0x42, 0x52, 0x62, 0x72):     # SBC HL,rr
            self.hl = self.sbc16(self.hl, getattr(self, ["bc", "de", "hl", "sp"][(op >> 4) - 4])); return
        if op in (0x4A, 0x5A, 0x6A, 0x7A):     # ADC HL,rr
            self.hl = self.adc16(self.hl, getattr(self, ["bc", "de", "hl", "sp"][(op >> 4) - 4])); return
        if op == 0x44:                         # NEG
            self.a = self.sub8(0, self.a); return
        if op in (0xB0, 0xB8, 0xA0, 0xA8):     # LDIR/LDDR/LDI/LDD
            step = 1 if op in (0xB0, 0xA0) else -1
            self.wb(self.de, self.rb(self.hl))
            self.de = (self.de + step) & 0xFFFF
            self.hl = (self.hl + step) & 0xFFFF
            self.bc = (self.bc - 1) & 0xFFFF
            self.f &= (S | Z | C)
            if op in (0xB0, 0xB8) and self.bc:
                self.pc = (self.pc - 2) & 0xFFFF       # repeat
            return
        if op in (0x46, 0x56, 0x5E, 0x4E, 0x66, 0x6E, 0x76, 0x7E):  # IM n
            return
        if op in (0x47, 0x4F, 0x57, 0x5F):     # LD I/R,A and back (no I/R modelled)
            return
        if op in (0x45, 0x4D):                 # RETN / RETI
            self.pc = self.pop(); return
        if op & 0xC7 == 0x41 and op != 0x71:   # OUT (C),r   (port = BC)
            self.io_out(self.bc, self.get_r((op >> 3) & 7)); return
        if op == 0x71:                         # OUT (C),0   (undocumented)
            self.io_out(self.bc, 0); return
        if op & 0xC7 == 0x40:                  # IN r,(C)    (port = BC), sets flags
            v = self.io_in(self.bc) & 0xFF
            if ((op >> 3) & 7) != 6:           # 0x70 = IN (C): flags only, no store
                self.set_r((op >> 3) & 7, v)
            self.f = (self.f & C) | self._szyx(v) | PARITY[v]
            return
        raise NotImplementedError(f"ED opcode {op:#04x} at PC {self.pc - 2:#06x}")

    # --- DD/FD index-prefixed ---------------------------------------------
    def _idx(self, reg):
        op = self.fetch()
        if op == 0xCB:                         # DDCB/FDCB: displacement THEN opcode
            disp = self._sb()
            return self._cb(idx=reg, disp=disp)
        # ops that take a (idx+d) operand fetch the displacement now
        disp = 0
        needs_d = (0x40 <= op <= 0x7F and (op & 7) == 6) or \
                  (0x40 <= op <= 0x7F and ((op >> 3) & 7) == 6) or \
                  (0x80 <= op <= 0xBF and (op & 7) == 6) or \
                  (op & 0xC7) in (0x04, 0x05, 0x06) and ((op >> 3) & 7) == 6
        if needs_d:
            disp = self._sb()
        self._main(op, idx=reg, disp=disp)
