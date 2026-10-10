"""D-DIMRESERVE (a): WHAT runs below a passing stk_guard? The evaluator's reserve
(STK_EVAL_RESERVE, 128) must hold the deepest stack reached below the most
recent passing guard before the next guard; scratchpad/lowpoint_probe.py read
81 B for a string comparison. This names the words in that span.

zerobas's OWN machine only (clean room is about the reference): a breakpoint on
our stk_guard keeps the SP of the most recent guard while CURLIN is 30; a write
watchpoint on our own stack band records, at the deepest write below that guard,
the PC and every word between SP and the guard's SP, named from our symbol
tables (main, sub; a page-1 word is ambiguous between them, both printed).

    python3 -u scratchpad/guardattr_probe.py 'IF "AB"+A$<"AC"+LEFT$(A$,1) THEN B=1'
    (GA_PLAY=1: PLAY running in the background, so an interrupt can land there)
"""
import bisect, os, re, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"


def table(fn):
    out = []
    for line in open(os.path.join(REPO, "build", fn)):
        p = line.split()
        if len(p) >= 3 and p[1] == "EQU" and p[0][:1].islower():
            out.append((int(p[2].rstrip("H"), 16), p[0]))
    out.sort()
    return out


TABLES = {"main": table("basic-reloc.sym"), "sub": table("sub.sym")}


def name(v):
    hits = []
    for t, tab in TABLES.items():
        i = bisect.bisect_right(tab, (v, "￿")) - 1
        if i >= 0 and v - tab[i][0] < 0x200:
            hits.append(f"{t}:{tab[i][1]}+{v - tab[i][0]}")
    return " | ".join(hits) or "-"


TCL = r"""
set ::g -1
set ::best -1
set ::armed 0
proc ::ln {} { expr {[peek 0xF41C] + 256*[peek 0xF41D]} }
proc ::onguard {} {
  if {!$::armed} {
    set ::armed 1
    set c [expr {[peek 0xE050] + 256*[peek 0xE051]}]
    debug set_watchpoint write_mem [list [expr {$c - 1500}] [expr {$c - 1}]] {} ::onwrite
  }
  if {[::ln] != 30} return
  set ::g [expr {[reg sp] + 2}]
}
proc ::onwrite {} {
  if {[::ln] != 30 || $::g < 0} return
  set a $::wp_last_address
  set b [expr {$::g - $a}]
  if {$b <= $::best} return
  set ::best $b
  set sp [reg sp]
  set w {}
  for {set x $sp} {$x < $::g} {incr x 2} { lappend w [expr {[peek $x] + 256*[peek [expr {$x+1}]]}] }
  set f [open {OUT} w]; puts $f "$b [reg pc] $sp $::g $w"; close $f
}
debug set_bp GUARD {[pc_in_slot 0]} ::onguard
"""


def main():
    stmt = sys.argv[1] if len(sys.argv) > 1 else 'IF "AB"+A$<"AC"+LEFT$(A$,1) THEN B=1'
    g = [a for a, n in TABLES["main"] if n == "stk_guard"][0]
    out = tempfile.mktemp(prefix="zb_guardattr_")
    open(out, "w").close()
    play = '10 PLAY "L64T255CDEFGABCDEFGAB","L64T255CDEFGAB"' if os.environ.get("GA_PLAY") \
        else "10 REM"
    prog = ["NEW", "5 DEF FNA(X)=X*2+1:DIM Z(3)", play,
            f"30 FOR K=1 TO 30:{stmt}:NEXT", '40 PRINT CHR$(91);"DONE";CHR$(93):END', "RUN"]
    tcl = TCL.replace("{OUT}", "{" + out + "}").replace("GUARD", f"0x{g:04X}")
    omsx_repl.run_cases(ZB, [("direct", prog)], batch=False, reset=("CLS",), boot=8.0,
                        step=3.0, run_gap=60.0, capture="screen", prologue=(tcl,))
    txt = open(out).read().split()
    if not txt:
        raise SystemExit("REFUSE: no write below a passing guard was seen")
    b, pc, sp, gsp = (int(x) for x in txt[:4])
    words = [int(x) for x in txt[4:]]
    print(f"statement: {stmt}")
    print(f"deepest below the last passing guard: {b} B (guard SP ${gsp:04X}, SP ${sp:04X}),"
          f" PC ${pc:04X} {name(pc)}")
    print("words from SP up to the guard (offset below the guard, value, candidate):")
    for i, v in enumerate(words):
        print(f"  -{gsp - (sp + 2 * i):3}  ${v:04X}  {name(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
