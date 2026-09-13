#!/usr/bin/env python3
"""Address->source mapper for the jp->jr remainder.

pasmo 0.5.5 emits no listing, so there is no direct ROM-address <-> source-line
bridge. This builds one by REGION + ORDINAL:

  * ROM side: a full linear decode collects every control-transfer with its
    address, mnemonic, and target address. Each is tagged with its REGION (the
    nearest preceding label that also exists as a `^name:` in source) and its
    ORDINAL among (mnemonic, target) within that region.
  * SOURCE side: the same, per file, keyed by (preceding code-label, mnemonic,
    target label, ordinal).
  * JOIN on (region-address, mnemonic, target, ordinal). A convertible ROM site
    (jp-class, in jr range, target not `ret`) with a UNIQUE source match is
    proposed for conversion.

🎯 SAFETY IS NOT ON THIS TOOL. jp->jr is correct for ANY in-range site, and the
assembler enforces range across BOTH builds -- so a mis-map that picks an
in-range line is still correct, and one that picks an out-of-range line fails the
build by name and is reverted. The mapper only has to propose in-range
candidates; the build disposes. A non-1:1 join is SKIPPED, never guessed.

Reuses tools/dupspan_indep.py's decoder. Writes proposals; --write applies them.
"""
import importlib.util, os, re, glob, collections, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("di", "tools/dupspan_indep.py")
di = importlib.util.module_from_spec(spec); spec.loader.exec_module(di)
BASE = di.BASE
rom = open("build/basic-reloc.rom", "rb").read(); n = len(rom)

# --- symbols: name<->addr ---
name2addr = {}
for ln in open("build/basic-reloc.sym"):
    m = re.match(r'(\S+)\s+EQU\s+0([0-9A-Fa-f]+)H', ln)
    if m:
        name2addr[m.group(1)] = int(m.group(2), 16)
addr2names = collections.defaultdict(list)
for nm, a in name2addr.items():
    addr2names[a].append(nm)

# --- code-label addresses: labels that appear as `^name:` in source ---
SRC = sorted(set(glob.glob("basic/*.asm")) | set(glob.glob("basic/*.inc")))
srclabels = set()
for f in SRC:
    for ln in open(f, errors="ignore"):
        m = re.match(r'^([A-Za-z_]\w*):', ln)
        if m and m.group(1) in name2addr:
            srclabels.add(m.group(1))
code_label_addrs = sorted({name2addr[l] for l in srclabels})
import bisect
def region_of(addr):
    i = bisect.bisect_right(code_label_addrs, addr) - 1
    return code_label_addrs[i] if i >= 0 else None

# --- opcode maps ---
JP  = {0xC3:"jp",0xCA:"jp z",0xC2:"jp nz",0xDA:"jp c",0xD2:"jp nc",
       0xEA:"jp pe",0xE2:"jp po",0xFA:"jp m",0xF2:"jp p"}
JR  = {0x18:"jr",0x28:"jr z",0x20:"jr nz",0x38:"jr c",0x30:"jr nc"}
CALL= {0xCD:"call",0xCC:"call z",0xC4:"call nz",0xDC:"call c",0xD4:"call nc",
       0xEC:"call pe",0xE4:"call po",0xFC:"call m",0xF4:"call p"}
CONVERTIBLE_JP = {"jp","jp z","jp nz","jp c","jp nc"}   # have a jr form
def ilen(i):
    op=rom[i]
    return di.decode(rom,i)[0] if op in (0xCB,0xDD,0xED,0xFD) else di._LEN[op]

# --- ROM walk: all control-transfers with region+ordinal ---
rom_sites = []      # (addr, mnem, target_addr, region, ordinal, convertible)
ord_counter = collections.Counter()
i = 0
while i < n:
    op = rom[i]; addr = BASE+i; L = ilen(i) or 1
    mnem = tgt = None
    if op in JP or op in CALL:
        if i+2 < n: tgt = rom[i+1]|(rom[i+2]<<8); mnem = JP.get(op) or CALL.get(op)
    elif op in JR:
        if i+1 < n:
            d=rom[i+1]; tgt=addr+2+(d-256 if d>127 else d); mnem=JR[op]
    if mnem is not None and tgt is not None:
        reg = region_of(addr)
        key = (reg, mnem, tgt)
        o = ord_counter[key]; ord_counter[key]+=1
        conv = False
        if mnem in CONVERTIBLE_JP:
            disp = tgt-(addr+2)
            # 🔴 BUG 1, MEASURED 2026-09-13: this read `-126<=disp<=129`, and a `jr`
            # displacement is -128..+127. It proposed $4F5C -> ev_ff_lof at disp
            # +129, which pasmo rejects with `Relative jump out of range`. The
            # bound is now the assembler's, conservatively: converting a 3-byte
            # `jp` to a 2-byte `jr` shifts everything after the site down one, so a
            # FORWARD target could stretch to +128 -- we do not take that byte,
            # because the shift also moves every OTHER proposal in the same pass.
            conv = (-128<=disp<=127) and (0<=tgt-BASE<n) and rom[tgt-BASE]!=0xC9
        rom_sites.append((addr,mnem,tgt,reg,o,conv))
    i += L

# --- SOURCE walk: control-transfer lines with region+ordinal ---
JLINE = re.compile(r'^(\s*)(jp|jr|call)\s+((?:z|nz|c|nc|pe|po|p|m)\s*,\s*)?([A-Za-z_]\w*)\s*(;.*)?$', re.I)
src_index = {}      # (region_addr, mnem, target_label, ordinal) -> [(file,line,raw)]
# 🔴 BUG 2, MEASURED THE SAME DAY: a `*-body.inc` is included by MORE THAN ONE
# ROM, and this walk maps only the main image -- so $65BC -> bl_load_error read
# +110, comfortably in range HERE, and the build still failed because the same
# source line sits at a different address in the other ROM that includes it. The
# instruction-pair route already carries this rule ("EXCLUDE any *-body.inc that
# sub/ also includes"); Route D never did. In range in one image is not in range.
SRC = [f for f in SRC if not f.endswith("-body.inc")]
for f in SRC:
    cur_region = None
    ordc = collections.Counter()
    for k, raw in enumerate(open(f, errors="ignore").read().split("\n"), 1):
        code = raw.split(";",1)[0]
        ml = re.match(r'^([A-Za-z_]\w*):', code)
        if ml:
            if ml.group(1) in name2addr:
                cur_region = name2addr[ml.group(1)]
                ordc = collections.Counter()   # ordinal resets at each code label
            # a line can be `label: jp ...` -- fall through to check the rest
            code = code[ml.end():]
        mj = JLINE.match(code.strip() and (raw if not ml else code.strip()) or code)
        mj = JLINE.match((code if ml else raw).split(";",1)[0].rstrip())
        if not mj: 
            continue
        _,mn,cc,lbl,_ = mj.groups()
        mnem = mn.lower()+((" "+cc.replace(",","").strip()) if cc else "")
        if lbl not in name2addr:
            continue
        key=(cur_region, mnem, lbl)
        o=ordc[key]; ordc[key]+=1
        src_index.setdefault((cur_region,mnem,name2addr[lbl],o),[]).append((f,k,raw))

# --- JOIN: convertible ROM sites -> unique source line ---
proposals=[]; skipped_nomatch=0; skipped_ambig=0
for addr,mnem,tgt,reg,o,conv in rom_sites:
    if not conv: continue
    locs = src_index.get((reg,mnem,tgt,o),[])
    if len(locs)==1:
        proposals.append((addr,mnem,tgt,reg,locs[0]))
    elif not locs:
        skipped_nomatch+=1
    else:
        skipped_ambig+=1

# exclude already-converted (source already reads jr) and re-report page split
page1=[p for p in proposals if 0x4000<=p[0]<0x8000]
low=[p for p in proposals if p[0]<0x4000]
print(f"convertible ROM sites: {sum(1 for s in rom_sites if s[5])}")
print(f"  proposals (unique source match): {len(proposals)}  "
      f"[page1 {len(page1)}, low {len(low)}]")
print(f"  skipped no-match: {skipped_nomatch}   skipped ambiguous: {skipped_ambig}")

if "--write" in sys.argv:
    byfile=collections.defaultdict(list)
    for addr,mnem,tgt,reg,(f,k,raw) in proposals:
        byfile[f].append((k,raw))
    total=0
    for f,edits in byfile.items():
        lines=open(f).read().split("\n")
        for k,raw in edits:
            old=lines[k-1]
            assert old==raw, f"{f}:{k} drift\n {old!r}\n {raw!r}"
            new=re.sub(r'\bjp\b','jr',old,count=1)
            assert new!=old, f"{f}:{k} no jp to convert: {old!r}"
            lines[k-1]=new; total+=1
        open(f,"w").write("\n".join(lines))
        print(f"  wrote {len(edits)} to {f}")
    print(f"APPLIED {total} conversions.")
else:
    # 🔴 THE LISTING USED TO SHOW page1 ONLY, so the ten LOW-region
    # proposals were counted in the summary and never named -- and page 1 being dry
    # read as "the carve is dry" for a whole session (D-CARVE5). The low region is
    # a separate wall with its own budget; a routine can be sited there and called
    # from page 1 for 3 bytes.
    for addr,mnem,tgt,reg,(f,k,raw) in (page1+low)[:24]:
        tl=addr2names.get(tgt,['?'])[0]
        print(f"    ${addr:04X} {mnem:6}-> {tl:20} {f}:{k}")
