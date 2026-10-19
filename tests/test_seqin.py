# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk.rom's INPUT-channel reader (hk_chin, H_CHIN $FE8A) -- no emulator.

🏗️ S10.C (D-ROMSIZE, 2026-10-15) moved the INPUT side of disk files into disk.rom:
the channel is an MSX-DOS FCB in its engine row (RS = 1, the random record the
byte offset past what has been loaded), its read-ahead the channel block's 256 B
record (+9, the position at +6), refilled through RDBLK's own k47b2_seek /
k47b2_nextbyte. The text rules moved with it from the sub-ROM's seqio tenant,
where the CF-3300 measured them (scratchpad/ipe_run*.out, inpnum_run2/3.out):

  R1  Ctrl-Z ($1A) is a SOFT end, never consumed; EOF() is -1 when it is next;
  R2  INPUT# / LINE INPUT# swallow the LF after a CR -- INPUT$ (FCH_RDMODE 2)
      does not;
  numeric INPUT # item: leading blanks / CR / LF skipped, the item ends at a
      blank, comma or CR, then blanks are eaten and ONE comma, or ONE CR with
      its LF -- any other byte is the NEXT item's and stays.

🎯 WHY A HOST TEST. The rows that can break are the ones at a RECORD BOUNDARY,
and a BASIC-level round trip rarely puts a CR, an LF or a numeric item exactly
there: a CR as byte 255 with its LF as byte 256 (the peek after the CR is what
refills), a number straddling 255/256, a file that is an exact multiple of 256
(the refill that must NOT happen at the end), and a read that fails mid-file
(D-LINEJECT: the code must be pending, not swallowed as an end). The disk is a
Python model laid down by OFFSET, never by the ROM, so a mis-placed byte or a
lost one is visible.

🏗️ S10.E (2026-10-19) added ops 6 LOF / 8 LOC to the same cell: a pure read of
the live channel's FCB row (+16..19 / +33..35) in DE:HL, for every disk mode --
they replace main's LOF / LOC mirror. Their rows are at the end.

read_sector serves the model (contiguous chain: fat_next_cluster is cluster + 1);
everything between -- hk_chin, din_peek / din_take / din_fill, k47b2_seek,
k47b2_nextbyte, rdblk_getbyte, fat_read_file_sector, fat_advance -- runs for real.

Clean-room: our own routines (disk/fat.asm, disk/kernel.asm, disk/driver.asm,
basic/fat-prim-body.inc), public FAT geometry.
"""

import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

DISK_BASE = 0x4000
SECSIZE = 512
DISK_ROM, DISK_SYM = tp("seqin_disk.rom"), tp("seqin_disk.sym")
CHAN = 1
BLOCK = 0xC000                  # the channel's 265 B block (main's fch_ctx_addr)
FIRST = 2                       # the file's first cluster
FIRSTDATA = 14                  # the first data sector
SPC = 2                         # sectors per cluster


def build():
    subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", DISK_ROM, DISK_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def row_addr(s, ch=CHAN):
    """dout_row's arithmetic, derived from the published cells, not copied."""
    return s["TXTMAX"] - (s["FCH_CEIL"] + 1) * s["FCH_STATESZ"] + ch * s["FCH_STATESZ"]


def lay_file(data):
    """The disk model: file byte o lives in sector FIRSTDATA + o // 512 (a
    contiguous chain from cluster FIRST)."""
    disk = {}
    for o, b in enumerate(data):
        disk.setdefault(FIRSTDATA + (FIRST - 2) * SPC + o // SECSIZE,
                        bytearray(SECSIZE))[o % SECSIZE] = b
    return disk


class Rig:
    """One INPUT channel, just opened (hk_finp's state), over `data`."""

    def __init__(self, data, mode=1, fail_at=None):
        self.m = m = Machine(DISK_ROM, DISK_SYM, rom_base=DISK_BASE)
        s = self.s = m.sym
        self.disk = lay_file(data)
        self.reads = []
        self.fail_at = fail_at          # a sector whose read fails (70)
        m.poke(s["FAT_SECPERCLUS"], SPC)
        m.poke_w(s["FAT_FIRSTDATA"], FIRSTDATA)
        m.poke(s["FCH_ACTIVE"], CHAN)
        m.poke(s["FCH_MODES"] + CHAN, mode)
        m.poke(s["FCH_RDMODE"], 1)      # LINE INPUT #: the line rule
        m.poke(s["DISKOP_ERR"], 0x99)   # stale: hk_chin must clear it
        row = self.row = row_addr(s)
        m.poke(row, bytes(s["FCH_STATESZ"]))
        m.poke(row + 14, 1)                                  # RS = 1
        m.poke(row + 16, len(data).to_bytes(4, "little"))    # the size
        m.poke_w(row + 26, FIRST)                            # the first cluster
        m.poke_w(row + s["DOUT_BLK"], BLOCK)
        m.poke(BLOCK, bytes(265))

        def read_sector(mm):
            sec = mm.cpu.de
            self.reads.append(sec)
            if sec == self.fail_at:
                mm.poke(s["DISKOP_ERR"], 70)
                mm.cpu.f |= 0x01
                return
            mm.poke(mm.cpu.hl, bytes(self.disk.get(sec, bytearray(SECSIZE))))
            mm.poke(s["DISKOP_ERR"], 0)     # a successful read clears it (dc_result)
            mm.cpu.f &= ~0x01

        def next_clus(mm):
            mm.cpu.hl = (mm.cpu.hl + 1) & 0xFFFF
            mm.cpu.f &= ~0x01

        m.trap("read_sector", read_sector)
        m.trap("fat_next_cluster", next_clus)

    def op(self, a):
        cpu = self.m.call("hk_chin", a=a)
        return cpu.a, carry(cpu)

    def read_all(self, a=0, limit=5000):
        out = []
        for _ in range(limit):
            b, end = self.op(a)
            if end:
                return bytes(out)
            out.append(b)
        raise RuntimeError("no end after %d bytes" % limit)

    def strscr(self):
        s = self.s
        n = self.m.mem[s["STRSCR"]]
        return bytes(self.m.peek(s["STRSCR"] + 1, n))


def line_rule(data):
    """The model of op 0 in line mode: up to the first Ctrl-Z; a CR's LF dropped."""
    data = data.split(b"\x1a", 1)[0]
    out, i = bytearray(), 0
    while i < len(data):
        out.append(data[i])
        if data[i] == 0x0D and i + 1 < len(data) and data[i + 1] == 0x0A:
            i += 1
        i += 1
    return bytes(out)


def run():
    build()
    fails = 0

    def report(label, ok, detail=""):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:60}" + ("" if ok else f"   {detail}"))

    # --- R2: the line rule, and INPUT$'s raw read of the same bytes ---------
    data = b"AB\r\nCD"
    got = Rig(data).read_all()
    report("op 0 line mode: CR eats its LF (R2)", got == b"AB\rCD", repr(got))
    r = Rig(data)
    r.m.poke(r.s["FCH_RDMODE"], 2)
    got = r.read_all()
    report("op 0 INPUT$ mode: the CR-LF pair is data", got == data, repr(got))

    # --- the stale-code rule: hk_chin clears DISKOP_ERR on entry ------------
    r = Rig(b"")
    b, end = r.op(0)
    report("empty file: the end at once, no sector read", end and r.reads == [],
           f"end={end} reads={r.reads}")
    report("empty file: no stale DSKIO code pending", r.m.mem[r.s["DISKOP_ERR"]] == 0,
           f"DISKOP_ERR={r.m.mem[r.s['DISKOP_ERR']]}")

    # --- a CR at the record boundary: byte 255 CR, byte 256 LF --------------
    data = bytes(b"x" * 255) + b"\r\n" + b"YZ"
    got = Rig(data).read_all()
    report("CR at record byte 255, LF at 256: swallowed across the refill",
           got == line_rule(data), f"{len(got)} B, tail {got[-4:]!r}")

    # --- every byte of a multi-cluster file, raw ----------------------------
    data = bytes((i * 37 + 11) & 0xFF for i in range(3000)).replace(b"\x1a", b"\x1b")
    r = Rig(data)
    r.m.poke(r.s["FCH_RDMODE"], 2)
    got = r.read_all()
    bad = next((i for i in range(min(len(got), len(data))) if got[i] != data[i]), None)
    report("3000 B over 3 clusters, raw: every byte, in order",
           got == data, f"len {len(got)}, first diff at {bad}")
    rr = int.from_bytes(r.m.peek(r.row + 33, 3), "little")
    report("... the random record ends at the size", rr == len(data), f"RR={rr}")

    # --- an exact multiple of 256: the last refill delivers 256, then the end -
    data = bytes(b"Q" * 512)
    r = Rig(data)
    r.m.poke(r.s["FCH_RDMODE"], 2)
    got = r.read_all()
    report("512 B file: 512 bytes, then the end", got == data, f"len {len(got)}")
    # --- the end is answered WITHOUT a seek (din_fill's RR = size test) ----------
    # 🔴 A 300 B FILE, NOT THE 512 ONE ABOVE: k47b2_seek reads a sector only when
    # the offset is INSIDE one, so at 512 it would read nothing either way and the
    # row could not tell the test from its absence (checked: a knife removing the
    # test leaves the 512 row green and turns this one red).
    r = Rig(bytes(b"Q" * 300))
    r.m.poke(r.s["FCH_RDMODE"], 2)
    r.read_all()
    n_reads = len(r.reads)
    b, end = r.op(2)                       # EOF() at the end
    report("300 B file: EOF() at the end reads no sector (RR = size)",
           end and len(r.reads) == n_reads, f"end={end} reads {n_reads}->{len(r.reads)}")
    r.fail_at = FIRSTDATA                  # the drive empties after the last byte
    b, end = r.op(0)
    report("... and a read there is a plain end, no DSKIO code (55, not 70)",
           end and r.m.mem[r.s["DISKOP_ERR"]] == 0,
           f"end={end} DISKOP_ERR={r.m.mem[r.s['DISKOP_ERR']]}")

    # --- R1: Ctrl-Z is a soft end, never consumed ---------------------------
    r = Rig(b"AB\x1aCD")
    got = r.read_all()
    report("Ctrl-Z: INPUT stops before it (R1)", got == b"AB", repr(got))
    b, end = r.op(2)
    report("... EOF() is true with it next", end)
    b, end = r.op(0)
    pos = r.m.mem[BLOCK + 6]
    report("... and a second read still meets it (not consumed)", end and pos == 2,
           f"end={end} position={pos}")

    # --- EOF() consumes nothing ---------------------------------------------
    r = Rig(b"HELLO")
    b, end = r.op(2)
    b2, end2 = r.op(0)
    report("EOF() at the start: false, and the first byte still follows",
           not end and not end2 and b2 == ord("H"), f"{end} {end2} {b2!r}")

    # --- the numeric item, across a refill ----------------------------------
    data = b" " * 253 + b"12345 \r\n7,8"
    r = Rig(data)
    b, end = r.op(4)
    report("numeric item straddling bytes 253..257: one item", not end and
           r.strscr() == b"12345", f"end={end} {r.strscr()!r}")
    b, end = r.op(0)
    report("... its blank, CR and LF eaten: the next byte is the next item's",
           not end and b == ord("7"), f"end={end} {b!r}")
    r = Rig(b" 1  2 ")
    r.op(4)
    rest = r.read_all()
    report("` 1  2 `: the item is 1, and `2 ` is left (inpnum_run2)",
           r.strscr() == b"1" and rest == b"2 ", f"{r.strscr()!r} {rest!r}")
    r = Rig(b"1   ,2")
    r.op(4)
    b, end = r.op(4)
    report("`1   ,2`: one comma eaten with the blanks; the next item is 2",
           r.strscr() == b"2" and not end, f"{r.strscr()!r} end={end}")
    r = Rig(b" 1 \r\n")
    r.op(4)
    b, end = r.op(2)
    report("` 1 CR LF`: nothing left after the last number (EOF -1)", end)
    r = Rig(b" \r\n ")
    b, end = r.op(4)
    report("blanks only: the end before any byte, length 0",
           end and r.m.mem[r.s["STRSCR"]] == 0, f"end={end}")

    # --- D-LINEJECT: a failed read is pending, not an end -------------------
    data = bytes(b"z" * 700)
    r = Rig(data, fail_at=FIRSTDATA + 1)       # the second sector
    r.m.poke(r.s["FCH_RDMODE"], 2)
    got = r.read_all()
    report("a failed read at byte 512: the bytes before it, then CF",
           got == data[:512], f"len {len(got)}")
    report("... with its code pending in DISKOP_ERR (70)",
           r.m.mem[r.s["DISKOP_ERR"]] == 70, f"DISKOP_ERR={r.m.mem[r.s['DISKOP_ERR']]}")

    # --- the guard: a live channel that is not open FOR INPUT ---------------
    r = Rig(b"DATA", mode=4)
    before = bytes(r.m.peek(BLOCK, 265))
    b, end = r.op(0)
    report("live channel RANDOM: the end, no sector read, block untouched",
           end and not r.reads and bytes(r.m.peek(BLOCK, 265)) == before,
           f"end={end} reads={r.reads}")

    # --- S10.E: ops 6 LOF / 8 LOC answer from the FCB row, any disk mode -------
    # 🎯 WHAT THESE ROWS PIN. LOF / LOC read a MIRROR in main until S10.E
    # (FAT_FILESIZE / FWR_BYTES, kept by disk.rom's dout_mirror and the sub-ROM's
    # t_fch_load); now main asks H_CHIN and gets DE:HL. So: the row's own +16..19
    # (LOF, all 32 bits) and +33..35 (LOC, high byte 0 -- +36 is poisoned, the
    # FCB's fourth random-record byte must not leak in), in every disk mode; the
    # row is FCH_ACTIVE's (two channels, different values); and the op is a pure
    # read -- no sector, no DISKOP_ERR clear (it is not a read's code), row and
    # record untouched. The DOUT value is the case the mirror got WRONG in main:
    # an APPEND channel on a 300 B file has LOF 300, LOC 256 (the last record's
    # start), and main's tenant read LOC's digits from FAT_FILESIZE.
    # modes: 1 INPUT, 3 DOUT_MODE (OUTPUT / APPEND), 4 RANDOM
    for mode, size, rr in ((1, 26, 0x0100), (3, 300, 256),
                           (4, 0x01_2C_00_00 + 76800, 0x0004_57),
                           (3, 0, 0)):
        r = Rig(b"", mode=mode)
        sym = r.s
        r.m.poke(r.row + 16, size.to_bytes(4, "little"))
        r.m.poke(r.row + 33, rr.to_bytes(3, "little"))
        r.m.poke(r.row + 36, 0xFF)                 # poison: not part of LOC
        # a SECOND channel, live instead: its row must be the one read
        r2 = row_addr(sym, 2)
        r.m.poke(r2, bytes(sym["FCH_STATESZ"]))
        r.m.poke(r2 + 16, (12345).to_bytes(4, "little"))
        r.m.poke(r2 + 33, (777).to_bytes(3, "little"))
        r.m.poke(sym["FCH_MODES"] + 2, mode)
        before = bytes(r.m.peek(r.row, sym["FCH_STATESZ"])) + bytes(r.m.peek(BLOCK, 265))
        vals = {}
        for op in (6, 8):
            cpu = r.m.call("hk_chin", a=op)
            vals[op] = (cpu.de << 16) | cpu.hl
        after = bytes(r.m.peek(r.row, sym["FCH_STATESZ"])) + bytes(r.m.peek(BLOCK, 265))
        tag = f"mode {mode}, size {size}, RR {rr}"
        report(f"op 6 LOF ({tag}): the row's +16..19, 32 bits", vals[6] == size,
               f"got {vals[6]}")
        report(f"op 8 LOC ({tag}): the row's +33..35, high byte 0", vals[8] == rr,
               f"got {vals[8]:#x}")
        report(f"... a pure read: no sector, DISKOP_ERR kept, row + record unchanged",
               not r.reads and r.m.mem[sym["DISKOP_ERR"]] == 0x99 and after == before,
               f"reads={r.reads} DISKOP_ERR={r.m.mem[sym['DISKOP_ERR']]:#x}")
        r.m.poke(sym["FCH_ACTIVE"], 2)
        two = []
        for op in (6, 8):
            cpu = r.m.call("hk_chin", a=op)     # (the CPU object is reused: read now)
            two.append((cpu.de << 16) | cpu.hl)
        report(f"... FCH_ACTIVE picks the row: #2 answers its own 12345 / 777",
               two == [12345, 777], f"got {two}")

    print()
    print("ALL PASS -- the INPUT reader keeps its text rules across every refill"
          if not fails else f"{fails} CHECK(S) FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
