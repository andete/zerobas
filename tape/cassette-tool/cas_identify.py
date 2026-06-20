#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

"""Identify the MSX files in a cassette WAV (real capture or synthetic).

Decodes the FSK byte stream (via the vendored cas_decode.py) and scans it for the
MSX cassette file-type markers -- ten identical lead bytes followed by a 6-char
filename -- reporting each file found, with the load/exec addresses for binary
files. Useful both for cataloguing real tape captures and as the byte-level
reference when checking the zerobas-tape read path against real audio.

  python3 cassette-tool/cas_identify.py /path/to/tape.wav
  python3 cassette-tool/cas_identify.py tape.wav --bytes 64   # also dump head
"""
from __future__ import annotations

import argparse, os, sys

# cas_decode is vendored alongside this script (the host FSK decoder).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cas_decode  # noqa: E402

# Ten identical lead bytes select the file type (MSX2 Technical Handbook).
TYPES = {0xD3: "BASIC (tokenised)", 0xEA: "ASCII", 0xD0: "binary (BSAVE)"}
RUN = 10


def find_files(data: list[int]) -> list[dict]:
    files: list[dict] = []
    i, n = 0, len(data)
    while i <= n - (RUN + 6):
        b = data[i]
        if b in TYPES and all(data[i + k] == b for k in range(RUN)):
            name = bytes(data[i + RUN:i + RUN + 6]).decode("latin1")
            entry = {"offset": i, "id": b, "type": TYPES[b], "name": name}
            if b == 0xD0 and i + RUN + 12 <= n:
                h = data[i + RUN + 6:i + RUN + 12]
                entry["start"] = h[0] | h[1] << 8
                entry["end"] = h[2] | h[3] << 8
                entry["exec"] = h[4] | h[5] << 8
            files.append(entry)
            i += RUN + 6
        else:
            i += 1
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav")
    ap.add_argument("--bytes", type=int, default=0,
                    help="also print the first N decoded bytes (hex)")
    ap.add_argument("--stop-bits", type=int, default=1)
    args = ap.parse_args()

    data, info = cas_decode.decode_file(args.wav, stop_bits=args.stop_bits)
    print(f"{args.wav}")
    print(f"  {info.get('nbytes', 0)} bytes decoded; "
          f"~{info.get('short_freq_hz')}/{info.get('long_freq_hz')} Hz FSK, "
          f"{info.get('framerate')} Hz sample rate")
    files = find_files(data)
    if not files:
        print("  no MSX file markers found")
    for f in files:
        line = (f"  @{f['offset']:6d}  {f['id']:02X}x{RUN}  {f['type']:<18}  "
                f"name={f['name']!r}")
        if "start" in f:
            line += (f"  start={f['start']:#06x} end={f['end']:#06x} "
                     f"exec={f['exec']:#06x}")
        print(line)
    if args.bytes:
        head = data[:args.bytes]
        print("  head: " + " ".join(f"{b:02X}" for b in head))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
