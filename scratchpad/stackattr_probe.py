"""D-DIMRESERVE: WHERE do zerobas's 147 B of statement stack go? (The VG-8020 runs
the same FOR/IF/PEEK statement in 79 B -- scratchpad/stackhwref_run.out.)

zerobas's OWN machine, so any debugger use is in bounds (the clean-room line is
about the reference). Two passes over stackhw_probe.py's `idle` program:

  1. read CSP (deterministic for a fixed boot and program);
  2. arm a write watchpoint on [CSP-LO, CSP-HI]; on every hit whose SP is a NEW
     MINIMUM, record SP, PC and every word in [SP, CSP) -- the call chain at the
     deepest point the statement reaches.

Words are named against OUR symbol tables (lower-case labels only; an equate is
upper case). A page-1 word ($4000-$7FFF) is ambiguous between main page 1, the
sub-ROM and disk.rom, so each table's candidate is printed; which slot was
selected is a later refinement if the attribution needs it.

    python3 -u scratchpad/stackattr_probe.py
"""
import os, re, sys, tempfile, bisect
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"
LO, HI = 160, 110            # the watched band, bytes below CSP
BAND = 1500


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


def prog():
    return ["NEW", f"10 C=PEEK(&HE050)+256*PEEK(&HE051):C%=C-65536:L%=C%-{BAND}:H%=C%-48",
            "20 FOR A%=L% TO H%:POKE A%,&HA5:NEXT",
            "30 A=1",
            "40 M%=H%+1:FOR A%=L% TO H%:IF PEEK(A%)<>&HA5 THEN IF A%<M% THEN M%=A%",
            "45 NEXT:PRINT CHR$(91);C;C%-M%;CHR$(93):END", "RUN"]


def run(tcl=()):
    raw = omsx_repl.run_cases(ZB, [("direct", prog())], batch=False, reset=("CLS",),
                              boot=8.0, step=3.0, run_gap=120.0, capture="screen",
                              prologue=tcl)[0] or ""
    m = re.findall(r"\[\s*(\d+)\s+(-?\d+)\s*\]", raw)
    return (int(m[-1][0]), int(m[-1][1])) if m else None


def main():
    first = run()
    if not first:
        raise SystemExit("REFUSE: pass 1 gave no reading")
    csp, depth = first
    print(f"pass 1: CSP = ${csp:04X}, depth {depth} B")
    out = tempfile.mktemp(prefix="zb_stackattr_")
    open(out, "w").close()
    tcl = ("set ::mins 65536",
           f"debug set_watchpoint write_mem {{0x{csp - LO:04X} 0x{csp - HI:04X}}} {{}} "
           f"{{ set sp [reg sp]; if {{$sp < $::mins}} {{ set ::mins $sp; set b {{}};"
           f" for {{set a $sp}} {{$a < {csp}}} {{incr a}} {{ lappend b [peek $a] }};"
           f" set f [open {{{out}}} w]; puts $f \"$sp [reg pc] $b\"; close $f }} }}")
    second = run(tcl)
    txt = open(out).read().split()
    if not second or not txt:
        raise SystemExit(f"REFUSE: pass 2 reading {second}, watch {'fired' if txt else 'NEVER fired'}")
    if second[0] != csp:
        raise SystemExit(f"REFUSE: CSP moved between passes (${csp:04X} -> ${second[0]:04X})")
    sp, pc, b = int(txt[0]), int(txt[1]), [int(x) for x in txt[2:]]
    print(f"pass 2: depth {second[1]} B (pass 1 {depth}); deepest SP ${sp:04X} = CSP-{csp - sp}, "
          f"PC ${pc:04X} {name(pc)}")
    print("stack words, deepest first (offset below CSP, value, candidate):")
    for i in range(0, len(b) - 1, 2):
        v = b[i] | b[i + 1] << 8
        print(f"  CSP-{csp - (sp + i):3}  ${v:04X}  {name(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
