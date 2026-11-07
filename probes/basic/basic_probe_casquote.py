#!/usr/bin/env python3
"""casquote-acceptance -- D-INPQUOTE2's cassette half (2026-11-07, fixed the same day): a STRING INPUT # field read from TAPE --
what follows a closing quote, and an unclosed one. Each row is its own encoded tape
(probes/lib/cas_encode.build_cas_ascii: an ASCII data file, CR LF lines, Ctrl-Z end);
the program reads it with INPUT #1,A$ then LINE INPUT #1,R$ and prints
[A$ with blanks as _ and quotes as # | LEN(A$) | R$ ERR], the disk probe's shape
(probes/disk/disk_probe_inpquote.py). VG-8020 vs zerobas NODISK. Typed BASIC in, the
screen out.

    python3 -u probes/basic/basic_probe_casquote.py [row...]
Exit 1 when a row is not SAME (a missing VG-8020 reading included).
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, cas_encode, probe_tmp                      # noqa: E402

ROWS = [("plain", 'AB\nNX'), ("quoted", '"  AB  "\nNX'), ("qcomma", '"A,B"\nNX'),
        ("qjunk", '"AB"CD\nNX'), ("qjunkc", '"AB"CD,EF\nNX'), ("qopen", '"AB,CD\nNX'),
        ("qmid", 'A"B"\nNX'), ("qlead", '  "AB"\nNX'), ("qsp", '"AB"  ,CD\nNX')]
SHOW = ('B$="":FOR I=1 TO LEN(A$):C$=MID$(A$,I,1):IF C$=" " THEN C$="_" ELSE IF C$=CHR$(34) THEN C$="#"',
        'B$=B$+C$:NEXT')
SIDES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))

def program():
    return ["NEW", "10 ON ERROR GOTO 90",
            '30 OPEN "CAS:F" FOR INPUT AS #1:INPUT #1,A$:LINE INPUT #1,R$:CLOSE',
            f"40 {SHOW[0]}", f"41 {SHOW[1]}",
            '60 PRINT CHR$(91);B$;"|";LEN(A$);"|";R$;E;CHR$(93):END',
            "90 E=ERR:RESUME 60", "RUN", "@WAIT30"]

def main():
    only = sys.argv[1:]
    bad = []
    for name, text in ROWS:
        if only and name not in only:
            continue
        tape = probe_tmp.tmp(f"inpquote_cas_{name}.cas")
        open(tape, "wb").write(cas_encode.build_cas_ascii("F", text))
        got = {}
        for side, m in SIDES:
            raw = omsx_repl.run_cases(m, [("direct", program())], batch=False,
                                      reset=("", "SCREEN 0"), cassette=tape)[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[side] = r[-1] if r else None
        v = "NO-REFERENCE" if got["VG"] is None else ("SAME" if got["VG"] == got["ZB"] else "DIVERGES")
        if v != "SAME":
            bad.append(name)
        print(f"ROW {name:7s} VG={got['VG']} ZB={got['ZB']} {v}", flush=True)
    print(__import__("probe_refcache").summary())
    print(f"{'PASS' if not bad else 'FAIL'}: INPUT # from tape ({len(bad)} not SAME: {bad})")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
