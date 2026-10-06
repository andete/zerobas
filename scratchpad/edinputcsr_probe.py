#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDINPUTCSR: the cursor keys inside `INPUT` across rows -- what does the
answer read after the cursor leaves the row it was typed on, on the VG-8020 and
on ours?

Each case: CLS, `INPUT A$`, a typed answer and edit keys, Enter, then
`PRINT "[";LEN(A$);"|";A$;"]"`. The readout is that printed line plus CSRY.
The answer is 45 distinct characters, so it wraps onto a second row and every
kept character says where it came from.

Headless, fresh boot per case. Clean room: typed keys, VRAM, work-area RAM.

    python3 -u scratchpad/edinputcsr_probe.py [CASE ...]
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
UP, DOWN, L, R, HOME = "\\x1e", "\\x1f", "\\x1d", "\\x1c", "\\x0b"
ANS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"      # 45: wraps
CASES = {
    "plain":     ANS,                           # control: typed straight through
    "up_over":   ANS + UP + "Q",                # overtype on the first row, Enter there
    "up_enter":  ANS + UP,                      # Enter on the first row, no edit
    "up_down":   ANS + UP + "Q" + DOWN,         # back down, Enter on the second row
    "up_left":   ANS + UP + L * 10 + "Q",       # cursor onto the `?` and overtype it
    "up2":       ANS + UP + UP,                 # Enter on the `INPUT A$` row above
    "short_dn":  "ABC" + DOWN,                  # one-row answer, Enter on the row below
    "short_up":  "ABC" + UP,                    # Enter on the `INPUT A$` row
    "short_r":   "ABC" + R * 5,                 # past the answer's end on its row
}


def measure(machine, keys):
    out = os.path.join(HERE, "edinputcsr.txt")
    tcl = f'''after time 14 {{type "CLS\\r"}}
after time 15 {{type "INPUT A\\$\\r"}}
after time 17 {{type "{keys}"}}
after time 23 {{type "\\r"}}
after time 24 {{type "PRINT\\"\\[\\";LEN(A\\$);\\"|\\";A\\$;\\"\\]\\"\\r"}}
after time 30 {{ set f [open "{out}" w]
  set s ""
  for {{set i 0}} {{$i < 960}} {{incr i}} {{ set c [debug read VRAM $i]
    if {{$c < 32 || $c > 126}} {{append s "."}} else {{append s [format %c $c]}} }}
  puts $f $s
  close $f; exit }}
'''
    tf = os.path.join(HERE, "edinputcsr.tcl")
    open(tf, "w").write(tcl)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=120)
    if not os.path.exists(out):
        return "<no reading>"
    # the prompt's TEXT is an identity marker by design (`ZB`), not an editor fact
    scr = open(out).read().replace("ZB", "Ok")
    # the printed `[ n |...]`, never the typed echo (which carries `";`)
    hits = [m for m in re.findall(r"\[[^\[\]]*\]", scr) if '";' not in m]
    # a 45-char answer prints across two rows: the answers hold no blanks, so
    # dropping every blank rejoins them (and the row padding between)
    return "".join(hits[-1].split()) if hits else "<no [..]> " + " ".join(scr.split())[:200]


def main():
    want = sys.argv[1:] or list(CASES)
    bad = 0
    for k in want:
        r, z = measure(REF, CASES[k]), measure(ZB, CASES[k])
        bad += r != z
        print(f"{'SAME' if r == z else 'DIFF'} {k:9} ref: {r}\n{'':15}zb:  {z}", flush=True)
    print(f"\nDIFF: {bad}/{len(want)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
