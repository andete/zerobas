#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CLEARCLOSE knives: each cut must move EXACTLY its own rows of
probes/disk/disk_probe_clearclose.py, and no other.

  K-CC1  basic/clear.asm clr_files returns at once (CLEAR closes nothing again)
         -> clear500, bare, himem, twochan DIVERGE; rej*/control still agree
  K-CC2  the channels close AFTER the new pool size is stored (the ordering
         clr_h_fits exists for) -> NOTHING MOVES, and that is recorded, not
         passed off as a witness. Run 2026-10-06 expecting twochan: inert,
         while the ROM hash did move. Why: a parked OUTPUT channel's partial
         sector is flushed when it is parked and re-read when it is restaged,
         so only the ACTIVE channel's 256 B copy lands in the wrong block --
         RAM the CLEAR then resets, unless a near-floor `CLEAR n,h` puts the
         new table over the program text (the fit margin does not count the
         table). The ordering stays as correct by construction; this arm
         pins that no row sees it.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-CC1": ("basic/clear.asm",
              """                push    hl
                call    fch_close_all
                pop     hl
                ret
""",
              """                ret                         ; K-CC1 CUT (restored on exit)
""",
              {"clear500", "bare", "himem", "twochan"}),
    "K-CC2": ("basic/clear.asm",
              """                ld      (POOLSIZE),bc       ; the OLD one while the files close
                call    clr_files
""",
              """                call    clr_files           ; K-CC2 CUT: under the NEW size
                ld      (POOLSIZE),bc
""",
              set()),                     # INERT BY RECORD -- see the docstring
}
TMP = "/tmp/zerobas"
PROBE = "ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 -u probes/disk/disk_probe_clearclose.py"


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
    sh("make repack-machine", f"{TMP}/ccknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
