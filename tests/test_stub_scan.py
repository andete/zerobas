#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""test_stub_scan -- D-BIOSRUNG: tools/stub_scan.py names both stub shapes, ignores a real
body, and REFUSES on a degenerate image instead of reporting "0 stubs".

Synthetic images only: a jump table of `jp` for all 108 entries into a body area, where
three entries land on the print_debug shape, one on a bare `ret`, the rest on a body
that is neither.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- tempfile under the project's temp root
import stub_scan  # noqa: E402
from entry_table import BIOS  # noqa: E402

PD = 0x7000          # the one print_debug routine the stub shape calls


def image(stub_pd=(), stub_ret=(), second_pd=False):
    rom = bytearray(0x8000)
    body = 0x4000
    for addr, name in BIOS:
        if addr == 0x0000:                       # CHKRAM: `di / jp`, as C-BIOS's reset
            rom[0:4] = bytes([0xF3, 0xC3, body & 0xFF, body >> 8])
        else:
            rom[addr:addr + 3] = bytes([0xC3, body & 0xFF, body >> 8])
        if name in stub_pd:
            pd = PD + (0x10 if second_pd and name == stub_pd[-1] else 0)
            rom[body:body + 9] = bytes([0xE5, 0xF5, 0x21, 0x00, 0x60, 0xCD, pd & 0xFF, pd >> 8, 0xC9])
        elif name in stub_ret:
            rom[body] = 0xC9
        else:
            rom[body:body + 3] = bytes([0x3E, 0x01, 0xC9])   # ld a,1 / ret: a real body
        body += 16
    return bytes(rom)


def run(img):
    fd, path = tempfile.mkstemp(suffix=".rom")
    os.write(fd, img)
    os.close(fd)
    try:
        return stub_scan.scan(path)
    finally:
        os.unlink(path)


def main():
    fails = 0

    def check(cond, msg):
        nonlocal fails
        print(("PASS  " if cond else "FAIL  ") + msg)
        fails += 0 if cond else 1

    r = run(image(stub_pd=("STRTMS", "FNKSB", "CALBAS"), stub_ret=("PNTINI",)))
    got = {v["name"]: v["kind"] for v in r.values() if v["kind"]}
    check(got == {"STRTMS": "print_debug", "FNKSB": "print_debug", "CALBAS": "print_debug",
                  "PNTINI": "bare ret"}, f"both shapes named, nothing else: {got}")
    check(len(r) == len(BIOS), f"all {len(BIOS)} entries scanned (CHKRAM's `di / jp` followed)")
    check(not any(v["kind"] for v in run(image()).values()), "a clean image: no stub")
    for label, img in (("an all-zero image", bytes(0x8000)),
                       ("a short image", image()[:0x4000]),
                       ("print_debug shapes calling two routines",
                        image(stub_pd=("STRTMS", "FNKSB"), second_pd=True))):
        try:
            run(img)
            check(False, f"{label}: answered instead of refusing")
        except stub_scan.ScanRefused as e:
            check(True, f"{label}: refused ({str(e)[:50]}...)")
    print(f"{'PASS' if not fails else 'FAIL'}  test_stub_scan: {fails} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
