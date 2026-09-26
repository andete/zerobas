"""D-KEYWIDTH: does the function-key row follow WIDTH?

Found 2026-09-26 (scr1prompt_probe.py, row s1_width): after SCREEN 1:WIDTH 20
the VG-8020's key row reads `col aut got lis run`; zerobas kept its fixed
per-mode layout. This sweeps 13 widths in SCREEN 0 and 11 in SCREEN 1: type
SCREEN n, then WIDTH w, and read row 23 of the live name table raw (a space is
`.`, so the COLUMN of every label shows), plus LINLEN. The reference's rule,
read off these rows: start at the text area's border (row - LINLEN + 1)/2,
pitch (LINLEN + 1)/5, pitch-1 characters a field, nothing at pitch <= 1.

Headless, fresh boot per row, keys through the matrix. Clean room: VRAM and
work-area RAM only. Prints both machines and a SAME/DIFF per width.
"""
import subprocess, os, sys
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
SP = os.path.dirname(os.path.abspath(__file__))
BS = "\\"
CASES = [(0, w) for w in (40, 39, 38, 37, 36, 30, 25, 24, 20, 15, 10, 5, 1)] + \
        [(1, w) for w in (32, 31, 30, 29, 25, 24, 20, 15, 10, 5, 1)]
got = {}
for m in (REF, ZB):
    for mode, w in CASES:
        out = os.path.join(SP, "keywidth.txt")
        lines = [f'after time 14 {{type "SCREEN {mode}{BS}r"}}', f'after time 17 {{type "WIDTH {w}{BS}r"}}']
        tclsrc = "\n".join(lines) + f'''
after time 21 {{ set f [open "{out}" w]
  set m [debug read memory 0xFCAF]
  if {{$m == 1}} {{ set a [expr {{0x1800 + 23*32}}]; set n 32 }} else {{ set a [expr {{23*40}}]; set n 40 }}
  set k ""; for {{set i 0}} {{$i < $n}} {{incr i}} {{ set c [debug read VRAM [expr {{$a+$i}}]]; if {{$c == 32}} {{ append k "." }} else {{ append k [format %c $c] }} }}
  puts $f "linlen=[debug read memory 0xF3B0] |$k|"
  close $f; exit }}
'''
        open(os.path.join(SP, "keywidth.tcl"), "w").write(tclsrc)
        subprocess.run(["openmsx", "-machine", m, "-command", "set save_settings_on_exit false; set renderer none; set sound_driver null", "-script", os.path.join(SP, "keywidth.tcl")], capture_output=True, timeout=120)
        got[(m, mode, w)] = open(out).read().strip()
bad = 0
for mode, w in CASES:
    r, z = got[(REF, mode, w)], got[(ZB, mode, w)]
    bad += r != z
    print(f"{'SAME' if r == z else 'DIFF'} S{mode} W{w:<3} ref {r}\n{'':13}zb  {z}")
print(f"\nDIFF: {bad}/{len(CASES)}")
