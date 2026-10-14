#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BLOADRTAIL (gate: bloadrtail-acceptance): what runs after `BLOAD"CAS:",R`.

On the VG-8020 `,R` CALLS the loaded program, and when it returns the rest of
the line runs: `BLOAD"CAS:T",R:PRINT"[OK]"` prints [OK], direct and in a
program, whatever the code does to HL/DE/BC. zerobas jumped to it, so its `ret`
went back past the statement and the line -- in a program, the RUN -- ended
silently. Tape loaders of the shape `BLOAD"CAS:",R` followed by more BASIC
stopped at the prompt after `Found:` (found 2026-10-14 by D-TAPELOAD's triage).

The tapes are OUR OWN, built per run with cas_encode: `ret` (a bare `ret`),
`clob` (HL/DE/BC zeroed, then `ret`), `ran` (stores 42 at &HD100, so the row
proves the code ran), and a two-file tape for `chain` (two `,R` loads in one
line, the multi-part loader shape).

Each row prints `ROW <name> VG=[...] ZB=[...] <verdict>`.
Exit 0 all agree; 1 a divergence; 2 the VG-8020 gave no reading.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

RET = bytes([0xC9])
CLOB = bytes([0x21, 0, 0, 0x11, 0, 0, 0x01, 0, 0, 0xC9])
RAN = bytes([0x3E, 42, 0x32, 0x00, 0xD1, 0xC9])      # ld a,42 / ld (&HD100),a / ret

TAPES = {"ret": build_cas("T", 0xD000, 0xD000, RET),
         "clob": build_cas("T", 0xD000, 0xD000, CLOB),
         "ran": build_cas("T", 0xD000, 0xD000, RAN),
         "chain": build_cas("A", 0xD000, 0xD000, RET) + build_cas("B", 0xD000, 0xD000, RAN)}

CASES = {
    "ret": ("ret", ['BLOAD"CAS:T",R:PRINT"[OK]"']),
    "clob": ("clob", ['BLOAD"CAS:T",R:PRINT"[OK]"']),
    "prog": ("clob", ["NEW", '10 BLOAD"CAS:T",R:PRINT"[OK]"', '20 PRINT"[L20]"', "RUN"]),
    "ran": ("ran", ['POKE&HD100,0:BLOAD"CAS:T",R:PRINT"[";PEEK(&HD100);"]"']),
    "chain": ("chain", ['POKE&HD100,0:BLOAD"CAS:A",R:BLOAD"CAS:B",R:PRINT"[";PEEK(&HD100);"]"']),
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    keep = [x for x in r if x.startswith("[") or "error" in x.lower()]
    return " | ".join(keep)


def main():
    only = sys.argv[1:] or list(CASES)
    tmp = tempfile.mkdtemp(prefix="bloadrtail_")
    bad, blind = [], []
    for name in only:
        tape, lines = CASES[name]
        path = os.path.join(tmp, f"{name}.cas")
        open(path, "wb").write(TAPES[tape])
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            got[side] = rows(omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=30.0, cassette=path)[0])
        if not got["VG"]:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: BLOAD\"CAS:\",R then the rest of the line "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
