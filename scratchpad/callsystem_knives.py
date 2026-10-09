#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CALLSYSTEM knives: each cut must move EXACTLY its predicted rows of
probes/disk/disk_probe_callsystem.py, judged on the zerobas column against the
uncut build's.

  K-CS1  the "MSX-DOS was booted" check cut      -> nosys, nosysprg, nosysund
  K-CS2  the CLOSE of every file cut             -> dosfile
  K-CS3  the key row's blanking cut              -> dos, dosprog, dosfile, doscom
  K-CS4  the WARM seed cut (a cold DOS boot)     -> dos, dosprog, dosfile, doscom
         (its first run "moved nothing" because the probe DIED on the cold
         boot's date prompt and the rows it never printed were scored as
         unmoved -- callsystem_knives_r1.out; a run missing rows now refuses)
  K-CS5  the hook_tab row cut (unclaimed)        -> every row but dosarg
  K-CS6  the end-of-statement test cut           -> dosarg

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ALL = {"nosys", "nosysprg", "nosysund", "dosarg", "dos", "dosprog", "dosfile", "doscom"}
DOSROWS = {"dos", "dosprog", "dosfile", "doscom"}
KNIVES = {
    "K-CS1": ("disk/kernel.asm",
              "                jp      nz,hsy_err\n",
              "                nop                         ; K-CS1 CUT\n                nop\n                nop\n",
              {"nosys", "nosysprg", "nosysund"}),
    "K-CS2": ("disk/kernel.asm",
              "                ld      ix,fch_close_all\n                call    calbak              ; close every file, as the CF-3300 does\n",
              "                nop                         ; K-CS2 CUT\n",
              {"dosfile"}),
    "K-CS3": ("disk/kernel.asm",
              "                call    $0056               ; FILVRM: the bottom row, blank\n",
              "                nop                         ; K-CS3 CUT\n                nop\n                nop\n",
              DOSROWS),
    "K-CS4": ("disk/kernel.asm",
              "                ld      ($F340),a           ; MSX-DOS's cold/warm seed: WARM\n",
              "                nop                         ; K-CS4 CUT\n                nop\n                nop\n",
              DOSROWS),
    "K-CS5": ("disk/kernel.asm",
              "                dw      H_SYST, hk_system    ; D-CALLSYSTEM: CALL SYSTEM, back to MSX-DOS\n",
              "                dw      H_FORM, hk_format    ; K-CS5 CUT (H_SYST left unclaimed)\n",
              ALL - {"dosarg"}),
    "K-CS6": ("disk/kernel.asm",
              "                cp      ':'\n                jp      nz,hsy_syn\nhsy_ok:\n",
              "                cp      ':'                 ; K-CS6 CUT\n                nop\n                nop\n                nop\nhsy_ok:\n",
              {"dosarg"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/disk/disk_probe_callsystem.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def zb(log):
    return {m.group(1): m.group(2) for m in
            re.finditer(r"^ROW (\w+) CF=\[.*?\] ZB=\[(.*?)\] ", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    sh("make repack-machine", f"{TMP}/csknife_base_build.out")
    sh(PROBE, f"{TMP}/csknife_base.out")
    base = zb(f"{TMP}/csknife_base.out")
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
    sh("make repack-machine", f"{TMP}/csknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
