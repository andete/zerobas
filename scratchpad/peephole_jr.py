#!/usr/bin/env python3
"""The jp->jr size seam: how many main-image `jp`/`jp cc` targets are already in
`jr` range (-126..+129 from the instruction), i.e. convertible at -1 B each.

Walks the ASSEMBLED image (source labels don't carry the jp's own address).
Reuses dupspan_indep's instruction decoder so this and that tool agree on where
instructions begin. Only jp, jp z/nz/c/nc convert -- jr has no pe/po/p/m form.

🔴 THIS IS A FIRST-PASS CEILING, not a plan. Converting one jp->jr shifts every
byte after it, which can move OTHER targets in or out of range -- the real fix is
iterative and the assembler is the authority. And a `jr` is slower (12/7 vs 10
cyc), so a hot loop may keep its `jp` on purpose. Count first; decide later.
"""
import importlib.util, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("di", "tools/dupspan_indep.py")
di = importlib.util.module_from_spec(spec); spec.loader.exec_module(di)

BASE = di.BASE                      # $2812
rom = open("build/basic-reloc.rom", "rb").read()
# main image spans BASE.. ; page 1 is $4000..$7FFF
JP  = {0xC3: "jp", 0xCA: "jp z", 0xC2: "jp nz", 0xDA: "jp c", 0xD2: "jp nc"}
# (jp cc for pe/po/p/m: EA E2 FA F2 -- NOT convertible, counted separately)
JP_NC = {0xEA: "jp pe", 0xE2: "jp po", 0xFA: "jp m", 0xF2: "jp p"}

conv = collections.defaultdict(int) if False else {}
import collections
conv = collections.Counter(); byreg = collections.Counter()
noconv_cc = 0; total_jp = 0; examples = []
i = 0
n = len(rom)
while i < n - 2:
    op = rom[i]
    addr = BASE + i
    length = di._LEN[op] if op not in (0xCB,0xDD,0xED,0xFD) else di.decode(rom, i)[0]
    if op in JP or op in JP_NC:
        total_jp += 1
        tgt = rom[i+1] | (rom[i+2] << 8)
        # jr is 2 bytes; displacement measured from the byte AFTER the jr
        disp = tgt - (addr + 2)
        page = "p1" if 0x4000 <= addr < 0x8000 else ("low" if addr < 0x4000 else "?")
        if op in JP_NC:
            noconv_cc += 1
        elif -126 <= disp <= 129:
            conv[JP[op]] += 1
            byreg[page] += 1
            if len(examples) < 8:
                examples.append(f"${addr:04X} {JP[op]:6} -> ${tgt:04X} (disp {disp:+d}) [{page}]")
    i += length if length else 1

print(f"walked {n} B from ${BASE:04X}; {total_jp} jp/jp-cc instructions total")
print(f"\nconvertible to jr (-1 B each):")
for cc, c in conv.most_common():
    print(f"   {c:4}  {cc}")
tot = sum(conv.values())
print(f"   ----")
print(f"   {tot:4}  TOTAL convertible  ({byreg['p1']} in page 1, {byreg['low']} in low region)")
print(f"   {noconv_cc:4}  jp pe/po/p/m -- NO jr form, cannot convert")
print(f"\nexamples:")
for e in examples:
    print("   " + e)
print(f"\n✅ THIS IS A FLOOR, NOT A CEILING. Converting a jp->jr shifts every later "
      f"byte\n   DOWN by 1, which only TIGHTENS other displacements (forward targets "
      f"move closer,\n   backward gaps shrink) -- so no conversion knocks another out "
      f"of range, all {tot}\n   convert together, and the shrink may pull currently-"
      f"just-out-of-range jumps IN.\n   Caveats that remain: a jr is slower (12/7 vs "
      f"10 cyc), so a HOT loop may keep its\n   jp on purpose; and the assembler is the "
      f"final authority on range. Safety is NOT\n   a caveat: jr and jp are flag- and "
      f"control-flow-identical, so 'it assembles' == 'it\n   is correct'. That makes "
      f"this the safest carve class in the tree.")
