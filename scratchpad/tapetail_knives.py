#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TAPETAIL knives: each cut must move EXACTLY its own rows of
probes/basic/basic_probe_tapetail.py.

  K-TT1  the tape BSAVE parses its 4th slot with the DISK parser again (,S a flag)
         -> bsavesx, bsavesbig, dbsavesbig
  K-TT2  the exec's typed check (check_expr_errors) cut
         -> dbsavebig, dbsavestr (the file is CREATED before the late raise),
            AND bsavesbig, dbsavesbig. 🎯 Predicted only the first two -- MISSED
            (tapetail_knives_miss.out): on TAPE the save completes and the
            pending 6 surfaces at the NEXT line, `6 in 40` for `6 in 30`, so the
            ERL is that row's witness.
  K-TT3  a bad CSAVE speed raises 2 instead of 5            -> csavespd
  K-TT4  SAVE "CAS:" junk back to the print-and-return path -> savejunk

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-TT1": ("basic/save.asm",
              "                call    bsave_opt4_cas      ; A = 0 none / 2 exec in DE\n",
              "                call    bsave_opt4          ; K-TT1 CUT (restored on exit)\n",
              {"bsavesx", "bsavesbig", "dbsavesbig"}),
    "K-TT2": ("basic/save.asm",
              "                call    check_expr_errors   ; string 13, past 65535 6 -- was a bare\n",
              "                nop                         ; K-TT2 CUT (restored on exit)\n"
              "                nop\n                nop\n",
              {"dbsavebig", "dbsavestr", "bsavesbig", "dbsavesbig"}),
    "K-TT3": ("basic/save.asm",
              "                jp      nz,gb_illegal       ; only ,1 / ,2: `CSAVE \"X\",3` is 5\n",
              "                jp      nz,stmt_error       ; K-TT3 CUT (restored on exit)\n",
              {"csavespd"}),
    "K-TT4": ("basic/save.asm",
              "                jp      nz,stmt_error       ; D-TAPETAIL: junk after the name is 2\n",
              "                jp      nz,load_error       ; K-TT4 CUT (restored on exit)\n",
              {"savejunk"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_tapetail.py"


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
    sh("make repack-machine", f"{TMP}/ttknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
