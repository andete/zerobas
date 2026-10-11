#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASDIRECT diagnostic (D-LOADERRRET's content arms): an ASCII program on
tape with a line that has NO line number -- the VG-8020 against zerobas's
diskless machine. cload.asm's cas_ascii_load sends it to dpl_err, which prints
`load error` and returns; the reference's answer was never measured.

Tape: ASCII X = `10 PRINT"A"` / `PRINT"B"` / `30 PRINT"C"`.
  dload   LOAD"CAS:X" typed, then LIST          -> message + what was kept
  dmerge  NEW, 5 REM, MERGE"CAS:X" typed, LIST
  pload   10 ON ERROR GOTO 90 : 15 LOAD"CAS:X"  -> [E err erl] or message
  pmerge  10 ON ERROR GOTO 90 : 15 MERGE"CAS:X"
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
TAPE = cas_encode.build_cas_ascii("X", '10 PRINT"A"\nPRINT"B"\n30 PRINT"C"\n')
HANDLER = '90 PRINT"[E";ERR;ERL;"]":END'
CASES = {
    "dload": ["NEW", 'LOAD"CAS:X"', "@WAIT30", "LIST"],
    "dmerge": ["NEW", "5 REM", 'MERGE"CAS:X"', "@WAIT30", "LIST"],
    "pload": ["NEW", "10 ON ERROR GOTO 90", '15 LOAD"CAS:X"', '30 PRINT"[N";1;"]":END',
              HANDLER, "RUN", "@WAIT30", "LIST"],
    "pmerge": ["NEW", "10 ON ERROR GOTO 90", '15 MERGE"CAS:X"', '20 PRINT"[N";1;"]":END',
               HANDLER, "RUN", "@WAIT30", "LIST"],
}


# the DISK twin: MERGE's mrg_fin is shared by the tape and disk arms, and the
# disk LOAD has its own `jr c,dpl_err` -- the CF-3300 against the disk build
sys.path.insert(0, os.path.join(REPO, "tools"))
from make_test_dsk import Fat12Image               # noqa: E402
CF = "National_CF-3300"
ZBD = os.environ.get("ZEROBAS_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
DISKCASES = {
    "kmerge": ["NEW", "5 REM", 'MERGE"DIR.BAS"', "@WAIT6", "LIST"],
    "kload": ["NEW", 'LOAD"DIR.BAS"', "@WAIT6", "LIST"],
    "kpmerge": ["NEW", "10 ON ERROR GOTO 90", '15 MERGE"DIR.BAS"', '20 PRINT"[N";1;"]":END',
                HANDLER, "RUN", "@WAIT6", "LIST"],
    "kpload": ["NEW", "10 ON ERROR GOTO 90", '15 LOAD"DIR.BAS"', '30 PRINT"[N";1;"]":END',
               HANDLER, "RUN", "@WAIT6", "LIST"],
    # a BSAVE binary LOADed as a program -- ascii_load's comment says it trips the
    # same non-numbered-line arm, so the fix would move it too: measure first
    "kbinload": ["NEW", "5 REM", 'LOAD"BIN.BIN"', "@WAIT6", "LIST"],
}


def disk_image():
    img = Fat12Image()
    img.add_file("DIR", "BAS", b'10 PRINT"A"\r\nPRINT"B"\r\n30 PRINT"C"\r\n\x1a')
    from make_test_dsk import make_bsave_file
    img.add_file("BIN", "BIN", make_bsave_file(0xC000, 0xC00F, 0xC000, bytes(range(16))))
    path = probe_tmp.tmp("casdirect.dsk")
    open(path, "wb").write(img.finish())
    return path


def reading(machine, name):
    if name in DISKCASES:
        raw = omsx_repl.run_cases(machine, [("direct", DISKCASES[name])], batch=False,
                                  reset=("", "SCREEN 0"), diska=disk_image())[0] or ""
        flat = re.sub(r"\s+", " ", raw)
        i = flat.find('DIR.BAS"')
        return flat[i:i + 260] if i >= 0 else flat[-260:]
    path = probe_tmp.tmp("casdirect.cas")
    open(path, "wb").write(TAPE)
    raw = omsx_repl.run_cases(machine, [("direct", CASES[name])], batch=False,
                              reset=("", "SCREEN 0"), cassette=path)[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    i = flat.find('LOAD"CAS:X"') if "load" in name else flat.find('MERGE"CAS:X"')
    return flat[i:i + 260] if i >= 0 else flat[-260:]


def main():
    for n in sys.argv[1:] or list(CASES) + list(DISKCASES):
        pair = (("CF-3300", CF), ("OURS-D", ZBD)) if n in DISKCASES else \
            (("VG-8020", REF), ("OURS", OURS))
        for side, m in pair:
            print(f"== {n:6s} {side:8s} {reading(m, n)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
