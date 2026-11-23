#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubscr.asm (sub-ROM SDFSCR / SETSCR).
    python3 scratchpad/xsubscr_decode.py RUNFILE [--side ref|ours]
Refuses a record whose sentinel ($5E at +511) is missing.
    --cases xsubset  for probes/bios/spec/xsubset.asm (SETSCR)
    --cases xsubsc2  for probes/bios/spec/xsubsc2.asm (SDFSCR, goldfish pass 1: 1024-byte record, "AAA" searched)"""
import re
import sys

REC = 512
SET = False
NAMES = {"xsubscr": ["0 SDFSCR found S0", "1 SDFSCR found S5", "2 SDFSCR set1", "3 SDFSCR set1 EI", "4 SDFSCR set3 EI",
                     "5 SDFSCR set3 S5", "6 SDFSCR set2", "7 SDFSCR set2 CY", "8 SDFSCR set2 Z", "9 SDFSCR set2 A=FF EI",
                     "10 SDFSCR set4(w100) S1", "11 SDFSCR set2 snap", "12 SDFSCR again (noise)", "13 +printer",
                     "14 +cassette", "15 +beep A", "16 +title colour 3", "17 +ID 5", "18 set10 ID A S1 w18",
                     "19 set11 = set10 ID 5"],
         "xsubset": ["0 SETSCR found S0 log", "1 set1 log", "2 set2 S5 log", "3 set2 EI", "4 set3 DI",
                     "5 set4(w100) S1 log", "6 SDFSCR set2 snap", "7 SETSCR set2 diff vs SDFSCR", "8 set2 title SXA",
                     "9 set2+tcol3 title SXA", "10 set2 title SXASXA", "11 set2 password SXA", "12 set2 prompt SXA",
                     "13 set2 ID5 empty title", "14 set7 S1 w18 key1 fill log", "15 set1 S1 w30 key0 fill log"],
         "xsubsc2": ["0 set6 (key+prn+cas) snap", "1 set12 (prn/cas 0) diff vs 0", "2 set2 w80 from TEXT2 DI fill",
                     "3 set3 w37 key1 fill log", "4 set1 S1 w30 fill before/after diff", "5 set1 A=FF F=41 DI",
                     "6 set13 S1 w36", "7 set14 S1 w50", "8 set15 S0 w0"]}
SC2 = False
CELLS = "SCRMOD OLDSCR LINL40 LINL32 LINLEN CRTCNT CLMLST CNSDFG CLIKSW FOR BAK BDR CSRY CSRX PUT GET".split()


def txt(bs):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in bs)


def decode(b, k, NAMES):
    r = b[2 + REC * k: 2 + REC * (k + 1)]
    if len(r) < REC or r[REC - 1] != 0x5E:
        sys.exit(f"REFUSED: case {k}: sentinel missing")
    out = [f"== {NAMES[r[0]] if r[0] < len(NAMES) else r[0]}"]
    out.append(f"  A={r[1]:02X} F={r[2]:02X} IFF={r[3]} (first read {r[14]}) BC={r[5]:02X}{r[4]:02X} "
               f"DE={r[7]:02X}{r[6]:02X} HL={r[9]:02X}{r[8]:02X} IX={r[11]:02X}{r[10]:02X} IY={r[13]:02X}{r[12]:02X}")
    out.append("  " + " ".join(f"{n}={r[16 + i]:02X}" for i, n in enumerate(CELLS)))
    out.append("  RG0-7SAV=" + r[32:40].hex(" ") + "  RG8-23SAV=" + r[40:56].hex(" "))
    out.append("  blk2 before=" + "".join(f"{x:X}" for x in r[371:384 - 0][:13]) +
               " after=" + "".join(f"{x:X}" for x in r[56:69]) + f" MODE={r[69]:X}"
               + "  blk3=" + "".join(f"{x:X}" for x in r[72:85]))
    v = r[88:202]
    out.append("  VDP R0-23=" + v[0:24].hex(" ") + "  R25-27=" + v[25:28].hex(" ")
               + "  S0-2=" + v[64:67].hex(" "))
    out.append("  palette=" + v[82:114].hex())
    base = r[368] | r[369] << 8
    out.append(f"  name base=${base:04X} rowlen={r[370]}")
    out.append("  row0 : |" + txt(r[208:288]) + "|")
    out.append("  rowK : |" + txt(r[288:368]) + "|")
    t = r[384:]
    ll = t[2] | t[3] << 8
    off = t[4] | t[5] << 8
    out.append(f"  keys injected={t[1]} log len={ll} {'AAA' if SC2 else 'SXA'} at={'none' if off == 0xFFFF else off} "
               f"log[..32]=|{txt(t[8:40])}| {t[8:40].hex()}")
    if SET:
        off2 = t[6] | t[7] << 8
        out.append(f"  MSX at={'none' if off2 == 0xFFFF else off2} log[..32]=|{txt(t[40:72])}| {t[40:72].hex()}")
        if ll:
            f1, f2 = t[248] | t[249] << 8, t[250] | t[251] << 8
            out.append(f"  AAA runs={t[252]} first={'none' if f1 == 0xFFFF else f1} last={'none' if f2 == 0xFFFF else f2}")
    if t[0]:
        lim = 44 if SET else 149 if SC2 else 21
        ds = [t[(72 if SET else 40) + 4 * i: (76 if SET else 44) + 4 * i] for i in range(min(t[0], lim))]
        out.append(f"  wa diffs={t[0]}: " + " ".join(f"{d[1]:02X}{d[0]:02X}:{d[2]:02X}>{d[3]:02X}" for d in ds))
    return "\n".join(out)


def main():
    which = sys.argv[sys.argv.index("--cases") + 1] if "--cases" in sys.argv else "xsubscr"
    names = NAMES[which]
    global REC, SET, SC2
    if which == "xsubset":
        REC, SET = 640, True
    if which == "xsubsc2":
        REC, SC2 = 1024, True
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(REC * 20)
        if b[0] != 0xA5:
            print("# NOT FINISHED", blk.split("\n", 1)[0])
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side, f"cases={b[1]}")
        for k in range(b[1]):
            print(decode(b, k, names))


if __name__ == "__main__":
    main()
