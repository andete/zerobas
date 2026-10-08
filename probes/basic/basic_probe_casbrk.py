#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASBRK: a tape LOAD / CLOAD / RUN broken with Ctrl-STOP while it searches
-- the VG-8020 against zerobas's diskless machine. One of D-LOADERRRET's
sites: cload.asm's `dpl_err` is `call load_error`, which PRINTS `load error`
and returns; castail's `cas-run-brk` counts ONE message on both machines but
maps each side's own text to one token (VG-8020 `Device I/O error`, ours
`load error`), so the text, and whether the code is TRAPPABLE, were never
read.

  dload   LOAD"CAS:NOSUCH" typed, broken           -> the message text
  pload   10 ON ERROR GOTO 90 : 20 LOAD"CAS:NOSUCH" -> `[E err erl]`
  pcload  the same with CLOAD"NOSUCH"
  prun    the same with RUN"CAS:NOSUCH"
  popen   the same with OPEN"CAS:NOSUCH"FOR INPUT AS#1 (files.asm's own
          header search -- castail's cas2-opencase, once its normaliser
          stopped hiding our `load error`)
  pmerge  the same with MERGE"CAS:NOSUCH"

No tape is inserted, so the search never ends by itself. Read as `[E err
erl]` (spelled so the typed source never matches) or the last message line.

Exit 0 all agree; 1 a divergence; 2 the reference gave no reading.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
BRK = ["@WAIT12", "@BREAK", "@WAIT8"]
HANDLER = ['90 PRINT"[E";ERR;ERL;"]":END']


def prog(verb):
    return ["NEW", "10 ON ERROR GOTO 90", f"20 {verb}", '30 PRINT"[N";1;"]":END'] \
        + HANDLER + ["RUN"] + BRK


CASES = {
    "dload": ["NEW", 'LOAD"CAS:NOSUCH"'] + BRK,
    "pload": prog('LOAD"CAS:NOSUCH"'),
    "pcload": prog('CLOAD"NOSUCH"'),
    "prun": prog('RUN"CAS:NOSUCH"'),
    "popen": prog('OPEN"CAS:NOSUCH"FOR INPUT AS#1'),
    "pmerge": prog('MERGE"CAS:NOSUCH"'),
}
RX_E = re.compile(r"\[E\s+(-?\d+)\s+(-?\d+)\s*\]")


def reading(machine, name):
    raw = omsx_repl.run_cases(machine, [("direct", CASES[name])], batch=False,
                              reset=("", "SCREEN 0"))[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    e = RX_E.findall(flat)
    if e:
        return f"E{e[-1][0]} in {e[-1][1]}"
    if "[N 1 ]" in flat:
        return "no error"
    m = re.findall(r"Device I/O error|load error|Break in \d+|Break", flat)
    return m[-1] if m else None


def main():
    only = sys.argv[1:] or list(CASES)
    got = {(t, n): reading(m, n) for t, m in (("VG-8020", REF), ("OURS", OURS)) for n in only}
    for n in only:
        print(f"== {n:6s} VG-8020 {got[('VG-8020', n)]!s:18s} ours {got[('OURS', n)]!s}")
    if any(got[("VG-8020", n)] is None for n in only):
        print("\nINSTRUMENT FAULT: the VG-8020 gave no reading -- no reference")
        return 2
    bad = [n for n in only if got[("VG-8020", n)] != got[("OURS", n)]]
    for n in bad:
        print(f"DIVERGES {n}: VG-8020 {got[('VG-8020', n)]} vs ours {got[('OURS', n)]}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a tape search broken with Ctrl-STOP "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
