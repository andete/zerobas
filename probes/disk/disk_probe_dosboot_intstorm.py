#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Pin the int_h<->$0038 storm mechanism: dump bytes + IFF at $4251 during the storm.

§8.74: the steady-state hang is a recursion $4251 (int_h) <-> $0038 (page-0 int
vector), SP walking down -2 per cycle, int_h_body never reached, VDP never acked.
Two candidate mechanisms with different fixes:
  (a) interrupt re-entrancy: the $0038->$4251 path leaves IFF=1, so the asserted
      VDP interrupt preempts at $4251 before `jp int_h_body` runs (fix: ack/DI
      ordering in the int path);
  (b) literal recursion: the bytes at $4251 are `call $0038` (CD 38 00) and $0038
      is `jp $4251` (fix: the vector/trampoline bytes themselves).
This breaks at $4251 with an SP-in-storm guard and dumps $0036-$0042, $424E-$425A,
IFF1, and the top-of-stack word — which settles (a) vs (b).

Black-box: a guarded register/memory snapshot. $0038 is DOS-installed; $4251 is our
own int_h. Read for diagnosis only.

    python3 probes/disk/disk_probe_dosboot_intstorm.py --dos-disk /tmp/dos.dsk
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
OURS_MACHINE = "National_CF-3300_ZEROBASDISK"


def run(machine: str, dsk: str, at: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
proc row {{a n}} {{
  set s [format "%04X:" $a]
  for {{set i 0}} {{$i < $n}} {{incr i}} {{
    append s [format " %02X" [debug read memory [expr {{($a+$i)&0xFFFF}}]]]
  }}
  return $s
}}
# wait until the storm is established (SP marched well below int_h), then snapshot
debug set_bp 0x{at:04X} {{1}} {{
  set f [open {{{out}}} w]
  catch {{
    set sp [reg SP]
    set tos [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
    puts $f [format "AT %04X  SP=%04X  top-of-stack=%04X  IFF1=%s  IM=?" [reg PC] $sp $tos [reg IFF1]]
    puts $f [row 0x0036 14]
    puts $f [row 0x424E 14]
  }} err
  if {{$err ne ""}} {{
    # IFF1 register may not exist on this build; retry without it
    catch {{
      set sp [reg SP]
      set tos [expr {{[debug read memory $sp] | ([debug read memory [expr {{($sp+1)&0xFFFF}}]] << 8)}}]
      puts $f [format "AT %04X  SP=%04X  top-of-stack=%04X  (no IFF reg: %s)" [reg PC] $sp $tos $err]
      puts $f [row 0x0036 14]
      puts $f [row 0x424E 14]
    }}
  }}
  close $f
  exit
}}
after time 35 {{ set f [open {{{out}}} w]; puts $f "NO-STORM-HIT"; close $f; exit }}
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
        if not os.path.exists(out):
            sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit("no capture")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--at", type=lambda s: int(s, 0), default=0x4251)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    print(f"=== int-storm snapshot at {args.at:#06x} on {OURS_MACHINE} ===")
    for ln in run(OURS_MACHINE, work, args.at, args.timeout):
        print(ln)
    os.unlink(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
