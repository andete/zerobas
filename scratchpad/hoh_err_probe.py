#!/usr/bin/env python3
"""Head over Heels after D-BAREEXTRA: `Bad file mode in 50` on zerobas -- who raises it?

The title loads as tapecorpus_run.py loads it (openMSX autorun); a breakpoint on our
own raise_error, armed only when A = 61, logs the time, PC / SP / A8, CURLIN and the
top 24 stack words -- our return addresses and the caller's RAM address, nothing of
the game decoded. Capped at 4 hits. From the first USR entry on, every RAM -> ROM
transition is logged as two PC values (`T from= to=`), 20 at most -- addresses only.

    TAPECORPUS_DIR=... python3 -u scratchpad/hoh_err_probe.py OUT [TITLE]
"""
import os, re, shutil, subprocess, sys, tempfile, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "scratchpad"), os.path.join(REPO, "probes", "lib")]
import tapecorpus_run as T  # noqa: E402
import omsx_preflight  # noqa: E402


def sym(name):
    for l in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        m = re.match(rf"{name}\s+EQU\s+0?([0-9A-F]+)H", l)
        if m:
            return int(m.group(1), 16)
    raise SystemExit(f"no {name}")


def main():
    out = os.path.abspath(sys.argv[1]); title = sys.argv[2] if len(sys.argv) > 2 else "Head over Heels"
    td = tempfile.mkdtemp(prefix="hoh_")
    zpath = os.path.join(os.environ["TAPECORPUS_DIR"], title + ".zip")
    cas = T.first_cas(zpath, td) if hasattr(T, "first_cas") else None
    if not cas:
        import zipfile
        with zipfile.ZipFile(zpath) as z:
            n = sorted(x for x in z.namelist() if x.lower().endswith(".cas"))[0]
            cas = os.path.join(td, "t.cas"); open(cas, "wb").write(z.read(n))
    log = os.path.join(td, "log.txt")
    re_ = sym("raise_error")
    L = ["after time 0.3 {", "  trace remove execution cassetteplayer leave ::__zb_unarm",
         "  set autoruncassettes on", f"  cassetteplayer insert {{{cas}}}", "}",
         "set throttle off", f"set ::f [open {{{log}}} w]", "set ::n 0",
         f"debug set_bp 0x{re_:04X} {{[reg A] == 61}} {{ if {{[incr ::n] > 4}} return; "
         "binary scan [debug read_block memory [reg SP] 48] H* s; "
         "puts $::f \"[format %.3f [machine_info time]] A=[reg A] pc=[format %04X [reg PC]] sp=[format %04X [reg SP]] "
         "a8=[format %02X [debug read ioports 0xA8]] curlin=[format %04X [peek16 0xF41C]] stk=$s\"; flush $::f }",
         # the USR entry's `ret` (usr_ret - 1): from there, log each RAM -> ROM
         # transition (the previous PC in RAM, the ROM PC entered), 20 at most
         f"set ::lp 0; set ::t 0",
         f"debug set_bp 0x{sym('usr_ret') - 1:04X} {{}} {{ if {{$::t == 0}} {{ set ::t 1; "
         "debug set_condition {1} { set pc [reg PC]; "
         "if {$::lp >= 0x8000 && $pc < 0x8000 && $::t <= 20} { "
         "puts $::f \"T [format %.3f [machine_info time]] from=[format %04X $::lp] to=[format %04X $pc] sp=[format %04X [reg SP]] a8=[format %02X [debug read ioports 0xA8]]\"; flush $::f; incr ::t }; "
         "set ::lp $pc } } }",
         # and a ring of the last 300 PCs, dumped at the first ERR 61 (PC values only)
         "set ::ring {}",
         f"debug set_bp 0x{sym('usr_ret') - 1:04X} {{}} {{ debug set_condition {{1}} {{ lappend ::ring [reg PC]; if {{[llength $::ring] > 300}} {{ set ::ring [lrange $::ring end-299 end] }} }} }}",
         f"debug set_bp 0x{re_:04X} {{[reg A] == 61}} {{ puts $::f \"RING [join $::ring ,]\"; flush $::f }}",
         "after time 120 { close $::f; exit }"]
    tcl = os.path.join(td, "s.tcl"); open(tcl, "w").write("\n".join(L) + "\n")
    p = subprocess.Popen(omsx_preflight.guarded([T.OMSX, "-machine", T.ZB, "-command",
                         "set renderer none; set sound_driver null", "-script", tcl]),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 400:
        time.sleep(0.5)
    if p.poll() is None:
        p.terminate(); p.wait()
    shutil.copy(log, out) if os.path.exists(log) else open(out, "w").write("NO LOG\n")
    shutil.rmtree(td)


if __name__ == "__main__":
    main()
