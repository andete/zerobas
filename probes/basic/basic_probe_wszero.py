#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO (gate: wszero-acceptance): a program owns HIMEM..$F37F.

On a real diskless MSX1 a program that does `CLEAR n,&Hxxxx` owns the RAM from
HIMEM up to $F37F; BASIC keeps its state in the published work area ($F380 up)
and below HIMEM. Tape loaders do exactly that and then BLOAD up to $F000 / $F37F
(D-TAPELOAD's triage: 22 of ~43 failing titles). zerobas keeps ~2.5 KB of its own
state at $E98A-$F37F; a load over it crashes BASIC (Joost, 2026-10-14: shrink it
to zero, TIER 1 -- scratchpad/wszero_inventory.md).

Each row: OUR OWN synthetic tape (cas_encode) holding one binary that covers one
slice of the window -- a `ret` at its start, the rest $A5 -- loaded by a program
with `CLEAR 100,&HE000:BLOAD"CAS:",R`, which then runs PRINT, GOSUB, FOR and a
string concatenation. `ctl` loads below the window; `noclear` runs the same
program WITHOUT the `CLEAR`, as the loaders of D-TAPELOAD's RESET class do, so
the stack is wherever boot put it. The VG-8020 is the oracle.

KNOWN_DIVERGE pins the rows zerobas still fails: they must DIVERGE (a row that
starts agreeing is a pin that ROTTED -- remove it), every other row must be SAME.
As D-WSZERO's slices land the pins come off; slice 11 empties the set.

Each row prints `ROW <name> VG=[...] ZB=[...] <verdict>`. Exit 0 as pinned;
1 a divergence outside the pins or a rotted pin; 2 the VG-8020 gave no reading.
Typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, re, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
from cas_encode import build_cas, build_cas_ascii  # noqa: E402

def sym(name):
    for ln in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        m = re.match(rf"^{name}\s+EQU\s+([0-9A-Fa-f]+)H", ln)
        if m:
            return int(m.group(1), 16)
    raise SystemExit(f"{name} is not in build/basic-reloc.sym -- build first")


# 🔁 SLICE 5 (2026-10-14) PACKED THE WORKSPACE against the top and raised the
# diskless ceiling (TXTMAX_NODISK $E98A -> the build's value), so the rows of
# slices 1-4 -- each the OLD HOME of a block that had just moved out -- stopped
# meaning anything: packed cells now sit in most of them. Their history, kept:
#   slice 0: ctl, w1-w5 (the window in five slices); first run w2 `Device I/O
#     error`, w3 nothing printed, w4 `Unprintable error in 10`, w5 stops after
#     [A][G] (scratchpad/wszero_gate_first.out).
#   slice 1: bl $EC20-$EC25, cas $F000-$F01F (BLOAD's loop cells, the tape
#     search's names); slice 2: trap $EDD1-$EE1F (the trap block, read by the
#     interrupt service every frame); slice 3: loop $EC26-$EC59 (PRGEND..SL_CEIL,
#     bisected: scratchpad/wszero_s3_bisect.out); slice 4: fperr $F03C-$F0A9 and
#     slot $F100-$F109 (scratchpad/wszero_w45_bisect.out), and `all` -- after
#     which no pin was left.
# The rows now come from the build: what is left of the window, in quarters and
# whole, and the RAM slice 5 handed back to programs.
NODISK = sym("TXTMAX_NODISK")
_q = (0xF380 - NODISK) // 4
RANGES = {
    "ctl": (0xC000, 0xC17F),
    # program RAM since slice 5: a load here must be harmless
    "freed": (0xE98A, NODISK - 1),
    "q1": (NODISK, NODISK + _q - 1),
    "q2": (NODISK + _q, NODISK + 2 * _q - 1),
    "q3": (NODISK + 2 * _q, NODISK + 3 * _q - 1),
    "q4": (NODISK + 3 * _q, 0xF37F),
    "all": (NODISK, 0xF37F),
    # D-TAPELOAD's RESET class (2026-10-14): a loader that does NOT `CLEAR` and
    # loads where the VG-8020 keeps free RAM below its stack ($F09E there). With
    # the ceiling at $E98A zerobas's SP was $E6A6, inside this block: the next
    # `ret` popped the loaded bytes.
    "noclear": (0xE000, 0xE7FF),
    # slice 6 (2026-10-14): the ceiling rose $EBCD -> $ECF8, so boot's stack moved
    # from ~$E8E9 to ~$EA14 -- this span held it before and must be free now.
    "noclear2": (0xE800, 0xE97F),
}
# Rows that run the program without `CLEAR` (the stack stays where boot put it).
NOCLEAR = {"noclear", "noclear2"}
# slice 7 (2026-10-14): an ERROR after the load, over the whole window. The run
# loop anchors SP in SAVSTK once per RUN and the error trap reloads it -- a load
# over that cell and then any error jumped to a garbage stack (Formula 1
# Simulator's SP = $00F3). `abort` has no handler, `onerr` resumes from one.
ERRROWS = {"abort", "onerr"}
RANGES["abort"] = RANGES["all"]
RANGES["onerr"] = RANGES["all"]
# slice 7 (2026-10-14): the statements a BASIC loader typically runs AFTER the
# load, each a different tenant -- DEF FN, the string GC, READ / DATA, PRINT
# USING, graphics, PLAY, DIM -- over the whole window. A cell that only one of
# them reads is invisible to the core program.
RICH = {"rich", "rich2"}
RANGES["rich"] = RANGES["all"]
RANGES["rich2"] = RANGES["all"]
# D-WSZERO S8 (2026-10-15): state SET BEFORE the load and READ AFTER it --
# the persistent cells (DRAW's scale / angle, the disk-ROM-present flag that
# decides a `d:` name: 56 with no disk ROM, the disk arm with one -- FILES does
# not read it, knife K-WS13's first cut). Every other row sets its state after
# the load, so a persistent cell that a load garbles was invisible to them.
# ⏱ The scan is 17x17: a 41x41 one ran past the 40 s run gap on zerobas after a
# full-window load (the VG-8020 finished inside it) and read as an empty screen.
RANGES["persist"] = RANGES["all"]
# D-WSZERO S10 (2026-10-15): the persistent cells a loader's NEXT statements
# read, each set BEFORE the load (or by a load inside the statement that reads
# it) -- an open channel (FCH_MODES), INPUT's cursor (CSR_*), the direct-mode
# flag mid-line (DIRECTF), a RESUME after a load in the handler (ERRRESUME), CONT
# after a direct load (CONTVALID) and the `Ok` after RUN (PRMWANT -- only a $00
# fill can see it: $A5 is nonzero, which is what the cell wants).
for _r in ("chan", "input", "midline", "resume", "contdir", "prm"):
    RANGES[_r] = RANGES["all"]
FILL = {"prm": 0x00}
# D-WSZERO S9 (2026-10-15): the DISK-ONLY cells, made disk-only in fact -- the
# diskless machine must neither read nor write them, so they may stay below
# $F380 when the ceiling rises (S15). Each row loads over one of them and runs
# the diskless statement that still touched it. `fldread` fills the FIELD table
# with $41 so EVERY entry names `AA$` -- a $A5 key matches no variable, which is
# why `rich2` (ERASE + string reads) never saw the table.
FT, FTE = sym("FLD_TAB"), sym("FLD_TABEND")
RANGES["fldread"] = (FT - 1, FTE - 1)
RANGES["fldclr"] = (FT - 1, FTE - 1)
RANGES["flderase"] = (FT - 1, FTE - 1)
FILL["fldread"] = 0x41
for _r in ("lset", "valtyp"):
    RANGES[_r] = RANGES["all"]
# `inpeof` loads nothing: its tape holds one ASCII file, and the row pokes the
# disk error cell between two LINE INPUT # -- the OPEN clears it, so a value
# written AFTER the OPEN is what a tape EOF reads (scratchpad/inpeof_probe.out).
RANGES["inpeof"] = (0, 0)
TAPES = {"inpeof": lambda: build_cas_ascii("D", "HELLO\r\n")}
VALTYP_OLD = 0xEF35     # S9 deleted the write-only VALTYP that lived here
# D-WSZERO S11 (2026-10-15): 63 TRANSIENT cells left the window for idle published
# bytes. A transient cell is rewritten before it is read, so no row could see it
# being loaded over -- what S11 changes is that its users no longer WRITE the
# window. Each row loads $A5 over the whole window, runs every user of one group,
# then sums the 91 bytes S11 vacated (the pre-S11 homes, frozen here: 19 spans):
# the VG-8020 leaves them alone, 165 * 91 = 15015.
for _r in ("s11gfx", "s11num", "s11inp"):
    RANGES[_r] = RANGES["all"]
S11_SPANS = "60724,60727,60761,60774,60800,60814,60820,60822,60826,60828,61229,61236,61238,61239,61288,61294,61325,61330,61332,61333,61363,61370,61579,61580,61638,61641,61646,61646,61649,61649,61651,61652,61698,61702,61709,61710,61721,61722"
_S11_SUM = ['900 SCREEN 0:S=0:RESTORE 950:FOR K=1 TO 19:READ P,Q:FOR I=P TO Q:S=S+PEEK(I):NEXT:NEXT'
            ':PRINT"[S";S;"]":END',
            "950 DATA " + S11_SPANS]
RUN_GAP = {"s11gfx": 60.0}
# D-WSZERO S12: 89 transient cells OVERLAY four hosts (BUF, the DEF FN shadow
# slots, MULPROD+DIVPAD, FBUFFR's idle bytes). As S11: load $A5 over the whole
# window, run every user of one group, sum the 290 bytes S12 vacated (the pre-S12
# homes, frozen here: 27 spans) -- the VG-8020 leaves them alone: 165 * 290 = 47850.
# The ov* rows sum nothing: each runs a host's users and its guests' users
# interleaved in ONE program (the closest-to-breaking shapes, s12_plan.md §5) and
# must read as the VG-8020 does.
for _r in ("s12gfx", "s12num", "s12inp", "s12dir", "ovbuf", "ovfn", "ovleaf", "ovfbuf"):
    RANGES[_r] = RANGES["all"]
S12_SPANS_A = "60664,60667,60671,60723,60815,60819,60825,60825,61037,61038,61041,61042,61085,61116,61119,61119,61121,61122,61130,61161,61183,61189,61296,61324,61335,61362"
S12_SPANS_B = "61373,61374,61405,61406,61416,61419,61599,61599,61608,61609,61611,61637,61642,61645,61647,61648,61653,61669,61688,61697,61703,61708,61711,61720,61725,61725,61727,61730"
_S12_SUM = ['900 SCREEN 0:S=0:RESTORE 950:FOR K=1 TO 27:READ P,Q:FOR I=P TO Q:S=S+PEEK(I):NEXT:NEXT'
            ':PRINT"[S";S;"]":END',
            "950 DATA " + S12_SPANS_A, "951 DATA " + S12_SPANS_B]
RUN_GAP.update({"s12gfx": 60.0, "s12num": 60.0, "s12dir": 60.0})
TAPES["s12dir"] = lambda: tape(*RANGES["s12dir"]) + build_cas_ascii("M", '30 PRINT"[M]"\r\n')
# D-WSZERO S14a (2026-10-16): CVT -> ARGB, five singles -> the DAC tail (over
# tk_float's cells), RVDESC -> DSCTMP, DISKOP_STATUS -> FLBMEM (s14_plan.md §3.1).
# `s14eq` sums the 27 vacated bytes (VG-8020 165 * 27 = 4455; LHS_VARTYPE at
# $F16C and VARTYPE at $F168 stay -- VARTYPE's DAC-tail home broke READ, which
# resolves its target before tk_float parses the item); `ovdac` / `ovargb` run
# the new overlays' users together, READ included.
for _r in ("s14eq", "ovdac", "ovargb"):
    RANGES[_r] = RANGES["all"]
_S14A_SUM = ['900 SCREEN 0:S=0:RESTORE 950:FOR K=1 TO 6:READ P,Q:FOR J=P TO Q:S=S+PEEK(J):NEXT:NEXT'
             ':PRINT"[S";S;"]":END',
             "950 DATA 60985,60985,61426,61428,61670,61687,61726,61726,61801,61803,61805,61805"]
# D-WSZERO S14b (2026-10-16): the render window (LIST / KEY LIST / PRINT USING /
# ASCII SAVE) and its detok cells move into BUF; the KEY-bar repaint -- the only
# writer reachable from an expression (INKEY$, read_line) -- is dispatched before
# db_begin now. `s14lst` sums the 112 vacated bytes (VG-8020 165 * 112 = 18480);
# `ovkey` types a 170-character LINE INPUT answer with the KEY bar ON: the
# repaint must not touch BUF (char 163 is where the window starts, $F600).
for _r in ("s14lst", "ovkey"):
    RANGES[_r] = RANGES["all"]
RUN_GAP["s14lst"] = 60.0
_S14B_SUM = ['900 SCREEN 0:S=0:RESTORE 950:FOR K=1 TO 4:READ P,Q:FOR J=P TO Q:S=S+PEEK(J):NEXT:NEXT'
             ':PRINT"[S";S;"]":END',
             "950 DATA 60829,60924,61420,61425,61600,61607,61731,61732"]
# D-WSZERO S14c (2026-10-16): WSTX = BUF+256 ($F65E-$F65F), the two bytes no
# expression can reach (STRSCR staging ends at $F65D), shared by cells that are
# each live in ONE statement only: MID$'s / LSET's target (MIDS_DEST), COLOR,
# LOCATE, LET's LHS type, OPEN's device type; the tape-save / RESUME NEXT pair
# TSV_PTR (= SSE_OUT) / TSV_CNT -> BUF $F5FA-$F5FC. `s14stx` sums the 11
# vacated bytes (VG-8020 1815); `ovstx` stages INPUT$(255) in STRSCR -- up to
# $F65D -- INSIDE a MID$ statement, whose target is held in WSTX at $F65E.
for _r in ("s14stx", "ovstx"):
    RANGES[_r] = RANGES["all"]
_S14C_SUM = ['900 SCREEN 0:S=0:RESTORE 950:FOR K=1 TO 7:READ P,Q:FOR J=P TO Q:S=S+PEEK(J):NEXT:NEXT'
             ':PRINT"[S";S;"]":END',
             "950 DATA 60669,60670,61051,61052,61242,61242,61277,61278,61281,61281,61407,61408,61804,61804"]
# D-WSZERO S14d (2026-10-16): INPUT$ allocates its result in string space (as
# INKEY$ does, and the reference: it raises 14 BEFORE taking a key --
# scratchpad/inpoom_probe.out), so no expression writes BUF past STRSCR+8; BUFTX
# ($F567-$F59F) then holds the cells FOR, PRINT USING and DRAW keep across their
# own evaluation. `s14buf` sums the 88 vacated bytes (VG-8020 14520); `ovbuftx`
# is the lever's witness: FOR's limit and step come from INPUT$(40) / INPUT$(2)
# and PRINT USING's item from INPUT$(60) -- staged in BUF, they would overwrite
# FOR's frame.
for _r in ("s14buf", "ovbuftx"):
    RANGES[_r] = RANGES["all"]
RUN_GAP["s14buf"] = 60.0
# `inpoom`: the INPUT$ change is also a BEHAVIOUR fix. With no string space the
# VG-8020 raises 14 BEFORE taking a key (the typed keys stay queued: 30 + Enter);
# zerobas read the keys into BUF first and left only the Enter
# (scratchpad/inpoom_probe.out). No load: the tape is never read.
RANGES["inpoom"] = (0, 0)
_S14D_SUM = ['900 SCREEN 0:S=0:RESTORE 950:FOR K=1 TO 5:READ P,Q:FOR J=P TO Q:S=S+PEEK(J):NEXT:NEXT'
             ':PRINT"[S";S;"]":END',
             "950 DATA 60728,60760,60775,60798,61194,61219,61581,61583,61589,61590"]
KNOWN_DIVERGE = set()

PROGRAM_NOCLEAR = [
    "NEW",
    '10 BLOAD"CAS:",R',
    '20 PRINT"[A]";:GOSUB 100:FOR I=1 TO 2:PRINT I;:NEXT:A$="X"+"Y":PRINT A$;"]"',
    "30 END",
    '100 PRINT"[G]";:RETURN',
    "RUN",
]
PROGRAM_RICH = [
    "NEW",
    '10 CLEAR 300,&HE000:DEFFNF(X)=X*2+1:READ P:BLOAD"CAS:",R',
    '20 SCREEN 2:CIRCLE(128,96),60,15:PAINT(128,96),4,15:C=POINT(128,96):SCREEN 0',
    '30 F=FNF(3):READ Q:FOR K=1 TO 40:B$=B$+"Z":NEXT:DIM Z(50):Z(50)=7:PLAY"T255L64C"',
    '40 PRINT"[";F;P;Q;LEN(B$);Z(50);C;:PRINT USING"##.##";3.14159;:PRINT"]"',
    "90 DATA 5,6",
    "RUN",
]
PROGRAM_RICH2 = [
    "NEW",
    '10 CLEAR 300,&HE000:A$="HELLO":DIM W(9):BLOAD"CAS:",R',
    '20 ON INTERVAL=2 GOSUB 100:INTERVAL ON:FOR K=1 TO 300:NEXT:INTERVAL OFF',
    '30 MID$(A$,2,2)="EY":I=INSTR(A$,"LO"):B$=STRING$(3,"Q"):SWAP A$,B$:ERASE W',
    '40 R=SQR(16)+INT(SIN(0))+INT(RND(1)):V=VAL(STR$(12)):VPOKE 6000,77:Q=VPEEK(6000)',
    '50 LOCATE 0,20:PRINT"[";-(T>0);A$;B$;I;R;V;Q;"]"',
    "60 END",
    "100 T=T+1:RETURN",
    "RUN",
]
PROGRAM_PERSIST = [
    "NEW",
    '10 CLEAR 100,&HE000:SCREEN 2:DRAW"S8A1":BLOAD"CAS:",R',
    '20 PSET(100,100),15:DRAW"C15R3U2"',
    '30 FOR Y=92 TO 108:FOR X=92 TO 108:IF POINT(X,Y)=15 THEN N=N+1:S=S+X*3+Y',
    '40 NEXT:NEXT:SCREEN 0:ON ERROR GOTO 100:OPEN"A:X"FOR INPUT AS#1',
    '50 PRINT"[";N;S;"]":END',
    '100 PRINT"[E";ERR;"]";:RESUME 50',
    "RUN",
]
PROGRAM_CHAN = [
    "NEW",
    '10 CLEAR 100,&HE000:ON ERROR GOTO 100:OPEN"CRT:"FOR OUTPUT AS#1:BLOAD"CAS:",R',
    '20 PRINT#1,"[C]"',
    '30 CLOSE#1:OPEN"CRT:"FOR OUTPUT AS#1:PRINT#1,"[D]":CLOSE',
    '40 FILES',
    '50 PRINT"[N]":END',
    '100 PRINT"[E";ERR;ERL;"]":RESUME NEXT',
    "RUN",
]
PROGRAM_INPUT = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 CLS:FOR R=0 TO 9:PRINT"[R";STRING$(34,"X");"]":NEXT:VPOKE &H25A5,7',
    '30 INPUT"[I";A:PRINT"[V";A;VPEEK(&H25A5);"]":END',
    "RUN",
    "@WAIT40",
    "42",
]
PROGRAM_MIDLINE = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R:DEFFNA(X)=X+1:PRINT"[A";FNA(1);"]";:ERROR 2',
    "RUN",
]
PROGRAM_RESUME = [
    "NEW",
    '10 CLEAR 100,&HE000:ON ERROR GOTO 100',
    '20 PRINT"[A]";:ERROR 2:PRINT"[B]"',
    '30 PRINT"[C]":END',
    '100 BLOAD"CAS:",R:RESUME NEXT',
    "RUN",
]
PROGRAM_CONTDIR = [
    "NEW",
    "CLEAR 100,&HE000",
    'BLOAD"CAS:",R',
    "@WAIT40",
    "CONT",
    'PRINT"[Z";ERR;"]"',
]
PROGRAM_PRM = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 CLS:PRINT"[P]"',
    "RUN",
    "@WAIT40",
    'PRINT"[Y";CSRLIN;"]"',
]
PROGRAM_FLDREAD = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 AA$="OK":PRINT"[";AA$;LEN(AA$);"]"',
    "RUN",
]
PROGRAM_FLDCLR = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    f'20 CLEAR 100,&HE000:PRINT"[";PEEK(&H{FT:04X});PEEK(&H{FT + 6:04X});PEEK(&H{FT + 90:04X});"]"',
    "RUN",
]
PROGRAM_FLDERASE = [
    "NEW",
    '10 CLEAR 100,&HE000:DIM W(9):BLOAD"CAS:",R',
    f'20 ERASE W:PRINT"[";PEEK(&H{FT + 1:04X});PEEK(&H{FT + 2:04X});"]"',
    "RUN",
]
PROGRAM_LSET = [
    "NEW",
    '10 CLEAR 100,&HE000:ON ERROR GOTO 100:BLOAD"CAS:",R',
    '20 LSET A$="X":RSET A$="X":FIELD#1,2 AS A$',
    f'30 PRINT"[";PEEK(&H{sym("LRSET_JUST"):04X});PEEK(&H{sym("FLD_CHAN"):04X});"]":END',
    '100 PRINT"[E";ERR;"]";:RESUME NEXT',
    "RUN",
]
PROGRAM_INPEOF = [
    "NEW",
    "10 ON ERROR GOTO 100",
    f'20 OPEN"CAS:D"FOR INPUT AS#1:LINE INPUT#1,A$:POKE &H{sym("DISKOP_ERR"):04X},165:LINE INPUT#1,B$',
    '30 PRINT"[";A$;"]":END',
    '100 PRINT"[E";ERR;ERL;"]";:RESUME 30',
    "RUN",
]
PROGRAM_VALTYP = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    f'20 A$="X":PRINT"[";PEEK(&H{VALTYP_OLD:04X});"]"',
    "RUN",
]
PROGRAM_S11GFX = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 SCREEN 2,2:SPRITE$(0)=STRING$(32,255):A$=SPRITE$(0):PUT SPRITE 0,(60,60),15,0:VDP(7)=VDP(7)',
    '30 LINE(10,10)-(60,40),15,B:LINE-(80,80),15:CIRCLE(128,96),40,15,-.5,-2.5,1.4',
    '40 B$="D3":K=4:DRAW"BM100,100S8A1NR10C15U5XB$;R=K;":GOTO 900',
] + _S11_SUM + ["RUN"]
PROGRAM_S11NUM = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 DIM X(2):READ X(1),B$:A%=7\\2:B%=-7 MOD 3:C#=1#/3#:D=1.5*2.25:E=A%+1.5:V=VAL("12.5E1")',
    '30 PRINT 1/3;123;HEX$(255);OCT$(8):PRINT USING"##.##";V:KEY 1,"AB":C$=B$+"Z":GOTO 900',
    '60 DATA 5,"Q"',
] + _S11_SUM + ["RUN"]
PROGRAM_S11INP = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 DIM A(2):INPUT"[I";A(1):GOTO 900',
] + _S11_SUM + ["RUN", "@WAIT40", "42"]
PROGRAM_S12GFX = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 SCREEN 2,2:SPRITE$(0)=STRING$(32,255):A$=SPRITE$(0):PUT SPRITE 0,(60,60),15,0',
    '30 LINE(10,10)-(60,40),15,B:LINE(70,10)-(120,40),15,BF:CIRCLE(128,96),40,15,-.5,-2.5,1.4',
    '40 CIRCLE(60,140),20,15:PAINT(60,140),15:DRAW"BM200,100R10D10L10":GOTO 900',
] + _S12_SUM + ["RUN"]
PROGRAM_S12NUM = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 DIM X(2):DEFINT W:READ X(1),B$:C#=1#/3#:D=1.5*2.25:E=300*200:A%=7:F=A%+1.5:V=VAL("12.5E1")',
    '30 J=INSTR("ABCDEF","DE"):PLAY"T255L64C":PRINT"[U";:PRINT USING"##.##^^^^";V',
    '40 PRINT"[N";X(1);C#;D;E;F;J;"]":GOTO 900',
    '60 DATA 5.5,"Q"',
] + _S12_SUM + ["RUN"]
PROGRAM_S12INP = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 DIM A(2):INPUT"[I";A(1):LINE INPUT"[L";B$:GOTO 900',
] + _S12_SUM + ["RUN", "@WAIT40", "4.2", "HI"]
PROGRAM_S12DIR = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    "20 END",
] + _S12_SUM + ["RUN", "@WAIT40", 'MERGE"CAS:"', "@WAIT40", "RENUM 2000,900,100", "GOTO 2000"]
# (the waits: lines typed while the tape load ran lost their leading characters
# on the VG-8020 -- the harness reported it as an apparatus failure, first cut)
PROGRAM_OVBUF = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 SCREEN 2:DRAW INPUT$(24):P=POINT(50,10)+2*POINT(50,50)+4*POINT(10,50)',
    '30 CIRCLE(128,96),30,15:PAINT(128,96),15:Q=POINT(128,96):LINE(0,0)-(20,20),15,BF:R=POINT(5,5)',
    '40 SCREEN 0:PRINT"[P";P;Q;R;"]":END',
    "RUN", "@WAIT40", "BM10,10R40D40L40U40BM0,0",
]
PROGRAM_OVFN = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 DEF FNA(A,B,C,D,E,F,G,H,I)=A+B+C+D+E+F+G+H+I:DEF FNE(X)=Y(99):X=7:DIM Z(2):ON ERROR GOTO 100',
    '30 PRINT"[U";:PRINT USING"###.##";FNA(1,2,3,4,5,6,7,8,9.5):SCREEN 2:K=FNA(1,1,1,1,1,1,1,1,2):DRAW"BM50,50R=K;D10"',
    '40 Q=POINT(55,50)+2*POINT(60,55):CIRCLE(FNA(1,2,3,4,5,6,7,8,9)+83,96),FNA(1,1,1,1,1,1,1,1,12),15:R=POINT(128,76)',
    '45 READ Z(FNA(0,0,0,0,0,0,0,0,1)):W=FNE(1)',
    '50 SCREEN 0:LINE INPUT"[L";B$:PRINT"[F";Q;R;Z(1);X;B$;"]":END',
    '60 DATA 5',
    '100 RESUME NEXT',
    "RUN", "@WAIT40", "HI",
]
PROGRAM_OVLEAF = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 SCREEN 2,VAL("2"):SPRITE$(0)=STRING$(32,VAL("255")):A$=SPRITE$(VAL("0")):PUT SPRITE 0,(INSTR("ABC","C")*10,VAL("50")),15,0',
    '30 J=INSTR(STR$(1/3),"3"):K=VAL("1.5E1")*3/7:L=300*200:M=VAL("2.5")+1.5:PLAY"T200L64C"',
    '40 SCREEN 0:PRINT"[V";LEN(A$);ASC(A$);J;K;L;M;"]":END',
    "RUN",
]
PROGRAM_OVFBUF = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 A=1/3:B$=STR$(-2/3):C=1.5*2.25:D#=-1.23456789012345D-12:PRINT"[Q";A;B$;C;D#;-7/3;"]":END',
    "RUN",
]
PROGRAM_S14EQ = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 A=1.5:B%=A\\1:C=A MOD 1:POKE &HE000+.5,1:H$=HEX$(255.4):X=INT(-1.5):A%=2.5:A#=A%',
    '30 A$="AB"+"C":PRINT"[L";A$;"]":DEFINT W:PLAY"C":K=VAL("12.5"):GOTO 900',
] + _S14A_SUM + ["RUN"]
PROGRAM_OVDAC = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 DIM A(3),Q(3):INPUT"[I";A%:A(VAL("1"))=INT(-2.5):B=1.5*2.25+INT(VAL("-0.5")):DEF FNC(X%)=X%\\2:Z=FNC(7.9)',
    '25 READ R,R$:READ Q(VAL("2"))',
    '30 PRINT"[D";A%;A(1);B;Z;R;R$;"]":END',
    '40 DATA 7.5,"X",9',
    "RUN", "@WAIT40", "2.5E1",
]
PROGRAM_OVARGB = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    # rounded to 6 digits: the full 14-digit results differ from the VG-8020's in
    # the last digit or two on zerobas already (a math-precision difference this
    # row is not about); an overlay fault garbles far more than that
    '15 DEF FNR(X)=INT(X*1E6+.5)',
    '20 PRINT"[M";FNR(SQR(2));FNR(ATN(1))',
    '30 PRINT"[N";FNR(2^0.5);FNR(EXP(1))',
    '40 PRINT"[O";FNR(LOG(2));FNR(SIN(1))',
    '50 PRINT"[P";(1/3)\\1;"]":END',
    "RUN",
]
PROGRAM_S14LST = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 KEY 1,"ABC":KEY LIST:PRINT USING"&";STRING$(120,"A"):END',
    "30 REM " + "LISTME" * 32,
] + _S14B_SUM + ["RUN", "@WAIT40", "LIST 30", "GOTO 900"]
PROGRAM_OVKEY = [
    "NEW",
    # CLEAR 300: the first cut's 100 B of string space refused the 170-char answer
    # with `Out of string space` on BOTH machines -- SAME, and blind
    '10 CLEAR 300,&HE000:BLOAD"CAS:",R',
    '20 KEY ON:LINE INPUT"[L";B$:PRINT"[B";LEN(B$);ASC(MID$(B$,163));"]":KEY LIST:END',
    "RUN", "@WAIT40", "A" * 162 + "Q" + "B" * 7,
]
PROGRAM_S14STX = [
    "NEW",
    '10 CLEAR 100,&HE000:ON ERROR GOTO 100:BLOAD"CAS:",R',
    '20 COLOR 15,4:LOCATE 5,5:OPEN"CRT:"FOR OUTPUT AS#1:PRINT#1,"[C]":CLOSE:A$="ABCDE":MID$(A$,2)="XY":A%=1.5',
    '30 ERROR 5:PRINT"[R";A$;A%;"]":GOTO 900',
    '100 RESUME NEXT',
] + _S14C_SUM + ["RUN"]
PROGRAM_OVSTX = [
    "NEW",
    '10 CLEAR 400,&HE000:BLOAD"CAS:",R',
    '20 DIM A$(3):A$(1)="ABCDE":MID$(A$(1),LEN(INPUT$(255))-252)=STRING$(2,"Q"):PRINT"[M";A$(1);"]":END',
    # 200 + Enter + 54 = the 255 keys INPUT$(255) takes (the harness refuses a
    # typed line over 254 characters -- first cut)
    # Z, not Q: the echo guard read the result's "QQ" as a mangled echo of a
    # typed Q line (second cut, an APPARATUS FAILURE on the VG-8020)
    "RUN", "@WAIT40", "Z" * 200, "Z" * 54,
]
PROGRAM_S14BUF = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 FOR I=1 TO 2.5 STEP .5:NEXT:PRINT USING"##.##";I:PRINT USING"#,###";1234',
    '30 SCREEN 2:A$="R2":B$="XA$;D2":C$="XB$;L2":V=3:DRAW"BM50,50XC$;U=V;":GOTO 900',
] + _S14D_SUM + ["RUN"]
PROGRAM_OVBUFTX = [
    "NEW",
    '10 CLEAR 300,&HE000:BLOAD"CAS:",R',
    '20 FOR I=1 TO LEN(INPUT$(40)) STEP LEN(INPUT$(2)):S=S+I:NEXT',
    '30 PRINT"[F";S;I;"]":PRINT USING"[U##.##]";LEN(INPUT$(60))/7:END',
    # each typed line is its keys + Enter: 39+1 = 40, 1+1 = 2, 59+1 = 60
    "RUN", "@WAIT40", "Z" * 39, "Z", "Z" * 59,
]
PROGRAM_INPOOM = [
    "NEW", "10 CLEAR 10:ON ERROR GOTO 100", '20 A$=INPUT$(30):PRINT"[OK";LEN(A$);"]":END',
    "100 T=TIME", "110 IF TIME-T<300 THEN 110", "120 N=0",
    '130 K$=INKEY$:IF K$<>"" THEN N=N+1:GOTO 130', '140 PRINT"[E";ERR;N;"]":END',
    "RUN", "Z" * 30,
]
PROGRAM_ABORT = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 PRINT"[A]";:ERROR 2',
    "RUN",
]
PROGRAM_ONERR = [
    "NEW",
    '10 CLEAR 100,&HE000:ON ERROR GOTO 100:BLOAD"CAS:",R',
    '20 PRINT"[A]";:ERROR 2',
    '30 PRINT"[R]";:GOSUB 200:PRINT"]":END',
    '100 PRINT"[E";ERR;"]";:RESUME 30',
    '200 PRINT"[G]";:RETURN',
    "RUN",
]
PROGRAM = [
    "NEW",
    '10 CLEAR 100,&HE000:BLOAD"CAS:",R',
    '20 PRINT"[A]";:GOSUB 100:FOR I=1 TO 2:PRINT I;:NEXT:A$="X"+"Y":PRINT A$;"]"',
    "30 END",
    '100 PRINT"[G]";:RETURN',
    "RUN",
]


PROGRAMS = {**{n: PROGRAM_NOCLEAR for n in NOCLEAR}, "abort": PROGRAM_ABORT,
            "onerr": PROGRAM_ONERR, "rich": PROGRAM_RICH, "rich2": PROGRAM_RICH2,
            "persist": PROGRAM_PERSIST, "chan": PROGRAM_CHAN, "input": PROGRAM_INPUT,
            "midline": PROGRAM_MIDLINE, "resume": PROGRAM_RESUME,
            "contdir": PROGRAM_CONTDIR, "prm": PROGRAM_PRM,
            "fldread": PROGRAM_FLDREAD, "fldclr": PROGRAM_FLDCLR,
            "flderase": PROGRAM_FLDERASE, "lset": PROGRAM_LSET,
            "inpeof": PROGRAM_INPEOF, "valtyp": PROGRAM_VALTYP,
            "s11gfx": PROGRAM_S11GFX, "s11num": PROGRAM_S11NUM, "s11inp": PROGRAM_S11INP,
            "s12gfx": PROGRAM_S12GFX, "s12num": PROGRAM_S12NUM, "s12inp": PROGRAM_S12INP,
            "s12dir": PROGRAM_S12DIR, "ovbuf": PROGRAM_OVBUF, "ovfn": PROGRAM_OVFN,
            "ovleaf": PROGRAM_OVLEAF, "ovfbuf": PROGRAM_OVFBUF,
            "s14eq": PROGRAM_S14EQ, "ovdac": PROGRAM_OVDAC, "ovargb": PROGRAM_OVARGB,
            "s14lst": PROGRAM_S14LST, "ovkey": PROGRAM_OVKEY,
            "s14stx": PROGRAM_S14STX, "ovstx": PROGRAM_OVSTX,
            "s14buf": PROGRAM_S14BUF, "ovbuftx": PROGRAM_OVBUFTX, "inpoom": PROGRAM_INPOOM}


def tape(lo, hi, fill=0xA5):
    data = bytes([0xC9]) + bytes([fill]) * (hi - lo)
    return build_cas("W", lo, lo, data)


def rows(scr):
    if scr is None:
        return None
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    keep = [x.strip() for x in r if x.strip().startswith("[") or "rror" in x
            or "zerobas" in x or "Microsoft" in x]
    return " | ".join(keep)


def main():
    only = sys.argv[1:] or list(RANGES)
    tmp = tempfile.mkdtemp(prefix="wszero_")
    bad, rotted, blind = [], [], []
    for name in only:
        lo, hi = RANGES[name]
        path = os.path.join(tmp, f"{name}.cas")
        open(path, "wb").write(TAPES[name]() if name in TAPES else tape(lo, hi, FILL.get(name, 0xA5)))
        got = {}
        for side, m in (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            prog = PROGRAMS.get(name, PROGRAM)
            got[side] = rows(omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                                 reset=("", "SCREEN 0:WIDTH 40"), step=3.0,
                                                 run_gap=RUN_GAP.get(name, 40.0), cassette=path)[0])
        if not got["VG"]:
            blind.append(name)
            verdict = "NO-REFERENCE"
        elif got["VG"] == got["ZB"]:
            verdict = "SAME"
            if name in KNOWN_DIVERGE:
                rotted.append(name)
                verdict = "SAME (PIN ROTTED)"
        else:
            verdict = "DIVERGES (pinned)" if name in KNOWN_DIVERGE else "DIVERGES"
            if name not in KNOWN_DIVERGE:
                bad.append(name)
        print(f"ROW {name} ${lo:04X}-${hi:04X} VG=[{got['VG']}] ZB=[{got['ZB']}] {verdict}",
              flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the VG-8020 gave no reading on {', '.join(blind)}")
        return 2
    ok = not bad and not rotted
    print(f"\n{'PASS' if ok else 'FAIL'}: a load over the window, then BASIC "
          f"({len(only) - len(bad) - len(rotted)}/{len(only)} as pinned)"
          + (f"; unpinned divergence: {', '.join(bad)}" if bad else "")
          + (f"; ROTTED pins (now SAME, remove them): {', '.join(rotted)}" if rotted else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
