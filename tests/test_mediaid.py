# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host test for D-MEDIAID: fat_mount takes a disk's geometry from the MEDIA ID in
the FAT's first byte (logical sector 1), not from the boot sector's BPB -- what
both references do (scratchpad/bpbrule_probe.py, scratchpad/bpbrule_run.out).

read_sector is trapped and served from an in-memory image built here (DE = the
logical sector, HL = the buffer), so fat_mount's own read, fat_media's BPB fields
and the geometry parse run for real. Then GETDPB on the all-zero-BPB disk must
give the CF-3300's 720 KB DPB, byte for byte (the same oracle as test_getdpb.py).
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
ROM = tp("zb_mediaid_ut.rom")
SYM = tp("zb_mediaid_ut.sym")

# media ID -> (sectors per cluster, sectors per FAT, root entries, total sectors)
FORMATS = {0xF8: (2, 2, 112, 720), 0xF9: (2, 3, 112, 1440), 0xFA: (2, 1, 112, 640),
           0xFB: (2, 2, 112, 1280), 0xFC: (1, 2, 64, 360), 0xFD: (2, 2, 112, 720),
           0xFE: (1, 1, 64, 320), 0xFF: (2, 1, 112, 640)}
BPB_720 = bytes.fromhex("0002" "02" "0100" "02" "7000" "a005" "f9" "0300" "0900" "0200")


def build():
    src = os.path.join(ROOT, "disk", "disk.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "disk"), "--bin", src, ROM, SYM],
                   check=True, capture_output=True)


def image(fat_media, bpb):
    """Sectors 0 and 1 of a disk: the boot sector with `bpb` at +11, and the FAT's
    first sector starting with `fat_media`."""
    s0 = bytearray(512)
    s0[0] = 0xEB
    s0[11:11 + len(bpb)] = bpb
    s1 = bytearray(512)
    s1[0:3] = bytes([fat_media, 0xFF, 0xFF])
    return {0: bytes(s0), 1: bytes(s1)}


def expect(spc, spf, rootn, total):
    root = 1 + 2 * spf
    data = root + rootn * 32 // 512
    return {"FAT_SECPERCLUS": spc, "FAT_FATSTART": 1, "FAT_NUMFATS": 2,
            "FAT_SECPERFAT": spf, "FAT_FIRSTROOT": root, "FAT_FIRSTDATA": data,
            "FAT_TOTCLUS": (total - data) // spc + 2}


def run():
    build()
    m = Machine(ROM, SYM, rom_base=DISK_BASE)
    fails = 0
    reads = []

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    def mount(sectors):
        reads.clear()

        def read_sector(mach):
            lsn = mach.cpu.de
            reads.append(lsn)
            mach.poke(mach.cpu.hl, sectors.get(lsn, bytes(512)))
            mach.cpu.f &= ~0x01
        m.trap("read_sector", read_sector)
        return m.call("fat_mount")

    def geometry():
        g = {}
        for k in ("FAT_SECPERCLUS", "FAT_NUMFATS", "FAT_SECPERFAT"):
            g[k] = m.mem[m.addr(k)]
        for k in ("FAT_FATSTART", "FAT_FIRSTROOT", "FAT_FIRSTDATA", "FAT_TOTCLUS"):
            a = m.addr(k)
            g[k] = m.mem[a] | m.mem[a + 1] << 8
        return g

    # --- every media ID, the BPB ALL ZERO: the format comes from the FAT --------
    for media, fmt in FORMATS.items():
        cpu = mount(image(media, bytes(19)))
        got, want = geometry(), expect(*fmt)
        check(not carry(cpu) and got == want and reads == [1],
              f"media {media:02X}, BPB all zero: Cy={int(carry(cpu))} reads {reads} "
              f"root {got['FAT_FIRSTROOT']} data {got['FAT_FIRSTDATA']} clusters "
              f"{got['FAT_TOTCLUS']} (want {want['FAT_FIRSTROOT']} / "
              f"{want['FAT_FIRSTDATA']} / {want['FAT_TOTCLUS']}, ONE read: sector 1)")

    # --- the reference's separating rows (scratchpad/bpbrule_run.out) ------------
    want720 = expect(*FORMATS[0xF9])
    cpu = mount(image(0xF9, b"\x37\x20\x20" + BPB_720[3:]))
    check(not carry(cpu) and geometry() == want720,
          "V1 facdemo3's damage (bytes/sector $2037, sectors/cluster $20): 720 KB")
    cpu = mount(image(0xF9, BPB_720[:10] + b"\xf8" + BPB_720[11:]))
    check(not carry(cpu) and geometry() == want720,
          "V3 BPB media $F8, FAT $F9: the FAT's 720 KB")
    cpu = mount(image(0xF8, BPB_720))
    check(not carry(cpu) and geometry() == expect(*FORMATS[0xF8]),
          "V4 BPB 720 KB, FAT $F8: the FAT's 360 KB single-sided format")

    # --- no media ID in the FAT: the boot sector's BPB, as before (own choice) ---
    cpu = mount(image(0x00, BPB_720))
    check(not carry(cpu) and geometry() == want720 and reads == [1, 0],
          f"FAT byte $00, BPB 720 KB: the BPB's geometry, reads {reads} (want [1, 0])")
    cpu = mount(image(0x00, bytes(19)))
    check(carry(cpu), "FAT byte $00, BPB all zero: Cy=1 (no geometry anywhere)")

    # --- GETDPB on the all-zero-BPB 720 KB disk = the CF-3300's 720 KB DPB -------
    m.trap("read_sector", lambda mach: None)
    dpb_oracle = bytes.fromhex("f9 0002 0f 04 01 02 0100 02 70 0e00 ca02 03 0700")
    fields = 0xC100

    def read_sector(mach):
        mach.poke(mach.cpu.hl, image(0xF9, bytes(19)).get(mach.cpu.de, bytes(512)))
        mach.cpu.f &= ~0x01
    m.trap("read_sector", read_sector)
    m.poke(fields - 1, bytes(21))
    cpu = m.call("getdpb", hl=fields - 1, a=0, b=0xF9, c=0xF9)
    got = bytes(m.mem[fields:fields + 18])
    check(not carry(cpu) and got == dpb_oracle,
          f"GETDPB, BPB all zero: {got.hex()} (want the CF-3300's {dpb_oracle.hex()})")

    print()
    print("ALL PASS — the geometry comes from the media ID, as on both references"
          if not fails else f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
