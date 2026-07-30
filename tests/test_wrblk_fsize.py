# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: M28 $23 FSIZE + $26 WRBLK arithmetic helpers, no emulator.

Covers the pieces of tier2-m28-blockrandom-spec.md that are pure register/RAM
arithmetic (no FDC I/O), so they can be host-unit-tested directly:

  * fsize_body's ceil-divide: r0..r2 (fcb copy+33..35) = ceil(size/128), a
    32-bit-add-127-then-shift-right-7. Exercised via the real fsize_body with
    fat_mount/fat_find MOCKED (same technique as test_fat_find.py) so the test
    stays focused on the arithmetic + not-found contract, not the dir walk
    (already covered by test_fat_find.py).
  * wrblk_mul_rr_rs: the 24-bit RR * 16-bit RS -> 32-bit shift-add multiply
    that seeds WRBLK_MULACC for both the normal-write size bookkeeping and the
    HL=0 size-only/shrink dispatch.
  * wrblk_size_max: the 32-bit max(FAT_FILESIZE, WRBLK_MULACC) -> BDOS_WRBYTES
    compare-and-copy.

Clean-room: our own routines (kernel.asm), our own synthetic FCB/RAM state,
public GET FILE SIZE / RANDOM BLOCK WRITE contracts (map.grauw.nl) — no stock
ROM disassembly. See disk/docs/tier2-m28-blockrandom-spec.md.
"""

import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry, zero  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
DISK_BASE = 0x4000

ROM = "/tmp/zb_wrblk_fsize_ut.rom"
SYM = "/tmp/zb_wrblk_fsize_ut.sym"

FCB = 0xDA40            # the kernel's 37-byte FCB copy, real fixed address


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    # === fsize_body: ceil-divide + found/not-found contract ===================
    def fsize_case(size, expect_r0r1r2, mount_ok=True, found=True):
        # mock fat_mount / fat_find so the test isolates the arithmetic + A/L
        # contract from the directory-walk machinery (already covered by
        # test_fat_find.py).
        def mock_mount(mm):
            mm.cpu.f = (mm.cpu.f & ~0x01) if mount_ok else (mm.cpu.f | 0x01)

        def mock_find(mm):
            if found:
                struct.pack_into("<I", mm.mem, m.addr("FAT_FILESIZE"), size)
                mm.cpu.f &= ~0x01
            else:
                mm.cpu.f |= 0x01

        m.trap("fat_mount", mock_mount)
        m.trap("fat_find", mock_find)
        # FCB copy: name field content is irrelevant (fat_find mocked); zero the
        # r0..r2 field first so a false pass can't be masked by leftover state.
        m.poke(FCB + 33, bytes(3))
        cpu = m.call("fsize_body", de=FCB)
        a = cpu.a
        l = cpu.l
        r0, r1, r2 = m.peek(FCB + 33, 3)
        if found and mount_ok:
            want_r0, want_r1, want_r2 = expect_r0r1r2
            check(a == 0 and l == 0,
                  f"fsize_body size={size}: A=L=0 (got A={a} L={l})")
            check((r0, r1, r2) == (want_r0, want_r1, want_r2),
                  f"fsize_body size={size}: r0..r2={(r0,r1,r2)} "
                  f"(want {(want_r0,want_r1,want_r2)})")
        else:
            check(a == 0xFF and l == 0xFF,
                  f"fsize_body size={size} mount_ok={mount_ok} found={found}: "
                  f"A=L=$FF (got A={a} L={l})")

    # ceil(size/128) cases, including exact multiples and the 24-bit boundary.
    fsize_case(0, (0, 0, 0))
    fsize_case(1, (1, 0, 0))
    fsize_case(128, (1, 0, 0))
    fsize_case(129, (2, 0, 0))
    fsize_case(640, (5, 0, 0))              # 5-record file (BDOSX record 5/6 shape)
    fsize_case(255 * 128, (255, 0, 0))
    fsize_case(256 * 128, (0, 1, 0))        # ceil==256 -> r0 wraps to 0, r1=1 (24-bit LE)
    fsize_case(65536 * 128, (0, 0, 1))      # r1 wraps into r2

    fsize_case(1234, None, found=False)     # not found -> A=L=$FF regardless of size
    fsize_case(1234, None, mount_ok=False)  # mount error -> A=L=$FF

    # === wrblk_mul_rr_rs: 24-bit RR * 16-bit RS -> 32-bit WRBLK_MULACC =========
    def mul_case(rr, rs):
        m.poke(FCB + 33, struct.pack("<I", rr)[:3])
        m.poke_w(m.addr("WRBLK_RS"), rs)
        m.call("wrblk_mul_rr_rs", ix=FCB)
        got = struct.unpack("<I", m.peek(m.addr("WRBLK_MULACC"), 4))[0]
        want = (rr * rs) & 0xFFFFFFFF
        check(got == want, f"wrblk_mul_rr_rs RR={rr} RS={rs}: got {got} want {want}")

    mul_case(0, 128)
    mul_case(1, 128)
    mul_case(5, 128)
    mul_case(256, 128)          # 24-bit RR crossing into byte 1 (r1=1 -> record 256)
    mul_case(65535, 128)        # RR needing the full low 16 bits
    mul_case(1, 1)              # RS=1 (degenerate but exercises the multiply's low end)
    mul_case(0, 512)            # RR=0 -> product 0 regardless of RS
    mul_case(1000, 512)

    # === wrblk_size_max: BDOS_WRBYTES := max(FAT_FILESIZE, WRBLK_MULACC) ======
    def size_max_case(old_size, mulacc, want):
        m.poke(m.addr("FAT_FILESIZE"), struct.pack("<I", old_size))
        m.poke(m.addr("WRBLK_MULACC"), struct.pack("<I", mulacc))
        m.call("wrblk_size_max")
        got = struct.unpack("<I", m.peek(m.addr("BDOS_WRBYTES"), 4))[0]
        check(got == want,
              f"wrblk_size_max old={old_size} new={mulacc}: got {got} want {want}")

    size_max_case(1000, 500, 1000)      # new < old -> old wins (grow-or-hold path only
                                        # ever calls this when new >= old, but the compare
                                        # itself must be correct either direction)
    size_max_case(500, 1000, 1000)      # new > old -> new wins
    size_max_case(1000, 1000, 1000)     # equal -> either (same value)
    size_max_case(0, 0, 0)
    size_max_case(0xFFFF, 0x10000, 0x10000)   # crosses a 16-bit boundary

    print()
    print("ALL PASS — fsize_body ceil-divide + wrblk_mul_rr_rs + wrblk_size_max"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
