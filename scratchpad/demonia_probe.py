#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-INITIO follow-up: Demonia (tape) resets on zerobas once cbios-repack/initio.patch
moves C-BIOS's bytes at $10ED..$1107 (INITIO + the dead INIFNK stub) -- even a variant
that changes NO behaviour, only the layout (demonia_C.out). Who executes code there?
A PC condition on that range (slot 0, page 0) logs PC / SP / the stack's top words, and a
breakpoint on $0000 after 10 s logs the reboot. Black box: registers and RAM only; the
tape is run, never decoded.

    TAPECORPUS_DIR=... python3 -u scratchpad/demonia_probe.py [MACHINE]
"""
import os, subprocess, sys, tempfile, glob, shutil
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import tapecorpus_run as T                          # noqa: E402
import omsx_preflight                               # noqa: E402

machine = sys.argv[1] if len(sys.argv) > 1 else "C-BIOS_MSX1_EU_REPACK_NODISK"
zp = [p for p in glob.glob(os.path.join(os.environ["TAPECORPUS_DIR"], "*")) if "Demonia" in p][0]
td = tempfile.mkdtemp(prefix="demonia_")
cas = T.unpack(zp, td) if zp.lower().endswith(".zip") else zp
log = os.path.join(td, "w.txt")
tcl = ["after time 0.3 {", "  trace remove execution cassetteplayer leave ::__zb_unarm",
       "  set autoruncassettes on", f"  cassetteplayer insert {{{cas}}}", omsx_preflight.AUTORUN_FIX, "}",
       "set throttle off", f"set ::wf [open {{{log}}} w]", "set ::n 0",
       "debug set_bp 0x003B {[machine_info time] > 10.0 && $::n < 400} {incr ::n; binary scan [debug read_block memory [reg sp] 2] H* st; "
       "puts $::wf \"[format %.4f [machine_info time]] INITIO sp=[format %04X [reg sp]] ret=$st\"; flush $::wf}",
       "after time 279.0 {binary scan [debug read_block memory 0xF380 0xC80] H* d; puts $::wf \"DUMP279 $d\"; flush $::wf}",
       "after time 200.0 {binary scan [debug read_block memory 0xF380 0xC80] H* d; puts $::wf \"DUMP200 $d\"; flush $::wf}",
       "debug set_bp 0x0000 {[machine_info time] > 10.0} {binary scan [debug read_block memory [reg sp] 8] H* st; "
       "puts $::wf \"[format %.4f [machine_info time]] RST0 sp=[format %04X [reg sp]] st=$st\"; flush $::wf}",
       "after time 300 { exit }"]
open(os.path.join(td, "s.tcl"), "w").write("\n".join(tcl) + "\n")
subprocess.run(omsx_preflight.guarded([T.OMSX, "-machine", machine, "-command",
               "set renderer none; set sound_driver null", "-script", os.path.join(td, "s.tcl")]),
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
print(open(log).read() if os.path.exists(log) else "<no log>")
shutil.rmtree(td, ignore_errors=True)
