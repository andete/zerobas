#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-MACHXML — drive the machine-config race instead of waiting for it.

`tools/install-repack-machine.py` published its machine XML with
`open(out, "w").write(cfg)`. That TRUNCATES the shared path and only then
writes, so between the two instants the file every gate unit's openMSX reads at
start is EMPTY. The 2026-08-26 D-ONLIST battery caught one:

    openMSX terminated ON ITS OWN (exit 1) after 0s wall ... emulator said:
    Loading of hardware configuration failed: C-BIOS_MSX1_EU_REPACK_DISK.xml:
    Document doesn't contain mandatory root Element

🔴 A FLAKE COUNT IS NOT CAUSAL EVIDENCE -- that is exactly what the settings.xml
work established, and its repro is the shape this one copies. Two arms, the same
readers and writers, differing ONLY in how the publish lands:

    SHARED   open(out,"w").write(cfg)          -- truncate-then-write
    ATOMIC   write to a sibling temp, os.replace  -- the shipped fix

⚠️ BOTH ARMS RUN AGAINST A COPY under /tmp/zerobas. The user's real
~/.openMSX/share/machines tree is never opened for writing by this script.

The reader parses with ElementTree, whose failure on an empty document is the
same class openMSX reports ("no root element"). It does NOT need to be openMSX:
the claim under test is about the FILE, and a parser is the honest detector for
"a reader saw a document that was not whole".
"""
from __future__ import annotations

import multiprocessing as mp
import os
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402

# A body the same order of magnitude as the real config, so the write is not
# a single page that the OS might complete indivisibly by luck.
BODY = "<msxconfig>\n" + ("  <device><name>pad</name></device>\n" * 200) + "</msxconfig>\n"

ROUNDS = 400


def writer(path, atomic, rounds):
    for _ in range(rounds):
        if atomic:
            tmp = f"{path}.{os.getpid()}.tmp"
            with open(tmp, "w") as f:
                f.write(BODY)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        else:
            open(path, "w").write(BODY)


def reader(path, rounds, q):
    bad = 0
    for _ in range(rounds):
        try:
            ET.parse(path)
        except Exception:
            bad += 1
        except BaseException:
            bad += 1
    q.put(bad)


def arm(name, atomic, nwriters=3, nreaders=3):
    d = probe_tmp.tmp(f"machxml_{name}")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "MACHINE.xml")
    open(path, "w").write(BODY)          # start whole
    q = mp.Queue()
    procs = [mp.Process(target=writer, args=(path, atomic, ROUNDS))
             for _ in range(nwriters)]
    procs += [mp.Process(target=reader, args=(path, ROUNDS, q))
              for _ in range(nreaders)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    bad = sum(q.get() for _ in range(nreaders))
    total = ROUNDS * nreaders
    shutil.rmtree(d, ignore_errors=True)
    print(f"  {name:7s} {bad:4d} / {total} reads saw a document that was NOT WHOLE"
          f"   ({100.0 * bad / total:.1f} %)", flush=True)
    return bad, total


def main():
    print(f"machine-XML publish race — {ROUNDS} rounds x 3 writers x 3 readers, "
          f"under {probe_tmp.ROOT}\n")
    bad_s, tot = arm("SHARED", atomic=False)
    bad_a, _ = arm("ATOMIC", atomic=True)
    print()
    if bad_s == 0:
        print("  ⚠️ THE CONTROL ARM SAW NOTHING — this run proves nothing about "
              "either publish. Raise ROUNDS or the writer count and re-run; a "
              "0-vs-0 result is the ALL-CONVERGED shape, not a pass.")
        return 2
    if bad_a != 0:
        print(f"  🔴 THE ATOMIC ARM STILL TORE ({bad_a}) — os.replace did not "
              f"close the window. Do NOT ship the fix on this evidence.")
        return 1
    print(f"  ✅ SHARED {bad_s}/{tot} torn, ATOMIC 0/{tot}. The window is the "
          f"truncate-then-write, and os.replace removes it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
