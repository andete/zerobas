#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), OUTDLP ($014D): "printer output, TAB expanded to spaces, a failure is
Device I/O error", called DIRECTLY -- VG-8020 against zerobas. Also LPTOUT ($00A5), LPTSTT
($00A8) and OUTDO ($0018) with PRTFLG ($F416) 1 / 0 (D-BIOSCONTRACT2, D-OUTDOPRT).

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


def code(table, entry=0x014D, prtflg=None):
    # [ld a,PRTFLG / ld ($F416),a] / ld hl,TBL / lp: ld a,(hl) / or a / jr z,dn / push hl /
    # call ENTRY / pop hl / inc hl / jr lp / dn: [xor a / ld ($F416),a] / ld a,($F415) /
    # ld ($D100),a / ret / TBL: bytes, 0
    pre = [] if prtflg is None else [0x3E, prtflg, 0x32, 0x16, 0xF4]
    post = [] if prtflg is None else [0xAF, 0x32, 0x16, 0xF4]
    tbl = 0xD000 + len(pre) + 22 + len(post)
    c = pre + [0x21, tbl & 255, tbl >> 8,
               0x7E, 0xB7, 0x28, 0x08, 0xE5, 0xCD, entry & 255, entry >> 8, 0xE1, 0x23, 0x18,
               0xF4] + post + [0x3A, 0x15, 0xF4, 0x32, 0x00, 0xD1, 0xC9]
    assert len(c) == tbl - 0xD000
    return c + list(table) + [0]


CASES = {
    "tab": [0x41, 9, 0x42, 9, 0x43, 13, 10],          # A TAB B TAB C CR LF
    "tabcol": [0x41, 0x42, 0x43, 9, 0x44, 13, 10],    # TAB from column 3
    # D-BIOSCONTRACT2 (2026-11-14): LPTOUT ($00A5) to a READY printer -- only its no-printer
    # abort (lptout_noprn / lptout_intflg below) was compared. The same table through
    # LPTOUT: a TAB goes out as $09 (OUTDLP expands it), and LPTPOS is OUTDLP's, not LPTOUT's.
    "lptout_tab": ([0x41, 9, 0x42, 13, 10], 0x00A5),
    # D-BIOSCONTRACT2 gap 4 (2026-11-14): OUTDO ($0018) -- only its registers were compared.
    # PRTFLG ($F416) = 1: the bytes go to the printer (the printer's bytes and LPTPOS are the
    # answer, the TAB the discriminating byte); PRTFLG = 0: to the screen, the printer
    # untouched (`<nothing printed>`) and the three characters just before BASIC's `[P`.
    "outdo_prn": ([0x41, 9, 0x42, 13, 10], 0x0018, 1),
    "outdo_prncol": ([0x41, 0x42, 0x43, 9, 0x44], 0x0018, 1),
    "outdo_scr": ([0x51, 0x52, 0x53], 0x0018, 0),
}
# rows whose screen reading includes the characters just before `[P` (their own output)
BEFORE = {"outdo_scr": 3}
# LPTSTT ($00A8) with the logger plugged (always ready): its A and F (gap 8: only the
# no-printer state was compared). `push af / pop hl / ld ($D100),hl` -> D100 = F, D101 = A.
LPTSTT_CODE = [0xCD, 0xA8, 0x00, 0xF5, 0xE1, 0x22, 0x00, 0xD1, 0xC9]


def lines(table):
    entry, prtflg = 0x014D, None
    if isinstance(table, tuple):
        table, entry, *rest = table
        prtflg = rest[0] if rest else None
    c = code(table, entry, prtflg)
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
    # D-BRKLATCH (2026-11-12): BASIC breaks on the interrupt's LATCH; BREAKX consumes a
    # press it sees (the VG-8020's face), so machine code that took it does not also
    # break the program; and STOP PAUSES a running program until the next STOP latch.
    "breakx_loop": ["CLEAR 200,&HCFFF:FOR I=0 TO 5:READ X:POKE &HD000+I,X:NEXT",
                    'DEFUSR=&HD000:Q=USR(0):PRINT "[C BRKX]"', "DATA 205,183,0,48,251,201"],
    "lptout_noprn": ["CLEAR 200,&HCFFF:FOR I=0 TO 5:READ X:POKE &HD000+I,X:NEXT",
                     'DEFUSR=&HD000:Q=USR(0):PRINT "[C RET]"', "DATA 62,65,205,165,0,201"],
    "stop_pause": ['T=TIME', 'IF TIME-T<225 THEN 20', 'PRINT "[C DONE]"'],
    # BREAKX's consumption, witnessed: after LPTOUT's CTRL-STOP abort INTFLG is 0, and 0
    # ten frames later with the key still down (without the OLDKEY marking: `0 3` and a
    # break -- knife K9, scratchpad/BL3_k9_intflg.out).
    "lptout_intflg": ["CLEAR 200,&HCFFF:FOR I=0 TO 23:READ X:POKE &HD000+I,X:NEXT",
                      'DEFUSR=&HD000:Q=USR(0):PRINT "[C";PEEK(&HD100);PEEK(&HD101);"]"',
                      "DATA 251,62,65,205,165,0,58,155,252,50,0,209,6,10,118,16,253,58,155,252,50,1,209,201"],
    # D-BRKLATCH step 2: the break at the STATEMENT the latch lands before -- the USR
    # loops on BREAKX, then waits (interrupts on) through the hold and the release, so
    # the latch is set when it returns: the VG-8020 breaks at the USR's own statement,
    # `Break in 20`; a line-start-only check broke one statement later
    # (scratchpad/brkconsume_run.out).
    "brk_midline": ["CLEAR 200,&HCFFF:FOR I=0 TO 42:READ X:POKE &HD000+I,X:NEXT",
                    'DEFUSR=&HD000:Q=USR(0):PRINT "[C";PEEK(&HD100);"]"', 'PRINT "[C END]"',
                    "DATA 251,205,183,0,48,251,58,155,252,50,0,209,6,5,118,16,253,58,155,252,50,1,209,118,58,236,251,230,16,40,248,6,5,118,16,253,58,155,252,50,2,209,201"],
    # D-BIOSCONTRACT2 gap 7 (2026-11-14): PINLIN / INLIN / QINLIN ($00AE / $00B1 / $00B4)
    # waiting for a line, CTRL-STOP held: the published answer is Cy set. `call / push af /
    # pop hl / ld ($D100),hl / ret`; BASIC prints F's Cy (or breaks, if the press reaches it).
    # Both machines BREAK before the PRINT, so the stored F is ALSO read from RAM after the
    # run (FREG_ROWS below; $D100 preset to $AA, which no F the entry leaves can be confused
    # with on its Cy alone -- $AA has Cy clear, so a missing store reads "Cy 0").
    "pinlin_stop": ["CLEAR 200,&HCFFF:FOR I=0 TO 8:READ X:POKE &HD000+I,X:NEXT:POKE &HD100,170",
                    'DEFUSR=&HD000:Q=USR(0):PRINT "[C";PEEK(&HD100) AND 1;"]"',
                    "DATA 205,174,0,245,225,34,0,209,201"],
    "inlin_stop": ["CLEAR 200,&HCFFF:FOR I=0 TO 8:READ X:POKE &HD000+I,X:NEXT:POKE &HD100,170",
                    'DEFUSR=&HD000:Q=USR(0):PRINT "[C";PEEK(&HD100) AND 1;"]"',
                    "DATA 205,177,0,245,225,34,0,209,201"],
    "qinlin_stop": ["CLEAR 200,&HCFFF:FOR I=0 TO 8:READ X:POKE &HD000+I,X:NEXT:POKE &HD100,170",
                    'DEFUSR=&HD000:Q=USR(0):PRINT "[C";PEEK(&HD100) AND 1;"]"',
                    "DATA 205,180,0,245,225,34,0,209,201"],
}
for _n, _p in NOPRN.items():                              # the POKE count FROM the bytes
    if _p[0].startswith("CLEAR") and "READ" in _p[0]:
        _n_bytes = len(_p[-1].split(" ", 1)[1].split(","))
        assert f"TO {_n_bytes - 1}:" in _p[0], (_n, _n_bytes)
# per-row key and (lead, secs): the press lasts secs - lead (omsx_repl's hold note).
# stop_pause: 0.5 s, below the 36-frame auto-repeat -- the VG-8020 stays paused.
KEY_OF = {"stop_pause": ((7, 0x10),)}
HOLD_OF = {"stop_pause": (0.5, 1.0)}


FREG_ROWS = ("pinlin_stop", "inlin_stop", "qinlin_stop")


def noprn(machine, prog, key=CTRL_STOP, hold=(0.5, 2.0), freg=False):
    if freg:                                       # the stored F / A, read from RAM
        m = omsx_repl.run_cases(machine, [("stored", prog)], batch=False,
                                reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                capture=("mem_abs", [(0xD100, 2)]),
                                holds=[key], hold_lead=hold[0], hold_secs=hold[1])[0]
        if not m:
            return None
        b = bytes.fromhex(m)
        return f"F={b[0]:02X} Cy={b[0] & 1} A={b[1]:02X}"
    scr = omsx_repl.run_cases(machine, [("stored", prog)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                              holds=[key], hold_lead=hold[0], hold_secs=hold[1])[0]
    if not scr:
        return None
    rows = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    keep = [x for x in rows if x.startswith("[C") or "rror" in x or "Break" in x]
    return " | ".join(keep) or "<NO OUTPUT>"


def main():
    bad = blind = 0
    for name, prog in NOPRN.items():
        got = {side: noprn(mach, prog, KEY_OF.get(name, CTRL_STOP), HOLD_OF.get(name, (0.5, 2.0)))
               for side, mach in MACHINES}
        if name in FREG_ROWS and got["VG"] and got["ZB"]:
            for side, mach in MACHINES:
                f = noprn(mach, prog, freg=True)
                got[side] += f" | {f or '<NO RAM READ>'}"
        if not got["VG"] or not got["ZB"] or "<NO RAM READ>" in got["VG"] + got["ZB"]:
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
            j = max(0, i - BEFORE.get(name, 0))
            got[side] = f"{prn_reading(raw)}  {txt[j:i + 12].strip() if i >= 0 else '<NO [P]>'}"
        if any("<NO [P]>" in v or "<NO CAPTURE>" in v for v in got.values()):
            verdict = "NO-READING"
            blind += 1
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad += 1
        print(f"ROW {name:7} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    got = {}
    for side, mach in MACHINES:
        log = probe_tmp.tmp(f"zb_outdlp_{side}_lptstt.log")
        plug = (f"set printerlogfilename {{{log}}}", "plug printerport logger")
        prog = ["NEW", "10 CLEAR 200,&HCFFF",
                f"20 FOR I=0 TO {len(LPTSTT_CODE) - 1}:READ X:POKE &HD000+I,X:NEXT",
                '30 DEFUSR=&HD000:Q=USR(0):PRINT "[P";PEEK(&HD101);PEEK(&HD100) AND &HC1;"]"',
                "40 DATA " + ",".join(str(b) for b in LPTSTT_CODE), "RUN"]
        raw = omsx_repl.run_cases(mach, [("direct", prog)], batch=False, reset=(), boot=8.0,
                                  step=2.5, prologue=plug, capture=("screen_printer", log))[0]
        scr, _, _ = (raw or "").partition("7c")
        txt = bytes.fromhex(scr).decode("latin1") if scr else ""
        i = txt.rfind("[P")
        got[side] = txt[i:i + 14].strip() if i >= 0 else None
    if not got["VG"] or not got["ZB"]:
        verdict, blind = "NO-READING", blind + 1
    elif got["VG"] == got["ZB"]:
        verdict = "SAME"
    else:
        verdict, bad = "DIVERGES", bad + 1
    print(f"ROW lptstt_rdy (A, F & S/Z/C) VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print("INSTRUMENT FAULT: a side gave no reading")
        return 2
    n = len(CASES) + len(NOPRN) + 1
    print(f"{'PASS' if not bad else 'FAIL'}: OUTDLP / LPTOUT against the VG-8020 ({n - bad}/{n})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
