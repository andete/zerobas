# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: OPEN..AS #n LEN=r record geometry (field.asm frnd_calc), no emulator.

Disk-BASIC option-closure Item 3 generalizes the random-record engine from a
hard-wired 256-byte record (2 per 512-byte sector) to any LEN=r that TILES the
512-byte sector -- r a power of two in 1..256, so a record never straddles two
sectors. frnd_calc is the pure-arithmetic core: it maps a 1-based record number
to (GP_SEC = file sector index, GP_WITHIN = byte offset within that sector) via
byteoffset = (recno-1)*r, GP_SEC = byteoffset>>9, GP_WITHIN = byteoffset&511.
Like test_field.py, this drives frnd_calc directly (no disk I/O -- the sector
move stays in the emulator probes); the reclen is seeded per-channel exactly as
OPEN's LEN= parse would leave it (FCH_RECLENS[FCH_ACTIVE]).

Oracle: the record-tiling layout is independently derivable (record N occupies
file bytes [(N-1)*r, N*r); 512/r records tile each sector) -- never the ROM's own
output. r=256 reproduces the historical 2-per-sector behaviour exactly.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

# ⚠️ frnd_calc IS A SUB-ROM TENANT, so this test drives the SUB image, not the
# main one. Its body is basic/randio-body.inc, which the main ROM used to inline
# in the lean build and the shipped build EVICTS to sub/randio.asm. Until S3 this
# test built basic/main.asm and read frnd_calc out of the main symbol file — which
# worked only because msxtest.Machine's rom_base defaulted to $4000 and it was
# therefore assembling the LEAN cart (docs/spec-lean-retire-s3-gates.md §5, F-U).
# The routine under test is the same source either way; this just loads it from
# the ROM that actually carries it. The sub image is flat $0000-$7FFF, page-0
# tenants low and page-1 tenants high, exactly where a real CALSLT maps them.
# The two halves live in DIFFERENT ROMs, so this test builds both.
SUB_BASE = 0x0000     # sub image: flat $0000-$7FFF, page-0 low / page-1 high
BASIC_BASE = 0x2812   # the shipped BASIC image's org

SUB_ROM = tp("zb_openlen_sub.rom")
SUB_SYM = tp("zb_openlen_sub.sym")
ROM = tp("zb_openlen.rom")
SYM = tp("zb_openlen.sym")


def build():
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), ROM, SYM],
                   check=True, capture_output=True)


def run():
    build()
    m = Machine(SUB_ROM, SUB_SYM, rom_base=SUB_BASE)
    s = m.sym
    fails = 0

    def report(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:42} -> {got!r}" + ("" if ok else f"   want {want!r}"))

    CHAN = 1
    m.poke(s["FCH_ACTIVE"], CHAN)

    def geom(reclen, recno):
        # seed FCH_RECLENS[CHAN] = reclen (word), the record number, and run frnd_calc
        m.poke_w(s["FCH_RECLENS"] + CHAN * 2, reclen)
        m.poke_w(s["GP_RECNO"], recno)
        m.call("frnd_calc")
        sec = m.mem[s["GP_SEC"]] | (m.mem[s["GP_SEC"] + 1] << 8)
        within = m.mem[s["GP_WITHIN"]] | (m.mem[s["GP_WITHIN"] + 1] << 8)
        return sec, within

    def expect(reclen, recno):
        off = (recno - 1) * reclen
        return off >> 9, off & 511

    # r=256 -- the historical 2-records-per-sector layout (regression anchor)
    for recno in (1, 2, 3, 4, 5, 255):
        report(f"r=256 recno={recno}", geom(256, recno), expect(256, recno))
    # r=128 -- 4 records per sector (the common non-default)
    for recno in (1, 2, 3, 4, 5, 8, 9, 255):
        report(f"r=128 recno={recno}", geom(128, recno), expect(128, recno))
    # r=64 -- 8 records per sector
    for recno in (1, 8, 9, 16, 17, 255):
        report(f"r=64 recno={recno}", geom(64, recno), expect(64, recno))
    # r=1 -- 512 records per sector (extreme tiling); recno<=255 -> all in sector 0
    for recno in (1, 2, 255):
        report(f"r=1 recno={recno}", geom(1, recno), expect(1, recno))

    # -----------------------------------------------------------------------
    # oo_parse_reclen: the OPEN LEN= clause parser + tiling validation. LEN is
    # the $FF $92 function token, '=' is EQ_TOKEN ($EF); numeric constants crunch
    # as $0F+byte (10..255) or $1C+word (expr.asm §const tokens). Absent LEN ->
    # 256, Cy=0; a non-power-of-two or out-of-range r -> Cy=1 (Syntax error).
    # -----------------------------------------------------------------------
    # oo_parse_reclen is MAIN-ROM resident (basic/files.asm), so this half runs
    # on the main image while the geometry half above ran on the sub image.
    from msxtest import carry
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym
    BUF = 0xC400

    def i1(v):   # INT1_TOKEN ($0F) + byte
        return bytes([0x0F, v])

    def i2(v):   # INT2_TOKEN ($1C) + word LE
        return bytes([0x1C, v & 0xFF, (v >> 8) & 0xFF])

    def parse(tokens):
        m.mem[BUF:BUF + len(tokens) + 1] = tokens + b"\x00"
        cpu = m.call("oo_parse_reclen", hl=BUF)
        return cpu.de, carry(cpu)

    LEN = bytes([0xFF, 0x92, 0xEF])            # LEN =
    cases = [
        ("no LEN=",      b"\x00",              256, False),
        ("LEN=256",      LEN + i2(256),        256, False),
        ("LEN=128",      LEN + i1(128),        128, False),
        ("LEN=64",       LEN + i1(64),          64, False),
        ("LEN=1",        LEN + i1(1),            1, False),
        ("LEN=200 (bad)", LEN + i1(200),         0, True),   # not a power of two
        ("LEN=0 (bad)",  LEN + i1(0),            0, True),
        ("LEN=512 (bad)", LEN + i2(512),         0, True),   # > 256
    ]
    for label, toks, want_de, want_cy in cases:
        de, cy = parse(toks)
        if want_cy:
            report(f"parse {label} rejected", cy, True)
        else:
            report(f"parse {label}", (de, cy), (want_de, False))

    print()
    print("ALL PASS — LEN= record geometry tiles the sector for every r"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
