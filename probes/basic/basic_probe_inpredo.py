#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-INPQUOTE2's console half (gate: inpredo-acceptance): what may follow a
closing quote typed at INPUT A$.

On the VG-8020 blanks and a comma may follow it (`"AB"  ` and `"AB" ,CD` read
AB); anything else -- `"AB"CD`, `"AB" CD`, `"AB""` -- is `?Redo from start`
and the statement asks again (scratchpad/inpquote_console.out). zerobas took
AB until 2026-11-05 (basic/files.asm ris_quoted).

⚠️ A REDO ROW IS READ BY ITS SECOND ANSWER, NOT BY ITS SILENCE. A machine that
asks again and one that hung both "give no reading" after the first line, so
every row types a second line, XY: a redo row must end with A$ = XY AND show
`Redo` on the screen; a row that took the first answer ends with its own
value and no `Redo`. Exit 0 all agree, 1 a divergence, 2 the VG-8020 gave no
reading. Clean-room: typed BASIC in, the screen out.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

TYPED = ['"AB"CD', '"AB"  ', '"AB" ,CD', '"AB",CD', '"AB" CD', '"AB""', '"AB']
PROG = ["NEW", "10 INPUT A$", '20 PRINT CHR$(91);A$;"|";LEN(A$);CHR$(93):END', "RUN"]
SIDES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))


def reading(raw):
    if not raw:
        return None
    flat = " ".join(str(raw).split())
    r = re.findall(r"\[[^\]\"]*\]", flat)
    if not r:
        return None
    return r[-1] + (" +Redo" if "Redo" in flat else "")


def main():
    bad, blind = [], []
    for v in TYPED:
        got = {}
        for side, m in SIDES:
            raw = omsx_repl.run_cases(m, [("direct", PROG + [v, "XY"])], batch=False,
                                      reset=("CLS",), capture="screen", step=4.0)[0]
            got[side] = reading(raw)
        if got["VG"] is None:
            blind.append(v)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(v)
        print(f"ROW {v!r:10} VG={got['VG']} ZB={got['ZB']} {verdict}", flush=True)
    print(__import__("probe_refcache").summary())
    if blind:
        print(f"INSTRUMENT FAULT: the VG-8020 gave no reading on {blind}")
        return 2
    print(f"{'PASS' if not bad else 'FAIL'}: console quote rows ({len(bad)} diverge)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
