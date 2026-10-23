#!/usr/bin/env python3
"""wszero noclear3 after D-DEFFNVAR: does zerobas's stack reach below $F080 while the
no-CLEAR BLOAD fills $E000..$F07F? A condition on SP < $F080 logs PC / SP (the first
N hits, then every 500th) and the run's last state. Registers only; our own ROM.

    python3 -u scratchpad/nc3_sp_probe.py OUT [MACHINE]   (default zerobas diskless)
"""
import os, shutil, subprocess, sys, tempfile, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "probes", "basic"), os.path.join(REPO, "probes", "lib")]
import basic_probe_wszero as W  # noqa: E402  (the row's own tape and program)
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"


def main():
    out = sys.argv[1]
    td = tempfile.mkdtemp(prefix="nc3_")
    cas = os.path.join(td, "t.cas"); open(cas, "wb").write(W.tape(0xE000, 0xF07F))
    log = os.path.join(td, "log.txt")
    lines = [l for l in W.PROGRAM_NOCLEAR]
    L = ["set throttle off", f"set __f [open {{{log}}} w]", "set ::n 0",
         "debug set_condition {[reg SP] < 0xF080} { incr ::n; if {$::n <= 12 || $::n % 500 == 0} "
         "{ puts $::__f \"[format %.3f [machine_info time]] n=$::n pc=[format %04X [reg PC]] sp=[format %04X [reg SP]]\"; flush $::__f }; "
         "if {$::n > 20000} { puts $::__f CAP; flush $::__f; debug remove_condition cond#1 } }",
         "set ::__f $__f"]
    t = 8.0
    for ln in ["", "SCREEN 0:WIDTH 40"] + lines:
        # braces, not quotes: a `"` inside the line ended a quoted Tcl word, and the
        # first run of this probe typed only `30 END` (every line with a quote lost)
        L.append(f'after time {t:.1f} {{ type {{{ln}}} }}')
        L.append(f'after time {t + 1.5:.1f} {{ type "\\r" }}'); t += 4.0
    for k in range(1, 13):
        L.append(f"after time {t + 5 * k:.1f} {{ puts $__f \"S{5 * k} pc=[format %04X [reg PC]] sp=[format %04X [reg SP]] a8=[format %02X [debug read ioports 0xA8]] iff=[reg iff] curlin=[format %04X [peek16 0xF41C]]\"; flush $__f }}")
    L.append(f"after time {t + 61:.1f} {{ binary scan [debug read_block VRAM 0 960] H* h; puts $__f \"SCR $h\"; "
             f"puts $__f \"END pc=[format %04X [reg PC]] sp=[format %04X [reg SP]] n=$::n\"; close $__f; exit }}")
    script = os.path.join(td, "t.tcl"); open(script, "w").write("\n".join(L) + "\n")
    machine = sys.argv[2] if len(sys.argv) > 2 else "C-BIOS_MSX1_EU_REPACK_NODISK"
    p = subprocess.Popen(omsx_preflight.guarded([OMSX, "-machine", machine,
                         "-cassetteplayer", cas, "-command", "set renderer none; set sound_driver null",
                         "-script", script]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 600:
        time.sleep(0.5)
    if p.poll() is None:
        p.terminate(); p.wait()
    shutil.copy(log, out) if os.path.exists(log) else open(out, "w").write("NO LOG\n")
    shutil.rmtree(td)


if __name__ == "__main__":
    main()
