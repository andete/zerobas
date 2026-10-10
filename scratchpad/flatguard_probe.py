"""D-DIMRESERVE S3: how deep is a STATEMENT's stack when its first factor passes
stk_guard? That depth plus STK_EVAL_RESERVE is what a DIM must leave for the
next statement to evaluate at all -- the floor under any smaller reserve.

zerobas only (a breakpoint on our OWN stk_guard, main ROM slot 0; nothing of the
reference's): the breakpoint keeps the lowest SP it saw while CURLIN ($F41C) is
in 30..39 -- the workload's own lines, an interrupt-trap handler at 36 included
-- and the reading is CSP minus that SP (bytes below the pool's frontier). The
breakpoint fires on the CALL target, so SP holds stk_guard's own return
address: the reading is CONSERVATIVE by 2 B.

    python3 -u scratchpad/flatguard_probe.py [case ...]
"""
import os, re, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"
CASES = {
    "assign":  ["30 A=1"],
    "add":     ["30 B=A+1"],
    "if":      ["30 IF A=0 THEN B=2"],
    "ifelse":  ["30 IF A=1 THEN B=2 ELSE B=3"],
    "print":   ['30 PRINT 1;"X";2.5'],
    "using":   ['30 PRINT USING "##.#";1.5'],
    "strings": ['30 A$=MID$(LEFT$("ABCDEF",4),2,2)+CHR$(65)'],
    "locate":  ["30 LOCATE 0,20"],
    "gosub":   ["30 GOSUB 36", "35 GOTO 40", "36 B=1:RETURN"],
    "ongosub": ["30 ON 1 GOSUB 36", "35 GOTO 40", "36 B=1:RETURN"],
    "for":     ["30 FOR I=1 TO 2:NEXT"],
    "fn":      ["30 X=FNA(2)"],
    "array":   ["30 Z(1)=Z(2)+1"],
    "vpoke":   ["30 VPOKE 0,VPEEK(0)"],
    "sound":   ["30 SOUND 8,0"],
    "play":    ['30 PLAY "C":B=1'],
    "color":   ["30 COLOR 15,4,4"],
    "graphics":["30 SCREEN 2:PSET(1,1):LINE(0,0)-(9,9):CIRCLE(50,50),9:SCREEN 0"],
    "read":    ["30 READ X", "31 DATA 1.5"],
    "swap":    ["30 SWAP A,B"],
    "midasg":  ['30 A$="ABC":MID$(A$,1,1)="Z"'],
    "instr":   ['30 X=INSTR("ABC","C")'],
    "trap":    ["30 ON INTERVAL=1 GOSUB 36:INTERVAL ON:FOR I=1 TO 30:NEXT:INTERVAL OFF",
                "35 GOTO 40", "36 B=B+1:RETURN"],
    "strig":   ["30 X=STICK(0)+STRIG(0)"],
    "chain":   ["30 B=((((1+1)+1)+1)+1)"],
}


def sym(name):
    for line in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        p = line.split()
        if p and p[0] == name:
            return int(p[2].rstrip("H"), 16)
    raise SystemExit(f"REFUSE: {name} not in build/basic-reloc.sym -- build first")


def prog(lines):
    return (["NEW", "5 DEF FNA(X)=X*2+1:DIM Z(3)",
             "10 C=PEEK(&HE050)+256*PEEK(&HE051):C%=C-65536"]
            + lines +
            ["40 PRINT CHR$(91);C%;CHR$(93):END", "RUN"])


def main():
    g = sym("stk_guard")
    names = sys.argv[1:] or list(CASES)
    d = tempfile.mkdtemp(prefix="zb_flatguard_")
    print(f"stk_guard @ ${g:04X}; bytes below CSP at the lowest passing guard, lines 30-39")
    worst, bad = (0, None), []
    for name in names:
        out = os.path.join(d, name)
        open(out, "w").close()
        tcl = ("set ::mins 65536",
               f"debug set_bp 0x{g:04X} {{[pc_in_slot 0]}} "
               f"{{ set ln [expr {{[peek 0xF41C] + 256*[peek 0xF41D]}}];"
               f" if {{$ln >= 30 && $ln <= 39 && [reg sp] < $::mins}} {{"
               f" set ::mins [reg sp]; set f [open {{{out}}} w];"
               f" puts $f $::mins; close $f }} }}")
        raw = omsx_repl.run_cases(ZB, [("direct", prog(CASES[name]))], batch=False,
                                  reset=("CLS",), boot=8.0, step=3.0, run_gap=60.0,
                                  capture="screen", prologue=tcl)[0]
        m = re.findall(r"\[\s*(-?\d+)\s*\]", raw or "")
        txt = open(out).read().strip()
        if not m or not txt:
            print(f"  {name:9} NO READING  (screen {'ok' if m else 'none'},"
                  f" bp {'ok' if txt else 'none'})", flush=True)
            bad.append(name)
            continue
        c = int(m[-1]) & 0xFFFF
        depth = c - int(txt)
        worst = max(worst, (depth, name))
        print(f"  {name:9} {depth:5}   {CASES[name][0][3:]}", flush=True)
    print(f"\nWORST: {worst[1]} {worst[0]} B" + (f"   NO READING: {' '.join(bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
