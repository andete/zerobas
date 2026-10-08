#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASPRDIR (gate: casprdir-acceptance): writing to a tape channel opened FOR
INPUT, and reading one opened FOR OUTPUT, under ON ERROR -- the VG-8020 against
zerobas's diskless machine. One of D-LOADERRRET's sites: print.asm sent the
first to `load_error`, which prints and RETURNS (untrappable), and the item
filed it as needing a TAPE FIXTURE -- which the Vleermuis side experiment's
ASCII tape builder (probes/lib/cas_encode.build_cas_ascii) now is.

  ctl    OPEN"CAS:D"FOR INPUT AS#1 : LINE INPUT#1,A$ -> the first line   (the
         control: the tape is found and read on both machines)
  pin    OPEN"CAS:D"FOR INPUT AS#1 : PRINT#1,"X"     -> ERR / ERL
  outin  OPEN"CAS:T"FOR OUTPUT AS#1 : INPUT#1,A$     -> ERR / ERL

Read as `[E err erl]`, `[N 1 ]` (no error) or `[R<line>]`; the markers are
spelled so the typed source never matches them (the echo fence).

Exit 0 all agree; 1 a divergence; 2 the reference gave no reading.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
TAIL = ['40 PRINT"[N";1;"]":END', '90 PRINT"[E";ERR;ERL;"]":END', "RUN", "@WAIT60"]
CASES = {
    "ctl": ["NEW", "10 ON ERROR GOTO 90", '20 OPEN"CAS:D"FOR INPUT AS#1',
            '30 LINE INPUT#1,A$:PRINT"[R";A$;"]":END'] + TAIL,
    "pin": ["NEW", "10 ON ERROR GOTO 90", '20 OPEN"CAS:D"FOR INPUT AS#1',
            '30 PRINT#1,"X"'] + TAIL,
    "outin": ["NEW", "10 ON ERROR GOTO 90", '20 OPEN"CAS:T"FOR OUTPUT AS#1',
              "30 INPUT#1,A$"] + TAIL,
}
RX = re.compile(r"\[E\s+(-?\d+)\s+(-?\d+)\s*\]|\[N 1 \]|\[R([A-Z]+)\]")


def tape():
    path = probe_tmp.tmp("casprdir.cas")
    open(path, "wb").write(cas_encode.build_cas_ascii("D", "HELLO\nWORLD\n"))
    return path


def reading(machine, name):
    raw = omsx_repl.run_cases(machine, [("direct", CASES[name])], batch=False,
                              reset=("", "SCREEN 0"), cassette=tape())[0] or ""
    hits = RX.findall(re.sub(r"\s+", " ", raw))
    if not hits:
        return None
    e, l, r = hits[-1]
    return f"E{e} in {l}" if e else (f"R {r}" if r else "no error")


def main():
    only = sys.argv[1:] or list(CASES)
    got = {(t, n): reading(m, n) for t, m in (("VG-8020", REF), ("OURS", OURS)) for n in only}
    for n in only:
        print(f"== {n:6s} VG-8020 {got[('VG-8020', n)]!s:14s} ours {got[('OURS', n)]!s}")
    if any(got[("VG-8020", n)] is None for n in only):
        print("\nINSTRUMENT FAULT: the VG-8020 gave no reading -- no reference")
        return 2
    bad = [n for n in only if got[("VG-8020", n)] != got[("OURS", n)]]
    for n in bad:
        print(f"DIVERGES {n}: VG-8020 {got[('VG-8020', n)]} vs ours {got[('OURS', n)]}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a tape channel used against its "
          f"direction ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
