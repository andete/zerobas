"""D-SCR1PROMPT: which screen mode does the prompt (and INPUT) come back in?

Found 2026-09-26 by cursorblock_probe.py: after `SCREEN 1` the VG-8020 waits in
SCREEN 1, zerobas in SCREEN 0 -- its txt_mode sent every non-zero SCRMOD to
INITXT. The reference's rule is the LAST TEXT MODE (OLDSCR), i.e. TOTEXT.

Each row types its keys through the matrix (openMSX `type`, one line per 3 s),
waits, and reads the published cells SCRMOD / OLDSCR / LINLEN / LINL32 plus
the function-key row (row 23 of whichever name table is live), on both
machines. Headless, fresh boot per row. Clean room: work-area RAM and VRAM.

Rows:
  s1direct     SCREEN 1 at the prompt
  s1_prog_s2   SCREEN 1, then a program that enters SCREEN 2 and ends
  s0_prog_s2   SCREEN 0, then the same program
  s2direct     SCREEN 2 at the prompt
  s1_width     SCREEN 1 then WIDTH 20 (which width cell it lands in)
  s1_input_s2  SCREEN 1, then INPUT inside a SCREEN 2 program (read WHILE it
               waits)
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
BS = "\\"


def seq(*items, t0=14, dt=3):
    return [f'after time {t0 + i * dt} {{type "{x}{BS}r"}}' for i, x in enumerate(items)]


PROG = "10 SCREEN 2:FOR I=1 TO 300:NEXT"
CASES = {
    "s1direct": seq("SCREEN 1"),
    "s1_prog_s2": seq("SCREEN 1", PROG, "RUN"),
    "s0_prog_s2": seq("SCREEN 0", PROG, "RUN"),
    "s2direct": seq("SCREEN 2"),
    "s1_width": seq("SCREEN 1", "WIDTH 20"),
    "s1_input_s2": seq("SCREEN 1", "10 SCREEN 2:INPUT A", "RUN"),
}


def measure(machine, lines):
    out = os.path.join(HERE, "scr1prompt.txt")
    end = 14 + 3 * len(lines) + 4
    tcl = "\n".join(lines) + f'''
after time {end} {{ set f [open "{out}" w]
  set m [debug read memory 0xFCAF]
  if {{$m == 1}} {{ set a [expr {{0x1800 + 23*32}}]; set w 32 }} else {{ set a [expr {{23*40}}]; set w 40 }}
  set k ""; for {{set i 0}} {{$i < $w}} {{incr i}} {{ append k [format %c [debug read VRAM [expr {{$a+$i}}]]] }}
  puts $f "scrmod=$m oldscr=[debug read memory 0xFCB0] linlen=[debug read memory 0xF3B0] linl32=[debug read memory 0xF3AF]|[string trim $k]"
  close $f; exit }}
'''
    tf = os.path.join(HERE, "scr1prompt.tcl")
    open(tf, "w").write(tcl)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=120)
    cells, keys = open(out).read().strip().split("|", 1)
    return f"{cells} keys={' '.join(keys.split())!r}"


def main():
    bad = 0
    for k, lines in CASES.items():
        r, z = measure(REF, lines), measure(ZB, lines)
        same = r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:12} ref: {r}\n{'':18}zb:  {z}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
