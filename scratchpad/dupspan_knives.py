#!/usr/bin/env python3
"""D-DUPSPAN knife runner. Predictions written BEFORE the run.

Conventions copied from scratchpad/paintbord_knives.py: the PROBE is the
subject, never `make <gate>` (make exits 2 for ANY failed recipe); restore by
WRITING THE BYTES, never shutil.copy2; `rm -rf build` before EVERY knife build;
hash BOTH images and refuse a knife whose cut did not move one; restore in
`finally`; calibrate the parser on a clean log, a planted one and a row-deleted
one BEFORE the baseline runs.

⚠️ EVERY CUT IS IN basic/*.asm, so `build/basic-reloc.rom` is the image that
must move and `build/sub.rom` must NOT. The runner prints both and names which.

THE CLAIM: thirteen `ld a,N / jp raise_error` tails were byte-identical to two
canonical ones and are now `equ` aliases of them. Collapsing them changed no
observable BECAUSE nothing but A distinguishes the sites -- `raise_error` reads
A, ERRFLG and the interpreter's own line state, never the stack or the entry
address, and it is never `call`ed.

🎯 THE KNIFE THAT MATTERS IS THE ONE THAT PROVES EACH SITE IS SEEN AT ALL. A
green battery says the collapse broke nothing; it cannot say the collapse was
observable. K-DS1 and K-DS2 cut the CANONICAL VALUE, so every site that really
routes through it must redden -- and a site that does not is a site no row
reaches, which is the finding either way.

  K-DS1  the ERR-5 canonical value   gb_illegal `ld a,5` -> `ld a,9`
  K-DS2  the ERR-2 canonical value   pl_syntax  `ld a,2` -> `ld a,9`
  K-DS3  the FALLTHROUGH REPAIR      sw_absent's new `jp gb_illegal` retargeted
  K-DS4  UN-ALIASING an ERR-5 name   gfx_err5    equ -> gfx_typeerr
  K-DS5  UN-ALIASING an ERR-2 name   trap_syntax equ -> gfx_typeerr

🟢 K-DS1 and K-DS2 have DISJOINT predicted sets and each carries the whole of
the other family as green controls: a knife that reddened both would be a
statement about the apparatus (an address shift, a rebuilt-wrong machine), not
about the tails.

🎯 K-DS3 is the only knife aimed at code this slice WROTE. `sw_illegal` was a
FALLTHROUGH target, so its alias could not stand alone and `sw_absent` reaches
ERR 5 through a `jp` that did not exist before. It must redden `e5.swapnew` and
NOT `e5.swap3`, which reaches the same tail by the surviving `jp sw_illegal` --
two SWAP faults that were one span and are now two routes.

🎯 K-DS4/K-DS5 prove the promise in gfx_absent's own comment, which this carve
inherits thirteen times over: *un-alias here and no call site moves*. Retargeting
ONE `equ` gives that one name a distinct face and leaves its family alone. A
collapse whose knife reddens the whole family would be a collapse that had lost
the distinction; these say the distinction is one line away from coming back.

⚠️ K-DS4/K-DS5 change a jp TARGET, not a jp into nothing: `gfx_typeerr` is
already live and `gb_illegal`/`pl_syntax` keep many other callers, so `make
deadcode` still passes and the knife can actually be run (the "cut a VALUE, not
a CALL" rule's real content).
"""
import hashlib, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRCS = [ROOT / p for p in ("basic/interp.asm", "basic/play.asm",
                           "basic/missing.asm", "basic/graphics.asm",
                           "basic/program.asm")]
ROMS = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom"]
ORIG = {p: p.read_text() for p in SRCS}

# label -> the face BOTH references printed, which is also what this build
# prints. FILLED FROM THE MEASURED REFERENCE ROUND -- see dupspan_refs.out.
E5 = ["e5.vpoke", "e5.mid0", "e5.chr", "e5.sound", "e5.pset0", "e5.eof300",
      "e5.interv", "e5.strig", "e5.key", "e5.swap3", "e5.swapnew"]
E2 = ["e2.play", "e2.line", "e2.pset", "e2.paint4", "e2.putspr", "e2.letvdp",
      "e2.oninterv"]
WANT = {**{l: "ERR 5" for l in E5}, **{l: "ERR 2" for l in E2}}
ROWS = tuple(WANT)
PROBE = ["python3", "scratchpad/dupspan_probe.py", *ROWS]
ENV = {"DUPSPAN_SIDES": "zb"}

KNIVES = [
    # The ERR-5 canonical VALUE. Every one of the eight tails is now these two
    # instructions, so every ERR-5 row must move to ERR 9 -- and every ERR-2 row
    # must not. Nothing changes size, so no address shifts.
    ("K-DS1  ERR-5 canonical value: gb_illegal `ld a,5` -> `ld a,9`",
     ROOT / "basic/interp.asm",
     # space plan B-3 (C4, 2026-10-04) reworded these comments; re-anchored
     "                ld      a,5                 ; cg_unclaimed and str-engine's MID$ bound\n"
     "                jp      raise_error         ; ERR 5 illegal function call  -- jump here",
     "                ld      a,9                 ; K-DS1\n"
     "                jp      raise_error         ; ERR 5 illegal function call  -- jump here",
     set(E5)),
    # The ERR-2 canonical value. The mirror, with the ERR-5 family as controls.
    ("K-DS2  ERR-2 canonical value: pl_syntax `ld a,2` -> `ld a,9`",
     ROOT / "basic/play.asm",
     "pl_syntax:\n"
     "                ld      a,2                 ; Syntax error (missing/bad voice operand),",
     "pl_syntax:\n"
     "                ld      a,9                 ; K-DS2",
     set(E2)),
    # The fallthrough repair, and ONLY it. e5.swap3 is the separating control:
    # it reaches the same tail through the surviving `jp sw_illegal`.
    ("K-DS3  fallthrough repair: sw_absent's `jp gb_illegal` -> `jp gfx_typeerr`",
     ROOT / "basic/missing.asm",
     "                jp      gb_illegal          ; 🔴 sw_illegal is a FALLTHROUGH target, so the",
     "                jp      gfx_typeerr         ; K-DS3",
     {"e5.swapnew"}),
    # Un-aliasing ONE ERR-5 name. Its six `jp gfx_err5` call sites do not move.
    ("K-DS4  un-alias: gfx_err5 equ gb_illegal -> equ gfx_typeerr",
     ROOT / "basic/graphics.asm",
     "gfx_err5        equ     gb_illegal  ; ERR 5 (PSET/PRESET in SCREEN 0/1)",
     "gfx_err5        equ     gfx_typeerr ; K-DS4",
     {"e5.pset0"}),
    # Un-aliasing ONE ERR-2 name, the one with fifteen call sites.
    ("K-DS5  un-alias: trap_syntax equ pl_syntax -> equ gfx_typeerr",
     ROOT / "basic/program.asm",
     "trap_syntax     equ     pl_syntax   ; ERR 2 (malformed trap statement)",
     "trap_syntax     equ     gfx_typeerr ; K-DS5",
     {"e2.oninterv"}),
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


def restore():
    for p, t in ORIG.items():
        p.write_text(t)


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
    clean = "".join(f"  zb      {l:11s} -> '{v}'   [x]\n" for l, v in WANT.items())
    if divergent(clean) != set():
        print("CALIBRATION FAILED: a clean log did not read clean"); return False
    planted = clean.replace("  zb      e5.sound    -> 'ERR 5'",
                            "  zb      e5.sound    -> 'ERR 9'")
    if planted == clean or divergent(planted) != {"e5.sound"}:
        print("CALIBRATION FAILED: a planted divergence was not found"); return False
    missing = "\n".join(l for l in clean.splitlines() if "e2.play " not in l)
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

        for name, src, old, new, pred in KNIVES:
            restore()
            if ORIG[src].count(old) != 1:
                print(f"APPARATUS: {name}: anchor matched {ORIG[src].count(old)}x")
                return 3
            src.write_text(ORIG[src].replace(old, new))
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
                  f"        want={sorted(pred)}\n"
                  f"        got ={sorted(got) if got is not None else 'UNPARSED'}",
                  flush=True)
    finally:
        restore(); sh(["rm", "-rf", "build"]); sh(["make", "repack-machine"])
        for p, t in ORIG.items():
            assert p.read_text() == t, f"{p} not restored!"
        print(f"\nrestored: roms={hashes()}  all five sources byte-identical")
    n = sum(rows)
    print(f"\n{n}/{len(rows)} knife rows EXACT")
    return 1 if n != len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
