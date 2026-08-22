#!/usr/bin/env python3
"""D-DEFFN CARVE HUNT — find byte-identical spans in the MAIN ROM.

D-PAINTBORD's carve is the shape being looked for: `gfx_absent` was
BYTE-IDENTICAL to `gfx_err5` and became `equ` it (-5 B), on
`basic/interp.asm`'s own `err_illegal_fn` precedent. This asks the whole main
image the same question mechanically instead of by eye.

A span is [label_addr, next_label_addr). Two spans are candidates when their
bytes are equal AND the span is position-independent under the collapse --
which this tool CANNOT decide (a span containing an absolute address is still
identical to another containing the same absolute address, and collapsing them
is then correct; a span containing a RELATIVE jump out of itself is not). So
every hit is a CANDIDATE to be read, never a verdict.

🔴 THE DENOMINATOR IS THE POINT. It prints how many spans it walked and how
many it could not (zero-length, or past the image), so a run that finds nothing
is a statement about a known number of spans rather than about the tool.

⚠️ CALIBRATION: `--selftest` plants two synthetic identical spans and asserts
the walk finds THAT pair, so a run reporting "0 candidates" is known not to be
a walk that finds nothing by construction.
"""
from __future__ import annotations
import sys, collections

def load_syms(path, lo, hi):
    out = []
    for line in open(path):
        line = line.strip()
        if not line or "EQU" not in line:
            continue
        name, _, val = line.partition("\tEQU")
        val = val.strip().rstrip("H").lstrip("0") or "0"
        try:
            a = int(val, 16)
        except ValueError:
            continue
        name = name.strip()
        if lo <= a < hi:
            out.append((a, name))
    out.sort()
    return out

def spans(syms, rom, base, end):
    """[(addr, name, bytes)] -- one per distinct address, longest run to next."""
    byaddr = collections.OrderedDict()
    for a, n in syms:
        byaddr.setdefault(a, []).append(n)
    addrs = sorted(byaddr)
    out = []
    for i, a in enumerate(addrs):
        nxt = addrs[i + 1] if i + 1 < len(addrs) else end
        if nxt <= a:
            continue
        b = rom[a - base:nxt - base]
        if b:
            out.append((a, "/".join(byaddr[a]), b))
    return out

def main() -> int:
    rom = open("build/basic-reloc.rom", "rb").read()
    BASE = 0x2812                       # the main image's load address
    END = BASE + len(rom)
    selftest = "--selftest" in sys.argv
    syms = load_syms("build/basic-reloc.sym", BASE, END)
    sp = spans(syms, rom, BASE, END)
    if selftest:
        # 🟢 plant two identical synthetic spans and require the walk to find them
        sp = list(sp) + [(0xFFFE, "__PLANT_A", b"\x11\x22\x33\x44\x55"),
                         (0xFFFF, "__PLANT_B", b"\x11\x22\x33\x44\x55")]
    print(f"  denominator: {len(syms)} labels in [{BASE:04X},{END:04X}), "
          f"{len(sp)} non-empty spans")
    groups = collections.defaultdict(list)
    for a, n, b in sp:
        if len(b) >= 3:                 # a 1-2 byte span is noise, not a carve
            groups[b].append((a, n))
    hits = [(b, g) for b, g in groups.items() if len(g) > 1]
    hits.sort(key=lambda t: -len(t[0]) * (len(t[1]) - 1))
    if selftest:
        ok = any(n == "__PLANT_A" for b, g in hits for _, n in g)
        print(f"  SELFTEST: planted pair found = {ok}")
        return 0 if ok else 1
    saved = 0
    for b, g in hits:
        saved += len(b) * (len(g) - 1)
        print(f"  {len(b):3d} B x{len(g)}  {b.hex()}")
        for a, n in g:
            print(f"        ${a:04X}  {n}")
    print(f"  {len(hits)} duplicate groups, {saved} B recoverable IF every "
          f"collapse is position-independent (READ EACH ONE)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
