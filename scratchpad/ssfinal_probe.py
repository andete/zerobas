#!/usr/bin/env python3
"""ss-final.dsk (D-DISKRUN lead, 2026-10-23): what memory picture does a program see
under MSX-DOS on the CF-3300 and on zerobas?

The CF-3300 (and zerobas until re-run 4) stop at the program's own `FATAL ERROR
Not enough free memory found (at least 32kB)`; HEAD's zerobas passes the check.
Black box: the image is COPIED to /tmp and booted; at each time the probe reads
the CPU's PC and SP, the primary-slot register, and RAM / work-area cells only:
  $0005..7    the BDOS jump (its operand = the top of the TPA), read ONLY while
              page 0 is the RAM slot RAMAD0 names -- never a ROM byte
  RAMAD0..3   $F341..$F344, the RAM slot of each page (disk work area)
  EXPTBL      $FCC1..$FCC4,  SLTTBL $FCC5..$FCC8
  HIMEM       $FC4A
No ROM byte is read; the program is RUN, never decoded.

    DISKCORPUS_DIR=... python3 -u scratchpad/ssfinal_probe.py [IMAGE] [MACHINE ...]
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
TIMES = [3, 4, 5, 6, 7, 8, 10, 12, 16, 20]


def run(image, machine):
    td = tempfile.mkdtemp(prefix="ssfinal_")
    dsk, out, script = (os.path.join(td, n) for n in ("d.dsk", "o.txt", "t.tcl"))
    shutil.copy(image, dsk)
    L = ["set throttle off", f"set __f [open {{{out}}} w]",
         "proc hx {a n} { binary scan [debug read_block memory $a $n] H* h; return $h }",
         # $0005 only while page 0 is the RAM slot RAMAD0 names (primary from the
         # $A8 register, secondary from SLTTBL, the work area's copy): with anything
         # else in page 0 the read would be ROM, which this project never reads.
         # RAMAD0 = $00 (not set yet: slot 0 is the BIOS ROM) or not a slot id
         # (bits 4-6 set, the $FF of an unwritten cell) also refuses.
         "proc p0ram {} { set a8 [debug read ioports 0xA8]; set r [peek 0xF341];"
         " if {$r == 0 || ($r & 0x70)} { return 0 };"
         " if {($a8 & 3) != ($r & 3)} { return 0 }; if {!($r & 0x80)} { return 1 };"
         " set s [peek [expr {0xFCC5 + ($r & 3)}]]; return [expr {($s & 3) == (($r >> 2) & 3)}] }",
         "proc st {tag} { global __f; set b [expr {[p0ram] ? [hx 0x0005 3] : {not-RAM}}];"
         " puts $__f \"$tag pc=[format %04X [reg PC]] sp=[format %04X [reg SP]]"
         " a8=[format %02X [debug read ioports 0xA8]] p0-bdos=$b ramad=[hx 0xF341 4]"
         " exptbl=[hx 0xFCC1 4] slttbl=[hx 0xFCC5 4] himem=[hx 0xFC4A 2]\"; flush $__f }"]
    L += [f"after time {t} {{ st T{t} }}" for t in TIMES]
    L.append(f"after time {TIMES[-1] + 0.5} {{ close $__f; exit }}")
    open(script, "w").write("\n".join(L) + "\n")
    p = subprocess.Popen(omsx_preflight.guarded([OMSX, "-machine", machine, "-diska", dsk, "-command",
                         "set renderer none; set sound_driver null", "-script", script]),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t = time.time()
    while p.poll() is None and time.time() - t < 120:
        time.sleep(0.2)
    if p.poll() is None:
        p.terminate()
        p.wait()
    rows = open(out).read().splitlines() if os.path.exists(out) else ["NO READING"]
    shutil.rmtree(td)
    return rows


def main():
    image = sys.argv[1] if len(sys.argv) > 1 else "ss-final.dsk"
    machines = sys.argv[2:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
    src = os.path.join(os.environ["DISKCORPUS_DIR"], image)
    for m in machines:
        print(f"=== {m}  {image}")
        for r in run(src, m):
            print("  " + r)


if __name__ == "__main__":
    main()
