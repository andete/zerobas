#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHPUT.md's evidence table, from a run of the XCHPUT matrix rung.

    python3 -u probes/bios/biosl_run.py probes/bios/spec/xchput.asm --row nodisk > RUN.out
    python3 probes/bios/spec/xchput_table.py RUN.out > scratchpad/XCH_table.out

Reads the harness's `CAP ref :` / `CAP ours:` hex dumps (the harness trims trailing zero bytes;
they are restored here) and prints one line per case: CSRX, CSRY, the A CHPUT returned, and the
three cells around the cursor, for the VG-8020 and for zerobas. Refuses a run whose block is
not complete on both machines (CAP+1 = $A5), so a short or broken run never becomes a table.
"""
import re
import sys

CAPLEN = 0x1202
MODES = ("CHPUT v", "CHPUT ESC, then v", "CHPUT 1 (the graphic prefix), then v")


def block(text, who):
    m = re.search(rf"CAP {who}\s*:\s*([0-9a-fA-F]+)", text)
    if not m:
        sys.exit(f"FAIL: no `CAP {who}` dump in the run")
    b = bytes.fromhex(m.group(1))
    b = b + bytes(CAPLEN - len(b))
    if b[1] != 0xA5:
        sys.exit(f"FAIL: the {who} block is not complete (CAP+1 = ${b[1]:02X}, not $A5)")
    return b


def cell(c):
    return chr(c) if 32 <= c < 127 else f"${c:02X}"


def main():
    text = open(sys.argv[1]).read()
    ref, zb = block(text, "ref"), block(text, "ours")
    print("XCHPUT (probes/bios/spec/xchput.asm), the CHPUT matrix, run through probes/bios/biosl_run.py on the")
    print("NODISK row: the Philips VG-8020 (the main-BIOS reference) against zerobas (C-BIOS repack). CHPUT is")
    print("called DIRECTLY by the cartridge. SCREEN 0, width 40 (LINL40 := 40, INITXT, CLS at INIT).")
    print("Before every case: CHPUT 'x' 'x', CR, ESC Y row 10 col 19 (0-based), 'P' 'Q' 'R', ESC Y row 10 col 20:")
    print("the cursor on the Q (CSRY 11, CSRX 21, 1-based); cells = row 10, columns 19 / 20 / 21 (P Q R before).")
    print("Columns: CSRX CSRY A cells (VG-8020) | the same (zerobas). Case n = mode * 256 + v.")
    print(f"LINLEN: VG-8020 {ref[0]}, zerobas {zb[0]}")
    for mo, name in enumerate(MODES):
        print(f"\n== mode {mo}: {name} ==")
        for v in range(256):
            n = mo * 256 + v
            r = ref[2 + 6 * n: 8 + 6 * n]
            z = zb[2 + 6 * n: 8 + 6 * n]
            fmt = lambda x: f"{x[0]:2} {x[1]:2} ${x[2]:02X} {cell(x[3])} {cell(x[4])} {cell(x[5])}"
            print(f"{n:4}  v {v:3} ${v:02X} | {fmt(r):22} | {fmt(z):22}{'  DIFF' if r != z else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
