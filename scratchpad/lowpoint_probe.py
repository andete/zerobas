"""D-DIMRESERVE S3: how far does a statement's stack go BELOW its deepest
passing stk_guard -- and how deep does it go before any guard has passed?

The two numbers a smaller reserve has to cover (basic/sysvars.inc):
  * BELOW-GUARD: a guard that passed at SP_g proves SP_g > CTLLIM +
    STK_EVAL_RESERVE, so a later write at address a is safe iff
    SP_g - a <= STK_EVAL_RESERVE. Max over every stack write of
    (deepest passing guard SP so far - a) is the evaluator reserve's floor.
  * UNGUARDED: a write before any guard has passed is covered only by what DIM,
    a new scalar and the line store leave (CTL_STACK_MARGIN). Max (CSP - a).
Also the deepest guard itself (CSP - SP_g): guard + reserve is what a flat
statement needs at the edge without an ERR 7.

zerobas's OWN machine only (a breakpoint on our stk_guard, a write watchpoint on
our own stack band; nothing of the reference's). The watchpoint is armed at the
first guard of the run over [CSP-1500, CSP), and only writes while CURLIN
($F41C) is in 30..39 count, measured against the CSP of the moment (a FOR frame
moves it). Every workload repeats 30 times with PLAY running in the background,
so interrupts land at many depths. PAINT is left out: its span stack is its own
margin's business (GFX_PAINT_MARGIN) and would read as stack writes here.

    python3 -u scratchpad/lowpoint_probe.py [case ...]
"""
import os, re, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"
if os.environ.get("LP_DISK"):           # LP_DISK=1: the disk machine (its H.TIMI too)
    ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
R = "30 FOR K=1 TO 30:{}:NEXT"
CASES = {
    "assign":  [R.format("A=1")],
    "add":     [R.format("B=A+1")],
    "var":     [R.format("B=A")],
    "if":      [R.format("IF A=0 THEN B=2")],
    "print":   [R.format('LOCATE 0,20:PRINT 1;"X";2.5;')],
    "using":   [R.format('LOCATE 0,20:PRINT USING "##.#";1.5;')],
    "strings": [R.format('A$=MID$(LEFT$("ABCDEF",4),2,2)+CHR$(65)')],
    "strnum":  [R.format("A$=STR$(1.5)+HEX$(255)")],
    "gosub":   [R.format("GOSUB 36"), "35 GOTO 40", "36 B=1:RETURN"],
    "fn":      [R.format("X=FNA(2)")],
    "array":   [R.format("Z(1)=Z(2)+1")],
    "trans":   [R.format("X=SIN(1)+ATN(.5)+EXP(2.5)+LOG(3)+SQR(2)+1.5^2.5")],
    "val":     [R.format('X=VAL("1.5")')],
    "vpoke":   [R.format("VPOKE 0,VPEEK(0)")],
    "sound":   [R.format("SOUND 8,0")],
    "strig":   [R.format("X=STICK(0)+STRIG(0)")],
    "instr":   [R.format('X=INSTR("ABC","C")')],
    "graphics":["30 SCREEN 2:FOR K=1 TO 10:PSET(K,1):LINE(0,0)-(K,9):CIRCLE(50,50),K:NEXT:SCREEN 0"],
    "trap":    ["30 ON INTERVAL=1 GOSUB 36:INTERVAL ON:FOR K=1 TO 60:NEXT:INTERVAL OFF",
                "35 GOTO 40", "36 B=B+1:RETURN"],
    "chain":   [R.format("B=((((1+1)+1)+1)+1)")],
    "gc":      [R.format('A$=STRING$(40,65)+B$:B$=LEFT$(A$,20)')],
    "list":    ['30 FOR K=1 TO 3:LIST 5-10:NEXT'],
    "next":    ["30 FOR K=1 TO 30:NEXT:FOR K=1 TO 30 STEP .5:NEXT"],
    "cls":     ["30 FOR K=1 TO 10:CLS:BEEP:KEY OFF:KEY ON:NEXT"],
    "keylist": ["30 KEY LIST"],
    "errtrap": ["30 ON ERROR GOTO 36:FOR K=1 TO 10:ERROR 5:NEXT", "35 GOTO 40",
                "36 RESUME NEXT"],
    "errmsg":  ["30 ON ERROR GOTO 36:FOR K=1 TO 3:ERROR 5:NEXT", "35 GOTO 40",
                "36 ON ERROR GOTO 0:RESUME NEXT"],
    "files":   ['30 FOR K=1 TO 3:FILES:NEXT'],
    # DIRECT MODE (CURLIN = 65535): the line editor typing and storing lines,
    # and direct statements. Armed on a timer after boot, not on a guard.
    "dm_edit": ["10 REM " + "A" * 60, "20 REM " + "B" * 60, "15 PRINT 1",
                "PRINT 1;2", "A=1", "LIST", "KEY LIST", "15", "PRINT FRE(0)"],
    "strcmp":  [R.format('IF "AB"+A$<"AC"+LEFT$(A$,1) THEN B=1')],
    "space":   [R.format('A$=SPACE$(10)+STRING$(5,"X")+RIGHT$(STR$(K),1)')],
}


def sym(name):
    for line in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        p = line.split()
        if p and p[0] == name:
            return int(p[2].rstrip("H"), 16)
    raise SystemExit(f"REFUSE: {name} not in build/basic-reloc.sym -- build first")


def prog(lines):
    return (["NEW", "5 DEF FNA(X)=X*2+1:DIM Z(3)",
             '10 PLAY "L64T255CDEFGABCDEFGABCDEFGAB","L64T255CDEFGABCDEFGAB"']
            + lines + ['40 PRINT CHR$(91);"DONE";CHR$(93):END', "RUN"])


TCL = r"""
set ::gmin 65536
set ::below -1
set ::ung 0
set ::gdeep 0
set ::armed 0
set ::writes 0
set ::total 0
proc ::ln {} { expr {[peek 0xF41C] + 256*[peek 0xF41D]} }
proc ::csp {} { expr {[peek 0xE050] + 256*[peek 0xE051]} }
proc ::dump {} {
  set f [open {OUT} w]
  puts $f "$::gdeep $::below $::ung $::writes $::total"
  close $f
}
proc ::onwrite {} {
  set ln [::ln]
  if {LINEFILTER} return
  set a $::wp_last_address
  set c [::csp]
  if {$a >= $c} return
  incr ::writes
  set t [expr {$c - $a}]
  if {$t > $::total} { set ::total $t; ::dump }
  if {$::gmin < 65536} {
    set b [expr {$::gmin - $a}]
    if {$b > $::below} { set ::below $b; ::dump }
  } else {
    set u [expr {$c - $a}]
    if {$u > $::ung} { set ::ung $u; ::dump }
  }
}
proc ::arm {} {
  if {!$::armed} {
    set ::armed 1
    set c [::csp]
    debug set_watchpoint write_mem [list [expr {$c - 1500}] [expr {$c - 1}]] {} ::onwrite
  }
}
proc ::onguard {} {
  ::arm
  set ln [::ln]
  if {LINEFILTER} return
  set sp [expr {[reg sp] + 2}]
  if {$sp < $::gmin} { set ::gmin $sp }
  set g [expr {[::csp] - $sp}]
  if {$g > $::gdeep} { set ::gdeep $g; ::dump }
}
debug set_bp GUARD {[pc_in_slot 0]} ::onguard
"""


def main():
    g = sym("stk_guard")
    names = sys.argv[1:] or list(CASES)
    d = tempfile.mkdtemp(prefix="zb_lowpoint_")
    print(f"{ZB}: stk_guard @ ${g:04X}; bytes; every workload x30 with PLAY in the background")
    print(f"  {'case':9} {'deepest guard':>13} {'below guard':>12} {'unguarded':>10} {'writes':>7} {'TOTAL':>6}")
    agg = [0, 0, 0, 0]
    bad = []
    for name in names:
        out = os.path.join(d, name)
        open(out, "w").close()
        tcl = TCL.replace("{OUT}", "{" + out + "}").replace("GUARD", f"0x{g:04X}")
        direct = name.startswith("dm_")
        tcl = tcl.replace("LINEFILTER", "$ln != 65535" if direct else "$ln < 30 || $ln > 39")
        if direct:                      # no program: arm on a timer once booted
            tcl += "\nafter time 9 ::arm\n"
        typed = (["NEW"] + CASES[name] + ['PRINT CHR$(91);"DONE";CHR$(93)']) if direct \
            else prog(CASES[name])
        raw = omsx_repl.run_cases(ZB, [("direct", typed)], batch=False,
                                  reset=("CLS",), boot=8.0, step=3.0, run_gap=90.0,
                                  capture="screen", prologue=(tcl,))[0]
        txt = open(out).read().split()
        done = "[DONE]" in (raw or "").replace(" ", "")
        if not done or len(txt) != 5 or int(txt[3]) == 0:
            print(f"  {name:9} NO READING (done {done}, file {txt})", flush=True)
            bad.append(name)
            continue
        gd, below, ung, writes, total = map(int, txt)
        agg = [max(agg[0], gd), max(agg[1], below), max(agg[2], ung), max(agg[3], total)]
        print(f"  {name:9} {gd:13} {below:12} {ung:10} {writes:7} {total:6}", flush=True)
    print(f"\nMAX: deepest guard {agg[0]}, below guard {agg[1]}, unguarded {agg[2]}, TOTAL {agg[3]}"
          + (f"   NO READING: {' '.join(bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
