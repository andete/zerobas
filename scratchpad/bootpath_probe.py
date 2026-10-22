#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKRUN triage: WHEN do the boot code's entry ($C01E, the disk's own RAM copy)
and the published BASIC entry $4022 run, and in what state? One image, one machine.

Black box: a breakpoint on an ADDRESS logs the time, the CPU registers, the primary
slot register ($A8), the two words at SP (RAM) and the work-area cell BASENT_REQ's
address ($F33D). It never steps, never reads a ROM byte, never follows a target; the
same two published addresses are watched on every machine. The image is copied to
/tmp; the collection's location comes from DISKCORPUS_DIR and is never written here.

    DISKCORPUS_DIR=... python3 -u scratchpad/bootpath_probe.py IMAGE MACHINE [SECONDS] [--ext E]
"""
import argparse, os, shutil, subprocess, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402  (no settings saved, autorun un-armed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("machine")
    ap.add_argument("seconds", nargs="?", type=float, default=30.0)
    ap.add_argument("--ext", action="append", default=[])
    ap.add_argument("--bp", action="append", default=[],
                    help="another PUBLISHED address to log (hex, e.g. F37D: the BDOS door)")
    a = ap.parse_args()
    td = tempfile.mkdtemp(prefix="bootpath_")
    try:
        src = os.path.join(os.environ["DISKCORPUS_DIR"], a.image)
        ext = os.path.splitext(src)[1].lower()
        dsk = os.path.join(td, "d" + (".xsa" if ext == ".xsa" else ".dsk"))
        shutil.copy(src, dsk)
        out = os.path.join(td, "log.txt")
        extra = "".join(f"debug set_bp 0x{b} {{}} {{ __hit {b} }}\n" for b in a.bp)
        tcl = f"""set throttle off
set __n 0
proc __hit {{tag}} {{
  global __n
  incr __n
  if {{$__n > 40}} return
  set f [open {{{out}}} a]
  set sp [reg sp]
  binary scan [debug read_block memory $sp 4] H* stk
  binary scan [debug read_block memory 0xF33D 2] H* req
  set a8 [debug read ioports 0xA8]
  puts $f [format "%-5s t=%7.3f a8=%02X af=%04X bc=%04X de=%04X hl=%04X sp=%04X stk=%s req=%s" \\
     $tag [machine_info time] $a8 [reg af] [reg bc] [reg de] [reg hl] $sp $stk $req]
  close $f
}}
debug set_bp 0xC01E {{}} {{ __hit C01E }}
debug set_bp 0x4022 {{}} {{ __hit 4022 }}
{extra}after time {a.seconds} {{ exit }}
"""
        open(os.path.join(td, "s.tcl"), "w").write(tcl)
        cmd = ["/opt/homebrew/bin/openmsx", "-machine", a.machine]
        for e in a.ext:
            cmd += ["-ext", e]
        cmd += ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                "-script", os.path.join(td, "s.tcl")]
        subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=90 + 3 * a.seconds)
        print(f"# {a.image} on {a.machine} {' '.join(a.ext)}")
        print(open(out).read() if os.path.exists(out) else "<NO HITS>", end="")
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
