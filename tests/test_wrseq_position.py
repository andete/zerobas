# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: disk-ROM wrseq_wr_writeback (Item 5, WRSEQ $15 FCB position
write-back), no emulator.

The write branch of $15 WRSEQ (wrseq_body_write) now advances the caller-
visible FCB position after every written record, mirroring the M33 read-branch
fix that only ever ran on RDSEQ. The differential BDOSX8 already proves the
whole write path byte-identical to the stock oracle; this fast, emulator-free
twin locks in the write-back ARITHMETIC directly, so a regression in the field
math is caught by `make unit-test` without booting openMSX.

It calls the REAL canonical routine (kernel.asm wrseq_wr_writeback) with the
write-iterator cells seeded to model a mid-write state, then asserts every FCB
field it maintains, plus that BDOS_SEQREC advanced and the routine is fully
register-transparent (the property that keeps the BDOSX3/BDOSX4 WRSEQ register
snaps byte-identical). No disk is needed: the routine only reads the seeded
cells and writes the $DA40 FCB copy -- no read_sector/write_sector, no FAT.

Clean-room: our own routine, our own seeded state, the published CP/M FCB
field layout (CR +32, EX +12, size +16..19, first cluster +26/27, current
cluster +28/29, rec-in-cluster +30) -- no stock disassembly.
"""

import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_wrseq_position_ut.rom"
SYM = "/tmp/zb_wrseq_position_ut.sym"

FCB = 0xDA40
RECSIZE = 128
RECPERSEC = 4                       # compile-time constant in disk/equates.inc (512/128)
SECPERCLUS = 2                      # 1024-byte cluster -> recPerClus = 8
RECPERCLUS = SECPERCLUS * RECPERSEC

FIRST_CLUS = 0x0152                 # file's first cluster (BDOS_WRFIRST)
CUR_CLUS = 0x0153                   # write iterator's current cluster (BDOS_WRCLUS)


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # K = records written so far (1-based) AFTER this call's increment.
    for k in (1, 8, 9, 12, 200):
        m = Machine(ROM, SYM)
        wrbytes = k * RECSIZE
        m.poke(FCB, bytes(37))                                  # FMAKE leaves a zeroed FCB
        m.poke_w(m.addr("BDOS_SEQREC"), k - 1)                  # will increment to K
        m.poke_w(m.addr("BDOS_WRCLUS"), CUR_CLUS)
        m.poke_w(m.addr("BDOS_WRFIRST"), FIRST_CLUS)
        m.poke(m.addr("BDOS_WRBYTES"), struct.pack("<I", wrbytes))
        m.poke(m.addr("FAT_SECPERCLUS"), bytes([SECPERCLUS]))

        # register-transparency sentinels (the property BDOSX3/BDOSX4 rely on)
        cpu = m.call("wrseq_wr_writeback", a=0x99, bc=0x1234, de=0x5678, hl=0x9ABC)

        cr = m.peek(FCB + 32)[0]
        ex = m.peek(FCB + 12)[0]
        size = struct.unpack_from("<I", m.peek(FCB + 16, 4))[0]
        first = struct.unpack_from("<H", m.peek(FCB + 26, 2))[0]
        cur = struct.unpack_from("<H", m.peek(FCB + 28, 2))[0]
        ric = m.peek(FCB + 30)[0]
        seqrec = struct.unpack_from("<H", m.peek(m.addr("BDOS_SEQREC"), 2))[0]

        want_ric = (k - 1) // RECPERCLUS
        check(cr == k % 128, f"K={k}: CR (+32) = {cr} (want {k % 128})")
        check(ex == k // 128, f"K={k}: EX (+12) = {ex} (want {k // 128})")
        check(size == wrbytes, f"K={k}: size (+16..19) = {size} (want {wrbytes})")
        check(first == FIRST_CLUS, f"K={k}: first cluster (+26/27) = {first:#06x} (want {FIRST_CLUS:#06x})")
        check(cur == CUR_CLUS, f"K={k}: cur cluster (+28/29) = {cur:#06x} (want {CUR_CLUS:#06x})")
        check(ric == want_ric, f"K={k}: rec-in-cluster (+30) = {ric} (want {want_ric})")
        check(seqrec == k, f"K={k}: BDOS_SEQREC advanced to {seqrec} (want {k})")
        check(cpu.a == 0x99, f"K={k}: A preserved = {cpu.a:#04x} (want 0x99)")
        check(cpu.bc == 0x1234, f"K={k}: BC preserved = {cpu.bc:#06x} (want 0x1234)")
        check(cpu.de == 0x5678, f"K={k}: DE preserved = {cpu.de:#06x} (want 0x5678)")
        check(cpu.hl == 0x9ABC, f"K={k}: HL preserved = {cpu.hl:#06x} (want 0x9ABC)")

    print(f"\n{'ALL PASSED' if not fails else str(fails) + ' FAILED'}")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
