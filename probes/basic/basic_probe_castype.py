#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASTYPE: does a tape verb's search FILTER BY FILE TYPE? -- the VG-8020
against zerobas's diskless machine.

Filed by D-CASBRK: MERGE and OPEN "CAS:X" FOR INPUT found a TOKENISED X and
then REJECTED it here -- MERGE through `mc_ioerr` -> `disk_error` (the pending
disk code: 255 on the diskless machine), OPEN through `oocas_ioerr` ->
`load_error` (printed, returned, untrappable). The VG-8020 does neither: it
searched on, and Ctrl-STOP read `19 in 20`. A first control here typed
LOAD"CAS:X" on that tape and the VG-8020 gave NO reading -- LOAD "CAS:" skipped
the tokenised X too, where ours LOADED it. So the question is the matcher's
rule, and two rules agree on a one-file tape:
  (a) match by NAME, then the verb accepts or rejects the type (ours)
  (b) match by NAME AND TYPE, skipping a wrong-typed file like a wrong name
The separating tapes hold the SAME name twice, once per type, in both orders.

  T  = X tokenised ("10 END")              A = X ascii ("20 STOP")
  TA = T then A                            AT = A then T

  lta    LOAD"CAS:X" on TA, LIST     (b): 20 STOP   (a): 10 END
  cat    CLOAD"X" on AT, LIST        (b): 10 END    (a): 20 STOP
  lbta   LOAD"CAS:" (bare) on TA     (b): 20 STOP   (a): 10 END
  cbat   CLOAD (bare) on AT          (b): 10 END    (a): 20 STOP
  mta    MERGE"CAS:X" on TA, LIST    (b): 20 STOP   (a): an error
  ota    OPEN"CAS:X"FOR INPUT on TA, LINE INPUT#1   (b): 20 STOP  (a): an error
  mt     MERGE"CAS:X" on T alone, ON ERROR, broken after 20 s   -> `[E err erl]`
  ot     OPEN"CAS:X"FOR INPUT on T alone, likewise
  skip   the screen's `Skip :` count for lta (does a type skip print a row?)

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
# "10 END" at the text base $8001: link $8007, line 10, END ($81), 00; then $0000
PROG = bytes([0x07, 0x80, 0x0A, 0x00, 0x81, 0x00, 0x00, 0x00])
# 🔴 build_cas_basic_csave, NOT build_cas_basic: the latter pads SIXTEEN $00
# after the end-link (single-file framing), where CSAVE writes SEVEN on all three
# machines. The first cut used it, and every row that SKIPS the tokenised file to
# reach the ASCII one read `Device I/O error` on ours -- the VG-8020 rides over
# the extra nine bytes, ours relocks past seven (D-CASRELOCK). A tape no machine
# writes, measured as a defect: D-CLOADSKIP made the same mistake on 09-23.
TOK = cas_encode.build_cas_basic_csave("X", PROG)
ASC = cas_encode.build_cas_ascii("X", "20 STOP\n")
TAPES = {"T": TOK, "A": ASC, "TA": TOK + ASC, "AT": ASC + TOK}
BRK = ["@WAIT20", "@BREAK", "@WAIT8"]
LOADW = ["@WAIT25"]


def prog(verb):
    return ["NEW", "10 ON ERROR GOTO 90", f"20 {verb}", '30 PRINT"[N";1;"]":END',
            '90 PRINT"[E";ERR;ERL;"]":END', "RUN"] + BRK


# name -> (tape, lines, kind)
CASES = {
    "lta": ("TA", ["NEW", 'LOAD"CAS:X"'] + LOADW + ["LIST"], "list"),
    "cat": ("AT", ["NEW", 'CLOAD"X"'] + LOADW + ["LIST"], "list"),
    "lbta": ("TA", ["NEW", 'LOAD"CAS:"'] + LOADW + ["LIST"], "list"),
    "cbat": ("AT", ["NEW", "CLOAD"] + LOADW + ["LIST"], "list"),
    "mta": ("TA", ["NEW", 'MERGE"CAS:X"'] + LOADW + ["LIST"], "list"),
    "ota": ("TA", ["NEW", 'OPEN"CAS:X"FOR INPUT AS#1'] + LOADW
            + ['LINE INPUT#1,A$:PRINT"[R";A$;"]"'], "read"),
    "mt": ("T", prog('MERGE"CAS:X"'), "err"),
    "ot": ("T", prog('OPEN"CAS:X"FOR INPUT AS#1'), "err"),
}
RX_E = re.compile(r"\[E\s+(-?\d+)\s+(-?\d+)\s*\]")


def tape(kind):
    path = probe_tmp.tmp(f"castype_{kind}.cas")
    open(path, "wb").write(TAPES[kind])
    return path


def reading(machine, name):
    kind, lines, how = CASES[name]
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), cassette=tape(kind))[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    skips = flat.count("Skip :")
    errs = re.findall(r"Device I/O error|load error|[A-Z][a-z]+(?: [a-z/]+)* error|"
                      r"Bad file mode|Bad file name|Unprintable error", flat)
    if how == "list":
        tail = flat.split("LIST", 1)[1] if "LIST" in flat else ""
        got = re.findall(r"\b(10 END|20 STOP)\b", tail)
        r = " + ".join(got) if got else (errs[-1] if errs else "nothing listed")
    elif how == "read":
        m = re.findall(r"\[R([A-Z0-9 ]+)\]", flat)
        r = f"read {m[-1].strip()}" if m else (errs[-1] if errs else None)
    else:
        e = RX_E.findall(flat)
        r = (f"E{e[-1][0]} in {e[-1][1]}" if e else
             "no error" if "[N 1 ]" in flat else (errs[-1] if errs else None))
    return r, skips


def main():
    only = sys.argv[1:] or list(CASES)
    got = {(t, n): reading(m, n) for t, m in (("VG-8020", REF), ("OURS", OURS)) for n in only}
    for n in only:
        (rv, sv), (ro, so) = got[("VG-8020", n)], got[("OURS", n)]
        print(f"== {n:5s} VG-8020 {rv!s:20s} skip {sv}   ours {ro!s:20s} skip {so}")
    if any(got[("VG-8020", n)][0] is None for n in only):
        print("\nINSTRUMENT FAULT: the VG-8020 gave no reading -- no reference")
        return 2
    bad = [n for n in only if got[("VG-8020", n)] != got[("OURS", n)]]
    for n in bad:
        print(f"DIVERGES {n}: VG-8020 {got[('VG-8020', n)]} vs ours {got[('OURS', n)]}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a tape search filters by file type "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
