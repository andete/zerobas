#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Layer the DOS work area $F1C9-$F37F: what C-BIOS/BASIC sets vs what our disk ROM adds.

The phase-1 work-area clear (tier2-phase1-spec.md) regresses BASIC FILES on the
C-BIOS_MSX1_EU_BASIC_DISK target. This probe characterises WHY by snapshotting
$F1C9-$F37F at two layers:
  * at our disk-ROM init entry ($4034) — what C-BIOS/BASIC set BEFORE our ROM ran;
  * at the BASIC prompt — what is live when FILES reads the work area.
It prints the C-BIOS-owned (non-FF at init-entry) runs and the cells that survive to
the BASIC prompt. Finding (2026-06-26): C-BIOS RET-fills ($C9) the disk-hook region
($F327/$F338/$F348/$F368...) so undefined hooks are safe no-ops; our disk ROM overlays
only the cells it owns; a blanket zero turns the surviving C9 stubs into 00 (NOP ->
garbage) -> FILES crashes. $F338 is C9 on C-BIOS (BASIC) but must be 00 for DOS -> the
construction is necessarily DOS-only.

Black-box: snapshots memory only. Uses a /tmp copy of the BASIC test disk.

    python3 probes/disk/disk_probe_dosboot_walayer.py
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
if not os.path.exists(OMSX):
    OMSX = "/Applications/openMSX.app/Contents/MacOS/openmsx"
LO, HI = 0xF1C9, 0xF37F


def snap(machine: str, dsk: str, at_init: bool, init_pc: int, prompt_t: float,
         timeout: float) -> str:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    trig = (f"debug set_bp {init_pc:#06x} {{}} {{ dump; exit }}" if at_init
            else f"after time {prompt_t} {{ dump; exit }}")
    tcl = f"""set throttle off
set renderer none
proc dump {{}} {{
  set s ""
  for {{set a {LO}}} {{$a <= {HI}}} {{incr a}} {{ append s [format "%02X" [debug read memory $a]] }}
  set f [open {{{out}}} w]; puts $f $s; close $f
}}
{trig}
after time {prompt_t + 16} {{ exit }}
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
    data = open(out).read().strip() if os.path.exists(out) else ""
    if os.path.exists(out):
        os.unlink(out)
    os.unlink(tcl_path)
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default="C-BIOS_MSX1_EU_BASIC_DISK")
    ap.add_argument("--src-dsk", default="disk/test720.dsk")
    ap.add_argument("--init-pc", type=lambda s: int(s, 16), default=0x4034)
    ap.add_argument("--prompt-t", type=float, default=14.0)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    dsk = "/tmp/" + os.path.basename(args.src_dsk)
    shutil.copy(args.src_dsk, dsk)
    ie = snap(args.machine, dsk, True, args.init_pc, args.prompt_t, args.timeout)
    shutil.copy(args.src_dsk, dsk)
    bp = snap(args.machine, dsk, False, args.init_pc, args.prompt_t, args.timeout)
    if not ie or not bp:
        sys.exit(f"capture failed (init={len(ie)} prompt={len(bp)})")
    IE, BP = bytes.fromhex(ie), bytes.fromhex(bp)
    print(f"{args.machine}  ${LO:04X}-${HI:04X}  (init-entry ${args.init_pc:04X} vs BASIC prompt)")
    print("=== C-BIOS/BASIC owns (non-FF at init-entry) — wa_clear must NOT clobber on BASIC boots ===")
    i = 0
    while i < len(IE):
        if IE[i] != 0xFF:
            a = LO + i
            vals = [IE[i]]
            j = i + 1
            while j < len(IE) and IE[j] != 0xFF:
                vals.append(IE[j])
                j += 1
            print(f"  ${a:04X}-${LO+j-1:04X}: {' '.join('%02X' % x for x in vals[:20])}"
                  f"{'..' if len(vals) > 20 else ''}")
            i = j
        else:
            i += 1
    c9 = [LO + i for i in range(len(IE)) if IE[i] == 0xC9]
    print(f"\nC9 (RET-stub) cells at init-entry: {len(c9)} "
          f"(e.g. {' '.join('$%04X' % a for a in c9[:8])}...) — DOS needs many of these as 00/code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
