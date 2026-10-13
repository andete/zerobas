#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""zerobas for openMSX: the download (`make dist`) and the install (`make install-openmsx`).

🏗️ Joost, 2026-10-13: the primary use is openMSX, and the download ships the
READY-MADE main ROM ("I think using the ready made Rom makes more sense"), so it
works whatever C-BIOS a given openMSX release bundles. C-BIOS's BSD-2 notice
travels with it (cbios-repack/LICENSE.C-BIOS).

The layout is openMSX's own for its C-BIOS machines -- flat machine files next
to a folder of ROMs, referenced by RELATIVE filename, so it works from any
openMSX user folder and nothing points back into this checkout:

    share/machines/zerobas_MSX1.xml          no disk (the VG-8020's shape)
    share/machines/zerobas_MSX1_disk.xml     + zerobas-disk behind a WD2793 in 3-1
    share/machines/zerobas/*.rom             main, logo, sub, sub2, disk
    share/machines/zerobas/LICENSE*, README.txt

The machine definition is the GATED one (tools/install-repack-machine.py
`config()`, the machines every acceptance suite runs on) -- not
install-openmsx-machine.py's, whose BASIC machines had no sub2 in 3-3.

THE MAIN ROM: build/zerobas-main-eu.rom when it exists (a build with a C-BIOS
checkout, CBIOS=<path>, or CI). Otherwise it is made here from the TRACKED patch
and openMSX's own bundled C-BIOS EU ROM -- what openMSX would do at load time --
and checked against the tracked .bps, which records the CRC32 of the C-BIOS it
expects and of the ROM it must produce: a different C-BIOS is REFUSED, never
patched into a plausible-looking wrong ROM.

    python3 tools/make_dist.py                 # -> build/dist/ + build/zerobas-openmsx.zip
    python3 tools/make_dist.py --install       # ...and copy into openMSX's user share
    python3 tools/make_dist.py --install --user <folder>
    python3 tools/make_dist.py --logo <rom>    # the C-BIOS logo ROM, when no openMSX
    python3 tools/make_dist.py --selftest
"""
import argparse
import importlib.util
import os
import shutil
import struct
import sys
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import openmsx_paths  # noqa: E402

BUILD = os.path.join(ROOT, "build")
DIST = os.path.join(BUILD, "dist")
ZIP = os.path.join(BUILD, "zerobas-openmsx.zip")
IPS = os.path.join(ROOT, "zerobas-main-eu.ips")
BPS = os.path.join(ROOT, "zerobas-main-eu.bps")
MACHINES = (("zerobas_MSX1", False, "zerobas MSX1 BASIC"),
            ("zerobas_MSX1_disk", True, "zerobas MSX1 BASIC with a disk drive"))


def _irm():
    spec = importlib.util.spec_from_file_location(
        "install_repack_machine", os.path.join(HERE, "install-repack-machine.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def apply_ips(base: bytes, patch: bytes) -> bytes:
    """The IPS format: 'PATCH', records [offset:3][size:2][data] or an RLE record
    (size 0: [count:2][byte]), 'EOF', an optional 3-byte truncation length."""
    if patch[:5] != b"PATCH":
        raise ValueError("not an IPS patch")
    out, i = bytearray(base), 5
    while patch[i:i + 3] != b"EOF":
        off = int.from_bytes(patch[i:i + 3], "big")
        size = int.from_bytes(patch[i + 3:i + 5], "big")
        i += 5
        if size:
            data = patch[i:i + size]
            i += size
        else:
            n = int.from_bytes(patch[i:i + 2], "big")
            data = patch[i + 2:i + 3] * n
            i += 3
        if off + len(data) > len(out):
            out.extend(b"\0" * (off + len(data) - len(out)))
        out[off:off + len(data)] = data
    tail = patch[i + 3:]
    if len(tail) == 3:
        del out[int.from_bytes(tail, "big"):]
    return bytes(out)


def bps_crcs(bps: bytes):
    """(source CRC32, target CRC32) from a BPS patch's 12-byte footer."""
    if bps[:4] != b"BPS1":
        raise ValueError("not a BPS patch")
    src, dst, _ = struct.unpack("<III", bps[-12:])
    return src, dst


def main_rom_from_patch(stock_path: str) -> bytes:
    base = open(stock_path, "rb").read()
    want_src, want_dst = bps_crcs(open(BPS, "rb").read())
    if zlib.crc32(base) != want_src:
        sys.exit(f"REFUSED: {stock_path} is not the C-BIOS release zerobas's patch was "
                 f"made from (CRC32 {zlib.crc32(base):08x}, the patch expects "
                 f"{want_src:08x}). Build the main ROM from a C-BIOS checkout instead: "
                 f"`make build/zerobas-main-eu.rom CBIOS=<path>`.")
    rom = apply_ips(base, open(IPS, "rb").read())
    if zlib.crc32(rom) != want_dst:
        sys.exit(f"REFUSED: the patched ROM's CRC32 {zlib.crc32(rom):08x} is not the "
                 f"{want_dst:08x} the .bps records -- the tracked .ips and .bps disagree.")
    return rom


README = """zerobas for openMSX
===================

zerobas is a clean-room MSX1 BASIC: https://github.com/andete/zerobas

Install: copy the `share` folder of this archive into openMSX's user folder
(~/.openMSX on Linux and macOS, Documents/openMSX on Windows), merging it with
the `share` folder already there. Then choose a machine in openMSX:

  zerobas_MSX1        BASIC only
  zerobas_MSX1_disk   with a disk drive (insert a disk image as drive A;
                      test720.dsk in this archive has a few files on it)

or from a terminal:  openmsx -machine zerobas_MSX1

The prompt is `ZB` where a real MSX says `Ok`.

Licences: zerobas is 0BSD (LICENSE). The main ROM contains C-BIOS, BSD-2-Clause
(LICENSE.C-BIOS). Built from {rev}.
"""


def build(logo: str | None = None) -> str:
    irm = _irm()
    rom_dir = os.path.join(DIST, "share", "machines", "zerobas")
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(rom_dir)
    merged = os.path.join(BUILD, "zerobas-main-eu.rom")
    if os.path.isfile(merged):
        main_rom, how = open(merged, "rb").read(), "build/zerobas-main-eu.rom"
    else:
        stock = openmsx_paths.find_cbios_rom(["cbios_main_msx1_eu.rom"])
        if not stock:
            sys.exit("no build/zerobas-main-eu.rom and no openMSX C-BIOS to patch: "
                     "install openMSX, or build with CBIOS=<checkout>")
        main_rom, how = main_rom_from_patch(stock), f"the tracked patch on {stock}"
    open(os.path.join(rom_dir, "zerobas-main-eu.rom"), "wb").write(main_rom)
    for n in ("sub.rom", "sub2.rom", "disk.rom"):
        src = os.path.join(BUILD, n)
        if not os.path.isfile(src):
            sys.exit(f"missing build/{n} -- run `make` first")
        shutil.copyfile(src, os.path.join(rom_dir, n))
    shutil.copyfile(logo or irm.find_logo(), os.path.join(rom_dir, "cbios_logo_msx1.rom"))
    shutil.copyfile(os.path.join(ROOT, "LICENSE"), os.path.join(rom_dir, "LICENSE"))
    shutil.copyfile(os.path.join(ROOT, "cbios-repack", "LICENSE.C-BIOS"),
                    os.path.join(rom_dir, "LICENSE.C-BIOS"))
    rev = os.popen(f"git -C {ROOT} describe --always --dirty 2>/dev/null").read().strip()
    open(os.path.join(rom_dir, "README.txt"), "w").write(README.format(rev=rev or "?"))
    # at the archive's root too, beside a disk image to try the disk machine with
    shutil.copyfile(os.path.join(rom_dir, "README.txt"), os.path.join(DIST, "README.txt"))
    dsk = os.path.join(ROOT, "disk", "test720.dsk")
    if os.path.isfile(dsk):
        shutil.copyfile(dsk, os.path.join(DIST, "test720.dsk"))
    rel = lambda n: "zerobas/" + n
    for name, disk, desc in MACHINES:
        cfg = irm.config(rel("zerobas-main-eu.rom"), rel("cbios_logo_msx1.rom"),
                         rel("disk.rom") if disk else "", rel("sub.rom"), rel("sub2.rom"))
        old = "<code>repack disk (acceptance)</code>"
        if cfg.count(old) != 1:
            sys.exit("install-repack-machine.config() changed shape: <code> not found")
        cfg = cfg.replace(old, f"<code>{name}</code>\n    <description>{desc}</description>")
        open(os.path.join(DIST, "share", "machines", name + ".xml"), "w").write(cfg)
    if os.path.exists(ZIP):
        os.unlink(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, fs in os.walk(DIST):
            for f in sorted(fs):
                p = os.path.join(d, f)
                z.write(p, os.path.relpath(p, DIST))
    print(f"main ROM from {how}")
    print(f"wrote {os.path.relpath(DIST, ROOT)}/ and {os.path.relpath(ZIP, ROOT)}")
    return DIST


def install(user: str | None):
    dest = os.path.join(openmsx_paths.find_user(user), "share")
    src = os.path.join(DIST, "share")
    for d, _, fs in os.walk(src):
        for f in fs:
            p = os.path.join(d, f)
            q = os.path.join(dest, os.path.relpath(p, src))
            os.makedirs(os.path.dirname(q), exist_ok=True)
            shutil.copyfile(p, q)
    print(f"installed into {dest}: machines "
          + ", ".join(n for n, _, _ in MACHINES))


def selftest() -> int:
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and bool(cond)
    base = bytes(range(16))
    p = b"PATCH" + (3).to_bytes(3, "big") + (2).to_bytes(2, "big") + b"\xAA\xBB" \
        + (10).to_bytes(3, "big") + (0).to_bytes(2, "big") + (3).to_bytes(2, "big") + b"\xCC" + b"EOF"
    r = apply_ips(base, p)
    arm("D1 an IPS data record and an RLE record land where they say",
        r[3:5] == b"\xAA\xBB" and r[10:13] == b"\xCC" * 3 and r[:3] == base[:3]
        and len(r) == 16)
    arm("D1 NEGATIVE: a non-IPS patch is refused", _raises(lambda: apply_ips(base, b"XX")))
    if os.path.isfile(IPS) and os.path.isfile(BPS):
        src, dst = bps_crcs(open(BPS, "rb").read())
        arm("D2 the tracked .bps names a source and a target CRC", src and dst and src != dst)
        stock = openmsx_paths.find_cbios_rom(["cbios_main_msx1_eu.rom"])
        if stock and zlib.crc32(open(stock, "rb").read()) == src:
            rom = main_rom_from_patch(stock)
            arm("D3 the tracked .ips on openMSX's C-BIOS gives the .bps's target", zlib.crc32(rom) == dst)
            merged = os.path.join(BUILD, "zerobas-main-eu.rom")
            if os.path.isfile(merged):
                arm("D3 ...which is byte-identical to the built merged ROM",
                    rom == open(merged, "rb").read())
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 2


def _raises(fn) -> bool:
    try:
        fn()
    except Exception:
        return True
    return False


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--install", action="store_true", help="also copy into openMSX")
    ap.add_argument("--user", default=None, help="openMSX user folder")
    ap.add_argument("--logo", default=None, help="the C-BIOS logo ROM (default: openMSX's)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    build(a.logo)
    if a.install:
        install(a.user)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
