"""D-CASRELOCK diagnostic: log OUR TAPION's steady-run comparisons.

The first steady-run build refused even the first file's leader. This puts a
breakpoint on zerobas's own `tapion_sdif` (tape/tape.asm -- our code, page 0 of
the repack main ROM) and logs B (this half), E (previous half), L (the smaller)
and A (|difference|) per comparison, plus a line each time the measure phase is
reached. Addresses from a standalone `pasmo` of tape/tape.asm (same FREE_ORG).
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "probes", "lib"),
                os.path.join(HERE, "..", "probes", "basic")]
import omsx_repl  # noqa: E402
import basic_probe_kwsweep as kw  # noqa: E402
sys.path.insert(0, HERE)
import cload_ta_probe as ct  # noqa: E402


def main():
    sdif, meas = int(sys.argv[1], 16), int(sys.argv[2], 16)
    log = os.path.join(tempfile.mkdtemp(prefix="zb_tapion_"), "t.txt")
    extra = kw._rig_kwargs(("tape",))
    extra.pop("_tape_path", None)
    extra["cassette"] = ct.faithful_tape()
    extra["capture"] = "screen"
    extra["cap_gap"] = 40.0
    tcl = (f"set ::lg [open {{{log}}} w]; set ::n 0; "
           f"debug set_bp 0x{sdif:04X} {{}} {{ if {{[incr ::n] < 400}} "
           f"{{ puts $::lg \"B=[reg B] E=[reg E] L=[reg L] A=[reg A]\"; flush $::lg }} }}; "
           f"debug set_bp 0x{meas:04X} {{}} {{ puts $::lg MEAS; flush $::lg }}")
    extra["prologue"] = tuple(extra.get("prologue", ())) + (tcl,)
    omsx_repl.run_cases("C-BIOS_MSX1_EU_REPACK_DISK",
                        [("direct", ["NEW", "CLOAD"])], reset=(), **extra)
    print(open(log).read() if os.path.exists(log) else "<NO LOG>")


if __name__ == "__main__":
    main()
