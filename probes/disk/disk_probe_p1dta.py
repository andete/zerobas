#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-P1DOS: does an MSX-DOS program's BDOS $27 RDBLK into a DTA in PAGE 1 land in
the RAM there -- on the CF-3300 and on zerobas?

D-P1RDBLK (2026-10-22) fixed the call made OUTSIDE MSX-DOS (a boot loader through
$F37D); this asks the same of the DOS-mode handler, through $0005. Our own program
(probes/disk/p1dta.asm) runs from AUTOEXEC.BAT on both machines: OPEN our own
P1DATA.BIN, SETDTA $4000, RDBLK one 128-byte record, the answers at $C000/$C001.
Read back at T40 from the `Main RAM` debuggable itself -- NOT CPU memory: at the
DOS prompt both machines show their disk ROM in page 1, and a first cut read its
"AB" header on both and called it the record. Then compared.
Black box: our own program, our own bytes; nothing of the reference is read.
"""
import os, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))

com = probe_tmp.tmp("p1dta.com")
subprocess.run(["pasmo", "--bin", os.path.join(HERE, "p1dta.asm"), com], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
DATA = bytes((i * 37 + 11) & 0xFF for i in range(512))
got = {}
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"p1dta_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "P1DTA", "COM", open(com, "rb").read())
    fat12_add(img, "P1DATA", "BIN", DATA)
    fat12_add(img, "P1SMALL", "BIN", DATA[:300])     # D-SRCHFCB: the record count's rounding
    fat12_add(img, "AUTOEXEC", "BAT", b"P1DTA\r\n")
    open(dsk, "wb").write(img)
    dump = probe_tmp.tmp(f"p1dta_{tag}.mem")
    tcl = (f"after time 40 {{ set f [open {{{dump}}} w]; "
           "binary scan [debug read_block {Main RAM} 0x4000 128] H* a; "
           "binary scan [debug read_block {Main RAM} 0xC000 6] H* b; "
           "binary scan [debug read_block {Main RAM} 0x4100 128] H* c; "
           "binary scan [debug read_block {Main RAM} 0x4200 34] H* d; "
           "binary scan [debug read_block {Main RAM} 0xC100 34] H* e; "
           "binary scan [debug read_block {Main RAM} 0xC200 34] H* g; "
           "puts $f \"$a $b $c $d $e $g\"; close $f }\n")
    W.run_once(machine, dsk, 14, 42, 300, cmd="P1DTA", extra_tcl=tcl, type_cmd=False)
    a, b, c, d, e, g = open(dump).read().split() if os.path.exists(dump) else ("",) * 6
    got[tag] = (bytes.fromhex(a), bytes.fromhex(b), bytes.fromhex(c), bytes.fromhex(d),
                bytes.fromhex(e), bytes.fromhex(g))
    rec = lambda h: "= the record" if bytes.fromhex(h) == DATA[:128] else h[:32] + "..."
    print(f"{tag}: answers RDBLK={b[0:2]} OPEN={b[2:4]} SEQRD={b[4:6]} SFIRST={b[6:8]}"
          f"   the program ran with A8={b[8:10]} subslots={b[10:12]}")
    print(f"{tag}:   RDBLK $4000.. {rec(a)}   SEQRD $4100.. {rec(c)}")
    print(f"{tag}:   SFIRST $4200.. {d}")
    print(f"{tag}:   SFIRST $C100.. {e}")
    print(f"{tag}:   SFIRST $C200.. {g}   (300 bytes)")
S, O = got["STOCK"], got["OURS"]
# SFIRST (D-P1SRCH, D-SRCHFCB): into page 3 the CF-3300 writes the FCB form (+0 the drive,
# +13 the attribute, +15 the record count) -- compared whole, at $C100 (512 B) and $C200
# (300 B). Into page 1 it writes the raw directory entry at +1 -- compared at +1..+32;
# +0 and +33 hold the PROGRAM'S own $55 pre-fill, which zerobas cannot write: D-TPAP1.
ok = (O[0] == S[0] == DATA[:128] and O[2] == S[2] == DATA[:128]
      and O[1][:4] == S[1][:4]                  # every answer
      and O[3][1:33] == S[3][1:33]              # SFIRST into page 1: the raw entry
      and O[4][:33] == S[4][:33]                # SFIRST into page 3: the FCB form
      and O[5][:33] == S[5][:33])               # ... and the record count's rounding
if O[1][4:6] != S[1][4:6]:
    print(f"KNOWN GAP: a DOS program runs with page 1 = subslots {O[1][5]:02X} here, "
          f"{S[1][5]:02X} on the CF-3300 -- the TPA is not RAM in page 1 (D-TPAP1)")
print("PASS: RDBLK, SEQRD and SFIRST land in page-1 RAM as on the CF-3300, SFIRST's "
      "entry byte for byte" if ok else
      "FAIL: a page-1 DTA differs (see above)")
sys.exit(0 if ok else 1)
