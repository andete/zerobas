#!/usr/bin/env python3
r"""D-LSETREF — is the LSET/RSET-on-a-never-FIELDed-variable split a DISK
CAPABILITY or a FIRMWARE REVISION?

TODO.md files `LSET`/`RSET` on a never-fielded variable as NO-ORACLE: the
cassette-only Philips VG-8020 raises `Illegal function call`, the disk-equipped
National CF-3300 pads in place. zerobas agrees with the CF-3300. The open
question is which of the two axes the split follows, because that decides
whether the CF-3300 is the right oracle for the row at all.

🎯 THE CONTROLLED PAIR IS FREE, AND IT IS AN ARITHMETIC ARGUMENT, NOT A
   MEASUREMENT. openMSX's own ROM set gives:

     cf-3000_basic-bios1.rom   sha1 c7a2c5baee6a9f0e1c6ee7d76944c0ab1886796c
     cf-3300_basic-bios1.rom   sha1 c7a2c5baee6a9f0e1c6ee7d76944c0ab1886796c

   BYTE-IDENTICAL. The National CF-3000 and CF-3300 run THE SAME main BASIC
   ROM; the CF-3300 additionally carries a disk ROM in slot 3-1. So for that
   pair a "firmware revision" explanation is excluded before any machine boots
   -- there is no revision to differ. Whatever separates them is the disk ROM.

   That makes `cf3000` the load-bearing side here. The other five are breadth:
   three more BIOS images (Philips, and on demand Canon/Toshiba) to show the
   cassette reading is not a Philips quirk, and a SECOND, UNRELATED disk
   lineage (Spectravideo SVI-738, its own DiskROM, sha1 c53b3f2c) to show the
   padding is not a National quirk.

     side      machine                  BIOS sha1   disk
     vg8020    Philips_VG_8020          829c00c3    no
     cf3000    National_CF-3000         c7a2c5ba    no     <- twin of cf3300
     cf3300    National_CF-3300         c7a2c5ba    YES
     svi738    Spectravideo_SVI-738     c53b3f2c    YES    <- other lineage
     zb        (repack disk)            --          YES

🔴 PREDICTIONS, RECORDED BEFORE THE RUN (score them, including the misses):
   P1  cf3000 reads `Illegal function call` on g.lset/g.rset, like vg8020.
       NOT a tautology: vg8020's ROM is a DIFFERENT image, so "the main ROM
       raises IFC" is so far a one-image observation. If cf3000 PADS, the
       split is not disk-vs-cassette and P1 is refuted outright.
   P2  svi738 pads in place like cf3300. Lower confidence -- a different
       vendor's DiskROM need not implement LSET the same way. If it raises
       instead, the padding is National-specific, the CF-3300 is still the
       right oracle (it is the target machine) but the row's class is
       narrower than "Disk BASIC".
   P3  b.lset (`LSET A$=5`) reads the same error on cf3000 as on vg8020.

A control that shares the subject's machinery is not a control
([[a-case-that-agrees-can-agree-for-the-wrong-reason]]), so both controls here
touch no LSET, no RSET and no FIELD.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

# --- extra reference sides ---------------------------------------------------
# Disk machines boot slower; the CF-3300 entry in basic_probe_deffn uses 14.0 s
# and a SCREEN 0 in its reset (Disk BASIC boots into a different width).
D.SIDES.update({
    "cf3000": dict(machine="National_CF-3000",     boot=8.0,
                   reset=("", "SCREEN 0", "NEW")),
    "svi738": dict(machine="Spectravideo_SVI-738", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "canon":  dict(machine="Canon_V-20",           boot=8.0,  reset=("NEW",)),
    "hx10":   dict(machine="Toshiba_HX-10",        boot=8.0,  reset=("NEW",)),
})

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the subject: LSET/RSET where the target was never FIELDed ---------------
add('g.lset',    ['A$="12345"', 'LSET A$="AB"'],       'A$+"|"')
add('g.rset',    ['A$="12345"', 'RSET A$="AB"'],       'A$+"|"')
# longer than the target: a padding implementation must TRUNCATE to 5
add('g.lsetlong',['A$="12345"', 'LSET A$="ABCDEFGH"'], 'A$+"|"')
# the target is a null string -- padding into a zero-length descriptor
add('g.lsetnul', ['LSET A$="AB"'],                     'A$+"|"')
# the DECLINE half: a numeric operand where a string is required
add('b.lset',    ['A$="12345"', 'LSET A$=5'],          '"bail-missed"')

# --- D-LSETTM: the DECLINE half has TWO causes and they need not share an
# --- answer. printusing.asm:66 records the trap in this exact machinery:
# `str_eval` declines both for "there is NOTHING here" and for "there IS
# something and it is not a string", and the references answer those
# DIFFERENTLY. Retargeting field.asm:535 without these rows would convert the
# missing-operand case too. [[two-rules-that-coincide-on-every-row-you-have]]
add('b.lsetmiss',['A$="12345"', 'LSET A$='],           '"bail-missed"')
add('b.lsetcol', ['A$="12345"', 'LSET A$=:PRINT'],     '"bail-missed"')
add('b.rsetmiss',['A$="12345"', 'RSET A$='],           '"bail-missed"')
add('b.lsetvar', ['A$="12345"', 'N=5', 'LSET A$=N'],   '"bail-missed"')
add('b.rset',    ['A$="12345"', 'RSET A$=5'],          '"bail-missed"')

# 🔴 face() COLLAPSES WHITESPACE RUNS (`" ".join(txt.split())`), so `AB   |`
# and `AB |` are the SAME reading. The four g.* rows above therefore CANNOT
# witness the pad WIDTH -- cf3300 and zb could pad to different lengths and
# still agree here. LEN() is a number and cannot collapse.
add('g.lsetlen', ['A$="12345"', 'LSET A$="AB"'],       'LEN(A$)')
add('g.rsetlen', ['A$="12345"', 'RSET A$="AB"'],       'LEN(A$)')

# --- controls: no LSET, no RSET, no FIELD anywhere in them ------------------
add('ctl.lit',   [],                                   '"AB"+"CD"')
add('ctl.str',   ['A$="12345"'],                       'A$+"|"')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1
         else "vg8020,cf3000,cf3300,svi738,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}

w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>20}" for s in sides))
print("-" * (w + 2 + 22 * len(sides)))
for l in ORDER:
    print(f"{l:<{w}}  " + "  ".join(f"{res[s][l]:>20}" for s in sides))
print()
for s in sides:
    print(f"{s:>8}: " + D.SIDES[s]["machine"])
