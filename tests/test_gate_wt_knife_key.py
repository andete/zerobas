#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""tools/gate_wt.py's knife_key (D-GATEKNIFESKIP): a gate skips the knives and the tape corpus
when this key matches the last passing run. A skip that fires when it should not removes a
safety net silently, so the key must move for ANY change to what the knives read:
  - one byte of a built ROM image;
  - a .sym file (the knives place their cuts by symbol);
  - the knife / corpus harness;
and it must REFUSE an empty build rather than key a skip on nothing.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import gate_wt as G  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- tempfile under the project's temp root


def fake_tree(root):
    os.makedirs(os.path.join(root, "build"))
    for f, b in (("build/zerobas-main-eu.rom", b"\x01" * 64), ("build/disk.rom", b"\x02" * 64),
                 ("build/basic-reloc.sym", b"LBL EQU 04000H\n")):
        open(os.path.join(root, f), "wb").write(b)
    for f in G.KNIFE_HARNESS:
        os.makedirs(os.path.dirname(os.path.join(root, f)), exist_ok=True)
        open(os.path.join(root, f), "w").write(f"# {f}\n")


def main():
    fails = []

    def check(ok, msg):
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")
        if not ok:
            fails.append(msg)

    with tempfile.TemporaryDirectory() as td:
        fake_tree(td)
        k0 = G.knife_key(td)
        check(k0 == G.knife_key(td), "the key is stable for the same tree")
        rom = os.path.join(td, "build", "disk.rom")
        b = bytearray(open(rom, "rb").read())
        b[17] ^= 1
        open(rom, "wb").write(bytes(b))
        k1 = G.knife_key(td)
        check(k1 != k0, "one ROM byte changes the key")
        open(os.path.join(td, "build", "basic-reloc.sym"), "a").write("NEW EQU 04001H\n")
        k2 = G.knife_key(td)
        check(k2 != k1, "a .sym change changes the key")
        open(os.path.join(td, G.KNIFE_HARNESS[0]), "a").write("# edited\n")
        check(G.knife_key(td) != k2, "a knife-harness edit changes the key")
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "build"))
        try:
            G.knife_key(td)
            check(False, "an empty build REFUSES (no key on nothing)")
        except SystemExit:
            check(True, "an empty build REFUSES (no key on nothing)")
    print()
    print(f"{len(fails)} CHECK(S) FAILED" if fails else "ALL CHECKS PASSED")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
