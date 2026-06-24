#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Classify the high-RAM band: loaded MSXDOS.SYS vs disk-ROM-built work area.

§8.52 sized the high-RAM kernel at ~1,920 B "to build", but MSXDOS.SYS is the DOS
kernel that relocates ITSELF into high RAM (§8.24: lands at $D606). Code that is just
the loaded MSXDOS.SYS is proprietary-we-load-it (like COMMAND.COM), NOT code we
write. This probe separates the two: it dumps $C000-$FFFF at A> idle, extracts the
real MSXDOS.SYS bytes from the disk (FAT12 walk), finds where the kernel relocated to
(best byte-match offset), and reclassifies each executed high-RAM region (§8.52) as
LOADED (inside the relocated MSXDOS.SYS image) or BUILT (disk-ROM work area = ours).

Black-box: reads RAM + the oracle file; never disassembles either.

    python3 probes/disk/disk_probe_dosboot_hiram_origin.py --dos-disk /tmp/dos-oracle.dsk
"""
from __future__ import annotations

import argparse
import os
import signal
import struct
import subprocess
import sys
import tempfile
import time

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
SPAN_CALL = 0xD821
# executed high-RAM regions (§8.52)
REGIONS = [
    (0xC200, 0xC27F), (0xCB90, 0xCBDF), (0xCE50, 0xD00F), (0xD070, 0xD08F),
    (0xD600, 0xD60F), (0xD820, 0xD8BF), (0xDDA0, 0xDDEF), (0xDE50, 0xDF6F),
    (0xEF90, 0xF05F), (0xF0F0, 0xF17F), (0xF1C0, 0xF1FF), (0xF250, 0xF2BF),
    (0xF360, 0xF39F), (0xFD90, 0xFDCF), (0xFFC0, 0xFFDF),
]


def fat12_read(dsk: str, name: str) -> bytes:
    """Minimal FAT12 reader: return the bytes of `name` (e.g. 'MSXDOS   SYS')."""
    img = open(dsk, "rb").read()
    bps = struct.unpack_from("<H", img, 11)[0]
    spc = img[13]
    rsvd = struct.unpack_from("<H", img, 14)[0]
    nfat = img[16]
    rootent = struct.unpack_from("<H", img, 17)[0]
    spf = struct.unpack_from("<H", img, 22)[0]
    root_start = (rsvd + nfat * spf) * bps
    data_start = root_start + rootent * 32
    fat = img[rsvd * bps: (rsvd + spf) * bps]

    def fat_entry(c: int) -> int:
        off = c + (c >> 1)
        v = fat[off] | (fat[off + 1] << 8)
        return (v >> 4) if (c & 1) else (v & 0xFFF)

    for i in range(rootent):
        e = img[root_start + i * 32: root_start + i * 32 + 32]
        if e[0] in (0x00, 0xE5):
            continue
        if e[11] & 0x08:        # volume label / LFN
            continue
        base = e[0:8].decode("latin1").rstrip()
        ext = e[8:11].decode("latin1").rstrip()
        nm = base + ("." + ext if ext else "")
        if nm == name:
            size = struct.unpack_from("<I", e, 28)[0]
            clus = struct.unpack_from("<H", e, 26)[0]
            out = bytearray()
            while 2 <= clus < 0xFF8:
                off = data_start + (clus - 2) * spc * bps
                out += img[off: off + spc * bps]
                clus = fat_entry(clus)
            return bytes(out[:size])
    raise SystemExit(f"{name} not found on {dsk}")


def dump_hiram(machine: str, dsk: str, timeout: float) -> bytes:
    out = tempfile.mktemp(suffix=".bin")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
set ::active 0
set ::idle 0
proc dump {{}} {{
  set data [debug read_block memory 0xC000 16384]
  set f [open {{{out}}} wb]
  puts -nonewline $f $data
  close $f
  exit
}}
debug set_bp 0x{SPAN_CALL:04X} {{}} {{
  if {{$::active}} return
  set ::active 1
  debug set_condition {{1}} {{
    set p [reg PC]
    if {{$p >= 0x0B90 && $p <= 0x0D8F}} {{
      incr ::idle
      if {{$::idle >= 150000}} {{ dump }}
    }}
  }}
}}
after time 120 {{ if {{$::active}} {{ dump }} else {{ exit }} }}
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
        sys.exit("no high-RAM dump captured")
    data = open(out, "rb").read()
    os.unlink(out)
    os.unlink(tcl_path)
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--machine", default=STOCK_MACHINE)
    ap.add_argument("--timeout", type=float, default=200.0)
    args = ap.parse_args()
    sysbytes = fat12_read(args.dos_disk, "MSXDOS.SYS")
    print(f"MSXDOS.SYS = {len(sysbytes)} bytes (${len(sysbytes):04X})")
    hiram = dump_hiram(args.machine, args.dos_disk, args.timeout)  # $C000..$FFFF
    n = len(sysbytes)

    def at(addr: int) -> int:
        return hiram[addr - 0xC000]

    # find best relocation base in $C000-$E800 by match ratio over the file
    best_base, best_match = 0, -1
    for base in range(0xC000, 0xE800):
        if base - 0xC000 + n > len(hiram):
            break
        m = sum(1 for i in range(0, n, 4) if at(base + i) == sysbytes[i])  # sample /4
        if m > best_match:
            best_match, best_base = m, base
    ratio = best_match / (n // 4)
    print(f"best MSXDOS.SYS relocation base = ${best_base:04X}  "
          f"(sampled match {ratio*100:.1f}%)  span ${best_base:04X}-${best_base+n-1:04X}\n")

    print("=== high-RAM region origin (§8.52 regions reclassified) ===")
    loaded = built = 0
    for s, e in REGIONS:
        size = e - s + 16
        # per-region match against MSXDOS.SYS at the relocation offset
        inside = best_base <= s < best_base + n
        if inside:
            hits = tot = 0
            for a in range(s, e + 1):
                fi = a - best_base
                if 0 <= fi < n:
                    tot += 1
                    if at(a) == sysbytes[fi]:
                        hits += 1
            r = hits / tot if tot else 0
            tag = "LOADED MSXDOS.SYS" if r >= 0.6 else "BUILT (work area)"
        else:
            r = 0.0
            tag = "BUILT (work area)"
        if tag.startswith("LOADED"):
            loaded += size
        else:
            built += size
        print(f"  {s:04X}-{e+15:04X}  {size:4d}B  match {r*100:5.1f}%  -> {tag}")
    print(f"\n  LOADED (MSXDOS.SYS, not ours): {loaded} B")
    print(f"  BUILT  (work area, OURS):      {built} B")
    print(f"  => high-RAM code WE build is ~{built} B, not 1,920 B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
