#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: the sub-ROM's disk block transfers BLTVD / BLTDV / BLTMD / BLTDM -- probes/bios/spec/xsubbltd.asm.

One module for the case table, the disk image and the decoder, so the probe's layout cannot drift from its reading:
    python3 scratchpad/xsubbltd.py table              # the probe's case table (pasted between its CASES markers)
    python3 scratchpad/xsubbltd.py mkdsk OUT.dsk      # the image drive A starts with (never committed)
    python3 scratchpad/xsubbltd.py decode RUNFILE DSKDIR   # the capture + the files on each machine's image after
The image is made with tools/make_test_dsk.py's FAT12 writer (720 KB, our own boot sector): the files below.
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

BLTVD, BLTDV, BLTMD, BLTDM = 0x019D, 0x01A1, 0x01A5, 0x01A9
ENAME = {BLTVD: "BLTVD", BLTDV: "BLTDV", BLTMD: "BLTMD", BLTDM: "BLTDM"}
BLK = 0xF562
NAMES = 0x9E00          # the file names, copied to RAM (FNPTR must point at RAM: page 1 is BASIC's during the call)
ALT = 0x9F00            # the second block, for HL != $F562
# the names, in this order, from NAMES; a quoted BASIC string + 0, except DM3 (unquoted)
NAMELIST = [("dm1", b'"DM1.BIN"'), ("dm2", b'"DM2.BIN"'), ("dm3", b"DM3.BIN"), ("nof", b'"NOFILE.BIN"'),
            ("bsv", b'"BSAVED.BIN"'), ("raw", b'"RAWDATA.BIN"'), ("dv1", b'"DV1.PIC"'), ("dv5", b'"DV5.PIC"'),
            ("arr", b'"ARR.PIC"'), ("fix", b'"FIX.BIN"'), ("hlb", b'"HLB.BIN"'), ("long", b'"LONG.BIN"'),
            ("dvx", b'"DVX.PIC"'), ("dvg", b'"DVG.PIC"')]
NADDR = {}
_a = NAMES
for _k, _v in NAMELIST:
    NADDR[_k] = _a
    _a += len(_v) + 1

# host-made files on the image
BSV_START, BSV_END = 0x9420, 0x942F
HOSTFILES = {
    "RAWDATA.BIN": bytes(0xC0 + i for i in range(64)),                       # no header at all
    "BSAVED.BIN": struct.pack("<BHHH", 0xFE, BSV_START, BSV_END, BSV_START) + bytes(0xD0 + i for i in range(16)),
    "ARR.PIC": struct.pack("<HH", 4, 2) + bytes(range(0xA1, 0xA9)),          # a RAM array (BLTVM's form), no $FE
    "LONG.BIN": bytes([0x33]) * 300,
}


def src(i):             # the RAM source $9000 + i
    return (i * 7 + 0x11) & 0xFF


def block(**w):
    """15 bytes: garbage $51.. everywhere, the named words / bytes set."""
    b = bytearray(0x51 + i for i in range(15))
    off = {"w0": 0, "w2": 2, "w4": 4, "w6": 6, "w8": 8, "w10": 10}
    for k, v in w.items():
        if k in off:
            struct.pack_into("<H", b, off[k], v)
        elif k == "cd":
            b[12] = v
        elif k == "arg":
            b[13] = v
        elif k == "log":
            b[14] = v
    return bytes(b)


def dm(sp, ep, fn):     # BLTDM: SPTR, EPTR, FNPTR
    return block(w0=sp, w2=ep, w4=NADDR[fn])


def md(fn, sp, ep):     # BLTMD: FNPTR, dummy, SPTR, EPTR
    return block(w0=NADDR[fn], w4=sp, w6=ep)


def dv(sx, sy, fn, nx, ny, arg=0):     # BLTDV: SX, SY, FNPTR, dummy, NX, NY (ARG not listed, but see case 20)
    return block(w0=sx, w2=sy, w4=NADDR[fn], w8=nx, w10=ny, arg=arg)


def vd(fn, dx, dy, log, arg=0):     # BLTVD: FNPTR, dummy, DX, DY, (NX, NY from the file), CDUMMY, ARG, LOGOP
    return block(w0=NADDR[fn], w4=dx, w6=dy, arg=arg, log=log)


# (label, entry, HL, SCRMOD, block, preset, wx, wy, ram, raddr)
#   ram 1: the window is 96 bytes of RAM from raddr, preset $EE; ram 0: 6 VRAM lines x 16 bytes from (wx, wy), preset;
#   ram 2: the same VRAM window, read only (the source rectangle itself, set by the probe)
CASES = [
    ("BLTDM $9000-$903F -> \"DM1.BIN\"", BLTDM, BLK, 8, dm(0x9000, 0x903F, "dm1"), 0, 0, 0, 1, 0x9000),
    ("BLTDM $9010-$9010 -> \"DM2.BIN\"", BLTDM, BLK, 8, dm(0x9010, 0x9010, "dm2"), 0, 0, 0, 1, 0x9000),
    ("BLTDM $9000-$900F -> DM3.BIN unquoted", BLTDM, BLK, 8, dm(0x9000, 0x900F, "dm3"), 0, 0, 0, 1, 0x9000),
    ("BLTMD \"DM1.BIN\" -> $9200-$9263", BLTMD, BLK, 8, md("dm1", 0x9200, 0x9263), 0, 0, 0, 1, 0x91F8),
    ("BLTMD \"DM1.BIN\" -> $9300-$930F (range < file)", BLTMD, BLK, 8, md("dm1", 0x9300, 0x930F), 0, 0, 0, 1, 0x92F8),
    ("BLTMD \"BSAVED.BIN\" ($FE, $9420-$942F) -> $9400-$94FF", BLTMD, BLK, 8, md("bsv", 0x9400, 0x94FF), 0, 0, 0, 1,
     0x93F8),
    ("BLTMD \"RAWDATA.BIN\" (no header) -> $9500-$95FF", BLTMD, BLK, 8, md("raw", 0x9500, 0x95FF), 0, 0, 0, 1, 0x94F8),
    ("BLTMD \"NOFILE.BIN\" (missing) -> $9600-$96FF", BLTMD, BLK, 8, md("nof", 0x9600, 0x96FF), 0, 0, 0, 1, 0x95F8),
    ("BLTMD \"DM1.BIN\" -> $9600-$96FF (after the error)", BLTMD, BLK, 8, md("dm1", 0x9600, 0x96FF), 0, 0, 0, 1,
     0x95F8),
    ("BLTDV SCREEN 8 (8,8) 8x4 -> \"DV1.PIC\"", BLTDV, BLK, 8, dv(8, 8, "dv1", 8, 4), 0, 8, 7, 2, 0),
    ("BLTVD \"DV1.PIC\" -> (40,8) LOGOP 0", BLTVD, BLK, 8, vd("dv1", 40, 8, 0), 0, 36, 7, 0, 0),
    ("BLTVD \"DV1.PIC\" -> (40,8) LOGOP 3 over $FF", BLTVD, BLK, 8, vd("dv1", 40, 8, 3), 0xFF, 36, 7, 0, 0),
    ("BLTVD \"ARR.PIC\" (RAM array, no $FE) -> (40,8)", BLTVD, BLK, 8, vd("arr", 40, 8, 0), 0, 36, 7, 0, 0),
    ("BLTDV SCREEN 5 (8,8) 7x3 -> \"DV5.PIC\"", BLTDV, BLK, 5, dv(8, 8, "dv5", 7, 3), 0, 8, 7, 2, 0),
    ("BLTVD \"DV5.PIC\" -> SCREEN 5 (40,8)", BLTVD, BLK, 5, vd("dv5", 40, 8, 0), 0, 32, 7, 0, 0),
    ("BLTVD \"NOFILE.BIN\" (missing) -> (40,8)", BLTVD, BLK, 8, vd("nof", 40, 8, 0), 0, 36, 7, 0, 0),
    ("BLTDM HL=$9F00 (\"HLB.BIN\" $9000-$9009); $F562: \"FIX.BIN\" $9000-$903F", BLTDM, ALT, 8,
     dm(0x9000, 0x903F, "fix"), 0, 0, 0, 1, 0x9000),
    ("BLTDM $9000-$900F -> \"LONG.BIN\" (exists, 300 B)", BLTDM, BLK, 8, dm(0x9000, 0x900F, "long"), 0, 0, 0, 1,
     0x9000),
    ("BLTMD \"DM1.BIN\" -> $9700-$96FF (EPTR < SPTR)", BLTMD, BLK, 8, md("dm1", 0x9700, 0x96FF), 0, 0, 0, 1, 0x96F8),
    ("BLTVD \"DV1.PIC\" -> (252,8): past the right edge", BLTVD, BLK, 8, vd("dv1", 252, 8, 0), 0, 240, 7, 0, 0),
    ("BLTDV SCREEN 8 (15,8) 8x4 ARG $04 (DIX) -> \"DVX.PIC\"", BLTDV, BLK, 8, dv(15, 8, "dvx", 8, 4, arg=0x04), 0, 8,
     7, 2, 0),
    ("BLTDV SCREEN 8 (8,8) 8x4 ARG $5E (MXC MXS DIY DIX EQ) -> \"DVG.PIC\"", BLTDV, BLK, 8,
     dv(8, 8, "dvg", 8, 4, arg=0x5E), 0, 8, 7, 2, 0),
]
ALTBLOCK = dm(0x9000, 0x9009, "hlb")


def table():
    out = ["; ---- CASES BEGIN (generated: python3 scratchpad/xsubbltd.py table) ----", "names_rom:"]
    for k, v in NAMELIST:
        out.append(f"                db      {', '.join(f'${c:02X}' for c in v)}, 0   ; {k} {v.decode()}")
    out.append("names_end:")
    out.append(f"alt_rom:        db      {', '.join(f'${c:02X}' for c in ALTBLOCK)}")
    out.append("cases:")
    for i, (lab, ent, hl, scr, blk, pre, wx, wy, ram, ra) in enumerate(CASES):
        out.append(f"                dw      ${ent:04X}, ${hl:04X}   ; {i} {lab}")
        out.append(f"                db      {scr}, {', '.join(f'${c:02X}' for c in blk)}, ${pre:02X}")
        out.append(f"                dw      {wx}")
        out.append(f"                db      {wy}, {ram}")
        out.append(f"                dw      ${ra:04X}")
    out.append("                dw      0")
    out.append("; ---- CASES END ----")
    return "\n".join(out)


def mkdsk(path):
    import make_test_dsk as m
    img = m.Fat12Image()
    for name, data in HOSTFILES.items():
        n, e = name.split(".")
        img.add_file(n, e, data)
    open(path, "wb").write(img.finish())
    print(f"wrote {path}")


def files(dsk):
    """{NAME.EXT: bytes} from a 720 KB FAT12 image: root directory + FAT chains (the host-side read-back)."""
    import make_test_dsk as m
    d = open(dsk, "rb").read()
    fat = d[m.FIRST_FAT * m.SECTOR:(m.FIRST_FAT + m.SEC_PER_FAT) * m.SECTOR]

    def nxt(c):
        i = c * 3 // 2
        v = fat[i] | fat[i + 1] << 8
        return v >> 4 if c & 1 else v & 0xFFF
    out = {}
    for k in range(m.ROOT_ENTRIES):
        e = d[m.FIRST_ROOT * m.SECTOR + 32 * k:][:32]
        if e[0] == 0:
            break
        if e[0] == 0xE5 or e[11] & 0x18:
            continue
        name = e[:8].decode("latin1").rstrip() + "." + e[8:11].decode("latin1").rstrip()
        c, size = struct.unpack_from("<H", e, 26)[0], struct.unpack_from("<I", e, 28)[0]
        data, guard = b"", 0
        while 2 <= c < 0xFF8 and guard < 800:
            s = (m.FIRST_DATA + (c - 2) * m.SEC_PER_CLUS) * m.SECTOR
            data += d[s:s + m.CLUSTER_BYTES]
            c, guard = nxt(c), guard + 1
        out[name] = data[:size]
    return out


def decode(runfile, dskdir):
    txt = open(runfile).read()
    for blk in re.split(r"^===== ", txt, flags=re.M)[1:]:
        hdr = blk.split("\n", 1)[0]
        m = re.match(r".*\.asm (\w+): (\S+) vs (\S+) =====", hdr)
        if not m:
            continue
        row, machines = m.group(1), {"ref": m.group(2), "ours": m.group(3)}
        for side in ("ref", "ours"):
            mc = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
            print(f"# {row} {side} {machines[side]}")
            if not mc:
                print("  NO READING")
                continue
            b = bytes.fromhex(mc.group(1)) + bytes(4000)
            print(f"  finished={b[0]:02X} cases={b[1]}")
            for k in range(b[1]):
                r = b[2 + 256 * k: 258 + 256 * k]
                lab, ent, hl, scr, blkin, pre, wx, wy, ram, ra = CASES[r[0]]
                f_, a_, c_, b_, e_, d_, l_, h_ = r[4:12]
                ix, iy = struct.unpack_from("<HH", r, 12)
                err = f"H.ERRO E={r[2]}" if r[1] & 1 else "no H.ERRO"
                print(f"  [{r[0]}] {lab}: {err}; A={a_:02X} F={f_:02X} BC={b_:02X}{c_:02X} DE={d_:02X}{e_:02X} "
                      f"HL={h_:02X}{l_:02X} IX={ix:04X} IY={iy:04X} IFF={r[3]}")
                after = r[16:31]
                chg = [f"+{i}:{blkin[i]:02X}->{after[i]:02X}" for i in range(15) if after[i] != blkin[i]]
                print(f"     block after: {after.hex()}  changed: {' '.join(chg) or 'none'}")
                v = r[128:242]
                print(f"     VDP after: R#32-46 {v[32:47].hex()} S#2 {v[66]:02X} R#14 {v[14]:02X}")
                w = r[32:128]
                if ram == 1:
                    print(f"     RAM ${ra:04X}: " + " ".join(f"{v:02X}" for v in w[:48]))
                    print(f"     RAM ${ra + 48:04X}: " + " ".join(f"{v:02X}" for v in w[48:]))
                else:
                    for y in range(6):
                        print("     " + " ".join(".." if v == pre and ram == 0 else f"{v:02X}"
                                                  for v in w[16 * y: 16 * y + 16]))
            img = os.path.join(dskdir, machines[side] + ".dsk")
            if os.path.exists(img):
                fs = files(img)
                print(f"  files on {machines[side]}'s drive A after the run (host-side read of the image):")
                for n, data in fs.items():
                    tag = " (host-made)" if n in HOSTFILES and HOSTFILES[n] == data else ""
                    print(f"     {n:13s} {len(data):4d} B{tag}: {data[:80].hex()}{'..' if len(data) > 80 else ''}")
            else:
                print(f"  (no image kept for {machines[side]})")


if __name__ == "__main__":
    if sys.argv[1] == "table":
        print(table())
    elif sys.argv[1] == "mkdsk":
        mkdsk(sys.argv[2])
    elif sys.argv[1] == "decode":
        decode(sys.argv[2], sys.argv[3])
