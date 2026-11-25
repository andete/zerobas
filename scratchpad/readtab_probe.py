#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-VALWS, before the fix: does READ of a DATA item with a TAB / LF inside the number skip it, as VAL does on the
VG-8020? A typed line cannot carry a TAB (the screen editor turns the key into spaces), so the program is typed with a
SPACE in the item and the space is POKEd to 9 (or 10) in the stored program text, then RUN.

    python3 -u scratchpad/readtab_probe.py > scratchpad/AE_readtab.out 2>&1
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = [("VG-8020", "Philips_VG_8020"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_NODISK")]
# find "1 2" (49 32 50) in the program text and put CODE over the space
# (a FOR / IF / NEXT one-liner skipped its own NEXT when the IF was false -- the first run's POKE never landed and
# its control showed it). The item is at TXTTAB + 6 on both machines ("10 DATA 1 2": link, number, DATA, space).
FIND = 'T=PEEK(&HF676)+256*PEEK(&HF677):IF PEEK(T+6)=49 AND PEEK(T+7)=32 THEN POKE T+7,{c}'
CASES = {
    "space": (["10 DATA 1 2", "20 READ A:PRINT\"[R\";A;\"]\""], None),
    "tab": (["10 DATA 1 2", "20 READ A:PRINT\"[R\";A;\"]\""], 9),
    "lf": (["10 DATA 1 2", "20 READ A:PRINT\"[R\";A;\"]\""], 10),
    # the CONTROL: a byte no machine skips ('X') -- if this still reads 12 the POKE never landed and every row above
    # agrees for the wrong reason
    "ctlx": (["10 DATA 1 2", "20 READ A:PRINT\"[R\";A;\"]\""], 88),
    "tabexp": (["10 DATA 1E 2", "20 READ A:PRINT\"[R\";A;\"]\""], None),
    "valtab": (["10 PRINT\"[R\";VAL(\"1\"+CHR$(9)+\"2\");\"]\""], None),
}
RX = re.compile(r"\[R\s*([^\]]*?)\s*\]")


def lines(name):
    prog, code = CASES[name]
    out = ["NEW"] + prog
    if code is not None:
        out.append(FIND.format(c=code))
    if name == "tabexp":            # "1E 2": the space after E becomes a TAB
        out.append('T=PEEK(&HF676)+256*PEEK(&HF677):IF PEEK(T+7)=69 AND PEEK(T+8)=32 THEN POKE T+8,9')
    return out + ["RUN"]


def load_rows():
    """The TYPED-literal row the item asks for: a TAB cannot be typed, but an ASCII program LOADed from disk is
    tokenised as it loads. A=1<TAB>2 in a program line, and the same in DATA, on the CF-3300 (Disk BASIC) and
    zerobas's DISK machine."""
    import shutil
    sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
    import probe_tmp
    from disk_probe_bdos import fat12_add
    src = b'10 A=1\t2:PRINT"[R";A;"]"\r\n20 READ B:PRINT"[R";B;"]"\r\n30 DATA 1\t2\r\n'
    if "--prefix" in sys.argv:          # the & prefix with a gap after it, typed (LOADed) rather than through VAL
        src = (b'10 A=& H10:PRINT"[R";A;"]"\r\n20 C=&\tH10:PRINT"[R";C;"]"\r\n'
               b'30 READ D:PRINT"[R";D;"]"\r\n40 DATA & H10\r\n')
    dsk = probe_tmp.tmp("readtab.dsk")
    shutil.copyfile(os.path.join(ROOT, "disk", "empty720.dsk"), dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "TABS", "BAS", src)
    open(dsk, "wb").write(img)
    for tag, m in (("CF-3300", "National_CF-3300"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_DISK")):
        r = omsx_repl.run_cases(m, [("direct", ['LOAD"TABS.BAS"', "RUN", "LIST"])], batch=False, diska=dsk, reset=("", "SCREEN 0"))[0]
        t = re.sub(r"\s+", " ", r or "")
        print(f"{tag:8s} load    {RX.findall(t)}  ...{t[-150:]}")


def main():
    if "--load" in sys.argv:
        load_rows()
        return
    for tag, m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", lines(n)) for n in CASES], batch=False)
        for n, r in zip(CASES, raw):
            g = RX.findall(re.sub(r"\s+", " ", r or ""))
            print(f"{tag:8s} {n:7s} {g[-1] if g else '<NO OUTPUT> ' + repr((r or '')[-60:])}")


if __name__ == "__main__":
    main()
