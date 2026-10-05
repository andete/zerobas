#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDCTRL: the screen editor's CTRL editing keys -- what does each one DO on
the VG-8020, and on ours?

sub/readline.asm's dispatch handles Ctrl-C, BS, Enter, HOME, CLS, INS, the
cursor keys and DEL; every other control byte below $20 is dropped. The manuals
document CTRL-B/E/F/N/U and TAB as editing keys. This MEASURES each one rather
than trusting the manual's table (the item's own instruction).

Each case types a key sequence through the keyboard matrix (openMSX `type`) at a
fresh prompt after a CLS, then reads INSFLG, CSRX/CSRY and the screen rows (`.` =
space, `#` = the cursor cell, character 255) and LINTTB rows 1..10 (1 = the row
ENDS its line, 0 = it continues). The shape is scratchpad/insmode_probe.py's.

Headless, fresh boot per case. Clean room: typed keys, VRAM and work-area RAM.

    python3 -u scratchpad/edctrl_probe.py [CASE ...]
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
L, R, INS = "\\x1d", "\\x1c", "\\x12"
CB, CE, CF, TAB, CN, CU, SEL, ESC = "\\x02", "\\x05", "\\x06", "\\x09", "\\x0e", "\\x15", "\\x18", "\\x1b"
LONG = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"          # 36 characters
WRAP = LONG + "abcdef"                                   # 42: wraps onto row 2
CASES = {
    # CTRL-E: erase from the cursor to the end of the (logical) line
    "ctrle":       "ABCDEF" + L * 3 + CE,
    "ctrle_wrap":  WRAP + L * 10 + CE,                   # cursor on row 1: does row 2 go too?
    # CTRL-U: erase the whole logical line
    "ctrlu":       "ABCDEF" + L * 3 + CU,
    "ctrlu_wrap":  WRAP + CU,                            # cursor on row 2
    # CTRL-B / CTRL-F: previous / next word
    "ctrlb":       "AB CD EF" + CB,
    "ctrlb2":      "AB CD EF" + CB + CB,
    "ctrlf":       "AB CD EF" + L * 8 + CF,
    "ctrlf2":      "AB CD EF" + L * 8 + CF + CF,
    # CTRL-N: to the end of the logical line
    "ctrln":       "ABCDEF" + L * 4 + CN,
    "ctrln_wrap":  WRAP + L * 20 + CN,
    # TAB: to the next tab stop -- blanking, or moving?
    "tab":         "AB" + TAB + "X",
    "tab_over":    "ABCDEFGHIJ" + L * 9 + TAB + "X",    # over existing text
    # SELECT / ESC: nothing at the editor?
    "select":      "ABC" + L + SEL + "X",
    "esc":         "ABC" + L + ESC + "X",
    # does insert mode survive a CTRL edit key?
    "ins_ctrle":   "ABCD" + L + L + INS + CE + "Q",
}


def measure(machine, keys):
    out = os.path.join(HERE, "edctrl.txt")
    tcl = f'''after time 14 {{type "CLS\\r"}}
after time 16 {{type "{keys}"}}
after time 24 {{ set f [open "{out}" w]
  set y [debug read memory 0xF3DC]
  set s ""
  for {{set r 0}} {{$r <= [expr {{$y + 1}}]}} {{incr r}} {{
    for {{set i 0}} {{$i < 40}} {{incr i}} {{ set c [debug read VRAM [expr {{$r*40+$i}}]]
      if {{$c == 32}} {{append s "."}} elseif {{$c == 255}} {{append s "#"}} else {{append s [format %c $c]}} }}
    append s "|" }}
  set t ""; for {{set i 0}} {{$i < 10}} {{incr i}} {{ append t [expr {{[debug read memory [expr {{0xFBB2+$i}}]] ? 1 : 0}}] }}
  puts $f "insflg=[debug read memory 0xFCA8] csrx=[debug read memory 0xF3DD] csry=$y linttb=$t rows=$s"
  close $f; exit }}
'''
    tf = os.path.join(HERE, "edctrl.tcl")
    open(tf, "w").write(tcl)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=120)
    if not os.path.exists(out):
        return "<no reading>"
    # the prompt's TEXT is an identity marker by design (`ZB`), not an editor fact
    return open(out).read().strip().replace("..ZB..", "..Ok..")


def main():
    want = sys.argv[1:] or list(CASES)
    bad = 0
    for k in want:
        keys = CASES[k]
        r, z = measure(REF, keys), measure(ZB, keys)
        same = r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:11} ref: {r}\n{'':17}zb:  {z}")
    print(f"\nDIFF: {bad}/{len(want)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
