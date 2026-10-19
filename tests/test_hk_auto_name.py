# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk.rom's AUTOEXEC.BAS probe (hk_auto) and NAME (hk_name) on the
disk ROM's OWN FAT -- no emulator.

🏗️ D-ROMSIZE step 1 (2026-10-19) moved two things off main's fat_mount /
fat_find shims (the sub-ROM FAT tenant):

  * AUTOEXEC.BAS's cold-start probe. Main's autoexec_run keeps the diskless
    gate and the load + RUN; the decision is hk_auto's, reached through
    H_FOPEN's dispatcher (hk_dpload) with FOPEN_SEL_AUTO. Contract
    (disk/docs/autoexec-bas-spec.md §2): run only a PRESENT, NON-EMPTY
    AUTOEXEC.BAS; absent, empty or no disk is silent.
  * NAME's two look-ups. hk_name mounted locally for the open check and then
    called BACK into main for a second mount and both finds, and its stamp read
    main's FWR_DIRSEC / DIROFF. It now finds with this ROM's fat_find, and the
    stamp reads this ROM's own cells -- so the rows below put the OLD entry
    somewhere other than the first slot of the first root sector, where a stale
    or wrong position would still have looked right.

The disk is a Python model served by trapping read_sector / write_sector;
fat_mount, fat_find, name_cmp, hk_srcfind, hkk_open_check and hkn_stamp run for
real. The call-backs into main (fname_expr, pdfcb_resume, parse_disk_fcb) are
modelled at calbak by their published contracts (tools/gen_resident_abi.py).

Clean-room: our own routines (disk/kernel.asm, basic/fat-prim-body.inc), the
public FAT12 layout.
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
DISK_ROM, DISK_SYM = tp("hkauto_disk.rom"), tp("hkauto_disk.sym")
FIRSTROOT = 7                   # 1 reserved + 2 FATs x 3 sectors
ROOTSECS = 7                    # 112 entries x 32 / 512
TEXT = 0x9000                   # where the NAME statement's text sits


def build():
    subprocess.run(["pasmo", "-I", "disk", "--bin", "disk/disk.asm", DISK_ROM, DISK_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def name83(s):
    base, _, ext = s.upper().partition(".")
    return (base.ljust(8) + ext.ljust(3)).encode()


def boot_sector():
    b = bytearray(SECSIZE)
    b[11:13] = (512).to_bytes(2, "little")      # bytes per sector
    b[13] = 2                                   # sectors per cluster
    b[14:16] = (1).to_bytes(2, "little")        # reserved sectors
    b[16] = 2                                   # FAT copies
    b[17:19] = (112).to_bytes(2, "little")      # root entries
    b[19:21] = (1440).to_bytes(2, "little")     # total sectors
    b[22:24] = (3).to_bytes(2, "little")        # sectors per FAT
    return b


class Disk:
    """Root-directory model: entries[i] = (8.3 name, size) at slot i."""

    def __init__(self, entries, fail=()):
        self.sec = {0: boot_sector()}
        for i in range(ROOTSECS):
            self.sec[FIRSTROOT + i] = bytearray(SECSIZE)
        for i, (nm, size) in enumerate(entries):
            if nm is None:
                continue
            s, o = FIRSTROOT + i // 16, (i % 16) * 32
            e = self.sec[s]
            e[o:o + 11] = name83(nm)
            e[o + 11] = 0x20                    # archive
            e[o + 26:o + 28] = (2 + i).to_bytes(2, "little")
            e[o + 28:o + 32] = size.to_bytes(4, "little")
        # a free slot ($E5) before the end mark keeps fat_find walking
        self.fail = set(fail)
        self.writes = []

    def entry(self, i):
        s, o = FIRSTROOT + i // 16, (i % 16) * 32
        return bytes(self.sec[s][o:o + 11])


def machine(disk, text=b""):
    m = Machine(DISK_ROM, DISK_SYM, rom_base=DISK_BASE)
    s = m.sym

    def read_sector(mm):
        sec = mm.cpu.de
        if sec in disk.fail:
            mm.poke(s["DISKOP_ERR"], 70)
            mm.cpu.f |= 0x01
            return
        mm.poke(mm.cpu.hl, bytes(disk.sec.get(sec, bytearray(SECSIZE))))
        mm.poke(s["DISKOP_ERR"], 0)
        mm.cpu.f &= ~0x01

    def write_sector(mm):
        sec = mm.cpu.de
        disk.writes.append(sec)
        disk.sec[sec] = bytearray(mm.peek(mm.cpu.hl, SECSIZE))
        mm.cpu.f &= ~0x01

    def stage_name(mm, raw):
        nm = name83(raw.decode())
        mm.poke(s["DISK_FCB_NAME"], nm)

    def calbak(mm):
        ix = mm.cpu.ix
        if ix == s["fname_expr"]:
            # HL = cursor at a string literal: STRSCR = [len][bytes],
            # FN_RESUME = past the closing quote
            hl = mm.cpu.hl
            while mm.mem[hl] == 0x20:
                hl += 1
            assert mm.mem[hl] == 0x22, "fname_expr model: a literal only"
            end = hl + 1
            while mm.mem[end] != 0x22:
                end += 1
            body = bytes(mm.mem[hl + 1:end])
            mm.poke(s["STRSCR"], bytes([len(body)]) + body)
            mm.poke_w(s["FN_RESUME"], end + 1)
            mm.cpu.hl = end + 1
        elif ix == s["pdfcb_resume"]:
            n = mm.mem[s["STRSCR"]]
            stage_name(mm, bytes(mm.peek(s["STRSCR"] + 1, n)))
            mm.cpu.hl = mm.mem[s["FN_RESUME"]] | mm.mem[s["FN_RESUME"] + 1] << 8
        elif ix == s["parse_disk_fcb"]:
            n = mm.mem[s["STRSCR"]]
            stage_name(mm, bytes(mm.peek(s["STRSCR"] + 1, n)))
        else:
            raise AssertionError("unexpected call-back to %04X" % ix)
        mm.cpu.f &= ~0x01

    m.trap("read_sector", read_sector)
    m.trap("write_sector", write_sector)
    m.trap("calbak", calbak)
    m.poke(TEXT, text + b"\x00")
    m.poke_w(s["FN_RESUME"], TEXT)
    return m


FAILS = []


def check(cond, what):
    print(("PASS  " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def auto_row(label, entries, want_run, fail=(), via_dpload=True):
    d = Disk(entries, fail)
    m = machine(d)
    s = m.sym
    m.poke(s["DISKOP_STATUS"], 0x77)
    if via_dpload:
        m.poke(s["FOPEN_SEL"], s["FOPEN_SEL_AUTO"])
        cpu = m.call("hk_dpload")
    else:
        cpu = m.call("hk_auto")
    st = m.mem[s["DISKOP_STATUS"]]
    check(carry(cpu), f"auto {label}: claimed (CF=1)")
    check((st == 0) == want_run,
          f"auto {label}: status {st:#04x} -> {'run' if st == 0 else 'skip'}"
          f" (want {'run' if want_run else 'skip'})")
    check(bytes(m.peek(s["DISK_FCB_NAME"], 11)) == b"AUTOEXECBAS",
          f"auto {label}: DISK_FCB_NAME holds the name disk_prog_load opens")
    check(not d.writes, f"auto {label}: nothing written")
    return m


def name_row(label, entries, text, want_status, want_err=None, fail=(),
             renamed=None):
    d = Disk(entries, fail)
    before = {i: d.entry(i) for i in range(len(entries))}
    m = machine(d, text)
    s = m.sym
    m.poke(s["DISKOP_ERR"], 0)
    cpu = m.call("hk_name")
    st = m.mem[s["DISKOP_STATUS"]]
    check(carry(cpu), f"name {label}: claimed (CF=1)")
    check(st == want_status, f"name {label}: status {st} (want {want_status})")
    if want_err is not None:
        err = m.mem[s["DISKOP_ERR"]]
        check(err == want_err, f"name {label}: DISKOP_ERR {err} (want {want_err})")
    for i in range(len(entries)):
        want = before[i]
        if renamed is not None and i == renamed[0]:
            want = name83(renamed[1])
        check(d.entry(i) == want,
              f"name {label}: slot {i} reads {d.entry(i)!r} (want {want!r})")
    if renamed is None:
        check(not d.writes, f"name {label}: nothing written")
    else:
        sec = FIRSTROOT + renamed[0] // 16
        check(d.writes == [sec], f"name {label}: one write, to sector {sec} ({d.writes})")


def main():
    build()
    filler = [(f"F{i}.DAT", 10) for i in range(18)]

    # --- hk_auto -------------------------------------------------------------
    auto_row("present, 100 B", filler + [("AUTOEXEC.BAS", 100)], True)
    auto_row("present, direct entry", filler + [("AUTOEXEC.BAS", 100)], True,
             via_dpload=False)
    auto_row("absent", filler, False)
    auto_row("only AUTOEXEC.BAT", [("AUTOEXEC.BAT", 50)], False)
    auto_row("empty (0 B)", [("AUTOEXEC.BAS", 0)], False)
    # each size byte on its own: the test must OR all four
    for k, size in enumerate((1, 0x100, 0x10000, 0x1000000)):
        auto_row(f"size byte {k} only ({size:#x})", [("AUTOEXEC.BAS", size)], True)
    m = auto_row("no disk (boot sector unreadable)", [("AUTOEXEC.BAS", 100)],
                 False, fail={0})
    check(m.mem[m.sym["DISKOP_ERR"]] == 70,
          "auto no disk: the mount's mapped code is left pending, as before")
    # a selector that is not ours falls off hk_dpload's chain without touching
    # the drive. ⚠️ ITS CF IS THE LAST `cp FOPEN_SEL_LOAD`'s BORROW, so the
    # header's "CF = 0 = not my selector" holds only for a selector ABOVE $4C
    # ($FF here); an idle 0 comes back CF = 1. Pre-existing, unchanged by the
    # FOPEN_SEL_AUTO arm (filed with this slice, not fixed in it).
    d = Disk([("AUTOEXEC.BAS", 100)])
    m = machine(d)
    m.poke(m.sym["FOPEN_SEL"], 0xFF)
    m.poke(m.sym["DISKOP_STATUS"], 0x77)
    cpu = m.call("hk_dpload")
    check(not carry(cpu), "dpload: a foreign selector above $4C is not claimed")
    check(m.mem[m.sym["DISKOP_STATUS"]] == 0x77 and not d.writes,
          "dpload: ...and nothing ran (status untouched, no I/O)")
    m = machine(d)
    m.poke(m.sym["FOPEN_SEL"], 0x00)
    m.poke(m.sym["DISKOP_STATUS"], 0x77)
    m.call("hk_dpload")
    check(m.mem[m.sym["DISKOP_STATUS"]] == 0x77,
          "dpload: an idle 0 selector runs no arm (its CF is the borrow, above)")

    # --- hk_name -------------------------------------------------------------
    # OLD at slot 18 = sector FIRSTROOT+1, offset 64: a position main's cells
    # never held in this harness, so a stamp at the wrong place shows.
    ents = filler + [("OLD.TXT", 5), ("KEEP.TXT", 7)]
    name_row("rename", ents, b'"OLD.TXT" AS "NEW.TXT"', 1, renamed=(18, "NEW.TXT"))
    name_row("new name taken", ents, b'"OLD.TXT" AS "KEEP.TXT"', 2, want_err=65)
    name_row("old missing", ents, b'"NOPE.TXT" AS "NEW.TXT"', 0)
    name_row("no AS, old present", ents, b'"OLD.TXT"', 4)
    name_row("no AS, old missing", ents, b'"NOPE.TXT"', 0)
    name_row("no disk", ents, b'"OLD.TXT" AS "NEW.TXT"', 2, want_err=70, fail={0})
    # the new name's look-up must not move the OLD entry's position: KEEP.TXT
    # sits AFTER the old one, so a found-and-not-restored position would point
    # at slot 19
    name_row("rename, first slot", [("OLD.TXT", 5)] + filler,
             b'"OLD.TXT" AS "NEW.TXT"', 1, renamed=(0, "NEW.TXT"))

    if FAILS:
        print(f"\n{len(FAILS)} FAILED")
        return 1
    print("\nALL PASS -- hk_auto and hk_name run on disk.rom's own FAT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
