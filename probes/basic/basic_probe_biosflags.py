#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS step 3: BIOS entries whose published OUTPUT IS A FLAG, compared on that flag
-- the VG-8020 against zerobas. biosregs-acceptance compares A / BC / DE / HL and leaves F
out ("not a documented contract" -- true for its sprite / VRAM rows, not for these): an
entry that answers in Z or C had no row reading its answer.

Each row: our code loads the inputs, calls the entry, stores F and A; BASIC prints F AND
<the documented flag mask> and, where A is part of the answer, A.

  DCOMPR $0020   HL ? DE                      Z (equal), C (HL < DE)          mask $41
  CHRGTR $0010   HL -> a byte before it        Z (end / ':'), C (a digit)      mask $41
  GETYPR $0028   VALTYP 2 / 3 / 4 / 8          S, Z, P/V, C (the type)         mask $C5
  CHSNS  $009C   the key buffer empty          Z (no key)                      mask $40
  BREAKX $00B7   no key down                   C (Ctrl-STOP)                   mask $01
  LPTSTT $00A8   no printer                    A and Z                         mask $40
  SCALXY $010E   BC = x, DE = y in / out       C (clipped: reset)              mask $01
  CNVCHR $00AB   plain / $01 / $01+$41 / $01+$30  Z, C and A (graphic code)    mask $41
  ISFLIO $014A   no file open                  Z, A = 0                        mask $40
  GSPSIZ $008A   SCREEN 1,0 / 1,2              C (16x16), A = the size         mask $01
  SETATR $011A   A = 5 / A = $20               C (bad attribute)               mask $01

Black box: registers only.

    python3 -u probes/basic/basic_probe_biosflags.py [ROW ...]      (`make biosflags-acceptance`)
Exit 0 all SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
DCOMPR, CHRGTR, GETYPR, CHSNS, BREAKX, LPTSTT, SCALXY = (0x0020, 0x0010, 0x0028, 0x009C,
                                                         0x00B7, 0x00A8, 0x010E)
VALTYP = 0xF663
# D-BIOSCONTRACT2 gap 7 (2026-11-14): flag answers this gate did not read
CNVCHR, ISFLIO, GSPSIZ, SETATR = 0x00AB, 0x014A, 0x008A, 0x011A


def code(entry, a=0, bc=0, de=0, hl=0, valtyp=None):
    c = []
    if valtyp is not None:
        c += [0x3E, valtyp, 0x32, VALTYP & 255, VALTYP >> 8]          # ld a,t / ld (VALTYP),a
    c += [0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8, 0x21, hl & 255, hl >> 8,
          0x3E, a, 0xCD, entry & 255, entry >> 8,
          0xF5, 0xE1, 0x22, 0x00, 0xD1]                                # AF -> $D100 (F, A)
    if valtyp is not None:      # back to an integer, or `Q=USR(0)` is a string (Type mismatch)
        c += [0x3E, 2, 0x32, VALTYP & 255, VALTYP >> 8]
    return c + [0xC9]


# name: (code, mask, compare A, before) -- `before` runs in BASIC ahead of the call
ROWS = {
    "dcmp_lt": (code(DCOMPR, hl=0x1234, de=0x1235), 0x41, False, ""),
    "dcmp_eq": (code(DCOMPR, hl=0x1234, de=0x1234), 0x41, False, ""),
    "dcmp_gt": (code(DCOMPR, hl=0x1235, de=0x1234), 0x41, False, ""),
    "dcmp_hi": (code(DCOMPR, hl=0x2200, de=0x11FF), 0x41, False, ""),
    # CHRGTR: HL points one before the byte to read (it increments first, skips spaces)
    "chr_dig": (code(CHRGTR, hl=0xD1FF), 0x41, True, "POKE &HD200,ASC(\"5\")"),
    "chr_ltr": (code(CHRGTR, hl=0xD1FF), 0x41, True, "POKE &HD200,ASC(\"A\")"),
    "chr_col": (code(CHRGTR, hl=0xD1FF), 0x41, True, "POKE &HD200,ASC(\":\")"),
    "chr_end": (code(CHRGTR, hl=0xD1FF), 0x41, True, "POKE &HD200,0"),
    "chr_spc": (code(CHRGTR, hl=0xD1FF), 0x41, True, "POKE &HD200,32:POKE &HD201,ASC(\"7\")"),
    "typ_int": (code(GETYPR, valtyp=2), 0xC5, False, ""),
    "typ_str": (code(GETYPR, valtyp=3), 0xC5, False, ""),
    "typ_sng": (code(GETYPR, valtyp=4), 0xC5, False, ""),
    "typ_dbl": (code(GETYPR, valtyp=8), 0xC5, False, ""),
    "chsns_e": (code(CHSNS), 0x40, False, ""),
    "brkx_up": (code(BREAKX), 0x01, False, ""),
    "lptstt":  (code(LPTSTT), 0x40, True, ""),
    "scal_in": (code(SCALXY, bc=100, de=100), 0x01, False, "SCREEN 2"),
    "scal_x":  (code(SCALXY, bc=300, de=100), 0x01, False, "SCREEN 2"),
    "scal_y":  (code(SCALXY, bc=100, de=250), 0x01, False, "SCREEN 2"),
    "scal_ng": (code(SCALXY, bc=0xFFF0, de=100), 0x01, False, "SCREEN 2"),
    # D-BIOSCONTRACT2 gap 7 (2026-11-14). CNVCHR: A in -> Z / C say header / converted /
    # plain, A the code; the second call after a header byte ($01) is the graphic path.
    "cnv_plain": (code(CNVCHR, a=0x41), 0x41, True, ""),
    "cnv_hdr":   (code(CNVCHR, a=0x01), 0x41, True, ""),
    "cnv_graph": ([0x3E, 0x01, 0xCD, CNVCHR & 255, CNVCHR >> 8] + code(CNVCHR, a=0x41),
                  0x41, True, ""),
    "cnv_nogfx": ([0x3E, 0x01, 0xCD, CNVCHR & 255, CNVCHR >> 8] + code(CNVCHR, a=0x30),
                  0x41, True, ""),                                     # header, then not $40..$5F
    "isflio":    (code(ISFLIO), 0x40, True, ""),                       # no file open
    "gspsiz8":   (code(GSPSIZ), 0x01, True, "SCREEN 1,0"),             # 8x8: Cy clear
    "gspsiz16":  (code(GSPSIZ), 0x01, True, "SCREEN 1,2"),             # 16x16: Cy set
    "setatr_ok": (code(SETATR, a=5), 0x01, False, "SCREEN 2"),
    "setatr_bad": (code(SETATR, a=0x20), 0x01, False, "SCREEN 2"),     # > 15: Cy
}


def prog(c, mask, before):
    return ["NEW", "10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 " + (before + ":" if before else "") + "DEFUSR=&HD000:Q=USR(0)",
            f'40 SCREEN 0:PRINT "[F";PEEK(&HD100) AND {mask};PEEK(&HD101);"]"',
            "50 DATA " + ",".join(str(b) for b in c), "RUN"]


def read(machine, c, mask, before):
    raw = omsx_repl.run_cases(machine, [("direct", prog(c, mask, before))], batch=False,
                              reset=("", "SCREEN 0"), step=3.0, run_gap=8.0)[0] or ""
    m = re.findall(r"\[F\s*(\d+)\s+(\d+)\s*\]", re.sub(r"\s+", " ", raw))
    return (int(m[-1][0]), int(m[-1][1])) if m else None


def main():
    only = sys.argv[1:] or list(ROWS)
    bad = blind = 0
    for name in only:
        c, mask, with_a, before = ROWS[name]
        got = {side: read(m, c, mask, before) for side, m in MACHINES}
        k = {s: None if g is None else (g if with_a else (g[0],)) for s, g in got.items()}
        if k["VG"] is None:
            verdict = "NO-REFERENCE"
            blind += 1
        else:
            verdict = "SAME" if k["ZB"] == k["VG"] else "DIVERGES"
            bad += verdict == "DIVERGES"
        print(f"ROW {name:8} VG={got['VG']} ZB={got['ZB']} (F&${mask:02X}{', A' if with_a else ''}) "
              f"{verdict}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: the VG-8020 gave no reading")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: flag-answering BIOS entries ({len(only) - bad}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
