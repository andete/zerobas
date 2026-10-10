# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DIMRESERVE S2 (gate: prec-acceptance): arithmetic precedence and
associativity, VG-8020 vs zerobas. The arithmetic levels became a precedence
climber on 2026-10-10 (basic/expr.asm ev_e / ev_pw); this pins what the old
five hand-written levels did and the reference does:

  chains at ONE level (left-assoc):  sub3 10-2-3   mix 10-2+3   div3 100/10/2
                                     pow3 2^3^2    idiv3 20\\4\\2   mul3 2*3/4
  mixed levels:                      addmul 1+2*3   mulpow 2*3^2   negpow -2^2
                                     modmul 7 MOD 4*2   idivmod 2+7\\2 MOD 3
                                     modchain 17 MOD 5 MOD 3
Each case prints its value in brackets. `ROW <name> VG=[...] ZB=[...] <verdict>`;
exit 0 all agree, 1 a divergence, 2 the VG-8020 gave no reading.
Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "sub3": "10-2-3", "mix": "10-2+3", "div3": "100/10/2", "pow3": "2^3^2",
    "idiv3": "20\\4\\2", "mul3": "2*3/4", "addmul": "1+2*3", "mulpow": "2*3^2",
    "negpow": "-2^2", "modmul": "7 MOD 4*2", "idivmod": "2+7\\2 MOD 3",
    "modchain": "17 MOD 5 MOD 3",
}


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    out = [x.strip() for x in r if x.strip().startswith("[")]
    return " | ".join(out) if out else "<NOTHING PRINTED>"


def main():
    only = sys.argv[1:] or list(CASES)
    lines = [f'PRINT "[";{CASES[n]};"]"' for n in only]
    got = {}
    for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
        out = omsx_repl.run_cases(m, [("direct", [ln]) for ln in lines], batch=True,
                                  reset=("CLS",), step=2.5)
        got[side] = [rows(o) for o in out]
    bad, blind = [], []
    for i, name in enumerate(only):
        vg, zb = got["VG"][i], got["ZB"][i]
        if vg is None:
            verdict = "NO-REFERENCE"
            blind.append(name)
        elif vg == zb:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{vg}] ZB=[{zb}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: arithmetic precedence "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
