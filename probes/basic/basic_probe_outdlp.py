#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), OUTDLP ($014D): "printer output, TAB expanded to spaces, a failure is
Device I/O error", called DIRECTLY -- VG-8020 against zerobas.

Our own machine code sends a byte table through $014D, one call a byte, then stores
LPTPOS ($F415, the printer column) and A / HL of the last call. The printer is
openMSX's `logger` (always READY), so the bytes OUTDLP SENT are the readout --
D-EDITVERB's apparatus: `screen_printer` capture, one boot per case (the log
accumulates). Black-box: registers, work-area RAM, the printer port's byte stream.

    python3 -u probes/basic/basic_probe_outdlp.py [--gate]

`make outdlp-acceptance` runs it (D-BIOSRUNG, 2026-11-12); scratchpad/outdlp_probe.py is
the development copy. A side with no `[P` row or no capture is an instrument fault (2).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl  # noqa: E402
import probe_tmp  # noqa: E402
from basic_probe_editverb import prn_reading  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))


def code(table):
    # ld hl,TBL / lp: ld a,(hl) / or a / jr z,dn / push hl / call $014D / pop hl /
    # inc hl / jr lp / dn: ld a,($F415) / ld ($D100),a / ret / TBL: bytes, 0
    tbl = 0xD000 + 22
    c = [0x21, tbl & 255, tbl >> 8,
         0x7E, 0xB7, 0x28, 0x08, 0xE5, 0xCD, 0x4D, 0x01, 0xE1, 0x23, 0x18, 0xF4,
         0x3A, 0x15, 0xF4, 0x32, 0x00, 0xD1, 0xC9]
    assert len(c) == 22
    return c + list(table) + [0]


CASES = {
    "tab": [0x41, 9, 0x42, 9, 0x43, 13, 10],          # A TAB B TAB C CR LF
    "tabcol": [0x41, 0x42, 0x43, 9, 0x44, 13, 10],    # TAB from column 3
}


def lines(table):
    c = code(table)
    return ["10 CLEAR 200,&HCFFF",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            '30 DEFUSR=&HD000:Q=USR(0):PRINT "[P";PEEK(&HD100);"]"',
            "40 DATA " + ",".join(str(b) for b in c), "RUN"]


# D-LPTSTOP (2026-11-12): NO PRINTER plugged, CTRL-STOP held -- the VG-8020 says `Device
# I/O error` for LPRINT and for OUTDLP; zerobas's LPTOUT spun forever
# (scratchpad/outdlp_fail_run5.out / _run6.out). Stored programs and the hold
# ctrlstop_probe.py proved (lead 0.5 s, 2 s): a `direct` case's hold, or a 3 s one,
# broke not even `10 GOTO 10` (outdlp_fail_run3.out / _run4.out).
CTRL_STOP = ((6, 0x02), (7, 0x10))
NOPRN = {
    "lprint_noprn": ['LPRINT "A":PRINT "[C LPR]"'],
    "outdlp_noprn": ["CLEAR 200,&HCFFF:FOR I=0 TO 5:READ X:POKE &HD000+I,X:NEXT",
                     'DEFUSR=&HD000:Q=USR(0):PRINT "[C RET]"',
                     "DATA 62,65,205,77,1,201"],          # ld a,"A" / call $014D / ret
    "loop_control": ["GOTO 10"],                          # the hold breaks a program at all
}


def noprn(machine, prog):
    scr = omsx_repl.run_cases(machine, [("stored", prog)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                              holds=[CTRL_STOP], hold_lead=0.5, hold_secs=2.0)[0]
    if not scr:
        return None
    rows = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    keep = [x for x in rows if x.startswith("[C") or "rror" in x or "Break" in x]
    return " | ".join(keep) or "<NO OUTPUT>"


def main():
    bad = blind = 0
    for name, prog in NOPRN.items():
        got = {side: noprn(mach, prog) for side, mach in MACHINES}
        if not got["VG"] or not got["ZB"]:
            verdict = "NO-READING"
            blind += 1
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad += 1
        print(f"ROW {name:13} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    for name, table in CASES.items():
        got = {}
        for side, mach in MACHINES:
            log = probe_tmp.tmp(f"zb_outdlp_{side}_{name}.log")
            plug = (f"set printerlogfilename {{{log}}}", "plug printerport logger")
            raw = omsx_repl.run_cases(mach, [("direct", ["NEW"] + lines(table))], batch=False,
                                      reset=(), boot=8.0, step=2.5, prologue=plug,
                                      capture=("screen_printer", log))[0]
            scr, _, _ = (raw or "").partition("7c")
            txt = bytes.fromhex(scr).decode("latin1") if scr else ""
            i = txt.rfind("[P")
            got[side] = f"{prn_reading(raw)}  {txt[i:i + 12].strip() if i >= 0 else '<NO [P]>'}"
        if any("<NO [P]>" in v or "<NO CAPTURE>" in v for v in got.values()):
            verdict = "NO-READING"
            blind += 1
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad += 1
        print(f"ROW {name:7} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    n = len(CASES) + len(NOPRN)
    print(f"{'PASS' if not bad else 'FAIL'}: OUTDLP / LPTOUT against the VG-8020 ({n - bad}/{n})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
