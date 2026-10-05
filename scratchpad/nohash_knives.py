#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-INPUTDNOHASH / D-ASCIINUM knives: each cut must move EXACTLY its own rows
of probes/disk/disk_probe_nohash.py, and no other.

  K-NH1  basic/strvar.asm sid_filef back to `#` REQUIRED right after the comma
         -> inputd, inputd_sp, inputd_nsp, inputd_2 DIVERGE; openas* still agree
  K-NH2  basic/expr.asm: a non-letter factor goes straight to ev_f_missop again
         (the ASCII-number arm unreachable)
         -> openas, openas_ex, openas_12, openas_len DIVERGE; inputd* still agree

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-NH1": ("basic/strvar.asm",
              """                rst     $10                 ; CHRGTR: past ',' and spaces; A = (HL)
                cp      '#'
                jr      nz,sid_fnum         ; no '#': the file number starts here
                inc     hl
sid_fnum:
                call    eval                ; DE = channel f; HL advanced
""",
              """                inc     hl                  ; K-NH1 CUT (restored on exit)
                ld      a,(hl)
                cp      '#'
                jp      nz,str_eval_no
                call    inc_eval
""",
              {"inputd", "inputd_sp", "inputd_nsp", "inputd_2"}),
    "K-NH2": ("basic/expr.asm",
              "                jr      nc,ev_f_nonlet      ; an ASCII number (D-ASCIINUM), else\n",
              "                jp      nc,ev_f_missop      ; K-NH2 CUT (restored on exit)\n",
              {"openas", "openas_ex", "openas_12", "openas_len"}),
}
TMP = "/tmp/zerobas"
PROBE = "ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 -u probes/disk/disk_probe_nohash.py"


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
    sh("make repack-machine", f"{TMP}/nhknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
