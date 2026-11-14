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

# (d) the disk-ROM pins: each tied to ITS function, never to the pin in front of it
pins = {r["addr"]: r for r in E.pinned_rows()}
check("WRZER" in pins[0x47D1]["status"], f"(d) $47D1 is WRZER's: {pins[0x47D1]['status']}")
check("AUXOUT" in pins[0x5474]["status"], f"(d) $5474 is AUXOUT's: {pins[0x5474]['status']}")
check("FREN" in pins[0x4392]["status"] and "FREN" not in pins[0x43A4]["status"],
      "(d) FREN is $4392's, not fdc_write_phys's at $43A4 (the window stops at a pin)")
check("ALLOC" in pins[0x505D]["status"] and "by its label" in pins[0x505D]["status"],
      f"(d) getalloc ties to ALLOC by its label: {pins[0x505D]['status']}")
check(pins[0x4C29]["fn"] is None, "(d) fdc_di_save names no function (a comment mention is not a tie)")
pub = {r["name"]: r for r in E.published_rows()}
check(set(pub) == {"DSKIO", "DSKCHG", "GETDPB", "CHOICE", "DSKFMT", "MTOFF"},
      "(d) the six published disk-ROM entries all have a row")

# (e) the main BIOS table: the published jump table, $0000 .. $0159, no gap or repeat
br = E.bios_rows(stubs={})   # the table's SHAPE only: CI has no merged main ROM here
ad = [r["addr"] for r in br]
check(ad == sorted(set(ad)) and ad[0] == 0x0000 and ad[-1] == 0x0159,
      f"(e) the BIOS table runs $0000..$0159 in order, {len(ad)} distinct entries")
bmap = {r["name"]: r for r in br}
check("slotregs-acceptance" in bmap["RDSLT"]["gates"],
      "(e) RDSLT is exercised by slotregs-acceptance (a direct BIOS witness)")

# (f) the contract level (tools/bios_levels.py): every claim's gate witnesses its entry,
# and a claim whose gate does not is REFUSED, not rendered
import bios_levels as BL  # noqa: E402
check(BL.check(br) == [], "(f) every BIOS level claim names a gate that witnesses its entry")
fake = dict(bmap["RDSLT"], gates=["biosregs-acceptance"])     # slotregs gone
check(BL.level_of(fake)[2] is not None and BL.level_of(fake)[0] == "L1 called",
      "(f) a claim whose gate no longer witnesses the entry is refused and reads L1")
check(BL.level_of(dict(bmap["RDSLT"], stub=True))[0] == "L0 stub", "(f) a stub outranks a claim")

print(f"\n{'ALL PASSED' if not fails else f'{fails} FAILED'}")
sys.exit(1 if fails else 0)
