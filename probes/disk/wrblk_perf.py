#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""WRBLK positioning performance — characterisation + M28-vs-M29 before/after.

Backs the numbers in disk/docs/tier2-m29-wrblk-position-cursor-spec.md §1 / §1.1.
Emulator-free: drives the REAL wrblk_body on the tests/ host Z80 harness against a
synthetic FAT12 image; read_sector/write_sector are trapped (modelled zero-cost),
so this separates CPU work (Z80 instructions executed) from disk work (sector I/O).
On real MSX hardware elapsed ~= steps*t_cpu + io*t_sector, t_sector (floppy, ~ms) >>
t_cpu (~us), so both columns are relevant and both drop with the M29 cursor.

  --shape       : I/O vs workload for the CURRENT (working-tree) ROM (spec §1).
  --before-after: CPU steps + I/O, baseline ROM vs current ROM (spec §1.1). The
                  baseline is built from a git ref (default: the commit BEFORE the
                  one that introduced the cursor) so the comparison is reproducible.

CLEAN-ROOM: our own routine, our own synthetic image, published WRBLK contract.
"""
from __future__ import annotations
import argparse, os, struct, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import test_wrblk_body_e2e as E   # Disk, n83, build(); harness geometry globals
from msxtest import Machine

SECSIZE = 512; FATSTART = 1; NUMFATS = 1; EOC = 0xFFF
_SENTINEL = 0xFFFE
DEFAULT_BASELINE_REF = "6535a59"   # M28, immediately before M29's cursor


def build_rom(ref: str | None) -> tuple[str, str]:
    """Assemble disk.rom+sym. ref=None -> working tree; else that git ref."""
    fd_rom, rom = tempfile.mkstemp(suffix=".rom"); os.close(fd_rom)
    sym = rom[:-4] + ".sym"
    if ref is None:
        src_disk = os.path.join(ROOT, "disk")
    else:
        d = tempfile.mkdtemp(prefix=f"wrblk_perf_{ref}_")
        tar = subprocess.run(["git", "archive", ref, "disk"], cwd=ROOT,
                             stdout=subprocess.PIPE, check=True).stdout
        subprocess.run(["tar", "-x", "-C", d], input=tar, check=True)
        src_disk = os.path.join(d, "disk")
    subprocess.run(["pasmo", "-I", src_disk, "--bin",
                    os.path.join(src_disk, "disk.asm"), rom, sym],
                   check=True, stderr=subprocess.DEVNULL)
    return rom, sym


def _geom(fat_sectors, total):
    E.FAT_SECTORS = fat_sectors; E.SECPERFAT = fat_sectors
    E.FIRSTROOT = FATSTART + NUMFATS * fat_sectors
    E.ROOTSECS = 1; E.FIRSTDATA = E.FIRSTROOT + E.ROOTSECS
    E.TOTAL_CLUSTERS = total


def _counted_call(m, name, **regs):
    """Machine.call, additionally counting CPU steps and trapped-I/O hits."""
    cpu = m.cpu
    for k, v in regs.items():
        setattr(cpu, k, v)
    cpu.sp = 0xF380; cpu.push(_SENTINEL); cpu.pc = m.sym[name]
    steps = io = 0
    io_pcs = {m.sym.get("read_sector"), m.sym.get("write_sector")}
    while cpu.pc != _SENTINEL:
        fn = m.traps.get(cpu.pc)
        if fn is not None:
            if cpu.pc in io_pcs:
                io += 1
            fn(m); cpu.pc = cpu.pop(); continue
        cpu.step(); steps += 1
        if steps > 80_000_000:
            raise RuntimeError(f"runaway PC={cpu.pc:#06x}")
    return steps, io, cpu.a


def _run(rom, sym, prefill_clusters, nrec, rs=128, extend=False):
    """ONE wrblk_body call writing nrec sequential 128B records. extend=False =>
    within an already-allocated prefill_clusters file (isolates positioning)."""
    total = prefill_clusters + nrec // 4 + 8
    fat_sectors = (total * 3 // 2 + SECSIZE) // SECSIZE
    _geom(fat_sectors, total)
    chain = [(2 + i, 2 + i + 1) for i in range(prefill_clusters - 1)]
    chain.append((2 + prefill_clusters - 1, EOC))
    disk = E.Disk("DATA.BIN", first_cluster=2, size=prefill_clusters * SECSIZE,
                  chain_links=chain)
    m = Machine(rom, sym, rom_base=0x4000); disk.install(m)   # disk.rom is a page-1 image
    m.trap("fat_total_clusters", lambda mm: setattr(mm.cpu, "de", total))
    FCB = 0xDA40
    m.poke(FCB, bytes(37)); m.poke(FCB + 1, E.n83("DATA.BIN"))
    m.poke_w(FCB + 14, rs)
    start = prefill_clusters * 4 if extend else 0
    m.poke(FCB + 33, struct.pack("<I", start)[:3])
    m.poke_w(m.addr("DOS_DTAPTR"), 0xC000)
    for i in range(min(nrec, 16)):
        m.poke(0xC000 + i * 128, bytes([0x40 + (i & 0x3F)] * 128))
    return _counted_call(m, "wrblk_body", de=FCB, hl=nrec)


def shape():
    rom, sym = build_rom(None)
    print("CURRENT ROM — sector reads for ONE wrblk_body call of N records "
          "within a 64-cluster file (within-EOF; isolates positioning):\n")
    print(f"{'N':>5} {'reads':>8} {'reads/N':>8}")
    for n in (16, 32, 64, 128, 256):
        _s, io, a = _run(rom, sym, 64, n)
        assert a == 0
        print(f"{n:>5} {io:>8} {io / n:>8.2f}")


def before_after(ref):
    b_rom, b_sym = build_rom(ref)
    m_rom, m_sym = build_rom(None)
    print(f"BEFORE ({ref}) vs AFTER (working tree) — ONE wrblk_body call, N "
          f"sequential 128B records within a 64-cluster file:\n")
    print(f"{'N':>4}  {'CPU(base)':>11} {'io':>6}   {'CPU(m29)':>10} {'io':>6}   "
          f"{'CPUx':>6} {'iox':>5}")
    for n in (16, 32, 64, 128, 256):
        bs, bio, ba = _run(b_rom, b_sym, 64, n)
        ms, mio, ma = _run(m_rom, m_sym, 64, n)
        assert ba == 0 and ma == 0, f"A base={ba} m29={ma}"
        print(f"{n:>4}  {bs:>11,} {bio:>6}   {ms:>10,} {mio:>6}   "
              f"{bs / ms:>5.1f}x {bio / mio:>4.1f}x")


def alloc_before_after(ref):
    """M30: ALLOCATION-bound before/after. ONE wrblk_body call extending a file
    by K new clusters (records written PAST EOF, so each new cluster is claimed
    by fat_alloc_cluster) on a disk whose free region starts 64 clusters in.
    Isolates the allocator: pre-M30 each of the K allocations rescans from
    cluster 2 (O(K^2)); M30 scans from the per-operation hint (O(K)). Positioning
    (M29) is identical in both, so the delta is purely the allocator."""
    b_rom, b_sym = build_rom(ref)
    m_rom, m_sym = build_rom(None)
    print(f"BEFORE ({ref}) vs AFTER (working tree) — ONE wrblk_body call "
          f"extending a 64-cluster file by K new clusters (allocation-bound):\n")
    print(f"{'K':>4}  {'CPU(base)':>11} {'io':>6}   {'CPU(cur)':>10} {'io':>6}   "
          f"{'CPUx':>6} {'iox':>5}")
    for k in (1, 2, 4, 8, 16, 32):
        bs, bio, ba = _run(b_rom, b_sym, 64, k * 4, extend=True)
        ms, mio, ma = _run(m_rom, m_sym, 64, k * 4, extend=True)
        assert ba == 0 and ma == 0, f"A base={ba} cur={ma}"
        print(f"{k:>4}  {bs:>11,} {bio:>6}   {ms:>10,} {mio:>6}   "
              f"{bs / ms:>5.1f}x {bio / mio:>4.1f}x")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shape", action="store_true")
    ap.add_argument("--before-after", action="store_true")
    ap.add_argument("--alloc", action="store_true",
                    help="M30 allocation-bound before/after (isolates fat_alloc_cluster)")
    ap.add_argument("--baseline-ref", default=DEFAULT_BASELINE_REF)
    args = ap.parse_args()
    E.build()   # ensure the tests harness's own ROM path exists (imports)
    if args.shape:
        shape()
    if args.alloc:
        alloc_before_after(args.baseline_ref)
    if args.before_after or not (args.shape or args.before_after or args.alloc):
        before_after(args.baseline_ref)
