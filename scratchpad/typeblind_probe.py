"""D-TYPEBLIND: are keys typed while a line is being stored LOST?

Everything else in this tree delivers input by writing the key BUFFER
(omsx_repl's KEYBUF injection), which bypasses the keyboard scan -- so no gate
could see this. Here the keys go through the MATRIX with openMSX's `type`,
~70 ms per key on every machine (measured: zerobas, VG-8020 and stock C-BIOS
alike), exactly as a typist's would. A second `type` QUEUES behind the first,
so a line typed "N s later" starts when the previous one has been delivered.

Found 2026-09-26: zerobas ran its page-0 tenants -- the tokeniser among them --
under DI, and tokenising a 38-character line took ~0.25 s with no keyboard
scan; keys pressed in that window never reached the buffer (`PRINT 5` arrived
as `NT 5`, `RUN` as `RRUN`). The fix runs the tokeniser with interrupts live
(sub/sub.asm tokenise_ei).

Cases (fresh boot each, headless, both machines; the screen is read at the end):
  wrap+N   a 38-char stored line (it wraps), then `PRINT 5` N s after it
  short+N  a 29-char stored line, then `PRINT 5`
  prog     a whole program typed in ONE go, `RUN` included -- a fast typist
           who never waits for a line to be stored

Clean room: typed keys and the screen (VRAM name table) only.
⚠️ The VG-8020 itself garbled one `type` in an earlier sweep (`RN`), so a
single reference miss is the instrument, not a verdict; the rows print both.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
BS = "\\"
W = "10 N=N+1:A=PAD(0):LOCATE 0,0:PRINT 44"
S = "10 N=N+1:A=PAD(0):LOCATE 0,0"
Q = BS + '"'        # a quote inside Tcl's double-quoted `type` argument
PROG = (f"10 A=12:B=30:C$={Q}TYPED{Q}{BS}r20 PRINT C$;A+B{BS}r"
        f"30 IF A<99 THEN PRINT {Q}OK{Q};A*B{BS}rRUN{BS}r")


def seq(*items):
    return [f'after time {t} {{type "{txt}{BS}r"}}' for t, txt in items]


CASES = {
    "wrap+1.0": seq((14, W), (15.0, "PRINT 5")),
    "wrap+2.0": seq((14, W), (16.0, "PRINT 5")),
    "short+0.5": seq((14, S), (14.5, "PRINT 5")),
    "prog": [f'after time 14 {{type "{PROG}"}}'],
}


def screen(machine, lines):
    out = os.path.join(HERE, "typeblind_screen.txt")
    tcl = "\n".join(lines) + f'''
after time 26 {{ set f [open "{out}" w]; set s ""
  for {{set i 0}} {{$i < 960}} {{incr i}} {{ append s [format %c [debug read VRAM $i]] }}
  for {{set r 0}} {{$r < 24}} {{incr r}} {{ puts $f "[string range $s [expr {{$r*40}}] [expr {{$r*40+39}}]]" }}
  close $f; exit }}
'''
    tf = os.path.join(HERE, "typeblind.tcl")
    open(tf, "w").write(tcl)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=180)
    rows = [r.strip() for r in open(out).read().split("\n") if r.strip()]
    # the function-key line and the PROMPT are furniture: the VG-8020 says `Ok`
    # (and leaves its cursor cell as `\xff`), zerobas's diskless build `ZB`
    return [r for r in rows if "color" not in r and r not in ("Ok", "ZB", "\xff")]


def answer(rows):
    """What followed the first stored line: the next typed line and its result."""
    i = [j for j, r in enumerate(rows) if r.startswith("10 ")]
    return " / ".join(rows[i[0] + 1:] if i else rows[-3:])


def main():
    bad = 0
    for k, lines in CASES.items():
        r, z = answer(screen(REF, lines)), answer(screen(ZB, lines))
        same = r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:10} ref: {r}\n{'':16}zb:  {z}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
