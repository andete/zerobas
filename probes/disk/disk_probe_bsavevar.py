#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""bsavevar-acceptance (D-BSAVEVAR) -- BSAVE's fourth argument, the exec
address, is an EXPRESSION: a variable (`Q`, `SX`) is its value, not an
unknown flag.

Each disk row puts a marker routine at &HC005 (LD A,42 : LD (&HD100),A : RET),
BSAVEs &HC000..&HC00F with the exec given as the row says, wipes the region,
and BLOADs it back with ,R -- the run writes 42 to &HD100 iff the exec saved
was &HC005. Registers and RAM only.

  lit     exec &HC005 (a literal)       the control: 42 on both
  var     Q=&HC005 : exec Q             a variable
  svar    SX=&HC005 : exec SX           NOT a variable: an S there is always the
                                        VRAM flag, the X is junk -- 2 in 14 on the
                                        CF-3300, and T.BIN must NOT be created
                                        (read as `E 2 14 N`)
  cas     BSAVE "CAS:T",&HC000,&HC00F,Q on the DISKLESS VG-8020 (no tape:
          the save completes -- OPEN "X" FOR OUTPUT did) -> [OK]

Fresh boot (and disk copy) per row. Exit 0 all agree; 1 a divergence; 2 a
reference gave no reading.

    python3 -u probes/disk/disk_probe_bsavevar.py [case ...]
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

DISK = ("National_CF-3300", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
TAPE = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
CODE = ["11 FOR I=0 TO 15:POKE &HC000+I,201:NEXT",
        "12 FOR I=0 TO 5:READ B:POKE &HC005+I,B:NEXT:DATA 62,42,50,0,209,201",
        "13 Q=&HC005:SX=&HC005"]
LOAD = ["15 FOR I=0 TO 15:POKE &HC000+I,0:NEXT:POKE &HD100,0",
        '16 BLOAD "T.BIN",R',
        '40 PRINT"[V";PEEK(&HD100);"]":END']
CASES = {
    "lit": CODE + ['14 BSAVE "T.BIN",&HC000,&HC00F,&HC005'] + LOAD,
    "var": CODE + ['14 BSAVE "T.BIN",&HC000,&HC00F,Q'] + LOAD,
    # 🔴 svar's ERROR is not enough: with the `,S`+junk raise cut, the S is taken
    # as the flag, the VRAM save RUNS, and the statement then meets the X and is
    # 2 in 14 anyway (knife K-BV1's first run: bsavevar_knives_miss.out). The
    # witness is whether T.BIN was CREATED: F = it exists, N = it does not.
    "svar": CODE + ['14 BSAVE "T.BIN",&HC000,&HC00F,SX', '40 END',
                    "90 E=ERR:L=ERL:RESUME 91",
                    '91 ON ERROR GOTO 95:OPEN "T.BIN" FOR INPUT AS #1:PRINT"[E";E;L;"F]":END',
                    '95 PRINT"[E";E;L;"N]":END'],
    "cas": ["13 Q=&HC005", '14 BSAVE "CAS:T",&HC000,&HC00F,Q', '40 PRINT"[OK]":END'],
}
NODISK = {"cas"}


def reading(machine, case, lines):
    own90 = any(l.startswith("90 ") for l in lines)
    prog = (["NEW", "10 SCREEN 0:ON ERROR GOTO 90"] + lines
            + ([] if own90 else ['90 PRINT"[E";ERR;ERL;"]":END']) + ["RUN"])
    if case in NODISK:
        kw = dict(reset=("CLS",))
    else:
        dsk = probe_tmp.tmp(f"bsavevar_{machine}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        kw = dict(diska=dsk, boot=14.0, reset=("", "SCREEN 0"))
    raw = omsx_repl.run_cases(machine, [("d", prog)], batch=False, run_gap=20.0, **kw)[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
    # `load error` is OURS ALONE (no reference prints it) and it RETURNS, so a row
    # can still reach its [OK] after it -- agreeing for the wrong reason. It is
    # the reading whenever it is on the screen.
    if "load error" in scr.lower():
        return "load error"
    m = re.findall(r"\[(OK|V[^\]]*|E[^\]]*)\]", scr)
    return " ".join(m[-1].split()) if m else None


def main():
    bad = 0
    only = sys.argv[1:]
    for case, lines in CASES.items():
        if only and case not in only:
            continue
        ref, ours = TAPE if case in NODISK else DISK
        r, z = reading(ref, case, lines), reading(ours, case, lines)
        if r is None:
            print(f"INSTRUMENT FAULT: {ref} gave no reading for {case}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {case:6} {ref[:12]:12} {r!r:14} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: BSAVE's exec expression as on the references ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
