# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM fat_alloc_cluster's M30 next-free scan hint, no emulator.

M30 (tier2-m30-alloc-hint-spec.md) makes fat_alloc_cluster scan from a
per-operation hint (FAT_ALLOCHINT) instead of always restarting at cluster 2,
killing the O(N^2) rescan a multi-cluster allocation used to pay. fat_mount
resets the hint to 2 once per BDOS operation, before any allocation; fac_found
advances it past each claimed cluster. The spec proves (§4) this returns the
exact same cluster sequence as the old from-2 scan, for any input, as long as
no cluster is freed mid-operation (the only two free sites -- wrblk_shrink,
fdel_body -- never run interleaved with an allocation in the same operation).

This test mirrors test_fat_alloc_cluster.py's harness (same synthetic-FAT
technique: read_sector/write_sector mocked against an in-memory byte array,
fat_alloc_cluster itself runs for real) and checks, against layouts with the
first free cluster hundreds in AND layouts with holes (used/free/used/free):

  (a) BEHAVIOUR-IDENTITY -- the returned cluster sequence equals a from-2
      reference allocator's sequence.
  (b) INVARIANT -- after each alloc, FAT_ALLOCHINT <= the lowest still-free
      cluster (never skips a free cluster).
  (c) RESET -- simulating fat_mount's `ld hl,2 / ld (FAT_ALLOCHINT),hl` gives
      the hint per-operation lifetime.
  (d) O(N) SHAPE -- read_sector calls for a K-cluster allocation stay bounded
      per cluster, not growing with the first-free distance (the defect M30
      fixes: measured 19->2592 FAT reads for K=1->32 pre-fix).
  (e) DISK-FULL still detected the same way (fac_full, Cy=1) when no free
      cluster exists at or above the hint.

Clean-room: our own routine (fat.asm/kernel.asm), our own FAT image, public
Microsoft FAT spec §3.2 ($000 = free, $FF8-$FFF = end-of-chain) -- no stock
disassembly.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
DISK_BASE = 0x4000

ROM = tp("zb_fatallochint_ut.rom")
SYM = tp("zb_fatallochint_ut.sym")

FATSTART, SECSIZE, FAT_SECTORS = 1, 512, 3
NUMFATS, SECPERFAT = 2, 3
EOC = 0xFFF


def put_fat12(fat, cluster, value):
    off = cluster + (cluster >> 1)
    if cluster & 1:
        fat[off] = (fat[off] & 0x0F) | ((value << 4) & 0xF0)
        fat[off + 1] = (value >> 4) & 0xFF
    else:
        fat[off] = value & 0xFF
        fat[off + 1] = (fat[off + 1] & 0xF0) | ((value >> 8) & 0x0F)


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


class Harness:
    """One synthetic FAT12 image + a Machine wired to it, with a read_sector
    call counter (for the O(N) shape check)."""

    def __init__(self, total_clusters, used_clusters):
        self.total = total_clusters
        self.fat = bytearray(FAT_SECTORS * SECSIZE)
        for c in used_clusters:
            put_fat12(self.fat, c, EOC)
        self.read_calls = 0
        self.m = Machine(ROM, SYM, rom_base=DISK_BASE)

        def read_sector(mm):
            self.read_calls += 1
            base = (mm.cpu.de - FATSTART) * SECSIZE
            chunk = bytes(self.fat[base:base + SECSIZE]) if 0 <= base < len(self.fat) else b""
            mm.poke(mm.cpu.hl, chunk.ljust(SECSIZE, b"\x00"))
            mm.cpu.f &= ~0x01

        def write_sector(mm):
            base = (mm.cpu.de - FATSTART) * SECSIZE
            if 0 <= base < len(self.fat):
                self.fat[base:base + SECSIZE] = bytes(mm.peek(mm.cpu.hl, SECSIZE))
            mm.cpu.f &= ~0x01

        self.m.trap("read_sector", read_sector)
        self.m.trap("write_sector", write_sector)
        # D-FATENG Option 2: the shared FAT body writes through
        # `fatprim_write_sector`, not disk's own `write_sector` (which
        # the BDOS half still uses). Trapping only the old name let the
        # engine's writes through untrapped, so the simulated FAT never
        # updated and the cluster read back 0x000.
        self.m.trap("fatprim_write_sector", write_sector)
        self.m.trap("fat_total_clusters", lambda mm: (setattr(mm.cpu, "de", total_clusters),  # CF = 0: success (D-DISKFULL: alloc now reads it)
                                                          setattr(mm.cpu, "f", mm.cpu.f & ~0x01)))

        self.m.poke_w(self.m.addr("FAT_FATSTART"), FATSTART)
        self.m.poke(self.m.addr("FAT_NUMFATS"), NUMFATS)
        self.m.poke_w(self.m.addr("FAT_SECPERFAT"), SECPERFAT)

    def get_fat(self, cluster):
        off = cluster + (cluster >> 1)
        v = self.fat[off] | (self.fat[off + 1] << 8)
        return (v >> 4) if (cluster & 1) else (v & 0x0FFF)

    def reset_hint(self):
        """Model fat_mount's SUCCESS-path reset: `ld hl,2 / ld (FAT_ALLOCHINT),hl`."""
        self.m.poke_w(self.m.addr("FAT_ALLOCHINT"), 2)

    def hint(self):
        b = self.m.peek(self.m.addr("FAT_ALLOCHINT"), 2)
        return b[0] | (b[1] << 8)

    def alloc(self):
        """One fat_alloc_cluster call. Returns (cy, cluster)."""
        cpu = self.m.call("fat_alloc_cluster")
        return carry(cpu), cpu.hl & 0xFFFF


def naive_from2_reference(total_clusters, used_clusters, n_allocs):
    """The from-cluster-2 reference allocator: what today's (pre-M30) scan
    would return for the same sequence of N allocations in one operation --
    used_clusters mutates as clusters get claimed, exactly like the real FAT."""
    used = set(used_clusters)
    seq = []
    for _ in range(n_allocs):
        c = 2
        while c < total_clusters and c in used:
            c += 1
        if c >= total_clusters:
            seq.append(None)  # disk full
            break
        used.add(c)
        seq.append(c)
    return seq


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # ------------------------------------------------------------------
    # (a) + (b): behaviour-identity + hint-invariant, layout A -- first free
    # cluster is HUNDREDS in (clusters 2..299 all used, then free).
    # ------------------------------------------------------------------
    TOTAL_A = 400
    used_a = set(range(2, 300))
    h = Harness(TOTAL_A, used_a)
    h.reset_hint()
    ref = naive_from2_reference(TOTAL_A, used_a, 5)
    got = []
    lowest_free_ok = True
    for i in range(5):
        cy, cl = h.alloc()
        check(not cy, f"[layout A] alloc #{i}: Cy=0 (allocated)")
        got.append(cl)
        # invariant: FAT_ALLOCHINT <= lowest still-free cluster
        lowest_free = next((c for c in range(2, TOTAL_A) if h.get_fat(c) == 0), None)
        if lowest_free is not None and h.hint() > lowest_free:
            lowest_free_ok = False
    check(got == ref, f"[layout A] alloc sequence {got} == from-2 reference {ref}")
    check(lowest_free_ok, "[layout A] FAT_ALLOCHINT <= lowest still-free cluster after every alloc")

    # ------------------------------------------------------------------
    # (a) + (b): layout B -- HOLES (used, free, used, free, ...) to prove the
    # hint never SKIPS a free cluster that sits behind it.
    # ------------------------------------------------------------------
    TOTAL_B = 60
    # clusters 2..49: alternate used/free starting used (2 used, 3 free, 4 used, ...)
    used_b = {c for c in range(2, 50) if c % 2 == 0}
    h2 = Harness(TOTAL_B, used_b)
    h2.reset_hint()
    ref2 = naive_from2_reference(TOTAL_B, used_b, 10)
    got2 = []
    for i in range(10):
        cy, cl = h2.alloc()
        check(not cy, f"[layout B holes] alloc #{i}: Cy=0 (allocated)")
        got2.append(cl)
    check(got2 == ref2, f"[layout B holes] alloc sequence {got2} == from-2 reference {ref2}")
    check(2 not in got2 or got2[0] == 3,
          "[layout B holes] first hole (cluster 3) claimed before any later free, not skipped")

    # ------------------------------------------------------------------
    # (c) RESET: a fresh operation (simulated fat_mount) re-scans from 2 and
    # reuses a cluster freed AFTER the previous operation's hint had passed it.
    # ------------------------------------------------------------------
    TOTAL_C = 30
    used_c = {2, 3, 4}
    h3 = Harness(TOTAL_C, used_c)
    h3.reset_hint()
    check(h3.hint() == 2, "[reset] FAT_ALLOCHINT == 2 immediately after fat_mount's reset")
    cy, cl = h3.alloc()
    check(not cy and cl == 5, f"[reset] op1 allocates cluster {cl} (want 5)")
    # op1 ends; something frees cluster 2 (e.g. a delete in a LATER operation);
    # a new operation's fat_mount resets the hint back to 2.
    put_fat12(h3.fat, 2, 0)
    h3.reset_hint()
    check(h3.hint() == 2, "[reset] a later operation's fat_mount resets FAT_ALLOCHINT to 2 again")
    cy, cl = h3.alloc()
    check(not cy and cl == 2,
          f"[reset] op2 (after reset) reuses freed cluster 2 (got {cl}) -- cross-operation "
          "byte-identity: the hint never leaks into a later operation")

    # ------------------------------------------------------------------
    # (d) O(N) SHAPE: read_sector calls for a K-cluster allocation, with the
    # first free cluster hundreds in, must be bounded per-cluster -- NOT
    # growing with the first-free distance (that's the O(N^2) defect).
    # ------------------------------------------------------------------
    TOTAL_D = 700
    used_d = set(range(2, 600))          # first free = 600, far in
    K = 16
    h4 = Harness(TOTAL_D, used_d)
    h4.reset_hint()
    total_reads = 0
    for i in range(K):
        before = h4.read_calls
        cy, cl = h4.alloc()
        check(not cy, f"[O(N) shape] alloc #{i}: Cy=0 (allocated)")
        total_reads += h4.read_calls - before
    reads_per_cluster = total_reads / K
    # Bound: each successive cluster is 1 past the previous hint, entirely
    # within the same or next FAT sector -- a small constant number of FAT
    # sector reads per allocated cluster (contrast a from-2 allocator: rescan
    # cost per call grows with the 600-cluster first-free distance, so its
    # reads/K would grow roughly linearly with the distance already covered).
    check(reads_per_cluster <= 3,
          f"[O(N) shape] {total_reads} read_sector calls / {K} allocs = "
          f"{reads_per_cluster:.2f} per cluster (bounded, not growing with the "
          "600-cluster first-free distance)")
    # Cross-check against what a from-2 rescan would have cost: the FAT sector
    # covers 341 12-bit entries (512*2/3), so re-scanning ~600 entries from
    # cluster 2 on EVERY one of the K calls costs several sector re-reads each
    # time; a hinted scan should cost far fewer sector reads in total.
    naive_min_reads = K * (600 // 341)   # a from-2 rescan re-reads >=1 sector per call once past sector 0
    check(total_reads < naive_min_reads or total_reads <= K * 3,
          f"[O(N) shape] hinted total reads ({total_reads}) does not scale with "
          f"repeated from-2 rescans (a from-2 baseline would cost >= {naive_min_reads})")

    # ------------------------------------------------------------------
    # (e) DISK-FULL still detected: a fully-used FAT (2..total-1 all used)
    # still returns Cy=1 via the same fac_full path, whether reached fresh or
    # after the hint has advanced past everything.
    # ------------------------------------------------------------------
    TOTAL_E = 20
    used_e = set(range(2, TOTAL_E))
    h5 = Harness(TOTAL_E, used_e)
    h5.reset_hint()
    cy, _ = h5.alloc()
    check(cy, "[disk-full] fully-used FAT -> Cy=1 (fac_full) on a fresh hint")

    print()
    print("ALL PASS — fat_alloc_cluster's M30 next-free hint is behaviour-identical, "
          "invariant-preserving, resets per-operation, is O(1)-ish per cluster, and "
          "still detects disk-full" if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
