#!/usr/bin/env python3
"""D-PAINTMC knife runner. Every prediction below was written BEFORE the run.

Conventions inherited from scratchpad/screen3_knives.py: the PROBE is the
subject (never `make <gate>`, whose rc 2 cannot be told from a tree fault);
restore by WRITING THE BYTES (never shutil.copy2 -- it keeps the mtime and make
then rebuilds nothing); `rm -rf build` before EVERY knife build; hash BOTH ROM
images and refuse a knife whose cut did not move one; restore in `finally`.

The knife rows run zb ALONE and score against the REFERENCE VALUES measured in
rounds r3/r4/r5, where the VG-8020 and the CF-3300 agreed on every row. That is
what makes a zb-only run legitimate here: the expectation is a reading, not a
prediction.

THE CLAIMS UNDER TEST:
  K-PM1  the MULTICOLOUR pitch (4)      -> the pre-slice symptom comes back
  K-PM2  RETIRED by D-PAINTS2SEED -> see paints2seed_knives.py K-S2S2
  K-PM3  MC never reports "background"  -> a background cell stops being a border
  K-PM4  the pitch in the UP direction  -> MC floods down but never up
  K-PM5  the SCREEN-2 pitch (1)         -> SCREEN 2 paints a sparse lattice
🟢 Each MC knife carries the two SCREEN-2 rows as GREEN CONTROLS and K-PM5 the
   reverse: a knife that reddens BOTH halves has not isolated anything.
"""
import hashlib, pathlib, re, subprocess, sys

ROOT = pathlib.Path("/Users/joost/projects/zerobas")
SUB  = ROOT / "sub/graphics.asm"
ROMS = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom"]

# label -> the value BOTH references printed (rounds r3/r4/r5, 2026-08-22)
WANT = {
    "box2.in":     "9",   "ac2.spread":  "9",   "ac2.stop":    "4",
    "box3.in":     "9",   "box3.out":    "4",
    "ac3.spread":  "9",   "ac3.stop":    "4",
    "mb.dflt.far": "9",   "mb.b7.up":    "9",
    "mb.b4.up":    "4",   "mb.b4.seed":  "4",
    "sc3.up":      "9",
    # 🔴 ADDED 2026-08-22 AFTER K-PM3 WENT BLIND (see its note below). The seed is
    # DRAWN to colour 9 so it is admitted, and B is the background, so the WALK is
    # where "is a background cell a border?" gets decided.
    "b4x.seed":    "1",   # ...the seed itself IS painted
    "b4x.far":     "4",   # ...and the fill does not spread: bg IS a border in MC
    "nt3.thru":    "9",   "nt3.above":   "9",   "tm3.far":     "9",
}
ROWS = tuple(WANT)
PROBE = ["python3", "scratchpad/paintmc_probe.py", *ROWS]
ENV = {"PAINTMC_SIDES": "zb"}

ORIG = SUB.read_text()

KNIVES = [
    # The headline claim. Pitch 1 in MC re-creates D-SCREEN3 §5's measured
    # symptom -- but NOT as "the seed only": a walk at pitch 1 still crosses cells
    # SIDEWAYS (gfx_paint_passable lets it through its own paint whenever C != B),
    # and it still steps to the row above when y-1 happens to fall in the next
    # cell row. What it can never do is leave the seed's own cell row when the
    # seed is not at a cell-row edge -- which is every row whose seed y is 10 or
    # 20. So the prediction is not "everything reddens".
    ("K-PM1  MULTICOLOUR pitch 4 -> 1",
     "                ld      a,4                 ; MULTICOLOUR: one cell is 4 pixels\n"
     "                jr      z,gpp_pitch_set",
     "                ld      a,1                 ; K-PM1\n"
     "                jr      z,gpp_pitch_set",
     {"box3.in", "ac3.spread", "mb.dflt.far", "mb.b7.up", "sc3.up",
      "nt3.thru", "tm3.far"}),
    # 🗑️ K-PM2 IS RETIRED, AND THE RUNNER IS WHAT NOTICED. It cut
    # `call gfx_paint_passable` -> `call gfx_paint_inside` in the seed gate, to
    # show the gate is the `!= B` half ONLY. D-PAINTS2SEED replaced that gate
    # with one comparison whose COMPARAND is chosen by mode, so the anchor
    # stopped existing and this runner ABORTED with "anchor matched 0x" rather
    # than scoring four knives and printing a tally -- which is the behaviour
    # worth keeping.
    # ✅ The claim is not lost: paints2seed_knives.py's K-S2S2 swaps that
    # comparand from GFX_B to GFX_C and predicts {sd3.wall.seed, mb.b4.seed,
    # sc3.up}. That is a SUPERSET of this knife's {sc3.up} and a strictly
    # stronger claim -- it pins the `== B` half as load-bearing too. Deleted here
    # rather than re-pointed, because a knife's value is in cutting the code that
    # actually ships.
    # gfx_paint_read's MC arm returns Zf=0 unconditionally: no MC cell is ever
    # "never-drawn background". Making colour 4 report background restores the
    # SCREEN-2 escape, and a background-coloured cell stops being a border --
    # which only shows where B IS the background.
    # 🔴 THIS KNIFE WENT BLIND AND THE RE-RUN IS WHAT CAUGHT IT. Its first set was
    # {mb.b4.up, mb.b4.seed}, and after D-PAINTS2SEED it reddened NOTHING with the
    # ROM provably moved. The cause is a real coupling, not a fixture accident:
    # that slice's seed gate reads the seed's COLOUR and ignores Zf, where the
    # gate it replaced went through gfx_paint_passable, which consulted it. In
    # mb.b4.* the seed IS the background, so it is now refused by colour alone and
    # the walk -- the only place Zf still matters -- never runs.
    # 🎯 b4x.* restores the teeth by DRAWING the seed first, so it is admitted and
    # the walk then meets background-coloured cells as borders. Under the knife
    # they stop being borders and the fill escapes: b4x.far goes 4 -> 1. b4x.seed
    # stays 1 either way and is the green anchor that says the seed ran at all.
    ("K-PM3  MC read: cp $FF -> cp $04 (colour 4 reads as background)",
     "                cp      $FF                 ; A preserved, Zf=0 -> \"drawn\", always",
     "                cp      $04                 ; K-PM3",
     {"b4x.far"}),
    # The pitch in ONE direction. `sub 1` is what the SCREEN-2 code already does
    # (pitch 1), so this knife CANNOT redden a SCREEN-2 row -- it is MC-only by
    # construction, and the downward rows must stay green.
    ("K-PM4  neighbour row y-pitch -> y-1",
     "                cp      (hl)\n"
     "                jr      c,gpp_up_done\n"
     "                sub     (hl)",
     "                cp      (hl)\n"
     "                jr      c,gpp_up_done\n"
     "                sub     1                   ; K-PM4",
     {"ac3.spread", "mb.b7.up", "nt3.above", "sc3.up"}),
    # ...and the mirror: SCREEN 2 at pitch 4 paints a sparse lattice, so a read
    # point that is not ON the lattice reads background. The MC rows must all
    # stay green.
    ("K-PM5  SCREEN-2 pitch 1 -> 4",
     "                ld      a,1\ngpp_pitch_set:",
     "                ld      a,4                 ; K-PM5\ngpp_pitch_set:",
     {"box2.in", "ac2.spread"}),
]


def sh(c, env=None):
    import os
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(c, cwd=ROOT, capture_output=True, text=True, env=e)


def hashes():
    return tuple(hashlib.sha256(r.read_bytes()).hexdigest()[:8] if r.exists()
                 else "<none>" for r in ROMS)


def restore(): SUB.write_text(ORIG)


ROW_RE = re.compile(r"^\s{2}zb\s+(\S+)\s+->\s+'([^']*)'")


def divergent(out):
    """Rows whose zb reading differs from the measured reference value.
    None if the row census is incomplete -- an apparatus fault, not a finding."""
    seen, bad = set(), set()
    for line in out.splitlines():
        m = ROW_RE.match(line)
        if not m or m.group(1) not in WANT:
            continue
        lab, val = m.groups()
        seen.add(lab)
        if val != WANT[lab]:
            bad.add(lab)
    if seen != set(ROWS):
        print(f"        APPARATUS: probe printed {len(seen)} of {len(ROWS)} rows; "
              f"missing {sorted(set(ROWS) - seen)}")
        return None
    return bad


def calibrate():
    """🔴 CALIBRATE THE PARSER ON KNOWN POSITIVES BEFORE TRUSTING IT. Two knife
    runners in this project have reported confident zeros because their regex
    matched nothing. Three logs: clean, one planted divergence, one row deleted."""
    clean = "".join(f"  zb      {l:11s} -> '{v}'\n" for l, v in WANT.items())
    if divergent(clean) != set():
        print("CALIBRATION FAILED: a clean log did not read clean"); return False
    planted = clean.replace("  zb      ac3.spread  -> '9'",
                            "  zb      ac3.spread  -> '4'")
    if planted == clean or divergent(planted) != {"ac3.spread"}:
        print("CALIBRATION FAILED: a planted divergence was not found"); return False
    missing = "\n".join(l for l in clean.splitlines() if "tm3.far" not in l)
    if divergent(missing) is not None:
        print("CALIBRATION FAILED: a deleted row did not read as apparatus"); return False
    print("parser calibrated: clean / planted / deleted all read correctly")
    return True


def build():
    sh(["rm", "-rf", "build"])
    return sh(["make", "repack-machine"]).returncode == 0


def main():
    if not calibrate():
        return 3
    rows = []
    try:
        print("== build BEFORE the baseline ==", flush=True)
        if not build():
            print("APPARATUS: repack failed"); return 3
        base_h = hashes()
        base = divergent(sh(PROBE, ENV).stdout)
        print(f"baseline roms={base_h} divergent="
              f"{sorted(base) if base is not None else 'UNPARSED'}", flush=True)
        if base is None:
            print("APPARATUS: baseline unparsed"); return 3
        if base:
            print(f"APPARATUS: baseline not clean ({sorted(base)})"); return 3

        for name, old, new, pred in KNIVES:
            restore()
            if ORIG.count(old) != 1:
                print(f"APPARATUS: {name}: anchor matched {ORIG.count(old)}x")
                return 3
            SUB.write_text(ORIG.replace(old, new))
            if not build():
                print(f"{name}: BUILD FAILED -- a knife that cannot run", flush=True)
                rows.append(False); continue
            h = hashes()
            if h == base_h:
                print(f"{name}: ROM DID NOT MOVE -- the cut was never applied",
                      flush=True)
                rows.append(False); continue
            got = divergent(sh(PROBE, ENV).stdout)
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
