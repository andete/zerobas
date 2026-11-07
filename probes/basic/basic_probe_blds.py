#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""blds-acceptance -- D-BLDS (gated 2026-11-07, fixed in sub2/loadsave.asm ls_pcr_bload). Was the diagnostic (D-LOADERRRET's last unmeasured tape arm): `BLOAD"CAS:X",S`.
bload-body.inc refuses `,S` on tape with `load error` ("VRAM-from-tape not
supported"); on tape BSAVE's `S` is a VARIABLE (D-TAPETAIL), so the question is
whether the VG-8020's BLOAD takes `,S` as an offset expression.
Tape: binary X, 4 KB at &HC000, bytes 0..255 repeated.
  s0    S=0  : BLOAD"CAS:X",S  -> PEEK(&HC005), PEEK(&HC015)
  s16   S=16 : BLOAD"CAS:X",S  -> the same two cells (shifted by 16?)
  ctl   BLOAD"CAS:X"           -> the same two cells
--gate: zerobas's `[P a b ]` reading must equal the VG-8020's on every row, which must
answer (scratchpad/blds_diag.out is the pre-fix reading: `load error` on s0 / s16).
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import cas_encode                                  # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
TAPE = cas_encode.build_cas("X", 0xC000, 0xC000, bytes(range(256)) * 16)
PEEKS = 'PRINT"[P";PEEK(&HC005);PEEK(&HC015);"]"'
CASES = {
    "s0": ["NEW", "POKE&HC005,99:POKE&HC015,99", "S=0", 'BLOAD"CAS:X",S', "@WAIT40", PEEKS],
    "s16": ["NEW", "POKE&HC005,99:POKE&HC015,99", "S=16", 'BLOAD"CAS:X",S', "@WAIT40", PEEKS],
    "ctl": ["NEW", "POKE&HC005,99:POKE&HC015,99", 'BLOAD"CAS:X"', "@WAIT40", PEEKS],
}


def reading(machine, name):
    path = probe_tmp.tmp("blds.cas")
    open(path, "wb").write(TAPE)
    raw = omsx_repl.run_cases(machine, [("direct", CASES[name])], batch=False,
                              reset=("", "SCREEN 0"), cassette=path)[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    i = flat.find('BLOAD"CAS:X"')
    return flat[i:i + 150]


def main():
    gate = "--gate" in sys.argv
    bad = []
    for n in [a for a in sys.argv[1:] if a != "--gate"] or list(CASES):
        got = {}
        for side, m in (("VG-8020", REF), ("OURS", OURS)):
            r = reading(m, n)
            print(f"== {n:4s} {side:8s} {r}", flush=True)
            # the PRINTED reading, never the typed echo (`PRINT"[P";...` -- an echo
            # carries `";`): with the echo admitted, two machines printing NOTHING
            # would agree [[trapsvc-echo-fence]]
            got[side] = [x for x in re.findall(r"\[P [^\]]*\]", r) if '";' not in x]
        ref, ours = got["VG-8020"], got["OURS"]
        if not ref:
            bad.append(f"{n}: the VG-8020 printed no [P ...] reading")
        elif ours[-1:] != ref[-1:]:
            bad.append(f"{n}: zerobas {ours[-1:]}, VG-8020 {ref[-1:]}")
    if gate:
        print(f"blds: {3 - len(bad)}/3 rows agree" + ("" if not bad else "; " + "; ".join(bad)))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
