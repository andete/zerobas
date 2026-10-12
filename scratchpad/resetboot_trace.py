#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RESETBOOT, step 2: WHERE does zerobas's INIT stop after a reset?
(resetboot_probe.out: after `reset` the machine stays on C-BIOS's info screen,
"Init ROM in slot: 0", the PC circling C-BIOS's chput_esc_m / search_roms_init.)

Breakpoints on zerobas's OWN INIT milestones (build/basic-reloc.sym; our ROM)
log their first hit -- once on the cold boot, once after `reset` -- with a few
RAM cells C-BIOS's CHPUT scroll reads (CSRY, CSRX, CRTCNT, LINLEN, SCRMOD).
Clean room: our own symbols, registers and RAM; no reference here at all.
"""
import os, re, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

M = os.environ.get("RESETBOOT_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
NAMES = ["init", "clear_vars", "clear_usrtab", "init_filechan", "new_prog",
         "init_ext_roms", "ctl_reset", "show_title", "repl",
         # round 2: clear_vars' own steps (round 1 stopped after ctl_reset)
         "trap_init", "heap_reset", "fld_init", "raise_error", "print_string"]


def syms():
    out = {}
    for line in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        m = re.match(r"(\w+)\s+EQU\s+0*([0-9A-F]+)H", line)
        if m and m.group(1) in NAMES:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def main():
    s = syms()
    out = probe_tmp.tmp("resetboot_trace.txt")
    tcl = probe_tmp.tmp("resetboot_trace.tcl")
    if os.path.exists(out):
        os.unlink(out)
    bps = "\n".join(
        f'debug set_bp 0x{a:04X} {{1}} {{ __hit {n} }}' for n, a in s.items())
    open(tcl, "w").write(r"""
set throttle off
set ::f [open {OUT} w]
set ::phase cold
array set ::seen {}
proc __cells {} {
  return "CSRY=[debug read memory 0xF3DC] CSRX=[debug read memory 0xF3DD] CRTCNT=[debug read memory 0xF3B1] LINLEN=[debug read memory 0xF3B0] SCRMOD=[debug read memory 0xFCAF]"
}
proc __hit {n} {
  set k "$::phase,$n"
  if {[info exists ::seen($k)]} return
  set ::seen($k) 1
  puts $::f "$::phase [format %8.3f [machine_info time]] $n  [__cells]"
}
BPS
after time 14 {
  set ::phase reset
  puts $::f "--- reset at [format %8.3f [machine_info time]]  [__cells]"
  reset
  foreach dt {3 4 5 6} { after time $dt { puts $::f "    pc [format %8.3f [machine_info time]] [format %04X [reg pc]] sp=[format %04X [reg sp]]" } }
  after time 14 {
    puts $::f "--- end [format %8.3f [machine_info time]] pc=[format %04X [reg pc]]  [__cells]"
    close $::f; exit
  }
}
""".replace("{OUT}", "{" + out + "}").replace("BPS", bps))
    proc = subprocess.Popen(omsx_preflight.guarded(
                                [OMSX, "-machine", M, "-command",
                                 "set renderer none; set sound_driver null", "-script", tcl]),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 180
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        print("TIMEOUT")
        return 2
    print(open(out).read().rstrip() if os.path.exists(out) else "NO OUTPUT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
