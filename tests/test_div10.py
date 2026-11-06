# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: div10 (basic/float-arith.asm) and its sub-ROM clone (sub/detok.asm).

HL = HL / 10, A = HL mod 10 -- for EVERY dividend 0..65535, both copies.
D-TRAPCOST (2026-11-06) gave a dividend under 256 an 8-step path beside the
16-step one; the two must agree with Python everywhere, and at 255 / 256 above all.
Number printing, LIST's line numbers and the integer widen all divide here.
"""
import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

MAIN_ROM, MAIN_SYM = tp("zb_div10.rom"), tp("zb_div10.sym")
SUB_ROM, SUB_SYM = tp("zb_div10_sub.rom"), tp("zb_div10_sub.sym")


def run():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), MAIN_ROM, MAIN_SYM],
                   check=True, capture_output=True)
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)
    fails = 0
    for label, m in (("main", Machine(MAIN_ROM, MAIN_SYM, rom_base=0x2781)),
                     ("sub ", Machine(SUB_ROM, SUB_SYM, rom_base=0x0000))):
        bad = []
        for n in range(65536):
            cpu = m.call("div10", hl=n)
            if cpu.hl != n // 10 or cpu.a != n % 10:
                bad.append((n, cpu.hl, cpu.a))
                if len(bad) > 3:
                    break
        ok = not bad
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  div10 ({label}): every dividend 0..65535"
              + ("" if ok else f" {bad}"))
    print()
    print("ALL PASS -- div10, both copies" if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
