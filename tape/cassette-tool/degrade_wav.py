#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Apply parameterised, in-spec tape degradations to a cassette WAV.

The zerobas-tape read path (TAPION/TAPIN) has so far only been proven against
*synthetic* recordings -- the clean, square, jitter-free output of its own write
path under openMSX. That proves the codec is self-consistent, not that it
tolerates a real tape. This tool takes a clean recording and applies the kinds of
impairment a real cassette + audio chain introduce, so the reader can be tested
across a tolerance envelope (and the breaking point found by pushing a parameter).

Impairments (compose in this order: time-base, then waveform, then level):

  --speed PCT     constant speed error (tape runs fast/slow): shifts all
                  frequencies by PCT, e.g. -4 or +4. The reader is baud-agnostic
                  (TAPION re-measures the leader), so moderate values must still
                  decode; large values map the lock range.
  --wow HZ:PCT    wow/flutter: sinusoidal speed modulation at HZ, depth PCT
                  (e.g. 6:3 = 6 Hz, +/-3%). Jitters half-period lengths.
  --lowpass HZ    one-pole low-pass: rounds the square edges toward the sine-ish
                  shape a real head/amplifier produces (e.g. 6000). The harshest
                  test of edge/zero-crossing detection.
  --bias FRAC     DC bias as a fraction of amplitude (e.g. 0.15): shifts the
                  comparator point, skewing the mark/space duty cycle.
  --gain FRAC     amplitude scale (e.g. 0.4 = quiet tape / weak signal).
  --noise FRAC    additive uniform noise, fraction of full scale (e.g. 0.05 hiss).
  --seed N        RNG seed (reproducible noise).

Output is 8-bit unsigned mono at the input framerate -- what openMSX's
cassetteplayer expects. Verify a degraded file by mounting it with
`omsx_run.py --cassette` and reading it back with the zerobas-tape read probes.

  # clean file from the write probe, then degrade and re-read:
  python3 cassette-tool/degrade_wav.py in.wav out.wav --lowpass 5000 --noise 0.03
"""
from __future__ import annotations

import argparse, math, random, struct, sys, wave


def read_wav_float(path: str) -> tuple[list[float], int]:
    """Read a mono/stereo 8- or 16-bit WAV as floats centred on 0, scaled ~[-1,1]."""
    w = wave.open(path, "rb")
    fr, sw, ch, n = (w.getframerate(), w.getsampwidth(),
                     w.getnchannels(), w.getnframes())
    raw = w.readframes(n)
    w.close()
    if sw == 1:
        data = [(b - 128) / 127.0 for b in raw]
    elif sw == 2:
        ints = struct.unpack("<%dh" % (len(raw) // 2), raw)
        data = [v / 32768.0 for v in ints]
    else:
        raise SystemExit(f"unsupported sample width {sw} bytes")
    if ch > 1:
        data = data[::ch]
    return data, fr


def write_wav_u8(path: str, samples: list[float], fr: int) -> None:
    """Write floats (~[-1,1]) as 8-bit unsigned mono."""
    buf = bytearray(len(samples))
    for i, v in enumerate(samples):
        q = int(round(v * 127.0)) + 128
        buf[i] = 0 if q < 0 else 255 if q > 255 else q
    w = wave.open(path, "wb")
    w.setnchannels(1)
    w.setsampwidth(1)
    w.setframerate(fr)
    w.writeframes(bytes(buf))
    w.close()


def time_warp(x: list[float], fr: int, speed_pct: float,
              wow_hz: float, wow_pct: float) -> list[float]:
    """Resample with a constant speed error plus sinusoidal wow/flutter.

    Output sample i reads input at a running position whose step per output
    sample is (1 + speed + wow*sin(2*pi*wow_hz*t)); speed>0 compresses time
    (higher frequencies), modelling a tape running fast.
    """
    if speed_pct == 0 and wow_pct == 0:
        return x
    s = speed_pct / 100.0
    d = wow_pct / 100.0
    w = 2.0 * math.pi * wow_hz / fr
    out: list[float] = []
    t = 0.0
    i = 0
    n = len(x)
    while t < n - 1:
        i0 = int(t)
        frac = t - i0
        out.append(x[i0] * (1.0 - frac) + x[i0 + 1] * frac)
        t += 1.0 + s + d * math.sin(w * i)
        i += 1
    return out


def lowpass(x: list[float], fr: int, fc: float) -> list[float]:
    """One-pole RC low-pass; rounds square edges toward a real head's response."""
    if fc <= 0:
        return x
    rc = 1.0 / (2.0 * math.pi * fc)
    dt = 1.0 / fr
    a = dt / (rc + dt)
    out: list[float] = []
    prev = 0.0
    for v in x:
        prev += a * (v - prev)
        out.append(prev)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--speed", type=float, default=0.0, metavar="PCT")
    ap.add_argument("--wow", default=None, metavar="HZ:PCT",
                    help="sinusoidal speed modulation, e.g. 6:3")
    ap.add_argument("--lowpass", type=float, default=0.0, metavar="HZ")
    ap.add_argument("--bias", type=float, default=0.0, metavar="FRAC")
    ap.add_argument("--gain", type=float, default=1.0, metavar="FRAC")
    ap.add_argument("--noise", type=float, default=0.0, metavar="FRAC")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    wow_hz, wow_pct = 0.0, 0.0
    if args.wow:
        try:
            wow_hz, wow_pct = (float(p) for p in args.wow.split(":"))
        except ValueError:
            ap.error("--wow wants HZ:PCT, e.g. 6:3")

    x, fr = read_wav_float(args.infile)
    n0 = len(x)
    x = time_warp(x, fr, args.speed, wow_hz, wow_pct)
    x = lowpass(x, fr, args.lowpass)
    rng = random.Random(args.seed)
    out = []
    for v in x:
        v = v * args.gain + args.bias
        if args.noise:
            v += rng.uniform(-args.noise, args.noise)
        out.append(v)
    write_wav_u8(args.outfile, out, fr)

    applied = []
    if args.speed:   applied.append(f"speed {args.speed:+g}%")
    if args.wow:     applied.append(f"wow {wow_hz:g}Hz/{wow_pct:g}%")
    if args.lowpass: applied.append(f"lowpass {args.lowpass:g}Hz")
    if args.bias:    applied.append(f"bias {args.bias:+g}")
    if args.gain != 1.0: applied.append(f"gain {args.gain:g}")
    if args.noise:   applied.append(f"noise {args.noise:g}")
    print(f"{args.infile} ({n0} frames) -> {args.outfile} ({len(out)} frames, "
          f"{fr} Hz u8); applied: {', '.join(applied) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
