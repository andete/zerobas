#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-BOOTDATE (disk/fat.asm boot_date .. bd_field, and the marks in
disk/kernel.asm basent_body / basent_pending / w50a9_stub).

A boot code that cannot open MSXDOS.SYS jumps to $4022; both disk references
then ask `Enter date (M-D-Y):` before BASIC starts (the EU VG-8020 + NMS 1200's
form is followed). The PARSE rows are the measured answers (TODO.md D-BOOTDATE,
scratchpad/bootdate_run.out): what each typed line set, or `Invalid date`.
Rows marked OWN are own choices the references were not asked about.

The question itself runs with CHGET / CHPUT / INITXT trapped: keys in, the
printed bytes and DATE_DAYS out. The marks: $4022 asks only when MSX-DOS never
started (the mark is not DOS_SIG), MSX-DOS's $50A9 call sets DOS_SIG, and disk
INIT's BASENT branch leaves DOS_SIG after A>BASIC and clears it after a question.
"""

import datetime
import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

DISK_BASE = 0x4000
ROM = tp("zb_bootdate_ut.rom")
SYM = tp("zb_bootdate_ut.sym")
EPOCH = datetime.date(1980, 1, 1)
BOOT_DAYS = 1461                       # 1984-01-01, the date from boot
INVALID = None

# typed line -> the date it set on the VG-8020 + NMS 1200, or INVALID
PARSE_ROWS = [
    ("1-2-90", (1990, 1, 2)), ("1/2/90", (1990, 1, 2)), ("1.2.90", (1990, 1, 2)),
    ("1-2-1990", (1990, 1, 2)), ("1-2-80", (1980, 1, 2)), ("1-2-79", (2079, 1, 2)),
    ("3-4-5", (2005, 3, 4)), ("1-2", (1984, 1, 2)), ("2-29-92", (1992, 2, 29)),
    ("12-31-99", (1999, 12, 31)),
    ("13-2-90", INVALID), ("2-29-91", INVALID), ("0-1-90", INVALID),
    ("1-0-90", INVALID), ("1--90", INVALID), ("XYZ", INVALID), (" 1-2-90", INVALID),
]
# OWN: not measured on a reference
OWN_ROWS = [
    ("1-2-90X", INVALID), ("1-2-", INVALID), ("1-2X", INVALID), ("1", INVALID),
    ("1-2-100", INVALID), ("1-2-2100", INVALID), ("1-2-99999", INVALID),
    ("300-2-90", INVALID), ("01-02-1990", (1990, 1, 2)),
]

DOS_SIG = ord("D") | ord("S") << 8
DOS_TRY = ord("D") | ord("T") << 8
MARK_BA = ord("B") | ord("A") << 8
MARK_BD = ord("B") | ord("D") << 8


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def days_of(ymd):
    return (datetime.date(*ymd) - EPOCH).days


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    days_at = m.addr("DATE_DAYS")
    line_at = m.addr("BD_LINE")
    req_at = m.addr("BASENT_REQ")
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    def days():
        return m.mem[days_at] | m.mem[days_at + 1] << 8

    def mark():
        return m.mem[req_at] | m.mem[req_at + 1] << 8

    # --- the parser: every measured answer, then the own-choice rows ---------
    for tag, rows in (("", PARSE_ROWS), ("OWN ", OWN_ROWS)):
        for text, want in rows:
            m.poke_w(days_at, BOOT_DAYS)
            m.poke(line_at, text.encode("ascii") + b"\0")
            cpu = m.call("bd_parse")
            got = days()
            if want is INVALID:
                ok = cpu.a != 0 and got == BOOT_DAYS
                exp = "Invalid date, the date kept"
            else:
                ok = cpu.a == 0 and got == days_of(want)
                exp = "%04d-%02d-%02d" % want
            shown = EPOCH + datetime.timedelta(days=got)
            check(ok, f"{tag}{text!r:12s} -> A={cpu.a:02X} {shown} (want {exp})")

    # --- the question: keys in, the screen bytes and the date out -----------
    def ask(keys, start_mark=MARK_BD, autoexec=False):
        m.poke_w(days_at, BOOT_DAYS)
        # AUTOEXEC.BAS's lookup (auto_find -> hk_srcfind): CF = 1 not found, 0 found
        def srcfind(mach):
            mach.cpu.f = (mach.cpu.f & ~1) | (0 if autoexec else 1)
        m.trap("hk_srcfind", srcfind)
        queue = list(keys)
        out = m.capture_chput()
        initxt = m.record("BIOS_INITXT")

        def chget(mach):
            if not queue:
                raise RuntimeError("the question asked for a key past the script")
            mach.cpu.a = ord(queue.pop(0))
        m.trap("BIOS_CHGET", chget)
        m.call("basent_resume", hl=start_mark)
        return bytes(out).decode("latin1"), len(initxt), queue

    prompt = "Enter date (M-D-Y):"
    scr, nini, left = ask("1-2-90\r")
    check(scr == prompt + "1-2-90" and nini == 1 and days() == days_of((1990, 1, 2))
          and mark() == 0 and not left,
          f"BD + '1-2-90': screen {scr!r}, INITXT x{nini}, mark {mark():04X} "
          "(want the prompt, the echo, 1990-01-02, the mark cleared)")
    scr, nini, left = ask("\r")
    check(scr == prompt and days() == BOOT_DAYS and mark() == 0,
          f"BD + RETURN: screen {scr!r}, date kept {days() == BOOT_DAYS}")
    scr, nini, left = ask("13-2-90\r\r")
    check(scr == prompt + "13-2-90\r\nInvalid date\r\n" + prompt
          and days() == BOOT_DAYS and nini == 1,
          f"BD + '13-2-90', RETURN: screen {scr!r} (want Invalid date and the prompt "
          "again, INITXT once)")
    scr, nini, left = ask("1-3\b2-90\r")
    check(scr == prompt + "1-3\b \b2-90" and days() == days_of((1990, 1, 2)),
          f"BD + '1-3', BS, '2-90': screen {scr!r}, "
          f"{EPOCH + datetime.timedelta(days=days())} (want BS erasing, 1990-01-02)")
    scr, nini, left = ask("\b\x1c1-2-90\r")
    check(scr == prompt + "1-2-90" and days() == days_of((1990, 1, 2)),
          f"BD + BS on an empty line, a cursor key, '1-2-90': screen {scr!r}")
    scr, nini, left = ask("1" * 30 + "\r\r")
    check(scr.startswith(prompt + "1" * 24 + "\r\nInvalid date"),
          f"BD + 30 digits: {len(scr[len(prompt):].split(chr(13))[0])} echoed "
          "(want 24 kept, then Invalid date)")
    m.poke(m.addr("DISK_FCB_NAME"), b"\0" * 11)
    m.poke_w(req_at, MARK_BD)
    scr, nini, left = ask("", autoexec=True)
    fcb = bytes(m.mem[m.addr("DISK_FCB_NAME"):m.addr("DISK_FCB_NAME") + 11])
    check(scr == "" and nini == 0 and mark() == 0 and days() == BOOT_DAYS
          and fcb == b"AUTOEXECBAS",
          f"BD + an AUTOEXEC.BAS on the disk: screen {scr!r}, INITXT x{nini}, mark "
          f"{mark():04X}, looked up {fcb!r} (want no question -- both references, any "
          "size -- and the mark cleared)")
    m.poke_w(req_at, MARK_BA)
    scr, nini, left = ask("", start_mark=MARK_BA)
    check(scr == "" and nini == 0 and mark() == DOS_SIG,
          f"BA (MSX-DOS's BASIC): screen {scr!r}, mark {mark():04X} (want no question, "
          "DOS_SIG)")

    # --- the marks -----------------------------------------------------------
    for val, want_z in ((MARK_BA, True), (MARK_BD, True), (DOS_SIG, False),
                        (DOS_TRY, False), (0, False)):
        m.poke_w(req_at, val)
        cpu = m.call("basent_pending")
        check(bool(cpu.f & 0x40) == want_z and cpu.hl == val,
              f"basent_pending, mark {val:04X}: Z={bool(cpu.f & 0x40)} HL={cpu.hl:04X}")
    m.trap("SECTOR_BUF", lambda mach: None)   # stop at the trampoline's copy
    for val, want in ((DOS_SIG, MARK_BA), (DOS_TRY, MARK_BD), (0, MARK_BD)):
        m.poke_w(req_at, val)
        m.call("basent_body")
        check(mark() == want, f"$4022 with mark {val:04X}: mark {mark():04X} "
              f"(want {want:04X})")
    m.poke_w(req_at, DOS_TRY)
    cpu = m.call("w50a9_stub")
    check(mark() == DOS_SIG and cpu.a == 0 and (cpu.f & 0xFF) == 0x42
          and cpu.de == 0xF1AA and cpu.hl == 0xF359,
          f"$50A9: mark {mark():04X} (want DOS_SIG), AF={cpu.a:02X}{cpu.f & 0xFF:02X} "
          f"DE={cpu.de:04X} HL={cpu.hl:04X} (the $50A9 contract unchanged)")

    print()
    print("ALL PASS — the boot-fallback date question answers as the VG-8020 does"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
