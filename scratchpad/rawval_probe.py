#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RAWVAL — the SECOND argument of POKE / VPOKE / OUT has no domain at all.

From the standing per-statement review tier, whose worklist names the raw-I/O
trio FIRST and says why: *"the coercion SURFACE is gated, the port/address
MECHANISM never reviewed"*. Reading all three handlers before writing any row,
the surface turns out to be gated on the wrong argument.

`intarg-acceptance` has eleven rows for these verbs and EVERY ONE is about the
FIRST argument -- poke_addr_ovf, poke_neg, vpoke_vram, vpoke_ill, vpoke_neg,
wait_port_ovf ... The second argument is unrepresented, and all three handlers
treat it identically:

    call eval_addr          ; the int16 domain: ERR 6 only beyond +-32767
    ...
    call check_fperr_only
    ld   a,e                ; <- the LOW BYTE, silently

\U0001f3af SO THE PREDICTION IS A WRAP, NOT A MISSING ERROR CODE. `POKE x,256`
should write nothing and raise; if this reading is right it writes **0**, and
`POKE x,-1` writes **255**. That is the D-PLAYCORNER class exactly, and it is
why every row below PEEKs the target back instead of only reading `ERR`.

\U0001f534 THE TREE ALREADY HAS THE LEAF THIS WANTS. `get_byte_arg` (0..255,
ERR 5 outside) is what `STRING$`'s char code uses -- `STRING$(5,256)` is a GATED
ERR 5 row. So `STRING$`'s byte is checked and `POKE`'s is not, in one tree, which
is the asymmetry that makes this worth measuring rather than assuming.

Each row PRIMES the target with 65 first, so a raise leaves 65 and only a write
changes it: the witness distinguishes "refused" from "wrote something".
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
# &HD020: between the variable area and the string pool on both references --
# the same scratch window casfch_probe writes at &HD014..&HD016.
# VRAM 16000: past everything SCREEN 0 uses (name table 0..959, patterns
# 2048..4095), so a write there cannot disturb the display the probe reads over.
PRIME = ["20 POKE &HD020,65", "25 VPOKE 16000,65"]
CASES = [
    ("p.ctl",  "POKE &HD020,42",  "PEEK(&HD020)",  "CONTROL: a legal byte"),
    ("p.255",  "POKE &HD020,255", "PEEK(&HD020)",  "the boundary that IS legal"),
    ("p.256",  "POKE &HD020,256", "PEEK(&HD020)",  "first illegal -- 0 = wrapped"),
    ("p.neg",  "POKE &HD020,-1",  "PEEK(&HD020)",  "negative -- 255 = wrapped"),
    ("v.ctl",  "VPOKE 16000,42",  "VPEEK(16000)",  "CONTROL: a legal byte"),
    ("v.256",  "VPOKE 16000,256", "VPEEK(16000)",  "first illegal"),
    ("v.neg",  "VPOKE 16000,-1",  "VPEEK(16000)",  "negative"),
    ("o.256",  "OUT 0,256",       "0",             "port 0 is undecoded on MSX1"),
    ("o.neg",  "OUT 0,-1",        "0",             "no witness -- the code is it"),
    # --- PRECEDENCE: which error wins when BOTH arguments are bad? ------------
    # The fix moves the value onto eval_byte_checked, which raises ERR 5 at the
    # point of evaluation, where today check_fperr_only surfaces the ADDRESS's
    # ERR 6 afterwards. If ERR 5 started winning, `POKE 99999,256` would change
    # answer -- and no gated row would notice, because every existing row pairs a
    # bad address with a LEGAL value. Measured first, fixed second.
    ("x.both", "POKE 99999,256",  "PEEK(&HD020)",  "bad addr AND bad value"),
    ("x.vovf", "POKE &HD020,99999", "PEEK(&HD020)", "value beyond int16"),
    # --- and OUT's PORT has no rows anywhere either --------------------------
    ("x.port", "OUT 256,0",       "0",             "port beyond a byte"),
    ("x.pneg", "OUT -1,0",        "0",             "negative port"),
]


def main() -> int:
    out = {}
    for tag, stmt, wit, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 100"] + PRIME + [
                f"30 {stmt}",
                f'40 PRINT"ZQ";0;",";{wit};"QZ":END',
                f'100 PRINT"ZQ";ERR;",";{wit};"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([0-9]+)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"ERR={row[s_][0]} got={row[s_][1]}") for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:7s} {stmt:18s} vg={f['vg8020']:20s} cf={f['cf3300']:20s} "
              f"zb={f['zb']:20s}{mark}", flush=True)

    for ctl in ("p.ctl", "v.ctl"):
        r = out.get(ctl, {})
        if any(r.get(s_) is None or r[s_] != ("0", "42") for s_ in SIDES):
            print(f"\n\U0001f534 CONTROL {ctl} DID NOT READ ERR 0 / 42 ({r}) -- the "
                  f"probe is not writing or not reading where it thinks, and no "
                  f"row above means anything.")
            return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    ref = out.get("p.256", {}).get("cf3300")
    if ref:
        print(f"  \U0001f3af `POKE x,256` on the reference: ERR {ref[0]}, target "
              f"left at {ref[1]}" +
              ("  -> REFUSED (the byte domain is real)" if ref[1] == "65" else
               "  -> WROTE; the reference wraps too and there is no defect here"))
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
