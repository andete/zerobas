#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHPUT.md's ROUND-2 evidence table, from a run of probes/bios/spec/xchput2.asm.

    python3 -u probes/bios/biosl_run.py probes/bios/spec/xchput2.asm --row nodisk > RUN.out
    python3 probes/bios/spec/xchput2_table.py RUN.out > scratchpad/XCH2_table.out

Decodes the six groups the rung's header documents, the VG-8020 (ref) beside zerobas (zb), one
line per case, ` DIFF` where they differ. Refuses a block that is not complete on both machines
(CAP+1 = $A5).
"""
import re
import sys

CAPLEN = 0x251C


def block(text, who):
    m = re.search(rf"CAP {who}\s*:\s*([0-9a-fA-F]+)", text)
    if not m:
        sys.exit(f"FAIL: no `CAP {who}` dump in the run")
    b = bytes.fromhex(m.group(1))
    b = b + bytes(CAPLEN - len(b))
    if b[1] != 0xA5:
        sys.exit(f"FAIL: the {who} block is not complete (CAP+1 = ${b[1]:02X}, not $A5)")
    return b


def ch(c):
    return chr(c) if 33 <= c < 127 else ("_" if c == 32 else f"${c:02X}")


def row(cells):
    return "".join(chr(c) if 32 <= c < 127 else "?" for c in cells).replace(" ", "_")


def main():
    t = open(sys.argv[1]).read()
    r, z = block(t, "ref"), block(t, "ours")
    print("XCHPUT2 (probes/bios/spec/xchput2.asm): CHPUT round 2, the VG-8020 (ref) against zerobas (zb), called")
    print("directly, SCREEN 0 width 40. Read the rung's header for each group's setup. Positions 0-based (row, col);")
    print("CSRX / CSRY 1-based. '_' = a space, $nn = a non-printable cell. Raw run: scratchpad/XCH2_run1.out.")
    print(f"INIT: LINLEN ref {r[0]} zb {z[0]}; CRTCNT ref {r[2]} zb {z[2]}; CNSDFG ref {r[3]} zb {z[3]}")

    def recs(off, size, n):
        for i in range(n):
            yield i, r[4 + off + size * i: 4 + off + size * (i + 1)], z[4 + off + size * i: 4 + off + size * (i + 1)]

    print("\n== G1 TAB: row 10 = 40 'o', cursor at (10, c), TAB -> CSRX CSRY, row 10 ==")
    for i, a, b in recs(0, 42, 40):
        d = " DIFF" if a != b else ""
        print(f"G1.{i:02} c {i:2} | ref {a[0]:2} {a[1]:2} {row(a[2:])} | zb {b[0]:2} {b[1]:2}{' ' + row(b[2:]) if d else ''}{d}")

    print("\n== G2 EDGES: key line, corner (row, col), byte -> CSRX CSRY | first cell of rows 0..23 | LINTTB ==")
    corners = ((0, 0), (0, 39), (23, 0), (23, 39))
    bytes_ = (8, 29, 127, 28, 30, 31, 10, 13, 9, ord("A"))
    for i, a, b in recs(1680, 50, 80):
        kl, rest = divmod(i, 40)
        cn, bi = divmod(rest, 10)
        lab = f"key {'on ' if kl else 'off'} ({corners[cn][0]:2},{corners[cn][1]:2}) {ch(bytes_[bi]):>3}"
        d = " DIFF" if a != b else ""
        print(f"G2.{i:02} {lab} | ref {a[0]:2} {a[1]:2} {row(a[2:26])} {a[26:50].hex()}")
        if d:
            print(f"      {' ' * len(lab)} | zb  {b[0]:2} {b[1]:2} {row(b[2:26])} {b[26:50].hex()} DIFF")

    print("\n== G3 PENDING: kind, c, then 'A' -> CSRX CSRY, cells (10, 19..21) [setup: P Q R, cursor on Q] ==")
    for i, a, b in recs(5680, 5, 64):
        kind, c = ("ESC" if i < 32 else "1"), i % 32
        d = " DIFF" if a != b else ""
        print(f"G3.{i:02} {kind:3} {c:2} A | ref {a[0]:2} {a[1]:2} {ch(a[2])} {ch(a[3])} {ch(a[4])}"
              f" | zb {b[0]:2} {b[1]:2} {ch(b[2])} {ch(b[3])} {ch(b[4])}{d}")

    print("\n== G4 EDITS: rows filled 'a'+r at cols 0..38, cursor (10, 20), op -> CSRX CSRY | rows' col 0 | col 38 | (10,19..21) ==")
    ops = ("ESC L", "ESC M", "ESC J", "ESC K", "ESC E", "ESC j", "ESC l", "12")
    for i, a, b in recs(6000, 53, 8):
        d = " DIFF" if a != b else ""
        c0 = row(a[2:50:2])
        c38 = row(a[3:50:2])
        print(f"G4.{i} {ops[i]:5} | ref {a[0]:2} {a[1]:2} col0 {c0} col38 {c38} cells {row(a[50:53])}")
        if d:
            print(f"            | zb  {b[0]:2} {b[1]:2} col0 {row(b[2:50:2])} col38 {row(b[3:50:2])} cells {row(b[50:53])} DIFF")

    print("\n== G5 ESC Y: v as the ROW parameter (column 32+5), then as the COLUMN parameter (row 32+5) -> CSRX CSRY ==")
    for i, a, b in recs(6424, 2, 512):
        kind, v = ("row" if i < 256 else "col"), i % 256
        d = " DIFF" if a != b else ""
        print(f"G5.{i:03} {kind} v {v:3} ${v:02X} | ref {a[0]:2} {a[1]:2} | zb {b[0]:2} {b[1]:2}{d}")

    print("\n== G6 ESC x / ESC y v (the state CARRIES case to case) -> CSRX CSRY ($FCA9) ($FCAA) ==")
    for i, a, b in recs(7448, 4, 512):
        kind, v = ("x" if i < 256 else "y"), i % 256
        d = " DIFF" if a != b else ""
        print(f"G6.{i:03} ESC {kind} v {v:3} ${v:02X} | ref {a[0]:2} {a[1]:2} ${a[2]:02X} ${a[3]:02X}"
              f" | zb {b[0]:2} {b[1]:2} ${b[2]:02X} ${b[3]:02X}{d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
