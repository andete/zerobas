"""D-STACKFLOOR: how far below the last PASSING stk_guard does zerobas's stack go?

stk_guard (basic/expr.asm) refuses a factor when SP is within STK_EVAL_RESERVE of
the arrays; what runs BELOW a factor that passed -- a leaf routine, its sub-ROM
CALSLT frames, an interrupt -- must fit in that reserve. This measures it on
zerobas's OWN ROM (a breakpoint on our own routine; nothing of the reference's):

  * a breakpoint on stk_guard (main ROM, slot 0) keeps the LOWEST SP it saw;
  * the band [CSP-1500, CSP-48] is painted $A5, the workload runs, and the lowest
    overwritten byte is the stack's true low point.

Each workload nests its leaf 8 parentheses deep, so its guard SPs sit far below
the painting/scan loops' own noise (~131 B below CSP, scratchpad/stackhw_run.out)
and the low point belongs to the workload. LEAF DEPTH = min guard SP - low point.

    python3 -u scratchpad/leafdepth_probe.py
"""
import os, re, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"
NEST = 8
LEAVES = [("int",   "1"),
          ("sin",   "SIN(1)"),
          ("atn",   "ATN(.5)"),
          ("exp",   "EXP(2.5)"),
          ("log",   "LOG(3)"),
          ("sqr",   "SQR(2)"),
          ("pow",   "1.5^2.5"),
          ("val",   'VAL("1.5")'),
          ("str",   "LEN(STR$(1.5))"),
          ("hex",   "LEN(HEX$(255))"),
          ("mid",   'LEN(MID$("ABCDEF",2,3))'),
          ("instr", 'INSTR("ABC","C")'),
          ("rnd",   "RND(1)"),
          ("fre",   "FRE(0)"),
          ("fn",    "FNA(2)"),
          ("usr",   "PEEK(0)"),
          ("vpeek", "VPEEK(0)"),
          ("stick", "STICK(0)")]


def sym(name):
    for line in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        p = line.split()
        if p and p[0] == name:
            return int(p[2].rstrip("H"), 16)
    raise SystemExit(f"REFUSE: {name} not in build/basic-reloc.sym -- build first")


def prog(leaf):
    expr = "(" * NEST + leaf + "+1)" * NEST
    return ["NEW", "5 DEF FNA(X)=X*2+1",
            "10 C=PEEK(&HE050)+256*PEEK(&HE051):C%=C-65536:L%=C%-1500:H%=C%-48",
            "20 FOR A%=L% TO H%:POKE A%,&HA5:NEXT",
            f"30 B={expr}",
            "40 M%=H%+1:FOR A%=L% TO H%:IF PEEK(A%)<>&HA5 THEN IF A%<M% THEN M%=A%",
            "45 NEXT:PRINT CHR$(91);C%;M%;CHR$(93):END", "RUN"]


def main():
    g = sym("stk_guard")
    d = tempfile.mkdtemp(prefix="zb_leafdepth_")
    print(f"stk_guard @ ${g:04X}; each leaf nested {NEST} deep; bytes below CSP")
    print(f"  {'leaf':6} {'guard min SP':>13} {'low point':>10} {'LEAF DEPTH':>11}")
    for name, leaf in LEAVES:
        out = os.path.join(d, name)
        open(out, "w").close()
        # the breakpoint fires on the CALL target, so SP holds stk_guard's own
        # return address: the caller's SP is SP+2 -- the reading below uses SP as
        # is, which makes the leaf depth CONSERVATIVE by 2 B
        tcl = ("set ::mins 65536",
               f"debug set_bp 0x{g:04X} {{[pc_in_slot 0]}} "
               f"{{ if {{[reg sp] < $::mins}} {{ set ::mins [reg sp];"
               f" set f [open {{{out}}} w]; puts $f $::mins; close $f }} }}")
        raw = omsx_repl.run_cases(ZB, [("direct", prog(leaf))], batch=False,
                                  reset=("CLS",), boot=8.0, step=3.0, run_gap=90.0,
                                  capture="screen", prologue=tcl)[0]
        m = re.findall(r"\[\s*(-?\d+)\s+(-?\d+)\s*\]", raw or "")
        txt = open(out).read().strip()
        if not m or not txt:
            print(f"  {name:6} NO READING  (screen {'ok' if m else 'none'}, bp {'ok' if txt else 'none'})")
            continue
        c, low = (int(v) & 0xFFFF for v in m[-1])
        gmin = int(txt)
        print(f"  {name:6} {c - gmin:>13} {c - low:>10} {gmin - low:>11}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
