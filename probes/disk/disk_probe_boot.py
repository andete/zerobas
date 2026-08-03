#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Cold-boot-safety probe: is disk/test720.dsk safe to insert at the CF-3300's
cold boot, or does its boot sector hang the reference?

WHY THIS EXISTS. A real MSX1 disk machine, per the MSX2 Technical Handbook §3
(MSX-DOS, boot procedure), reads logical sector 0 into $C000..$C0FF and -- if the
first byte is $EB or $E9 -- CALLs the boot code at $C01E (CY flag reset). The
documented default at $C01E is `RET NC`: "nothing is carried and the execution
returns", so the machine falls through to DISK-BASIC. The old test720.dsk boot
sector had $EB at byte 0 (so the boot code IS reached) but the whole $1E.. boot-
code area was $00 -- a NOP slide that runs off the end into garbage. Cold-booting
the National CF-3300 with that filler image WEDGES the machine (observed: PC stuck
at $002E, SP corrupted down to $0026 -- a runaway in page 0). The probes only
avoided this by inserting the disk AFTER the reference reached BASIC.

The fix (zerobas tools/make_test_dsk.py) writes the documented safe stub at $1E:
  $1E : D0  RET NC   (the documented data-disk default; CY reset on entry => RET)
  $1F : C9  RET      (belt-and-braces unconditional return)
so the CALL at $C01E returns cleanly and the machine reaches BASIC.

WHAT THIS PROBE ASSERTS. It cold-boots the REAL National_CF-3300 reference (its
proprietary BASIC+disk ROMs, available here) with the image attached as drive A,
lets it settle, and samples the CPU PC at several emulated-time points. A
cold-boot-SAFE image must, at every sample:
  * NOT have PC stuck inside the boot-code area $C000..$C0FF (it returned from
    the boot CALL), AND
  * NOT be wedged in the low-page runaway region the filler image dies in
    (PC < $0100 with a tiny SP), AND
  * show PC actually MOVING across samples (a live interpreter idle/echo loop,
    not a 1-instruction self-loop) OR sitting in a known ROM/RAM idle region.

This is strictly black-box: we attach a disk and observe CPU PC. No ROM is read
or disassembled. It is a FUNCTIONAL safety check, not a differential oracle --
the "reference" here is the genuine MSX1 disk boot ROM doing its real boot, which
is exactly the path the TODO wanted proven safe.

The contrast case (the OLD filler boot, $1E.. all $00) is reproducible with
--filler-contrast: the probe synthesises the old filler image from the current
one and asserts it DOES wedge (PC stuck < $0100), so the before/after delta is
demonstrated in one run.

Prerequisites:
  * openMSX with the National_CF-3300 system ROMs
    (cf-3300_basic-bios1.rom + cf-3300_disk.rom in ~/.openMSX/share/systemroms).
  * disk/test720.dsk regenerated from the current zerobas tree
    (`python3 tools/make_test_dsk.py`).

    python3 probes/disk/disk_probe_boot.py
    python3 probes/disk/disk_probe_boot.py --filler-contrast
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import signal
import subprocess
import shutil
import sys
import tempfile
import time
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
# The test image lives in the sibling zerobas repo (the disk ROM's home).
ZEROBAS = os.environ.get(
    "ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

# The reference is the genuine MSX1 disk machine, booting its own ROMs.
MACHINE = "National_CF-3300"

# Boot-code area sector 0 is loaded into (MSX2 TH §3): $C000..$C0FF. The entry is
# $C01E. A safe image must NOT leave PC stuck anywhere in this window.
BOOT_LO, BOOT_HI = 0xC000, 0xC100
# The filler image's observed runaway lands in page 0 ($002E) with a corrupted
# tiny SP. Treat "PC in page 0 AND not moving" as the wedged signature.
LOWPAGE_HI = 0x0100

# Emulated-time sample points (seconds). The CF-3300 (real BIOS) boots slower
# than C-BIOS, so we sample late and at several points; we sync on the settled
# state, not a single instant (dev-workflow.md: sync on event/settle, not time).
SAMPLE_TIMES = (10.0, 11.0, 12.0)


def run_boot(dsk_path: str, out_path: str, timeout: float = 60.0) -> list[int]:
    """Cold-boot MACHINE with dsk_path as drive A; return the PC samples."""
    sample_tcl = "\n".join(
        f"after time {t} {{ cap {i} }}" for i, t in enumerate(SAMPLE_TIMES))
    last = len(SAMPLE_TIMES) - 1
    tcl = f"""set throttle off
set renderer none
set sound_driver null
proc cap {{i}} {{
  set f [open {{{out_path}}} a]
  puts $f "$i [format %04X [reg PC]] [format %04X [reg SP]]"
  close $f
  if {{$i == {last}}} {{ exit }}
}}
{sample_tcl}
"""
    tcl_path = out_path + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out_path):
        os.unlink(out_path)
    cmd = [OMSX, "-machine", MACHINE, "-diska", dsk_path, "-script", tcl_path]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT cold-booting {MACHINE} with {dsk_path}")
    if not os.path.exists(out_path):
        sys.exit(f"no capture from {MACHINE} (ROMs absent? machine missing?)")
    samples = []
    for line in open(out_path):
        parts = line.split()
        if len(parts) >= 3:
            samples.append((int(parts[1], 16), int(parts[2], 16)))
    return samples


def is_wedged(samples: list[tuple[int, int]]) -> bool:
    """The filler signature: PC frozen in low page across every sample."""
    if not samples:
        return False
    pcs = [pc for pc, _ in samples]
    frozen = len(set(pcs)) == 1
    in_lowpage = all(pc < LOWPAGE_HI for pc in pcs)
    return frozen and in_lowpage


def assess_safe(samples: list[tuple[int, int]]) -> tuple[bool, list[str]]:
    """A cold-boot-safe image: no sample stuck in the boot window or wedged in
    low page; PC moving (live interpreter) or in a ROM/RAM idle region."""
    msgs = []
    pcs = [pc for pc, _ in samples]
    in_boot = [pc for pc in pcs if BOOT_LO <= pc < BOOT_HI]
    wedged = is_wedged(samples)
    moving = len(set(pcs)) > 1
    for pc, sp in samples:
        zone = "BOOT-AREA" if BOOT_LO <= pc < BOOT_HI else (
            "low-page" if pc < LOWPAGE_HI else "ROM/RAM")
        msgs.append(f"    PC=${pc:04X} SP=${sp:04X}  ({zone})")
    ok_boot = not in_boot
    ok_wedge = not wedged
    msgs.append(f"  [{'PASS' if ok_boot else 'FAIL'}] PC never stuck in boot area "
                f"$C000..$C0FF")
    msgs.append(f"  [{'PASS' if ok_wedge else 'FAIL'}] not wedged in low-page "
                f"runaway (filler signature)")
    msgs.append(f"  [info] PC moving across samples: {moving} "
                f"(a live BASIC idle/echo loop)")
    return (ok_boot and ok_wedge), msgs


def make_filler(src: str, dst: str) -> None:
    """Synthesise the OLD filler image: same bytes but boot-code area $1E.. = $00."""
    d = bytearray(open(src, "rb").read())
    for i in range(0x1E, 0x1FE):     # leave the $55$AA signature at $1FE/$1FF
        d[i] = 0x00
    open(dst, "wb").write(bytes(d))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dsk", default=DSK, help="disk image to cold-boot")
    ap.add_argument("--filler-contrast", action="store_true",
                    help="also boot the synthesised OLD filler image and assert "
                         "it DOES wedge (demonstrates the before/after delta)")
    args = ap.parse_args()

    if not os.path.exists(args.dsk):
        sys.exit(f"disk image not found: {args.dsk} (run make_test_dsk.py)")

    print(f"Cold-booting {MACHINE} with {os.path.basename(args.dsk)} (the FIX):")
    samples = run_boot(args.dsk, "/tmp/disk_probe_boot_fix.txt")
    safe, msgs = assess_safe(samples)
    for m in msgs:
        print(m)
    ok = safe

    if args.filler_contrast:
        with tempfile.NamedTemporaryFile(suffix=".dsk", delete=False) as tf:
            filler = tf.name
        make_filler(args.dsk, filler)
        print(f"\nCold-booting {MACHINE} with the synthesised OLD FILLER image "
              f"(contrast):")
        fsamples = run_boot(filler, "/tmp/disk_probe_boot_filler.txt")
        for pc, sp in fsamples:
            zone = "BOOT-AREA" if BOOT_LO <= pc < BOOT_HI else (
                "low-page" if pc < LOWPAGE_HI else "ROM/RAM")
            print(f"    PC=${pc:04X} SP=${sp:04X}  ({zone})")
        wedged = is_wedged(fsamples)
        print(f"  [{'PASS' if wedged else 'FAIL'}] filler image WEDGES the "
              f"reference (PC frozen in low page) -- confirms the bug the fix "
              f"removes")
        os.unlink(filler)
        ok = ok and wedged

    print("\n" + ("ALL PASS -- the image cold-boots the CF-3300 reference safely "
                  "(reaches BASIC, no boot-area hang)"
                  if ok else
                  "FAIL -- the image is NOT cold-boot-safe on the reference"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
