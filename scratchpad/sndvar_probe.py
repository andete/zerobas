"""D-SNDVAR: does `SOUND r,v` reach the PSG when r / v are not literals?

ex_sound kept the register number in C across the value's `eval`, and eval keeps
C only for a LITERAL factor -- a variable lookup clobbers it. Found 2026-09-27
while fixing D-STACKFLOOR (whose first cut clobbered BC even for literals, and
tests/test_sound.py caught THAT). Every SOUND row in the gates uses literals.

The PSG registers are I/O STATE, readable under the clean room on both machines:
a `POKE &HC000,173` marker's watchpoint reads R7 and R8 as the statement ends.

    python3 -u scratchpad/sndvar_probe.py
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
CASES = [("lit",  "SOUND 8,11"),                 # control: a literal always worked
         ("varv", "V=12:SOUND 8,V"),
         ("varr", "R=8:V=13:SOUND R,V"),
         ("expr", "V=7:SOUND 8,V*2"),
         ("reg7", "V=63:SOUND 7,V")]


def reading(machine, stmt, out):
    open(out, "w").close()
    tcl = ("set ::got 0",
           "debug set_watchpoint write_mem 0xC000 {} { if {!$::got && $::wp_last_value == 173"
           " && [reg sp] > 0x8000} { set ::got 1;"
           f" set f [open {{{out}}} w]; puts $f \"[debug read {{PSG regs}} 7] "
           "[debug read {PSG regs} 8]\"; close $f } }")
    omsx_repl.run_cases(machine, [("direct", ["NEW", f"10 {stmt}:POKE &HC000,173", "RUN"])],
                        batch=False, reset=("CLS",), boot=8.0, step=2.5, capture="screen",
                        prologue=tcl)
    return open(out).read().strip() or "NO READING"


def main():
    d = tempfile.mkdtemp(prefix="zb_sndvar_")
    got = {m: [reading(m, s, os.path.join(d, f"{m}_{k}")) for k, s in CASES] for m in (REF, ZB)}
    print(f"{'row':5} {'statement':22} {'VG-8020 R7 R8':>14} {'zerobas R7 R8':>14}")
    agree = 0
    for i, (k, s) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        agree += r == z
        print(f"{'  ' if r == z else '✗ '}{k:5} {s:22} {r:>14} {z:>14}")
    print(f"AGREE {agree}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
