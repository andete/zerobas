#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ENTRYTIERS step 5 (2026-11-09): BIOS PHYDIO ($0144) called directly from Disk
BASIC, the National_CF-3300 (stock) against zerobas's disk machine: sector 0 of
drive A read into $D200 (A = 0, B = 1, C = $F9, DE = 0, HL = $D200, Cy = 0). The
CONTRACT is compared -- Cy, A, B (the sectors not transferred), a position-weighted
checksum of the 512 bytes and three of them; HL and C are not (the CF-3300 leaves
HL = $D200 / C = $3C, ours 1 / 1: outside it). disk/test720.dsk, copied.

    python3 -u probes/disk/disk_probe_phydio.py [--machine M]   (or $ZEROBAS_BASIC_MACHINE)
Exit 0 = the contract matches.
"""
import argparse, os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
import probe_tmp  # noqa: E402  -- every scratch file under the project's temp root

REF = "National_CF-3300"
# or a / ld bc,$01F9 / ld de,0 / ld hl,$D200 / ld a,0 / call $0144 / push af /
# ld ($D100),hl / ld ($D102),de / ld ($D104),bc / pop hl / ld ($D106),hl / ret
STUB = [0xB7, 0x01, 0xF9, 0x01, 0x11, 0x00, 0x00, 0x21, 0x00, 0xD2, 0x3E, 0x00,
        0xCD, 0x44, 0x01, 0xF5, 0x22, 0x00, 0xD1, 0xED, 0x53, 0x02, 0xD1,
        0xED, 0x43, 0x04, 0xD1, 0xE1, 0x22, 0x06, 0xD1, 0xC9]
PROG = ["NEW",
        "10 CLEAR 200,&HCFFF:FOR I=0 TO 511:POKE &HD200+I,&HAA:NEXT",
        f"20 FOR I=0 TO {len(STUB) - 1}:READ X:POKE &HD000+I,X:NEXT",
        "30 DEFUSR=&HD000:Q=USR(0)",
        '40 S=0:FOR I=0 TO 511:S=S+PEEK(&HD200+I)*(1+(I AND 7)):NEXT',
        '45 R$=HEX$(PEEK(&HD101)*256+PEEK(&HD100))+" "+HEX$(PEEK(&HD103)*256+PEEK(&HD102))+" "+HEX$(PEEK(&HD105)*256+PEEK(&HD104))',
        '50 PRINT "[R";R$;" A";HEX$(PEEK(&HD107));" F";HEX$(PEEK(&HD106) AND 1);'
        '" S";S;" B0 ";HEX$(PEEK(&HD200));HEX$(PEEK(&HD203));HEX$(PEEK(&HD20B));"]"',
        "60 DATA " + ",".join(str(b) for b in STUB),
        "RUN"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE")
    out = {}
    for side, m in (("CF", REF), ("ZB", args.machine)):
        dsk = probe_tmp.tmp(f"phydio_{side}.dsk")
        shutil.copy(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        scr = omsx_repl.run_cases(m, [("direct", PROG)], batch=False, diska=dsk,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=20.0)[0] or ""
        rows = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
        out[side] = " | ".join(r for r in rows if r.startswith("[R") or "rror" in r or "ffline" in r) or None
        print(f"{side} ({m}): {out[side]}", flush=True)
    def contract(r):   # drop HL (1st field) and C (low byte of the 3rd)
        m = re.match(r"\[R(\S+) (\S+) (\S+) (.*)\]", r or "")
        return m and (m.group(2), m.group(3).zfill(4)[:2], m.group(4))
    ok = out["CF"] is not None and contract(out["CF"]) == contract(out["ZB"])
    print("PASS: PHYDIO's contract matches the CF-3300" if ok else "FAIL: PHYDIO DIVERGES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
