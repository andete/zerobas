#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-2 a3 §8.34: characterise HOW the MSX-DOS boot reaches our FDC driver's
Restore-and-wait-BUSY loop at `$43EC` (`fdc_wr_loop`) and why BUSY never clears.

Background (§8.33): after the `$027C` derail was cleared the boot advances to real
disk I/O and then stalls in OUR FDC driver at `$43EC` (the `bit 0,(FDC_STATUS)`
BUSY poll inside `fdc_wait_ready`, reached from `fdc_restore $43E4`). Crucially the
standard DSKIO entry `$4010` shows ZERO hits, so the FDC code is NOT being driven
through the documented sector entry. Two hypotheses to decide:

  (A) LEGIT-BUT-NONSTANDARD: the kernel's first directory read enters our sector
      engine through some path other than `$4010` (e.g. straight into `dskio`
      `$4231` or `fdc_read_phys` `$42C0`), the first attempt fails, and the retry
      `call fdc_restore` ($43E4) then hangs.
  (B) DERAIL: the kernel computed a wrong address and CALL/JP'd directly into the
      middle of our ROM at/near `fdc_restore`, so `FDC_CTRL` (drive-select+motor)
      was never written -> the WD2793 has no selected drive -> RESTORE can't
      complete -> BUSY never clears.

Method (pure black-box of OUR ROM's runtime behaviour; Tier-1 only, no stock
needed — the stall is in code only we have): trap the milestone entry points
DSKIO `$4010`, `dskio` `$4231`, `fdc_read_phys` `$42C0`, `fdc_write_phys` `$434B`,
`fdc_restore` `$43E4`, `fdc_wait_ready` `$43E9`, `fdc_wr_loop` `$43EC`, plus the
file-layer vectors that precede them. For the first few hits of each we log PC,
SP, the return address on the stack (= the immediate caller), a short stack
window (return chain), and AF/BC/DE/HL/IX/IY. The ORDER of first-hits reconstructs
the approach; the caller of `fdc_restore` decides (A) vs (B): a caller inside our
ROM ($43xx, the read/write retry tails) => (A); a caller in kernel/RAM space
($Cxxx/$Dxxx) or a bogus stack => (B).

At the stall we also snapshot the live FDC registers (status $7FB8, sector $7FBA,
data $7FBB, ctrl/IRQ-DRQ $7FBC) to characterise WHY BUSY is stuck (e.g. ctrl=$00
=> no drive/motor selected, the (B) signature).

RESULT (§8.34): hypothesis (A). `DSKIO $4010` was 0 only because our own BDOS file
layer CALLs the `dskio` BODY ($4231) directly (callers all inside our ROM); not a
derail. The early boot reads succeed; the failing reads are in the post-init
COMMAND/high-RAM context (SP=$8Fxx) where the FDC status reads `$04` = LOST DATA —
the WD2793 DRQ poll was preempted by the 50 Hz VDP interrupt (live once the kernel
runs EI; the boot ran masked). Fix: an IFF-preserving DI guard around
fdc_read_phys/fdc_write_phys (disk.asm fdc_di_save/fdc_io_done). After the fix
`fdc_restore` hits drop to 0 and the boot advances to MSXDOS.SYS driving the public
`$4010` DSKIO vector itself — exposing the §8.35 gap: the kernel asks DSKIO to
transfer into HL=$5290, a buffer INSIDE page 1 (our ROM), which our `ld (hl),a`
cannot write.

DISK SAFETY: boots only a /tmp copy of the DOS disk.

    python3 probes/disk/disk_probe_dosboot_fdc.py \
        --dos-disk ~/Documents/msx/msx/disks/msxdos103-cmd111.dsk
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
TIER1_MACHINE = "National_CF-3300_ZEROBASDISK"

# Milestone addresses from disk/disk.asm's pasmo symbol table
# (`pasmo --bin disk/disk.asm out.rom syms.txt`).
MILESTONES = [
    (0x4010, "DSKIO_ENTRY"),
    (0x4257, "dskio"),
    (0x4312, "fdc_read_phys"),
    (0x43A4, "fdc_write_phys"),
    (0x4444, "fdc_restore"),
    (0x4449, "fdc_wait_ready"),
    # NB: $444C (fdc_wr_loop) is the tight BUSY-poll itself — never breakpoint it,
    # a persistent bp on a hot loop starves emutime. PC_at_stall confirms it.
    (0x44FF, "bdos_entry"),
    (0x448E, "getdpb"),
    (0x448C, "dskchg"),
]
# Per-address cap on how many hits we log (keeps the tight $43EC loop cheap).
LOG_CAP = 4

# FDC register window (memory-mapped WD2793, National style).
FDC_REGS = [(0x7FB8, "status"), (0x7FBA, "sector"), (0x7FBB, "data"),
            (0x7FBC, "ctrl_irqdrq")]


def run(machine: str, dsk: str, settle: float, timeout: float) -> dict:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")

    names = " ".join(f"0x{a:04X} {{{n}}}" for a, n in MILESTONES)
    fdc = " ".join(f"0x{a:04X} {{{n}}}" for a, n in FDC_REGS)

    tcl = f"""set throttle off
set renderer none
set ::log {{}}
array set ::nm [list {names}]
array set ::cnt {{}}
array set ::bp {{}}
proc rb {{a}} {{ debug read memory $a }}
proc rw {{a}} {{ binary scan [debug read_block memory $a 2] s v; return [expr {{$v & 0xFFFF}}] }}
proc onhit {{pc}} {{
  set name $::nm($pc)
  if {{![info exists ::cnt($pc)]}} {{ set ::cnt($pc) 0 }}
  incr ::cnt($pc)
  if {{$::cnt($pc) <= {LOG_CAP}}} {{
    set sp [reg SP]
    set s0 [rw $sp]; set s1 [rw [expr {{$sp+2}}]]; set s2 [rw [expr {{$sp+4}}]]
    lappend ::log [format \
      "%-14s pc=%04X #%d sp=%04X ret=%04X stk=%04X,%04X,%04X AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X" \
      $name $pc $::cnt($pc) $sp $s0 $s0 $s1 $s2 [reg AF] [reg BC] [reg DE] [reg HL] [reg IX] [reg IY]]
  }}
  # Early exit: once the FDC retry signature has been sampled enough, capture and
  # stop — don't pay onhit cost across a full settle window of the retry cycle.
  if {{$pc == 0x443E && $::cnt($pc) >= {LOG_CAP}}} {{ cap }}
}}
foreach {{mpc mnm}} [array get ::nm] {{
  set ::bp($mpc) [debug set_bp $mpc {{}} "onhit $mpc"]
}}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "=== ordered milestone hits (first {LOG_CAP} each) ==="
  foreach e $::log {{ puts $f $e }}
  puts $f "=== total hit counts ==="
  foreach {{mpc mnm}} [array get ::nm] {{
    set c 0; if {{[info exists ::cnt($mpc)]}} {{ set c $::cnt($mpc) }}
    puts $f [format "%-14s %04X count=%d" $mnm $mpc $c]
  }}
  puts $f "=== FDC registers at stall ==="
  foreach {{ra rnm}} [list {fdc}] {{
    puts $f [format "%-14s %04X = %02X" $rnm $ra [rb $ra]]
  }}
  puts $f [format "PC_at_stall=%04X SP=%04X" [reg PC] [reg SP]]
  close $f
  exit
}}
after time {settle:.1f} {{ cap }}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture (machine/ROMs/disk missing? machine={machine})")
    text = open(out).read()
    os.unlink(out)
    os.unlink(tcl_path)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--settle", type=float, default=16.0)
    ap.add_argument("--timeout", type=float, default=70.0)
    args = ap.parse_args()

    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")

    tmp = tempfile.mktemp(suffix=".dsk")
    shutil.copyfile(args.dos_disk, tmp)
    try:
        text = run(TIER1_MACHINE, tmp, args.settle, args.timeout)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    print(text)

    # Quick verdict heuristic on the first fdc_restore caller.
    restore_ret = None
    for line in text.splitlines():
        if line.startswith("fdc_restore "):
            for tok in line.split():
                if tok.startswith("ret="):
                    restore_ret = int(tok[4:], 16)
            break
    print("---- verdict ----")
    if restore_ret is None:
        print("fdc_restore was not hit in the window — the $43EC loop is reached "
              "via fdc_wait_ready directly (a SEEK wait, not a Restore), or not at all.")
    elif 0x4000 <= restore_ret <= 0x7FFF:
        print(f"fdc_restore caller ret={restore_ret:04X} is INSIDE our ROM "
              f"=> hypothesis (A): legit read/write retry path.")
    else:
        print(f"fdc_restore caller ret={restore_ret:04X} is OUTSIDE our ROM "
              f"=> hypothesis (B): derail straight into the FDC code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
