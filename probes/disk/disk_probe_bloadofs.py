#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""bloadofs-acceptance (D-BLOADOFS) -- BLOAD's documented `,offset`:
`BLOAD "f"[,R][,S][,offset]` loads the file at its header addresses PLUS the
offset (and, with ,R, runs it there).

Each row writes its own file with BSAVE, clears the target, BLOADs it back
and prints what is where -- registers and RAM only, never a ROM byte.

  ram     16 bytes 1..16 saved from &HC000, BLOAD ,&H1000 -> where they land
  exec    code at &HC005 (LD A,42 : LD (&HD100),A : RET), saved with exec
          &HC005; BLOAD ,R,&H1000 -> does the run go to &HD005 (marker 42)?
  wrap    BLOAD ,&HF000 -> &HB000 (16-bit wrap: an offset is an address)
  vram    16 bytes saved from VRAM &H1000 with ,S; BLOAD ,S,&H100 -> &H1100
  dec     BLOAD ,61440 -- the DECIMAL spelling of &HF000: separates "an int16
          offset" (6) from "an address offset, -32768..65535" (&HB000)
  big     BLOAD ,70000 under ON ERROR
  str     BLOAD ,"A" under ON ERROR
  strfn   BLOAD ,VAL(STR$(4096)) -- an offset whose evaluation writes STRSCR,
          where the filename is staged
  order   BLOAD "NOSUCH.BIN","A" -- the tail is parsed BEFORE the file is looked
          up (13), not after (53)
  nd_str  BLOAD "CAS:X","A" on the DISKLESS VG-8020 vs ours (Joost 2026-09-03:
          disk work adds diskless rows) -- 13, the tail parsed before the tape
  zero    BLOAD ,Q (Q=0) -> a plain load (D-DISKERRS' row, with the file there)

Fresh boot and disk copy per row. Exit 0 all agree; 1 a divergence; 2 a
reference gave no reading.

    python3 -u probes/disk/disk_probe_bloadofs.py [case ...]
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

DISK = ("National_CF-3300", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
TAPE = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")   # the diskless target
NODISK = {"nd_str"}             # rows booted on TAPE, with no disk
SAVE16 = ["11 FOR I=0 TO 15:POKE &HC000+I,I+1:NEXT", '12 BSAVE "T.BIN",&HC000,&HC00F',
          "13 FOR I=0 TO 15:POKE &HC000+I,0:POKE &HD000+I,0:POKE &HB000+I,0:NEXT"]
CASES = {
    "ram": SAVE16 + ['30 BLOAD "T.BIN",&H1000',
                     '40 PRINT"[V";PEEK(&HC000);PEEK(&HD000);PEEK(&HD00F);"]":END'],
    "exec": ["11 FOR I=0 TO 15:POKE &HC000+I,201:NEXT",
             "12 FOR I=0 TO 5:READ B:POKE &HC005+I,B:NEXT:DATA 62,42,50,0,209,201",
             '13 BSAVE "T.BIN",&HC000,&HC00F,&HC005',
             "14 FOR I=0 TO 15:POKE &HC000+I,201:POKE &HD000+I,0:NEXT:POKE &HD100,0",
             '30 BLOAD "T.BIN",R,&H1000',
             '40 PRINT"[V";PEEK(&HD100);PEEK(&HD005);PEEK(&HC005);"]":END'],
    "wrap": SAVE16 + ['30 BLOAD "T.BIN",&HF000',
                      '40 PRINT"[V";PEEK(&HC000);PEEK(&HB000);PEEK(&HB00F);"]":END'],
    "vram": ["11 FOR I=0 TO 15:VPOKE &H1000+I,I+1:NEXT", '12 BSAVE "V.BIN",&H1000,&H100F,S',
             "13 FOR I=0 TO 15:VPOKE &H1000+I,0:VPOKE &H1100+I,0:NEXT",
             '30 BLOAD "V.BIN",S,&H100',
             '40 PRINT"[V";VPEEK(&H1000);VPEEK(&H1100);VPEEK(&H110F);"]":END'],
    "dec": SAVE16 + ['30 BLOAD "T.BIN",61440',
                     '40 PRINT"[V";PEEK(&HC000);PEEK(&HB000);PEEK(&HB00F);"]":END'],
    "big": SAVE16 + ['30 BLOAD "T.BIN",70000', '40 PRINT"[OK]":END'],
    "str": SAVE16 + ['30 BLOAD "T.BIN","A"', '40 PRINT"[OK]":END'],
    "strfn": SAVE16 + ['30 BLOAD "T.BIN",VAL(STR$(4096))',
                       '40 PRINT"[V";PEEK(&HC000);PEEK(&HD000);PEEK(&HD00F);"]":END'],
    "order": ['30 BLOAD "NOSUCH.BIN","A"', '40 PRINT"[OK]":END'],
    "nd_str": ['30 BLOAD "CAS:X","A"', '40 PRINT"[OK]":END'],
    "zero": SAVE16 + ['30 BLOAD "T.BIN",Q',
                      '40 PRINT"[V";PEEK(&HC000);PEEK(&HC00F);"]":END'],
}


def reading(machine, case, lines):
    prog = ["NEW", "10 SCREEN 0:ON ERROR GOTO 90"] + lines + ['90 PRINT"[E";ERR;ERL;"]":END', "RUN"]
    if case in NODISK:
        kw = dict(reset=("CLS",))
    else:
        dsk = probe_tmp.tmp(f"bloadofs_{machine}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        kw = dict(diska=dsk, boot=14.0, reset=("", "SCREEN 0"))
    raw = omsx_repl.run_cases(machine, [("d", prog)], batch=False, run_gap=20.0, **kw)[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
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
        print(f"{'ok  ' if r == z else 'DIFF'} {case:6} {ref[:12]:12} {r!r:16} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: BLOAD's ,offset as on the CF-3300 ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
