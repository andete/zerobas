# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-RAMAD (disk/init.asm set_ramad): the disk ROM's INIT fills
RAMAD0-3 ($F341-$F344) with the RAM slot id and sets HOKVLD ($FB20) bit 0 on
EVERY host -- both references read them so from the Disk BASIC prompt on
(scratchpad/memman_cells*.out, scratchpad/memman_hokvld*.out: the CF-3300
83 83 83 83 and 1, the VG-8020 + NMS 1200 03 03 03 03 and 1). Before, RAMAD was
filled only when the host left RAMAD0 at $FF, and C-BIOS leaves $C9.

The slot is derived from page 3 ($A8 bits 7-6, and $FFFF's inverted subslot when
EXPTBL says that primary is expanded); IN is served by the test. The $F368 jump
table keeps the old $FF gate.
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
ROM = tp("zb_ramad_ut.rom")
SYM = tp("zb_ramad_ut.sym")
RAMAD0, HOKVLD, EXPTBL, WA_JMPTAB = 0xF341, 0xFB20, 0xFCC1, 0xF368


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # (label, RAMAD0 before, HOKVLD before, page-3 primary, expanded?, page-3 subslot,
    #  want RAMAD, want HOKVLD, want the $F368 table)
    rows = [
        ("C-BIOS host (RAMAD0 $C9), RAM in 3-0", 0xC9, 0x00, 3, True, 0, 0x83, 0x01, False),
        ("uninitialised host ($FF), RAM in 3-0", 0xFF, 0x00, 3, True, 0, 0x83, 0x01, True),
        ("RAM in 3-2, expanded", 0xC9, 0x00, 3, True, 2, 0x8B, 0x01, False),
        ("RAM in slot 3, not expanded (the VG-8020's 03)", 0xC9, 0x00, 3, False, 0, 0x03, 0x01,
         False),
        ("HOKVLD's other bits kept", 0xC9, 0x80, 3, True, 0, 0x83, 0x81, False),
    ]
    for label, ramad0, hok, prim, exp, sub, want, want_hok, want_tab in rows:
        m = Machine(ROM, SYM, rom_base=DISK_BASE)
        m.trap("install_res_print", lambda mach: None)
        m.poke(RAMAD0, bytes([ramad0, 0xC9, 0xC9, 0xC9]))
        m.poke(HOKVLD, bytes([hok]))
        m.poke(EXPTBL, bytes([0x80 if (i == prim and exp) else 0 for i in range(4)]))
        m.poke(0xFFFF, bytes([(~(sub << 6)) & 0xFF]))      # $FFFF reads inverted
        m.poke(WA_JMPTAB, bytes([0x5A]))                   # sentinel: table not built
        m.cpu.io_in = lambda port, prim=prim: (prim << 6) if port & 0xFF == 0xA8 else 0xFF
        m.call("set_ramad")
        got = bytes(m.mem[RAMAD0:RAMAD0 + 4])
        tab = m.mem[WA_JMPTAB] == 0xC3
        check(got == bytes([want] * 4) and m.mem[HOKVLD] == want_hok and tab == want_tab,
              f"{label}: RAMAD {got.hex(' ')} (want {want:02x} x4), HOKVLD "
              f"{m.mem[HOKVLD]:02X} (want {want_hok:02X}), $F368 table "
              f"{'built' if tab else 'not built'} (want {'built' if want_tab else 'not'})")

    print()
    print("ALL PASS — RAMAD0-3 and HOKVLD as both references hold them"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
