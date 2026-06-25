#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Dead-zone tripwire: catch the FIRST control-flow derail in the DOS boot.

The Tier-2 DOS boot derails before the A> prompt: control leaves legitimate
code, ends up sliding through memory as NOP-padding, and the interrupt "storm"
follows downstream. The storm is a symptom; the root is the *first wrong
control transfer*. This instrument traps that moment directly.

INVARIANT (verified): the disk-ROM real code contains ZERO intentionally
executed `nop` mnemonics (35 `ds ...,$00` pads are absorption/alignment fill
that legitimate flow always jumps OVER, never lands on; and `$00` operand bytes
are never PC targets). Therefore:

    PC in the disk-ROM page  AND  opcode at PC == $00  <=>  control has derailed

We catch that with a single openMSX watchpoint, NOT 121 per-byte breakpoints:

    debug watchpoint create -type read_mem -address {lo hi} \
        -condition {[reg PC]>=lo && [reg PC]<=hi && [debug read memory [reg PC]]==0}

`read_mem` fires on the Z80 opcode FETCH (empirically confirmed), the address
range is checked natively in C++ (cheap while executing outside the band), and
the condition tests the byte at PC (the opcode) -- so in-band *data* reads of a
$00 byte do NOT false-trip. `-once` removes it after the first hit.

On trip we dump the trip PC, all registers, the stack top (return-address
backtrace), and a disassembly window around PC. That alone pinpoints the
derail far earlier and more precisely than the linear-run heuristic.

To name the FAULTY TRANSFER (the jp/call/ret that branched into the dead zone),
pass `--arm <addr>`: a per-instruction ring buffer of recent PCs is enabled only
AFTER execution first reaches that landmark, so tracing stays fast. The last
real (non-pad) PC in the ring before the slide is the culprit.

Black-box: PC/opcode/stack sampling of a booting proprietary DOS. No
disassembly of MSXDOS.SYS/COMMAND.COM; our own ROM is our own work.

    python3 probes/disk/disk_probe_dosboot_tripwire.py
    python3 probes/disk/disk_probe_dosboot_tripwire.py --bands 4000-7FFF,D000-DFFF
    python3 probes/disk/disk_probe_dosboot_tripwire.py --arm 0xD88A --history 48
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
OURS_MACHINE = "National_CF-3300_ZEROBASDISK"


def parse_bands(spec: str) -> list[tuple[int, int]]:
    bands = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        lo, hi = part.split("-")
        bands.append((int(lo, 16), int(hi, 16)))
    return bands


def build_tcl(out: str, bands: list[tuple[int, int]], arm: int | None,
              history: int, timeout: float) -> str:
    # The trip handler: dump everything we need to name the derail, then exit.
    wp_lines = []
    for lo, hi in bands:
        cond = (f"[reg PC] >= 0x{lo:04X} && [reg PC] <= 0x{hi:04X} && "
                f"[debug read memory [reg PC]] == 0")
        wp_lines.append(
            f"debug watchpoint create -type read_mem "
            f"-address {{0x{lo:04X} 0x{hi:04X}}} -once "
            f"-condition {{{cond}}} -command {{trip}}")
    wp_block = "\n".join(wp_lines)

    arm_block = ""
    if arm is not None:
        arm_block = f"""
set ::ring {{}}
debug breakpoint create -address 0x{arm:04X} -once -command {{
  debug condition create -command {{
    lappend ::ring [format "%04X %02X" [reg PC] [debug read memory [reg PC]]]
    if {{[llength $::ring] > {history}}} {{
      set ::ring [lrange $::ring end-{history - 1} end]
    }}
  }}
}}
"""

    return f"""set throttle off
set renderer none

proc trip {{}} {{
  catch {{
    set pc [reg PC]
    set f [open {{{out}}} w]
    puts $f "TRIP"
    puts $f [format "REGS PC=%04X SP=%04X AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X" \\
              [reg PC] [reg SP] [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY]]
    set sp [reg SP]
    set sw {{}}
    for {{set i 0}} {{$i < 12}} {{incr i}} {{
      set a [expr {{($sp + 2*$i) & 0xFFFF}}]
      set w [expr {{[debug read memory $a] | ([debug read memory [expr {{($a+1)&0xFFFF}}]] << 8)}}]
      lappend sw [format "%04X" $w]
    }}
    puts $f "STACK [join $sw {{ }}]"
    set a [expr {{($pc - 16) & 0xFFFF}}]
    for {{set i 0}} {{$i < 18}} {{incr i}} {{
      set d [debug disasm $a]
      set mn [string trim [lindex $d 0]]
      set hb [lindex $d 1]
      set len [expr {{[string length $hb] / 2}}]
      if {{$len < 1}} {{ set len 1 }}
      set mark [expr {{$a == $pc ? {{>>}} : {{  }}}}]
      puts $f [format "%s %04X  %-8s %s" $mark $a $hb $mn]
      set a [expr {{($a + $len) & 0xFFFF}}]
      if {{$a > [expr {{($pc + 6) & 0xFFFF}}]}} break
    }}
    if {{[info exists ::ring]}} {{
      puts $f "RING"
      puts $f [join $::ring "\\n"]
    }}
    close $f
  }} err
  if {{$err ne ""}} {{ set g [open {{{out}}} w]; puts $g "TCL-ERROR: $err"; close $g }}
  exit
}}
{arm_block}
{wp_block}

after time {timeout:.1f} {{
  set f [open {{{out}}} w]; puts $f "NO-TRIP"; close $f; exit
}}
"""


def run(machine: str, dsk: str, tcl: str, timeout: float) -> list[str]:
    out_path = tcl_path = None
    for line in tcl.splitlines():
        if "open {" in line and "} w]" in line:
            out_path = line.split("open {", 1)[1].split("}", 1)[0]
            break
    tcl_path = tempfile.mktemp(suffix=".tcl")
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout + 30
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    lines = []
    if out_path and os.path.exists(out_path):
        lines = open(out_path).read().splitlines()
        os.unlink(out_path)
    os.unlink(tcl_path)
    return lines


def annotate_ring(ring: list[str]) -> str | None:
    """Find the faulty transfer: scanning from the trip backwards, the slide is a
    forward walk of in-band $00 opcodes; the last entry before it whose opcode is
    non-$00 (or that jumps) is the transfer that derailed control."""
    parsed = []
    for r in ring:
        try:
            a, op = r.split()
            parsed.append((int(a, 16), int(op, 16)))
        except ValueError:
            continue
    if not parsed:
        return None
    # walk back over the trailing NOP slide
    i = len(parsed) - 1
    while i > 0 and parsed[i][1] == 0:
        i -= 1
    # parsed[i] is the last non-NOP; parsed[i+1] (if any) is where the pad began
    src_a, src_op = parsed[i]
    landed = parsed[i + 1][0] if i + 1 < len(parsed) else None
    if landed is None:
        return f"transfer source ${src_a:04X} (op ${src_op:02X}) -- ran straight into pad"
    return (f"FAULTY TRANSFER: ${src_a:04X} (op ${src_op:02X}) "
            f"--> landed ${landed:04X} (dead pad)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", default="/tmp/dos.dsk")
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--machine")
    ap.add_argument("--bands", default="4000-7FFF",
                    help="comma list of hex lo-hi NOP-trap bands (default disk-ROM page)")
    ap.add_argument("--arm", help="hex landmark; enable the PC ring buffer only after it is reached")
    ap.add_argument("--history", type=int, default=48, help="ring buffer depth for --arm")
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()

    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    bands = parse_bands(args.bands)
    arm = int(args.arm, 16) if args.arm else None

    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    tcl = build_tcl(tempfile.mktemp(suffix=".cap"), bands, arm, args.history, args.timeout)
    lines = run(machine, work, tcl, args.timeout)
    os.unlink(work)

    band_str = ",".join(f"{lo:04X}-{hi:04X}" for lo, hi in bands)
    print(f"=== dead-zone tripwire on {machine}  (bands {band_str}"
          + (f", armed @ {arm:04X}" if arm is not None else "") + ") ===")

    if not lines:
        print("  no capture (launch failure?)")
        return 1
    if lines[0] == "NO-TRIP":
        print("  VERDICT: NO-TRIP -- no NOP executed in the trap bands within the window.")
        print("  (boot may have stalled elsewhere, or reached A>. Cross-check with the triage oracle.)")
        return 0
    if lines[0].startswith("TCL-ERROR"):
        print(f"  {lines[0]}")
        return 1

    regs = next((l for l in lines if l.startswith("REGS ")), "")
    stack = next((l for l in lines if l.startswith("STACK ")), "")
    win = []
    ring = []
    mode = None
    for l in lines:
        if l in ("TRIP",) or l.startswith(("REGS ", "STACK ")):
            mode = None
            continue
        if l == "RING":
            mode = "ring"
            continue
        if mode == "ring":
            if l:
                ring.append(l)
        elif l and (l.startswith(">>") or l.startswith("  ")):
            win.append(l)

    trip_pc = regs.split("PC=")[1][:4] if "PC=" in regs else "????"
    print(f"  VERDICT: DERAIL -- NOP ($00) executed at ${trip_pc} (control left legitimate code)")
    print(f"  {regs[5:]}")
    if stack:
        print(f"  stack@SP: {stack[6:]}")
    if win:
        print("  disasm window (>> = trip PC):")
        for w in win:
            print(f"    {w}")
    if ring:
        note = annotate_ring(ring)
        if note:
            print(f"  {note}")
        print(f"  ring (last {len(ring)}, oldest first):")
        print("    " + "  ".join(r.split()[0] for r in ring))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
