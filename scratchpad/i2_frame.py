#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""I2 frame characterization -- the Z80-SPEED bit-bang harness.

scratchpad/i2_pinmap.py established WHICH terminal the touchpad answers on, but
drove the line from a BASIC `FOR`/`OUT` loop (~kHz) -- far too slow to clock a
uPD7001 frame, so it only ever saw the envelope of the response. This harness
injects a small Z80 routine into RAM instead, ~50x faster (~10 us per sample),
logs R14 into a buffer, and reads the buffer back with `debug read_block`.

Still purely a characterization of the DEVICE: we drive the port ourselves and
record what comes back. No ROM is read and no reference implementation consulted.

Two experiments:
  A  TOGGLE   -- square-wave the 8th terminal, sample R14 after every edge.
  B  ENVELOPE -- pull the 8th terminal low ONCE, then sample R14 as fast as the
                 Z80 can, giving the response's time structure at ~10 us
                 resolution (this is what BASIC could never see).

The paddle is run as the KNOWN-ANSWER CONTROL throughout, exactly as in
i2_pinmap.py: its circuit is published (a 10 us..3 ms one-shot on terminal 1), so
experiment B must show a pulse of about that length on bit 0. If it does not, the
harness is wrong and its touchpad verdict means nothing.
"""
from __future__ import annotations
import os, re, signal, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from omsx_run import find_omsx

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")

KEYBUF, GETPNT, PUTPNT = 0xFBF0, 0xF3FA, 0xF3F8
CODE, BUF, NBUF = 0xC000, 0xC100, 64

# R15 value: b7=1 kana lamp off, b6=0 -> R14 reads interface 1, b5=1 -> if-2 8th
# terminal idle high, b4 = the line we drive, b3..b0 unused.
HI, LO = 0xBF, 0xAF


def asm_toggle(n_pairs: int = 32) -> list[int]:
    """Square-wave the 8th terminal; one R14 sample after each edge."""
    body = []
    for val in (LO, HI):
        body += [0x3E, 0x0F, 0xD3, 0xA0,      # ld a,15 / out ($A0),a
                 0x3E, val, 0xD3, 0xA1,       # ld a,val / out ($A1),a
                 0x3E, 0x0E, 0xD3, 0xA0,      # ld a,14 / out ($A0),a
                 0xDB, 0xA2,                  # in a,($A2)
                 0x77, 0x23]                  # ld (hl),a / inc hl
    code = [0xF3,                                     # di
            0x21, BUF & 0xFF, BUF >> 8,               # ld hl,BUF
            0x06, n_pairs]                            # ld b,n_pairs
    disp = (-(len(body) + 2)) & 0xFF                  # djnz back to loop top
    code += body + [0x10, disp, 0xFB, 0xC9]           # djnz / ei / ret
    return code


def asm_envelope(n: int = NBUF) -> list[int]:
    """Pull the 8th terminal low ONCE, then sample R14 flat out (~10 us/sample)."""
    return ([0xF3,                                    # di
             0x3E, 0x0F, 0xD3, 0xA0,                  # ld a,15 / out ($A0),a
             0x3E, LO, 0xD3, 0xA1,                    # ld a,LO / out ($A1),a
             0x3E, 0x0E, 0xD3, 0xA0,                  # ld a,14 / out ($A0),a
             0x21, BUF & 0xFF, BUF >> 8,              # ld hl,BUF
             0x06, n,                                 # ld b,n
             0xDB, 0xA2, 0x77, 0x23,                  # in / ld (hl),a / inc hl
             0x10, 0xFA,                              # djnz -6
             0xFB, 0xC9])                             # ei / ret


def asm_burst(n_clocks: int = 8, n_samples: int = NBUF) -> list[int]:
    """Clock the 8th terminal `n_clocks` times, leave it idle HIGH, then sample
    R14 flat out. Decisive for SO-vs-EOC on terminal 2: EOC is specified low only
    *during conversion* (t_CONV = 14*4/f_CK), so if terminal 2 is EOC it must
    RISE again a bounded time after the clocking stops. A data line would not."""
    clk = []
    for val in (LO, HI):
        clk += [0x3E, 0x0F, 0xD3, 0xA0,       # ld a,15 / out ($A0),a
                0x3E, val, 0xD3, 0xA1]        # ld a,val / out ($A1),a
    code = [0xF3,                                     # di
            0x21, BUF & 0xFF, BUF >> 8,               # ld hl,BUF
            0x06, n_clocks]                           # ld b,n_clocks
    code += clk + [0x10, (-(len(clk) + 2)) & 0xFF]    # djnz loop1
    code += [0x3E, 0x0E, 0xD3, 0xA0,                  # ld a,14 / out ($A0),a
             0x06, n_samples,                         # ld b,n_samples
             0xDB, 0xA2, 0x77, 0x23,                  # in / ld (hl),a / inc hl
             0x10, 0xFA,                              # djnz loop2
             0xFB, 0xC9]                              # ei / ret
    return code


HEADER = f"""
set throttle off
set __f [open {{%OUT%}} w]
proc __key {{s}} {{
  set n [string length $s]
  for {{set i 0}} {{$i < $n}} {{incr i}} {{
    debug write memory [expr {{{KEYBUF} + $i}}] [scan [string index $s $i] %c]
  }}
  debug write memory {GETPNT} [expr {{{KEYBUF} & 0xFF}}]
  debug write memory [expr {{{GETPNT}+1}}] [expr {{({KEYBUF} >> 8) & 0xFF}}]
  set p [expr {{{KEYBUF} + $n}}]
  debug write memory {PUTPNT} [expr {{$p & 0xFF}}]
  debug write memory [expr {{{PUTPNT}+1}}] [expr {{($p >> 8) & 0xFF}}]
}}
proc __inj {{s}} {{ append s "\\r"; __key $s }}
proc __poke {{addr bytes}} {{
  foreach b $bytes {{ debug write memory $addr $b; incr addr }}
}}
"""


def run(code: list[int], prologue: list[str], *, timeout=300.0):
    binary = find_omsx(None)
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="i2f_", delete=False).name
    tcl = out + ".tcl"
    body = [
        # Reserve RAM above $BFFF FIRST, so nothing BASIC does can land on the
        # routine or its buffer, and only then poke the code in.
        'after time 8.0 { __inj {CLEAR 200,&HBFFF} }',
        f'after time 11.0 {{ __poke {CODE} {{{" ".join(str(b) for b in code)}}} }}',
        'after time 12.0 { __inj {DEFUSR=&HC000:A=USR(0)} }',
        f'after time 16.0 {{ binary scan [debug read_block memory {BUF} {NBUF}] H* h;'
        f' puts $__f "case.0=$h"; flush $__f; close $__f; exit }}',
    ]
    with open(tcl, "w") as f:
        f.write(HEADER.replace("%OUT%", out) + "\n".join(prologue + body) + "\n")
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
    hexs = None
    if os.path.exists(out):
        for ln in open(out):
            m = re.match(r"case\.0=([0-9a-f]+)", ln.strip())
            if m:
                hexs = m.group(1)
        os.unlink(out)
    os.unlink(tcl)
    return bytes.fromhex(hexs) if hexs else None


def show(label, data):
    if data is None:
        print(f"  {label:10s} -> CAPTURE FAILED")
        return
    masked = [b & 0x3F for b in data]
    print(f"  {label:10s} -> " + " ".join(f"{b:02X}" for b in masked))
    # which of the six input terminals ever left the idle-high state?
    moved = [t for t in range(6) if any(not (b >> t) & 1 for b in masked)]
    term = {0: 1, 1: 2, 2: 3, 3: 4, 4: 6, 5: 7}
    print(f"  {'':10s}    terminals low at some point: "
          f"{[term[t] for t in moved] or 'none'}")


EXPS = {"toggle": asm_toggle(), "envelope": asm_envelope(),
        "burst8": asm_burst(8), "burst32": asm_burst(32)}
CONFIGS = {
    "control-none": [],
    "paddleA": ["plug joyporta paddle"],
    "touchpadA": ["plug joyporta touchpad"],
}

for cfg in (sys.argv[1:] or list(CONFIGS)):
    print(f"=== {cfg}: {CONFIGS[cfg]}", flush=True)
    for name, code in EXPS.items():
        show(name, run(code, CONFIGS[cfg]))
