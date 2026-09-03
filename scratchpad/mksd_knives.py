#!/usr/bin/env python3
r"""D-MKSD knives — four arms, aimed at the PARAMETERISATION rather than the presence.

Deleting a keyword-table entry proves only that the verb is wired up, which the
32 green rows already say. These arms attack the two claims the shared bodies
actually rest on:

  * that the width threaded through `C` really drives the length check, and
  * that "the width IS the FACTYP code" is load-bearing and not a coincidence.

PREDICTIONS, RECORDED BEFORE THE RUN:
  K-MK1  length check `cp c` -> `cp 2`      x.cvsshort, x.cvdmks
         (round 1 also predicted x.cvsempty and was WRONG: an empty string
          fails `cp 2` as well, so no rule separates them there)
  K-MK2  MKS$ packs as DOUBLE not single    a.mksdbl
  K-MK3  drop the CVD keyword-table entry   r.cvd, r.third, a.mkdint, x.cvdmks
  K-MK4  ev_cv_float types everything 4     r.third  ONLY
         🎯 THE NARROWEST PREDICTION IN THE SET, AND THE REASONING IS THE POINT:
         forcing FACTYP=4 still COPIES C bytes, so `CVD(MKD$(1.5))` and
         `CVD(MKD$(7))` print the SAME either way -- 1.5 and 7 need no more than
         a single's 3 mantissa bytes. Only 1/3 does. And `x.cvdmks` errors at the
         length check, before any type is set, so it cannot move.
         ⚠️ Round 1 said this arm moved four rows and I ADOPTED THAT AS THE
         PREDICTION. It was contaminated (see the restore note below); the four
         rows were K-MK3's. A prediction inherited from a bad measurement is not
         a prediction.

K-MK2's prediction is deliberately NARROW and that is the interesting part:
`MKS$(1.5)` packs to `65 21 0 0` under EITHER rounding, because only the first
four bytes are copied and 1.5 is exact in both. Only a value that needs the
6-digit round -- `a.mksdbl`, `1.23456789#` -> `1.23457` -- can separate them. If
more rows move than that, my model of the coercion is wrong.

Every arm hashes the ROM: "moved 0 rows" is what an inert knife and a
legitimately-empty arm look like alike.
[[a-knife-can-be-inert-because-the-build-did-not-happen]]
"""
import hashlib, os, subprocess, sys, time

# 🔴 BOTH ROMS, BECAUSE THE KEYWORD TABLE IS NOT IN THE MAIN ONE. K-MK3 edits
# basic/kwtable.inc, which `sub/sub.asm` is the SOLE includer of -- so hashing
# only the main ROM reported that arm INERT (correctly refusing to believe it,
# but for the wrong reason). A guard that watches the wrong artefact is the same
# blindness it exists to prevent.
ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
ARMS = {
    "K-MK1": ("basic/expr.asm",
              "                cp      c                   ; fewer bytes than the width -> deferred",
              "                cp      2                   ; KNIFE",
              # 🔴 `x.cvsempty` WAS PREDICTED AND CANNOT WITNESS THIS ARM: an
              # EMPTY string has length 0, which fails the weakened `cp 2` check
              # too, so both rules agree on it. Corrected after round 1 rather
              # than left as a standing wrong expectation.
              {"x.cvsshort", "x.cvdmks"}),
    "K-MK2": ("basic/strvar.asm",
              "                call    round_single_and_pack   ; 6-digit half-up round -> FAC as single",
              "                call    round_and_finalize      ; KNIFE",
              {"a.mksdbl"}),
    "K-MK3": ("basic/kwtable.inc",
              '                db      3,"CVD",2,PEEK_PREFIX,CVD_TOKEN\n',
              "",
              {"r.cvd", "r.third", "a.mkdint", "x.cvdmks"}),
    "K-MK4": ("basic/expr.asm",
              "                ld      a,c\n                ld      (FACTYP),a\n                ld      b,0",
              "                ld      a,4\n                ld      (FACTYP),a\n                ld      b,0",
              {"r.third"}),
}


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        h.update(open(r, "rb").read() if os.path.exists(r) else b"ABSENT")
    return h.hexdigest()[:12]


def diff_rows(path):
    for line in open(path):
        if line.startswith("DIFF (cf3300 vs zb):"):
            return set(line.split()[5:])   # [4] is the "n/32" COUNT, not a label
    return None


def main():
    only = set(sys.argv[1:]) or None
    sh("make repack-machine", "/tmp/zerobas/mk_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 scratchpad/mksd_probe.py", "/tmp/zerobas/mk_base.out")
    base = diff_rows("/tmp/zerobas/mk_base.out")
    print(f"base ROM {base_hash}   base DIFF: {sorted(base) if base is not None else '<UNREADABLE>'}\n")
    for lab, (f, find, repl, want) in ARMS.items():
        if only and lab not in only:
            continue
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: PLANT SITE NOT FOUND in {f} -- arm skipped, NOT green")
            continue
        open(f, "w").write(orig.replace(find, repl, 1))
        try:
            rc = sh("make repack-machine", f"/tmp/zerobas/mk_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} rom={h} (base {base_hash}); verdict DISCARDED")
                continue
            sh("caffeinate -i -s python3 scratchpad/mksd_probe.py", f"/tmp/zerobas/mk_{lab}.out")
            got = diff_rows(f"/tmp/zerobas/mk_{lab}.out")
            if got is None:
                print(f"{lab}: rom={h} <UNREADABLE probe output>"); continue
            moved = got - base
            print(f"{lab}: rom={h}  moved={sorted(moved) or '<none>'}  "
                  f"want={sorted(want)}  {'PASS' if moved == want else 'FAIL'}")
        finally:
            open(f, "w").write(orig)
            # 🔴 AND MAKE THE RESTORE VISIBLE TO `make`. Round 1 of this set had
            # K-MK4 report K-MK3'S ROW SET, because the INERT fast-path skipped
            # the probe and that whole arm finished inside make's 1-SECOND mtime
            # resolution: the restored kwtable.inc was not strictly newer than
            # the sub.rom built from the knifed copy, so the next arm built
            # against a STALE sub-ROM and measured the previous plant. The
            # guard's own fast path is what created the contamination.
            os.utime(f, (time.time() + 1, time.time() + 1))
    sh("make repack-machine", "/tmp/zerobas/mk_restore.out")
    print(f"\nrestored ROM {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
