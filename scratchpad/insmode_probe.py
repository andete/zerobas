"""D-INSMODE: the screen editor's INS / DEL / BS -- do they SHIFT the line?

Joost, 2026-09-26: "The cursor also changes in normal and insert mode." The
measurement behind this probe found the gap is wider than the cursor: on the
VG-8020, INS (key 18) turns insert mode on (INSFLG $FCA8 = 255) and typed
characters push the rest of the LOGICAL line right -- across the row end, onto
the next row; DEL ($7F) deletes the character UNDER the cursor and pulls the
rest left; Backspace (8) deletes the one to its LEFT and pulls the rest left.
zerobas overwrote on INS, and its DEL and BS did not shift.

Each row types a key sequence through the matrix (openMSX `type`) at the
prompt of a fresh boot, then reads INSFLG, CSRX and the edited screen rows
(`.` = space, `#` = the cursor cell, character 255). A CLS comes first, so the
rows start at the top of a clean screen; zerobas's `ZB` prompt reads as `Ok`.

Cases (cursor on `C` of `ABCD` = `ABCD` + two cursor-lefts):
  ins_xy     INS, XY          ins_twice  INS INS XY (toggles off)
  ins_right  INS, right, XY   ins_left   INS, left, XY (a cursor key ends it)
  ins_bs     INS, BS, XY      ins_enter  INS, Enter, PRI (Enter ends it)
  ins_wrap   a 36-char line, back to its start, INS, ZZ (spills to the next row)
  ins_full   a full 37-char row, back to its start, INS, Q
  ins_nextln a full `10 REM AAA..` row LISTed above `20 REM B`, INS + Q at its
             column 4 (it has a blank continuation row below it, on both machines)
  ins_nextocc a 36-char line 10 with line 20 DIRECTLY below; INS + QQ spills one
             character: is line 20 pushed down or overwritten?
  del        DEL              bs         Backspace
(HOME is left out: `type` with it hung the emulator in this harness.)

Headless, fresh boot per case. Clean room: typed keys, VRAM and work-area RAM.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
L, R, INS, DEL, BS_ = "\\x1d", "\\x1c", "\\x12", "\\x7f", "\\x08"
ABCD_ON_C = "ABCD" + L + L
LONG = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"          # 36 characters
FULL = LONG + "!"                                       # 37: a full row at WIDTH 37
CASES = {
    "ins_xy": ABCD_ON_C + INS + "XY",
    "ins_twice": ABCD_ON_C + INS + INS + "XY",
    "ins_right": ABCD_ON_C + INS + R + "XY",
    "ins_left": ABCD_ON_C + INS + L + "XY",
    "ins_bs": ABCD_ON_C + INS + BS_ + "XY",
    "ins_enter": ABCD_ON_C + INS + "\\r" + "PRI",
    "ins_wrap": LONG + L * 36 + INS + "ZZ",
    "ins_full": FULL + L * 37 + INS + "Q",
    # the line BELOW is a different logical line: pushed down, or overwritten?
    "ins_nextln": "10 REM " + "A" * 30 + "\\r20 REM B\\rLIST\\r" + "\\x1e" * 4 + R * 3 + INS + "Q",
    # 36 characters: NO continuation row, line 20 sits directly below
    "ins_nextocc": "10 REM " + "A" * 29 + "\\r20 REM B\\rLIST\\r" + "\\x1e" * 3 + R * 3 + INS + "QQ",
    "del": ABCD_ON_C + DEL,
    "bs": ABCD_ON_C + BS_,
}


def measure(machine, keys):
    out = os.path.join(HERE, "insmode.txt")
    # CLS first (Joost: "if the banner is making the test harder, just do a CLS
    # first"), so the rows compared start at the top of a clean screen
    tcl = f'''after time 14 {{type "CLS\\r"}}
after time 16 {{type "{keys}"}}
after time 24 {{ set f [open "{out}" w]
  set y [debug read memory 0xF3DC]
  set s ""
  for {{set r 0}} {{$r <= [expr {{$y + 1}}]}} {{incr r}} {{
    for {{set i 0}} {{$i < 40}} {{incr i}} {{ set c [debug read VRAM [expr {{$r*40+$i}}]]
      if {{$c == 32}} {{append s "."}} elseif {{$c == 255}} {{append s "#"}} else {{append s [format %c $c]}} }}
    append s "|" }}
  puts $f "insflg=[debug read memory 0xFCA8] csrx=[debug read memory 0xF3DD] rows=$s"
  close $f; exit }}
'''
    tf = os.path.join(HERE, "insmode.tcl")
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
    bad = 0
    for k, keys in CASES.items():
        r, z = measure(REF, keys), measure(ZB, keys)
        same = r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:10} ref: {r}\n{'':16}zb:  {z}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
