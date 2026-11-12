#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""test_kwidx -- D-KWIDX: detok_kw found through basic/kwidx.inc says exactly what the
kwtable walk it replaced said, for EVERY token byte.

The reference answer is computed here from the ASSEMBLED sub-ROM's own kwtable (the
same rule the walk had: the first entry with tlen == 1 carrying the token; nothing for
a byte no entry carries). detok_kw runs on the host Z80 over the sub-ROM's page 0, its
pchar trapped to collect what it prints. Every byte $00..$FF is asked: below $80 and
the unassigned tokens must print nothing and answer CF = 0.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from msxtest import _build_subrom  # noqa: E402
from z80 import Z80  # noqa: E402

SENTINEL = 0xFFF0


def main() -> int:
    sub, sym = _build_subrom()
    if not isinstance(sym, dict):
        sym = {k: v for k, v in sym}
    for need in ("detok_kw", "detok_kw2", "pchar", "kwtable", "kw_ord", "kw_ord2", "kw_bkt"):
        if need not in sym:
            print(f"FAIL  symbol {need} missing from the sub-ROM build -- nothing measured")
            return 1
    mem = bytearray(0x10000)
    mem[0:0x4000] = sub[0:0x4000]
    # the reference: the walk's rule over the assembled table
    ents, p = [], sym["kwtable"]
    while mem[p]:
        kl = mem[p]
        tl = mem[p + 1 + kl]
        ents.append((bytes(mem[p + 1:p + 1 + kl]).decode("latin1"), list(mem[p + 2 + kl:p + 2 + kl + tl])))
        p += 2 + kl + tl
    want = {}
    for name, toks in ents:
        if len(toks) == 1 and toks[0] not in want:
            want[toks[0]] = name
    fails = checked = 0
    for t in range(256):
        cpu = Z80(mem)
        cpu.sp = 0xF000
        cpu.push(SENTINEL)
        cpu.pc = sym["detok_kw"]
        cpu.a = t
        out = []
        for _ in range(20000):
            if cpu.pc == SENTINEL:
                break
            if cpu.pc == sym["pchar"]:
                out.append(chr(cpu.a))
                cpu.pc = cpu.pop()
                continue
            cpu.step()
        else:
            print(f"FAIL  token ${t:02X}: detok_kw did not return")
            fails += 1
            continue
        got, cf = "".join(out), cpu.f & 1
        exp = want.get(t, "") if t >= 0x80 else ""
        checked += 1
        if got != exp or cf != (1 if exp else 0):
            print(f"FAIL  token ${t:02X}: printed {got!r} CF={cf}, the walk's answer {exp!r} CF={1 if exp else 0}")
            fails += 1
    print(f"{'PASS' if not fails else 'FAIL'}  detok_kw over kwidx.inc: {checked} token bytes, "
          f"{len(want)} keywords, {fails} mismatch(es)")
    # D-KWIDX2: detok_kw2 (A = first byte, C = second) against the walk's rule -- the first
    # tlen == 2 entry with both bytes; nothing printed when none. Every $FF xx, and every
    # first byte any two-byte entry uses, with every second byte.
    want2 = {}
    for name, toks in ents:
        if len(toks) == 2 and (toks[0], toks[1]) not in want2:
            want2[(toks[0], toks[1])] = name
    firsts = sorted({k[0] for k in want2} | {0xFF})
    fails2 = checked2 = 0
    for f in firsts:
        for c in range(256):
            cpu = Z80(mem)
            cpu.sp = 0xF000
            cpu.push(SENTINEL)
            cpu.pc = sym["detok_kw2"]
            cpu.a, cpu.c = f, c
            out = []
            for _ in range(40000):
                if cpu.pc == SENTINEL:
                    break
                if cpu.pc == sym["pchar"]:
                    out.append(chr(cpu.a))
                    cpu.pc = cpu.pop()
                    continue
                cpu.step()
            else:
                print(f"FAIL  token ${f:02X} ${c:02X}: detok_kw2 did not return")
                fails2 += 1
                continue
            got, exp = "".join(out), want2.get((f, c), "")
            checked2 += 1
            if got != exp:
                print(f"FAIL  token ${f:02X} ${c:02X}: printed {got!r}, the walk's answer {exp!r}")
                fails2 += 1
    print(f"{'PASS' if not fails2 else 'FAIL'}  detok_kw2 over kw_ord2: {checked2} token pairs, "
          f"{len(want2)} two-byte keywords, {fails2} mismatch(es)")
    return 1 if fails or fails2 else 0


if __name__ == "__main__":
    raise SystemExit(main())
