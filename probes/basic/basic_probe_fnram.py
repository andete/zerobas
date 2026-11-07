#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""fnram-acceptance -- D-FNRAM (2026-11-07; Joost on D-FNALIAS: "measure what reference
does? we try to match RAM?"). The free memory a DEF FN call with arguments costs,
read with FRE(0), against the VG-8020 (TIER 4: RAM usage, VG-8020). BASIC only.

  body rows   FRE(0) IS the body, N formals: the call costs 25 bytes on both
              references whatever N and the type (zerobas 24: its frame was 13 B)
  nest1       one FN calling another: 36 more per level (zerobas 35)
  peak rows   FRE(0) as the LAST actual, after N parked actuals: 27 + 12 per actual
              on both references, single / double / string variable / literal alike
              (zerobas read 34 whatever N: its FRE model charged an FN call as a
              built-in function and the parked actuals nothing)
Measured: scratchpad/fnram_run.out, scratchpad/fnram_peak.out (before),
scratchpad/fnram_after2.out (after). Fixed by a 14-byte FN frame (sub/deffn.asm)
and the FN classes of the FRE model (sub2/frelive.asm).

--gate: every row's differences (the cost) equal the VG-8020's.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides                               # noqa: E402

LET = "ABCDEFGHI"


def body(tag, sfx, actual, n):
    forms = ",".join(f"{LET[i]}{sfx}" for i in range(n))
    use = "+".join((f"0*LEN({LET[i]}$)" if sfx == "$" else f"0*{LET[i]}{sfx}")
                   for i in range(n)) or "0"
    head = f"DEF FNA({forms})" if n else "DEF FNA"
    call = f"FNA({','.join([actual] * n)})" if n else "FNA"
    return ['10 CLEAR 300:Z$="QQ"', f"20 {head}=FRE(0)+{use}", f"30 F0=FRE(0):F1={call}",
            f'40 PRINT CHR$(91);"{tag}";F0-F1;CHR$(93)', "RUN"]


def peak(tag, sfx, actual, n):
    forms = ",".join([f"{LET[i]}{sfx}" for i in range(n)] + ["J"])
    call = "FNA(" + ",".join([actual] * n + ["FRE(0)"]) + ")"
    return ['10 CLEAR 300:Z$="QQ"', f"20 DEF FNA({forms})=J", f"30 F0=FRE(0):F1={call}",
            f'40 PRINT CHR$(91);"{tag}";F0-F1;CHR$(93)', "RUN"]


ROWS = [("b0", body("b0", "", "1", 0)), ("b9", body("b9", "", "1", 9)),
        ("bd9", body("bd9", "#", "1", 9)), ("bz9", body("bz9", "$", "Z$", 9)),
        ("nest1", ["10 CLEAR 300", "20 DEF FNB(X)=FRE(0)+0*X", "25 DEF FNA(X)=FNB(X)+0*X",
                   "30 F0=FRE(0):F1=FNB(1):F2=FNA(1)",
                   '40 PRINT CHR$(91);"nest1";F0-F1;F1-F2;CHR$(93)', "RUN"]),
        ("p0", peak("p0", "", "1", 0)), ("p1", peak("p1", "", "1", 1)),
        ("p8", peak("p8", "", "1", 8)), ("pd5", peak("pd5", "#", "1", 5)),
        ("pz8", peak("pz8", "$", "Z$", 8)), ("pl5", peak("pl5", "$", '"AB"', 5))]


def fence(tag, cap):
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0:
            return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]:
            v = c[i + len(tag) + 1:j].split()
            return v if v and all(x.lstrip("-").isdigit() for x in v) else None
        k = i


def main():
    gate = "--gate" in sys.argv
    only = [a for a in sys.argv[1:] if a != "--gate"]
    cfg = probe_sides.sides("vg8020", "zb")
    bad, n = [], 0
    for tag, p in ROWS:
        if only and tag not in only:
            continue
        n += 1
        got = {}
        for side in ("vg8020", "zb"):
            cap = omsx_repl.run_cases(cfg[side]["machine"], [(tag, p)], batch=False,
                                      boot=cfg[side]["boot"], reset=cfg[side]["reset"],
                                      run_gap=6.0)[0]
            got[side] = fence(tag, cap)
        print(f"== {tag:6s} vg8020={got['vg8020']} zb={got['zb']}", flush=True)
        if got["vg8020"] is None:
            bad.append(f"{tag}: the VG-8020 printed no reading")
        elif got["zb"] != got["vg8020"]:
            bad.append(f"{tag}: zerobas {got['zb']}, VG-8020 {got['vg8020']}")
    if gate:
        print(f"fnram: {n - len(bad)}/{n} rows agree" + ("" if not bad else "; " + "; ".join(bad)))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
