#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ROBOREG: a MULTI-sector DSKIO read that STARTS in page 1 -- does each sector after
the first land where it should, on the CF-3300 and on zerobas?

zerobas reads a page-1 sector through a bounce buffer (disk/driver.asm, D-P1RDBLK).
D-DSKFMT carve 16 (2026-11-10) made that arm skip the destination store, so every
sector AFTER a page-1 one landed at the bounce buffer + 512 * n: SDSNAT1C.DSK's 36-sector
read into $2000 ran up over the hooks at $FD9A and the game never started. The page-1
probes then in the battery read ONE record, so none of them could see it.

Our own code (Disk BASIC, a USR routine): saves $8000-$81FF, reads TWO sectors (S, S+1)
through DSKIO ($4010 through CALSLT, the disk slot from DRVINF+1) into $7E00 -- the first
in page 1 (bounced), the second at $8000 in page 2 -- copies $8000-$81FF to $D600 and
puts the program text back. BASIC prints DSKIO's A / F and four bytes of $D600 at
offsets 0, 1, 255, 511. Sector S+1 of the image is a pattern this probe wrote; the
same four bytes are the expectation, on BOTH machines. Black box: our own code, our
own bytes; nothing of the reference is read.

    ZEROBAS_BASIC_MACHINE=... python3 -u probes/disk/disk_probe_p1multi.py
"""
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402

SECTOR = 1300           # far into a 720 KB image's data area: our own pattern goes in
IMAGE = os.path.join(REPO, "disk", "test720.dsk")   # the build's blank data disk (make: $(DISK_TEST_DSK))
PAT = bytes(((i * 29) + 7) & 0xFF for i in range(512))

CODE = [0x21, 0x00, 0x80, 0x11, 0x00, 0xD4, 0x01, 0x00, 0x02, 0xED, 0xB0,   # save $8000
        0x3E, 0x00, 0x06, 0x02, 0x0E, 0xF9,                                  # A 0, B 2, C $F9
        0x11, SECTOR & 255, SECTOR >> 8, 0x21, 0x00, 0x7E, 0xB7,             # DE, HL $7E00, Cy 0
        0xFD, 0x21, 0x00, 0x00,                                              # IY (IYh POKEd)
        0xDD, 0x21, 0x10, 0x40, 0xCD, 0x1C, 0x00, 0xFB,                      # CALSLT $4010, ei
        0xF5, 0xE1, 0x22, 0x00, 0xD2,                                        # AF -> $D200
        0x21, 0x00, 0x80, 0x11, 0x00, 0xD6, 0x01, 0x00, 0x02, 0xED, 0xB0,   # $8000 -> $D600
        0x21, 0x00, 0xD4, 0x11, 0x00, 0x80, 0x01, 0x00, 0x02, 0xED, 0xB0,   # restore $8000
        0xC9]
IYH = CODE.index(0xFD) + 3


def prog():
    return ["NEW", "10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(CODE) - 1}:READ X:POKE &HD000+I,X:NEXT",
            f"30 POKE &HD000+{IYH},PEEK(&HFB22):DEFUSR=&HD000:Q=USR(0)",
            '40 S$="":FOR I=0 TO 3:READ O:S$=S$+" "+RIGHT$("0"+HEX$(PEEK(&HD600+O)),2):NEXT',
            '50 PRINT "[F";HEX$(PEEK(&HD201));" ";HEX$(PEEK(&HD200));S$;"]"',
            "60 DATA " + ",".join(str(b) for b in CODE),
            "70 DATA 0,1,255,511",
            "RUN"]


def main():
    want = " ".join(f"{PAT[o]:02X}" for o in (0, 1, 255, 511))
    bad = blind = 0
    for side, mach in (("REF", RT.REF_MACHINE), ("ZB", RT.OUR_MACHINE)):
        dsk = probe_tmp.tmp(f"p1multi_{side}.dsk")
        shutil.copyfile(IMAGE, dsk)
        img = bytearray(open(dsk, "rb").read())
        assert len(img) >= (SECTOR + 2) * 512, "the image is too small for the pattern sector"
        img[(SECTOR + 1) * 512:(SECTOR + 2) * 512] = PAT
        open(dsk, "wb").write(img)
        raw = omsx_repl.run_cases(mach, [("direct", prog())], batch=False, diska=dsk,
                                  reset=("", "SCREEN 0", "NEW"), boot=14.0, step=3.0,
                                  run_gap=12.0)[0] or ""
        t = " ".join(raw.split())
        i = t.rfind("[F")
        got = t[i + 2:t.find("]", i)] if i >= 0 else None
        if got is None:
            verdict = "NO-READING"
            blind += 1
        else:
            f = got.split()
            ok = len(f) == 6 and " ".join(f[2:]) == want and not int(f[0], 16) & 1
            verdict = "SAME" if ok else "DIVERGES"
            bad += not ok
        print(f"ROW {side:3} F/A + $8000[0,1,255,511] = [{got}]  want Cy 0 and {want}  {verdict}",
              flush=True)
    if blind:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: a 2-sector DSKIO read from page 1 into page 2")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
