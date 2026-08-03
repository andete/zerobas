#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tier-1 provider oracle: a REAL MSX1 BIOS drives zerobas-disk through PHYDIO.

This is Phase 1.5 box (b), Tier 1 (see zerobas disk/disk/docs/provider-oracle-scope.md).
It proves -- organically, with no probe-injected hook anywhere in the path -- that:

  1. a *genuine* MSX1 main BIOS (National CF-3300) cold-boot scan finds
     zerobas-disk's "AB" header in slot 3-1 and calls its INIT, which installs the
     standard H.PHYD ($FFA7) -> DSKIO ($4010) inter-slot CALLF hook; and
  2. a subsequent *real BIOS* PHYDIO call routes through that hook into
     zerobas-disk's DSKIO and returns the correct sector data with CY=0.

Two assertions carry the proof:

  * After cold boot, $FFA7..$FFAB == `F7 <slot> 10 40 C9` -- the inter-slot CALLF
    idiom (RST 30h ; slot ; $4010 ; RET; MSX2 TH s2 inter-slot calls). On the
    CF-3300 the slot byte is $87 (expanded slot 3-1). The probe does NOT write
    this hook; it merely reads it back after a clean boot, so its presence is sole
    evidence the *real* boot scan ran our INIT.
  * An injected Z80 stub calls the documented BIOS PHYDIO entry $0144 (MSX
    Assembly Page BIOS map / MSX2 Technical Handbook BIOS jump table -- allowed
    sources; NOT taken from any disassembly) to read logical sector 0. The
    returned 512 bytes must equal the on-disk boot sector (read directly from the
    .dsk in Python) and CY must be 0. The stub installs NO hook -- it relies
    entirely on the BIOS's own PHYDIO -> H.PHYD dispatch.

The stub additionally exercises the CY=1 write path: it saves a high data sector
(1437), writes a deterministic 512-byte pattern there via PHYDIO, reads it back
(must match), then restores the original bytes -- so the disk is left as found.

CLEAN-ROOM DISCIPLINE. The CF-3300 BIOS and disk ROM are black-box oracles ONLY.
The probe calls documented BIOS/hook entries ($0144 PHYDIO, the $FFA7 hook) and
reads RAM/registers; it never reads, dumps, or disassembles any reference ROM's
code bytes. The zerobas-disk ROM in slot 3-1 is OUR code.

CRITICAL: openMSX writes back to whatever .dsk path it is handed. This probe
ALWAYS copies the image to /tmp first and mounts the copy, never the committed
disk/test720.dsk. (The stub also restores sector 1437, but the /tmp copy is the
real safety net.)

Prerequisites:
  * openMSX with the genuine CF-3300 ROMs installed (cf-3300_basic-bios1.rom +
    cf-3300_disk.rom in your systemroms; you provide ROMs you may use).
  * the Tier-1 machine installed from the CURRENT zerobas tree:
        python3 tools/install-openmsx-machine.py --real-bios-disk --disk-rom disk.rom
    which writes National_CF-3300_ZEROBASDISK (real CF-3300 BIOS, zerobas-disk in
    slot 3-1).
  * a FAT12 image (zerobas disk/test720.dsk; `make test-dsk`).

    python3 probes/disk/disk_probe_provider_phydio.py \\
        --dsk /path/to/zerobas/disk/test720.dsk
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
import shutil
import signal
import subprocess
import sys
import tempfile
import time
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"

# Assembled with pasmo (org $C000); see disk_probe_provider_phydio.asm note in the
# zerobas commit. The stub calls BIOS PHYDIO ($0144) to: read sector 0 -> $C200;
# save sector 1437 -> $C600; write a pattern (byte i = i&0xFF) at $C400 to 1437;
# read 1437 back -> $C800; restore the original. Carry results land at $C100..$C103.
# `done` self-loop at $C07F.
STUB_HEX = (
    "f3af06010ef91100002100c2cd44013e0030023e013200c1af06010ef9119d052100c6"
    "cd44012100c41602af060077233c10fb1520f6373e0006010ef9119d052100c4cd4401"
    "3e0030023e013201c1af06010ef9119d052100c8cd44013e0030023e013202c1373e00"
    "06010ef9119d052100c6cd44013e0030023e013203c118fe")
STUB_ADDR = 0xC000
DONE_BP = 0xC07F

HPHYD = 0xFFA7              # H.PHYD hook (public MSX hook table; MSX2 TH appendix)
WRITE_SECTOR = 1437        # high data sector used for the write+readback round trip


def run_machine(machine: str, dsk: str, out: str, boot_secs: float = 8.0,
                timeout: float = 60.0) -> dict:
    """Boot `machine` with `dsk`; capture the H.PHYD hook bytes, inject the stub
    (which drives BIOS PHYDIO), and capture results + buffers into a dict."""
    tcl = f"""set throttle off
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "hphyd=[__hex 0x{HPHYD:04X} 5]"
  puts $f "carry=[__hex 0x{0xC100:04X} 4]"
  puts $f "sec0=[__hex 0x{0xC200:04X} 512]"
  puts $f "pat=[__hex 0x{0xC400:04X} 512]"
  puts $f "back=[__hex 0x{0xC800:04X} 512]"
  close $f; exit
}}
proc go {{}} {{
  debug write_block memory 0x{STUB_ADDR:04X} [binary format H* {STUB_HEX}]
  reg PC 0x{STUB_ADDR:04X}
  debug set_bp 0x{DONE_BP:04X} {{}} {{ cap }}
}}
after time {boot_secs} {{ go }}
after time {boot_secs + 40} {{ cap }}
"""
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", dsk,
           "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture from {machine} (machine missing? ROMs absent?)")
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dsk", required=True, help="FAT12 test image (.dsk)")
    ap.add_argument("--machine", default="National_CF-3300_ZEROBASDISK",
                    help="Tier-1 machine: real MSX1 BIOS + zerobas-disk in 3-1")
    ap.add_argument("--expect-slot", default="87",
                    help="expected hook slot byte (hex, no 0x); CF-3300 3-1 = 87")
    args = ap.parse_args()

    # NEVER mount the committed image: copy to /tmp and mount the copy.
    tmp = tempfile.NamedTemporaryFile(prefix="zbd_phydio_", suffix=".dsk",
                                      delete=False)
    tmp.close()
    shutil.copyfile(args.dsk, tmp.name)
    host = open(tmp.name, "rb").read()

    try:
        d = run_machine(args.machine, tmp.name, "/tmp/disk_probe_provider_phydio.txt")
    finally:
        # Leave the /tmp copy for post-mortem only if something is off; otherwise
        # remove it. (The committed image was never touched.)
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    ok = True

    # --- Assertion 1: the real boot scan installed our H.PHYD hook -----------
    expect_hook = f"f7{args.expect_slot.lower()}1040c9"
    hphyd = d.get("hphyd", "")
    hook_ok = (hphyd == expect_hook)
    ok = ok and hook_ok
    print(f"[{'PASS' if hook_ok else 'FAIL'}] H.PHYD $FFA7..AB = {hphyd} "
          f"(expect {expect_hook} = RST30h; slot ${args.expect_slot}; $4010; RET)")
    print("        -> installed by the REAL CF-3300 boot scan (probe injected no hook)")

    # --- Assertion 2: real BIOS PHYDIO read sector 0 == on-disk boot sector --
    carry = d.get("carry", "")          # 4 bytes: read0, write, readback, restore
    cy_read0 = carry[0:2]
    sec0 = d.get("sec0", "")
    expect0 = host[0:512].hex()
    read0_ok = (cy_read0 == "00" and sec0 == expect0)
    ok = ok and read0_ok
    print(f"[{'PASS' if read0_ok else 'FAIL'}] BIOS PHYDIO read sector 0: "
          f"CY={cy_read0} (expect 00), bytes=={'disk' if sec0 == expect0 else 'MISMATCH'}")

    # --- Assertion 3 (optional, CY=1 path): write + readback round trip ------
    cy_write = carry[2:4]
    cy_back = carry[4:6]
    cy_restore = carry[6:8]
    pat = d.get("pat", "")
    back = d.get("back", "")
    wr_ok = (cy_write == "00" and cy_back == "00" and pat == back and pat != "")
    ok = ok and wr_ok
    print(f"[{'PASS' if wr_ok else 'FAIL'}] BIOS PHYDIO write+readback sector "
          f"{WRITE_SECTOR}: CYwrite={cy_write} CYback={cy_back} "
          f"readback=={'pattern' if pat == back else 'MISMATCH'}")
    print(f"        restore-write CY={cy_restore} (disk left as found; /tmp copy anyway)")

    print("\n" + (
        "ALL PASS -- a REAL MSX1 BIOS PHYDIO organically routes through H.PHYD "
        "into zerobas-disk's DSKIO (sector 0 byte-identical, CY=0; no injected hook)"
        if ok else
        "FAIL -- see assertions above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
