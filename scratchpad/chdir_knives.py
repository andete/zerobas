#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CHDIR knives: each cut must move EXACTLY its own rows of
probes/disk/disk_probe_dout.py, and no other.

  K-CD1  basic/print.asm: PRINT#'s mode check back to `jp nz,load_error`
         -> dir_print_in, dir_print_rnd DIVERGE
  K-CD2  basic/files.asm: INPUT#'s back to `jp nz,load_error`
         -> dir_input_out, dir_linein_out, dir_input_rnd, dir_input_app DIVERGE

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-CD1": ("basic/print.asm",
              """                cp      4
                jp      z,sid_badmode       ; RANDOM: 61 (Bad file mode)
                and     $FE                 ; S10.B: 3 (OUTPUT) or 2 (APPEND)
                cp      2                   ; must be open FOR OUTPUT
                jp      nz,err_badfnum_raise ; INPUT: 52 (Bad file number)
""",
              """                and     $FE                 ; K-CD1 CUT (restored on exit)
                cp      2
                jp      nz,load_error
""",
              {"dir_print_in", "dir_print_rnd"}),
    "K-CD2": ("basic/files.asm",
              """                cp      4
                jp      z,sid_badmode
                cp      1                   ; a channel must be open for INPUT
                jp      nz,err_badfnum_raise
""",
              """                cp      1                   ; K-CD2 CUT (restored on exit)
                jp      nz,load_error
""",
              {"dir_input_out", "dir_linein_out", "dir_input_rnd", "dir_input_app"}),
}
TMP = "/tmp/zerobas"
PROBE = "ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 -u probes/disk/disk_probe_dout.py dir_print_in dir_print_rnd dir_input_out dir_linein_out dir_input_rnd dir_input_app lofloc"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def diverging(log):
    return {m.group(1) for m in re.finditer(r"^DIVERGES (\S+)", open(log, errors="replace").read(), re.M)}


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
    sh("make repack-machine", f"{TMP}/cdknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
