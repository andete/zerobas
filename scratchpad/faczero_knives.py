#!/usr/bin/env python3
r"""D-FACZERO knives — one arm per zero exit, and one of them exists to find a hole.

Every arm hashes the ROM: "moved 0 rows" is what an inert knife and a
legitimately-empty arm look like alike.
[[a-knife-can-be-inert-because-the-build-did-not-happen]]
"""
import hashlib, os, subprocess, sys

ROM = "build/zerobas-main-eu.rom"
CALL_S = "                call    fac_zero_mantissa   ; D-FACZERO: and the mantissa too\n"
CALL_D = "                call    fac_zero_mantissa   ; D-FACZERO: ...and its mantissa.\n"
CALL_V = "                call    fac_zero_mantissa   ; D-FACZERO: an UNSET variable reads back as\n"

ARMS = {
    "K-FZ1": ("basic/float-arith.asm", CALL_S, "",
              {"s.zero", "z.lit", "z.calc", "z.mul", "z.int", "z.reassign",
               "z.arr", "z.read", "z.defsng"}),
    "K-FZ2": ("basic/float-arith.asm", CALL_D, "",
              {"d.zero", "z.dcalc", "z.dlit"}),
    "K-FZ3": ("basic/vars.asm", CALL_V, "", {"z.unset", "z.dunset"}),
}


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    return hashlib.sha1(open(ROM, "rb").read()).hexdigest()[:12] if os.path.exists(ROM) else "ABSENT"


def diff_rows(path):
    for line in open(path):
        if line.startswith("DIFF:"):
            return set(line.split()[2:])
    return None


def main():
    sh("make repack-machine", "/tmp/zerobas/fz_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 scratchpad/mkfloat_scout.py", "/tmp/zerobas/fz_base.out")
    base = diff_rows("/tmp/zerobas/fz_base.out")
    print(f"base ROM {base_hash}   base DIFF rows: {sorted(base) if base is not None else '<UNREADABLE>'}\n")
    for lab, (f, find, repl, want) in ARMS.items():
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: PLANT SITE NOT FOUND in {f} -- arm skipped, NOT green")
            continue
        open(f, "w").write(orig.replace(find, repl, 1))
        try:
            rc = sh("make repack-machine", f"/tmp/zerobas/fz_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} rom={h} (base {base_hash}); verdict DISCARDED")
                continue
            sh("caffeinate -i -s python3 scratchpad/mkfloat_scout.py", f"/tmp/zerobas/fz_{lab}.out")
            got = diff_rows(f"/tmp/zerobas/fz_{lab}.out")
            if got is None:
                print(f"{lab}: rom={h} <UNREADABLE probe output>"); continue
            moved = got - base
            print(f"{lab}: rom={h}  moved={sorted(moved) or '<none>'}  "
                  f"want={sorted(want) or '<none>'}  {'PASS' if moved == want else 'FAIL'}")
        finally:
            open(f, "w").write(orig)
    sh("make repack-machine", "/tmp/zerobas/fz_restore.out")
    print(f"\nrestored ROM {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
