"""TIER 4 goal (c), SAME ECONOMY -- the op list WIDENED past fremem_probe.py.

fremem_probe.py found every fresh-boot economy delta equal to the VG-8020's to
the byte (CLEAR, DIM, strings, scalars, program lines), and filed "widen the op
list (control flow, graphics, file I/O)". Control flow costs memory only WHILE
a program runs, so each row here measures INSIDE one program: every variable
is created first, `A=FRE(0)` is read, the operation is entered, `B=FRE(0)` is
read, and `A-B` is printed -- the program text and the variables cancel, and
what is left is the operation's own footprint.

Rows: one FOR frame; two nested FOR frames; one GOSUB; two nested GOSUBs;
inside a DEF FN call; inside an ON ERROR handler; DIM A$(10); DIM A#(10).

Diskless pair, fresh boot per row. Clean room: screen output only.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
PRE = "A=0:B=0:I=0:J=0:X=0"
OUT = 'PRINT"[";A-B;"]"'
CASES = [
    ("for1", [f"10 {PRE}:A=FRE(0)", "20 FOR I=1 TO 2:B=FRE(0)", f"30 {OUT}:END"]),
    ("for2", [f"10 {PRE}:A=FRE(0)", "20 FOR I=1 TO 2:FOR J=1 TO 2:B=FRE(0)", f"30 {OUT}:END"]),
    ("gosub1", [f"10 {PRE}:A=FRE(0):GOSUB 100", f"20 {OUT}:END", "100 B=FRE(0):RETURN"]),
    ("gosub2", [f"10 {PRE}:A=FRE(0):GOSUB 100", f"20 {OUT}:END", "100 GOSUB 200:RETURN",
                "200 B=FRE(0):RETURN"]),
    ("deffn", [f"10 {PRE}:DEF FNF(X)=FRE(0)", "20 A=FRE(0):B=FNF(1)", f"30 {OUT}:END"]),
    ("onerr", [f"10 {PRE}:ON ERROR GOTO 100:A=FRE(0):ERROR 250", "20 END",
               f"100 B=FRE(0):{OUT}:END"]),
    ("dimstr", [f"10 {PRE}:A=FRE(0):DIM S$(10):B=FRE(0)", f"20 {OUT}:END"]),
    ("dimdbl", [f"10 {PRE}:A=FRE(0):DIM D#(10):B=FRE(0)", f"20 {OUT}:END"]),
]


def val(raw):
    m = re.findall(r"\[\s*(-?\d+)\s*\]", raw or "")
    return int(m[-1]) if m else None


def main():
    specs = [("direct", ["NEW"] + lines + ["RUN"]) for _k, lines in CASES]
    res = {m: omsx_repl.run_cases(m, specs, batch=False, reset=("CLS",), boot=8.0,
                                  capture="screen") for m in (REF, ZB)}
    bad = 0
    print(f"{'op':8} {'ref A-B':>8} {'zb A-B':>8}")
    for i, (k, _l) in enumerate(CASES):
        r, z = val(res[REF][i]), val(res[ZB][i])
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:8} {str(r):>8} {str(z):>8}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
