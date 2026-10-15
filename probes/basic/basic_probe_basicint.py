#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BASICINT (gate: basicint-acceptance): the three undocumented BASIC-ROM entry
points tape games jump to, at their FIXED addresses.

Tape games call into the reference's BASIC ROM at addresses no published table
names: $73AC (RUN without an argument: Loopy Laundry, Punch & Judy), $6CF3
(BLOAD,R's continuation) and $3297 (`pop hl / ret`: Harry Fox). They were
characterised black-box on the VG-8020 (scratchpad/basicint_probe.py) and are
pinned in zerobas at those addresses (tools/pin_plan.py; `make pin-check` holds
the pads). Before the pins every row here was `load error` or a wrong
continuation on zerobas.

The machine code and the tape are OUR OWN, built per run with cas_encode, and
run by `BLOAD"CAS:",R` exactly as the games run theirs -- so the stack holds the
same `,R` return chain. Each row prints ONLY what its routine controls:
  run_vt   `ld hl,(VARTAB) / jp $73AC`: the program runs from the top with its
           variables cleared ("[1] 0 [2]"; A=7 was set before the BLOAD).
  run_0    the same with HL = 0 (HL is ignored).
  run_link line 10's link garbled to $FFFF first: the reference still runs it.
  run_data a direct-mode READ first: RUN restores the DATA pointer.
  cont     `pop hl / jp $6CF3`: the rest of the statement runs, as after `ret`.
  vt64     FRE(0) after `VARTAB += 64 / jp $73AC`, MINUS FRE(0) after the
           same with += 0, per machine: the variables start AT VARTAB AS GIVEN,
           so it is -64 on both. (A difference of two readings, so neither the
           D-WSZERO free-RAM gap nor the variable layout enters the row.)
  pop3297  a continuation and a marker pushed, BC / DE set, `jp $3297`: the
           continuation runs with HL = the marker and BC / DE untouched; its
           output cells are zeroed first, and A / F (BLOAD,R's own) are not read.
  play_ok / play_e5 / play_e13 (D-AVTAK, 2026-10-15): $73E5 is the reference's
           PLAY body, which A View to a Kill CALLs. OUR code, run by USR, calls
           it with HL at a tokenised text it POKEd ("ABC" / "HELLO" / 7); the row
           is the outcome ([OK] + PLAY(0..3), or [E n] under ON ERROR) and the HL
           it returns. ("AB" is NOT a row: the reference reports voice 2 busy
           after a direct call, which a plain PLAY "AB" does not -- recorded in
           TODO D-AVTAK, not chased.)
Each row prints `ROW <name> VG=[...] ZB=[...] <verdict>`.
Exit 0 all SAME; 1 a divergence; 2 the VG-8020 gave no reading.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas                    # noqa: E402

VARTAB, TXTTAB = 0xF6C2, 0xF676


def lo(a):
    return a & 0xFF


def hi(a):
    return a >> 8


JP73AC = [0xC3, 0xAC, 0x73]
CODE = {
    "run_vt": [0x2A, lo(VARTAB), hi(VARTAB)] + JP73AC,
    "run_0": [0x21, 0x00, 0x00] + JP73AC,
    # ld hl,(TXTTAB) / ld (hl),$FF / inc hl / ld (hl),$FF -- line 10's link garbled
    "run_link": [0x2A, lo(TXTTAB), hi(TXTTAB), 0x36, 0xFF, 0x23, 0x36, 0xFF] + JP73AC,
    "run_data": JP73AC,
    "cont": [0xE1, 0xC3, 0xF3, 0x6C],
    # ld hl,(VARTAB) / ld de,K / add hl,de / ld (VARTAB),hl / jp $73AC
    "vt64": [0x2A, lo(VARTAB), hi(VARTAB), 0x11, 64, 0, 0x19, 0x22, lo(VARTAB), hi(VARTAB)] + JP73AC,
    "vt0": [0x2A, lo(VARTAB), hi(VARTAB), 0x11, 0, 0, 0x19, 0x22, lo(VARTAB), hi(VARTAB)] + JP73AC,
    # ld hl,$D020 / push hl / ld hl,$ABCD / push hl / ld hl,0 / ld de,$1111 /
    # ld bc,$2222 / jp $3297; at $D020: ld ($D180),hl / ld ($D182),bc /
    # ld ($D184),de / ret
    "pop3297": ([0x21, 0x20, 0xD0, 0xE5, 0x21, 0xCD, 0xAB, 0xE5, 0x21, 0x00, 0x00,
                 0x11, 0x11, 0x11, 0x01, 0x22, 0x22, 0xC3, 0x97, 0x32]
                + [0x00] * 12
                + [0x22, 0x80, 0xD1, 0xED, 0x43, 0x82, 0xD1, 0xED, 0x53, 0x84, 0xD1, 0xC9]),
}
TAIL = 'BLOAD"CAS:",R:PRINT"[TAIL]"'
PROG = ["NEW", '10 PRINT"[1]";A;', '20 PRINT"[2]":END', '30 PRINT"[3]"']
LINES = {
    "run_vt": PROG + ["A=7:" + TAIL],
    "run_0": PROG + ["A=7:" + TAIL],
    "run_link": PROG + ["A=7:" + TAIL],
    "run_data": ["NEW", '10 READ X:PRINT"[";X;"]":END', "20 DATA 5,6", "READ Q:" + TAIL],
    "cont": PROG + ["A=7:" + TAIL],
    "vt64": ["NEW", '10 PRINT"[";FRE(0);"]":END', TAIL],
    "vt0": ["NEW", '10 PRINT"[";FRE(0);"]":END', TAIL],
    "pop3297": ["NEW", "10 FOR I=&HD180 TO &HD185:POKE I,0:NEXT",
                '20 BLOAD"CAS:",R',
                '30 P$="[":FOR I=&HD180 TO &HD185:P$=P$+RIGHT$("0"+HEX$(PEEK(I)),2):NEXT:PRINT P$;"]":END',
                "RUN"],
}
ROWS = ["run_vt", "run_0", "run_link", "run_data", "cont", "vt64", "pop3297",
        "play_ok", "play_e5", "play_e13"]
PLAYTEXT = {"play_ok": [0x22, 0x41, 0x42, 0x43, 0x22, 0x00],                 # "ABC"
            "play_e5": [0x22, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x22, 0x00],     # "HELLO"
            "play_e13": [0x18, 0x00]}                                       # 7


def play_lines(name):
    # USR routine: ld hl,$D200 / call $73E5 / ld ($D180),hl / ret
    code = [0x21, 0x00, 0xD2, 0xCD, 0xE5, 0x73, 0x22, 0x80, 0xD1, 0xC9]
    text = PLAYTEXT[name]
    return ["NEW",
            "10 FOR I=0 TO %d:READ B:POKE &HD000+I,B:NEXT" % (len(code) - 1),
            "20 FOR I=0 TO %d:READ B:POKE &HD200+I,B:NEXT:POKE &HD180,0:POKE &HD181,0" % (len(text) - 1),
            '30 ON ERROR GOTO 50:DEFUSR=&HD000:X=USR(0)',
            '40 PRINT"[OK";PLAY(0);PLAY(1);PLAY(2);PLAY(3);"]":GOTO 60',
            '50 PRINT"[E";ERR;"]":RESUME 60',
            '60 PRINT"[HL";PEEK(&HD180);PEEK(&HD181);"]":END',
            "70 DATA " + ",".join(str(b) for b in code),
            "80 DATA " + ",".join(str(b) for b in text),
            "RUN"]
MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))


def screen_rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    keep = [x.strip() for x in r if x.strip().startswith("[") or "rror" in x]
    return " | ".join(keep)


def run(machine, name, tmp):
    if name in PLAYTEXT:
        return screen_rows(omsx_repl.run_cases(machine, [("direct", play_lines(name))], batch=False,
                                               reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                               run_gap=20.0)[0])
    path = os.path.join(tmp, f"{name}.cas")
    open(path, "wb").write(build_cas("T", 0xD000, 0xD000, bytes(CODE[name])))
    return screen_rows(omsx_repl.run_cases(machine, [("direct", LINES[name])], batch=False,
                                           reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                           run_gap=30.0, cassette=path)[0])


def fre(text):
    try:
        return int(text.strip("[] ").split()[0])
    except (AttributeError, ValueError, IndexError):
        return None


def main():
    only = sys.argv[1:] or ROWS
    tmp = tempfile.mkdtemp(prefix="basicint_")
    bad, blind = [], []
    for name in only:
        got = {}
        for side, m in MACHINES:
            if name == "vt64":
                a, b = fre(run(m, "vt64", tmp)), fre(run(m, "vt0", tmp))
                got[side] = None if a is None or b is None else f"{a - b}"
            else:
                got[side] = run(m, name, tmp)
        if not got["VG"]:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: undocumented BASIC entries "
          f"({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
