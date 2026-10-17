# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: fat_rand_put's sector overlay, INCLUDING the straddle — no emulator.

`fat_rand_put` overlays a record into `FWBUF + GP_WITHIN` with ONE `ldir`. When
`within + reclen > 512` that runs PAST the 512-byte buffer: record 6 at r=100
has within=500, so 88 bytes land beyond FWBUF. `oo_parse_reclen`'s power-of-two
rule exists to make that unreachable, and this file is what will let it open.

🔴 WHY A HOST TEST AND NOT EMULATOR ROWS. D-RECLEN2 tried this widening on
2026-08-30 and its rows were blind TWICE:

  * **a round-trip cannot see a wrong offset**, because `PUT` and `GET` share
    it — write to the wrong place, read from the same wrong place, get the bytes
    back [[a-coverage-row-whose-geometry-cannot-reach-the-case]];
  * `mul_reclen` was a SHIFT, so record 6 sat at within=320 and the row that was
    supposed to straddle never straddled (fixed 2026-09-06, D-MULREC).

The cure for the first is to build the expected sector image INDEPENDENTLY in
Python and compare bytes. That needs no emulator and no disk, and no shared
offset can fool it.

🎯 AND THE ROW THAT MATTERS IS THE ONE NOBODY ASKS ABOUT. The overrun's damage
lands in memory past FWBUF — not in the record being written, whose own
round-trip stays perfectly green. `mem_above_fwbuf_clean` is therefore a claim
about the ENGINE, not about the disk, and it is what the emulator cannot make.

`frnd_locate` is trapped to make GP_PHYS a function of GP_SEC, isolating the
overlay from the cluster walk exactly as test_fat_read_file_sector.py isolates
the address math from `fat_advance`. read_sector / fatprim_write_sector serve and
capture a virtual disk.

🧭 S10.D (2026-10-15): THE ENGINE IS disk.rom's NOW (disk/kernel.asm hk_dget, the
record I/O behind H_DGET), so this drives the DISK image at $4000 -- it drove the
sub image while the engine was the sub-ROM's randio tenant. Two contract changes
come with it, and the rows are unchanged by both: the file's size is the
channel's FCB row (+16..19, IX), not main's FWR_BYTES; and GP_FLAGS is set by
hk_dget, not by the engine (frnd_locate is trapped here, so nothing reads it).

🏗️ D-FLDDESC (2026-10-17): THE RECORD IS THE CHANNEL BLOCK'S +9 NOW, not
FSECTOR_BUF -- the engine reaches it through the row's cached block address
(ROW + DOUT_BLK, rnd_rec), as the CF-3300 keeps it and as FIELD points a
variable's descriptor into it. So the fixture plants a block (BLK) in the row and
seeds / reads the record at BLK + FCH_HDRSZ; the sector images are unchanged.

Clean-room: our own routines (disk/kernel.asm, disk/fat.asm), public FAT sector
geometry.
"""

import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

DISK_BASE = 0x4000
SECSIZE = 512
DISK_ROM, DISK_SYM = tp("rand_straddle_disk.rom"), tp("rand_straddle_disk.sym")
PHYS0 = 100                     # GP_PHYS = PHYS0 + GP_SEC, under the trap
ROW = 0xD000                    # the channel's FCB row (IX): +16..19 = the size
BLK = 0xC000                    # the channel's 265 B block (ROW + DOUT_BLK caches it)
REC = BLK + 9                   # its record, block + FCH_HDRSZ (D-FLDDESC)


def build():
    subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", DISK_ROM, DISK_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def set_size(m, size):
    """The file's size, where the engine reads it: the FCB row's +16..19."""
    m.poke(ROW + 16, size.to_bytes(4, "little"))


def rec_bytes(recno, reclen):
    """A pattern unique per (record, offset) so a mis-placed byte is visible."""
    return bytes(((recno * 7 + i) & 0xFF) for i in range(reclen))


def model_put(disk, recno, reclen):
    """The expected sector image, derived from the LAYOUT and never from the ROM.

    Record N occupies file bytes [(N-1)*r, N*r); byte B lives in sector B >> 9 at
    offset B & 511. A record whose span crosses a multiple of 512 therefore
    touches TWO sectors, which is the whole subject.
    """
    data = rec_bytes(recno, reclen)
    base = (recno - 1) * reclen
    for i, b in enumerate(data):
        off = base + i
        disk.setdefault(PHYS0 + (off >> 9), bytearray(b" " * SECSIZE))[off & 511] = b


def make_machine(disk):
    m = Machine(DISK_ROM, DISK_SYM, rom_base=DISK_BASE)

    def frnd_locate(mm):
        sec = mm.mem[mm.sym["GP_SEC"]] | (mm.mem[mm.sym["GP_SEC"] + 1] << 8)
        mm.poke_w(mm.sym["GP_PHYS"], PHYS0 + sec)
        mm.cpu.f &= ~0x01                       # Cy = 0: located

    def read_sector(mm):
        sec = mm.cpu.de
        mm.poke(mm.cpu.hl, bytes(disk.get(sec, bytearray(b" " * SECSIZE))))
        mm.cpu.f &= ~0x01

    def write_sector(mm):
        disk[mm.cpu.de] = bytearray(mm.peek(mm.cpu.hl, SECSIZE))
        mm.cpu.f &= ~0x01

    m.trap("frnd_locate", frnd_locate)
    m.trap("read_sector", read_sector)
    # D-FATENG Option 2: the shared FAT body writes through
    # `fatprim_write_sector`, not disk's own `write_sector` (the kernel's, which
    # the BDOS half still uses and which maps no DSKIO code) -- and so does the
    # record engine since S10.D. Trapping only the old name would let the
    # engine's writes through untrapped.
    m.trap("fatprim_write_sector", write_sector)
    # the directory stamp is a separate concern with its own tests
    m.trap("fat_dir_update", lambda mm: mm.cpu.__setattr__("f", mm.cpu.f & ~0x01))
    # D-FLDDESC: the row caches the channel's block; the record is its +9
    m.poke_w(ROW + m.sym["DOUT_BLK"], BLK)
    assert m.sym["FCH_RECMAX"] == 256 and REC - BLK == 9
    return m


def run():
    build()
    fails = 0

    def report(label, ok, detail=""):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:52}" + ("" if ok else f"   {detail}"))

    CHAN = 1
    GUARD = 64                  # bytes ABOVE FWBUF+512 that must stay untouched

    # D-PUTU32 (2026-09-10): records whose byte offset needs more than 16 bits.
    # (256, 257) is offset 65536 -- sector 128, within 0 -- the exact boundary the
    # CF-3300 serves and the 16-bit mul_reclen wrapped to 0; (1, 65535) is the
    # largest record number the evaluator hands over, offset 65534.
    for reclen, recno, straddles in [(256, 1, False), (256, 2, False), (256, 3, False),
                                     (256, 257, False), (1, 65535, False), (256, 300, False),
                                     (100, 1, False), (100, 5, False),
                                     (100, 6, True), (100, 7, False),
                                     (7, 74, True), (255, 3, True)]:
        disk = {}
        want = {}
        m = make_machine(disk)
        s = m.sym
        fwbuf = s["FWBUF"]
        m.poke(fwbuf + SECSIZE, b"\xA5" * GUARD)          # the overrun witness
        m.poke(s["FCH_ACTIVE"], CHAN)
        m.poke_w(s["FCH_RECLENS"] + CHAN * 2, reclen)
        m.poke_w(s["GP_RECNO"], recno)
        set_size(m, 0)
        m.poke(REC, rec_bytes(recno, reclen))
        model_put(want, recno, reclen)

        m.call("fat_rand_put", ix=ROW)

        tag = f"r={reclen} rec={recno}" + ("  [STRADDLE]" if straddles else "")
        # 🔴 THE GUARD HAS TO EXCLUDE THE CELLS THE ROUTINE LEGITIMATELY
        # WRITES, or it flags every row and says nothing. The sub-ROM engine's
        # `frnd_update_size` stored FWR_BYTES and FAT_FILESIZE, and BOTH sat above
        # FWBUF+512 (offsets 51 and 14) — the first cut of this guard reported "8
        # of 64 clobbered" on rows with no straddle at all, which is an instrument
        # result read as a machine one [[an-unnamed-outcome-reads-as-no-outcome]].
        # Since S10.D it writes the FCB row and dout_mirror's two MAIN cells;
        # every one of them is excluded by address, wherever it falls.
        legit = set()
        for name, width in (("main_FAT_FILESIZE", 4), ("main_FWR_BYTES", 4),
                            ("FCH_RECNOS", 32)):
            for k in range(width):
                legit.add(s[name] - (fwbuf + SECSIZE) + k)
        for k in range(50):
            legit.add(ROW - (fwbuf + SECSIZE) + k)
        got_guard = bytes(m.peek(fwbuf + SECSIZE, GUARD))
        clob = [i for i, b in enumerate(got_guard) if b != 0xA5 and i not in legit]
        report(f"{tag}: nothing written above FWBUF+512", not clob,
               f"{len(clob)} of {GUARD} guard bytes clobbered, first at +{clob[0]}"
               if clob else "")
        for sec, exp in sorted(want.items()):
            got = disk.get(sec)
            if got is None:
                report(f"{tag}: sector {sec - PHYS0} written", False, "sector absent")
                continue
            bad = [i for i in range(SECSIZE) if got[i] != exp[i]]
            report(f"{tag}: sector {sec - PHYS0} matches the model", not bad,
                   f"{len(bad)} byte(s) differ, first at offset {bad[0]}" if bad else "")

    # 🎯 THE ADJACENCY ROW: write the straddling record LAST and require both
    # NEIGHBOURS to survive. This is the property docs/spec-basic-put3.md §2
    # measured on the CF-3300, and the one a round-trip of record 6 alone cannot
    # make -- damage from a wrong offset lands on a record nobody asked about.
    disk, want = {}, {}
    m = make_machine(disk)
    s = m.sym
    m.poke(s["FCH_ACTIVE"], CHAN)
    m.poke_w(s["FCH_RECLENS"] + CHAN * 2, 100)
    set_size(m, 0)
    for recno in (5, 7, 6):
        m.poke_w(s["GP_RECNO"], recno)
        m.poke(REC, rec_bytes(recno, 100))
        m.call("fat_rand_put", ix=ROW)
        model_put(want, recno, 100)
    for sec, exp in sorted(want.items()):
        got = disk.get(sec)
        bad = [] if got is None else [i for i in range(SECSIZE) if got[i] != exp[i]]
        report(f"adjacency r=100 recs 5,7 then 6: sector {sec - PHYS0} intact",
               got is not None and not bad,
               "sector absent" if got is None else
               (f"{len(bad)} byte(s) differ, first at offset {bad[0]}" if bad else ""))

    # 🎯 THE READ SIDE, AND IT NEEDS ITS OWN ROWS FOR THE SAME REASON. A GET's
    # failure is a wrong ANSWER rather than corruption -- the old single `ldir`
    # copied a straddling record's tail out of the bytes ABOVE FWBUF -- and a
    # PUT-then-GET round trip cannot see it, because both used the same offset.
    # So the disk here is built by the MODEL, never by fat_rand_put, and the
    # record read back is compared against the pattern the model laid down.
    for reclen, recno in ((256, 1), (100, 5), (100, 6), (7, 74), (255, 3)):
        disk = {}
        # ⚠️ MODEL THE RECORD BEING READ AND ITS NEIGHBOURS, not a fixed 1..11:
        # the first cut laid down records 1..11 and then asked for record 74, so
        # `GET r=7 rec=74` read bytes the model had never written and reported
        # "7 byte(s) differ" — a fault in the FIXTURE presented as one in the
        # engine [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
        for r in (recno - 1, recno, recno + 1):
            if r >= 1:
                model_put(disk, r, reclen)
        m = make_machine(disk)
        s = m.sym
        m.poke(s["FCH_ACTIVE"], CHAN)
        m.poke_w(s["FCH_RECLENS"] + CHAN * 2, reclen)
        m.poke_w(s["GP_RECNO"], recno)
        set_size(m, 0xFFFF)                       # far past the record: never EOF
        m.poke(REC, b"\x00" * reclen)
        m.call("fat_rand_get", ix=ROW)
        got = bytes(m.peek(REC, reclen))
        exp = rec_bytes(recno, reclen)
        bad = [i for i in range(reclen) if got[i] != exp[i]]
        straddle = " [STRADDLE]" if ((recno - 1) * reclen) // SECSIZE \
            != (recno * reclen - 1) // SECSIZE else ""
        report(f"GET r={reclen} rec={recno}{straddle}: reads the record back",
               not bad,
               f"{len(bad)} byte(s) differ, first at offset {bad[0]}" if bad else "")

    # 🎯 THE CHAIN WALK'S DIVISION, PAST 128 KB (S10.D). The sub-ROM's
    # frnd_locate divided GP_SEC by sectors-per-cluster on its LOW BYTE only, so
    # file sector 300 walked to cluster index 22 instead of 150. Every row above
    # traps frnd_locate, so none of them can see it; this one runs it for real
    # over a contiguous chain (frnd_next: cluster + 1) and checks GP_PHYS against
    # FIRSTDATA + (cluster - 2) * spc + sector-in-cluster, derived here.
    for spc, sec in ((2, 0), (2, 1), (2, 255), (2, 300), (2, 1439), (1, 300)):
        m = Machine(DISK_ROM, DISK_SYM, rom_base=DISK_BASE)
        s = m.sym
        FIRST, FIRSTDATA = 2, 14
        m.poke(s["FAT_SECPERCLUS"], spc)
        m.poke_w(s["FAT_FIRSTDATA"], FIRSTDATA)
        m.poke_w(ROW + s["DOUT_FIRST"], FIRST)
        m.poke(s["GP_FLAGS"], 0)                  # GET: walk, never extend
        m.poke_w(s["GP_SEC"], sec)

        def next_clus(mm):
            mm.cpu.hl = (mm.cpu.hl + 1) & 0xFFFF
            mm.cpu.f &= ~0x01
        m.trap("frnd_next", next_clus)
        cpu = m.call("frnd_locate", ix=ROW)
        phys = m.mem[s["GP_PHYS"]] | (m.mem[s["GP_PHYS"] + 1] << 8)
        want = FIRSTDATA + (FIRST + sec // spc - 2) * spc + sec % spc
        report(f"frnd_locate spc={spc} GP_SEC={sec}: GP_PHYS",
               not (cpu.f & 1) and phys == want,
               f"got {phys} (CF={cpu.f & 1}), want {want}")

    print()
    print("ALL PASS — a straddling record writes both sectors and damages neither "
          "neighbour" if not fails else f"{fails} CHECK(S) FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
