#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""M32 $24 SETRND black-box characterisation (disk/docs/tier2-m32-setrnd-char.md).

$24 SETRND is meant to write the FCB random-record field (FCB+33..35) from the
CURRENT sequential position. We do NOT assume a formula: this drives the position
to a known place — FOPEN, then K sequential reads — calls $24 on BOTH machines,
and DUMPS the resulting FCB position fields (EX/S2/CR/RR) so we can read stock's
actual RESULT and derive the mapping empirically. It also settles the open
question of whether OURS' $24 is a no-op (RR stays 0) — the deferred gate-green
piece — by putting ours and stock side by side.

Method (clean-room, black-box): assemble setrnd_char.asm (SETRND.COM), patch its
per-case param block ($0103 nreads, $0104 rs), inject SETRND.COM + a large
RDTEST.BIN into a /tmp copy of a real MSX-DOS-1 disk, then run disk_probe_diff.py
`capture --machine <ours|stock>` (ONE-SIDED dump, no diff) at SETRND's `done`
self-loop on each machine and read the 6 result bytes. Stock ROM code is never
read/disassembled; only the RAM result stock's SETRND wrote is observed. Test
disks are always /tmp copies.

  python3 probes/disk/disk_probe_setrnd_char.py
  python3 probes/disk/disk_probe_setrnd_char.py --only 128
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicate)

# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ASM = os.path.join(HERE, "setrnd_char.asm")
DIFF = os.path.join(HERE, "disk_probe_diff.py")
DEFAULT_DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")

MAGIC = 0x5A                       # arm signature at $0102 (constant)
RES_BASE = 0x0340                  # res_ex/res_s2/res_cr/res_rr[3]
RES_LEN = 6
FILESIZE = 20000                   # 156.25 records => sweep can cross the extent boundary at 128

# Sweep of "K sequential reads before $24". 0..4 map the current-record (CR) low
# byte; 127/128/129/130 straddle the extent-0/extent-1 boundary (record 128) so we
# can read the EX contribution to the random record.
DEFAULT_KS = [0, 1, 2, 3, 4, 5, 127, 128, 129, 130]


def rdtest_bin(size: int) -> bytes:
    return bytes([(i * 5 + 7) & 0xFF for i in range(size)])


def assemble(tmp_dir: str) -> tuple[bytearray, int]:
    com = os.path.join(tmp_dir, "setrnd.com")
    sym = os.path.join(tmp_dir, "setrnd.sym")
    subprocess.run(["pasmo", "--bin", ASM, com, sym], check=True)
    done = None
    for line in open(sym):
        name, _, rest = line.strip().partition("\t")
        if name.strip() == "done":
            done = int(rest.strip().split()[-1].rstrip("H"), 16)
    if done is None:
        sys.exit("could not find `done` in setrnd.sym")
    return bytearray(open(com, "rb").read()), done


def patch_params(com: bytearray, nreads: int, rs: int, dosr: int) -> None:
    off = 0x0103 - 0x0100          # .com loaded at $0100
    com[off] = nreads & 0xFF
    com[off + 1] = rs & 0xFF
    com[off + 2] = (rs >> 8) & 0xFF
    com[off + 3] = dosr & 0xFF


def dump_one(machine: str, done: int, disk: str,
             base: int = RES_BASE, length: int = RES_LEN) -> list[int] | None:
    cmd = ["python3", DIFF, "capture",
           "--at", f"{done:#06x}", "--arm-check-val", f"{MAGIC:#04x}",
           "--keys", "\\rSETRND\\r", "--keys-at", "20", "--settle", "40",
           "--machine", machine, "--mem", f"{base:#06x}:{length:#04x}",
           "--diska", disk]
    p = subprocess.run(omsx_preflight.guarded(cmd), cwd=ROOT, capture_output=True, text=True, timeout=400)
    txt = p.stdout + p.stderr
    if "never reached occurrence" in txt:
        return None
    m = re.search(r"memory 0x[0-9a-fA-F]+\+\d+:\s+([0-9A-Fa-f ]+)", txt)
    if not m:
        return None
    return [int(x, 16) for x in m.group(1).split()]


def rr24(b: list[int]) -> int:
    return b[3] | (b[4] << 8) | (b[5] << 16)


def build_disk(k: int, rs: int, dosr: int, dos_src: str, com_base: bytearray,
               tmp_dir: str) -> str:
    com = bytearray(com_base)
    patch_params(com, k, rs, dosr)
    out = os.path.join(tmp_dir, f"zerobas_setrnd_k{k}.dsk")
    shutil.copyfile(dos_src, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "RDTEST", "BIN", rdtest_bin(FILESIZE))
    fat12_add(img, "SETRND", "COM", bytes(com))
    open(out, "wb").write(img)
    return out


def run_case(k: int, rs: int, dosr: int, dos_src: str, done: int,
             com_base: bytearray, tmp_dir: str) -> dict | None:
    out = build_disk(k, rs, dosr, dos_src, com_base, tmp_dir)
    ours = dump_one("ours", done, out)
    stock = dump_one("stock", done, out)
    return {"k": k, "ours": ours, "stock": stock}


def fmt(b: list[int] | None) -> str:
    if b is None:
        return "  <no anchor>                 "
    return (f"EX={b[0]:02X} S2={b[1]:02X} CR={b[2]:02X} "
            f"RR={b[5]:02X}{b[4]:02X}{b[3]:02X}(={rr24(b)})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", default=DEFAULT_DOS)
    ap.add_argument("--tmp-dir", default="/tmp")
    ap.add_argument("--rs", type=lambda x: int(x, 0), default=0,
                    help="record size to store in FCB+14..15 before $24 (0=leave)")
    ap.add_argument("--only", type=int, help="run a single K (number of RDSEQ)")
    ap.add_argument("--no-setrnd", action="store_true",
                    help="skip the $24 call (isolate whether $24 or FOPEN/RDSEQ writes RR)")
    ap.add_argument("--full-fcb", action="store_true",
                    help="dump the whole 37-byte FCB ($0300) on both machines instead of the table")
    args = ap.parse_args()

    if not os.path.exists(args.dos_disk):
        sys.exit(f"missing DOS oracle disk: {args.dos_disk}")
    com_base, done = assemble(args.tmp_dir)
    dosr = 0 if args.no_setrnd else 1
    print(f"SETRND.COM assembled; done = {done:#06x}; RDTEST.BIN = {FILESIZE}B "
          f"(~{FILESIZE//128} records); rs={args.rs}; "
          f"$24 {'SKIPPED' if args.no_setrnd else 'called'}")
    print("  K = sequential reads before $24. Extent boundary at record 128.\n")

    ks = [args.only] if args.only is not None else DEFAULT_KS

    if args.full_fcb:
        print(f"  Full FCB dump ($0300+37). FCB+12=EX +14/15=S2/RC +32=CR +33/34/35=RR\n")
        for k in ks:
            disk = build_disk(k, args.rs, dosr, args.dos_disk, com_base, args.tmp_dir)
            for who in ("stock", "ours"):
                b = dump_one(who, done, disk, base=0x0300, length=0x25)
                hx = " ".join(f"{x:02X}" for x in b) if b else "<no anchor>"
                print(f"  K={k:>3} {who:<5}: {hx}")
            print()
        return 0

    print(f"  {'K':>4}  {'STOCK (CF-3300)':<40}  OURS (zerobas-disk)")
    print(f"  {'-'*4}  {'-'*40}  {'-'*40}")
    rows = []
    for k in ks:
        r = run_case(k, args.rs, dosr, args.dos_disk, done, com_base, args.tmp_dir)
        rows.append(r)
        print(f"  {k:>4}  {fmt(r['stock']):<40}  {fmt(r['ours'])}")

    # Derived observations
    print("\n  --- derived ---")
    ours_noop = all(r["ours"] and rr24(r["ours"]) == 0 for r in rows if r["ours"])
    stock_tracks = all(
        r["stock"] and rr24(r["stock"]) == (r["stock"][0] * 128 + r["stock"][2])
        for r in rows if r["stock"])
    print(f"  ours' $24 leaves RR=0 for every K (no-op gap): {ours_noop}")
    print(f"  stock RR == EX*128 + CR for every K (CP/M formula holds): {stock_tracks}")
    if not stock_tracks:
        print("  -> stock does NOT follow EX*128+CR; inspect the table for the real rule.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
