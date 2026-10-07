#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BLOADOFS knives: each cut must move EXACTLY its own rows of
probes/disk/disk_probe_bloadofs.py.

  K-BO1  basic/bload-body.inc bl_apply_ofs reads 0 instead of BL_OFS
         -> ram, exec, wrap, vram, dec DIVERGE (zero / big / str / order do not)
  K-BO2  basic/bload.asm pcr_bload's check_expr_errors cut
         -> order alone DIVERGES. 🎯 First predicted {str, order, big} -- MISSED
         (bloadofs_knives_miss.out): without the check the pending FPERR is
         still raised later in the statement, so `big` / `str` read 6 / 13
         anyway -- AFTER the load. Only `order` (a missing file) shows the
         check is what raises BEFORE the disk is touched.
  K-BO3  bl_apply_ofs's EXEC relocation cut -> exec alone DIVERGES

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-BO1": ("basic/bload-body.inc",
              "                ld      de,(BL_OFS)\n",
              "                ld      de,0                ; K-BO1 CUT (restored on exit)\n"
              "                nop\n",
              {"ram", "exec", "wrap", "vram", "dec"}),
    "K-BO2": ("basic/bload.asm",
              "                call    check_expr_errors   ; a string 13, past 65535 6\n",
              "                nop                         ; K-BO2 CUT (restored on exit)\n"
              "                nop\n                nop\n",
              {"order"}),
    "K-BO3": ("basic/bload-body.inc",
              "                ld      hl,(EXECPTR)\n                add     hl,de\n                ld      (EXECPTR),hl\n",
              "                nop                         ; K-BO3 CUT (restored on exit)\n",
              {"exec"}),
}
TMP = "/tmp/zerobas"
PROBE = "ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 -u probes/disk/disk_probe_bloadofs.py"


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
    sh("make repack-machine", f"{TMP}/boknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
