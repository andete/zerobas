#!/usr/bin/env python3
"""D-MISSOP KNIVES — three cuts, three DISTINCT predicted sets.

The fix is five bytes at `ev_f_err` plus one table byte, and each knife attacks
a different claim the fix makes:

  K-MO1  `ld e,FPERR_MISSOP` -> `ld e,0`
         THE DEFERRED CODE IS WHAT CLOSES THE ROWS. penderr_set with A=0 sets
         FPERR:=0, i.e. a no-op, so the machine goes back to the silent-zero
         behaviour. Predicts: every row the fix closed reverts, and NOTHING else
         moves. Size-neutral (2 B for 2 B), a VALUE cut.

  K-MO2  `db 24` -> `db 5` in fperr_to_err
         THE TABLE INDEX IS RIGHT. `fperr_to_err` is a DENSE table indexed by the
         FPERR code, and FPERR_MISSOP's value MOVES WITH `CLEARPOOL` (12 with,
         11 without) -- getting it wrong is silent, it just reads a neighbouring
         byte and reports some other error. If the closed rows answer 5 under
         this cut, the entry being read is the one this slice added.

  K-MO3  expr.asm:807 `jp nz,ev_f_err` -> `jp nz,ev_f_missop`
         THE FIX IS NARROW, AND THIS RE-CREATES THE BUG A SHIPPED GATE CAUGHT.
         The first draft sat on the shared `ev_f_err` tail, which has EIGHT jump
         sites; `make lineerr-acceptance` went 209/210 because site :807 -- a
         parenthesised expression closed by ',' instead of ')' -- is `Syntax
         error` (ERR 2) on both references, not 24. Point that one site at the
         new label and `b.paren` (`A=(1+2`) must move, while every row of the
         26-row verb matrix stays exactly where it is. Size-neutral.

🔴 EVERY KNIFE BUILD IS PRECEDED BY `rm -rf build`, RESTORES BY WRITING THE
BYTES (never a copy that preserves mtime), and ASSERTS THE RIGHT IMAGE MOVED --
a basic/*.asm cut moves basic-reloc.rom + the merged image and NOT sub.rom.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPR = ROOT / "basic/expr.asm"
INTERP = ROOT / "basic/interp.asm"
ROMS = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom",
        ROOT / "build/zerobas-main-eu.rom"]
RNAMES = ["basic-reloc.rom", "sub.rom", "zerobas-main-eu.rom"]
MAIN_MOVES = {"basic-reloc.rom", "zerobas-main-eu.rom"}
PROBES = (["python3", "scratchpad/missop_probe.py", "--sides=zb"],
          ["python3", "scratchpad/missop_blast.py", "--sides=zb", "b."])
NROWS = 26 + 11          # the verb matrix + the ev_f_err blast radius

# the 13 rows the fix closes -- K-MO1/K-MO2 must move exactly these
CLOSED = {"poke.val", "poke.plus", "poke.colon", "vpoke.val", "out.val",
          "sound.val", "let.val", "let.plus", "defusr.val", "pset.val",
          "sprite.val", "print.val", "lets.val"}

# (name, file, old, new, predicted MOVED set)
KNIVES = [
    ("K-MO1  the deferred code (ld e,FPERR_MISSOP -> ld e,0)", EXPR,
     "                ld      e,FPERR_MISSOP\n",
     "                ld      e,0                 ; K-MO1\n",
     set(CLOSED)),
    ("K-MO2  the fperr_to_err table byte (db 24 -> db 5)", INTERP,
     "                db      24                  ; FPERR_MISSOP (sysvars.inc, D-MISSOP): MISSING\n",
     "                db      5                   ; K-MO2\n",
     set(CLOSED)),
    ("K-MO3  the NARROWNESS: point site :807 at the new label", EXPR,
     "                cp      ')'\n"
     "                jp      nz,ev_f_err\n"
     "                inc     ix\n"
     "                ret\n",
     "                cp      ')'\n"
     "                jp      nz,ev_f_missop      ; K-MO3\n"
     "                inc     ix\n"
     "                ret\n",
     {"b.paren"}),
]


def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def hashes():
    return tuple(hashlib.sha256(r.read_bytes()).hexdigest()[:8] if r.exists()
                 else "<none>" for r in ROMS)


def moved(base, now):
    return {n for n, b, c in zip(RNAMES, base, now) if b != c}


def build():
    sh(["rm", "-rf", "build"])
    r = sh(["make", "repack-machine"])
    if r.returncode:
        print((r.stdout + r.stderr)[-1200:])
    return r.returncode == 0


def rows(out):
    d = {}
    for line in out.splitlines():
        if "zb='" in line and line.startswith("  ") and " ran " not in line:
            d[line.split()[0]] = line.split("zb='", 1)[1].split("'", 1)[0]
    return d


def main() -> int:
    orig = {EXPR: EXPR.read_text(), INTERP: INTERP.read_text()}
    verdicts = []
    try:
        print("== clean build, baseline (the SHIPPING tree) ==", flush=True)
        if not build():
            print("APPARATUS: clean build failed")
            return 3
        base_h = hashes()
        before = {}
        for pr in PROBES:
            before.update(rows(sh(pr).stdout))
        print(f"baseline roms={dict(zip(RNAMES, base_h))}")
        print(f"baseline rows={before}\n", flush=True)
        if len(before) != NROWS:
            print(f"APPARATUS: {len(before)} rows parsed, expected {NROWS}")
            return 3

        for name, src, old, new, want in KNIVES:
            base = orig[src]
            if base.count(old) != 1:
                print(f"{name}: APPARATUS -- anchor matched {base.count(old)}x")
                verdicts.append((name, False, "anchor"))
                continue
            print(f"== {name} ==", flush=True)
            src.write_text(base.replace(old, new, 1))
            if not build():
                print(f"{name}: APPARATUS -- knifed build failed")
                verdicts.append((name, False, "build failed"))
                src.write_text(base)
                continue
            h = hashes()
            mv = moved(base_h, h)
            if mv != MAIN_MOVES:
                print(f"{name}: APPARATUS -- wrong image moved: {sorted(mv)}")
                verdicts.append((name, False, f"moved {sorted(mv)}"))
                src.write_text(base)
                continue
            after = {}
            for pr in PROBES:
                after.update(rows(sh(pr).stdout))
            got = {l for l in before if before.get(l) != after.get(l)}
            print(f"  roms={dict(zip(RNAMES, h))}")
            for l in sorted(got):
                print(f"  MOVED  {l:<11} {before[l]!r} -> {after.get(l)!r}")
            ok = got == want
            print(f"  => {'EXACT' if ok else 'MISS'}  moved={sorted(got)}\n"
                  f"     want={sorted(want)}\n", flush=True)
            verdicts.append((name, ok, f"moved={sorted(got)}"))
            src.write_text(base)
    finally:
        for p, t in orig.items():
            p.write_text(t)
        build()
        assert all(p.read_text() == t for p, t in orig.items()), "not restored!"
        print(f"restored roms={dict(zip(RNAMES, hashes()))}", flush=True)

    n = sum(1 for _, ok, _ in verdicts if ok)
    print(f"\n{n}/{len(verdicts)} knife rows EXACT")
    for name, ok, why in verdicts:
        print(f"  {'EXACT' if ok else 'MISS '}  {name}   {why}")
    return 0 if n == len(verdicts) else 1


if __name__ == "__main__":
    sys.exit(main())
