#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Scope scan 2: the call-edge graph of the COMMAND.COM-load span.

§8.48 sized the executed footprint; this maps its control flow. Over the bounded
$D821 -> CALL $47B2 -> $D824 window it records every control-flow transition that
either (a) lands on a known canonical cluster entry / page-0 vector, or (b) crosses
a region boundary (TPA <-> disk-ROM <-> high-RAM). Each edge is from-addr -> to-addr
with a hit count and the order it was first seen.

That yields three things needed to sequence the build (tier2-kernel-plan.md):
  * who calls each disk-ROM cluster entry (-> order M5.6..N);
  * the precise high-RAM kernel entry addresses inside the 8 §8.48 regions
    (-> the M5.2/M5.4 relocation blueprint);
  * the first-seen order of every entry (-> which to fill first).

Black-box: it records addresses + counts only, never disassembles COMMAND.COM or the
kernel. The per-instruction monitor is installed at $D821 and removed at $D824, so it
costs nothing outside the span.

    python3 probes/disk/disk_probe_dosboot_edges.py --dos-disk /tmp/dos-oracle.dsk
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
SPAN_CALL = 0xD821
SPAN_RET = 0xD824
# canonical cluster entries + page-0 vectors (spec §5; §8.41/§8.46)
INTEREST = [0x402D, 0x41FD, 0x4558, 0x46C8, 0x47B2, 0x4919, 0x4935, 0x498C,
            0x49B4, 0x4A39, 0x4B59, 0x4BE5, 0x4C25, 0x4E4B, 0x4EDE, 0x4010,
            0x5FE5, 0x607B, 0x75A5, 0x77B8, 0x782B,
            0x000C, 0x0014, 0x001C, 0x0024, 0x0030, 0x0038]


def run(machine: str, dsk: str, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    interest_set = " ".join(f"set ::want({a}) 1;" for a in INTEREST)
    tcl = f"""set throttle off
set renderer none
set ::active 0
set ::ppc 0
set ::ppr 9
set ::seq 0
{interest_set}

proc rgn {{p}} {{
  if {{$p < 0x4000}} {{ return 0 }}
  if {{$p < 0x8000}} {{ return 1 }}
  if {{$p < 0xC000}} {{ return 2 }}
  return 3
}}

debug set_bp 0x{SPAN_CALL:04X} {{}} {{
  if {{$::active}} return
  set ::active 1
  set ::cond [debug set_condition {{1}} {{
    set p [reg PC]
    set r [rgn $p]
    if {{[info exists ::want($p)] || $r != $::ppr}} {{
      if {{$p >= 0x0100}} {{
        set k "[format %04X $::ppc]->[format %04X $p]"
        if {{[info exists ::e($k)]}} {{ incr ::e($k) }} else {{
          set ::e($k) 1
          set ::o($k) $::seq
          incr ::seq
        }}
      }}
    }}
    set ::ppc $p
    set ::ppr $r
  }}]
}}

debug set_bp 0x{SPAN_RET:04X} {{}} {{
  if {{!$::active}} return
  catch {{ debug remove_condition $::cond }}
  set f [open {{{out}}} w]
  if {{[info exists ::e]}} {{
    foreach k [lsort [array names ::e]] {{
      puts $f "$k $::e($k) $::o($k)"
    }}
  }} else {{
    puts $f "NO edges captured"
  }}
  close $f
  exit
}}

after time 180 {{
  set f [open {{{out}}} w]
  puts $f "NEVER reached span return within 180s"
  close $f
  exit
}}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def region(addr: int) -> str:
    if addr < 0x4000:
        return "TPA"
    if addr < 0x8000:
        return "diskROM"
    if addr < 0xC000:
        return "page2"
    return "hiRAM"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    edges = []  # (frm, to, count, order)
    for ln in run(args.machine, args.dos_disk, args.timeout):
        parts = ln.split()
        if len(parts) == 3 and "->" in parts[0]:
            frm, to = parts[0].split("->")
            edges.append((int(frm, 16), int(to, 16), int(parts[1]), int(parts[2])))
        else:
            print(ln)
    if not edges:
        return 0
    interest = set(INTEREST)
    # group by callee
    callees: dict[int, list[tuple[int, int, int]]] = {}
    first: dict[int, int] = {}
    for frm, to, cnt, order in edges:
        callees.setdefault(to, []).append((frm, cnt, order))
        first[to] = min(first.get(to, order), order)

    print(f"=== call-edge graph, COMMAND.COM-load span ({args.machine}) ===")
    print(f"    {len(edges)} distinct edges, {len(callees)} callees\n")

    print("  -- entries in first-seen order (callee  [region]  first@  callers) --")
    for to in sorted(callees, key=lambda a: first[a]):
        tag = " *CANON" if to in interest else ""
        callers = sorted(callees[to], key=lambda x: -x[1])
        csum = sum(c for _, c, _ in callers)
        cstr = " ".join(f"{f:04X}x{c}" for f, c, _ in callers[:6])
        more = "" if len(callers) <= 6 else f" +{len(callers)-6}"
        print(f"  {to:04X} [{region(to):7}] @{first[to]:<4} x{csum:<6}{tag}  <- {cstr}{more}")

    # distinct hiRAM entry addresses (refine the 8 §8.48 regions)
    hk = sorted(a for a in callees if a >= 0xC000)
    print(f"\n  -- {len(hk)} distinct high-RAM kernel entry addresses (M5.2 blueprint) --")
    print("    " + " ".join(f"{a:04X}" for a in hk))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
