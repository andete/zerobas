# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM _GDATE handler ($553C) return contract, no emulator.

The MSX-DOS-1 kernel BDOS dispatcher routes _GDATE ($2A) to the canonical
page-1 disk-ROM address $553C (gdate_handler). On a clock-less MSX1 (CF-3300,
C-BIOS) _GDATE returns the default system date, so our handler returns a
constant. This test calls it by label with junk inputs and asserts the exact
return registers + the $F306 re-entrancy-flag clear.

Oracle basis (every expected value is independent of the ROM's own output):
  - The date 1984-01-01 (Sunday) is the *documented* MSX-DOS-1 clock-less
    default (MSX-DOS system date epoch). HL=year=1984=$07C0, D=month=$01,
    E=day=$01, A=day-of-week=$00 (Sunday) are that documented contract — like
    test_tape's documented-FSK basis, NOT a copied ROM listing.
  - The return register/flag image (HL=$07C0, DE=$0101, BC=$0000, A=$00,
    F=$44) is CORROBORATED by the black-box capture of the stock CF-3300 at the
    GDATE return $CC04 (disk_probe_diff capture; docs/tier2-gdate-spec.md §4) —
    like test_getdpb's CF-3300 oracle. `xor a` is what leaves F=$44 (Z|P/V).
  - $F306 is the dispatcher re-entrancy flag the kernel sets to 1 on BDOS entry
    ($D831); stock's _GDATE clears it, so the handler must leave $F306=0.
CLEAN-ROOM: derived from the documented _GDATE contract + black-box observation;
no stock-ROM disassembly. The handler is this project's own code (kernel.asm).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
DISK_BASE = 0x4000

ROM = "/tmp/zb_gdate_ut.rom"
SYM = "/tmp/zb_gdate_ut.sym"

# Expected _GDATE return image (the $CC04 contract, docs/tier2-gdate-spec.md §4).
EXPECT = {"hl": 0x07C0, "de": 0x0101, "bc": 0x0000, "a": 0x00, "f": 0x44}
F306 = 0xF306


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    m.poke(F306, 0x01)                         # kernel set it to 1 on BDOS entry

    # call with junk inputs — the contract ignores them, must overwrite.
    cpu = m.call("gdate_handler", hl=0xFFFF, de=0xFFFF, bc=0xFFFF, a=0xFF)

    fails = 0
    for reg, want in EXPECT.items():
        got = getattr(cpu, reg)
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {reg.upper():<2} {got:#06x} "
              f"{'==' if ok else '!='} {want:#06x}")

    got306 = m.mem[F306]
    ok = got306 == 0x00
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  $F306 re-entrancy flag cleared ({got306:#04x})")

    print()
    print("ALL PASS — _GDATE returns the 1984-01-01 default (CF-3300 $CC04 contract)"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
