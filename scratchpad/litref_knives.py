#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LITREF knives: each cut must move EXACTLY its own rows of
probes/basic/basic_probe_litref.py.

  K-LR1  the scalar LET intercept cut (let_ref)       -> scall, copyvar
  K-LR2  the array LET intercept cut (ary_let_ref)    -> aryl
  K-LR3  MID$'s copy-out cut (mid_own, D-READREF's)   -> mid: a literal now points
         at the text, so without it MID$ rewrites the program line

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-LR1": ("basic/interp.asm",
              "                call    let_ref             ; D-LITREF: a RHS in the program text is\n"
              "                jr      z,fp_stmt_done      ; stored by reference, as on the VG-8020\n",
              "                ; K-LR1 CUT (restored on exit)\n",
              {"scall", "copyvar"}),
    "K-LR2": ("basic/arrays.asm",
              "                call    ary_let_ref         ; D-LITREF: a RHS in the program text is\n"
              "                jp      z,exec_stmt         ; stored by reference (the VG-8020: `aryl`)\n",
              "                ; K-LR2 CUT (restored on exit)\n",
              {"aryl"}),
    "K-LR3": ("basic/str-engine.asm",
              "                call    mid_own             ; D-READREF: a body in the program text is\n",
              "                nop                         ; K-LR3 CUT (restored on exit)\n"
              "                nop\n                nop\n",
              {"mid"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_litref.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def diverging(log):
    return {m.group(1) for m in re.finditer(r"^DIFF (\S+)", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    fails = []
    for k, (src, old, new, want) in KNIVES.items():
        orig = open(src).read()
        if orig.count(old) != 1:
            print(f"KNIFE BROKEN: {k} anchor count {orig.count(old)} in {src}")
            return 2
        restore = lambda o=orig, f=src: open(f, "w").write(o)
        atexit.register(restore)
        try:
            open(src, "w").write(orig.replace(old, new))
            before = knife_guard.hashes()
            moved, after, rc = knife_guard.build(f"{TMP}/{k}_build.out", before)
            print(knife_guard.report(k, moved, before, after))
            if rc:
                print(f"{k}: BUILD FAILED with the cut in -- {TMP}/{k}_build.out")
                return 2
            if not moved:
                print(f"{k}: refusing to score an INERT cut")
                return 2
            sh(PROBE, f"{TMP}/{k}_probe.out")
        finally:
            restore()
            atexit.unregister(restore)
        got = diverging(f"{TMP}/{k}_probe.out")
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: diverged {sorted(got)} (want exactly {sorted(want)})")
        if not ok:
            fails.append(k)
    sh("make repack-machine", f"{TMP}/lrknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
