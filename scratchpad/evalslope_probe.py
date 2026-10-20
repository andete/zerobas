# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EVALSLOPE (2026-10-20): the evaluator's stack per pending construct, and its
T-states per construct, measured on the HOST Z80 (tests/z80.py) -- no emulator.

    python3 scratchpad/evalslope_probe.py [--root DIR] [--label NAME]

--root assembles DIR/basic/main.asm instead of this tree's (point it at a
`git archive HEAD basic | tar -x` copy to read the BEFORE side).

Two readings per row, both from `call eval` on the tokenised text:
  * DEPTH: the lowest SP the main side reaches below eval's own entry SP (the
    harness's call frame), over the whole evaluation;
  * T: the Z80 T-states of the whole `call eval`, plain Z80 timings (no MSX M1
    wait state), from a table over the opcode bytes at each step; a conditional
    transfer is charged its taken/not-taken time from where the PC went.
SLOPE rows evaluate the same construct nested N and N+1 deep and print the
difference: the bytes one more PENDING construct holds. Every row's value is
also checked against the expected result, so a wrong answer cannot pass as a
fast one.

No row reaches a sub-ROM tenant (`^` and the transcendentals do, and the host
core does not run the sub ROM's code), so `^` is not a row: it takes the same
typed-frame path as `* /`.
"""

import argparse
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from msxtest import Machine  # noqa: E402

RELOC_BASE = 0x2781
SRC, TOKBUF = 0xC000, 0xC100


# --------------------------------------------------------------------------
# Z80 T-states (plain Z80, as the source comments count them)
# --------------------------------------------------------------------------
def _main_t(op):
    """(base, taken) for an unprefixed opcode; taken=None if unconditional."""
    if 0x40 <= op <= 0x7F:
        return (7 if (op & 7) == 6 or ((op >> 3) & 7) == 6 else 4), None
    if 0x80 <= op <= 0xBF:
        return (7 if (op & 7) == 6 else 4), None
    T = {
        0x00: 4, 0x01: 10, 0x02: 7, 0x03: 6, 0x07: 4, 0x08: 4, 0x09: 11, 0x0A: 7,
        0x0B: 6, 0x0F: 4, 0x11: 10, 0x12: 7, 0x13: 6, 0x17: 4, 0x18: 12, 0x19: 11,
        0x1A: 7, 0x1B: 6, 0x1F: 4, 0x21: 10, 0x22: 16, 0x23: 6, 0x27: 4, 0x29: 11,
        0x2A: 16, 0x2B: 6, 0x2F: 4, 0x31: 10, 0x32: 13, 0x33: 6, 0x34: 11, 0x35: 11,
        0x36: 10, 0x37: 4, 0x39: 11, 0x3A: 13, 0x3B: 6, 0x3F: 4,
        0xC3: 10, 0xC9: 10, 0xCD: 17, 0xD3: 11, 0xD9: 4, 0xDB: 11, 0xE3: 19,
        0xE9: 4, 0xEB: 4, 0xF3: 4, 0xF9: 6, 0xFB: 4,
    }
    if op in T:
        return T[op], None
    lo3 = op & 7
    if op < 0x40:
        if lo3 in (4, 5):
            return 4, None                     # inc/dec r ((hl) handled above)
        if lo3 == 6:
            return 7, None                     # ld r,n
        if op == 0x10:
            return 8, 13                       # djnz
        if op in (0x20, 0x28, 0x30, 0x38):
            return 7, 12                       # jr cc
    if op >= 0xC0:
        if lo3 == 0:
            return 5, 11                       # ret cc
        if lo3 == 1:
            return 10, None                    # pop
        if lo3 == 2:
            return 10, 10                      # jp cc
        if lo3 == 4:
            return 10, 17                      # call cc
        if lo3 == 5:
            return 11, None                    # push
        if lo3 == 6:
            return 7, None                     # alu n
        if lo3 == 7:
            return 11, None                    # rst
    raise KeyError(f"no T-state entry for opcode {op:02X}")


def _len_main(op):
    if op in (0xCB, 0xDD, 0xED, 0xFD):
        raise ValueError
    if op < 0x40:
        lo3 = op & 7
        if op in (0x01, 0x11, 0x21, 0x31, 0x22, 0x2A, 0x32, 0x3A):
            return 3
        if lo3 == 6 or op in (0x10, 0x18, 0x20, 0x28, 0x30, 0x38):
            return 2
        return 1
    if op < 0xC0:
        return 1
    lo3 = op & 7
    if lo3 in (2, 4) or op in (0xC3, 0xCD):
        return 3
    if lo3 == 6 or op in (0xD3, 0xDB):
        return 2
    return 1


def tstates(mem, pc, newpc):
    op = mem[pc]
    if op == 0xCB:
        o2 = mem[(pc + 1) & 0xFFFF]
        if (o2 & 7) == 6:
            return 12 if 0x40 <= o2 <= 0x7F else 15
        return 8
    if op == 0xED:
        o2 = mem[(pc + 1) & 0xFFFF]
        if o2 in (0xB0, 0xB8, 0xB1, 0xB9, 0xB2, 0xBA, 0xB3, 0xBB):
            return 21 if newpc == pc else 16
        if o2 in (0xA0, 0xA8, 0xA1, 0xA9, 0xA2, 0xAA, 0xA3, 0xAB):
            return 16
        if (o2 & 0xC7) == 0x43 or (o2 & 0xC7) == 0x4B:
            return 20
        if (o2 & 0xC7) in (0x42, 0x4A):
            return 15
        if o2 in (0x44,):
            return 8
        if o2 in (0x45, 0x4D):
            return 14
        if o2 in (0x67, 0x6F):
            return 18
        if o2 in (0x47, 0x4F, 0x57, 0x5F):
            return 9
        if (o2 & 0xC7) in (0x40, 0x41):
            return 12
        if o2 in (0x46, 0x56, 0x5E):
            return 8
        raise KeyError(f"no T-state entry for ED {o2:02X}")
    if op in (0xDD, 0xFD):
        o2 = mem[(pc + 1) & 0xFFFF]
        if o2 == 0xCB:
            o4 = mem[(pc + 3) & 0xFFFF]
            return 20 if 0x40 <= o4 <= 0x7F else 23
        special = {0x21: 14, 0x22: 20, 0x2A: 20, 0x23: 10, 0x2B: 10, 0xE5: 15,
                   0xE1: 14, 0xE3: 23, 0xE9: 8, 0xF9: 10, 0x34: 23, 0x35: 23,
                   0x36: 19, 0x09: 15, 0x19: 15, 0x29: 15, 0x39: 15}
        if o2 in special:
            return special[o2]
        uses_mem = False
        if 0x40 <= o2 <= 0x7F and o2 != 0x76:
            uses_mem = (o2 & 7) == 6 or ((o2 >> 3) & 7) == 6
        elif 0x80 <= o2 <= 0xBF:
            uses_mem = (o2 & 7) == 6
        if uses_mem:
            return 19
        base, taken = _main_t(o2)
        return 4 + base
    base, taken = _main_t(op)
    if taken is None:
        return base
    fall = (pc + _len_main(op)) & 0xFFFF
    return base if newpc == fall else taken


# --------------------------------------------------------------------------
def build(root, out):
    rom, sym = out + ".rom", out + ".sym"
    subprocess.run(["pasmo", "--bin", os.path.join("basic", "main.asm"), rom, sym],
                   check=True, capture_output=True, cwd=root)
    return rom, sym


def instrument(m):
    """Count T-states and the lowest SP over every step."""
    st = {"t": 0, "lo": 0x10000}
    cpu = m.cpu
    step = cpu.step
    mem = m.mem

    def tracked():
        pc = cpu.pc
        step()
        st["t"] += tstates(mem, pc, cpu.pc)
        if cpu.sp < st["lo"]:
            st["lo"] = cpu.sp
    cpu.step = tracked
    return st


def setup(root):
    tmp = tempfile.mkdtemp(prefix="evalslope-")
    rom, sym = build(root, os.path.join(tmp, "zb"))
    m = Machine(rom, sym, rom_base=RELOC_BASE)
    s = m.sym
    m.poke_w(s["PRGEND"], 0x9000)
    m.poke(0x9000, b"\x00\x00")
    m.poke_w(s["ARYTAB"], 0x9002)
    m.poke(0x9002, b"\x00\x00")
    m.poke_w(s["POOLSIZE"], 4096)
    m.call("heap_reset")
    m.poke_w(s["CTLLIM"], 0x9100)          # far below: no guard refuses
    return m


def run_expr(m, st, text):
    s = m.sym
    m.poke(SRC, text.encode("ascii") + b"\x00")
    m.mem[TOKBUF:TOKBUF + 256] = b"\x00" * 256
    m.call("tokenise", hl=SRC, de=TOKBUF)
    m.poke(s["FPERR"], 0)
    m.poke(s["ERRMARK"], 0)
    m.poke_w(s["TEMPPT"], s["TEMPPOOL"])
    st["t"] = 0
    st["lo"] = 0x10000
    cpu = m.call("eval", hl=TOKBUF)
    # Machine.call starts at SP $F380 and pushes its sentinel: eval's entry SP
    # is $F37E, and `depth` is how far below THAT the evaluation reached.
    depth = 0xF37E - st["lo"]
    end = cpu.hl - TOKBUF
    return cpu.de & 0xFFFF, depth, st["t"], m.mem[s["FPERR"]], end


# (label, text, expected DE) -- the T-state rows: one construct each
TROWS = [
    ("factor: digit",            "1",              1),
    ("factor: byte const",       "100",            100),
    ("factor: word const",       "1000",           1000),
    ("factor: single const",     "1.5",            None),
    ("factor: variable",         "A",              0),
    ("paren",                    "(1)",            1),
    ("paren x2",                 "((1))",          1),
    ("+",                        "1+2",            3),
    ("-",                        "5-2",            3),
    ("*",                        "2*3",            6),
    ("/",                        "6/3",            2),
    ("MOD",                      "7MOD3",          1),
    ("\\",                       "7\\2",           3),
    ("AND",                      "6AND3",          2),
    ("OR",                       "6OR3",           7),
    ("XOR",                      "6XOR3",          5),
    ("EQV",                      "6EQV3",          0xFFFA),
    ("IMP",                      "6IMP3",          0xFFFB),
    ("unary minus",              "-2",             0xFFFE),
    ("NOT",                      "NOT0",           0xFFFF),
    ("relational =",             "1=1",            0xFFFF),
    ("relational <",             "1<2",            0xFFFF),
    ("relational <=",            "2<=1",           0),
    ("relational <>",            "1<>2",           0xFFFF),
    ("function ABS",             "ABS(-3)",        3),
    ("function PEEK",            "PEEK(0)",        None),
    ("mixed 1+2*3-4",            "1+2*3-4",        3),
    ("mixed 2*3+4*5",            "2*3+4*5",        26),
    ("mixed 1<2 AND 3>2",        "1<2AND3>2",      0xFFFF),
    ("mixed NOT 1=2 OR 0",       "NOT1=2OR0",      0xFFFF),
    ("mixed 1+(2*(3+4))",        "1+(2*(3+4))",    15),
]


def nest(kind, n):
    """A construct nested n deep, each level PENDING while the next is parsed."""
    if kind == "(":
        return "(" * n + "1" + ")" * n
    if kind == "MOD":                    # 90MOD(91MOD(...(100))): never a 0 divisor
        return "".join(f"{90 + i}MOD(" for i in range(n)) + "100" + ")" * n
    if kind in ("+", "-", "*", "/", "^", "\\", "AND", "OR", "XOR", "EQV", "IMP"):
        return ("1" + kind + "(") * n + "1" + ")" * n
    if kind in ("=", "<"):
        return ("1" + kind + "(") * n + "1" + ")" * n
    if kind == "neg":
        return "-(" * n + "1" + ")" * n
    if kind == "NOT":
        return "NOT" * n + "0"
    if kind == "NOT(":
        return "NOT(" * n + "0" + ")" * n
    if kind == "ABS":
        return "ABS(" * n + "1" + ")" * n
    raise KeyError(kind)


# OUTCOME rows: no expected value written here -- run the probe on both builds and
# diff the `diff` lines (DE, FACTYP, FPERR, ERRMARK, where the cursor stopped).
# Precedence and associativity at every level boundary, coercion, the string
# comparison and its continuation, the deferred errors, and malformed tails.
DIFF = [
    "1+2*3", "2*3+1", "7-2-1", "8/2/2", "-2*3", "2*-3",
    "--2", "-+2", "+-2", "7MOD4MOD3", "7\\2\\2", "7\\2MOD3", "7MOD3\\2",
    "1+7MOD3", "7MOD3+1", "2*7MOD4", "7MOD4*2", "1+7\\2", "7\\2*2",
    "1<2<3", "3<2<1", "1=1=1", "1=0=0", "1+1=2", "2=1+1", "1<2=-1", "1<>2<>3",
    "1>=1", "1=<1", "1=>1", "1><2", "1<<2", "1==1",
    "NOT1", "NOTNOT1", "NOT1=2", "NOT1AND0", "NOT0OR1", "1ANDNOT0", "NOT-1",
    "NOT1+1", "NOT(1)+1", "1=NOT0", "1+NOT0", "-NOT0",
    "6AND3OR8", "8OR6AND3", "6XOR3AND1", "1OR2XOR3", "5EQV3XOR1", "5XOR3EQV1",
    "1IMP0OR1", "1OR0IMP0", "5EQV3IMP0", "0IMP5EQV3", "1AND2=2", "2=2AND1",
    "1<2AND3<4", "1<2OR3<4AND0", "NOT1<2OR1",
    "1.5+1", "1.5*2", "3/2", "2.5AND3", "3AND2.5", "40000=40000!", "1.5<1.4",
    "1.5=1.5", "NOT1.5", "-1.5", "32767+1", "-32768-1", "32767*2", "-32768\\-1",
    "7MOD0", "1/0", "1\\0", "65536AND1", "1AND65536", "NOT65536",
    "(1+2)*3", "((((1))))", "(1", "1+", "1+)", "()", "1 + 2 * 3", " ( 1 + 2 ) ",
    "1AND", "NOT", "1<", "1<>", "*2", "1**2", "1+*2",
    'A', 'A+1', 'A=0', 'NOTA',
    '"A"="A"', '"A"<"B"', '"A"="B"', '"A"="A"=-1', '"A"="B"=0',
    '"A"="B"-1', '"A"="B"*2', '"A"="B"MOD2', '"A"="B"AND1', '"A"="A"OR0',
    'NOT"A"="B"', '("A"="A")', '1AND"A"="A"', '"A"="A"AND"B"="B"',
    '1="A"', '1<"A"+"B"', '1=+"A"', '"A"', '"A"+"B"="AB"', '1=1="A"',
    '1+"A"', '"A"=1', 'NOT"A"', '-"A"',
    'ABS(-3)+1', 'ABS(-3)*2', '-ABS(3)', 'PEEK(0)+1', 'LEN("AB")+1',
    'LEN("AB")=2', 'VAL("12")*2', 'ASC("A")=65', 'INSTR("ABC","C")+1',
]

SLOPES = ["(", "+", "-", "*", "/", "MOD", "\\", "AND", "OR", "XOR", "EQV",
          "IMP", "=", "<", "neg", "NOT", "NOT(", "ABS"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    m = setup(a.root)
    st = instrument(m)
    where = "this tree" if os.path.abspath(a.root) == ROOT else "--root (another tree)"
    print(f"# evalslope_probe {a.label}: basic/main.asm from {where}")
    print("# --- T-states and depth per construct (whole `call eval`) ---")
    bad = 0
    for label, text, want in TROWS:
        de, depth, t, fperr, end = run_expr(m, st, text)
        ok = (want is None or de == want) and fperr == 0
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {label:24s} {text!r:16s} DE={de:04X} "
              f"T={t:6d} depth={depth:4d} FPERR={fperr} end={end}")
    print("# --- slope: bytes per extra PENDING level (depth(N+1) - depth(N)) ---")
    for k in SLOPES:
        ds = []
        for n in (4, 5, 6):
            de, depth, t, fperr, end = run_expr(m, st, nest(k, n))
            ds.append((depth, t, de, fperr))
        sl = ds[1][0] - ds[0][0]
        sl2 = ds[2][0] - ds[1][0]
        tsl = ds[1][1] - ds[0][1]
        flag = "" if sl == sl2 and all(f == 0 for *_, f in ds) else "  ⚠️ irregular/FPERR"
        print(f"slope {k:5s} {sl:3d} B/level  ({sl2:3d})  T/level={tsl:6d}  "
              f"depth@4={ds[0][0]:4d}  DE@4={ds[0][2]:04X}{flag}")
    print("# --- outcomes (diff these lines between builds) ---")
    for text in DIFF:
        de, depth, t, fperr, end = run_expr(m, st, text)
        print(f"diff {text!r:28s} DE={de:04X} FACTYP={m.mem[m.sym['FACTYP']]} "
              f"FPERR={fperr} ERRMARK={m.mem[m.sym['ERRMARK']]:02X} end={end}")
    print(f"# {bad} BAD row(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
