#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASDIRECT (D-LOADERRRET's content arms): an ASCII program with a line that
has NO line number. Both references print `Direct statement in file` (57) with
no line and run no handler -- LOAD and MERGE, from tape (VG-8020 vs the diskless
build) and from disk (CF-3300 vs the disk build), and a BSAVE binary LOADed as
a program. zerobas printed `load error` and RAN ON (LOAD) or raised `Syntax
error` with a garbage line (MERGE).

Program in the file: `10 PRINT"A"` / `PRINT"B"` / `30 PRINT"C"`.
  dload / dmerge / kload / kmerge     typed (d = tape, k = disk), then LIST
  pload / pmerge / kpload / kpmerge   under 10 ON ERROR GOTO 90, then LIST
  kbinload                            a BSAVE file LOADed, then LIST
A reading is the messages after the verb, any handler marker, and the line
numbers LIST shows -- prompts (`Ok` / zerobas's own) are dropped.

Exit 0 all agree; 1 a divergence; 2 a reference gave no reading.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402
from make_test_dsk import Fat12Image, make_bsave_file   # noqa: E402

VG = "Philips_VG_8020"
CF = "National_CF-3300"
ZBN = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
ZBD = os.environ.get("ZEROBAS_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
TEXT = '10 PRINT"A"\nPRINT"B"\n30 PRINT"C"\n'
HANDLER = '90 PRINT"[E";ERR;ERL;"]":END'


def prog(verb, nxt):
    return ["NEW", "10 ON ERROR GOTO 90", f"15 {verb}", f'{nxt} PRINT"[N";1;"]":END',
            HANDLER, "RUN"]


CASES = {  # name: (medium, lines, the verb text the reading starts after)
    "dload": ("tape", ["NEW", 'LOAD"CAS:X"', "@WAIT30", "LIST"], 'LOAD"CAS:X"'),
    "dmerge": ("tape", ["NEW", "5 REM", 'MERGE"CAS:X"', "@WAIT30", "LIST"], 'MERGE"CAS:X"'),
    "pload": ("tape", prog('LOAD"CAS:X"', 30) + ["@WAIT30", "LIST"], " RUN "),
    "pmerge": ("tape", prog('MERGE"CAS:X"', 20) + ["@WAIT30", "LIST"], " RUN "),
    "kload": ("disk", ["NEW", 'LOAD"DIR.BAS"', "@WAIT6", "LIST"], 'LOAD"DIR.BAS"'),
    "kmerge": ("disk", ["NEW", "5 REM", 'MERGE"DIR.BAS"', "@WAIT6", "LIST"], 'MERGE"DIR.BAS"'),
    "kpload": ("disk", prog('LOAD"DIR.BAS"', 30) + ["@WAIT6", "LIST"], " RUN "),
    "kpmerge": ("disk", prog('MERGE"DIR.BAS"', 20) + ["@WAIT6", "LIST"], " RUN "),
    "kbinload": ("disk", ["NEW", "5 REM", 'LOAD"BIN.BIN"', "@WAIT6", "LIST"], 'LOAD"BIN.BIN"'),
}
MSG = re.compile(r"Direct statement in file|load error|Syntax error(?: in \d+)?|"
                 r"Device I/O error|\[E\s*-?\d+\s+-?\d+\s*\]|\[N 1 \]")


def media(medium):
    if medium == "tape":
        p = probe_tmp.tmp("casdirect.cas")
        open(p, "wb").write(cas_encode.build_cas_ascii("X", TEXT))
        return {"cassette": p}
    img = Fat12Image()
    img.add_file("DIR", "BAS", TEXT.replace("\n", "\r\n").encode() + b"\x1a")
    img.add_file("BIN", "BIN", make_bsave_file(0xC000, 0xC00F, 0xC000, bytes(range(16))))
    p = probe_tmp.tmp("casdirect.dsk")
    open(p, "wb").write(img.finish())
    return {"diska": p}


def reading(machine, name):
    medium, lines, after = CASES[name]
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), **media(medium))[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    i = flat.rfind(after)
    if i < 0:
        return None
    tail = flat[i + len(after):]
    j = tail.find(" LIST ")
    msgs = MSG.findall(tail[:j] if j >= 0 else tail)
    listed = re.findall(r"(?:^| )(\d+) (?:PRINT|REM|ON|MERGE|LOAD)", tail[j:]) if j >= 0 else []
    return " | ".join(msgs) + " || LIST " + " ".join(listed)


def main():
    only = sys.argv[1:] or list(CASES)
    if os.environ.get("CASDIRECT_OURS_ONLY"):      # the knife runner's switch
        for n in only:
            zm = ZBN if CASES[n][0] == "tape" else ZBD
            print(f"== {n:8s} ours {reading(zm, n)}", flush=True)
        return 0
    bad, fault = [], False
    for n in only:
        medium = CASES[n][0]
        ref, rm, zm = ("VG-8020", VG, ZBN) if medium == "tape" else ("CF-3300", CF, ZBD)
        a, b = reading(rm, n), reading(zm, n)
        print(f"ROW {n:8s} {ref} [{a}] zerobas[{b}] {'SAME' if a == b else 'DIVERGES'}",
              flush=True)
        fault |= a is None
        if a != b:
            bad.append(n)
    if fault:
        print("\nINSTRUMENT FAULT: a reference gave no reading")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: a line with no number in an ASCII program "
          f"({len(only) - len(bad)}/{len(only)})" + (f" -- {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
