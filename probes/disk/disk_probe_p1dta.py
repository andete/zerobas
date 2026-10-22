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
    fat12_add(img, "AUTOEXEC", "BAT", b"P1DTA\r\n")
    open(dsk, "wb").write(img)
    dump = probe_tmp.tmp(f"p1dta_{tag}.mem")
    tcl = (f"after time 40 {{ set f [open {{{dump}}} w]; "
           "binary scan [debug read_block {Main RAM} 0x4000 128] H* a; "
           "binary scan [debug read_block {Main RAM} 0xC000 4] H* b; "
           "binary scan [debug read_block {Main RAM} 0x4100 128] H* c; "
           "binary scan [debug read_block {Main RAM} 0x4200 33] H* d; "
           "puts $f \"$a $b $c $d\"; close $f }\n")
    W.run_once(machine, dsk, 14, 42, 300, cmd="P1DTA", extra_tcl=tcl, type_cmd=False)
    a, b, c, d = open(dump).read().split() if os.path.exists(dump) else ("", "", "", "")
    got[tag] = (bytes.fromhex(a), bytes.fromhex(b), bytes.fromhex(c), bytes.fromhex(d))
    rec = lambda h: "= the record" if bytes.fromhex(h) == DATA[:128] else h[:32] + "..."
    print(f"{tag}: answers RDBLK={b[0:2]} OPEN={b[2:4]} SEQRD={b[4:6]} SFIRST={b[6:8]}")
    print(f"{tag}:   RDBLK $4000.. {rec(a)}   SEQRD $4100.. {rec(c)}")
    print(f"{tag}:   SFIRST $4200.. {d}")
S, O = got["STOCK"], got["OURS"]
ok = (O[0] == S[0] == DATA[:128] and O[2] == S[2] == DATA[:128]
      and O[1][:3] == S[1][:3])                 # RDBLK / OPEN / SEQRD answers
# SFIRST's DTA fill into page 1 is a FILED gap (D-P1SRCH, TODO.md): measured and
# printed every run, not yet in the verdict -- and said out loud when it closes.
if O[3] == S[3]:
    print("NOTE: SFIRST's page-1 entry now matches -- D-P1SRCH can close; put it in the verdict")
else:
    print("KNOWN GAP: SFIRST's directory entry does not reach page-1 RAM here (D-P1SRCH)")
print("PASS: RDBLK and SEQRD land in page-1 RAM as on the CF-3300" if ok else
      "FAIL: a page-1 DTA differs (see above)")
sys.exit(0 if ok else 1)
