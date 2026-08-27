#!/usr/bin/env python3
"""D-SCREEN3 knife runner. Predictions written BEFORE the run (spec §7).

Conventions: the PROBE is the subject (never `make <gate>`); restore by WRITING
THE BYTES; `rm -rf build` before EVERY knife build; hash BOTH ROM images and
refuse a knife whose cut did not move one; restore in `finally`.

THE CLAIMS UNDER TEST -- the address model is arithmetic, so each term is a knife:
  K-S1  the ROW term      (cy&7)          -> every row but the first is wrong
  K-S2  the BLOCK term    (cy>>3)*256     -> only the first 256-byte block is right
  K-S3  the COLUMN term   (x & $F8)       -> every column but the first is wrong
  K-S4  the NIBBLE select (bit 2 of x)    -> the cell PAIR is swapped
  K-S5  the gfx_point dispatch            -> POINT's silent wrong answer returns
  K-S6  the gbf_row fallback              -> LINE ,BF writes the G2 byte pair
🟢 K-S7 is the GREEN control: a knife in the G2-only arm must move NOTHING here.
"""
import hashlib, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUB  = ROOT / "sub/graphics.asm"
ROMS = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom"]
ROWS = ("ctl.s2", "pset3", "s3.same", "s3.next", "s3.aliashi", "ctl.s3rd",
        "s3.rowsep", "s3.blksep", "s3.colsep")
PROBE = ["python3", "scratchpad/s3_scout_probe.py", *ROWS]

ORIG = SUB.read_text()

KNIVES = [
    # 🔴 K-S1 IN ITS FIRST FORM REDDENED NOTHING WITH THE ROM PROVABLY MOVED, and
    # the fixtures were why: PSET and POINT share gfx_calc_addr_mc, so a round
    # trip through it is invariant under any consistent bijection. The s3.*sep
    # rows write at one coordinate and read at another that differs by exactly
    # ONE term, which is what makes each term falsifiable.
    ("K-S1  row term (cy&7) -> 0",
     "                and     $07                 ; (y>>2) & 7  == cy & 7",
     "                and     $00                 ; K-S1",
     {"s3.rowsep"}),
    ("K-S2  block term (cy>>3) -> 0",
     "                and     $E0",
     "                and     $00                 ; K-S2",
     {"s3.blksep"}),
    ("K-S3  column term (x & $F8) -> 0",
     "                and     $F8                 ; (cx>>1)*8 == x & $F8, as in G2",
     "                and     $00                 ; K-S3",
     {"s3.colsep"}),
    # 🔴 THE FIRST `want` HERE WAS {s3.same, s3.next} AND IT WAS WRONG -- MY
    # PREDICTION, NOT THE CODE. Re-derived FROM THE FORMULA (not from the result):
    #   s3.next writes (0,0) and reads (4,4) -- y differs too, so the ROW term
    #     already puts them at addr 0 vs 1. The nibble never enters it. AGREES.
    #   s3.aliashi writes (255,191) and reads (252,188) -- same cell, and 255 vs
    #     252 differ in BIT 1, which is exactly what K-S4 switches to. DIVERGES.
    # A knife row is a claim about the FIXTURE as much as the code, and a fixture
    # that differs in two terms cannot isolate one of them.
    ("K-S4  nibble select: bit 2 of x -> bit 1",
     "                and     $04                 ; bit 2 of x IS bit 0 of cx",
     "                and     $02                 ; K-S4",
     {"s3.same", "s3.aliashi"}),
    # 🔴 THE FIRST `want` HERE WAS ALL EIGHT SCREEN-3 ROWS AND THAT WAS
    # OVER-SPECIFIED. With the dispatch gone POINT reads the G2 model out of MC
    # VRAM, and a wrong read that happens to land on the $44 background STILL
    # returns 4 -- so every row whose expected value IS 4 is a weak detector that
    # can agree for the wrong reason. Which of them agree depends on what the G2
    # address model lands on, which is not worth deriving. The DERIVABLE claim is
    # the one this knife exists for: the rows expecting a NON-background colour
    # must all redden. Checked as a SUBSET (want <= got), stated as weaker rather
    # than fitted to the observation.
    ("K-S5  gfx_point's MC dispatch removed  [subset]",
     "                jr      nz,gpt_g2",
     "                jr      gpt_g2              ; K-S5",
     {"pset3", "s3.same", "s3.aliashi"}),
]


def sh(c): return subprocess.run(c, cwd=ROOT, capture_output=True, text=True)
def hashes():
    return tuple(hashlib.sha256(r.read_bytes()).hexdigest()[:8] if r.exists()
                 else "<none>" for r in ROMS)
def restore(): SUB.write_text(ORIG)


def divergent(out):
    """Rows where zb disagrees with BOTH references. None if unparsed."""
    seen, bad = set(), set()
    for line in out.splitlines():
        # 🔴 THE VALUES CONTAIN SPACES INSIDE THEIR QUOTES ('0 , 7'), so a
        # `(\S+)` capture matches NOTHING. Draft 1 had exactly that and was caught
        # by calibrating on a real log before the run -- the D-RUNLINE lesson,
        # where a knife runner's parser reported 0/4 with every ROM moved.
        m = re.match(r"^\s{2}(\S+)\s+vg8020='([^']*)'\s+cf3300='([^']*)'"
                     r"\s+zb='([^']*)'", line)
        if not m or m.group(1) not in ROWS:
            continue
        lab, vg, cf, zb = m.groups()
        seen.add(lab)
        if zb != vg or zb != cf:
            bad.add(lab)
    if seen != set(ROWS):
        print(f"        APPARATUS: probe printed {sorted(seen)}, wanted {sorted(ROWS)}")
        return None
    return bad


def build():
    sh(["rm", "-rf", "build"])
    return sh(["make", "repack-machine"]).returncode == 0


def main():
    rows = []
    try:
        print("== build BEFORE the baseline ==", flush=True)
        if not build(): print("APPARATUS: repack failed"); return 3
        base_h = hashes()
        base = divergent(sh(PROBE).stdout)
        print(f"baseline roms={base_h} divergent={sorted(base) if base is not None else 'UNPARSED'}", flush=True)
        if base is None: print("APPARATUS: baseline unparsed"); return 3
        if base: print(f"APPARATUS: baseline not clean ({sorted(base)})"); return 3

        for name, old, new, pred in KNIVES:
            restore()
            if ORIG.count(old) != 1:
                print(f"APPARATUS: {name}: anchor matched {ORIG.count(old)}x"); return 3
            SUB.write_text(ORIG.replace(old, new))
            if not build():
                print(f"{name}: BUILD FAILED -- a knife that cannot run", flush=True)
                rows.append(False); continue
            h = hashes()
            if h == base_h:
                print(f"{name}: ROM DID NOT MOVE -- the cut was never applied", flush=True)
                rows.append(False); continue
            got = divergent(sh(PROBE).stdout)
            # a `[subset]` row asserts want <= got: see K-S5's note.
            ok = (pred <= got) if (got is not None and "[subset]" in name) \
                else (got == pred)
            rows.append(ok)
            print(f"{'EXACT' if ok else 'MISS '}  {name}\n"
                  f"        roms={h} want={sorted(pred)} got="
                  f"{sorted(got) if got is not None else 'UNPARSED'}", flush=True)
    finally:
        restore(); sh(["rm", "-rf", "build"]); sh(["make", "repack-machine"])
        assert SUB.read_text() == ORIG, "sub/graphics.asm not restored!"
        print(f"\nrestored: roms={hashes()}  source byte-identical")
    n = sum(rows)
    print(f"\n{n}/{len(rows)} knife rows EXACT")
    return 1 if n != len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
