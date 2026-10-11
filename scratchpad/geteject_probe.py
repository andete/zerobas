#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOADERRRET, the GET site (basic/field.asm: `jp c,load_error` after
fat_rand_get): what does a GET whose disk READ fails raise, under ON ERROR?

No row reached a GET read failure before; this makes one. A 40-record random
file is written and reopened, then the program POKEs &HD000 = 1 and spins; a Tcl
poll sees the mark and EJECTS the disk (`diska eject`); the program then GETs
record 20 -- data the drive must read -- under ON ERROR, and prints ERR / ERL /
a sentinel that says whether the line after the GET ran. Clean room: typed BASIC
and the text screen, a RAM mark, a media command; no ROM byte read.

    python3 -u scratchpad/geteject_probe.py [cf] [zb]
"""
import os, re, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight, probe_tmp

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
SIDES = {"cf": "National_CF-3300", "zb": "C-BIOS_MSX1_EU_REPACK_DISK"}
PROG = [
    "10 ON ERROR GOTO 90",
    '20 OPEN "R.DAT" AS 1 LEN=128:FIELD 1,128 AS F$',
    '30 FOR I=1 TO 40:LSET F$=STR$(I):PUT 1,I:NEXT:CLOSE 1',
    '40 OPEN "R.DAT" AS 1 LEN=128:FIELD 1,128 AS F$',
    "50 POKE &HD000,1:FOR W=1 TO 3000:NEXT",
    "60 GET 1,20",
    '70 PRINT CHR$(91);"RAN";VAL(F$);CHR$(93):END',
    '90 PRINT CHR$(91);"ERR";ERR;ERL;CHR$(93):END',  # CHR$(91): a typed `[` is Tcl
                                                    # command substitution -- the first
                                                    # run typed NOTHING on either side
]


def run(tag, machine, eject=True):
    dsk = probe_tmp.tmp(f"geteject_{tag}.dsk")
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    out = probe_tmp.tmp(f"geteject_{tag}.txt")
    if os.path.exists(out):
        os.remove(out)
    def tcl_quote(s):   # every character a Tcl "..." string interprets
        for a, b in (("\\", "\\\\"), ('"', '\\"'), ("$", "\\$"), ("[", "\\["), ("]", "\\]")):
            s = s.replace(a, b)
        return s
    # the second run typed nothing either: STR$(I) is Tcl's array variable $(I)
    typed = "".join(tcl_quote(l) + "\\r" for l in ["NEW"] + PROG + ["RUN"])
    tcl = f'''set throttle off
set f [open {{{out}}} w]
set ::ej 0
proc scr {{}} {{ set b [expr {{[debug read "VDP regs" 2] * 1024}}]; set s ""; for {{set i 0}} {{$i < 960}} {{incr i}} {{ set c [debug read VRAM [expr {{$b + $i}}]]; if {{$c < 32 || $c > 126}} {{append s " "}} else {{append s [format %c $c]}} }}; return $s }}
proc poll {{}} {{
  if {{{int(eject)} && !$::ej && [debug read memory 0xD000] == 1}} {{ set ::ej 1; diska eject; puts $::f "EJECTED t=[machine_info time]"; flush $::f }}
  after time 0.05 poll
}}
proc ::fdc {{}} {{ if {{$::ej}} {{ puts $::f "FDC [format %02X $::wp_last_value] trk=[debug read memory 0x7FB9] sec=[debug read memory 0x7FBA] st=[format %02X [debug read memory 0x7FB8]] t=[machine_info time]"; flush $::f }} }}
debug set_watchpoint write_mem 0x7FB8 {{}} ::fdc
after time 12 {{ type "\\r" }}
after time 14 {{ debug write memory 0xD000 0; type "SCREEN 0:WIDTH 40\\r" }}
after time 16 {{ type "{typed}"; poll }}
after time 120 {{ puts $f "scr=[scr]"; close $f; exit }}
'''
    tf = probe_tmp.tmp(f"geteject_{tag}.tcl")
    open(tf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(
        [OMSX, "-machine", machine, "-diska", dsk, "-command",
         "set renderer none; set sound_driver null; set save_settings_on_exit false",
         "-script", tf]), capture_output=True, timeout=600)
    r = open(out).read() if os.path.exists(out) else ""
    ej = "EJECTED" in r
    for line in r.splitlines():
        if line.startswith("FDC "):
            print(f"   {tag} {line}")
    sc = r[r.find("scr=") + 4:] if "scr=" in r else ""
    rows = [sc[k:k + 40].rstrip() for k in range(0, len(sc), 40) if sc[k:k + 40].strip()]
    m = re.findall(r"\[\s*(ERR|RAN)\s*([^\]]*)\]", sc)
    return ej, (m[-1][0] + " " + " ".join(m[-1][1].split())) if m else None, rows[-6:]


def main():
    args = sys.argv[1:]
    eject = "noeject" not in args          # noeject: the CONTROL -- GET 1,20 reads 20
    which = [a for a in args if a in SIDES] or ["cf", "zb"]
    for tag in which:
        ej, reading, tail = run(tag, SIDES[tag], eject)
        print(f"{tag}: ejected={ej} reading={reading}")
        for r in tail:
            print(f"   |{r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
