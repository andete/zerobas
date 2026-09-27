"""How does the REFERENCE keep GOSUB / FOR / trap frames? A RAM-only study.

Joost (2026-09-27): "About the gosub ram how does reference do it? Study it in
detail for gosub and other stack using commands to understand the mechanism."

🔴 CLEAN ROOM: this reads RAM CONTENTS and REGISTERS only -- never a ROM byte,
never a breakpoint in ROM code. The BASIC program under test marks the moment
itself with `POKE &HC000,<tag>`; an openMSX WATCHPOINT on that RAM cell (a data
write, not code) records, at the instant of the write:
    SP (a register), STKTOP ($F674, a published work-area cell) and every byte
    of [SP, STKTOP) (RAM).
Each case runs on a fresh boot. The baseline (no construct open) gives what the
interpreter itself keeps below its frames; each case's EXTRA bytes (SP_base -
SP_case) are that construct's frame(s), and the dump shows what they hold.

    python3 -u scratchpad/stackframe_probe.py [--zb]
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
MARK = "POKE &HC000,173"   # a DISTINCT value: the boot RAM test also writes $C000

CASES = [
    # 🔴 the first run fired at BOOT (SP $3000, STKTOP $FFFF on every case): the
    # RAM test writes $C000 before any program. The watch now fires only on the
    # marker VALUE, with STKTOP inside RAM and SP above $8000.
    ("base",    [f"10 {MARK}"]),
    ("gosub1",  ["10 GOSUB 30", "20 END", f"30 {MARK}:RETURN"]),
    ("gosub1b", ["10 A=1:GOSUB 30:B=2", "20 END", f"30 {MARK}:RETURN"]),
    ("gosub2",  ["10 GOSUB 30", "20 END", "30 GOSUB 40:RETURN", f"40 {MARK}:RETURN"]),
    ("for1",    [f"10 FOR I=1 TO 2:{MARK}:NEXT"]),
    ("for1int", [f"10 FOR I%=1 TO 2:{MARK}:NEXT"]),
    ("for1dbl", [f"10 FOR I#=1 TO 2:{MARK}:NEXT"]),
    ("for1stp", [f"10 FOR I=1 TO 2 STEP 3:{MARK}:NEXT"]),
    ("for2",    [f"10 FOR I=1 TO 2:FOR J=5 TO 6:{MARK}:NEXT:NEXT"]),
    ("forgos",  ["10 FOR I=1 TO 1:GOSUB 30:NEXT", "20 END", f"30 {MARK}:RETURN"]),
    ("gosfor",  ["10 GOSUB 30", "20 END", f"30 FOR I=1 TO 1:{MARK}:NEXT:RETURN"]),
    ("onerr",   ["10 ON ERROR GOTO 30:ERROR 5", "20 END", f"30 {MARK}:RESUME 20"]),
    ("trap",    ["10 ON INTERVAL=1 GOSUB 30:INTERVAL ON", "20 GOTO 20",
                 f"30 {MARK}:INTERVAL OFF:END"]),
]


def run(machine, name, lines, out):
    tcl = (f"set ::got 0",
           "debug set_watchpoint write_mem 0xC000 {} {"
           " set top0 [expr {[peek 0xF674] + 256*[peek 0xF675]}];"
           " if {!$::got && $::wp_last_value == 173 && [reg sp] > 0x8000 && $top0 < 0xF400} { set ::got 1;"
           "  set sp [reg sp];"
           "  set top [expr {[peek 0xF674] + 256*[peek 0xF675]}];"
           f"  set f [open {{{out}}} w];"
           "  puts $f \"$sp $top\";"
           "  if {$top > $sp && $top - $sp < 400} {"
           "   for {set a $sp} {$a < $top} {incr a} { puts -nonewline $f \"[peek $a] \" } };"
           "  close $f } }")
    open(out, "w").close()
    omsx_repl.run_cases(machine, [("direct", ["NEW"] + lines + ["RUN"])], batch=False,
                        reset=("CLS",), boot=8.0, step=2.5, capture="screen", prologue=tcl)
    txt = open(out).read().split("\n")
    if not txt[0].strip():
        return None
    sp, top = map(int, txt[0].split())
    data = [int(x) for x in txt[1].split()] if len(txt) > 1 and txt[1].strip() else []
    return sp, top, data


def main():
    machines = [REF] + ([ZB] if "--zb" in sys.argv else [])
    d = tempfile.mkdtemp(prefix="zb_stackframe_")
    for m in machines:
        print(f"==================== {m}")
        base = None
        for name, lines in CASES:
            r = run(m, name, lines, os.path.join(d, f"{m}_{name}.txt"))
            if r is None:
                print(f"{name:8} NO READING (the marker POKE never ran)")
                continue
            sp, top, data = r
            if base is None and name == "base":
                base = sp
            extra = (base - sp) if base is not None else 0
            print(f"{name:8} SP={sp:#06x} STKTOP={top:#06x} depth={top - sp:3d} B"
                  f"  frames(+vs base)={extra:3d} B   {' | '.join(lines)}")
            # print the dump TOP-DOWN (frames are pushed downward from STKTOP),
            # 8 bytes a row, each row labelled with its lowest address
            rows = []
            for a in range(top - 8, sp - 8, -8):
                lo = max(a, sp)
                chunk = data[lo - sp: a + 8 - sp]
                rows.append(f"   {lo:#06x}: " + " ".join(f"{b:02X}" for b in chunk))
            print("\n".join(rows[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
