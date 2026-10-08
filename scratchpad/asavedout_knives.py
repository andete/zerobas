#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ASAVEDOUT knives (S10 increment 3): each cut must move EXACTLY its own rows
of probes/disk/disk_probe_asavedev.py (plain / big / crt) and
probes/disk/disk_probe_diskfull.py (eight rows; `astamp` is SAVE ,A's).

  K-AD1  ascii_save's PRDEV store cut (PRDEST alone, as before)   -> crt
  K-AD2  hco_asav's partial stamp cut (D-ASAVEFULLSTAMP's rule)   -> astamp
  K-AD3  hk_chclose_e's fat_io_close cut (no flush, no entry)     -> plain, big, crt:
         the full disk raises mid-listing, before any close, so astamp stays

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-AD1": ("basic/save.asm",
              "                ld      hl,1\n"
              "                ld      (PRDEST),hl         ; PRDEST = 1 (pchar -> the file), PRDEV = 0\n",
              "                ld      a,1                 ; K-AD1 CUT (restored on exit)\n"
              "                ld      (PRDEST),a\n",
              {"crt"}),
    "K-AD2": ("disk/kernel.asm",
              "                jr      nz, hco_tail        ; an I/O fault: leave the entry\n",
              "                jr      hco_tail            ; K-AD2 CUT (restored on exit)\n",
              {"astamp"}),
    "K-AD3": ("disk/kernel.asm",
              "                ei\n"
              "                call    fat_io_close\n"
              "                jr      hco_tail\n",
              "                ei\n"
              "                or      a                   ; K-AD3 CUT (restored on exit)\n"
              "                jr      hco_tail\n",
              {"plain", "big", "crt"}),
}
TMP = "/tmp/zerobas"
PROBE = ("ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 -u probes/disk/disk_probe_asavedev.py; "
         "ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 -u probes/disk/disk_probe_diskfull.py")


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def diverging(log):
    return {m.group(1) for m in re.finditer(r"^DIVERGES (\w+)", open(log, errors="replace").read(), re.M)}


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
    sh("make repack-machine", f"{TMP}/adknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
