#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LOADDI / D-HOOKDI / D-BLDI knives: each cut must move EXACTLY its predicted row of
probes/disk/disk_probe_loaddi.py, judged on the zerobas column against the
uncut build's.

  K-LD1  the `ei` on hk_dpload's load path              -> load
  K-HD1  the `ei` after calbak's CALSLT (KILL's path)   -> kill
  K-HD2  the `ei` at hk_dpsave's entry                  -> save
  K-HD3  the `ei` at hk_dskf's entry                    -> dskf
  K-BL1  the `ei` after dskio_calslt's CALSLT (sub-ROM) -> bsave bload
         (ctl reads TIME with no command in between: named, not missed)

🔴 RESTORE ON EVERY EXIT: originals in memory, put back by try/finally AND
atexit; knife_guard proves the cut reached the installed ROM. A run with rows
missing refuses (D-KNIFEROWS).
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ALL = {"load", "save", "kill", "dskf", "bsave", "bload", "ctl"}
KNIVES = {
    "K-LD1": ("disk/kernel.asm",
              "                ei                          ; D-LOADDI: the hook arrives through\n",
              "                nop                         ; K-LD1 CUT\n",
              {"load"}),
    "K-HD1": ("disk/kernel.asm",
              "                call    CALSLT\n                ei\n",
              "                call    CALSLT\n                nop                         ; K-HD1 CUT\n",
              {"kill"}),
    "K-HD2": ("disk/kernel.asm",
              "                ei                          ; D-HOOKDI: the hook arrives DI (CALSLT),\n",
              "                nop                         ; K-HD2 CUT\n",
              {"save"}),
    "K-HD3": ("disk/kernel.asm",
              "                ei                          ; D-HOOKDI: the hook arrives DI (CALSLT);\n",
              "                nop                         ; K-HD3 CUT\n",
              {"dskf"}),
    "K-BL1": ("basic/fat-prim-body.inc",
              "                ei                          ; ...under DI: give the caller its EI back\n",
              "                nop                         ; K-BL1 CUT\n",
              {"bsave", "bload"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/disk/disk_probe_loaddi.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def zb(log):
    return {m.group(1): m.group(2) for m in
            re.finditer(r"^ROW ([\w-]+) CF=\[.*?\] ZB=\[(.*?)\] ", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    sh("make repack-machine", f"{TMP}/ldknife_base_build.out")
    sh(PROBE, f"{TMP}/ldknife_base.out")
    base = zb(f"{TMP}/ldknife_base.out")
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
    sh("make repack-machine", f"{TMP}/ldknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
