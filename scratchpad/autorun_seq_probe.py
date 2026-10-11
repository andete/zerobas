#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-AUTORUN: the hook order in the two cases autorun_order_probe.py left
open -- a typed NUMBERED line (stored, no prompt), and what the screen shows
after CLOAD (the reference calls H.MAIN only there: does it print a prompt?).

Same method as autorun_order_probe.py (our tag logger behind H.READ = R and
H.MAIN = M, typed markers '1' '2'), but the log sits at $D000 under
CLEAR 200,&HD000 -- below zerobas's $DB00 workspace -- so the zerobas rows are
valid too (the first probe's were void). Timeline: RUN (installs the hooks,
END) -> '1' -> a typed numbered line -> '2' -> CLOAD from tape -> the line
that prints the log. The screen around `Found:` is printed as well.
Black-box: our code in RAM, two documented hook cells, PEEK, the screen.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")


def tokenised(lines, base=0x8001):
    out, addr = b"", base
    for n, t in lines:
        body = bytes([0x8F]) + t.encode() + b"\x00"
        nxt = addr + 4 + len(body)
        out += nxt.to_bytes(2, "little") + n.to_bytes(2, "little") + body
        addr = nxt
    return out + b"\x00\x00"


# PUSH AF / PUSH HL / LD HL,($D030) / LD (HL),tag / INC HL / LD ($D030),HL /
# POP HL / POP AF / RET
def logger(tag):
    return f"F5,E5,2A,30,D0,36,{tag:02X},23,22,30,D0,E1,F1,C9,0,0"


LINES = ["NEW", "CLEAR 200,&HD000",
         '10 FOR I=0 TO 31:READ A$:POKE &HD000+I,VAL("&H"+A$):NEXT',
         "20 DATA " + logger(ord("R")),
         "30 DATA " + logger(ord("M")),
         "40 FOR I=0 TO 63:POKE &HD040+I,46:NEXT:POKE &HD030,&H40:POKE &HD031,&HD0",
         "50 POKE &HFF08,0:POKE &HFF09,&HD0:POKE &HFF07,&HC3",
         "60 POKE &HFF0D,16:POKE &HFF0E,&HD0:POKE &HFF0C,&HC3:END",
         "70 P=PEEK(&HD030):POKE &HD000+P,M:POKE &HD030,P+1:RETURN",
         "RUN",
         "M=49:GOSUB 70",
         "100 REM",
         "M=50:GOSUB 70",
         "CLOAD",
         "@WAIT30",
         "FORI=0TO63:?CHR$(PEEK(&HD040+I));:NEXT"]
RX = re.compile(r"[RM12.]{40,}")


def main():
    path = probe_tmp.tmp("autorun_seq.cas")
    open(path, "wb").write(cas_encode.build_cas_basic_csave(
        "X", tokenised([(10, " LOADED")])))
    for m in (REF, OURS):
        raw = omsx_repl.run_cases(m, [("direct", LINES)], batch=False,
                                  reset=("", "SCREEN 0"), cassette=path)[0] or ""
        flat = "".join(raw.split())
        hits = RX.findall(flat)
        j = raw.rfind("Found:")
        tail = " | ".join(r.strip() for r in raw[j:].splitlines()[:4]) if j >= 0 else None
        print(f"{m:32s} log: {hits[-1] if hits else None}")
        print(f"{'':32s} after CLOAD: {tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
