#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DIMRESERVE S2 knives (the arithmetic climber): each cut must move EXACTLY
its predicted rows of probes/basic/basic_probe_prec.py, judged on the zerobas
column against the uncut build's.

  K-CL2  float-style rhs at the SAME level (no `inc a`)   -> sub3 mix div3 pow3
         (mul3 2*(3/4) = (2*3)/4 = 1.5 either way: named, not missed)
  K-CL3  int-style rhs at the same level                  -> idiv3 modchain
  K-CL4  the "looser than allowed" stop cut               -> sub3 mix div3 pow3
                                                             idiv3 idivmod modchain

🔴 RESTORE ON EVERY EXIT: originals in memory, put back by try/finally AND
atexit; knife_guard proves the cut reached the installed ROM. A run with rows
missing refuses (D-KNIFEROWS).
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ALL = {"sub3", "mix", "div3", "pow3", "idiv3", "mul3", "addmul", "mulpow", "negpow",
       "modmul", "idivmod", "modchain"}
KNIVES = {
    "K-CL2": ("basic/expr.asm",
              "                inc     a\n                ld      c,a                 ; C = the rhs's minimum: TIGHTER only\n",
              "                nop                         ; K-CL2 CUT\n                ld      c,a\n",
              {"sub3", "mix", "div3", "pow3"}),
    "K-CL3": ("basic/expr.asm",
              "                inc     a\n                ld      c,a                 ; C = the rhs's minimum (again)\n",
              "                nop                         ; K-CL3 CUT\n                ld      c,a\n",
              {"idiv3", "modchain"}),
    "K-CL4": ("basic/expr.asm",
              "                jr      c,evk_done          ; looser than allowed: the caller's to take\n",
              "                nop                         ; K-CL4 CUT\n                nop\n",
              {"sub3", "mix", "div3", "pow3", "idiv3", "idivmod", "modchain"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_prec.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def zb(log):
    return {m.group(1): m.group(2) for m in
            re.finditer(r"^ROW (\w+) VG=\[.*?\] ZB=\[(.*?)\] ", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    sh("make repack-machine", f"{TMP}/clknife_base_build.out")
    sh(PROBE, f"{TMP}/clknife_base.out")
    base = zb(f"{TMP}/clknife_base.out")
    if set(base) != ALL:
        print(f"BASELINE BROKEN: rows {sorted(base)}")
        return 2
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
        cut = zb(f"{TMP}/{k}_probe.out")
        if set(cut) != ALL:
            print(f"{k}: KNIFE RUN INCOMPLETE -- rows {sorted(ALL - set(cut))} never printed; "
                  f"refusing to score them as unmoved ({TMP}/{k}_probe.out)")
            return 2
        got = {r for r, v in cut.items() if v != base.get(r)}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {sorted(got)} (want exactly {sorted(want)})")
        if not ok:
            fails.append(k)
    sh("make repack-machine", f"{TMP}/clknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
