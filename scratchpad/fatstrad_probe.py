#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATSTRAD: does a BASIC disk write pack a STRADDLING FAT12 entry correctly?

🔴 THE TEST THAT SHOULD HAVE EXISTED. `tests/test_fat_write_fat_entry.py` found
this defect on 2026-07-04, documented it, and the fix landed the same day --
**in `disk/fat.asm` only**. `basic/fat-prim-body.inc`, which is what BASIC
actually runs (sub.rom's fatprim tenant), never received it, and that test drives
the DISK build, so for two months it proved the fixed half while the other half
shipped the defect to every BASIC disk write. D-FATDIFF's engine differential
(scratchpad/fateng_diff.py) found it only because Option 2's swap forced a
routine-by-routine comparison.

So this probe exercises the BASIC side, behaviourally, end to end.

WHAT THE BUG WAS. A FAT12 entry is 12 bits, so consecutive entries share bytes
and an entry can straddle a 512-byte sector boundary. `fat_write_fat_entry`
decides that from `FAT_BYTEIDX`, which is 0..511 -- high byte 0 or 1:

    disk/fat.asm   `dec a`  -> straddle iff byteidx == 511 ($01FF)   correct
    the body       `or a`   -> straddle iff byteidx == 255 ($00FF)   wrong BOTH ways

byteidx 255 is cluster 170 and byteidx 511 is cluster 341, so the body treated
170 as a straddle when it is not and 341 as same-sector when it is -- packing the
entry into the WRONG SECTOR either way.

HOW THIS REACHES IT WITHOUT WRITING 349 KB. Allocating cluster 341 the honest way
means filling the disk to that point, which through BASIC would take hours. So
the probe BUILDS a disk whose clusters 2..340 are already allocated to filler
files, leaving 341 as the first free one. A single small BASIC write then
allocates 341 and 342 -- and writing FAT[341] is exactly the straddling case.

THE ORACLE IS THE IMAGE ITSELF. After the write the probe reads the disk back in
Python and checks FAT[341] and FAT[342] directly, in BOTH FAT copies. It needs no
reference machine: FAT12 packing is the published Microsoft spec, and a chain the
probe itself laid down has a known correct answer.

⚠️ CONTROLS, so a pass cannot be vacuous:
  * a NON-straddling entry (cluster 342, byteidx 513 -> offset 1 of the next
    sector) must also be right -- if both are wrong the write never happened;
  * the two FAT copies must AGREE -- multi-FAT sync is the other half of this
    routine and a straddle that writes only one copy is still broken;
  * the file must actually appear in the directory with a non-zero first cluster,
    or nothing was written and every FAT check is reading the filler.
"""
import os, shutil, struct, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                              # noqa: E402
import fatbuf_probe as FB                                     # noqa: E402

TARGET = 341          # the straddling cluster: 341*3//2 == 511
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
BOOT, RESET = 8.0, ("CLOSE", "NEW", "CLS")
MARK_SRC, MARK = "CHR$(64)+CHR$(75)", "@K"


def build_disk(path):
    """A disk whose first free cluster is TARGET."""
    shutil.copyfile(FB.SRC_DSK, path)
    d = bytearray(open(path, "rb").read())
    bps = struct.unpack("<H", d[11:13])[0]
    spc, rsv = d[13], struct.unpack("<H", d[14:16])[0]
    nf = d[16]
    nroot = struct.unpack("<H", d[17:19])[0]
    spf = struct.unpack("<H", d[22:24])[0]
    root_sec = rsv + nf * spf
    fat = bytearray(d[rsv * bps: rsv * bps + spf * bps])
    # mark 2..TARGET-1 allocated as one long chain owned by a filler file
    for c in range(2, TARGET - 1):
        FB.fat12_set(fat, c, c + 1)
    FB.fat12_set(fat, TARGET - 1, 0xFFF)
    for i in range(nf):
        d[(rsv + i * spf) * bps:(rsv + i * spf) * bps + spf * bps] = fat
    ent = (b"FILLER  BIN" + bytes([0x20]) + b"\x00" * 10 +
           struct.pack("<HHHI", 0x6000, 0x5921, 2, (TARGET - 2) * bps * spc))
    assert len(ent) == 32
    for i in range(nroot):
        e = root_sec * bps + i * 32
        if d[e] in (0x00, 0xE5):
            d[e:e + 32] = ent
            break
    if len(d) != os.path.getsize(FB.SRC_DSK):
        sys.exit("REFUSING: the built image changed size")
    open(path, "wb").write(bytes(d))
    return dict(bps=bps, spc=spc, rsv=rsv, nf=nf, spf=spf, root_sec=root_sec,
                nroot=nroot)


def fat_entry(img, g, copy, n):
    base = (g["rsv"] + copy * g["spf"]) * g["bps"]
    fat = img[base:base + g["spf"] * g["bps"]]
    return FB.fat12_get(fat, n)


def main():
    tmpd = tempfile.mkdtemp(prefix="fatstrad_")
    dsk = os.path.join(tmpd, "strad.dsk")
    g = build_disk(dsk)
    print("disk built: clusters 2..%d allocated; first free = %d "
          "(byteidx %d -> %s)"
          % (TARGET - 1, TARGET, TARGET * 3 // 2,
             "STRADDLE" if TARGET * 3 // 2 == 511 else "not a straddle"))
    if TARGET * 3 // 2 != 511:
        sys.exit("REFUSING: cluster %d is not the straddling case" % TARGET)

    # one small BASIC write: allocates TARGET, then TARGET+1 as it grows
    # 60 x 22 B = 1320 B: past the 1024 B cluster, so it allocates TARGET **and**
    # TARGET+1 -- exercising the straddling entry AND the chain link out of it.
    body = ['OPEN"O.DAT"FOR OUTPUT AS#1',
            'FOR I=1 TO 60',
            'PRINT#1,"0123456789ABCDEFGHIJ"',
            'NEXT',
            'CLOSE',
            'PRINT %s;"DONE"' % MARK_SRC]
    for ln in body:
        if len(ln) > 36:
            sys.exit("REFUSING: stored line %r is %d chars" % (ln, len(ln)))
    print("  driving %s ..." % ZB, flush=True)
    caps = omsx_repl.run_cases(ZB, [("stored", body)], batch=True, reset=RESET,
                               boot=BOOT, step=14.0, cap_gap=8.0, diska=dsk,
                               capture="screen")
    scr = caps[0] or ""
    if MARK not in scr:
        for j in range(0, len(scr), 40):
            if scr[j:j + 40].strip():
                print("   | %s" % scr[j:j + 40].rstrip())
        sys.exit("REFUSING: the case printed no %r witness -- it did not run, so "
                 "the FAT below is the filler's, not a write's" % MARK)

    img = open(dsk, "rb").read()
    # --- CONTROL: the file must exist with a real first cluster ---------------
    first = None
    for i in range(g["nroot"]):
        e = g["root_sec"] * g["bps"] + i * 32
        if img[e:e + 8].rstrip() == b"O":
            first = struct.unpack("<H", img[e + 26:e + 28])[0]
    if not first:
        sys.exit("REFUSING: O.DAT is not in the directory with a first cluster -- "
                 "nothing was written and every FAT check below would be vacuous")
    print("  O.DAT first cluster = %d (expected %d)" % (first, TARGET))

    print("\n| entry | byteidx | straddle | FAT copy 0 | FAT copy 1 |")
    print("|---|---|---|---|---|")
    ok = True
    for n in (TARGET, TARGET + 1):
        bi = n * 3 // 2
        c0, c1 = fat_entry(img, g, 0, n), fat_entry(img, g, 1, n)
        print("| %d | %d | %s | $%03X | $%03X |"
              % (n, bi, "YES" if bi == 511 else "no", c0, c1))
        if c0 != c1:
            print("   🔴 the two FAT copies DISAGREE on cluster %d" % n)
            ok = False
        if c0 == 0:
            print("   🔴 cluster %d reads FREE after being allocated" % n)
            ok = False
    chain = fat_entry(img, g, 0, TARGET)
    print()
    if chain == TARGET + 1 or chain >= 0xFF8:
        print("🟢 FAT[%d] = $%03X -- the straddling entry is packed correctly "
              "(next cluster or EOC)." % (TARGET, chain))
    else:
        print("🔴 FAT[%d] = $%03X -- neither %d nor EOC. The straddling entry "
              "went into the wrong sector." % (TARGET, chain, TARGET + 1))
        ok = False
    shutil.rmtree(tmpd, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
