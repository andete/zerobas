"""D-DIMRESERVE S3: with STK_EDGE_RESERVE at 116, does ANY statement run at the
DIM edge write into the arrays?

At the edge nothing in BASIC can read a canary back (every expression's guard
refuses, the handler's included), so the witness is a WRITE WATCHPOINT on our
own RAM from CTLLIM-12 upward (CTLLIM = ARYEND+2, basic/sysvars.inc), armed by
a breakpoint on our own exec_stmt at the first statement of line 20 (the DIM
was line 10). Only a STACK write counts -- one at or just above SP; a new
scalar shifts the arrays up with a block move whose SP is far away, and the
first cut of this probe read those twelve bytes as a corruption. Per run:
MARGIN = the lowest stack write minus the LIVE CTLLIM (< 0 is CORRUPT), over
the workload, its handlers, and DIRECT MODE afterwards (CURLIN 65535: the line
editor runs at the edge too, so every run then types direct statements).
zerobas only, our own ROM.

    python3 -u scratchpad/edgesafe_probe.py [K ...]       (LP_DISK=1: disk machine)

Each row: the outcome on screen (DONE / an error) and m<MARGIN>.
"""
import os, re, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

ZB = "C-BIOS_MSX1_EU_REPACK_DISK" if os.environ.get("LP_DISK") else "C-BIOS_MSX1_EU_REPACK_NODISK"
KS = [144, 160, 176, 192, 224]
WORK = {
    "flat":    ["20 B=1"],
    "strcmp":  ['20 IF "AB"+S$<"AC"+LEFT$(S$,1) THEN B=1'],
    "strings": ['20 S$=MID$(LEFT$(S$+"ABCDEF",4),2,2)+CHR$(65)'],
    "trans":   ["20 B=SIN(1)+ATN(.5)+EXP(2.5)+LOG(3)+SQR(2)+1.5^2.5"],
    "chain":   ["20 B=((((((((1+1)+1)+1)+1)+1)+1)+1)+1)"],
    "fn":      ["20 B=FNA(2)"],
    "using":   ['20 PRINT USING "##.#";1.5'],
    "keylist": ["20 KEY LIST"],
    "cls":     ["20 CLS:BEEP:KEY OFF:KEY ON"],
    "next":    ["20 FOR K=1 TO 20:NEXT"],
    "gosub":   ["20 GOSUB 25", "24 GOTO 30", "25 RETURN"],
    "trap":    ["20 ON INTERVAL=1 GOSUB 25:INTERVAL ON:FOR K=1 TO 40:NEXT:INTERVAL OFF",
                "24 GOTO 30", "25 RETURN"],
    "play":    ['20 PLAY "L64T255CDEFGABCDEFGAB":FOR K=1 TO 40:NEXT'],
    "error":   ["20 ERROR 5"],
    "graphics":["20 SCREEN 2:PSET(1,1):LINE(0,0)-(20,9):CIRCLE(50,50),9:SCREEN 0"],
    "list":    ["20 LIST 10-15"],
}
DIRECT = ["PRINT 1", "B=2", "LIST 15"]   # short: the program's own line stays on screen


def sym(name):
    for line in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        p = line.split()
        if p and p[0] == name:
            return int(p[2].rstrip("H"), 16)
    raise SystemExit(f"REFUSE: {name} not in build/basic-reloc.sym -- build first")


def prog(k, lines):
    return (["NEW", "5 DEF FNA(X)=X*2+1",
             f'10 CLEAR 200:S$="AB":X=INT((FRE(0)-{k})/8):DIM A(X)',
             ]
            + lines +
            ['30 PRINT CHR$(91);"DONE";CHR$(93):END', "RUN"] + DIRECT)


TCL = r"""
set ::armed 0
set ::bad 0
set ::margin 99999
proc ::ln {} { expr {[peek 0xF41C] + 256*[peek 0xF41D]} }
proc ::lim {} { expr {[peek 0xE056] + 256*[peek 0xE057]} }
proc ::dump {} {
  set f [open {OUT} w]; puts $f "$::bad $::margin $::last"; close $f
}
set ::last "-"
proc ::onwrite {} {
  set ln [::ln]
  if {$ln < 20} return
  set a $::wp_last_address
  set sp [reg sp]
  # a STACK write: at or just above SP (a push, a frame slot); a block move of
  # the arrays (a new scalar shifts them) runs with SP far above
  if {$a < $sp - 2 || $a >= $sp + 48} return
  set m [expr {$a - [::lim]}]
  if {$m < $::margin} {
    set ::margin $m
    set ::last "ln=$ln a=[format %04X $a] pc=[format %04X [reg pc]]"
    if {$m < 0} { incr ::bad }
    ::dump
  }
}
proc ::onstmt {} {
  if {$::armed || [::ln] < 20 || [::ln] == 65535} return
  set ::armed 1
  set lim [::lim]
  ::dump
  debug set_watchpoint write_mem [list [expr {$lim - 12}] [expr {$lim + 1500}]] {} ::onwrite
}
debug set_bp STMT {[pc_in_slot 0]} ::onstmt
"""


def outcome(raw):
    s = (raw or "").replace("\n", "")
    rows = [s[i:i + 40].strip() for i in range(0, len(s), 40)]
    after = [r for r in rows if r]
    for r in after:
        if "[DONE]" in r.replace(" ", ""):
            return "DONE"
        m = re.search(r"([A-Z][a-z]+( [a-z]+)*) in \d+", r)
        if m:
            return m.group(0)
    return "?" + "|".join(after[:3])[:40]


def main():
    g = sym("exec_stmt")
    ks = [int(a) for a in sys.argv[1:]] or KS
    d = tempfile.mkdtemp(prefix="zb_edgesafe_")
    print(f"{ZB}: armed at exec_stmt ${g:04X}, line >= 20; MARGIN = deepest stack write - CTLLIM (< 0: CORRUPT)")
    corrupt, unarmed = [], []
    only = os.environ.get("ES_ONLY", "").split()   # ES_ONLY="keylist list": a subset
    for name, lines in WORK.items():
        if only and name not in only:
            continue
        cases, outs = [], []
        for k in ks:
            out = os.path.join(d, f"{name}_{k}")
            open(out, "w").close()
            outs.append(out)
            cases.append(prog(k, lines))
        got = []
        for prg, out in zip(cases, outs):
            tcl = TCL.replace("{OUT}", "{" + out + "}").replace("STMT", f"0x{g:04X}")
            got.append(omsx_repl.run_cases(ZB, [("direct", prg)], batch=False,
                                           reset=("CLS",), boot=8.0, step=3.0,
                                           run_gap=30.0, capture="screen",
                                           prologue=(tcl,))[0])
        cells = []
        for k, raw, out in zip(ks, got, outs):
            txt = open(out).read().split()
            if not txt:
                cells.append(f"K{k}:UNARMED")
                unarmed.append(f"{name}@{k}")
                continue
            n, m = int(txt[0]), int(txt[1])
            if n:
                corrupt.append(f"{name}@{k} ({' '.join(txt[2:])})")
            cells.append(f"K{k}:{outcome(raw)} m{m if m < 99999 else '-'}{' CORRUPT' if n else ''}")
        print(f"  {name:9} " + "  ".join(cells), flush=True)
    print()
    print("CORRUPT: " + (", ".join(corrupt) if corrupt else "none"))
    if unarmed:
        print("UNARMED (no witness): " + ", ".join(unarmed))
    return 1 if corrupt or unarmed else 0


if __name__ == "__main__":
    sys.exit(main())
