#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""savetail-acceptance (D-SAVETAIL) -- a SAVE whose option is not `,A` is a
TRAPPABLE Syntax error, on disk and on cassette.

`10 REM` + `20 ON ERROR GOTO 90` + `30 SAVE "<dev>"<tail>`; the handler prints
`[E <ERR> <ERL>]`, a completed SAVE prints `[OK]`.

  disk_b    SAVE "X.BAS",B      CF-3300: 2 in 30   (ours aborted with `load error`)
  disk_a1   SAVE "X.BAS",A,1    CF-3300: 2 in 30   (likewise)
  disk_a    SAVE "X.BAS",A      the positive control: it saves -- and a SAVE inside
                                a program returns to the prompt (ENDED) on both
  disk_acolon SAVE "X.BAS",A:PRINT  a `:` after the A ends the STATEMENT: it saves
                                and ENDS, not 2 (the first fix took `:` for junk;
                                wprotect-acceptance's wp_asave caught it)
  cas_b     SAVE "CAS:X",B      VG-8020: 2 in 30   (likewise, diskless machine)
  cas_a1    SAVE "CAS:X",A,1    VG-8020: 2 in 30

Fixed 2026-10-06 (basic/save.asm sav_flag_a: `jp nz,load_error` -> stmt_error;
the disk and cassette paths share the body). Fresh boot (and disk copy) per row.
Exit 0 all agree; 1 a divergence; 2 a reference gave no reading.

    python3 -u probes/disk/disk_probe_savetail.py
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

DISK = ("National_CF-3300", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
TAPE = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
CASES = {"disk_b": (DISK, '"X.BAS",B'), "disk_a1": (DISK, '"X.BAS",A,1'), "disk_a": (DISK, '"X.BAS",A'),
         "disk_acolon": (DISK, '"X.BAS",A:PRINT"[X]"'),
         "cas_b": (TAPE, '"CAS:X",B'), "cas_a1": (TAPE, '"CAS:X",A,1')}


def reading(machine, arg, disk):
    prog = ["NEW", "10 REM", "20 ON ERROR GOTO 90", f"30 SAVE {arg}", '40 PRINT"[OK]":END',
            '90 PRINT"[E";ERR;ERL;"]":END', "RUN"]
    kw = dict(reset=("CLS",))
    if disk:
        dsk = probe_tmp.tmp(f"savetail_{machine}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        kw = dict(diska=dsk, boot=14.0, reset=("", "SCREEN 0"))
    raw = omsx_repl.run_cases(machine, [("d", prog)], batch=False, run_gap=15.0, **kw)[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
    m = re.findall(r"\[(OK|E[^\]]*)\]", scr)
    if m:
        return " ".join(m[-1].split())
    # a SAVE that completes inside a program returns to the PROMPT, ending the
    # run, on both references (measured 2026-10-06): RUN, then Ok / our ZB
    return "ENDED" if re.search(r"\bRUN (Ok|ZB)\b", scr) else None


def main():
    bad = 0
    for case, ((ref, ours), arg) in CASES.items():
        disk = ref.startswith("National")
        r, z = reading(ref, arg, disk), reading(ours, arg, disk)
        if r is None:
            print(f"INSTRUMENT FAULT: {ref} gave no reading for {case}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {case:8} {ref[:12]:12} {r!r:12} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: SAVE's option tail as on the references ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
