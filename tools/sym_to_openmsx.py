#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Convert a pasmo `--sym` symbol file to openMSX 'generic' symbol format.

pasmo emits   NAME<TAB>EQU 0XXXXH
openMSX wants  NAME: equ 0xXXXX   (loaded with: debug symbols load <file> generic)

so disassembly and traces can show symbol names instead of bare addresses.

    python3 tools/sym_to_openmsx.py build/disk.sym build/disk.omsx.sym
"""
import re
import sys


def convert(src: str, dst: str) -> int:
    n = 0
    out = []
    pat = re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H\s*$")
    for line in open(src):
        m = pat.match(line.strip())
        if not m:
            continue
        name, hexval = m.group(1), m.group(2)
        out.append(f"{name}: equ 0x{int(hexval, 16):04X}\n")
        n += 1
    open(dst, "w").write("".join(out))
    return n


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: sym_to_openmsx.py <pasmo.sym> <out.omsx.sym>")
    count = convert(sys.argv[1], sys.argv[2])
    print(f"wrote {sys.argv[2]}: {count} symbols (openMSX generic format)")
