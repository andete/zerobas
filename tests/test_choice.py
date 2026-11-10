"""Host test for D-DSKFMT's CHOICE: HL -> the CF-3300's four-choice menu, $00-ended.

Measured first: the text a program is handed by the CF-3300's CHOICE
(scratchpad/dskfmt_stock2.out, dskfmt_stock_c2..c4.out -- 82 bytes with the $00).
"""

import os
import subprocess
import sys
from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

DISK_BASE = 0x4000
ROM = tp("zb_choice_ut.rom")
SYM = tp("zb_choice_ut.sym")
WANT = (b"\r\n1 - 1 side\r\n2 - 2 sides\r\n3 - 1 side, double track"
        b"\r\n4 - 2 sides,double track\r\n\r\n\x00")


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    cpu = m.call("choice")
    got = bytes(m.mem[cpu.hl:cpu.hl + len(WANT)])
    ok = got == WANT and len(WANT) == 82
    print(f"{'PASS' if ok else 'FAIL'}  CHOICE: HL ${cpu.hl:04X} -> {got!r}")
    print()
    print("ALL PASS — CHOICE hands over the CF-3300's menu" if ok else "1 CHECK(S) FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
