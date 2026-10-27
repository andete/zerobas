#!/usr/bin/env python3
"""D-DEFERRSTUDY: is the published error hook H.ERRO ($FFB1) called when an error is
raised, and what is VALTYP ($F663) at that moment? (VG-8020 vs zerobas)

A RAM routine at $D000 copies VALTYP to $D010 and bumps a counter at $D011; H.ERRO gets
`JP $D000`. Our own RAM code, read back through RAM: nothing of the reference's ROM is
read. Explains prototype test_forint's one differing field (FACTYP = $F663 at the error
boundary: 8 with deferral, 2 when Division by zero is raised at once).

    python3 -u scratchpad/herro_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

SETUP = ['POKE-12288,58:POKE-12287,99:POKE-12286,246',       # ld a,($F663)
         'POKE-12285,50:POKE-12284,16:POKE-12283,208',       # ld ($D010),a
         'POKE-12282,33:POKE-12281,17:POKE-12280,208',       # ld hl,$D011
         'POKE-12279,52:POKE-12278,201',                     # inc (hl) / ret
         'POKE-12272,255:POKE-12271,0',                      # VALTYP cell, counter
         'POKE-78,0:POKE-77,208:POKE-79,195']                # H.ERRO := JP $D000
READ = 'PRINT"[V";PEEK(-12272);"C";PEEK(-12271);"]"'
CASES = {
    "ctl_none":  'I%=3:X=10/(I%-2)',
    "div_int":   'I%=3:X=10/(I%-3)',
    "div_sng":   'X!=0:Y=10/X!',
    "sqr":       'X=SQR(-1)',
    "intdiv":    'I%=0:X=10\\I%',
    "syntax":    'X=1+',
    "log0":      'X=LOG(0)',
    "pow0":      'X=0^-1',
    "negfrac":   'X=(-2)^.5',
    "asc":       'X=ASC("")',
}


def main():
    for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
        for name, stmt in CASES.items():
            lines = SETUP + [stmt, READ]
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=10.0,
                                      reset=("SCREEN 0:WIDTH 40",), step=3.0, run_gap=4.0)[0]
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            i = max((k for k, r in enumerate(rows) if r == stmt[:40]), default=-1)
            after = [r for r in rows[i + 1:] if r and r not in ("Ok", "ZB") and r != READ[:40]
                     and not r.startswith("color")]
            print(f"{m:30s} {name:9s} {stmt:20s} {' | '.join(after)}", flush=True)


if __name__ == "__main__":
    main()
