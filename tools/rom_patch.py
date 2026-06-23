#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Make, apply, and inspect ROM patches in IPS and BPS formats.

Used by the zerobas-tape component to ship the clean-room cassette routines as a
*patch* against a pristine C-BIOS ROM rather than a modified ROM: the patch
carries only our added bytes, the user supplies their own stock C-BIOS.

  python3 tools/rom_patch.py make pristine.rom modified.rom out.ips   # or out.bps
  python3 tools/rom_patch.py apply pristine.rom out.bps result.rom
  python3 tools/rom_patch.py info out.bps

Format is taken from the output extension on `make` (.ips / .bps) and autodetected
from the magic on `apply`/`info`.

IPS  -- classic, universally supported, but carries *no source checksum*: applying
        it to the wrong ROM silently corrupts. `make`/`info` print the target sha1
        to compensate. Records are (24-bit offset, 16-bit length, data); 16 MB max.
BPS  -- newer; embeds CRC32 of source, target, and the patch itself, so applying to
        the wrong ROM *fails cleanly*. Encoded here with just SourceRead/TargetRead
        actions (source and target are the same-size ROM), which is optimal for a
        sparse in-place diff like ours.
"""
from __future__ import annotations

import argparse, hashlib, re, struct, sys, zlib

# ---------------------------------------------------------------- shared diff

def _runs_exact(a: bytes, b: bytes):
    """Yield (offset, b-slice) for each maximal run of *consecutive* differing
    bytes. Used by BPS, where identical spans are free (SourceRead)."""
    n = len(b)
    i = 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        s = i
        while i < n and a[i] != b[i]:
            i += 1
        yield s, b[s:i]


def _runs_merged(a: bytes, b: bytes, gap: int = 8):
    """Like _runs_exact but merges diffs separated by <= `gap` identical bytes
    into one record. Used by IPS, where every record costs a 5-byte header so a
    few literal same-bytes are cheaper than a fresh record."""
    n = len(b)
    i = 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        start = last = i
        i += 1
        while i < n and i - last <= gap:
            if a[i] != b[i]:
                last = i
            i += 1
        yield start, b[start:last + 1]


# ------------------------------------------------------------------- IPS

IPS_MAGIC, IPS_EOF, IPS_MAXLEN = b"PATCH", b"EOF", 0xFFFF


def make_ips(pristine: bytes, modified: bytes) -> bytes:
    if len(modified) > len(pristine):
        raise SystemExit("modified ROM larger than pristine; unexpected for a "
                         "fixed-size C-BIOS image")
    out = bytearray(IPS_MAGIC)
    for off, data in _runs_merged(pristine, modified):
        if off == 0x454F46:                 # avoid the "EOF" offset collision
            off -= 1
            data = modified[off:off + len(data) + 1]
        for s in range(off, off + len(data), IPS_MAXLEN):
            chunk = modified[s:min(s + IPS_MAXLEN, off + len(data))]
            out += bytes([(s >> 16) & 0xFF, (s >> 8) & 0xFF, s & 0xFF])
            out += bytes([(len(chunk) >> 8) & 0xFF, len(chunk) & 0xFF])
            out += chunk
    out += IPS_EOF
    return bytes(out)


def apply_ips(pristine: bytes, patch: bytes) -> bytes:
    if patch[:5] != IPS_MAGIC:
        raise SystemExit("not an IPS patch (missing PATCH header)")
    rom = bytearray(pristine)
    p = 5
    while patch[p:p + 3] != IPS_EOF:
        off = (patch[p] << 16) | (patch[p + 1] << 8) | patch[p + 2]
        size = (patch[p + 3] << 8) | patch[p + 4]
        p += 5
        if size == 0:                        # RLE
            rsize = (patch[p] << 8) | patch[p + 1]
            rom[off:off + rsize] = bytes([patch[p + 2]]) * rsize
            p += 3
        else:
            rom[off:off + size] = patch[p:p + size]
            p += size
    return bytes(rom)


def records_ips(patch: bytes):
    p = 5
    while patch[p:p + 3] != IPS_EOF:
        off = (patch[p] << 16) | (patch[p + 1] << 8) | patch[p + 2]
        size = (patch[p + 3] << 8) | patch[p + 4]
        p += 5
        if size == 0:
            yield off, ((patch[p] << 8) | patch[p + 1]), "RLE"
            p += 3
        else:
            yield off, size, "data"
            p += size


# ------------------------------------------------------------------- BPS

BPS_MAGIC = b"BPS1"


def _vint_encode(n: int) -> bytes:
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def _vint_decode(buf: bytes, p: int):
    data, shift = 0, 1
    while True:
        x = buf[p]; p += 1
        data += (x & 0x7F) * shift
        if x & 0x80:
            return data, p
        shift <<= 7
        data += shift


def make_bps(source: bytes, target: bytes, metadata: bytes = b"") -> bytes:
    out = bytearray(BPS_MAGIC)
    out += _vint_encode(len(source))
    out += _vint_encode(len(target))
    out += _vint_encode(len(metadata))
    out += metadata
    pos = 0
    for s, data in _runs_exact(source, target):
        if s > pos:                               # SourceRead (cmd 0)
            out += _vint_encode((((s - pos) - 1) << 2) | 0)
        out += _vint_encode(((len(data) - 1) << 2) | 1)   # TargetRead (cmd 1)
        out += data
        pos = s + len(data)
    if pos < len(target):
        out += _vint_encode((((len(target) - pos) - 1) << 2) | 0)
    out += struct.pack("<I", zlib.crc32(source) & 0xFFFFFFFF)
    out += struct.pack("<I", zlib.crc32(target) & 0xFFFFFFFF)
    out += struct.pack("<I", zlib.crc32(bytes(out)) & 0xFFFFFFFF)
    return bytes(out)


def apply_bps(source: bytes, patch: bytes) -> bytes:
    if patch[:4] != BPS_MAGIC:
        raise SystemExit("not a BPS patch (missing BPS1 header)")
    if zlib.crc32(patch[:-4]) & 0xFFFFFFFF != struct.unpack_from("<I", patch, len(patch) - 4)[0]:
        raise SystemExit("BPS patch is corrupt (patch checksum mismatch)")
    src_crc = struct.unpack_from("<I", patch, len(patch) - 12)[0]
    tgt_crc = struct.unpack_from("<I", patch, len(patch) - 8)[0]
    if zlib.crc32(source) & 0xFFFFFFFF != src_crc:
        raise SystemExit("source ROM does not match this patch (CRC32 mismatch) -- "
                         "wrong base ROM")
    p = 4
    src_size, p = _vint_decode(patch, p)
    tgt_size, p = _vint_decode(patch, p)
    meta_size, p = _vint_decode(patch, p)
    p += meta_size
    out = bytearray()
    src_rel = tgt_rel = 0
    end = len(patch) - 12
    while p < end:
        action, p = _vint_decode(patch, p)
        cmd, length = action & 3, (action >> 2) + 1
        if cmd == 0:                                  # SourceRead
            out += source[len(out):len(out) + length]
        elif cmd == 1:                                # TargetRead
            out += patch[p:p + length]; p += length
        elif cmd == 2:                                # SourceCopy
            off, p = _vint_decode(patch, p)
            src_rel += -(off >> 1) if off & 1 else (off >> 1)
            out += source[src_rel:src_rel + length]; src_rel += length
        else:                                         # TargetCopy
            off, p = _vint_decode(patch, p)
            tgt_rel += -(off >> 1) if off & 1 else (off >> 1)
            for _ in range(length):
                out.append(out[tgt_rel]); tgt_rel += 1
    if len(out) != tgt_size:
        raise SystemExit("BPS apply produced wrong target size")
    if zlib.crc32(bytes(out)) & 0xFFFFFFFF != tgt_crc:
        raise SystemExit("BPS apply target checksum mismatch (patch/base corrupt)")
    return bytes(out)


def records_bps(patch: bytes):
    p = 4
    for _ in range(3):
        _, p = _vint_decode(patch, p)
    # re-read to skip metadata properly
    p = 4
    _, p = _vint_decode(patch, p)
    _, p = _vint_decode(patch, p)
    meta_size, p = _vint_decode(patch, p)
    p += meta_size
    out_pos = 0
    end = len(patch) - 12
    while p < end:
        action, p = _vint_decode(patch, p)
        cmd, length = action & 3, (action >> 2) + 1
        name = ("SourceRead", "TargetRead", "SourceCopy", "TargetCopy")[cmd]
        if cmd == 1:
            yield out_pos, length, name
            p += length
        elif cmd in (2, 3):
            _, p = _vint_decode(patch, p)
            yield out_pos, length, name
        else:
            yield out_pos, length, name
        out_pos += length


# ----------------------------------------------------- forge from regions
# Build a patch from explicit (offset, data) regions rather than by diffing two
# full ROMs. This lets the zerobas-tape patch be built from *our* assembled code
# alone (tape/tape.asm) -- no C-BIOS ROM is needed to make the IPS. A
# stock ROM is still required for BPS, which embeds source/target CRC32.

def apply_regions(source: bytes, regions) -> bytes:
    rom = bytearray(source)
    for off, data in regions:
        rom[off:off + len(data)] = data
    return bytes(rom)


def make_ips_regions(regions) -> bytes:
    """One IPS record per region, straight from the bytes -- no source ROM."""
    out = bytearray(IPS_MAGIC)
    for off, data in regions:
        if not data:
            continue
        if off <= 0x454F46 < off + len(data):
            raise SystemExit("region overlaps the IPS 'EOF' offset; unsupported")
        s = 0
        while s < len(data):
            chunk = data[s:s + IPS_MAXLEN]
            o = off + s
            out += bytes([(o >> 16) & 0xFF, (o >> 8) & 0xFF, o & 0xFF])
            out += bytes([(len(chunk) >> 8) & 0xFF, len(chunk) & 0xFF])
            out += chunk
            s += len(chunk)
    out += IPS_EOF
    return bytes(out)


def make_bps_regions(source: bytes, regions):
    target = apply_regions(source, regions)
    return make_bps(source, target), target


def _load_symbols(path: str) -> dict:
    syms = {}
    if path:
        for line in open(path):
            m = re.match(r"\s*(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", line)
            if m:
                syms[m.group(1)] = int(m.group(2), 16)
    return syms


# ------------------------------------------------------------------- CLI

def _fmt_of_patch(patch: bytes) -> str:
    if patch[:5] == IPS_MAGIC:
        return "ips"
    if patch[:4] == BPS_MAGIC:
        return "bps"
    raise SystemExit("unrecognised patch format (not IPS or BPS)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("pristine"); m.add_argument("modified"); m.add_argument("out")
    a = sub.add_parser("apply"); a.add_argument("pristine"); a.add_argument("patch"); a.add_argument("out")
    i = sub.add_parser("info"); i.add_argument("patch")
    f = sub.add_parser("forge", help="build a patch from explicit regions of an assembled blob")
    f.add_argument("out")
    f.add_argument("--bin", required=True, help="assembled binary (pasmo --bin output)")
    f.add_argument("--base", required=True, help="address the blob's first byte maps to")
    f.add_argument("--sym", help="pasmo symbol file; lets START/END be label names")
    f.add_argument("--region", action="append", required=True, metavar="START:END",
                   help="absolute address range to extract (hex/dec/label); repeatable")
    f.add_argument("--source", help="stock ROM (patch target) for BPS CRC32 + verification")
    args = ap.parse_args()

    if args.cmd == "make":
        pr = open(args.pristine, "rb").read()
        mo = open(args.modified, "rb").read()
        fmt = "bps" if args.out.lower().endswith(".bps") else "ips"
        patch = make_bps(pr, mo) if fmt == "bps" else make_ips(pr, mo)
        open(args.out, "wb").write(patch)
        if (apply_bps if fmt == "bps" else apply_ips)(pr, patch) != mo:
            raise SystemExit("ERROR: patch does not reproduce the modified ROM")
        nrec = len(list(records_bps(patch) if fmt == "bps" else records_ips(patch)))
        print(f"wrote {args.out}: {fmt.upper()}, {nrec} records, {len(patch)} bytes")
        print(f"  target (pristine) sha1: {hashlib.sha1(pr).hexdigest()}")
        print(f"  result (modified) sha1: {hashlib.sha1(mo).hexdigest()}")
        if fmt == "bps":
            print(f"  embedded CRC32 source/target: "
                  f"{zlib.crc32(pr)&0xFFFFFFFF:08x}/{zlib.crc32(mo)&0xFFFFFFFF:08x}")
        print("  self-check: patch applied to pristine reproduces modified ROM OK")
        return 0

    if args.cmd == "forge":
        blob = open(args.bin, "rb").read()
        syms = _load_symbols(args.sym)
        resolve = lambda t: syms[t.strip()] if t.strip() in syms else int(t.strip(), 0)
        base = resolve(args.base)
        regions = []
        for spec in args.region:
            lo, hi = spec.split(":")
            start, end = resolve(lo), resolve(hi)
            regions.append((start, blob[start - base:end - base]))
        fmt = "bps" if args.out.lower().endswith(".bps") else "ips"
        src = open(args.source, "rb").read() if args.source else None
        if fmt == "bps":
            if src is None:
                raise SystemExit("BPS embeds source/target CRC32 -- pass --source <stock C-BIOS ROM>")
            patch, target = make_bps_regions(src, regions)
            open(args.out, "wb").write(patch)
            if apply_bps(src, patch) != target:
                raise SystemExit("ERROR: BPS forge self-check failed")
        else:
            patch = make_ips_regions(regions)
            open(args.out, "wb").write(patch)
            target = apply_regions(src, regions) if src is not None else None
            if src is not None and apply_ips(src, patch) != target:
                raise SystemExit("ERROR: IPS forge self-check failed")
        print(f"wrote {args.out}: {fmt.upper()}, {len(regions)} regions, {len(patch)} bytes")
        for off, data in regions:
            print(f"  0x{off:06X}  {len(data):5d} bytes")
        if src is not None:
            print(f"  source (stock)   sha1: {hashlib.sha1(src).hexdigest()}")
            print(f"  result (patched) sha1: {hashlib.sha1(target).hexdigest()}")
            if fmt == "bps":
                print(f"  embedded CRC32 source/target: "
                      f"{zlib.crc32(src)&0xFFFFFFFF:08x}/{zlib.crc32(target)&0xFFFFFFFF:08x}")
            print("  self-check: patch applied to stock ROM reproduces target OK")
        return 0

    if args.cmd == "apply":
        pr = open(args.pristine, "rb").read()
        patch = open(args.patch, "rb").read()
        fmt = _fmt_of_patch(patch)
        res = (apply_bps if fmt == "bps" else apply_ips)(pr, patch)
        open(args.out, "wb").write(res)
        print(f"wrote {args.out}: {len(res)} bytes, sha1 {hashlib.sha1(res).hexdigest()}")
        return 0

    if args.cmd == "info":
        patch = open(args.patch, "rb").read()
        fmt = _fmt_of_patch(patch)
        recs = list(records_bps(patch) if fmt == "bps" else records_ips(patch))
        print(f"{args.patch}: {fmt.upper()}, {len(recs)} records, {len(patch)} bytes")
        if fmt == "bps":
            print(f"  source CRC32 {struct.unpack_from('<I', patch, len(patch)-12)[0]:08x}  "
                  f"target CRC32 {struct.unpack_from('<I', patch, len(patch)-8)[0]:08x}")
        for off, size, kind in recs:
            print(f"  0x{off:06X}  {size:5d} bytes  {kind}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
