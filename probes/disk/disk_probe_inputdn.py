#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""inputdn-acceptance (D-INPUTDN) -- INPUT$'s count outside 1..255 is Illegal
function call (5), raised at the READ, after the channel checks.

`10 <setup>` + `20 ON ERROR GOTO 90` + `30 <stmt>`; the handler prints
`[E <ERR> <ERL>]`, a statement that returns prints `[OK<A$>]`. A channel
row's setup writes `ABC` to I.TXT and reopens it FOR INPUT as #1.

  con_0      A$=INPUT$(0)           CF-3300: 5 in 30
  con_256    A$=INPUT$(256)         CF-3300: 5 in 30
  con_neg    A$=INPUT$(-1)          measured here first
  ch_0       A$=INPUT$(0,#1)        measured here first (channel open)
  ch_256     A$=INPUT$(256,#1)      measured here first (channel open)
  ch_closed0 A$=INPUT$(0,#1)        the control: #1 NOT open -- 59 on both
                                    (the channel is checked before the count)
  ch_2       A$=INPUT$(2,#1)        the positive control: `OKAB` on both
  nd_0       A$=INPUT$(0)           VG-8020 (diskless): measured here first
  con_str    A$=INPUT$("A")         13 -- the count is TYPED at the eval (this
                                    row caught the first fix answering 5)
  con_big    A$=INPUT$(70000)       | these two SEPARATE "range-check the count
  ch_closed256 A$=INPUT$(256,#1)    | at the read" from "a byte argument at the
                                    eval, only 0 refused at the read"

Fresh boot (and disk copy) per row. Exit 0 all agree; 1 a divergence; 2 a
reference gave no reading.

    python3 -u probes/disk/disk_probe_inputdn.py [case ...]
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

DISK = ("National_CF-3300", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
TAPE = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
OPEN1 = 'OPEN "I.TXT" FOR OUTPUT AS #1:PRINT #1,"ABC":CLOSE:OPEN "I.TXT" FOR INPUT AS #1'
CASES = {"con_0": (DISK, ("REM", "A$=INPUT$(0)")), "con_256": (DISK, ("REM", "A$=INPUT$(256)")),
         "con_neg": (DISK, ("REM", "A$=INPUT$(-1)")),
         "ch_0": (DISK, (OPEN1, "A$=INPUT$(0,#1)")), "ch_256": (DISK, (OPEN1, "A$=INPUT$(256,#1)")),
         "ch_closed0": (DISK, ("REM", "A$=INPUT$(0,#1)")), "ch_2": (DISK, (OPEN1, "A$=INPUT$(2,#1)")),
         "nd_0": (TAPE, ("REM", "A$=INPUT$(0)")),
         "con_str": (DISK, ("REM", 'A$=INPUT$("A")')), "con_big": (DISK, ("REM", "A$=INPUT$(70000)")),
         "ch_closed256": (DISK, ("REM", "A$=INPUT$(256,#1)"))}


def reading(machine, arg, disk):
    setup, stmt = arg
    prog = ["NEW", f"10 {setup}", "20 ON ERROR GOTO 90", f"30 {stmt}", '40 PRINT"[OK";A$;"]":END',
            '90 PRINT"[E";ERR;ERL;"]":END', "RUN"]
    kw = dict(reset=("CLS",))
    if disk:
        dsk = probe_tmp.tmp(f"inputdn_{machine}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        kw = dict(diska=dsk, boot=14.0, reset=("", "SCREEN 0"))
    raw = omsx_repl.run_cases(machine, [("d", prog)], batch=False, run_gap=15.0, **kw)[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
    m = re.findall(r"\[(OK[^\]]*|E[^\]]*)\]", scr)
    if m:
        return " ".join(m[-1].split())
    return None


def main():
    bad = 0
    only = sys.argv[1:]
    for case, ((ref, ours), arg) in CASES.items():
        if only and case not in only:
            continue
        disk = ref.startswith("National")
        r, z = reading(ref, arg, disk), reading(ours, arg, disk)
        if r is None:
            print(f"INSTRUMENT FAULT: {ref} gave no reading for {case}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {case:8} {ref[:12]:12} {r!r:12} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: INPUT$'s count range as on the references ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
