#!/usr/bin/env python3
"""D-PAINTBORD knife runner. Predictions written BEFORE the run.

Same conventions as scratchpad/paintmc_knives.py and paints2seed_knives.py: the
PROBE is the subject, never `make <gate>` (make exits 2 for ANY failed recipe, so
a runner shelling out to a gate cannot tell a tree fault from an instrument
fault); restore by WRITING THE BYTES, never shutil.copy2; `rm -rf build` before
EVERY knife build; hash BOTH images and refuse a knife whose cut did not move
one; restore in `finally`; calibrate the parser on a clean log, a planted one and
a row-deleted one BEFORE the baseline runs.

⚠️ THIS SLICE CUTS `basic/graphics.asm`, so `build/basic-reloc.rom` is the image
that must move and `build/sub.rom` must NOT -- the mirror of D-PAINTS2SEED, which
cut sub/graphics.asm and moved only sub.rom. The runner prints both and names
which one moved, because a guard watching the wrong image halts with the right
verdict and the wrong reason.

THE CLAIM, in four separable pieces:

    B is 0..255 in SCREEN 2 and 0..15 in MULTICOLOUR; outside -> ERR 5,
    raised as B is parsed, ABOVE the 4th-argument grammar test.

  K-PB1  the MULTICOLOUR bound   -- the nibble mask $F0 -> $00
  K-PB2  the BYTE bound          -- gfx_chk_dom's `or d` -> `or a`
  K-PB3  the mode SELECTION      -- `cp 3` -> `cp 2` (the two domains swap)
  K-PB4  the PLACEMENT           -- the grammar test moved above the check

🟢 K-PB1 and K-PB2 have DISJOINT predicted sets, and each carries the other
half's rows as green controls. K-PB3 reddens BOTH halves in OPPOSITE directions,
which is what a swapped domain looks like and what a merely-absent one does not.
🎯 K-PB2's set had to be DERIVED and that is what makes it a claim: dropping the
high-byte test does NOT redden all four out-of-range rows. `-1` is $FFFF, so in
multicolour `and $F0` still sees $F0 and raises anyway (bd3.neg stays GREEN);
`256` is $0100, whose low byte is $00, so the mask sees nothing (bd3.256 REDDENS).
Two rows that look like one class part company under the knife.

⚠️ K-PB4 is a code MOTION, not a value cut. The "cut a VALUE, not a CALL" rule
exists because deleting the only call to a routine fails `make deadcode` and so
builds no ROM -- a knife that cannot be run. A motion keeps every symbol
referenced and assembles, and it is the only edit that expresses "the check sits
below the grammar", which is precisely what §4 measured it does not.
"""
import hashlib, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path("/Users/joost/projects/zerobas")
SRC  = ROOT / "basic/graphics.asm"
ROMS = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom"]

# label -> the value BOTH references printed (2026-08-22), which is also what the
# fixed build prints. Kept lean on the SLOW rows: bd2.* run at step=90 (a
# 256x192 flood) and bd3.* at 30, while every error row is pre-tenant and fast.
# One flooding positive per mode is enough to say "the fill still runs".
WANT = {
    # --- SCREEN 2: the domain is the whole byte ---
    "bd2.15":    "9",       # in domain -> floods
    "bd2.neg":   "ERR 5",   # $FFFF -- caught by the high byte
    "bd2.256":   "ERR 5",   # $0100 -- low byte $00, caught ONLY by the high byte
    "od2.b256c": "ERR 5",   # ...and it beats a 4th argument
    "od2.b16c":  "ERR 2",   # 16 IS in domain here, so the grammar wins
    # --- MULTICOLOUR: the domain is the nibble ---
    "bd3.15":    "9",       # in domain -> floods
    "bd3.16":    "ERR 5",
    "bd3.17":    "ERR 5",
    "bd3.255":   "ERR 5",
    "bd3.neg":   "ERR 5",
    "bd3.256":   "ERR 5",
    "od3.b16c":  "ERR 5",   # the domain beats a 4th argument
    "od3.b15c":  "ERR 2",   # 15 IS in domain, so the grammar wins -- and this row
                            # is ALSO what excludes the second cause of ERR 5:
                            # a SCREEN-3 PAINT refused outright cannot reach ERR 2
}
ROWS = tuple(WANT)
PROBE = ["python3", "scratchpad/paintmc_probe.py", *ROWS]
ENV = {"PAINTMC_SIDES": "zb"}

ORIG = SRC.read_text()

KNIVES = [
    # The MULTICOLOUR bound alone. With the mask $00 the MC domain widens to the
    # whole byte, so 16/17/255 stop raising and flood -- but -1 and 256 still have
    # a non-zero high byte and are still caught by `or d`, and every SCREEN-2 row
    # is untouched.
    ("K-PB1  multicolour bound: mask $F0 -> $00",
     "                ld      a,$F0               ; ...then B is a nibble, 0..15",
     "                ld      a,$00               ; K-PB1",
     {"bd3.16", "bd3.17", "bd3.255", "od3.b16c"}),
    # The BYTE bound alone, in the shared leaf. See the header for why bd3.neg
    # stays green and bd3.256 does not.
    ("K-PB2  byte bound: gfx_chk_dom `or d` -> `or a`",
     "                or      d                   ; non-zero -> outside the domain",
     "                or      a                   ; K-PB2",
     {"bd2.neg", "bd2.256", "od2.b256c", "bd3.256"}),
    # The mode SELECTION. `cp 2` makes SCREEN 2 take the nibble arm and
    # MULTICOLOUR the byte arm: the domains swap, so the two halves redden in
    # OPPOSITE directions and the rows caught by the high byte in both modes stay
    # green throughout.
    ("K-PB3  mode selection: cp 3 -> cp 2",
     "                cp      3                   ; MULTICOLOUR?",
     "                cp      2                   ; K-PB3",
     {"od2.b16c", "bd3.16", "bd3.17", "bd3.255", "od3.b16c"}),
    # The PLACEMENT. Only the two rows with an out-of-domain border BEHIND a 4th
    # argument can move; their in-domain twins already read ERR 2 and must stay
    # green, which is what distinguishes "the order changed" from "the check
    # vanished".
    ("K-PB4  placement: the grammar test moved ABOVE the domain check",
     """                ld      a,(SCRMOD)
                cp      3                   ; MULTICOLOUR?
                ld      a,$F0               ; ...then B is a nibble, 0..15
                jr      z,ep_b_dom          ; (`ld a,n` does not touch the flags)
                xor     a                   ; SCREEN 2: B is a whole byte, 0..255
ep_b_dom:
                call    gfx_chk_dom         ; A = E; ERR 5 outside the mode's domain
                ld      (GFX_B),a           ; low byte only (spec §6: GFX_B is 1 B)
                call    skip_spaces
                cp      ','
                jp      z,ep_syntax         ; a 4th argument -> ERR 2""",
     """                call    skip_spaces         ; K-PB4: the grammar test FIRST.
                cp      ','                 ; HL is at the char after the
                jp      z,ep_syntax         ; expression; skip_spaces preserves DE
                ld      a,(SCRMOD)
                cp      3
                ld      a,$F0
                jr      z,ep_b_dom
                xor     a
ep_b_dom:
                call    gfx_chk_dom
                ld      (GFX_B),a""",
     {"od2.b256c", "od3.b16c"}),
]


def sh(c, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(c, cwd=ROOT, capture_output=True, text=True, env=e)


def hashes():
    return tuple(hashlib.sha256(r.read_bytes()).hexdigest()[:8] if r.exists()
                 else "<none>" for r in ROMS)


def moved(base, now):
    names = ["basic-reloc.rom", "sub.rom"]
    return [n for n, b, c in zip(names, base, now) if b != c]


def restore(): SRC.write_text(ORIG)


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
    clean = "".join(f"  zb      {l:11s} -> '{v}'\n" for l, v in WANT.items())
    if divergent(clean) != set():
        print("CALIBRATION FAILED: a clean log did not read clean"); return False
    planted = clean.replace("  zb      bd3.16      -> 'ERR 5'",
                            "  zb      bd3.16      -> '9'")
    if planted == clean or divergent(planted) != {"bd3.16"}:
        print("CALIBRATION FAILED: a planted divergence was not found"); return False
    missing = "\n".join(l for l in clean.splitlines() if "bd2.15" not in l)
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
            SRC.write_text(ORIG.replace(old, new))
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
                  f"        roms={h} moved={moved(base_h, h)}\n"
                  f"        want={sorted(pred)} got="
                  f"{sorted(got) if got is not None else 'UNPARSED'}", flush=True)
    finally:
        restore(); sh(["rm", "-rf", "build"]); sh(["make", "repack-machine"])
        assert SRC.read_text() == ORIG, "basic/graphics.asm not restored!"
        print(f"\nrestored: roms={hashes()}  source byte-identical")
    n = sum(rows)
    print(f"\n{n}/{len(rows)} knife rows EXACT")
    return 1 if n != len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
