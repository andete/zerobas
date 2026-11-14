#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS: INITIO ($003B) called DIRECTLY -- what does it reset? The VG-8020 against
zerobas. Joost (2026-11-13): "INITIO is a strange one" -- measure it before deciding what a
gate row should hold.

BASIC sets PSG registers 0-13 to our own values with SOUND (and, before the call, reg 15
through WRTPSG), then our routine: F = $A5 and marker BC / DE / HL, call INITIO, store
AF BC DE HL; read all sixteen PSG registers back through RDPSG ($0096) and port $AA (the
PPI's port C: keyboard row, CAPS LED, cassette motor / out). BASIC prints them in groups.
Black box: registers and I/O ports only.

    python3 -u probes/basic/basic_probe_initio.py      (`make initio-acceptance`)

Found 2026-11-13 (initio_run1..3.out, the CF-3300 agreeing, initio_cf.out): both references
write PSG register 15 := $CF and register 11 := $0B; C-BIOS wrote $8F and left 11. Fixed by
cbios-repack/initio.patch (D-INITIO); after: initio_run4.out.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
INITIO, RDPSG, WRTPSG, GICINI = 0x003B, 0x0096, 0x0093, 0x0090


def call(a):
    return [0xCD, a & 255, a >> 8]


# reg 15 := $5A (WRTPSG), AF = $00A5 (push / pop), BC / DE / HL markers, call INITIO;
# HL -> $D106, AF -> $D100, BC -> $D102, DE -> $D104; RDPSG 0..15 -> $D110..; $AA -> $D120
CODE = ([0x3E, 15, 0x1E, 0x5A, *call(WRTPSG),
         0x11, 0xA5, 0x00, 0xD5, 0xF1,
         0x01, 0x34, 0x12, 0x11, 0x78, 0x56, 0x21, 0xBC, 0x9A,
         *call(INITIO),
         0x22, 0x06, 0xD1,                             # HL -> $D106
         0xF5, 0xE1, 0x22, 0x00, 0xD1,                 # AF -> $D100
         0xED, 0x43, 0x02, 0xD1, 0xED, 0x53, 0x04, 0xD1,   # BC -> $D102, DE -> $D104
         0x06, 0x00, 0x21, 0x10, 0xD1,
         0x78, 0xC5, 0xE5, *call(RDPSG), 0xE1, 0xC1, 0x77, 0x23, 0x04, 0x78, 0xFE, 16,
         0x20, 0xF0,                                   # jr nz,<the ld a,b>
         0xDB, 0xAA, 0x32, 0x20, 0xD1, 0xC9])
_loop = len(CODE) - 6 - 16                             # the `ld a,b` the loop returns to
assert CODE[_loop] == 0x78 and CODE[_loop + 14] == 0x20
assert _loop + 16 + (CODE[_loop + 15] - 256) == _loop

PROG = ["NEW", "10 CLEAR 200,&HCFFF:K=KK:M=MM",
        "15 FOR R=0 TO 13:SOUND R,(R*37+11+K) AND 255:NEXT:SOUND 7,M",
        f"20 FOR I=0 TO {len(CODE) - 1}:READ X:POKE &HD000+I,X:NEXT",
        "30 DEFUSR=&HD000:Q=USR(0)",
        '40 S$="":FOR I=0 TO 7:S$=S$+" "+HEX$(PEEK(&HD100+I)):NEXT:PRINT "[R";S$;"]"',
        '50 S$="":FOR I=0 TO 15:S$=S$+" "+HEX$(PEEK(&HD110+I)):NEXT:PRINT "[P";S$;"]"',
        '60 PRINT "[A ";HEX$(PEEK(&HD120));"]"',
        "70 DATA " + ",".join(str(b) for b in CODE), "RUN"]


def read(machine, k=0, mix=0xB8, entry=INITIO):
    # K shifts every SOUND value; M is the mixer (reg 7: BASIC forces bits 6-7 to 10);
    # `entry` swaps the call (GICINI: which of INITIO's writes are GICINI's)
    code = CODE[:CODE.index(0xCD, 15)] + call(entry) + CODE[CODE.index(0xCD, 15) + 3:]
    assert CODE[CODE.index(0xCD, 15) + 1:CODE.index(0xCD, 15) + 3] == [INITIO & 255, INITIO >> 8]
    prog = [l.replace("KK", str(k)).replace("MM", str(mix)) for l in PROG]
    prog = [("70 DATA " + ",".join(str(b) for b in code)) if l.startswith("70 DATA") else l
            for l in prog]
    raw = omsx_repl.run_cases(machine, [("direct", prog)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=15.0)[0] or ""
    t = re.sub(r"\s+", " ", raw)
    out = {}
    for k in ("R", "P", "A"):
        m = re.findall(r"\[%s ([0-9A-F ]+)\]" % k, t)
        out[k] = m[-1].split() if m else None
    return out


def main():
    # (K, mixer): the plain set, then every value moved and the mixer off its default;
    # the GICINI run is the control that says which writes are INITIO's own.
    # Compared: the sixteen PSG registers, port $AA, and (D-GICINIQ, 2026-11-14, gap 9) the
    # exit registers: both references leave INITIO's F $54, A $FF, E $0B (initio_cf.out)
    # and GICINI's every register as it found them; C-BIOS's differed until
    # cbios-repack #27 and bios_gicini.
    bad = blind = 0
    for kk, mix, entry in ((0, 0xB8, INITIO), (100, 0x92, INITIO), (100, 0x92, GICINI)):
        got = {side: read(m, kk, mix, entry) for side, m in MACHINES}
        print(f"=== call ${entry:04X}, SOUND values shifted by {kk}, mixer ${mix:02X}")
        for k, label in (("R", "F A C B E D L H"), ("P", "PSG 0..15"), ("A", "port $AA")):
            print(f"{label}:")
            for side in ("VG", "ZB"):
                print(f"  {side} {got[side][k]}")
        if not got["VG"]["P"] or not got["VG"]["A"]:
            blind += 1
            print("ROW NO-REFERENCE")
            continue
        same = ((got["ZB"]["P"], got["ZB"]["A"], got["ZB"]["R"])
                == (got["VG"]["P"], got["VG"]["A"], got["VG"]["R"]))
        bad += not same
        print(f"ROW {'SAME' if same else 'DIVERGES'}")
    if blind:
        print("INSTRUMENT FAULT: the VG-8020 gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: INITIO's PSG / port $AA / exit registers against the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
