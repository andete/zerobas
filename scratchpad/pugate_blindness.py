#!/usr/bin/env python3
r"""Can `make pusing-acceptance` actually go RED?

A gate that cannot fail is not a gate, and this one is suspiciously cheap: 67
rows in ~36 s with the refcache OFF. That is explained -- the probe's boot and
step budgets are EMULATED seconds and openMSX runs well above real time -- but
"explained" is not "measured". So the ROM is broken on purpose, four ways, and
the gate has to notice each one.

  M1  never round in the fixed-point renderer      -> the `.` rows
  M2  no commas                                    -> the `,` rows
  M3  exponent path unreachable                    -> the `^^^^` rows
  M4  drop the `**` fill                           -> the `*` rows
  M0  CONTROL: a comment-only edit that changes no bytes -> must stay GREEN

⚠️ M0 IS THE ARM THAT MATTERS. If the gate reddened for M0 too it would be
reacting to the tree being touched rather than to the machine's behaviour, and
all four "successes" would mean nothing.
"""
import atexit, hashlib, os, signal, subprocess, sys

ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
P, R = "sub/punum.asm", "basic/pu-render.inc"
BAK = ".knifebak"
MUT = {
    "M1": (P, "                jr      c,pnt_comma         ; below half -> plain truncation",
           "                jr      pnt_comma           ; MUTANT: never round", True),
    "M2": (P, "                bit     7,a\n                jp      z,pnt_point",
           "                bit     7,a\n                jp      pnt_point           ; MUTANT", True),
    "M3": (P, "                jp      m,pnt_exp",
           "                                    ; MUTANT: no exponent path", True),
    "M4": (R, "                bit     2,a\n                jr      z,ptf_num_sw\n                inc     b\n                inc     b",
           "                bit     2,a\n                jr      ptf_num_sw          ; MUTANT: no `**` width\n                inc     b\n                inc     b", True),
    "M0": (P, "; --- D-PUEXP: `^^^^`, the exponent form ---",
           "; --- D-PUEXP: `^^^^`, the exponent form (control edit) ---", False),
}


def _restore(verbose=True):
    n = 0
    for f in {m[0] for m in MUT.values()}:
        if os.path.exists(f + BAK):
            os.replace(f + BAK, f); n += 1
            if verbose:
                print(f"🔴 LEFTOVER MUTANT in {f} -- restored from sidecar")
    return n


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        h.update(open(r, "rb").read() if os.path.exists(r) else b"ABSENT")
    return h.hexdigest()[:12]


def gate():
    return sh("ZEROBAS_REFCACHE=0 caffeinate -i -s make pusing-acceptance",
              "/tmp/zerobas/pgb_gate.out")


def main():
    if _restore():
        print("   (a previous run was killed; tree repaired)\n")
    atexit.register(_restore, False)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    for r in ROMS:
        if os.path.exists(r):
            os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/pgb_build.out")
    base_hash, base_rc = rom_hash(), gate()
    print(f"baseline: roms={base_hash} gate rc={base_rc} "
          f"{'GREEN' if base_rc == 0 else '🔴 RED BEFORE ANY MUTANT'}\n")
    if base_rc != 0:
        return 2
    fails = 0
    for lab, (f, find, repl, want_red) in sorted(MUT.items()):
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: SITE NOT FOUND in {f} -- NOT scored"); fails += 1; continue
        open(f + BAK, "w").write(orig)
        open(f, "w").write(orig.replace(find, repl, 1))
        for r in ROMS:
            if os.path.exists(r):
                os.remove(r)
        try:
            rc_build = sh("make repack-machine", f"/tmp/zerobas/pgb_{lab}_build.out")
            h = rom_hash()
            moved = h != base_hash
            if want_red and (rc_build != 0 or not moved):
                print(f"{lab}: INERT (rc={rc_build} roms={h}) -- NOT scored")
                fails += 1; continue
            rc = gate()
            ok = (rc != 0) if want_red else (rc == 0 and not moved)
            fails += not ok
            print(f"{lab}: roms={h} bytes-{'moved' if moved else 'same'} "
                  f"gate rc={rc} -> {'RED' if rc else 'GREEN'}   "
                  f"{'PASS' if ok else 'FAIL'}"
                  f"{'' if want_red else '   (control: must stay GREEN and byte-identical)'}")
        finally:
            open(f, "w").write(orig)
            if os.path.exists(f + BAK):
                os.remove(f + BAK)
            for r in ROMS:
                if os.path.exists(r):
                    os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/pgb_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}\n"
          f"{len(MUT) - fails}/{len(MUT)} mutants scored as intended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
