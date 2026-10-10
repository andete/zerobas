#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-WCACHE knives: each cut must move EXACTLY its predicted rows of
probes/disk/disk_probe_wcache.py, judged on the zerobas column against the uncut
build's.

  K-WC1  fat_total_clusters re-reads the boot sector per call (W1 undone)
         -> zb-reads; content and writes unmoved
  K-WC2  disk.rom's hot FAT write always reads (W2 undone) -> zb-reads AND
         zb-writes since W3a: the always-read path also flushes the held sector
  K-WC3  the deferral never asked for (W3a undone)            -> zb-writes
  K-WC4  a deferred FAT sector NOT flushed before another one loads -> fat-x
         (the last cluster's mark is lost: the chain ends FREE; the content
         still reads back -- readers stop at the file size)

🔴 RESTORE ON EVERY EXIT: originals in memory, put back by try/finally AND
atexit; knife_guard proves the cut reached the installed ROM. A run with rows
missing refuses (D-KNIFEROWS).
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ALL = {"content", "content-x", "fat-x", "zb-reads", "zb-writes"}
KNIVES = {
    "K-WC1": ("basic/fat-prim-body.inc",
              "                ld      de, (FAT_TOTCLUS)\n                or      a\n                ret\n",
              "                push    hl                  ; K-WC1 CUT\n"
              "                ld      de, 0\n                ld      hl, FAT_MBUF\n"
              "                call    read_sector\n                pop     hl\n"
              "                ld      de, (FAT_TOTCLUS)\n                or      a\n                ret\n",
              {"zb-reads"}),
    "K-WC2": ("disk/fat.asm",
              "                jp      z, fwe_have         ; already loaded: no read\n",
              "                nop                         ; K-WC2 CUT\n                nop\n                nop\n",
              {"zb-reads", "zb-writes"}),
    "K-WC3": ("basic/fat-prim-body.inc",
              "                ld      a, 1                ; D-WCACHE W3a: a chain EXTENSION -- the\n",
              "                ld      a, 0                ; K-WC3 CUT\n",
              {"zb-writes"}),
    "K-WC4": ("disk/fat.asm",
              "                call    z, fat_write_buf_allfats    ; out FIRST (it clears the flag)\n",
              "                nop                         ; K-WC4 CUT\n                nop\n                nop\n",
              {"fat-x"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/disk/disk_probe_wcache.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def zb(log):
    return {m.group(1): m.group(2) for m in
            re.finditer(r"^ROW ([\w-]+) CF=\[.*?\] ZB=\[(.*?)\] ", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    sh("make repack-machine", f"{TMP}/wcknife_base_build.out")
    sh(PROBE, f"{TMP}/wcknife_base.out")
    base = zb(f"{TMP}/wcknife_base.out")
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
    sh("make repack-machine", f"{TMP}/wcknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
