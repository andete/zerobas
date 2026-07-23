#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""I2 pin-mapping characterization -- which joyport terminal carries which
uPD7001 signal, derived from OUR OWN black-box oracle.

The MSX2 TH publishes the port wiring (R15 b4 = the 8th terminal of interface 1,
R15 b6 selects which interface R14 b0..b5 reads) and the NEC uPD7001 datasheet
publishes the serial protocol (conversion starts on the RISE of CS; with CS low
data is exchanged; SO and EOC are open-drain; 8 result bits MSB-first clocked by
SCK; 2 address bits in on SI latched by DL). What NEITHER publishes is which
joyport terminal is CS / SCK / SI / SO / EOC.

So: drive the one output line we have (R15 b4) ourselves from BASIC, sample
R14 after every edge, and watch what the plugged touchpad does. No ROM is read
and no reference implementation is consulted -- this characterizes the DEVICE.

Run with nothing plugged too: that is the control, and any bit that moves in the
control is not the device answering.
"""
from __future__ import annotations
import os, re, signal, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl as R
from omsx_run import find_omsx

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")

PSG_ADDR, PSG_WR, PSG_RD = 0xA0, 0xA1, 0xA2
# R15: b7 kana lamp off, b6=0 -> R14 reads interface 1, b5=1 -> if-2 8th
# terminal idle high, b4 = the line we toggle, b3..b0 unused.
HI, LO = 0xBF, 0xAF


def run(cases, prologue, *, boot=8.0, step=2.5, cap_gap=4.0, timeout=600.0):
    binary = find_omsx(None)
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="i2pm_", delete=False).name
    tcl = out + ".tcl"
    with open(tcl, "w") as f:
        f.write("\n".join(prologue) + "\n" +
                R._tcl(out, cases, boot, step, cap_gap, ("NEW", "CLS"),
                       "screen", None, 12.0))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen([binary, "-machine", REF, "-command",
                             "set renderer none", "-script", tcl],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.05)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    caps = {}
    if os.path.exists(out):
        for ln in open(out):
            m = re.match(r"case\.(\d+)=([0-9a-f]*)", ln.strip())
            if m and m.group(2):
                data = bytes.fromhex(m.group(2))
                caps[int(m.group(1))] = "".join(
                    chr(b) if 32 <= b < 127 else " " for b in data)
        os.unlink(out)
    os.unlink(tcl)
    return [caps.get(i) for i in range(len(cases))]


def span(raw):
    if raw is None:
        return None
    m = re.findall(r"\[([^\]]*)\]", raw)
    return m[-1].strip() if m else None


# --- case 1: toggle the 8th terminal 16 times, print R14 after every edge -----
# Two-digit hex per sample so the whole trace fits one span.
TOGGLE = ["ON ERROR GOTO 60",
          'A$="":FORI=0TO15',
          f"OUT{PSG_ADDR},15:OUT{PSG_WR},{LO}+16*(I AND 1)",
          f"OUT{PSG_ADDR},14:V=INP({PSG_RD})AND63",
          'A$=A$+RIGHT$("0"+HEX$(V),2):NEXT',
          'PRINT"[";A$;"]":END',
          'PRINT"[E";ERR;"]":END']

# --- case 2: hold the line LOW and sample repeatedly (is anything free-running?)
STATIC_LO = ["ON ERROR GOTO 60",
             f"OUT{PSG_ADDR},15:OUT{PSG_WR},{LO}",
             'A$="":FORI=0TO7',
             f"OUT{PSG_ADDR},14:V=INP({PSG_RD})AND63",
             'A$=A$+RIGHT$("0"+HEX$(V),2):NEXT',
             'PRINT"[";A$;"]":END',
             'PRINT"[E";ERR;"]":END']

# --- case 3: same but held HIGH ----------------------------------------------
STATIC_HI = [l.replace(str(LO), str(HI)) for l in STATIC_LO]

CASES = [("stored", TOGGLE), ("stored", STATIC_LO), ("stored", STATIC_HI)]
NAMES = ["toggle-16", "static-low", "static-high"]

CONFIGS = {
    "control-none": [],
    "touchpadA": ["plug joyporta touchpad"],
    "paddleA": ["plug joyporta paddle"],
}

for cfg in (sys.argv[1:] or list(CONFIGS)):
    print(f"=== {cfg}: {CONFIGS[cfg]}", flush=True)
    for name, raw in zip(NAMES, run(CASES, CONFIGS[cfg])):
        s = span(raw)
        pretty = s
        if s and re.fullmatch(r"[0-9A-F]+", s or ""):
            pretty = " ".join(s[i:i + 2] for i in range(0, len(s), 2))
        print(f"  {name:11s} -> {pretty}", flush=True)
