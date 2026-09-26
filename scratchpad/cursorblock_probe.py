"""D-CURSORBLOCK: does the line editor show the MSX block cursor?

Joost, 2026-09-26: "zerobas doesn't show the square rect prompt indication".
While the VG-8020's editor waits for a key, the name-table cell at CSRY/CSRX
holds character 255 and character 255's pattern is the glyph it covers with all
8 bytes inverted. Each row here reads, on each machine, while it waits:

  cell      the character in the cursor cell (255 = the cursor is drawn)
  inverse   whether pattern 255 == NOT(the covered character's own glyph) --
            a relation, so it holds across the two machines' different fonts
  csrsw     the published cursor-display cell (0 on the reference: the editor
            draws the cursor itself)
  scrmod    the mode it waits in

  rows      per pattern row: i = inverted, = = as the glyph (insert mode's
            cursor is a PARTIAL block -- Joost: "The cursor also changes in
            normal and insert mode")
  insflg    INSFLG ($FCA8), the published insert-mode flag

Rows: the boot prompt; mid-line after `PRI`; INPUT's `? `; over a character
(`ABC` + two cursor-lefts, so it covers `B`); after `SCREEN 1` -- which is ALSO
the D-SCR1PROMPT reading (zerobas's prompt drops SCREEN 1 back to SCREEN 0);
INS over `B` and INS over a space.

Headless, fresh boot per row. Clean room: VRAM and work-area RAM only.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
BS = "\\"
CASES = {
    "prompt": [],
    "typing": ['after time 14 {type "PRI"}'],
    "input": [f'after time 14 {{type "INPUT A{BS}r"}}'],
    "overB": ['after time 14 {type "ABC\\x1d\\x1d"}'],
    "screen1": [f'after time 14 {{type "SCREEN 1{BS}r"}}'],
    # Joost: "The cursor also changes in normal and insert mode." INS is key 18
    "insB": ['after time 14 {type "ABC\\x1d\\x1d\\x12"}'],
    "insspace": ['after time 14 {type "\\x12"}'],
}
TAIL = '''
after time 18 {
  set f [open "%s" w]
  if {[catch {
    set y [debug read memory 0xF3DC]; set x [debug read memory 0xF3DD]
    set sw [debug read memory 0xFCA9]; set lin [debug read memory 0xF3B0]
    set smod [debug read memory 0xFCAF]; set ins [debug read memory 0xFCA8]
    if {$smod == 1} { set nam 0x1800; set w 32; set pat 0x0000 } else { set nam 0; set w 40; set pat 0x0800 }
    set a [expr {$nam + ($y-1)*$w + ($x-1) + ($w-$lin+1)/2}]
    set cell [debug read VRAM $a]
    set p255 ""; for {set i 0} {$i < 8} {incr i} { append p255 [format %%02X [debug read VRAM [expr {$pat + 255*8 + $i}]]] }
    set cov [debug read VRAM [expr {$a + 1}]]
    puts $f "cell=$cell csrsw=$sw scrmod=$smod linlen=$lin p255=$p255 addr=$a insflg=$ins"
    for {set c 0} {$c < 256} {incr c} {
      set g ""; for {set i 0} {$i < 8} {incr i} { append g [format %%02X [debug read VRAM [expr {$pat + $c*8 + $i}]]] }
      puts $f "glyph $c $g"
    }
  } err]} { puts $f "TCLERR $err" }
  close $f; exit
}
'''


def measure(machine, lines, covered):
    out = os.path.join(HERE, "cursorblock.txt")
    tf = os.path.join(HERE, "cursorblock.tcl")
    open(tf, "w").write("\n".join(lines) + TAIL % out)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=120)
    txt = open(out).read().split("\n")
    head = dict(kv.split("=") for kv in txt[0].split())
    glyph = {int(l.split()[1]): l.split()[2] for l in txt[1:] if l.startswith("glyph")}
    inv = "".join(f"{0xFF ^ int(glyph[covered][i:i+2], 16):02X}" for i in range(0, 16, 2))
    # which of the 8 pattern rows are the covered glyph INVERTED (i) vs as-is (=)
    rows = "".join("i" if head["p255"][i:i+2] == inv[i:i+2] else
                   "=" if head["p255"][i:i+2] == glyph[covered][i:i+2] else "?"
                   for i in range(0, 16, 2))
    return (f"cell={head['cell']} inverse={'yes' if head['p255'] == inv else 'NO'} "
            f"rows={rows} csrsw={head['csrsw']} scrmod={head['scrmod']} "
            f"insflg={head['insflg']}")


def main():
    covered = {"prompt": 32, "typing": 32, "input": 32, "overB": 66, "screen1": 32,
               "insB": 66, "insspace": 32}
    bad = 0
    for k, lines in CASES.items():
        r, z = measure(REF, lines, covered[k]), measure(ZB, lines, covered[k])
        same = r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:8} ref: {r}\n{'':14}zb:  {z}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
