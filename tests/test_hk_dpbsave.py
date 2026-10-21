# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BSAVE to disk in disk.rom (hk_dpbsave) -- no emulator.

🏗️ D-ROMSIZE step 1 (2026-10-19) moved BSAVE's disk write out of the sub-ROM
save tenant (sub/save.asm, over that ROM's second FAT engine) into disk.rom.
Main's do_bsave keeps the parse -- name, start, end, exec / `,S` and the end of
the statement -- and crosses H_FOPEN once with FOPEN_SEL_BSAVE, as the CF-3300's
BSAVE enters $FE5D exactly once (scratchpad/bsave_hook_run.out). hk_dpload
dispatches to hk_dpbsave, which runs the SAME engine the tenant ran
(basic/sv-bsvdisk.inc, verbatim) over disk.rom's own create / write / close.

What is asserted, on a FAT12 model served by trapping read_sector and
fatprim_write_sector (everything between runs for real -- fat_mount, fat_fits,
fat_dir_create, the allocator, fat_write_fat_entry, the close):

  * the file: [$FE][start LE][end LE][exec LE] then start..end inclusive, its
    directory size, its cluster chain, and the 0821h date the sub-ROM tenant
    stamped (here: DATE_DAYS = 1461, the boot value, as on the CF-3300);
  * `,S`: the header verbatim, the data read through RDVRM;
  * the dispositions: status 0 / CF = 1 claimed; no disk -> status 3 with 70
    pending and nothing written; write protect -> 68; a disk too small for the
    image -> the CF-3300's refusal (header + Ctrl-Z, size 8, then 66,
    D-DISKFULLSTAMP); DISKSLOT_OK = 0 -> status 3 with no code (main prints
    `load error`, as the tenant's path did);
  * tokenised SAVE still writes through the prologue it now shares
    (hk_dpsave -> hkds_go, `jp (hl)`).

Clean-room: our own routines (disk/kernel.asm, basic/sv-bsvdisk.inc,
basic/fat-prim-body.inc) and the public FAT12 / BSAVE layouts.
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
DISK_ROM, DISK_SYM = tp("hkbsave_disk.rom"), tp("hkbsave_disk.sym")
RESERVED, NFATS, SPF = 1, 2, 3
FIRSTROOT = RESERVED + NFATS * SPF          # 7
ROOTSECS = 7                                # 112 entries x 32 / 512
FIRSTDATA = FIRSTROOT + ROOTSECS            # 14
SPC = 2
TOTSEC = 1440
NCLUS = (TOTSEC - FIRSTDATA) // SPC + 2     # FAT entries incl. 0 and 1
RDVRM = 0x004A


def build():
    subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", DISK_ROM, DISK_SYM],
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
    def __init__(self, free=None, fail_read=(), wprot=False):
        self.sec = {0: boot_sector()}
        self.fail_read = set(fail_read)
        self.wprot = wprot
        self.writes = []
        fat = bytearray(SPF * SECSIZE)
        fat[0:3] = b"\xF9\xFF\xFF"
        self.fat = fat
        if free is not None:                # every cluster used but `free` of them
            for c in range(2, NCLUS):
                if c >= 2 + free:
                    self.set_fat(c, 0xFFF)
        self.sync_fat()

    def set_fat(self, c, v):
        o = c * 3 // 2
        if c & 1:
            self.fat[o] = (self.fat[o] & 0x0F) | ((v << 4) & 0xF0)
            self.fat[o + 1] = (v >> 4) & 0xFF
        else:
            self.fat[o] = v & 0xFF
            self.fat[o + 1] = (self.fat[o + 1] & 0xF0) | ((v >> 8) & 0x0F)

    def get_fat(self, c):
        o = c * 3 // 2
        w = self.fat[o] | self.fat[o + 1] << 8
        return (w >> 4) if c & 1 else (w & 0xFFF)

    def sync_fat(self):
        for k in range(NFATS):
            for i in range(SPF):
                self.sec[RESERVED + k * SPF + i] = bytearray(
                    self.fat[i * SECSIZE:(i + 1) * SECSIZE])

    def load_fat(self):
        self.fat = bytearray(b"".join(bytes(self.sec.get(RESERVED + i, bytearray(SECSIZE)))
                                      for i in range(SPF)))

    def dir_entry(self, nm):
        want = name83(nm)
        for i in range(ROOTSECS * 16):
            s, o = FIRSTROOT + i // 16, (i % 16) * 32
            e = bytes(self.sec.get(s, bytearray(SECSIZE))[o:o + 32])
            if e[:11] == want:
                return e
        return None

    def read_file(self, nm):
        self.load_fat()
        e = self.dir_entry(nm)
        if e is None:
            return None, None
        clus = e[26] | e[27] << 8
        size = int.from_bytes(e[28:32], "little")
        data = bytearray()
        chain = []
        while 2 <= clus < 0xFF8 and len(data) < size:
            chain.append(clus)
            for k in range(SPC):
                data += self.sec.get(FIRSTDATA + (clus - 2) * SPC + k, bytearray(SECSIZE))
            clus = self.get_fat(clus)
        return bytes(data[:size]), (e, chain)


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

    def write_sector(mm):
        if disk.wprot:
            mm.poke(s["DISKOP_ERR"], 68)
            mm.cpu.a = 0
            mm.cpu.f |= 0x01
            return
        sec = mm.cpu.de
        disk.writes.append(sec)
        disk.sec[sec] = bytearray(mm.peek(mm.cpu.hl, SECSIZE))
        mm.poke(s["DISKOP_ERR"], 0)
        mm.cpu.f &= ~0x01

    m.trap("read_sector", read_sector)
    m.trap("fatprim_write_sector", write_sector)
    m.poke(s["DISKSLOT_OK"], 1)
    m.poke_w(s["DATE_DAYS"], 1461)          # the boot value: 1984-01-01
    return m


FAILS = []


def check(cond, what):
    print(("PASS  " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def bsave(m, name, start, end, exec_=None, vram=False, data=None):
    s = m.sym
    m.poke(s["DISK_FCB_NAME"], name83(name))
    m.poke_w(s["CURPTR"], start)
    m.poke_w(s["DSV_END"], end)
    m.poke_w(s["EXECPTR"], start if exec_ is None else exec_)
    m.poke(s["VRAM_FLAG"], 1 if vram else 0)
    if data is not None and not vram:
        m.poke(start, data)
    m.poke(s["DISKOP_STATUS"], 0x77)
    m.poke(s["DISKOP_ERR"], 0x55)            # stale: the hook must clear it
    m.poke(s["FOPEN_SEL"], s["FOPEN_SEL_BSAVE"])
    cpu = m.call("hk_dpload")
    return cpu, m.mem[s["DISKOP_STATUS"]], m.mem[s["DISKOP_ERR"]]


def header(start, end, exec_):
    return bytes([0xFE]) + b"".join(v.to_bytes(2, "little") for v in (start, end, exec_))


def ok_row(label, start, end, exec_=None, vram=False):
    n = end - start + 1
    d = Disk()
    m = machine(d)
    pat = bytes((i * 7 + 3) & 0xFF for i in range(n))
    if vram:
        m.trap(RDVRM, lambda mm: setattr(mm.cpu, "a", (mm.cpu.hl * 5 + 1) & 0xFF))
        pat = bytes(((start + i) * 5 + 1) & 0xFF for i in range(n))
    cpu, st, err = bsave(m, "T.BIN", start, end, exec_, vram, None if vram else pat)
    check(carry(cpu), f"{label}: claimed (CF=1)")
    check(st == 0, f"{label}: status {st} (want 0)")
    check(err == 0, f"{label}: no code pending ({err})")
    body, info = d.read_file("T.BIN")
    want = header(start, end, start if exec_ is None else exec_) + pat
    check(body == want, f"{label}: file is header + {n} B ({len(body or b'')} B read)")
    if info:
        e, chain = info
        size = int.from_bytes(e[28:32], "little")
        check(size == 7 + n, f"{label}: directory size {size} (want {7 + n})")
        clusters = -(-(7 + n) // (SPC * SECSIZE))
        check(len(chain) == clusters, f"{label}: {len(chain)} cluster(s) (want {clusters})")
        date = e[24] | e[25] << 8
        check(date == 0x0821, f"{label}: dated {date:#06x} (want 0x0821, as the tenant did)")


def main():
    build()

    ok_row("plain", 0xC000, 0xC00F)
    ok_row("exec", 0xC000, 0xC00F, exec_=0xC005)
    ok_row("one byte", 0xD000, 0xD000)
    ok_row("2 clusters + (1200 B)", 0x9000, 0x94AF)
    ok_row("exactly one sector of file (505 B data)", 0x9000, 0x9000 + 504)
    ok_row(",S from VRAM", 0x1800, 0x18FF, vram=True)

    # no disk: nothing can be read -- 70 pending, nothing written
    d = Disk(fail_read={0, 1})      # no disk: sector 1 (D-MEDIAID) and the boot sector
    m = machine(d)
    cpu, st, err = bsave(m, "T.BIN", 0xC000, 0xC00F, data=b"\x00" * 16)
    check(carry(cpu) and st == 3, f"no disk: claimed, status {st} (want 3)")
    check(err == 70, f"no disk: DISKOP_ERR {err} (want 70)")
    check(not d.writes, "no disk: nothing written")

    # write protect: the create's first write fails -- 68 pending
    d = Disk(wprot=True)
    m = machine(d)
    cpu, st, err = bsave(m, "T.BIN", 0xC000, 0xC00F, data=b"\x00" * 16)
    check(carry(cpu) and st == 3, f"write protect: claimed, status {st} (want 3)")
    check(err == 68, f"write protect: DISKOP_ERR {err} (want 68)")

    # disk full (one free cluster = 1024 B, image 7 + 2000 B): the CF-3300's
    # refusal -- the header and a Ctrl-Z, stamped, then 66 (D-DISKFULLSTAMP)
    d = Disk(free=1)
    m = machine(d)
    cpu, st, err = bsave(m, "F.BIN", 0x9000, 0x9000 + 1999, data=bytes(2000))
    check(carry(cpu) and st == 3, f"disk full: claimed, status {st} (want 3)")
    check(err == 66, f"disk full: DISKOP_ERR {err} (want 66)")
    body, _ = d.read_file("F.BIN")
    want = header(0x9000, 0x9000 + 1999, 0x9000) + b"\x1A"
    check(body == want, f"disk full: file is header + Ctrl-Z, 8 B ({body!r})")

    # exactly fits: one free cluster, 7 + 1017 = 1024 B
    d = Disk(free=1)
    m = machine(d)
    pat = bytes(range(256)) * 4
    cpu, st, err = bsave(m, "X.BIN", 0x9000, 0x9000 + 1016, data=pat[:1017])
    check(st == 0 and err == 0, f"fits to the byte: status {st}, err {err} (want 0 / 0)")
    body, _ = d.read_file("X.BIN")
    check(body == header(0x9000, 0x9000 + 1016, 0x9000) + pat[:1017],
          "fits to the byte: the whole image")

    # DISKSLOT_OK = 0: disk_write_begin refuses before the drive -- status 3, no
    # code, so main's disk_error prints `load error` as the tenant's path did
    d = Disk()
    m = machine(d)
    m.poke(m.sym["DISKSLOT_OK"], 0)
    cpu, st, err = bsave(m, "T.BIN", 0xC000, 0xC00F, data=b"\x00" * 16)
    check(carry(cpu) and st == 3 and err == 0,
          f"no disk slot: status {st}, err {err} (want 3 / 0)")
    check(not d.writes, "no disk slot: nothing written")

    # tokenised SAVE through the prologue BSAVE now shares (hk_dpsave -> hkds_go)
    d = Disk()
    m = machine(d)
    s = m.sym
    prog = bytes([0x07, 0x80, 0x0A, 0x00, 0x91, 0x31, 0x00, 0x00, 0x00])  # 10 PRINT 1-ish
    base = s["TXTBASE"]
    m.poke(base, prog)
    m.poke_w(s["TXTTAB"], base)
    m.poke_w(s["PRGEND"], base + len(prog) - 2)
    m.poke(s["DISK_FCB_NAME"], name83("P.BAS"))
    m.poke(s["FOPEN_SEL"], s["FOPEN_SEL_SAVE"])
    m.poke(s["DISKOP_STATUS"], 0x77)
    cpu = m.call("hk_dpload")
    st = m.mem[s["DISKOP_STATUS"]]
    check(carry(cpu) and st == 0, f"SAVE: claimed, status {st} (want 0)")
    body, _ = d.read_file("P.BAS")
    check(body == b"\xFF" + prog, f"SAVE: $FF + the image ({body!r})")

    if FAILS:
        print(f"\n{len(FAILS)} FAILED")
        return 1
    print("\nALL PASS -- BSAVE to disk runs in disk.rom (hk_dpbsave)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
