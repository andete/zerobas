#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode scratchpad/AE_xsubdln_msx2.out (probes/bios/spec/xsubdln.asm): sub-ROM DELLNO ($0121) / INSLNO ($0125).

    python3 scratchpad/xsubdln_decode.py [scratchpad/AE_xsubdln_msx2.out]
    python3 scratchpad/xsubdln_decode.py --r2 scratchpad/AE_xsubdln2_msx2.out    (round 2, probes/bios/spec/xsubdln2.asm)
    python3 scratchpad/xsubdln_decode.py --r3 scratchpad/AE_xsubdln3_msx2.out    (round 3, out-of-range L)
    python3 scratchpad/xsubdln_decode.py --r4 scratchpad/AE_xsubdln4_msx2.out    (round 4, goldfish pass 1)

Per case and machine: the registers, IFF, the cells, LINTTB's changes (entry i was $C0 + i, $FBCA $5D), and the name
table as a row map: per row the source row whose pattern it holds whole (`5` = row 5's cells), `_` = all spaces,
`k` = something else (printed in full below the map: spaces / first / last / matches).
"""
import re
import sys

ORDER = [("msx2jp", "ref"), ("msx2eu", "ref"), ("msx2p", "ref"), ("msx2jp", "ours"), ("msx2eu", "ours"),
         ("msx2p", "ours")]
LABEL = ["F900", "8250", "WSX", "cb2jp", "cb2eu", "cb2+"]
NAMES = ["base w40 H7 L5", "L9", "H20", "A3", "cursor (3,18)", "L1", "L24", "L24 key line on", "L10 key line on",
         "EI", "w80 L5", "SCREEN 1 L5", "w37 L5", "LINTTB[5]=0 L5", "LINTTB[4]=0 L5", "CRTCNT 20 L5", "L23"]
NAMES2 = ["$FBCA 3", "$FBCA 4", "$FBCA 5", "$FBCA 6", "$FBCA 24", "$FBCA 0", "L24 $FBCA 30", "width 37 L5",
          "width 30 L5", "SCREEN 1 LINL32 29 L5"]
NAMES3 = ["L23 key line on", "L25", "L21 CRTCNT 20", "L22 CRTCNT 20", "L26", "L0"]
NAMES4 = ["L5 BC 2468 DE 9ABC", "L24 BC 2468 DE 9ABC", "L25 BC 2468 DE 9ABC", "L128", "L255", "CNSDFG 1 L5",
          "LINTTB[22]=0 L5", "LINTTB[23]=0 L5", "LINTTB[23]=0 L24",
          "w40 LINLEN 37 LINL40 33 LINL32 29 NAMBAS 2000 TXTNAM 3000",
          "SCREEN 1 LINLEN 29 LINL40 33 LINL32 25 NAMBAS 3000 TXTNAM 2400",
          "w80 LINLEN 72 LINL40 75 LINL32 29 NAMBAS 2000 TXTNAM 3000", "80 columns LINLEN 40", "40 columns LINLEN 60",
          "40 columns LINLEN 29", "SCREEN 1 LINLEN 40"]
RECLEN = 192
R2 = False
R4 = False


def caps(path):
    row, out = None, {}
    for line in open(path):
        m = re.match(r"===== \S+ (\w+):", line)
        if m:
            row = m.group(1)
        m = re.match(r"\s+CAP (ref |ours): ([0-9a-f]+)", line)
        if m and row:
            out[(row, m.group(1).strip())] = bytes.fromhex(m.group(2)) + bytes(0x1A00)
    return out


def sig(r):
    a, f, iff = r[1], r[2], r[3]
    w = lambda o: r[o] | r[o + 1] << 8
    bc, de, hl, ix, iy = w(4), w(6), w(8), w(10), w(12)
    cells = r[16:24]
    lt = r[24:49]
    rl = r[164]
    ltd = " ".join(f"{i}:{v:02X}" for i, v in enumerate(lt[:24]) if v != 0xC0 + i)
    if R2:
        ltd += f" | FBCA {lt[24]:02X} FBCB {r[49]:02X}"
    elif lt[24] != 0x5D:
        ltd += f" FBCA:{lt[24]:02X}"
    rows, odd = [], []
    for k in range(27):
        sp, fi, la, ma = r[56 + 4 * k: 60 + 4 * k]
        if sp == rl:
            rows.append("_")
        elif ma == rl and fi >= 0x80:
            rows.append(str((fi & 0x7F) >> 2))
        else:
            rows.append("k")
            odd.append(f"row {k}: spaces {sp} first {fi:02X} last {la:02X} matches {ma}")
    if R2:
        for k, o in ((4, 168), (5, 208), (23, 248)):
            odd.append(f"row {k} in full: {r[o:o + 40].hex()}")
    if R4:
        w2 = lambda o: r[o] | r[o + 1] << 8
        odd.append(f"rows filled at {w2(165):04X}; the table CHGMOD set up ({w2(296):04X}): sum {w2(288):04X} -> "
                   f"{w2(290):04X}; after the call NAMBAS {w2(292):04X} TXTNAM {w2(294):04X} LINL40 {cells[6]} "
                   f"LINL32 {cells[7]}")
    return (f"A {a:02X} F {f:02X} BC {bc:04X} DE {de:04X} HL {hl:04X} IX {ix:04X} IY {iy:04X} IFF {iff}/{r[14]} | "
            f"CSRY {cells[0]} CSRX {cells[1]} CNSDFG {cells[2]:02X} SCRMOD {cells[3]} LINLEN {cells[4]} CRTCNT "
            f"{cells[5]} | LINTTB [{ltd}]\n      rows: {' '.join(rows)}"
            + "".join(f"\n      {o}" for o in odd))


def main():
    global RECLEN, R2
    args = sys.argv[1:]
    names, n = NAMES, 17
    global R4
    if args and args[0] in ("--r2", "--r3", "--r4"):
        R2, RECLEN = True, 320
        R4 = args[0] == "--r4"
        names, n = {"--r2": (NAMES2, 10), "--r3": (NAMES3, 6), "--r4": (NAMES4, 16)}[args[0]]
        args = args[1:]
    cs = caps(args[0] if args else "scratchpad/AE_xsubdln_msx2.out")
    for k, lab in zip(ORDER, LABEL):
        print(f"{lab:6} done {cs[k][0]:02X} cases {cs[k][1]}")
    for i in range(2 * n):
        ent = "DELLNO $0121" if i < n else "INSLNO $0125"
        sigs = []
        for k in ORDER:
            r = cs[k][2 + RECLEN * i: 2 + RECLEN * (i + 1)]
            sigs.append(sig(r) if r[RECLEN - 1] == 0x5E and r[0] == i else "missing")
        print(f"\n== case {i}: {ent} {names[i % n]}")
        groups = {}
        for lab, s in zip(LABEL, sigs):
            groups.setdefault(s, []).append(lab)
        for s, labs in groups.items():
            print(f"  {','.join(labs)}: {s}")


if __name__ == "__main__":
    main()
