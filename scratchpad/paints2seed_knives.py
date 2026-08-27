#!/usr/bin/env python3
"""D-PAINTS2SEED knife runner. Predictions written BEFORE the run.

Same conventions as scratchpad/paintmc_knives.py: the PROBE is the subject, never
`make <gate>`; restore by WRITING THE BYTES; `rm -rf build` before EVERY knife
build; hash BOTH images and refuse a knife whose cut did not move one; restore in
`finally`; calibrate the parser on planted logs before the baseline runs.

THE CLAIM: PAINT's seed admission test is ONE comparison whose COMPARAND is
chosen by mode -- SCREEN 2 refuses a seed already reading C, MULTICOLOUR refuses
one already reading B -- and those are MIRRORS, not one shared rule. Each knife
gives one arm the OTHER mode's comparand.

  K-S2S1  SCREEN 2 compares against C   -> swap it for B
  K-S2S2  MULTICOLOUR compares against B -> swap it for C

🟢 Each knife carries the other mode's rows as green controls. A knife that
reddened both halves would have shown the two arms are not independent.
"""
import hashlib, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUB  = ROOT / "sub/graphics.asm"
ROMS = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom"]

# label -> the value BOTH references printed (rounds r3..r11, 2026-08-22)
WANT = {
    # --- SCREEN 2 ---
    "sc2.up":        "4",   # drawn seed == C, open screen
    "su2.drawn":     "4",   # drawn seed == C, inside a box, reads the interior
    "su2.row.cbg":   "9",   # UNDRAWN seed, C == bg; the witness is on the seed's row
    "su2.row.ctl":   "9",   # ...same geometry, C != bg: the fill DOES run
    "sd2.wall.in":   "9",   # seed == B floods in SCREEN 2
    "sd2.wall.seed": "9",
    "box2.in":       "9",   # a plain bounded fill
    # --- MULTICOLOUR ---
    "sd3.wall.in":   "4",   # seed == B paints NOTHING in MC
    "sd3.wall.seed": "15",
    "mb.b4.up":      "4",
    "mb.b4.seed":    "4",
    "sc3.up":        "9",   # ...and a seed == C floods
    "ac3.stop":      "4",
    "box3.in":       "9",
}
ROWS = tuple(WANT)
PROBE = ["python3", "scratchpad/paintmc_probe.py", *ROWS]
ENV = {"PAINTMC_SIDES": "zb"}

ORIG = SUB.read_text()

KNIVES = [
    # SCREEN 2's arm gets MULTICOLOUR's comparand. Every SCREEN-2 seed row flips:
    # the two `== C` seeds stop being refused and flood, and the two `== B` seeds
    # start being refused and stop flooding. box2.in's seed is neither (undrawn,
    # background 4, B=15, C=9) so it must stay green -- as must every MC row.
    ("K-S2S1  SCREEN 2 comparand: GFX_C -> GFX_B",
     "                ld      a,(GFX_C)           ; SCREEN 2: the paint colour",
     "                ld      a,(GFX_B)           ; K-S2S1",
     {"sc2.up", "su2.drawn", "su2.row.cbg", "sd2.wall.in", "sd2.wall.seed"}),
    # ...and the mirror. 🎯 NOT all four `== B` rows redden, and deriving why is
    # the point: un-refusing those seeds lets the fill paint the SEED CELL, but in
    # both geometries the seed's neighbours are border-coloured, so it goes
    # nowhere. Only the `.seed` rows move; `.in`/`.up` read a cell the fill still
    # never reaches. sc3.up moves the other way -- a seed == C now IS refused.
    ("K-S2S2  MULTICOLOUR comparand: GFX_B -> GFX_C",
     "                ld      a,(GFX_B)           ; MC: the border colour",
     "                ld      a,(GFX_C)           ; K-S2S2",
     {"sd3.wall.seed", "mb.b4.seed", "sc3.up"}),
]


def sh(c, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(c, cwd=ROOT, capture_output=True, text=True, env=e)


def hashes():
    return tuple(hashlib.sha256(r.read_bytes()).hexdigest()[:8] if r.exists()
                 else "<none>" for r in ROMS)


def restore(): SUB.write_text(ORIG)


ROW_RE = re.compile(r"^\s{2}zb\s+(\S+)\s+->\s+'([^']*)'")


def divergent(out):
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
    clean = "".join(f"  zb      {l:13s} -> '{v}'\n" for l, v in WANT.items())
    if divergent(clean) != set():
        print("CALIBRATION FAILED: a clean log did not read clean"); return False
    planted = clean.replace("  zb      sc2.up        -> '4'",
                            "  zb      sc2.up        -> '9'")
    if planted == clean or divergent(planted) != {"sc2.up"}:
        print("CALIBRATION FAILED: a planted divergence was not found"); return False
    missing = "\n".join(l for l in clean.splitlines() if "box3.in" not in l)
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
            ok = got == pred
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
