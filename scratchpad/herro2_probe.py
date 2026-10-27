#!/usr/bin/env python3
"""D-HERRO: what does the published error hook H.ERRO ($FFB1) see? (VG-8020 vs zerobas)

scratchpad/herro_probe.py showed the VG-8020 calls H.ERRO once per error and zerobas
never does. This routine (our own RAM code at $D000, read back through RAM) records, at
hook time: VALTYP ($F663) -> $D020, a call count -> $D021, register E -> $D022 and ERR
($F414) -> $D023. One case runs the error TRAPPED by ON ERROR inside a program.

    python3 -u scratchpad/herro2_probe.py [MACHINE ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CODE = [0x3A, 0x63, 0xF6,  0x32, 0x20, 0xD0,      # ld a,(VALTYP) / ld ($D020),a
        0x7B,              0x32, 0x22, 0xD0,      # ld a,e / ld ($D022),a
        0x3A, 0x14, 0xF4,  0x32, 0x23, 0xD0,      # ld a,(ERR) / ld ($D023),a
        0x21, 0x21, 0xD0,  0x34, 0xC9]            # ld hl,$D021 / inc (hl) / ret
SETUP = []
for i in range(0, len(CODE), 6):
    SETUP.append(":".join(f"POKE{-12288 + j},{CODE[j]}" for j in range(i, min(i + 6, len(CODE)))))
SETUP += ['POKE-12256,255:POKE-12255,0:POKE-12254,255:POKE-12253,255',
          'POKE-78,0:POKE-77,208:POKE-79,195']                # H.ERRO := JP $D000
READ = 'PRINT"[V";PEEK(-12256);"C";PEEK(-12255);"E";PEEK(-12254);"R";PEEK(-12253)'
CASES = {
    "div":     ['X=1/0'],
    "syntax":  ['X=1+'],
    "error7":  ['ERROR 7'],
    "trapped": ['NEW', '10 ON ERROR GOTO 100', '20 X=1/0', '30 END', '100 RESUME 30', 'RUN'],
}


def main():
    for m in sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]:
        for name, stmts in CASES.items():
            lines = SETUP + stmts + [READ]
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=10.0,
                                      reset=("SCREEN 0:WIDTH 40",), step=3.0, run_gap=4.0)[0]
            rows = [scr[i:i + 40].strip() for i in range(0, len(scr or ""), 40)]
            got = next((r for r in reversed(rows) if r.startswith("[V")), "<no reading>")
            err = [r for r in rows if r in ("Division by zero", "Missing operand", "Out of memory")]
            print(f"{m:30s} {name:8s} {got:28s} {' | '.join(err)}", flush=True)


if __name__ == "__main__":
    main()
