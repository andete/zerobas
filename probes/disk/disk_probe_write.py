#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Differential DSKIO WRITE oracle: zerobas-disk's write path, proven black-box.

Proves that zerobas-disk's `dskio_write` (the new WD2793 Write Sector primitive)
produces a real, correctly-formatted sector -- bidirectionally:

  1. ROUND-TRIP (ours -> ours): on `C-BIOS_MSX1_BASIC_DISK` (our clean-room disk
     ROM in slot 3-1), inject a stub that DSKIO-WRITEs a distinctive 512-byte
     pattern to a data sector of a /tmp scratch image, then DSKIO-READs it back
     (the read path is already differential-confirmed). Read-back must equal the
     written bytes, and DSKIO write must return A=0/Cy=0.

  2. PERSISTENCE: re-open the SAME image fresh (a clean reboot) and DSKIO-READ
     the sector again -> the write persisted to the image file on disk.

  3. CROSS-MACHINE DIFFERENTIAL (the decisive check): boot the genuine
     `National_CF-3300` (its proprietary disk ROM) with that same /tmp image and
     DSKIO-READ the sector via the reference's OWN disk ROM -> byte-identical to
     what we wrote. This proves our WD2793 write sequence yields a sector the
     real hardware/ROM accepts and reads back correctly.

CLEAN-ROOM DISCIPLINE. The reference disk ROM is used ONLY as a black box. The
probe calls its DSKIO entry at the standard offset $4010 (MSX2 Technical
Handbook, disk ROM interface) via CALSLT ($001C) and observes ONLY the returned
data + carry/A. It never reads, dumps, or disassembles the reference ROM's code.

TEST DISK SAFETY. openMSX `-diska` writes back to the image file, so this probe
NEVER touches the committed `disk/test720.dsk` -- it makes a fresh /tmp scratch
COPY for every run and writes only into that. The target sector (default 1400)
is high in the data area, clear of the test image's FAT, root directory, and the
TEST.BIN / HI.TXT / PROG.BIN / PROG.BAS files.

Prerequisites:
  * openMSX with the CF-3300 ROMs installed (you provide ROMs you may use).
  * zerobas-disk's `*_BASIC_DISK` machine installed FROM THE BUILD UNDER TEST
    (`python3 tools/install-openmsx-machine.py --disk-rom disk.rom`).
  * the test image `disk/test720.dsk` (`make test-dsk`) as the seed.

    python3 probes/disk/disk_probe_write.py \\
        --dsk /path/to/zerobas-disk/disk/test720.dsk
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

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")

# Target data sector (logical). High in the data area of the 720K test image,
# clear of FAT (sectors 1..6), root dir (7..13) and the test files (start at 14).
TARGET_SEC = 1400

# --- injected stubs (assembled with pasmo, org $C000; hex embedded) ----------
#
# WRITE+READ stub (our machine). DSKIO-writes 512 bytes from $C200 to TARGET_SEC
# (pattern preloaded into $C200 by TCL), then DSKIO-reads the same sector to
# $C400.  Stores: $C100 = write A, $C101 = write carry (0=ok),
#                 $C102 = read  A, $C103 = read  carry (0=ok).
# CALSLT IY=$8700 (expanded slot 3-1); IX=$4010 (DSKIO). Direction carry is set
# with SCF immediately before the WRITE call (xor/ld clear carry), OR a before
# the READ call. `done` self-loop at $C049.
STUB_WRITE_HEX = (
    "f33e0006010ef91178052100c2dd211040fd21008737cd1c003200c13e0030023e01"
    "3201c13e0006010ef91178052100c4dd211040fd210087b7cd1c003202c13e003002"
    "3e013203c118fe")
STUB_WRITE_BP = 0xC049

# READ-ONLY stub (persistence reboot + CF-3300). DSKIO-reads TARGET_SEC -> $C400.
# Stores: $C102 = read A, $C103 = read carry. `done` self-loop at $C025.
STUB_READ_HEX = (
    "f33e0006010ef91178052100c4dd211040fd210087b7cd1c003202c13e0030023e01"
    "3203c118fe")
STUB_READ_BP = 0xC025

PATTERN_BUF = 0xC200    # source buffer for the write (preloaded)
READBACK_BUF = 0xC400   # read destination


def make_pattern() -> bytes:
    """A distinctive 512-byte pattern: a rolling counter XORed with a marker so
    it is neither all-zero, a single repeated byte, nor anything plausibly stale
    in the test image's data area."""
    return bytes(((i * 7 + 0x5A) ^ (i >> 8)) & 0xFF for i in range(512))


def run_machine(machine: str, dsk: str, out: str, stub_hex: str, stub_bp: int,
                pattern: bytes | None, boot_secs: float = 8.0,
                timeout: float = 60.0) -> dict:
    """Boot `machine` with `dsk`, optionally preload `pattern` at $C200, inject
    `stub_hex`, break at `stub_bp`, capture the result bytes to a dict."""
    pre = ""
    if pattern is not None:
        pre = (f"  debug write_block memory 0x{PATTERN_BUF:04X} "
               f"[binary format H* {pattern.hex()}]\n")
    tcl = f"""set throttle off
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "res=[__hex 0x{0xC100:04X} 4]"
  puts $f "readback=[__hex 0x{READBACK_BUF:04X} 512]"
  close $f; exit
}}
proc go {{}} {{
{pre}  debug write_block memory 0x{0xC000:04X} [binary format H* {stub_hex}]
  reg PC 0x{0xC000:04X}
  debug set_bp 0x{stub_bp:04X} {{}} {{ cap }}
}}
after time {boot_secs} {{ go }}
after time {boot_secs + 35} {{ cap }}
"""
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", dsk,
           "-command", "set renderer none", "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
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
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dsk", required=True, help="FAT12 seed image (.dsk); copied to /tmp, never written")
    ap.add_argument("--our-machine", default="C-BIOS_MSX1_BASIC_DISK")
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--sector", type=int, default=TARGET_SEC)
    args = ap.parse_args()

    pattern = make_pattern()
    pat_hex = pattern.hex()

    # Scratch COPY in /tmp -- openMSX writes back to the image, so we must never
    # let it touch the committed seed image.
    scratch = tempfile.NamedTemporaryFile(prefix="disk_probe_write_", suffix=".dsk", delete=False)
    scratch.close()
    shutil.copyfile(args.dsk, scratch.name)
    seed_bytes = open(scratch.name, "rb").read()
    print(f"scratch image: {scratch.name}  (copy of {args.dsk})")
    print(f"target sector: {args.sector}")

    ok = True
    try:
        # 1. ROUND-TRIP: write the pattern, read it back, same boot.
        rt = run_machine(args.our_machine, scratch.name, "/tmp/disk_probe_write_rt.txt",
                         STUB_WRITE_HEX, STUB_WRITE_BP, pattern)
        wA, wcy, rA, rcy = (rt["res"][0:2], rt["res"][2:4], rt["res"][4:6], rt["res"][6:8])
        rb = rt["readback"]
        wr_ok = (wA == "00" and wcy == "00")
        rd_ok = (rA == "00" and rcy == "00")
        match = (rb == pat_hex)
        good = wr_ok and rd_ok and match
        ok = ok and good
        print(f"\n[1] ROUND-TRIP (ours write -> ours read, same boot)")
        print(f"    write: A={wA} cy={wcy}  read: A={rA} cy={rcy}")
        print(f"    read-back == written pattern: {match}  {'PASS' if good else 'FAIL'}")

        # 1b. The image file must actually differ from the seed at the sector.
        post = open(scratch.name, "rb").read()
        off = args.sector * 512
        wrote_to_file = (post[off:off + 512] == pattern)
        ok = ok and wrote_to_file
        changed = (seed_bytes[off:off + 512] != post[off:off + 512])
        print(f"    image file sector now == pattern: {wrote_to_file} "
              f"(changed vs seed: {changed})  {'PASS' if wrote_to_file else 'FAIL'}")

        # 2. PERSISTENCE: fresh reboot, read-only.
        pr = run_machine(args.our_machine, scratch.name, "/tmp/disk_probe_write_persist.txt",
                         STUB_READ_HEX, STUB_READ_BP, None)
        prA, prcy = pr["res"][4:6], pr["res"][6:8]
        prb = pr["readback"]
        persist = (prA == "00" and prcy == "00" and prb == pat_hex)
        ok = ok and persist
        print(f"\n[2] PERSISTENCE (fresh reboot, ours read)")
        print(f"    read: A={prA} cy={prcy}  bytes == pattern: {prb == pat_hex}  "
              f"{'PASS' if persist else 'FAIL'}")

        # 3. CROSS-MACHINE: CF-3300 reads what we wrote.
        cm = run_machine(args.ref_machine, scratch.name, "/tmp/disk_probe_write_xm.txt",
                         STUB_READ_HEX, STUB_READ_BP, None)
        cmA, cmcy = cm["res"][4:6], cm["res"][6:8]
        cmb = cm["readback"]
        xmatch = (cmA == "00" and cmcy == "00" and cmb == pat_hex)
        ok = ok and xmatch
        print(f"\n[3] CROSS-MACHINE DIFFERENTIAL (CF-3300 reads ours-written sector)")
        print(f"    read: A={cmA} cy={cmcy}  CF-3300 bytes == our pattern: {cmb == pat_hex}  "
              f"{'PASS' if xmatch else 'FAIL'}")
        if not xmatch and cmb != pat_hex:
            # first differing byte, for diagnosis
            a = bytes.fromhex(cmb) if len(cmb) == 1024 else b""
            for i in range(min(len(a), 512)):
                if a[i] != pattern[i]:
                    print(f"    first diff at byte {i}: CF-3300=0x{a[i]:02X} ours=0x{pattern[i]:02X}")
                    break
    finally:
        os.unlink(scratch.name)

    print("\n" + ("ALL PASS -- zerobas-disk's DSKIO write produces a real sector: "
                  "round-trips, persists to the image, and is read byte-identical by the CF-3300"
                  if ok else "FAIL -- see results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
