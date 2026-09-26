"""D-INSBOTTOM: insert mode growing a line that already ends on the BOTTOM row.

D-INSMODE grows a full line by inserting a row BELOW it (ESC L, measured). A
line that ends on the bottom text row has no row below, and zerobas dropped the
spilled character. Measured 2026-09-26: the VG-8020 SCROLLS the screen up one
row and the spill lands on the freed bottom row, which continues the line.

Setup: `FOR I=1 TO 30:PRINT I:NEXT` scrolls the screen so the prompt sits near
the bottom; a 36-character line is typed there, the cursor goes back to its
start, INS, `ZZ` -- the second Z must spill. Read: CSRY/CSRX, LINTTB for rows
18..24 (1 = the row ends its line), and screen rows 18..23 (`.` = space,
`#` = the cursor cell). The prompt's identity text is normalised (`ZB` -> `Ok`).
CRTCNT is NOT compared: it reads 24 on the reference and 23 here under KEY ON,
a long-stated difference of how the key row is reserved.

Headless, fresh boot per machine. Clean room: typed keys, VRAM, work-area RAM.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
L, INS = "\\x1d", "\\x12"
LONG = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LINES = ['after time 14 {type "FOR I=1 TO 30:PRINT I:NEXT\\r"}',
         f'after time 20 {{type "{LONG}{L * 36}{INS}ZZ"}}']


def measure(machine):
    out = os.path.join(HERE, "insbottom.txt")
    tcl = "\n".join(LINES) + f'''
after time 30 {{ set f [open "{out}" w]
  set s ""; for {{set r 17}} {{$r < 23}} {{incr r}} {{ for {{set i 0}} {{$i < 40}} {{incr i}} {{ set c [debug read VRAM [expr {{$r*40+$i}}]]; if {{$c == 32}} {{append s "."}} elseif {{$c == 255}} {{append s "#"}} else {{append s [format %c $c]}} }}; append s "|" }}
  set t ""; for {{set i 17}} {{$i < 24}} {{incr i}} {{ append t [expr {{[debug read memory [expr {{0xFBB2+$i}}]] ? 1 : 0}}] }}
  puts $f "csry=[debug read memory 0xF3DC] csrx=[debug read memory 0xF3DD] linttb18-24=$t rows=$s"
  close $f; exit }}
'''
    tf = os.path.join(HERE, "insbottom.tcl")
    open(tf, "w").write(tcl)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=120)
    if not os.path.exists(out):
        return "<no reading>"
    return open(out).read().strip().replace("..ZB..", "..Ok..")


def main():
    r, z = measure(REF), measure(ZB)
    same = r == z
    print(f"{'SAME' if same else 'DIFF'} bottom_ins\n  ref: {r}\n  zb:  {z}")
    print(f"\nDIFF: {0 if same else 1}/1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
