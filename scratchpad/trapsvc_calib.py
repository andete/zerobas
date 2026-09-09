#!/usr/bin/env python3
"""CALIBRATE trapsvc_probe.py ON KNOWN POSITIVES, before believing any zero.

`scratchpad/trapsvc_probe.py` asks whether leaving a trap handler without its
`RETURN` permanently disables that trap. 🔴 **A ROW THAT AGREES IS EVIDENCE
ABOUT A READING, NOT A MECHANISM**, and a row that reads "the trap is dead" is
worth nothing until the shape has been shown able to read "the trap is alive"
*because of the code under test*. So: re-run the SAME rows, zerobas only, with
each of two size-neutral cuts inside `trap_return_check` (basic/traps.asm) --
the routine that is the ONLY writer of both halves of the trap's re-enable.

    K-TR1  `or ZTS_ON` -> `or ZTS_SERVICING`   the auto-resume VALUE
    K-TR2  `dec (hl)`  -> `nop`                the TRAPSVC decrement

Both cut a VALUE, not a call (a deleted call fails `make deadcode` and builds no
ROM), and both are byte-for-byte the same size.

🎯 THE TWO KNIVES ARE SEPARATED BY `int.one`, WHICH EXISTS FOR THAT REASON.
K-TR1 kills the trap after ONE normal RETURN; K-TR2 only kills it once the
un-decremented count reaches TRAPSTK_MAX=6. So `int.one` (period 60 in a
90-frame window -- exactly one fire) must go red under K-TR1 and STAY GREEN
under K-TR2. If both knives moved the same set, the suite could not tell the
re-enable from the count, and would be one knife wearing two names.

Predictions are in scratchpad/trapsvc_predictions.md, written before the matrix.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "basic/traps.asm"
ROMS = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom",
        ROOT / "build/zerobas-main-eu.rom"]
RNAMES = ["basic-reloc.rom", "sub.rom", "zerobas-main-eu.rom"]
MAIN_MOVES = {"basic-reloc.rom", "zerobas-main-eu.rom"}
PROBE = ["python3", "scratchpad/trapsvc_probe.py", "--sides=zb"]

# (name, old, new, predicted MOVED rows)
KNIVES = [
    ("K-TR1  the SERVICING -> ON auto-resume value",
     "                or      ZTS_ON              ; SERVICING -> ON (auto-resume)\n",
     "                or      ZTS_SERVICING       ; K-TR1\n",
     {"int.ctl", "int.one", "int.resnext"}),
    # 🔴 RE-ANCHORED 2026-09-09. The 2026-08-23 anchor carried the comment
    # "; pop the service record", which D-CTLPOOL moved up to the `ld (TSP),de`
    # line -- so this knife matched 0 sites and the run ABORTED on the assert.
    # It was INERT-BY-ANCHOR from the day the pool landed, and only said so
    # because the assert is there. Anchor on the PAIR now, not on a comment.
    # 🎯 AND ITS PREDICTION INVERTED WITH THE ANCHOR. It used to move
    # {int.ctl, int.resnext} because an un-decremented count reached
    # TRAPSTK_MAX=6 and ct_svc_full raised ERR 7; that arm is retired with the
    # array. What is left of TRAPSVC is one gate in ex_return ("call
    # trap_return_check only when non-zero"), and a count stuck non-zero makes
    # that call happen MORE often, never less -- where the pool's pointer
    # identity TSP + TRAP_FRAME == GSP declines it. So the COUNT is no longer
    # load-bearing for these seven rows and the empty set is the prediction.
    # scratchpad/trapsvc_predictions.md carries it, written before the run.
    ("K-TR2  the TRAPSVC decrement (post-pool: the count, not the cap)",
     "                ld      hl,TRAPSVC\n                dec     (hl)\n",
     "                ld      hl,TRAPSVC\n                nop\n",
     set()),
]


def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def hashes():
    return tuple(hashlib.sha256(r.read_bytes()).hexdigest()[:8] if r.exists()
                 else "<none>" for r in ROMS)


def moved(base, now):
    return {n for n, b, c in zip(RNAMES, base, now) if b != c}


def build():
    sh(["rm", "-rf", "build"])           # 🔴 EVERY knife build, not just the first
    r = sh(["make", "repack-machine"])
    if r.returncode:
        print((r.stdout + r.stderr)[-1500:])
    return r.returncode == 0


def rows(out):
    d = {}
    for line in out.splitlines():
        if "zb='" in line and line.startswith("  ") and " ran " not in line:
            d[line.split()[0]] = line.split("zb='", 1)[1].split("'", 1)[0]
    return d


def main() -> int:
    orig = SRC.read_text()
    verdicts = []
    try:
        print("== clean build, baseline ==", flush=True)
        if not build():
            print("APPARATUS: clean build failed")
            return 3
        base_h = hashes()
        before = rows(sh(PROBE).stdout)
        print(f"baseline roms={dict(zip(RNAMES, base_h))}")
        print(f"baseline rows={before}\n", flush=True)
        if len(before) != 7:
            print(f"APPARATUS: {len(before)} rows parsed, expected 7")
            return 3

        for name, old, new, want in KNIVES:
            assert orig.count(old) == 1, f"{name}: anchor matched {orig.count(old)}x"
            print(f"== {name} ==", flush=True)
            SRC.write_text(orig.replace(old, new, 1))
            if not build():
                print(f"{name}: APPARATUS -- knifed build failed")
                verdicts.append((name, False, "build failed"))
                SRC.write_text(orig)
                continue
            h = hashes()
            mv = moved(base_h, h)
            if mv != MAIN_MOVES:            # a basic/*.asm cut moves main, not sub
                print(f"{name}: APPARATUS -- wrong image moved: {sorted(mv)}")
                verdicts.append((name, False, f"moved {sorted(mv)}"))
                SRC.write_text(orig)
                continue
            after = rows(sh(PROBE).stdout)
            got = {l for l in before if before.get(l) != after.get(l)}
            print(f"  roms={dict(zip(RNAMES, h))}")
            for l in before:
                tag = "MOVED" if l in got else "same "
                print(f"  {tag}  {l:<10} {before[l]!r} -> {after.get(l)!r}")
            ok = got == want
            print(f"  => {'EXACT' if ok else 'MISS'}  moved={sorted(got)} "
                  f"want={sorted(want)}\n", flush=True)
            verdicts.append((name, ok, f"moved={sorted(got)} want={sorted(want)}"))
            SRC.write_text(orig)
    finally:
        SRC.write_text(orig)
        build()
        assert SRC.read_text() == orig, "source not restored!"
        print(f"restored roms={dict(zip(RNAMES, hashes()))}", flush=True)

    n = sum(1 for _, ok, _ in verdicts if ok)
    print(f"\n{n}/{len(verdicts)} knife rows EXACT")
    for name, ok, why in verdicts:
        print(f"  {'EXACT' if ok else 'MISS '}  {name}   {why}")
    return 0 if n == len(verdicts) else 1


if __name__ == "__main__":
    sys.exit(main())
