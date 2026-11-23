#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TRSPEC (tr6): build the WAV files the xpcmwav* probes feed into the turbo R's PCM input (biosl_run `@wavin`).
Media are never committed: they go to $ZEROBAS_TMP (agent_wt sets it per instance), rebuilt on every run.

    python3 scratchpad/xpcmwav_mk.py            # writes $ZEROBAS_TMP/xpcmwav_*.wav

All mono, 16-bit signed, 44100 Hz, 60 s (openMSX plays the file once, from the moment it is plugged = boot):
  sq1k    a 1 kHz square wave, +16384 / -16384 (half scale), starting high
  stairs  a staircase: 32 levels -32768, -30720, ... +30720 (step 2048 = 8 units of an 8-bit scale), each held 10 ms,
          period 320 ms, repeated
  burst   silence (0) except a 1 kHz square at +-16384 for 5 ms in every 500 ms (from 0.25 s into each period)
  rampup  silence (0) except, from 0.5 s into every 1 s period, a ramp 0, +256, +512, ... +32512 (one 8-bit unit per
          step), each step held 2 ms (0.256 s), then silence again
  rampdn  the same ramp downwards: 0, -256, ... -32512
  gaps    1 s period: silence until 0.5 s, then 14 marks -- mark k a level of +256 x 8(k+2) (8-bit $90, $98, ... $F8)
          held 1 ms -- each followed by a silence of GAPS_MS[k] (0.1 ... 130 ms), then silence to the period's end
  lowlev  1 s period: silence until 0.5 s, then for each 8-bit level in LOWLEV ($82 $86 $87 $88 $8F $90 $7A $79
          $78 $71 $70): a mark ($F0, 1 ms) and that level for 2 ms; a last mark, then silence
"""
import os
import struct
import wave

RATE, SECS = 44100, 60


def write(name, gen):
    d = os.environ.get("ZEROBAS_TMP") or "/tmp/zerobas"
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"xpcmwav_{name}.wav")
    n = RATE * SECS
    data = bytearray()
    for i in range(n):
        data += struct.pack("<h", gen(i))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(data))
    print(path)


def sq1k(i):
    return 16384 if (i * 2000 // RATE) % 2 == 0 else -16384


def stairs(i):
    step = (i * 100 // RATE) % 32          # 10 ms per level
    return -32768 + 2048 * step


def burst(i):
    t = i % (RATE // 2)                      # 500 ms period
    if RATE // 4 <= t < RATE // 4 + RATE // 200:
        return sq1k(i)
    return 0


GAPS_MS = [0.1, 0.2, 0.5, 1, 2, 4, 8, 8.2, 8.5, 16, 16.4, 33, 65, 130]


def _gaps_table():
    segs, t = [], 0.5
    for k, g in enumerate(GAPS_MS):
        segs.append((t, t + 0.001, 256 * 8 * (k + 2)))
        t += 0.001 + g / 1000
    return segs


_GAPS = _gaps_table()


def gaps(i):
    t = (i % RATE) / RATE
    for a, b, v in _GAPS:
        if a <= t < b:
            return v
    return 0


LOWLEV = [0x82, 0x86, 0x87, 0x88, 0x8F, 0x90, 0x7A, 0x79, 0x78, 0x71, 0x70]


def lowlev(i):
    t = (i % RATE) / RATE - 0.5
    if t < 0:
        return 0
    k, r = int(t // 0.003), t % 0.003
    if k < len(LOWLEV):
        return 256 * (0xF0 - 128) if r < 0.001 else 256 * (LOWLEV[k] - 128)
    if k == len(LOWLEV) and r < 0.001:
        return 256 * (0xF0 - 128)
    return 0


def ramp(i, sign):
    t = i % RATE                             # 1 s period
    k = (t - RATE // 2) * 500 // RATE        # 2 ms per step
    if 0 <= k < 128:
        return sign * 256 * k
    return 0


if __name__ == "__main__":
    for name, gen in (("sq1k", sq1k), ("stairs", stairs), ("burst", burst), ("rampup", lambda i: ramp(i, 1)),
                      ("rampdn", lambda i: ramp(i, -1)), ("gaps", gaps),
                      ("lowlev", lowlev)):
        write(name, gen)
