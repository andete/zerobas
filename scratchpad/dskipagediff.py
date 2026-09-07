#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DSKIBYTES, the follow-up row: WHICH bytes of page $EB00 move with the sector?

D-DSKIWHERE found page $2B ($EB00) tracking the sector number and I read that as
the landing address. D-DSKIBYTES refuted it -- $EB00..$EB07 holds 0 after both
DSKI$(0,0) and DSKI$(0,1), where the image has EB FE 90 5A ... and F9 FF FF 03 ...

So something in that page depends on the sector and it is not the sector. This
copies the whole page into an array after reading sector 0, reads sector 1, and
counts the bytes that changed, with the FIRST and LAST offset.

MEASURED (CF-3300, disk/test720.dsk, refcache OFF): **N=25, first=149, last=180**.
Twenty-five bytes inside a 32-byte span at $EB95..$EBB4 -- a work-area record of
the REQUEST, not a 512-byte transfer.

🎯 SO THE SECTOR DATA IS NOT IN $C000..$FFFF AT ALL: D-DSKIWHERE checksummed
every page of that window and only this one moved. Where it does go is NOT
established -- below $C000, or in RAM the BASIC slot configuration does not let
PEEK see.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT,"probes","lib"))
import omsx_repl
DSK=os.path.join(ROOT,"disk","test720.dsk")
prog=[ '10 ON ERROR GOTO 900',
       '20 DIM C(255):F=-1:P=-1:N=0',
       '30 A$=DSKI$(0,0)',
       '40 FORI=0TO255:C(I)=PEEK(&HEB00+I):NEXT',
       '50 A$=DSKI$(0,1)',
       '60 FORI=0TO255:IF PEEK(&HEB00+I)<>C(I) THEN N=N+1:P=I:IF F<0 THEN F=I',
       '70 NEXT',
       '80 PRINT"ZQ";N;F;P;"QZ":END',
       '900 PRINT"ZQ";999;ERR;0;"QZ":END' ]
raw="".join(omsx_repl.run_cases("National_CF-3300",[("direct",["NEW"]+prog+["RUN"])],
    batch=False,reset=("","SCREEN 0","NEW"),boot=14.0,step=5.0,run_gap=90.0,
    cap_gap=5.0,timeout=600.0,diska=DSK)[0] or "")
m=[g for g in re.findall(r"ZQ\s*([0-9 -]*?)\s*QZ",raw) if '"' not in g and ';' not in g]
print("readings:", m)
print("=> N (bytes differing), F (first offset), P (last offset)")
if not m:
    for r in range(24):
        row=raw[r*40:(r+1)*40].rstrip()
        if row.strip(): print(f"  r{r:02d}|{row}")
