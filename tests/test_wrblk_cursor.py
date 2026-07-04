# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: M29 wrblk_position_ext incremental position cursor, no emulator.

tier2-m29-wrblk-position-cursor-spec.md: the pre-M29 wrblk_position_ext
re-fat_open'd and re-walked the chain from the head on EVERY record, making a
sequential N-record WRBLK O(N^2) in sector reads. M29 keeps a cursor
(WRBLK_CURVALID/WRBLK_CURSEC) across calls within one wrblk_body invocation so
a same-sector call (3 of every 4 records, given the 4-records/512B-sector
convention) needs NO positioning I/O at all, and a next-sector call advances
by exactly one step instead of re-walking from the start.

This test asserts BOTH halves of the spec's invariant (§4/§6):
  (a) correctness is unchanged -- the resulting dirent/FAT chain/record bytes
      are exactly what the same inputs have always produced (cross-checked
      against test_wrblk_body_e2e.py's known-good shapes).
  (b) the I/O shape is now O(N): counting read_sector calls, a same-sector
      run of records incurs ZERO extra positioning reads after the first, and
      a multi-cluster sequential extend does not re-walk the chain from the
      head on every record.

Harness: reuses tests/test_wrblk_body_e2e.py's Disk/Machine setup (imported,
not duplicated) -- only read_sector is wrapped further here to COUNT calls
without changing its behaviour.

Clean-room: our own routine (kernel.asm), our own synthetic disk image, the
published RANDOM BLOCK WRITE contract (map.grauw.nl) -- no stock disassembly.
See disk/docs/tier2-m29-wrblk-position-cursor-spec.md.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from test_wrblk_body_e2e import (  # noqa: E402
    Disk, EOC, FCB, SECSIZE, build, get_fat12, n83, new_machine, setup_fcb,
)


def install_counting(disk, m):
    """Like Disk.install, but wraps read_sector to count calls (without
    changing behaviour) so the test can assert on I/O shape."""
    disk.install(m)
    counts = {"reads": 0, "read_secs": []}
    orig_read = m.traps[m.addr("read_sector")]

    def counting_read(mm):
        counts["reads"] += 1
        counts["read_secs"].append(mm.cpu.de)
        orig_read(mm)

    m.trap("read_sector", counting_read)
    return counts


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # === (a) correctness: within-EOF sequential write of all 4 records of a
    # single 512-byte sector -- must land identically to writing them one at a
    # time the old way (each call's data is independent per record slot, so
    # the reference is simply "each record's 128 bytes at its slot").
    m = new_machine()
    disk = Disk("DATA.BIN", first_cluster=5, size=512, chain_links=[(5, EOC)])
    counts = install_counting(disk, m)
    setup_fcb(m, "DATA.BIN", rs=128, rr=0)
    patterns = [bytes([0xB0 + i] * 128) for i in range(4)]
    dta = 0xC000
    for i, pat in enumerate(patterns):
        m.poke(dta + i * 128, pat)
    cpu = m.call("wrblk_body", de=FCB, hl=4)
    check(cpu.a == 0, f"sequential same-sector 4-record write: A={cpu.a} (want 0)")
    base = (5 - 2) * SECSIZE
    for i, pat in enumerate(patterns):
        got = bytes(disk.data[base + i * 128: base + i * 128 + 128])
        check(got == pat, f"  record {i}'s 128 bytes landed correctly")
    r0, r1, r2 = m.peek(FCB + 33, 3)
    check((r0, r1, r2) == (4, 0, 0), f"  RR advanced to {(r0,r1,r2)} (want (4,0,0))")
    cluster, size = disk.dirent()
    check(size == 512, f"  dirent size unchanged at {size} (within EOF)")
    # --- (b) I/O shape: all 4 records share ONE 512B sector. Fixed overhead
    # unrelated to positioning: fat_mount's boot-sector read (1) + fat_find's
    # root-dir read (1) + fat_dir_update's own re-read/rewrite of the dir
    # sector at the end (1 read) = 3 reads, constant regardless of record
    # count. The POSITIONING work itself must read the data sector at most
    # ONCE for all 4 records (wpe_same elides the other 3 -- no re-walk-from-
    # head per record, which pre-M29 would have re-read it 4 times = 1+2+3+4
    # positioning reads instead of 1).
    data_sector = (5 - 2) + 4  # FIRSTDATA + (cluster-2), per this Disk's geometry
    data_reads = counts["read_secs"].count(data_sector)
    check(data_reads == 1,
          f"  data sector read {data_reads}x across 4 same-sector records (want 1x, not 4x)")
    check(counts["reads"] <= 4,
          f"  total read_sector calls = {counts['reads']} (want <=4: boot+dir+data+dirupdate, "
          f"NOT growing with record count)")

    # === multi-cluster sequential extend: 1 sector/cluster file, write 12
    # consecutive 128B records (=3 sectors=3 clusters) past EOF from an empty
    # file, one record per wrblk_body call (worst case for the OLD from-head
    # re-walk: call k would have re-walked k steps, O(N^2) total).
    NREC = 12
    m = new_machine()
    disk = Disk("DATA.BIN", first_cluster=0, size=0, chain_links=[])
    counts = install_counting(disk, m)
    total_reads = 0
    for i in range(NREC):
        setup_fcb(m, "DATA.BIN", rs=128, rr=i)
        pat = bytes([0x40 + i] * 128)
        m.poke(0xC000, pat)
        cpu = m.call("wrblk_body", de=FCB, hl=1)
        check(cpu.a == 0, f"  extend record {i}: A={cpu.a} (want 0)")
        total_reads += counts["reads"]
        counts["reads"] = 0
    # Correctness: walk the resulting chain and verify every record's bytes.
    cluster, size = disk.dirent()
    check(size == NREC * 128, f"final size = {size} (want {NREC * 128})")
    chain = []
    c = cluster
    while c < 0x0FF8 and c != 0:
        chain.append(c)
        c = get_fat12(disk.fat, c)
    check(len(chain) == 3, f"chain length = {len(chain)} (want 3, 1 sector/cluster, 4 rec/sector)")
    for i in range(NREC):
        clus = chain[i // 4]
        slot = i % 4
        base = (clus - 2) * SECSIZE + slot * 128
        got = bytes(disk.data[base: base + 128])
        want = bytes([0x40 + i] * 128)
        check(got == want, f"  record {i} bytes correct in cluster {clus} slot {slot}")
    # I/O shape: with the cursor, each wrblk_body call is now a FRESH call (new
    # invocation -> WRBLK_CURVALID reset to 0), so each one still does its own
    # single from-head walk -- that per-call walk is the accepted O(1)-per-call
    # (amortized) shape from the spec, NOT the fix target. The fix target is
    # MULTIPLE records within the SAME wrblk_body call, exercised below. Sanity
    # bound here: total reads across all N separate calls must stay LINEAR in N
    # (each call's own fixed overhead -- boot+dir+dirupdate -- is constant per
    # call, so N calls cost O(N), never O(N^2)).
    check(total_reads <= NREC * 8,
          f"  total read_sector across {NREC} separate calls = {total_reads} "
          f"(want <= {NREC * 8}, linear in N)")

    # === the spec's headline case: ONE wrblk_body call writing many sequential
    # records spanning multiple clusters (the actual O(N^2) -> O(N) fix site).
    NREC2 = 16  # 4 clusters worth, 1 sector/cluster, 4 records/sector
    m = new_machine()
    disk = Disk("DATA.BIN", first_cluster=0, size=0, chain_links=[])
    counts = install_counting(disk, m)
    setup_fcb(m, "DATA.BIN", rs=128, rr=0)
    for i in range(NREC2):
        m.poke(0xC000 + i * 128, bytes([0x80 + i] * 128))
    cpu = m.call("wrblk_body", de=FCB, hl=NREC2)
    check(cpu.a == 0, f"single-call {NREC2}-record multi-cluster extend: A={cpu.a} (want 0)")
    cluster, size = disk.dirent()
    check(size == NREC2 * 128, f"  final size = {size} (want {NREC2 * 128})")
    chain = []
    c = cluster
    while c < 0x0FF8 and c != 0:
        chain.append(c)
        c = get_fat12(disk.fat, c)
    check(len(chain) == 4, f"  chain length = {len(chain)} (want 4)")
    for i in range(NREC2):
        clus = chain[i // 4]
        slot = i % 4
        base = (clus - 2) * SECSIZE + slot * 128
        got = bytes(disk.data[base: base + 128])
        want = bytes([0x80 + i] * 128)
        check(got == want, f"  record {i} bytes correct")
    # O(N) shape assertion: pre-M29, wrblk_position_ext re-fat_open'd and
    # re-walked from the head for EVERY one of the 16 records, so positioning
    # alone would cost sum_{k=1}^{16} k = 136 data-sector reads (the O(N^2)
    # this spec fixes), on top of the fixed boot/dir/dirupdate/alloc-scan
    # overhead. Post-M29, each of the 4 clusters is visited/read exactly ONCE
    # (3 records/cluster reuse it for free via wpe_same) -- linear in the
    # number of SECTORS touched (4), not records (16). Empirically (see the
    # spec's characterisation) this workload costs ~5 reads/new-sector
    # (1 FAT-alloc-scan read + 1 data read, plus fixed overhead); bound well
    # below the old quadratic total (136) to prove the fix landed.
    check(counts["reads"] <= 6 * 4 + 4,
          f"  total read_sector for one {NREC2}-record multi-cluster call = "
          f"{counts['reads']} (want <= {6 * 4 + 4}; O(N) not O(N^2) -- pre-M29 "
          f"this would be >= {sum(range(1, NREC2 + 1))})")

    print()
    print("ALL PASS — M29 wrblk_position_ext incremental cursor (correctness + O(N) I/O)"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
