#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Real-tape regression for the cbios-tape read path (Tier 2/3).

Reads real MSX tapes through the patched-C-BIOS cassette BIOS (TAPION/TAPIN) in
openMSX and checks the bytes against an independent oracle.

  .cas corpus (e.g. the "martos" collection) -- RELIABLE, pass/fail:
      openMSX renders the .cas at 3744 baud; ground truth is the .cas container
      itself, split on the 8-byte block-sync marker 1F A6 DE BA CC 13 7D 74.

  .wav recordings (real analog tapes) -- CHARACTERIZATION, not pass/fail:
      openMSX plays the recording; the oracle is cas_decode.py, our own edge
      decoder. cas_decode is only trustworthy on standard 1200/2400 FSK -- it
      mis-clusters turbo / non-2:1 encodings (observed: it returns zeros for
      Zanac while cbios-tape reads the header fine). So .wav mode reports what
      each side read and only asserts when they agree, or against --expect-header.

Scope note: a .cas can only encode standard MSX FSK blocks, so the whole .cas
corpus is BIOS-readable block by block (a game's custom loader still calls
TAPIN). Genuine custom/turbo loaders live only in analog recordings; for those
cbios-tape reads the standard header/bootstrap, but the turbo bulk is out of
scope for a BIOS-format read path. See docs/tape-regression.md.

The read cart locks the first block (TAPION + 16x TAPIN), re-locks (TAPIOF +
TAPION), then reads the start of the next block (32x TAPIN) -- exercising two
leader locks and the mid-tape re-lock on real, varied data. A run passes when
both locks succeed and the 48 read bytes are a contiguous subsequence of the
oracle bytes.

The corpus is NOT committed (copyrighted game images). Point at it with
--corpus / $MSX_TAPE_CORPUS (a dir of .cas or .zip) and/or --wav-dir /
$MSX_TAPE_WAVS (a dir of .wav). Clean-room: this drives only public BIOS entry
points; decoding tape *data* is not reading any reference BIOS/BASIC ROM.

  python3 probes/tape/bios_probe_realtape.py --corpus <your-cas-corpus> --limit 12
  python3 probes/tape/bios_probe_realtape.py --wav-dir <your-wav-dir>
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import glob
import os
import subprocess
import sys
import tempfile
import zipfile

import z80probe as Z  # noqa: E402

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")

TAPION, TAPIN, TAPIOF = 0x00E1, 0x00E4, 0x00E7
SYNC = bytes([0x1F, 0xA6, 0xDE, 0xBA, 0xCC, 0x13, 0x7D, 0x74])  # .cas block marker
NH, ND = 16, 32                       # header bytes, then data-block start bytes
CAS_MACHINE = "C-BIOS_MSX1_EU_TAPE"   # stock C-BIOS + cbios-tape IPS (no zerobas)


# ---- read cart: lock + 16 TAPIN, re-lock + 32 TAPIN, carries recorded ----------
def build_read_cart() -> bytes:
    c = Z.Cart()
    cy0 = c.alloc(1)
    hbuf = c.alloc(NH)
    cy1 = c.alloc(1)
    dbuf = c.alloc(ND)
    carry = [0xF5, 0xC1, 0x79, 0xE6, 0x01]   # push af; pop bc; ld a,c; and 1
    c.emit(Z.di())
    c.emit(Z.call(TAPION)); c.emit(carry, Z.sta(cy0))
    for i in range(NH):
        c.emit(Z.call(TAPIN), Z.sta(hbuf + i))
    c.emit(Z.call(TAPIOF))
    c.emit(Z.call(TAPION)); c.emit(carry, Z.sta(cy1))
    for i in range(ND):
        c.emit(Z.call(TAPIN), Z.sta(dbuf + i))
    c.emit(Z.call(TAPIOF))
    return c.build()


def run_read(cassette: str, timeout: int = 150) -> bytes | None:
    """Boot CAS_MACHINE with the read cart + this cassette, return the 50-byte
    result block (cy0, 16 header, cy1, 32 data) or None if the cart didn't run."""
    rom = tempfile.mktemp(suffix=".rom", prefix="realtape_")
    out = tempfile.mktemp(suffix=".txt", prefix="realtape_")
    with open(rom, "wb") as f:
        f.write(build_read_cart())
    n = 2 + NH + ND
    subprocess.call([sys.executable, OMSX_RUN, "--machine", CAS_MACHINE,
                     "--cart", rom, "--cassette", cassette,
                     "--bp", hex(Z.DONE), "--reg", "PC",
                     "--mem", f"memory:0x{Z.RESULT:04X}:{n}",
                     "--out", out, "--timeout", str(timeout)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    data = None
    if os.path.exists(out):
        for line in open(out):
            if line.startswith(f"mem.memory:0x{Z.RESULT:04X}:"):
                data = bytes.fromhex(line.split("=", 1)[1])
        os.unlink(out)
    os.unlink(rom)
    return data


# ---- oracles -------------------------------------------------------------------
def cas_oracle(path: str) -> bytes:
    """Ground truth from a .cas container: concatenate every block's bytes
    (everything after each 8-byte sync marker)."""
    raw = open(path, "rb").read()
    parts, i = [], 0
    while True:
        j = raw.find(SYNC, i)
        if j < 0:
            break
        nxt = raw.find(SYNC, j + 8)
        parts.append(raw[j + 8: nxt if nxt > 0 else len(raw)])
        i = j + 8
    return b"".join(parts)


def wav_oracle(path: str) -> tuple[bytes, dict]:
    from cas_decode import decode_file
    data, info = decode_file(path)
    return bytes(data), info


# ---- one file ------------------------------------------------------------------
def check_cas(label: str, casfile: str) -> bool:
    oracle = cas_oracle(casfile)
    if not oracle:
        print(f"  {label:26} SKIP  (no .cas blocks found)")
        return None
    d = run_read(casfile)
    if d is None:
        print(f"  {label:26} FAIL  (cart did not finish / no capture)")
        return False
    cy0, cy1 = d[0], d[1 + NH]
    read = bytes(d[1:1 + NH]) + bytes(d[2 + NH:2 + NH + ND])
    off = oracle.find(read)
    ok = (cy0 == 0 and cy1 == 0 and off >= 0)
    print(f"  {label:26} {'PASS' if ok else 'FAIL'}  lock={cy0:02x}/{cy1:02x} off={off}")
    if not ok:
        print(f"       read   {read[:16].hex()} | {read[16:].hex()}")
        print(f"       oracle {oracle[:48].hex()}")
    return ok


def check_wav(label: str, wavfile: str, expect_header: str | None) -> None:
    oracle, info = wav_oracle(wavfile)
    d = run_read(wavfile)
    sf, lf = info.get("short_freq_hz"), info.get("long_freq_hz")
    ratio = (sf / lf) if (sf and lf) else 0.0
    if d is None:
        print(f"  {label:26} ?     (cart did not finish)  ratio={ratio:.2f}")
        return
    cy0, cy1 = d[0], d[1 + NH]
    read = bytes(d[1:1 + NH]) + bytes(d[2 + NH:2 + NH + ND])
    hdr = bytes(d[1:1 + NH])
    # filename portion of a standard header block is bytes 10..16
    name = bytes(hdr[10:16]).decode("latin1", "replace")
    agree = (read in oracle) if oracle else False
    note = ""
    if expect_header is not None:
        want = expect_header.encode("latin1")
        hit = want in hdr
        note = f"  expect={expect_header!r} -> {'MATCH' if hit else 'MISS'}"
    elif agree:
        note = "  (cbios-tape agrees with cas_decode)"
    else:
        note = "  (oracle/read differ -- turbo or weak-oracle; characterization only)"
    print(f"  {label:26} lock={cy0:02x}/{cy1:02x} ratio={ratio:.2f} name={name!r}{note}")
    print(f"       read   {read[:16].hex()} | {read[16:].hex()}")


# ---- corpus iteration ----------------------------------------------------------
def cas_files_from(corpus: str, limit: int, names: list[str]):
    """Yield (label, path-to-.cas). Handles raw .cas and .zip (extracted to
    temp; the largest contained file is taken as the .cas)."""
    if names:
        entries = [os.path.join(corpus, n) for n in names]
    else:
        entries = sorted(glob.glob(os.path.join(corpus, "*")))
    count = 0
    for e in entries:
        if limit and count >= limit:
            break
        if not os.path.isfile(e):
            continue
        low = e.lower()
        if low.endswith(".zip"):
            td = tempfile.mkdtemp(prefix="realtape_zip_")
            try:
                zipfile.ZipFile(e).extractall(td)
            except Exception:
                continue
            inner = [p for p in glob.glob(td + "/**/*", recursive=True)
                     if os.path.isfile(p)]
            inner = [p for p in inner if p.lower().endswith(".cas")] or inner
            if not inner:
                continue
            inner.sort(key=lambda p: -os.path.getsize(p))
            yield os.path.basename(e), inner[0]
            count += 1
        elif low.endswith(".cas"):
            yield os.path.basename(e), e
            count += 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=os.environ.get("MSX_TAPE_CORPUS"),
                    help="dir of .cas / .zip game tapes (or $MSX_TAPE_CORPUS)")
    ap.add_argument("--wav-dir", default=os.environ.get("MSX_TAPE_WAVS"),
                    help="dir of real analog .wav recordings (or $MSX_TAPE_WAVS)")
    ap.add_argument("--limit", type=int, default=12,
                    help="max .cas files to test from the corpus (default 12)")
    ap.add_argument("--name", action="append", default=[],
                    help="test only this corpus entry (repeatable)")
    ap.add_argument("--wav", action="append", default=[],
                    help="test only this .wav in --wav-dir (repeatable)")
    ap.add_argument("--expect-header", action="append", default=[],
                    help="for --wav, expected header text per --wav (by position)")
    args = ap.parse_args()

    if not args.corpus and not args.wav_dir:
        ap.error("need --corpus and/or --wav-dir (or $MSX_TAPE_CORPUS / $MSX_TAPE_WAVS)")

    failures = 0
    if args.corpus:
        if not os.path.isdir(args.corpus):
            print(f"corpus not found: {args.corpus}", file=sys.stderr)
            return 2
        print(f"== .cas corpus (3744-baud) vs container oracle :: {args.corpus} ==")
        results = []
        for label, casf in cas_files_from(args.corpus, args.limit, args.name):
            r = check_cas(label[:26], casf)
            if r is not None:
                results.append(r)
        passed = sum(1 for r in results if r)
        failures += len(results) - passed
        print(f"  -> {passed}/{len(results)} PASS\n")

    if args.wav_dir:
        if not os.path.isdir(args.wav_dir):
            print(f"wav-dir not found: {args.wav_dir}", file=sys.stderr)
            return 2
        print(f"== .wav characterization vs cas_decode oracle :: {args.wav_dir} ==")
        wavs = args.wav or sorted(os.path.basename(p)
                                  for p in glob.glob(os.path.join(args.wav_dir, "*.wav")))
        for i, w in enumerate(wavs):
            wp = os.path.join(args.wav_dir, w)
            if not os.path.exists(wp):
                print(f"  {w:26} (missing)")
                continue
            exp = args.expect_header[i] if i < len(args.expect_header) else None
            check_wav(w[:26], wp, exp)
        print("  (.wav results are characterization, not counted as pass/fail)\n")

    # exit non-zero only on .cas-corpus failures (the reliable tier)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
