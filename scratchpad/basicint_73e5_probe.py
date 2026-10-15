#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-AVTAK: characterise the undocumented BASIC-ROM internal $73E5 BLACK-BOX.

A View to a Kill CALLs $73E5 (three times in its line 140, from a USR-like
context; TODO D-AVTAK has the entry states). The VG-8020 is the oracle: OUR OWN
machine code, run by `X=USR(0)`, sets HL / DE / BC / A, calls $73E5, and stores
what comes back -- HL, DE, BC, AF at $D180.. -- and BASIC then prints those and
VALTYP + DAC as $73E5 left them ($D188 / $D189.., then VALTYP is set
back to 2 so `X=USR(0)` does not raise: the first run's VG-8020 answered `Type
mismatch in 40`, i.e. $73E5 RETURNED and changed the result type), and
two 16-byte buffers: $D200.. (HL's, filled 1, 2, 3, ...) and $D300.. (zeroed).
No ROM byte is read, nothing is stepped; outputs are the screen.

Cases (name: HL, DE, BC, A):
  de38   $D200, $0038, $00F3, $07   (the game's first call's shape)
  debuf  $D200, $D300, $0010, $00   (DE a second buffer)
  bc0    $D200, $D300, $0000, $83   (BC = 0)
Run 2 (VALTYP reset before our `ret`) STILL said `Type mismatch in 40`: our code
after the call apparently never ran, so line 40 now traps the error and the dumps
print either way ([OK] or [E n]).
Runs 3-5: with tokenised TEXT at HL it RETURNS for "", "A", "AB", "ABC" and
raises 5 for "HELLO" / A$="XYZ" (13 for a number or a numeric variable) -- the
rule is the CHARACTERS, not the length: H, X, Y are not music-macro notes. Run 6
prints PLAY(0..3) right after: does it QUEUE the string as music (PLAY's
per-voice string handler)?
PREDICTED, before the run: it RETURNS (the game calls it three times and goes
on) and it moves or compares memory between HL and DE (low confidence).

    python3 -u scratchpad/basicint_73e5_probe.py [case ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {"de38": (0xD200, 0x0038, 0x00F3, 0x07),
         "debuf": (0xD200, 0xD300, 0x0010, 0x00),
         "bc0": (0xD200, 0xD300, 0x0000, 0x83),
         # run 3: HL -> a tokenised BASIC TEXT at $D200 (the game's HL points into
         # its own RAM, and with a garbage buffer all three rows above raised 13)
         "t_str": (0xD200, 0x0038, 0x00F3, 0x07),
         "t_num": (0xD200, 0x0038, 0x00F3, 0x07),
         "t_var": (0xD200, 0x0038, 0x00F3, 0x07),
         # run 4: the string's length and where DE points
         "t_hello": (0xD200, 0x0038, 0x00F3, 0x07),
         "t_svar": (0xD200, 0x0038, 0x00F3, 0x07),
         # run 5: the length rule ("AB" returned, "HELLO" / "XYZ" raised 5)
         "len0": (0xD200, 0x0038, 0x00F3, 0x07),
         "len1": (0xD200, 0x0038, 0x00F3, 0x07),
         "len3": (0xD200, 0x0038, 0x00F3, 0x07)}
# the $D200 text per case (default: 1, 2, 3, ... -- not BASIC text)
TEXT = {"t_str": [0x22, 0x41, 0x42, 0x22, 0x00],     # "AB"
        "t_num": [0x18, 0x00],                      # 7  (digit tokens $11..$1A)
        "t_var": [0x41, 0x00],                      # A
        "t_hello": [0x22, 0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x22, 0x00],   # "HELLO"
        "t_svar": [0x41, 0x24, 0x00],               # A$ (line 15 sets A$="XYZ")
        "len0": [0x22, 0x22, 0x00],                 # ""
        "len1": [0x22, 0x41, 0x22, 0x00],           # "A"
        "len3": [0x22, 0x41, 0x42, 0x43, 0x22, 0x00]}   # "ABC"
MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))


def routine(hl, de, bc, a):
    lo = lambda v: v & 0xFF
    hi = lambda v: v >> 8
    return [0x21, lo(hl), hi(hl),          # ld hl,HL
            0x11, lo(de), hi(de),          # ld de,DE
            0x01, lo(bc), hi(bc),          # ld bc,BC
            0x3E, a,                       # ld a,A
            0xCD, 0xE5, 0x73,              # call $73E5
            0x22, 0x80, 0xD1,              # ld ($D180),hl
            0xED, 0x53, 0x82, 0xD1,        # ld ($D182),de
            0xED, 0x43, 0x84, 0xD1,        # ld ($D184),bc
            0xF5, 0xE1,                    # push af / pop hl
            0x22, 0x86, 0xD1,              # ld ($D186),hl
            0xEB,                          # ex de,hl  (HL = the returned DE)
            0x11, 0x91, 0xD1,              # ld de,$D191
            0x01, 0x08, 0x00,              # ld bc,8
            0xED, 0xB0,                    # ldir      (8 bytes AT the returned DE)
            0x3A, 0x63, 0xF6,              # ld a,(VALTYP $F663)
            0x32, 0x88, 0xD1,              # ld ($D188),a
            0x21, 0xF6, 0xF7,              # ld hl,DAC ($F7F6)
            0x11, 0x89, 0xD1,              # ld de,$D189
            0x01, 0x08, 0x00,              # ld bc,8
            0xED, 0xB0,                    # ldir      (DAC as $73E5 left it)
            0x3E, 0x02,                    # ld a,2
            0x32, 0x63, 0xF6,              # ld (VALTYP),a -- USR returns an integer
            0xC9]                          # ret


def program(case):
    code = routine(*CASES[case])
    data = ",".join(str(b) for b in code)
    return ["NEW",
            f"10 FOR I=0 TO {len(code) - 1}:READ B:POKE &HD000+I,B:NEXT",
            '15 A$="XY"+"Z"',
            "20 FOR I=0 TO 15:POKE &HD200+I,I+1:POKE &HD300+I,0:NEXT",
            "25 " + ("FOR I=0 TO %d:READ B:POKE &HD200+I,B:NEXT" % (len(TEXT[case]) - 1)
                     if case in TEXT else "REM"),
            "30 FOR I=&HD180 TO &HD198:POKE I,0:NEXT",
            '40 ON ERROR GOTO 45:DEFUSR=&HD000:X=USR(0):PRINT"[OK";PLAY(0);PLAY(1);PLAY(2);PLAY(3);"]":GOTO 50',
            '45 PRINT"[E";ERR;"]":RESUME 50',
            '50 P$="[R":FOR I=&HD180 TO &HD198:P$=P$+RIGHT$("0"+HEX$(PEEK(I)),2):NEXT:PRINT P$;"]"',
            '60 P$="[H":FOR I=&HD200 TO &HD20F:P$=P$+RIGHT$("0"+HEX$(PEEK(I)),2):NEXT:PRINT P$;"]"',
            '70 P$="[D":FOR I=&HD300 TO &HD30F:P$=P$+RIGHT$("0"+HEX$(PEEK(I)),2):NEXT:PRINT P$;"]":END',
            f"80 DATA {data}",
            "81 DATA " + ",".join(str(b) for b in TEXT.get(case, [0])),
            "RUN"]


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    return " | ".join(x.strip() for x in r if x.strip().startswith("[") or "rror" in x)


def main():
    only = sys.argv[1:] or list(CASES)
    for name in only:
        got = {}
        for side, m in MACHINES:
            got[side] = rows(omsx_repl.run_cases(m, [("direct", program(name))], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=20.0)[0])
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}] "
              f"{'SAME' if got['VG'] == got['ZB'] else 'DIVERGES'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
