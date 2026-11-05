# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-TRAPCOST round 3 (2026-11-05) -- the two main-ROM answers that
used to be sub-ROM round trips.

ary_resolve_fast (basic/files.asm): a ONE-subscript RESOLVE of an array that
exists is answered in main; everything else must reach ary_engine_call (trapped
here, so a fall-through is SEEN, never executed). The descriptor chain is built
by hand in RAM in the tenant's own layout ([name0][name1][type][ndim][stride:2]
[bounds][data], sub/arrays.asm ary_find / ary_alloc) and the expected address is
the tenant's formula for ndim 1 (aryr_loop_done: data + subscript * elsize,
elsize 3 for a string, else the type). Cases: every type at bound 0 / mid /
bound, a shared name0 under another type and name1, and the six fall-throughs
(op 3, two subscripts, negative, over the bound, a 2-D descriptor, not found).

var_alloc_or_find (basic/varfind.asm): an existing scalar is returned from the
main-ROM walk with no tenant call; a miss reaches vaof_engine (trapped) with the
key in BC and the type in A, as the tenant's find-or-insert expects.
Clean-room: our own routines and layouts only.
"""
import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

BASIC_BASE = 0x2781
ROM, SYM = tp("zb_ary_fast.rom"), tp("zb_ary_fast.sym")
CHAIN = 0xA000
IDXW = 0xC100       # the parsed subscript word(s), as apsub_close leaves them


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym
    fails = 0

    def check(label, ok, detail=""):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}{': ' + detail if detail else ''}")

    # --- the array chain ---------------------------------------------------
    arrays = [(b"H", 0, 8, [9]), (b"H", 0, 2, [5]), (b"S", ord("X"), 1, [4]),
              (b"H", ord("B"), 4, [20]), (b"M", 0, 8, [3, 2]), (b"Q", 0, 2, [0])]
    desc, addr = {}, CHAIN
    for n0, n1, ty, bounds in arrays:
        el = 3 if ty == 1 else ty
        count = 1
        for b in bounds:
            count *= b + 1
        size = 6 + 2 * len(bounds) + el * count
        hdr = bytes([n0[0], n1, ty, len(bounds)]) + size.to_bytes(2, "little")
        hdr += b"".join(b.to_bytes(2, "little") for b in bounds)
        m.poke(addr, hdr + bytes(el * count))
        desc[(n0[0], n1, ty)] = (addr, addr + 6 + 2 * len(bounds), el, bounds)
        addr += size
    m.poke(addr, b"\x00\x00")
    m.poke_w(s["ARYTAB"], CHAIN)

    slow = []
    m.trap("ary_engine_call", lambda mm: slow.append(mm.mem[s["ARY_OP"]]))

    def resolve(n0, n1, ty, subs, op=0):
        slow.clear()
        m.poke(s["ARY_OP"], op)
        m.poke(s["ARY_KEY"], bytes([n1, n0]))         # `ld bc,(ARY_KEY)`: C = name1
        m.poke(s["ARY_TYPE"], ty)
        m.poke(s["ARY_NIDX"], len(subs))
        for i, v in enumerate(subs):                   # subscript 0 at the HIGH end
            m.poke_w(IDXW - 2 * i, v & 0xFFFF)
        m.poke_w(s["ARY_IDXP"], IDXW)
        m.poke_w(s["ARY_ADDR"], 0x5A5A)
        m.poke(s["ARY_ERR"], 0x77)
        cpu = m.call("ary_resolve_fast")
        return cpu, bool(slow)

    bad = []
    hits = 0
    for (n0, n1, ty), (_, data, el, bounds) in desc.items():
        if len(bounds) != 1:
            continue
        for sub in sorted({0, bounds[0] // 2, bounds[0]}):
            cpu, fell = resolve(n0, n1, ty, [sub])
            got = m.mem[s["ARY_ADDR"]] | m.mem[s["ARY_ADDR"] + 1] << 8
            want = data + sub * el
            ok = (not fell and got == want and m.mem[s["ARY_ERR"]] == 0
                  and cpu.a == 0 and not carry(cpu) and cpu.f & 0x40)
            hits += 1
            if not ok:
                bad.append((chr(n0), n1, ty, sub, fell, hex(got), hex(want)))
    check("ary_resolve_fast: in-range 1-D reads answered in main", not bad,
          f"{hits} reads over 5 arrays (types 8/2/1/4/2, shared name0 H)"
          + ("" if not bad else " " + repr(bad[:3])))

    falls = [("op 3 (COPY_STR)", (ord("H"), 0, 8, [1]), 3),
             ("two subscripts", (ord("M"), 0, 8, [1, 1]), 0),
             ("negative", (ord("H"), 0, 8, [-1]), 0),
             ("over the bound", (ord("H"), 0, 2, [6]), 0),
             ("1 subscript on a 2-D array", (ord("M"), 0, 8, [1]), 0),
             ("not DIMmed (auto-DIM)", (ord("Z"), 0, 8, [1]), 0),
             ("name matches, type does not", (ord("S"), ord("X"), 2, [1]), 0)]
    for label, (n0, n1, ty, subs), op in falls:
        _, fell = resolve(n0, n1, ty, subs, op)
        check(f"ary_resolve_fast falls through: {label}", fell)

    # --- var_alloc_or_find ---------------------------------------------------
    base = 0xB000
    m.poke_w(s["PRGEND"], base - 2)
    m.poke(s["FN_FEND"], s["FN_PAREA"] & 0xFF)
    chain = [(ord("A"), 0, 2), (ord("A"), 0, 8), (ord("S"), ord("X"), 1), (ord("I"), 0, 4)]
    at, addr = {}, base
    for n0, n1, ty in chain:
        width = 3 + (3 if ty == 1 else ty)
        m.poke(addr, bytes([n0, n1, ty]) + bytes(width - 3))
        at[(n0, n1, ty)] = addr
        addr += width
    m.poke_w(s["ARYTAB"], addr)
    eng = []
    m.trap("vaof_engine", lambda mm: eng.append((mm.cpu.b, mm.cpu.c, mm.cpu.a)))
    bad = []
    for (n0, n1, ty), want in at.items():
        eng.clear()
        cpu = m.call("var_alloc_or_find", b=n0, c=n1, a=ty)
        if eng or not carry(cpu) or cpu.hl != want:
            bad.append((chr(n0), n1, ty, eng[:], hex(cpu.hl)))
    check("var_alloc_or_find: an existing scalar never reaches the tenant", not bad,
          f"{len(at)} entries" + ("" if not bad else " " + repr(bad)))
    eng.clear()
    m.call("var_alloc_or_find", b=ord("A"), c=0, a=4)
    check("var_alloc_or_find: a miss reaches vaof_engine with the key and type",
          eng == [(ord("A"), 0, 4)], repr(eng))

    print()
    print("ALL PASS -- the main-ROM array resolve and scalar find-or-insert front"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
