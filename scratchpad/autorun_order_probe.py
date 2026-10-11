#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""WHEN and IN WHICH ORDER does the reference call H.READ ($FF07) and H.MAIN
($FF0C)? (autorun_hook_probe.py showed the VG-8020 calls both, zerobas
neither.) openMSX's autorun types CLOAD from an H.READ breakpoint and then
types RUN from the NEXT H.MAIN, with the note "H_READ isn't called after
CLOAD, but H_MAIN is" -- so the order, and what CLOAD's return calls, are part
of the contract.

THE METHOD: each hook JPs to our own RAM routine that appends a tag to a log
(R = H.READ, M = H.MAIN); typed lines append markers ('1', '2') through a
GOSUB, so the log reads as a timeline: program END -> '1' -> an error -> '2'
-> CLOAD from tape -> the line that prints the log. Black-box: our code in
RAM, two documented hook cells, PEEK. No ROM byte is read.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = "C-BIOS_MSX1_EU_REPACK_NODISK"


def tokenised(lines, base=0x8001):
    out, addr = b"", base
    for n, t in lines:
        body = bytes([0x8F]) + t.encode() + b"\x00"
        nxt = addr + 4 + len(body)
        out += nxt.to_bytes(2, "little") + n.to_bytes(2, "little") + body
        addr = nxt
    return out + b"\x00\x00"


# PUSH AF / PUSH HL / LD HL,($E030) / LD (HL),tag / INC HL / LD ($E030),HL /
# POP HL / POP AF / RET
def logger(tag):
    return f"F5,E5,2A,30,E0,36,{tag:02X},23,22,30,E0,E1,F1,C9,0,0"


LINES = ["NEW", "CLEAR 200,&HE000",
         '10 FOR I=0 TO 31:READ A$:POKE &HE000+I,VAL("&H"+A$):NEXT',
         "20 DATA " + logger(ord("R")),
         "30 DATA " + logger(ord("M")),
         "40 FOR I=0 TO 63:POKE &HE040+I,46:NEXT:POKE &HE030,&H40:POKE &HE031,&HE0",
         "50 POKE &HFF08,0:POKE &HFF09,&HE0:POKE &HFF07,&HC3",
         "60 POKE &HFF0D,16:POKE &HFF0E,&HE0:POKE &HFF0C,&HC3:END",
         "70 P=PEEK(&HE030):POKE &HE000+P,M:POKE &HE030,P+1:RETURN",
         "RUN",
         "M=49:GOSUB 70",
         "X=1/0",
         "M=50:GOSUB 70",
         "CLOAD",
         "@WAIT30",
         "FORI=0TO63:?CHR$(PEEK(&HE040+I));:NEXT"]
RX = re.compile(r"[RM12.]{40,}")


def main():
    path = probe_tmp.tmp("autorun_order.cas")
    open(path, "wb").write(cas_encode.build_cas_basic_csave(
        "X", tokenised([(10, " LOADED")])))
    for m in (REF, OURS):
        raw = omsx_repl.run_cases(m, [("direct", LINES)], batch=False,
                                  reset=("", "SCREEN 0"), cassette=path)[0] or ""
        flat = "".join(raw.split())
        hits = RX.findall(flat)
        print(f"{m:32s} log: {hits[-1] if hits else None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
