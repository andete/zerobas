# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BLOAD from disk in disk.rom (hk_dpbload) -- no emulator.

🏗️ D-ROMSIZE step 1 (2026-10-19) moved BLOAD's disk load out of the sub-ROM BLOAD
tenant (basic/bload-body.inc's do_disk_bload, over that ROM's second FAT engine --
its last user) into disk.rom. Main parses the tail (`,R` / `,S` / `,offset`,
pcr_bload); the sub-ROM tenant decides the device and builds DISK_FCB_NAME, then
answers BL_STAT = FOPEN_SEL_BLOAD; main crosses H_FOPEN with that selector, as the
CF-3300's BLOAD enters $FE5D once (disk/docs/spec-diskcode-eviction.md §6.6ab /
§8.2); hk_dpload dispatches to hk_dpbload.

PART 1 -- disk.rom's hk_dpbload, on a FAT12 model served by trapping read_sector
(fat_mount, fat_io_find, the chain walk and fat_io_getbyte run for real):
  * the load: [$FE][start][end][exec] then start..end inclusive into RAM, a file
    spanning sectors and clusters, CURPTR = ENDPTR = end and EXECPTR = exec after;
  * D-BLOADOFS: the offset added to start, end AND exec, wrapping at 16 bits;
  * `,S`: every byte through WRTVRM ($004D) at the header's VRAM addresses, RAM
    untouched;
  * the dispositions in BL_STAT's code: 0 loaded; 53 not found (D-BLNF); 61 no
    $FE marker (D-BLMODE); 1 + 70 pending with no disk; 1 and no code for a file
    that ends early (header or data) and for an empty one;
  * a stale DISKOP_ERR is cleared; FOPEN_SEL is disarmed; CF = 1 claimed;
  * a byte aimed at page 1 ($4000-$7FFF, THIS ROM while the hook runs) is dropped,
    as the ROM under the old tenant dropped it -- the model's ROM image is unchanged.
PART 2 -- the sub-ROM tenant's half (bload_tenant on sub.rom): a disk name builds
DISK_FCB_NAME and answers FOPEN_SEL_BLOAD; a drive past B: is 62 and a malformed
name 56 with no load; diskless `A:X` is 56; `CAS:` reaches the tape search.

Clean-room: our own routines (disk/kernel.asm, basic/fatio-body.inc,
basic/fat-prim-body.inc, sub/bload.asm, basic/bload-body.inc) and the public FAT12
/ BSAVE layouts.
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
DISK_ROM, DISK_SYM = tp("hkbload_disk.rom"), tp("hkbload_disk.sym")
SUB_ROM, SUB_SYM = tp("hkbload_sub.rom"), tp("hkbload_sub.sym")
RESERVED, NFATS, SPF = 1, 2, 3
FIRSTROOT = RESERVED + NFATS * SPF          # 7
ROOTSECS = 7                                # 112 entries x 32 / 512
FIRSTDATA = FIRSTROOT + ROOTSECS            # 14
SPC = 2
TOTSEC = 1440
WRTVRM = 0x004D


def build():
    subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", DISK_ROM, DISK_SYM],
                   check=True, capture_output=True, cwd=ROOT)
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def name83(s):
    base, _, ext = s.upper().partition(".")
    return (base.ljust(8) + ext.ljust(3)).encode()


def boot_sector():
    b = bytearray(SECSIZE)
    b[11:13] = SECSIZE.to_bytes(2, "little")
    b[13] = SPC
    b[14:16] = RESERVED.to_bytes(2, "little")
    b[16] = NFATS
    b[17:19] = (112).to_bytes(2, "little")
    b[19:21] = TOTSEC.to_bytes(2, "little")
    b[21] = 0xF9
    b[22:24] = SPF.to_bytes(2, "little")
    return b


class Disk:
    """A FAT12 720 KB volume as a sector dict; files are laid out contiguously."""

    def __init__(self, fail_read=()):
        self.sec = {0: boot_sector()}
        self.fail_read = set(fail_read)
        self.fat = bytearray(SPF * SECSIZE)
        self.fat[0:3] = b"\xF9\xFF\xFF"
        self.next_clus = 2
        self.nfiles = 0
        self.sync_fat()

    def set_fat(self, c, v):
        o = c * 3 // 2
        if c & 1:
            self.fat[o] = (self.fat[o] & 0x0F) | ((v << 4) & 0xF0)
            self.fat[o + 1] = (v >> 4) & 0xFF
        else:
            self.fat[o] = v & 0xFF
            self.fat[o + 1] = (self.fat[o + 1] & 0xF0) | ((v >> 8) & 0x0F)

    def sync_fat(self):
        for k in range(NFATS):
            for i in range(SPF):
                self.sec[RESERVED + k * SPF + i] = bytearray(
                    self.fat[i * SECSIZE:(i + 1) * SECSIZE])

    def add_file(self, nm, data, size=None):
        """Store `data` in a fresh cluster chain; `size` (default len) is the
        directory size -- a smaller one models a file that ENDS early."""
        csize = SPC * SECSIZE
        nclus = max(1, -(-len(data) // csize)) if data else 0
        first = self.next_clus if nclus else 0
        for k in range(nclus):
            c = self.next_clus + k
            self.set_fat(c, c + 1 if k < nclus - 1 else 0xFFF)
            chunk = data[k * csize:(k + 1) * csize].ljust(csize, b"\x00")
            for s in range(SPC):
                self.sec[FIRSTDATA + (c - 2) * SPC + s] = bytearray(
                    chunk[s * SECSIZE:(s + 1) * SECSIZE])
        self.next_clus += nclus
        self.sync_fat()
        e = bytearray(32)
        e[0:11] = name83(nm)
        e[11] = 0x20
        e[26:28] = first.to_bytes(2, "little")
        e[28:32] = (len(data) if size is None else size).to_bytes(4, "little")
        i = self.nfiles
        self.nfiles += 1
        s, o = FIRSTROOT + i // 16, (i % 16) * 32
        sec = self.sec.setdefault(s, bytearray(SECSIZE))
        sec[o:o + 32] = e


def header(start, end, exec_):
    return bytes([0xFE]) + b"".join(v.to_bytes(2, "little") for v in (start, end, exec_))


def machine(disk):
    m = Machine(DISK_ROM, DISK_SYM, rom_base=DISK_BASE)
    s = m.sym

    def read_sector(mm):
        sec = mm.cpu.de
        if sec in disk.fail_read:
            mm.poke(s["DISKOP_ERR"], 70)
            mm.cpu.f |= 0x01
            return
        mm.poke(mm.cpu.hl, bytes(disk.sec.get(sec, bytearray(SECSIZE))))
        mm.poke(s["DISKOP_ERR"], 0)
        mm.cpu.f &= ~0x01

    m.trap("read_sector", read_sector)
    m.trap("fatprim_write_sector", lambda mm: FAILS.append("a BLOAD wrote a sector"))
    m.poke(s["DISKSLOT_OK"], 1)
    return m


FAILS = []


def check(cond, what):
    print(("PASS  " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def bload(m, name, ofs=0, vram=False):
    s = m.sym
    m.poke(s["DISK_FCB_NAME"], name83(name))
    m.poke_w(s["BL_OFS"], ofs & 0xFFFF)
    m.poke(s["VRAM_FLAG"], 1 if vram else 0)
    m.poke(s["DISKOP_STATUS"], 0x77)
    m.poke(s["DISKOP_ERR"], 0x55)            # stale: the hook must clear it
    m.poke(s["FOPEN_SEL"], s["FOPEN_SEL_BLOAD"])
    cpu = m.call("hk_dpload")
    return cpu, m.mem[s["DISKOP_STATUS"]], m.mem[s["DISKOP_ERR"]]


def ok_row(label, start, end, exec_, ofs=0):
    n = end - start + 1
    d = Disk()
    pat = bytes((i * 7 + 3) & 0xFF for i in range(n))
    d.add_file("T.BIN", header(start, end, exec_) + pat)
    m = machine(d)
    s = m.sym
    cpu, st, err = bload(m, "T.BIN", ofs)
    lo = (start + ofs) & 0xFFFF
    hi = (end + ofs) & 0xFFFF
    check(carry(cpu), f"{label}: claimed (CF=1)")
    check(st == 0 and err == 0, f"{label}: status {st}, err {err} (want 0 / 0)")
    check(m.peek(lo, n) == pat, f"{label}: {n} B at ${lo:04X}")
    check(m.mem[(lo - 1) & 0xFFFF] == 0 and m.mem[(hi + 1) & 0xFFFF] == 0,
          f"{label}: nothing outside [${lo:04X}..${hi:04X}]")
    cur = m.mem[s["CURPTR"]] | m.mem[s["CURPTR"] + 1] << 8
    endp = m.mem[s["ENDPTR"]] | m.mem[s["ENDPTR"] + 1] << 8
    ex = m.mem[s["EXECPTR"]] | m.mem[s["EXECPTR"] + 1] << 8
    check(cur == hi and endp == hi, f"{label}: CURPTR ${cur:04X} = ENDPTR ${endp:04X} (want ${hi:04X})")
    check(ex == (exec_ + ofs) & 0xFFFF, f"{label}: EXECPTR ${ex:04X} (want ${(exec_ + ofs) & 0xFFFF:04X})")
    check(m.mem[s["FOPEN_SEL"]] == 0, f"{label}: FOPEN_SEL disarmed")


def fail_row(label, disk, name, want_st, want_err):
    m = machine(disk)
    cpu, st, err = bload(m, name)
    check(carry(cpu), f"{label}: claimed (CF=1)")
    check(st == want_st and err == want_err,
          f"{label}: status {st}, err {err} (want {want_st} / {want_err})")
    return m


def disk_part():
    ok_row("plain", 0xC000, 0xC00F, 0xC000)
    ok_row("exec", 0xC000, 0xC00F, 0xC005)
    ok_row("one byte", 0xD000, 0xD000, 0xD000)
    ok_row("3 clusters (2500 B)", 0x9000, 0x9000 + 2499, 0x9000)
    ok_row("offset +&H1000 (start, end AND exec)", 0xC000, 0xC0FF, 0xC010, ofs=0x1000)
    ok_row("offset &HF000 wraps $C000 -> $B000", 0xC000, 0xC0FF, 0xC000, ofs=0xF000)
    ok_row("negative offset -&H100", 0xC100, 0xC1FF, 0xC100, ofs=-0x100)

    # ,S: every byte through WRTVRM at the header's VRAM addresses (+ offset)
    d = Disk()
    pat = bytes((i * 5 + 1) & 0xFF for i in range(256))
    d.add_file("V.BIN", header(0x1800, 0x18FF, 0x1800) + pat)
    m = machine(d)
    log = m.record(WRTVRM, regs=("hl", "a"))
    cpu, st, err = bload(m, "V.BIN", ofs=0x100, vram=True)
    check(st == 0 and err == 0, f",S: status {st}, err {err} (want 0 / 0)")
    check([(e["hl"], e["a"]) for e in log] == [(0x1900 + i, pat[i]) for i in range(256)],
          f",S: 256 WRTVRM calls at $1900.. with the file's bytes ({len(log)} made)")
    check(m.peek(0x1900, 256) == bytes(256), ",S: RAM at the VRAM addresses untouched")

    # page 1 is THIS ROM while the hook runs: those bytes are dropped
    d = Disk()
    pat = bytes(range(1, 9))
    d.add_file("P.BIN", header(0x7FFC, 0x8003, 0x7FFC) + pat)
    m = machine(d)
    before = m.peek(0x7FFC, 4)
    cpu, st, err = bload(m, "P.BIN")
    check(st == 0, f"page 1: status {st} (want 0)")
    check(m.peek(0x7FFC, 4) == before, "page 1: the 4 bytes aimed at $7FFC-$7FFF dropped")
    check(m.peek(0x8000, 4) == pat[4:], "page 1: the 4 at $8000-$8003 stored")

    # the dispositions, in BL_STAT's code
    d = Disk()
    d.add_file("T.BIN", header(0xC000, 0xC00F, 0xC000) + bytes(16))
    fail_row("not found", d, "NOSUCH.BIN", 53, 0)
    d = Disk()
    d.add_file("PROG.BAS", b"\xFF\x07\x80\x0A\x00\x91\x31\x00\x00\x00")
    fail_row("tokenised BASIC: no $FE marker", d, "PROG.BAS", 61, 0)
    d = Disk()
    d.add_file("TEST.BIN", b"ABCDEFGH")
    fail_row("data with a .BIN name", d, "TEST.BIN", 61, 0)
    # no disk: EVERY read fails -- fat_mount reads sector 1 (the media ID) first
    # since D-MEDIAID, so failing only the boot sector no longer models one
    fail_row("no disk", Disk(fail_read={0, 1}), "T.BIN", 1, 70)
    d = Disk()
    d.add_file("E.BIN", b"")
    fail_row("empty file", d, "E.BIN", 1, 0)
    d = Disk()
    d.add_file("H.BIN", header(0xC000, 0xC00F, 0xC000)[:4])
    fail_row("header cut short", d, "H.BIN", 1, 0)
    d = Disk()
    d.add_file("S.BIN", header(0xC000, 0xC00F, 0xC000) + bytes(range(1, 9)))
    m = fail_row("data cut short (8 of 16)", d, "S.BIN", 1, 0)
    check(m.peek(0xC000, 8) == bytes(range(1, 9)), "data cut short: the 8 bytes it had are stored")
    # a read failure INSIDE the file: the code it left is pending
    d = Disk()
    d.add_file("R.BIN", header(0x9000, 0x9000 + 1999, 0x9000) + bytes(2000))
    d.fail_read.add(FIRSTDATA + 1)           # the file's second sector
    fail_row("eject mid-file", d, "R.BIN", 1, 70)

    # every other selector still reaches its arm: an idle selector claims nothing
    m = machine(Disk())
    m.poke(m.sym["FOPEN_SEL"], 0x99)
    cpu = m.call("hk_dpload")
    check(not carry(cpu), "an unknown selector is not claimed (CF=0)")


def sub_part():
    m = Machine(SUB_ROM, SUB_SYM, rom_base=0)
    s = m.sym
    stage = 0xC800

    def run(name, diskslot=1):
        m.poke(stage, bytes(32))             # parse_disk_fcb peeks name[1] even
        m.poke(stage, name.encode() + b'"')  # past an empty name's closing quote
        m.poke_w(s["BL_PTR"], stage)
        m.poke(s["DISKSLOT_OK"], diskslot)
        m.poke(s["DISK_FCB_NAME"], b"OLDNAMEOLD ")
        m.poke(s["DISK_FCB_DRV"], 0x77)
        m.poke(s["BL_STAT"], 0x33)
        m.call("bload_tenant")
        return m.mem[s["BL_STAT"]]

    sel = s["FOPEN_SEL_BLOAD"]
    st = run("GAME.BIN")
    check(st == sel and m.peek(s["DISK_FCB_NAME"], 11) == name83("GAME.BIN")
          and m.mem[s["DISK_FCB_DRV"]] == 0,
          f"tenant: GAME.BIN -> BL_STAT {st:#x} (want {sel:#x}), name built, drive 0")
    st = run("b:x.bin")
    # the TYPED case is kept since 2026-10-28 (OPEN twice): disk.rom upper-cases
    # where the name meets the disk, so the builder's own answer is `x       bin`
    check(st == sel and m.peek(s["DISK_FCB_NAME"], 11) == b"x       bin"
          and m.mem[s["DISK_FCB_DRV"]] == 2,
          f"tenant: b:x.bin -> BL_STAT {st:#x}, name x.bin (typed case), drive 2")
    st = run("Q:X.BIN")
    check(st == 62, f"tenant: Q:X.BIN -> BL_STAT {st} (want 62, Bad drive name)")
    st = run("")
    check(st == 56, f'tenant: "" -> BL_STAT {st} (want 56, Bad file name)')
    st = run("A:X.BIN", diskslot=0)
    check(st == 56, f"tenant, diskless: A:X.BIN -> BL_STAT {st} (want 56)")

    # CAS: goes to the tape search, not the disk: a failed search is 19
    def no_tape(mm):
        mm.cpu.f |= 0x01
    m.trap("cas_open_match", no_tape)
    m.trap(0x00E7, lambda mm: None)          # TAPIOF
    st = run("CAS:GAME")
    check(st == 19, f"tenant: CAS:GAME -> the tape search, BL_STAT {st} (want 19)")


def main():
    build()
    disk_part()
    sub_part()
    if FAILS:
        print(f"\n{len(FAILS)} FAILED")
        return 1
    print("\nALL PASS -- BLOAD from disk runs in disk.rom (hk_dpbload)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
