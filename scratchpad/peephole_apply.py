#!/usr/bin/env python3
"""Emit the page-1 jp->jr conversions as (file, line, from, to), located by the
target LABEL rather than by address, so the edit is applied to source safely.

For every class-A site (jp cc in jr range, page 1), resolve the target address to
its .sym label, then find `jp <cc,>label` in the page-1 source files. A site is
APPLIED only if that (mnemonic,label) text is UNIQUE across page-1 source -- an
ambiguous one is SKIPPED and reported, never guessed. The assembler is the final
check: range only tightens under conversion, so every applied jr must assemble.
"""
import importlib.util, os, re, glob, collections, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("di", "tools/dupspan_indep.py")
di = importlib.util.module_from_spec(spec); spec.loader.exec_module(di)
BASE = di.BASE
rom = open("build/basic-reloc.rom", "rb").read(); n = len(rom)

# addr -> label (first label at that addr)
addr2lbl = {}
for ln in open("build/basic-reloc.sym"):
    m = re.match(r'(\S+)\s+EQU\s+0([0-9A-Fa-f]+)H', ln)
    if m:
        a = int(m.group(2), 16)
        addr2lbl.setdefault(a, m.group(1))

JP = {0xC3: "jp", 0xCA: "jp z", 0xC2: "jp nz", 0xDA: "jp c", 0xD2: "jp nc"}
def ilen(i):
    op = rom[i]
    return di.decode(rom, i)[0] if op in (0xCB,0xDD,0xED,0xFD) else di._LEN[op]

sites = []          # (mnemonic, label)
i = 0
while i < n:
    op = rom[i]; addr = BASE + i; L = ilen(i) or 1
    if op in JP and 0x4000 <= addr < 0x8000 and i+2 < n:
        tgt = rom[i+1] | (rom[i+2] << 8)
        disp = tgt - (addr + 2)
        if -126 <= disp <= 129 and rom[tgt-BASE] != 0xC9:   # exclude jp->ret (class B)
            lbl = addr2lbl.get(tgt)
            if lbl:
                sites.append((JP[op], lbl))
    i += L

# page-1 source files
PAGE1_SRC = sorted(set(glob.glob("basic/*.asm")) | set(glob.glob("basic/*.inc")))
# build an index: (mnemonic,label) -> [(file,lineno,rawline)]
want = collections.Counter(sites)
found = collections.defaultdict(list)
JPRE = re.compile(r'^(\s*)jp\s+((?:z|nz|c|nc)\s*,\s*)?([A-Za-z_]\w*)\s*(;.*)?$')
for f in PAGE1_SRC:
    for k, raw in enumerate(open(f, errors="ignore"), 1):
        code = raw.rstrip("\n")
        m = JPRE.match(code.split(";",1)[0].rstrip() + (" " + code.split(";",1)[1] if ";" in code else ""))
        mm = JPRE.match(code)
        if not mm:
            continue
        ind, cc, lbl, cmt = mm.groups()
        mnem = "jp" if not cc else "jp " + cc.replace(",","").strip()
        found[(mnem, lbl)].append((f, k, code, ind, cc, cmt))

applied, skipped, ambig = [], [], []
for (mnem, lbl), cnt in want.items():
    locs = found.get((mnem, lbl), [])
    if len(locs) == cnt == 1:
        applied.append((mnem, lbl, locs[0]))
    elif not locs:
        skipped.append((mnem, lbl, cnt, "no source match (macro/other file)"))
    else:
        ambig.append((mnem, lbl, cnt, len(locs)))

print(f"page-1 class-A sites: {len(sites)}  (unique labels: {len(want)})")
print(f"  cleanly locatable & UNIQUE (will apply): {len(applied)}")
print(f"  ambiguous (mnemonic+label appears >1x)  : {len(ambig)}")
print(f"  no source match                         : {len(skipped)}")

if "--write" in sys.argv:
    byfile = collections.defaultdict(list)
    for mnem, lbl, (f, k, code, ind, cc, cmt) in applied:
        byfile[f].append((k, code, ind, cc, lbl, cmt))
    for f, edits in byfile.items():
        lines = open(f).read().split("\n")
        for k, code, ind, cc, lbl, cmt in edits:
            old = lines[k-1]
            new = re.sub(r'\bjp\b', "jr", old, count=1)
            assert old == code, f"{f}:{k} drift:\n  {old!r}\n  {code!r}"
            lines[k-1] = new
        open(f, "w").write("\n".join(lines))
        print(f"  wrote {len(edits)} conversions to {f}")
    print(f"\nAPPLIED {len(applied)} conversions. Build now.")
else:
    for mnem, lbl, cnt, why in skipped[:8]:
        print(f"    skip  {mnem:6} {lbl:24} {why}")
    for mnem, lbl, cnt, nloc in ambig[:8]:
        print(f"    ambig {mnem:6} {lbl:24} rom={cnt} src={nloc}")
