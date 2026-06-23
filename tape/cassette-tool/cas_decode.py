#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Decode an MSX cassette FSK recording (WAV) back to bytes.

Oracle infrastructure for the zerobas-tape side project (see
zerobas-tape/docs/feasibility.md): when a probe cart drives the BIOS write path
(TAPOON/TAPOUT) and openMSX records the CAS-out signal with `cassetteplayer new`,
this turns that WAV back into the byte stream so the spec's "to capture" rows can
be filled and a write->read round-trip asserted. It observes only signal edges --
no reference disassembly is involved.

MSX Kansas-City-style FSK (derived from the documented format, MSX2 Technical
Handbook cassette I/O chapter; re-confirmed by measuring this project's own
oracle recordings):

  * '0' bit = one cycle of the low frequency  (1200 Hz @ 1200 baud)
  * '1' bit = two cycles of the high frequency (2400 Hz @ 1200 baud)
  * byte framing = 1 start bit (0), 8 data bits LSB-first, >=1 stop bits (1)
  * a block is preceded by a long leader = continuous high-frequency tone (1s)

The decoder is baud-agnostic: it auto-thresholds the two half-period clusters
from the signal itself, so a 2400-baud recording (2400/4800 Hz) decodes the same
way.

  python3 probes/lib/cas_decode.py recording.wav
  python3 probes/lib/cas_decode.py recording.wav --expect 55,AA,4A,4F,4E,47
"""
from __future__ import annotations

import argparse
import sys
import wave


def read_samples(path: str) -> tuple[list[int], int]:
    """Return (centered int samples, framerate). Handles 8/16-bit mono/stereo."""
    w = wave.open(path, "rb")
    fr, sw, ch, n = (w.getframerate(), w.getsampwidth(),
                     w.getnchannels(), w.getnframes())
    raw = w.readframes(n)
    w.close()
    if sw == 1:                       # 8-bit unsigned, midpoint 128
        data = [b - 128 for b in raw]
    elif sw == 2:                     # 16-bit signed little-endian
        import struct
        data = list(struct.unpack("<%dh" % (len(raw) // 2), raw))
    else:
        raise SystemExit(f"unsupported sample width {sw} bytes")
    if ch > 1:
        data = data[::ch]             # take channel 0
    return data, fr


def zero_crossings(s: list[int]) -> list[int]:
    """Sample indices where the signal crosses its midpoint."""
    xs = []
    prev = s[0]
    for i in range(1, len(s)):
        cur = s[i]
        if (prev <= 0 and cur > 0) or (prev >= 0 and cur < 0):
            xs.append(i)
        prev = cur
    return xs


def half_periods(xs: list[int]) -> list[int]:
    return [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]


def auto_threshold(hp: list[int]) -> float:
    """Split the two half-period clusters (short=high freq, long=low freq).

    The two tones are an octave apart, so the long cluster sits near 2x the
    short one. Threshold at 1.5x the short cluster's centre."""
    lo, hi = min(hp), max(hp)
    # crude k=2 split: short cluster centre is near the global min mode.
    shorts = [h for h in hp if h <= (lo + hi) / 2]
    short_centre = sorted(shorts)[len(shorts) // 2] if shorts else lo
    return short_centre * 1.5


def decode_bits(hp: list[int], thr: float) -> list[int]:
    """S/L half-period stream -> bits. 'LL'=>0, 'SSSS'=>1 (two high cycles).

    Robust to odd boundary half-periods: it consumes a long pair as a 0 and a
    run of four shorts as a 1, skipping a stray unmatched half-period."""
    sym = ["L" if h > thr else "S" for h in hp]
    bits: list[int] = []
    i, n = 0, len(sym)
    while i < n:
        if sym[i] == "L":
            if i + 1 < n and sym[i + 1] == "L":
                bits.append(0); i += 2
            else:
                i += 1                      # stray long, skip
        else:  # 'S'
            if i + 3 < n and sym[i + 1] == sym[i + 2] == sym[i + 3] == "S":
                bits.append(1); i += 4
            else:
                i += 1                      # stray short (leader tail), skip
    return bits


def frame_bytes(bits: list[int], stop_bits: int = 1) -> list[int]:
    """Bits -> bytes using start(0)/8 data LSB-first/stop(1) framing.

    Skips leading '1' leader bits; resynchronises on each start bit."""
    out: list[int] = []
    i, n = 0, len(bits)
    while i < n:
        if bits[i] != 0:                    # leader / stop padding
            i += 1
            continue
        if i + 9 > n:
            break
        data = bits[i + 1:i + 9]            # 8 data bits, LSB first
        val = sum(b << k for k, b in enumerate(data))
        out.append(val)
        i += 9 + stop_bits                  # past data + stop bit(s)
    return out


def decode_file(path: str, stop_bits: int = 1, verbose: bool = False):
    s, fr = read_samples(path)
    xs = zero_crossings(s)
    hp = half_periods(xs)
    if not hp:
        return [], {}
    thr = auto_threshold(hp)
    bits = decode_bits(hp, thr)
    data = frame_bytes(bits, stop_bits)
    shorts = sum(1 for h in hp if h <= thr)
    short_hp = [h for h in hp if h <= thr]
    long_hp = [h for h in hp if h > thr]
    info = {
        "framerate": fr,
        "halfperiods": len(hp),
        "threshold_samples": round(thr, 2),
        "short_freq_hz": round(fr / (2 * (sum(short_hp) / len(short_hp))))
                         if short_hp else None,
        "long_freq_hz": round(fr / (2 * (sum(long_hp) / len(long_hp))))
                        if long_hp else None,
        "short_pct": round(100 * shorts / len(hp), 1),
        "nbits": len(bits),
        "nbytes": len(data),
    }
    if verbose:
        for k, v in info.items():
            print(f"# {k}: {v}", file=sys.stderr)
    return data, info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav")
    ap.add_argument("--stop-bits", type=int, default=1)
    ap.add_argument("--expect", help="comma/space hex bytes to assert, e.g. 55,AA,4A")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    data, info = decode_file(args.wav, args.stop_bits, verbose=not args.quiet)
    hexs = " ".join(f"{b:02X}" for b in data)
    print(hexs)

    if args.expect:
        want = [int(x, 16) for x in args.expect.replace(",", " ").split()]
        # the leader may yield a spurious leading byte or two; look for the run.
        ok = any(data[i:i + len(want)] == want
                 for i in range(0, max(1, len(data) - len(want) + 1)))
        print(("MATCH" if ok else "MISMATCH") +
              f" expected: {' '.join(f'{b:02X}' for b in want)}",
              file=sys.stderr)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
