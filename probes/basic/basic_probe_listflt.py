#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""listflt-acceptance (D-LISTFLT, reported by Vampier 2026-10-11): how LIST
spells a float literal, and that an ASCII SAVE / LOAD round trip keeps it.

zerobas's detokeniser had no arm for the float-literal tokens ($1D single,
$1F double): LIST and ASCII SAVE printed the value bytes as themselves
(`321 i=0.123456789` -> `321 I=@14VxSTOP`), so a SAVE "X",A of such a program
wrote garbage.

  rows A: 24 literals typed, LISTed -- VG-8020 vs the diskless build. The
          reference's spelling is PRINT's text without the sign space, then
          `#` on a double in fixed form, `!` on a single in fixed form with no
          '.', nothing in E form.
  row  B: type, SAVE "T.BAS",A, NEW, LOAD, LIST, RUN -- CF-3300 vs the disk
          build, everything from LOAD on (the prompt word aside).
Clean room: typed BASIC and the screen.
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "tools"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
from make_test_dsk import Fat12Image               # noqa: E402

VG, ZBN = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
CF, ZBD = "National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"
ROUNDS = (["0.123456789", "1.5", "0.5", "1E10", "1.5#", "1.5!", "123456789",
           "3.14159265358979", "1.5D3", "2E-5", "12345678", "40000"],
          ["1.5D20", "1E20", "1.5E-10", "0.05", "1234567", "123456", "0.0",
           "-1.5", "1.23456789012345678", "1D-20", "100000", "0.1"])
TRIP = ["NEW", "10 A=0.123456789:B=1.5E-10", "20 C=40000:D=1.5D20:E=0.05",
        "30 PRINT A;B;C;D;E", 'SAVE"T.BAS",A', "NEW", 'LOAD"T.BAS"', "LIST", "RUN"]


def listed(machine, lits):
    lines = ["NEW"] + [f"{100 + i} A={v}" for i, v in enumerate(lits)] + ["LIST"]
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"))[0] or ""
    flat = raw.replace("\n", "")
    rows = [flat[k:k + 40].strip() for k in range(0, len(flat), 40)]
    return {r.split(" ", 1)[0]: r for r in rows if re.match(r"1\d\d A", r)}


def trip(machine):
    p = probe_tmp.tmp("listflt_gate.dsk")
    open(p, "wb").write(Fat12Image().finish())
    raw = omsx_repl.run_cases(machine, [("direct", TRIP)], batch=False,
                              reset=("", "SCREEN 0"), diska=p)[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    i = flat.rfind('LOAD"T.BAS"')
    return flat[i:].replace("Ok", "ZB") if i >= 0 else None


def main():
    bad, fault = [], False
    for n, lits in enumerate(ROUNDS, 1):
        ref, ours = listed(VG, lits), listed(ZBN, lits)
        fault |= len(ref) != len(lits)
        for k in sorted(set(ref) | set(ours)):
            same = ref.get(k) == ours.get(k)
            print(f"ROW r{n}:{k} VG-8020 [{ref.get(k)}] zerobas [{ours.get(k)}] "
                  f"{'SAME' if same else 'DIVERGES'}", flush=True)
            if not same:
                bad.append(f"r{n}:{k}")
    a, b = trip(CF), trip(ZBD)
    fault |= a is None
    print(f"ROW trip CF-3300 [{a}]\n         zerobas [{b}] {'SAME' if a == b else 'DIVERGES'}")
    if a != b:
        bad.append("trip")
    if fault:
        print("\nINSTRUMENT FAULT: a reference gave no (or a short) reading")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: LIST and ASCII SAVE spell float literals as "
          f"the references do" + (f" -- {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
