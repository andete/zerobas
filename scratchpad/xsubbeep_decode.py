#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode probes/bios/spec/xsubbeep.asm's capture (D-MSX2SPEC, docs/msx2/sub/BEEP.md).

    python3 scratchpad/xsubbeep_decode.py scratchpad/AE_xsubbeep_msx2.out [--trace]

Per machine and case: the registers, IFF, MODE, block 2 reg 10, port C, PSG R0-R15 at return and after the tail,
and the PSG trace (R14 markers $5A / $A5 / $3C = call / return / tail end), times in ms from the call marker.
--trace prints every write; otherwise the trace is summarised as tone segments (R0/R1 period, R8 volume).
"""
import re
import sys

KIND = {0: "sub DI", 1: "main $00C0 DI", 2: "sub EI"}
SLOT, BASE = 0x380, 0x8001


def caps(path):
    row = None
    for line in open(path):
        m = re.match(r"===== \S+ (\w+): (\S+) vs (\S+) =====", line)
        if m:
            row = (m.group(2), m.group(3))
        m = re.match(r"\s+CAP (ref |ours): ([0-9a-f]+)", line)
        if m and row:
            yield row[0] if m.group(1) == "ref " else row[1], bytes.fromhex(m.group(2))


def decode(name, c, trace):
    c = c + bytes(0x3F00 - len(c))
    if c[0] != 0xA5:
        print(f"## {name}: NOT FINISHED ({c[0]:02X})"); return
    n = c[1]
    print(f"## {name}: {n} cases; block 2 regs 0-12 at INIT: {' '.join(f'{b:X}' for b in c[2:15])}")
    for k in range(n):
        r = c[0xFF + k * SLOT: 0xFF + (k + 1) * SLOT]
        if r[51] != 0xEE:
            print(f"  case {k}: SENTINEL MISSING"); continue
        ix, iy = r[10] | r[11] << 8, r[12] | r[13] << 8
        print(f"  case {k}: {KIND[r[0]]}, V={'none' if r[1] == 0xFF else f'{r[1]:X}'}: A={r[2]:02X} F={r[3]:02X} "
              f"BC={r[5]:02X}{r[4]:02X} DE={r[7]:02X}{r[6]:02X} HL={r[9]:02X}{r[8]:02X} IX={ix:04X} IY={iy:04X} "
              f"SP={r[54] | r[55] << 8:04X} IFF={r[14]}/{r[15]} M={r[56]:02X} MODEbefore={r[57]:X} MODE={r[16]:X} reg10={r[17]:X} portC={r[18]:02X}")
        print(f"     PSG at return : {r[19:35].hex(' ')}")
        print(f"     PSG after tail: {r[35:51].hex(' ')}")
        end = r[52] | r[53] << 8
        start = BASE + 0xFF + k * SLOT + 64     # the record's +64 (record +0 at CAP + $FF)
        nent = (end - start) // 5
        if nent < 0 or nent * 5 + 64 > SLOT:
            print(f"     TRACE OVERFLOW / bad end {end:04X} (start {start:04X})"); continue
        ents = [r[64 + 5 * i: 69 + 5 * i] for i in range(nent)]
        ents = [(e[0], e[1], e[2] | e[3] << 8 | e[4] << 16) for e in ents]
        t0 = next((t for g, v, t in ents if g == 14 and v == 0x5A), ents[0][2] if ents else 0)
        ms = lambda t: ((t - t0) & 0xFFFFFF) / 1000.0
        tret = next((ms(t) for g, v, t in ents if g == 14 and v == 0xA5), None)
        print(f"     trace: {nent} writes; return at {tret} ms")
        if trace:
            for g, v, t in ents:
                print(f"       {ms(t):9.3f} R{g:<2} := {v:02X}")
        else:
            # compact: every write except R14 markers / R15, grouped
            line = []
            for g, v, t in ents:
                if g in (14,) and v in (0x5A, 0xA5, 0x3C):
                    line.append(f"[{ {0x5A: 'call', 0xA5: 'ret', 0x3C: 'end'}[v]}@{ms(t):.1f}]"); continue
                if g == 15:
                    continue
                line.append(f"R{g}={v:02X}@{ms(t):.1f}")
            print("       " + " ".join(line))


def main():
    trace = "--trace" in sys.argv
    for name, c in caps(sys.argv[1]):
        decode(name, c, trace)



def compare(path):
    """--cmp: per case, are the three references' write sequences (register, byte) equal; segment lengths."""
    seqs = {}
    for name, c in caps(path):
        c = c + bytes(0x3F00 - len(c))
        out = []
        for k in range(c[1]):
            r = c[0xFF + k * SLOT: 0xFF + (k + 1) * SLOT]
            end = r[52] | r[53] << 8
            n = (end - (BASE + 0xFF + k * SLOT + 64)) // 5
            ents = [(r[64 + 5 * i], r[65 + 5 * i], r[66 + 5 * i] | r[67 + 5 * i] << 8 | r[68 + 5 * i] << 16)
                    for i in range(n)]
            t0 = ents[0][2]
            tr = next(t for g, v, t in ents if g == 14 and v == 0xA5)
            out.append(([(g, v) for g, v, t in ents if g != 14], ((tr - t0) & 0xFFFFFF) / 1000.0,
                        ents[1][2] - t0 if len(ents) > 1 else 0))
        seqs[name] = out
    names = list(seqs)
    for k in range(len(seqs[names[0]])):
        line = f"case {k:2}:"
        for n in names:
            s, tret, tfirst = seqs[n][k]
            same = "=" if s == seqs[names[0]][k][0] else "DIFF"
            line += f" | {n[:14]} {len(s)}w ret {tret:.1f}ms {same}"
        print(line)


if "--cmp" in sys.argv:
    compare(sys.argv[1])
    sys.exit(0)


main()
