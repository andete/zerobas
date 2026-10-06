#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LINTTBWRAP knife: build WITHOUT cbios-repack/linttb-scroll.patch (the
repack's old SHA-1 and island 1 back at $1AF2) and read ours again.

  K-LTW  -> screditor's x.botwrap reads 1 (only the wrapped line's first row
            runs) and scratchpad/linttbwrap_probe.py's flags read `1 1 1`
            (the wrapped row's "continues" mark is lost); and
            scratchpad/linttbstale_probe.py (D-LINTTBSTALE) is read too: its
            wrap_low reads A = 0 there (a stale zero glues the row above), 1 on
            the patched build and on the VG-8020; wrap_off / wrap_mid read 1
            either way (they cannot reach the defect)

A three-file cut, so not kwknife's one-anchor shape: originals held in memory
and put back by try/finally AND atexit; knife_guard proves the cut reached the
installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
CUTS = [
    ("tools/build_repacked_cbios.py",
     '    os.path.join(REPO, "cbios-repack", "linttb-scroll.patch"),\n', ""),
    ("tools/build_repacked_cbios.py",
     'REPACKED_SHA1 = "f0e3e80512bc5c70d968ca868241a3f18dd838ce"',
     'REPACKED_SHA1 = "daeac96df7d5c9ae239000832b1d7e24b9a25f7d"'),
    ("tools/build_mainrom.py", "(0x1AF5, 0x1BBF)", "(0x1AF2, 0x1BBF)"),
    ("basic/islands.asm", "                org     $1AF5\n", "                org     $1AF2\n"),
]
TMP = "/tmp/zerobas"


def main():
    os.makedirs(TMP, exist_ok=True)
    orig = {}
    for f, old, _ in CUTS:
        orig.setdefault(f, open(f).read())
        if orig[f].count(old) != 1 and open(f).read().count(old) != 1:
            print(f"KNIFE BROKEN: anchor in {f}: {old[:50]!r}")
            return 2

    def restore():
        for f, text in orig.items():
            open(f, "w").write(text)
    atexit.register(restore)
    try:
        for f, old, new in CUTS:
            t = open(f).read()
            assert t.count(old) == 1, (f, old)
            open(f, "w").write(t.replace(old, new))
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build(f"{TMP}/ltw_build.out", before)
        print(knife_guard.report("K-LTW", moved, before, after))
        if rc or not moved:
            print("K-LTW: build failed or inert -- refusing to score")
            return 2
        sub = subprocess.run(["python3", "-u", "-c", """
import sys; sys.path.insert(0,'probes/basic'); sys.path.insert(0,'probes/lib')
import basic_probe_screditor as m, probe_sides
m.CASES=[c for c in m.CASES if c[0]=='x.botwrap']
cfg=probe_sides.sides('zb')
print('x.botwrap', m.read('zb', cfg['zb']))
"""], capture_output=True, text=True, timeout=600)
        print(sub.stdout.strip().splitlines()[0] if sub.stdout.strip() else sub.stderr[-300:])
        sub = subprocess.run(["python3", "-u", "scratchpad/linttbwrap_probe.py"],
                             capture_output=True, text=True, timeout=600)
        print("\n".join(l for l in sub.stdout.splitlines() if "NODISK" in l))
        # D-LINTTBSTALE's probe too: does the unpatched scroll leave a STALE
        # zero above a later row (the item's mechanism)?
        sub = subprocess.run(["python3", "-u", "scratchpad/linttbstale_probe.py"],
                             capture_output=True, text=True, timeout=900)
        print("\n".join(l for l in sub.stdout.splitlines() if "NODISK" in l))
    finally:
        restore()
        atexit.unregister(restore)
    subprocess.call("make repack-machine > /tmp/zerobas/ltw_restore.out 2>&1", shell=True)
    print("restored:", knife_guard.hashes())
    return 0


if __name__ == "__main__":
    sys.exit(main())
