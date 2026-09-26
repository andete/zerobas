"""D-HOMEKEY: does HOME move the cursor home, and only SHIFT+HOME clear?

C-BIOS's key table decoded HOME (matrix row 8, bit 1) as $0C -- CLS -- where an
MSX gives $0B (cursor home) and $0C only with SHIFT (row 6, bit 0). Measured
2026-09-26 before the fix: the VG-8020's HOME left `ABC` on screen and put the
cursor at row 1 column 1; zerobas cleared the screen on HOME too.

The keys are pressed on the MATRIX with keymatrixdown/up (an openMSX `type` of
$0B hung the reference in an earlier harness). Each case: CLS, type `ABC`, then
the key(s); read CSRY/CSRX and the top four rows (`.` = space, `#` = the cursor
cell). The prompt row is normalised: `ZB` reads as `Ok`, and a cursor on its
first letter (`#B`) reads as the reference's `#k`.

Headless, fresh boot per case. Clean room: key matrix, VRAM and work-area RAM.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
HOME = "keymatrixdown 8 0x02; after time 0.1 {keymatrixup 8 0x02}"
SHOME = ("keymatrixdown 6 0x01; after time 0.05 {keymatrixdown 8 0x02}; "
         "after time 0.15 {keymatrixup 8 0x02; keymatrixup 6 0x01}")
BASE = ['after time 14 {type "CLS\\r"}', 'after time 16 {type "ABC"}']
CASES = {
    "home": BASE + [f"after time 18 {{{HOME}}}"],
    "shifthome": BASE + [f"after time 18 {{{SHOME}}}"],
    "home_z": BASE + [f"after time 18 {{{HOME}}}", 'after time 19 {type "Z"}'],
    "shifthome_z": BASE + [f"after time 18 {{{SHOME}}}", 'after time 19 {type "Z"}'],
}


def measure(machine, lines):
    out = os.path.join(HERE, "homekey.txt")
    tcl = "\n".join(lines) + f'''
after time 22 {{ set f [open "{out}" w]
  set s ""; for {{set r 0}} {{$r < 4}} {{incr r}} {{ for {{set i 0}} {{$i < 40}} {{incr i}} {{ set c [debug read VRAM [expr {{$r*40+$i}}]]; if {{$c == 32}} {{append s "."}} elseif {{$c == 255}} {{append s "#"}} else {{append s [format %c $c]}} }}; append s "|" }}
  puts $f "csry=[debug read memory 0xF3DC] csrx=[debug read memory 0xF3DD] rows=$s"
  close $f; exit }}
'''
    tf = os.path.join(HERE, "homekey.tcl")
    open(tf, "w").write(tcl)
    if os.path.exists(out):
        os.remove(out)
    try:
        subprocess.run(["openmsx", "-machine", machine, "-command",
                        "set save_settings_on_exit false; set renderer none; set sound_driver null",
                        "-script", tf], capture_output=True, timeout=90)
    except subprocess.TimeoutExpired:
        return "<TIMEOUT>"
    if not os.path.exists(out):
        return "<no reading>"
    head, rows = open(out).read().strip().split("rows=", 1)
    rows = rows.split("|")
    # the PROMPT row's text is an identity marker (`ZB` vs `Ok`), and HOME puts
    # the cursor on its FIRST letter -- so `#B` on zerobas is `#k` on the reference
    rows[0] = rows[0].replace("ZB", "Ok").replace("#B", "#k")
    return head + "rows=" + "|".join(rows)


def main():
    bad = 0
    for k, lines in CASES.items():
        r, z = measure(REF, lines), measure(ZB, lines)
        same = r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:11} ref: {r}\n{'':17}zb:  {z}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
