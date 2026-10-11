# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GETEJECT (gate: geteject-acceptance) -- D-LOADERRRET's GET site
(basic/field.asm gp_fin, after fat_rand_get): what does a GET whose disk READ
fails raise, under ON ERROR?

No row reached a GET read failure before; this makes one. A 40-record random
file is written and reopened, then the program POKEs &HD000 = 1 and spins; a Tcl
poll sees the mark and EJECTS the disk (`diska eject`); the program then GETs
record 20 -- data the drive must read -- under ON ERROR, and prints ERR / ERL /
a sentinel that says whether the line after the GET ran. Clean room: typed BASIC
and the text screen, a RAM mark, a media command; no ROM byte read.

Rows (CF-3300 vs zerobas DISK): `ctl` the disk stays in, GET reads 20; then,
with the disk ejected before line 60: `get`, `put`, `linput` (LINE INPUT #
through a 300-line file), `load`, `bload`, `files`, `openin` -- each `ERR 70 60`
(Disk offline, in the verb's line, trapped) on both. `printc` (PRINT # + CLOSE)
is zerobas-only: the CF-3300 waits there, and our 70 is pinned.
D-LINEJECT (2026-10-11): LINE INPUT # answered 55 `Input past end`, the same
read-failure-as-EOF shape (basic/files.asm seq_end).
Before 2026-10-11 zerobas answered `get` with RAN 0: the chain walk's failed
FAT read was taken for end-of-file and the record filled with spaces
(basic/randio-body.inc frg_eofchk). Exit 0 all same, 1 a divergence, 2 no
CF-3300 reading.
"""
import os, re, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight, probe_tmp

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
SIDES = {"cf": "National_CF-3300", "zb": "C-BIOS_MSX1_EU_REPACK_DISK"}
# (name, prep lines 20-49, the verb on line 60) -- the eject happens at line 50
CASES = {
    "get":    (['20 OPEN "R.DAT" AS 1 LEN=128:FIELD 1,128 AS F$',
                '30 FOR I=1 TO 40:LSET F$=STR$(I):PUT 1,I:NEXT:CLOSE 1',
                '40 OPEN "R.DAT" AS 1 LEN=128:FIELD 1,128 AS F$'],
               "60 GET 1,20"),
    "put":    (['20 OPEN "R.DAT" AS 1 LEN=128:FIELD 1,128 AS F$',
                '30 FOR I=1 TO 40:LSET F$=STR$(I):PUT 1,I:NEXT:CLOSE 1',
                '40 OPEN "R.DAT" AS 1 LEN=128:FIELD 1,128 AS F$:LSET F$="Z"'],
               "60 PUT 1,20"),
    "linput": (['20 OPEN "S.TXT" FOR OUTPUT AS 1:FOR I=1 TO 300:PRINT#1,"LINE";I:NEXT:CLOSE 1',
                '40 OPEN "S.TXT" FOR INPUT AS 1'],
               "60 FOR I=1 TO 300:LINE INPUT#1,A$:NEXT"),
    "printc": (['20 OPEN "W.TXT" FOR OUTPUT AS 1'],
               '60 FOR I=1 TO 300:PRINT#1,"LINE";I:NEXT:CLOSE 1'),
    "load":   (['20 SAVE "P.BAS"'], '60 LOAD "P.BAS"'),
    "bload":  (['20 BSAVE "B.BIN",&H9000,&H97FF'], '60 BLOAD "B.BIN"'),
    "files":  ([], "60 FILES"),
    "openin": (['20 OPEN "S.TXT" FOR OUTPUT AS 1:PRINT#1,"X":CLOSE 1'],
               '60 OPEN "S.TXT" FOR INPUT AS 1'),
}

# printc: the CF-3300 WAITS -- no output, no prompt, no FDC command for over a
# minute after its write saw NOT READY (scratchpad/ejectsweep_run.out). A hang is
# not a face to copy; zerobas's trappable 70 is pinned, zerobas only.
ZB_ONLY = {"printc": "ERR 70 60"}


def prog(case):
    prep, verb = CASES["get" if case == "ctl" else case]   # ctl: GET's program, disk kept
    return (["10 ON ERROR GOTO 90"] + prep +
            ["50 POKE &HD000,1:FOR W=1 TO 3000:NEXT", verb,
             '70 PRINT CHR$(91);"RAN";VAL(F$);CHR$(93):END' if case in ("ctl", "get") else
             '70 PRINT CHR$(91);"RAN";CHR$(93):END',
             # STOP, not END: END closes the files, and on the CF-3300 a PUT
             # channel that cannot be flushed raises 70 AGAIN in this line,
             # trapped back into this handler forever -- the first gate run read
             # `ERR 70 90` with the verb's own error scrolled away
             '90 PRINT CHR$(91);"ERR";ERR;ERL;CHR$(93):STOP'])


def run(tag, machine, eject=True, case="get"):
    dsk = probe_tmp.tmp(f"geteject_{tag}_{case}.dsk")
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    out = probe_tmp.tmp(f"geteject_{tag}_{case}.txt")
    if os.path.exists(out):
        os.remove(out)
    def tcl_quote(s):   # every character a Tcl "..." string interprets
        for a, b in (("\\", "\\\\"), ('"', '\\"'), ("$", "\\$"), ("[", "\\["), ("]", "\\]")):
            s = s.replace(a, b)
        return s
    # the second run typed nothing either: STR$(I) is Tcl's array variable $(I)
    typed = "".join(tcl_quote(l) + "\\r" for l in ["NEW"] + prog(case) + ["RUN"])
    tcl = f'''set throttle off
set f [open {{{out}}} w]
set ::ej 0
proc scr {{}} {{ set b [expr {{[debug read "VDP regs" 2] * 1024}}]; set s ""; for {{set i 0}} {{$i < 960}} {{incr i}} {{ set c [debug read VRAM [expr {{$b + $i}}]]; if {{$c < 32 || $c > 126}} {{append s " "}} else {{append s [format %c $c]}} }}; return $s }}
proc poll {{}} {{
  if {{{int(eject)} && !$::ej && [debug read memory 0xD000] == 1}} {{ set ::ej 1; diska eject; puts $::f "EJECTED t=[machine_info time]"; flush $::f }}
  after time 0.05 poll
}}
after time 12 {{ type "\\r" }}
after time 14 {{ debug write memory 0xD000 0; type "SCREEN 0:WIDTH 40\\r" }}
after time 16 {{ type "{typed}"; poll }}
after time 120 {{ puts $f "scr=[scr]"; close $f; exit }}
'''
    tf = probe_tmp.tmp(f"geteject_{tag}_{case}.tcl")
    open(tf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(
        [OMSX, "-machine", machine, "-diska", dsk, "-command",
         "set renderer none; set sound_driver null; set save_settings_on_exit false",
         "-script", tf]), capture_output=True, timeout=600)
    r = open(out).read() if os.path.exists(out) else ""
    ej = "EJECTED" in r
    sc = r[r.find("scr=") + 4:] if "scr=" in r else ""
    rows = [sc[k:k + 40].rstrip() for k in range(0, len(sc), 40) if sc[k:k + 40].strip()]
    m = re.findall(r"\[\s*(ERR|RAN)\s*([^\]]*)\]", sc)
    return ej, (m[-1][0] + " " + " ".join(m[-1][1].split())) if m else None, rows[-6:]


def main():
    rows = ["ctl"] + list(CASES)
    bad, blind = [], []
    for name in rows:
        eject = name != "ctl"
        zej, zb, _t = run("zb", SIDES["zb"], eject, name)
        if not zej == eject:
            zb = f"EJECT={zej}?"
        if name in ZB_ONLY:
            want = ZB_ONLY[name]
            v = "PINNED" if zb == want else f"PIN-ROTTED (want {want})"
            if zb != want:
                bad.append(name)
            print(f"ROW {name} CF=[-] ZB=[{zb}] {v}", flush=True)
            continue
        cej, cf, _t = run("cf", SIDES["cf"], eject, name)
        if cf is None or cej != eject:
            v = "NO-REFERENCE"
            blind.append(name)
        elif cf == zb:
            v = "SAME"
        else:
            v = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} CF=[{cf}] ZB=[{zb}] {v}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: no CF-3300 reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: disk verbs with the disk gone "
          f"({len(rows) - len(bad)}/{len(rows)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
