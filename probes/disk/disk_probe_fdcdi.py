# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FDCDI (gate: fdcdi-acceptance): keys typed during long disk work are kept.

The program writes 4200 B (200 x PRINT#1 + CLOSE) and POKEs &HD000 = 1 when it
starts and 2 when it is done. DELAY emulated seconds after the start, openMSX
TYPES the next line through the key matrix -- `print"z"+"q"+str$(7*6)` -- so it
can only arrive if the keyboard is scanned while the disk works. 30 s later the
screen is read: `zq 42`, the line's own output, says it arrived whole and ran.

The FDC driver used to keep interrupts masked for each whole sector command,
rotational wait included, so keys typed meanwhile were lost: 7-12 of 22
characters arrived here, 15-18 on the National CF-3300
(scratchpad/fdcdi_typeahead*.out). Since 2026-10-11 the wait for a sector's
FIRST byte opens interrupt windows when the caller had interrupts on (disk/fat.asm
fdc_fdrq, the inline poll in disk/kernel.asm's fdc_read_data_body), and a first
byte lost to an interrupt is simply read again; every delay ARRIVED whole.
🔴 2026-10-12 (D-TOKOVF): "every delay" WAS THREE PHASES, NOT A PROPERTY. A
change of ~2 T-states per crunched character in the tokeniser -- nowhere near
the disk code -- lost the shifted `*` at d8 (`str$(76)`). The frame interrupt
is never held off a whole frame here any more: during this workload zerobas's
longest wait is 16 ms, in the sector loops (fwd_wait / fdc_rd_wait: one 512-byte
sector at 32 us a byte, which cannot be interrupted without losing data), with
NO frame lost, where the CF-3300 waits up to 212 ms and loses 25 frames
(scratchpad/irqlat_fdcdi.out). So a key event can still fall inside a sector
transfer on both machines, and WHOLE at every phase is not attainable. The
bound is therefore the reference's own BEST: each row must keep at least
REF_BEST of the 22 characters (the CF-3300 kept 15-18); before the windows
zerobas kept 7-13, so the knife K-FD1 still turns every row red.

Rows `d3`, `d5`, `d8`: `ZB=[WHOLE]` or `ZB=[LOST <echo>]`. Exit 0 all whole,
1 a loss, 2 no reading.
"""
import os, re, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
LOOP = 'for i=1 to 200:print#1,\\"abcdefghijklmnopqrs\\":next:close#1:poke \\&hd000,2'
TYPED = 'print\\"z\\"+\\"q\\"+str\\$(7*6)\\r'   # \\$: Tcl would read $(7*6) as a variable
DELAYS = (3, 5, 8)
PLAIN = 'print"z"+"q"+str$(7*6)'                  # TYPED as it reaches the screen
REF_BEST = 18                                       # the CF-3300's best, of 22


def kept(echo):
    """How many of PLAIN's characters arrived, in order (a lost key only ever
    REMOVES one -- a greedy subsequence count)."""
    n, j = 0, 0
    for c in echo:
        if j < len(PLAIN) and c == PLAIN[j]:
            n, j = n + 1, j + 1
        else:
            k = PLAIN.find(c, j)
            if k >= 0:
                n, j = n + 1, k + 1
    return n


def run(delay):
    dsk = probe_tmp.tmp(f"fdcdi_{delay}.dsk")
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    out = probe_tmp.tmp(f"fdcdi_{delay}.txt")
    if os.path.exists(out):
        os.remove(out)
    tcl = f'''set throttle off
set f [open {{{out}}} w]
set t1 0
set t2 0
proc scr {{}} {{ set b [expr {{[debug read "VDP regs" 2] * 1024}}]; set s ""; for {{set i 0}} {{$i < 960}} {{incr i}} {{ set c [debug read VRAM [expr {{$b + $i}}]]; if {{$c < 32 || $c > 126}} {{append s " "}} else {{append s [format %c $c]}} }}; return $s }}
proc fin {{}} {{ puts $::f "t=[expr {{$::t2 - $::t1}}] scr=[scr]"; close $::f; exit }}
proc poll {{}} {{
  set v [debug read memory 0xD000]
  if {{$v == 1 && $::t1 == 0}} {{ set ::t1 [machine_info time]; after time {delay} {{ type "{TYPED}" }}; after time [expr {{{delay} + 30}}] fin }}
  if {{$v == 2 && $::t2 == 0}} {{ set ::t2 [machine_info time] }}
  if {{$::t2 == 0}} {{ after time 0.02 poll }}
}}
after time 12 {{ type "\\r" }}
after time 14 {{ debug write memory 0xD000 0; type "open\\"big.txt\\" for output as #1:poke \\&hd000,1:{LOOP}\\r"; poll }}
after time 400 {{ puts $f "timeout m=[debug read memory 0xD000] scr=[scr]"; close $f; exit }}
'''
    tf = probe_tmp.tmp(f"fdcdi_{delay}.tcl")
    open(tf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(
        [OMSX, "-machine", ZB, "-diska", dsk, "-command",
         "set renderer none; set sound_driver null; set save_settings_on_exit false",
         "-script", tf]), capture_output=True, timeout=900)
    r = open(out).read().strip() if os.path.exists(out) else ""
    if not r.startswith("t="):
        return None
    if "zq 42" in r:
        return "WHOLE"
    sc = r[r.find("scr=") + 4:]
    rows = [sc[k:k + 40].strip() for k in range(0, len(sc), 40)]
    i = max((k for k, x in enumerate(rows) if x.endswith("000,2")), default=None)
    echo = rows[i + 2] if i is not None and i + 2 < len(rows) else "?"
    return f"LOST {echo}"


def main():
    bad, blind = [], []
    for d in DELAYS:
        v = run(d)
        name = f"d{d}"
        if v is None:
            verdict = "NO-READING"
            blind.append(name)
        elif v == "WHOLE":
            verdict = f"KEPT {len(PLAIN)}/{len(PLAIN)}"
        else:
            k = kept(v[len("LOST "):])
            verdict = f"KEPT {k}/{len(PLAIN)}"
            if k < REF_BEST:
                verdict += f" -- UNDER THE CF-3300'S {REF_BEST}"
                bad.append(name)
        print(f"ROW {name} ZB=[{v}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: keys typed during PRINT# + CLOSE "
          f"({len(DELAYS) - len(bad)}/{len(DELAYS)} at or above the CF-3300's best, "
          f"{REF_BEST}/{len(PLAIN)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
