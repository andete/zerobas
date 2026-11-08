#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""tools/entry_table.py (D-ENTRYTIERS): the BDOS rows' mechanical parts.

Each row is only as good as two rules, so both are pinned here:
  (a) scan_asm reads the function number from the last `ld c, N` before a BDOS
      call -- a number in any of the three spellings, the file's own `equ`, or
      the published function name (lstoutx.asm loads `LSTOUT` and read NOT
      MEASURED until the name was resolved);
  (b) a script REACHES a probe only in CODE: diskbasic_acceptance.py's docstring
      names disk_bdos_acceptance.py, and that mention credited every bdosx probe
      to diskbasic-acceptance and callsystem-acceptance in the first prototype.
And a third: the table never drops a function -- all 49 numbers, every real
MSX-DOS 1 name present, unused numbers marked as such.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import entry_table as E  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- tempfile under the project's temp root

fails = 0


def check(ok, msg):
    global fails
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {msg}")


src = """
MYFN    equ     $1A
        ld      c, $0F          ; hex
        call    BDOS
        ld      c, 16           ; decimal
        call    $0005
        ld      c, 22h
        call    BDOS
        ld      c, MYFN         ; the file's own equ
        call    BDOS
        ld      c, LSTOUT       ; a published name
        call    BDOS
        ld      c, $09
        ld      de, msg         ; not the C load: the last `ld c` still counts
        call    $F37D
;       ld      c, $30          ; a comment: not a load
        call    BDOS            ; -> still $09
"""
with tempfile.NamedTemporaryFile("w", suffix=".asm", delete=False) as f:
    f.write(src)
got = E.scan_asm(f.name)
os.unlink(f.name)
check(got == {0x0F: 1, 0x10: 1, 0x22: 1, 0x1A: 1, 0x05: 1, 0x09: 2},
      f"(a) scan_asm: numbers, equ, published name, last load wins: {dict(got)}")

code = E._scripts()
check("disk_bdos_acceptance.py" not in code.get("diskbasic_acceptance.py", ""),
      "(b) a docstring mention is not a reach (diskbasic_acceptance.py)")
check("build_bdosx_disk.py" in code.get("disk_bdos_acceptance.py", ""),
      "(b) a code mention IS a reach (disk_bdos_acceptance.py -> build_bdosx_disk.py)")

rs, _ = E.rows()
check([r["num"] for r in rs] == list(range(0x31)), "(c) every number $00-$30 has a row")
names = {r["name"] for r in rs}
check(all(n in names for n in E.DOS1 if n), "(c) every MSX-DOS 1 function name present")
check(all(r["status"] == "unused in MSX-DOS 1" for r in rs if r["name"] == "—"),
      "(c) the unused numbers say so")
bd = {r["name"]: r for r in rs}
check("bdos-acceptance" in bd["FOPEN"]["gates"],
      "(c) FOPEN is exercised by bdos-acceptance (the two-hop reach)")

print(f"\n{'ALL PASSED' if not fails else f'{fails} FAILED'}")
sys.exit(1 if fails else 0)
