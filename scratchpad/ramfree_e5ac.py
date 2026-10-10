#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-WCACHE W3a RAM hunt -- is `$E5AC..$E5BF` free in BOTH maps? Ask the machine.

W3a needs one byte the shared FAT body can read in disk.rom AND in the sub-ROM:
a "defer the FAT write" flag that only the sequential writer sets. The maps
say this run is nobody's: basic/sysvars.inc caps its cells below $E560 and puts
its buffers from $E5C0, and disk/equates.inc's own cells there end at
MBUF_PTR ($E5AA, a word). `tools/ram_map.py` lists `$E5AC..$E5C0` as an
UNATTRIBUTED run -- a candidate, not a guarantee: a cell addressed by offset
has no `equ`. So the machine is asked.

THE MEASUREMENT. A write watchpoint on `$E5AC..$E5BF`, armed 12 s after power-on
(the boot's own init is not the subject), logs every write with its PC, through:
MSX-DOS first (the disk boots into it: DIR, COPY, DEL), `BASIC`, the BASIC disk
verbs (OPEN / PRINT# / CLOSE, a random file, SAVE, LOAD, COPY, KILL, NAME, BSAVE,
BLOAD, FILES, DSKF), then `CALL SYSTEM` back into MSX-DOS and DIR, COPY, TYPE -- MSX-DOS keeps page 3 busy, which is the risk no BASIC
read-back could see. zerobas only: a claim about its own map.

    python3 -u scratchpad/ramfree_e5ac.py [system-disk.dsk]
"""
import os, shutil, subprocess, sys, time, signal
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight                                          # noqa: E402
import probe_tmp                                               # noqa: E402

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
DOS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
LO, HI = 0xE5AC, 0xE5BF
STEPS = [  # (typed line, seconds to wait after it). This disk BOOTS INTO MSX-DOS
    # (it holds MSXDOS.SYS): the first run typed BASIC at the A> prompt and saw
    # nothing, the control included -- so DOS first, then BASIC, then back.
    ('', 5),                           # MSX-DOS's date prompt (dosmode_probe's step)
    ('DIR', 6), ('COPY COMMAND.COM C.COM', 10), ('DEL C.COM', 6),
    ('BASIC', 10),
    ('POKE &HE5AC,PEEK(&HE5AC)', 2),   # the CONTROL: exactly this write must be seen
    ('OPEN "P.TXT" FOR OUTPUT AS 1:FOR I=1 TO 60:PRINT#1,"HELLO WORLD":NEXT:CLOSE 1', 14),
    ('OPEN "R.DAT" AS 1 LEN=32:FIELD 1,32 AS F$:LSET F$="X":PUT 1,3:GET 1,1:CLOSE 1', 8),
    ('10 REM A PROGRAM', 2), ('SAVE "Q.BAS"', 6), ('LOAD "Q.BAS"', 6),
    ('COPY "Q.BAS" TO "C.BAS"', 8), ('NAME "C.BAS" AS "D.BAS"', 4), ('KILL "D.BAS"', 4),
    ('BSAVE "B.BIN",&H9000,&H93FF', 6), ('BLOAD "B.BIN"', 6), ('FILES', 4),
    ('PRINT DSKF(0)', 6), ('CALL SYSTEM', 16), ('DIR', 6), ('COPY Q.BAS Z.BAS', 8),
    ('TYPE P.TXT', 8),
]


def main():
    if not os.path.isfile(DOS):
        print(f"INSTRUMENT FAULT: no MSX-DOS system disk at {DOS}")
        return 2
    out = probe_tmp.tmp("ramfree_e5ac.log")
    dsk = probe_tmp.tmp("ramfree_e5ac.dsk")
    shutil.copyfile(DOS, dsk)
    if os.path.exists(out):
        os.unlink(out)
    t = 20.0                       # MSX-DOS boots from this disk (dosmode_probe: 16 s)
    b = ["set throttle off",
         f"set ::wf [open {{{out}}} w]",
         "proc ::w {} { puts $::wf \"W [format %04X $::wp_last_address] "
         "[format %02X $::wp_last_value] pc=[format %04X [reg pc]] t=[machine_info time]\"; flush $::wf }",
         f"after time {t:.1f} {{ debug set_watchpoint write_mem {{0x{LO:04X} 0x{HI:04X}}} {{}} ::w; "
         "puts $::wf ARMED; flush $::wf }"]
    for typed, wait in STEPS:
        t += 1.0
        safe = typed.replace('"', '\\"')
        b.append(f'after time {t:.1f} {{ type "{safe}\\r"; puts $::wf "STEP {safe}"; flush $::wf }}')
        t += wait
    # the screen at the end, as dosmode_probe reads it: the mode decides the base
    b += ["proc rd {a} { debug read memory $a }",
          "proc rd16 {a} { expr {[rd $a] + 256*[rd [expr {$a+1}]]} }",
          f"after time {t + 1:.1f} {{ set m [rd 0xFCAF]; "
          "if {$m == 0} { set base [rd16 0xF3B3]; set w 40 } else { set base [rd16 0xF3BD]; set w 32 }; "
          "binary scan [debug read_block VRAM $base [expr {$w*24}]] H* h; "
          "puts $::wf \"SCREEN $w $h\"; flush $::wf }"]
    b.append(f"after time {t + 2:.1f} {{ puts $::wf DONE; close $::wf; exit }}")
    script = probe_tmp.tmp("ramfree_e5ac.tcl")
    open(script, "w").write("\n".join(b) + "\n")
    proc = subprocess.Popen(omsx_preflight.guarded(
        [OMSX, "-machine", ZB, "-diska", dsk, "-command",
         "set renderer none; set sound_driver null", "-script", script]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 400
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.5)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    lines = open(out).read().splitlines() if os.path.exists(out) else []
    if "ARMED" not in lines or "DONE" not in lines:
        print("INSTRUMENT FAULT: the session did not arm or did not finish")
        print("\n".join(lines[-5:]))
        return 2
    step, writes, control = None, [], []
    for l in lines:
        if l.startswith("STEP "):
            step = l[5:]
        elif l.startswith("W "):
            (control if step and step.startswith("POKE") else writes).append(l)
    scr = [l for l in lines if l.startswith("SCREEN ")]
    if scr:
        _, w, hx = scr[-1].split(" ", 2)
        txt = "".join(chr(c) if 32 <= c < 127 else " " for c in bytes.fromhex(hx))
        w = int(w)
        print("final screen:")
        for i in range(0, len(txt), w):
            if txt[i:i + w].strip():
                print("  |" + txt[i:i + w].rstrip())
    if len(control) != 1:
        print(f"INSTRUMENT FAULT: the control POKE was seen {len(control)} times, not once")
        return 2
    step = None
    for l in lines:
        if l.startswith("STEP "):
            step = l[5:]
        elif l.startswith("W "):
            if not (step or "").startswith("POKE"):
                print(f"  WRITE during {step!r}: {l}")
    print(f"\ncontrol seen once; {len(writes)} other write(s) to ${LO:04X}..${HI:04X} over {len(STEPS) - 1} steps"
          f" -- {'FREE as measured' if not writes else 'NOT free'}")
    return 0 if not writes else 1


if __name__ == "__main__":
    sys.exit(main())
