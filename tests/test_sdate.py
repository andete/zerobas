#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-DOSDATE: _SDATE (sdate_body), _GDATE's conversion (gdate_core)
and the FAT date word every file stamp uses (date_fat_word), disk/kernel.asm.

The DOS date is a day count since 1980-01-01 in DATE_DAYS ($F33B), where the
CF-3300 keeps it. The SDATE rows are the CF-3300's own answers
(scratchpad/sdatebad.out): A and the stored count after each call. The GDATE
rows check the reverse conversion and the day of week against Python's own
calendar, and the FAT word against the format (year - 1980) << 9 | month << 5
| day (the CF-3300 stamped 0821h for 1984-01-01 and 279Fh for 1999-12-31).
"""

import datetime
import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

DISK_BASE = 0x4000
ROM = tp("zb_sdate_ut.rom")
SYM = tp("zb_sdate_ut.sym")

# (year, month, day) -> (A, stored count) on the CF-3300; a rejected date leaves
# the count where it was (1461 here, the boot value).
SDATE_ROWS = [((2100, 1, 1), 0xFF, 1461), ((1979, 12, 31), 0xFF, 1461),
              ((1999, 13, 1), 0xFF, 1461), ((1999, 0, 1), 0xFF, 1461),
              ((1999, 1, 0), 0xFF, 1461), ((1999, 2, 29), 0xFF, 1461),
              ((1999, 4, 31), 0xFF, 1461), ((2000, 2, 29), 0x00, 7364),
              ((1980, 1, 1), 0x00, 0), ((2099, 12, 31), 0x00, 43829),
              ((1999, 12, 31), 0x00, 7304)]
EPOCH = datetime.date(1980, 1, 1)


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    days_at = m.addr("DATE_DAYS")
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    for (y, mo, d), want_a, want_days in SDATE_ROWS:
        m.poke_w(days_at, 1461)
        cpu = m.call("sdate_body", hl=y, de=(mo << 8) | d)
        got = m.mem[days_at] | m.mem[days_at + 1] << 8
        check(cpu.a == want_a and got == want_days,
              f"SDATE {y:04d}-{mo:02d}-{d:02d}: A={cpu.a:02X} days={got} "
              f"(CF-3300: A={want_a:02X} days={want_days})")

    for days in (0, 59, 60, 365, 366, 1461, 7304, 7364, 43829):
        want = EPOCH + datetime.timedelta(days=days)
        want_dow = (want.weekday() + 1) % 7          # Python: Monday 0; DOS: Sunday 0
        m.poke_w(days_at, days)
        cpu = m.call("gdate_core")
        check((cpu.hl, cpu.d, cpu.e, cpu.a) == (want.year, want.month, want.day, want_dow),
              f"GDATE days={days}: {cpu.hl}-{cpu.d:02d}-{cpu.e:02d} dow {cpu.a} "
              f"(want {want} dow {want_dow})")
        cpu = m.call("date_fat_word")
        word = (want.year - 1980) << 9 | want.month << 5 | want.day
        check(cpu.de == word, f"  FAT word {cpu.de:04X} (want {word:04X})")

    print()
    print("ALL PASS — SDATE/GDATE/date stamps keep the date as the CF-3300 does"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
