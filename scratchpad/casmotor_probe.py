#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM order step (1), the design risk: how does the VG-8020 PACE a cassette
ASCII LOAD with ONE buffer?

casbuf_probe.out: the reference does all tape I/O through the channel's own
256 B buffer; zerobas keeps a page-aligned DOUBLE buffer (CAL_BUF / CAL_BUF2)
because its tokeniser could not keep up with the tape between blocks. One
buffer works only if the tape does not stream past while a block's lines are
crunched -- i.e. the motor stops between blocks. The motor line is PPI port C
($AA) bit 4 (CASON: 0 = motor ON, per the published PPI map): readable, an I/O
port, never a ROM byte.

METHOD: a multi-block ASCII tape (40 lines, ~5 blocks of 256 B, built by
cas_encode); from boot, $AA sampled every 5 ms of emulated time and every
motor ON / OFF transition logged with its time; LOAD"CAS:X" typed. Both
machines.

Prediction: on the VG-8020 the motor goes OFF between blocks (about one ON
period per block); on zerobas it stays ON for the whole load.
"""
import os, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
LINES = [f"{10 * (i + 1)} REM LINE NUMBER {i:02d} PADDING PADDING PADDING" for i in range(40)]


def main():
    from basic_probe_cas_ascii import build_ascii_cas
    tmp = tempfile.mkdtemp(prefix="casmotor_")
    cas = os.path.join(tmp, "m.cas")
    data = build_ascii_cas("X", LINES)
    open(cas, "wb").write(data)
    print(f"tape: {len(LINES)} lines, {sum(len(l) + 2 for l in LINES) + 1} B of text, "
          f"{(sum(len(l) + 2 for l in LINES) + 256) // 256} data block(s)")
    for m in MACHINES:
        fd, log = tempfile.mkstemp(suffix=".txt", prefix="casmotor_")
        os.close(fd)
        os.unlink(log)
        pro = (f"set ::__mf {{{log}}}", "set ::__last -1",
               "proc __m {} { set v [expr {([debug read ioports 0xAA] >> 4) & 1}]; "
               "if {$v != $::__last} { set ::__last $v; set f [open $::__mf a]; "
               "puts $f \"[machine_info time] $v\"; close $f }; after time 0.005 __m }",
               "after time 7.5 __m",
               f"cassetteplayer insert {{{cas}}}")
        raw = omsx_repl.run_cases(m, [("direct", ["NEW", 'LOAD"CAS:X"', "LIST 400"])],
                                  batch=False, reset=("", "SCREEN 0"), run_gap=90.0,
                                  prologue=pro)[0]
        ev = [l.split() for l in open(log)] if os.path.exists(log) else []
        on = [float(t) for t, v in ev if v == "0"]
        off = [float(t) for t, v in ev if v == "1"]
        print(f"=== {m}: {len(on)} motor-ON transition(s), {len(off)} OFF")
        for t, v in ev[:40]:
            print(f"   t={float(t):8.3f}  {'ON ' if v == '0' else 'off'}")
        tail = [r for r in (raw or "").replace("\n", "").split("  ") if "400" in r][:1]
        print(f"   LIST 400 after the load: {tail[0].strip() if tail else '(not found)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
