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
  K-PM2  the seed gate is `!= B` ONLY   -> a seed already C stops the fill
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
    # The seed gate is the `!= B` half ONLY -- gfx_paint_passable, not
    # gfx_paint_inside. Swapping in the stricter test also refuses a seed that is
    # already C, which the references do NOT do in multicolour (sc3.up = 9).
    ("K-PM2  seed gate: passable -> inside",
     "                call    gfx_paint_passable\n"
     "                ret     nc                  ; the seed cell reads B",
     "                call    gfx_paint_inside    ; K-PM2\n"
     "                ret     nc                  ; the seed cell reads B",
     {"sc3.up"}),
    # gfx_paint_read's MC arm returns Zf=0 unconditionally: no MC cell is ever
    # "never-drawn background". Making colour 4 report background restores the
    # SCREEN-2 escape, and a background-coloured cell stops being a border --
    # which only shows where B IS the background.
    ("K-PM3  MC read: cp $FF -> cp $04 (colour 4 reads as background)",
     "                cp      $FF                 ; A preserved, Zf=0 -> \"drawn\", always",
     "                cp      $04                 ; K-PM3",
     {"mb.b4.up", "mb.b4.seed"}),
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
