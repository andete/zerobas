#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-NODISKVERBS knives: each cut must move EXACTLY its own rows of
probes/basic/basic_probe_nodiskverbs.py.

  K-NV1  fname_dev (LOAD / RUN / SAVE / BSAVE) skips the diskless rule
         -> save, bsave, loadd, rund, saved, bsaved
  K-NV2  MERGE skips it                       -> merged
  K-NV3  the BLOAD tenant skips it            -> bloadd
  K-NV4  a tape SAVE returns instead of ending the run -> save, savecas

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-NV1": ("basic/save.asm",
              "                jp      nodisk_dev          ; D-NODISKVERBS: no disk -> the tape arm\n",
              "                ret                         ; K-NV1 CUT (restored on exit)\n",
              {"save", "bsave", "loadd", "rund", "saved", "bsaved"}),
    "K-NV2": ("basic/files.asm",
              "                call    nodisk_dev          ; D-NODISKVERBS: no disk -> the tape, `d:` 56\n"
              "                jr      z,merge_cas         ; (was `load error`)\n",
              "                ; K-NV2 CUT (restored on exit)\n",
              {"merged"}),
    "K-NV3": ("basic/bload-body.inc",
              "                jr      nz,isd_disk\n",
              "                jr      isd_disk            ; K-NV3 CUT (restored on exit)\n",
              {"bloadd"}),
    "K-NV4": ("basic/save.asm",
              "                jp      end_line_end\n",
              "                ret                         ; K-NV4 CUT (restored on exit)\n",
              {"save", "savecas"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_nodiskverbs.py"


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
    sh("make repack-machine", f"{TMP}/nvknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
