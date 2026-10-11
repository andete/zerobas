#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BLDS diagnostic (D-LOADERRRET's last unmeasured tape arm): `BLOAD"CAS:X",S`.
bload-body.inc refuses `,S` on tape with `load error` ("VRAM-from-tape not
supported"); on tape BSAVE's `S` is a VARIABLE (D-TAPETAIL), so the question is
whether the VG-8020's BLOAD takes `,S` as an offset expression.
Tape: binary X, 4 KB at &HC000, bytes 0..255 repeated.
  s0    S=0  : BLOAD"CAS:X",S  -> PEEK(&HC005), PEEK(&HC015)
  s16   S=16 : BLOAD"CAS:X",S  -> the same two cells (shifted by 16?)
  ctl   BLOAD"CAS:X"           -> the same two cells
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    for n in sys.argv[1:] or list(CASES):
        for side, m in (("VG-8020", REF), ("OURS", OURS)):
            print(f"== {n:4s} {side:8s} {reading(m, n)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
