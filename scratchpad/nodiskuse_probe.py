#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""RAM lever (2) step (b), measure first: which bytes of zerobas's remaining
workspace ($E26A..$F37F) does the DISKLESS build ever WRITE?

The static map (tools/ram_map.py) says which cells are disk-only, but it also
says its own limit out loud: an unattributed run is a CANDIDATE, never free
space -- a stack that grows down from a named top, or a cell addressed only as
an offset, is invisible to it. So before re-laying the workspace out (the
disk-only tenants packed at the floor, the diskless ceiling above them), ask
the machine.

METHOD (refwork_probe.py's): one boot per case on C-BIOS_MSX1_EU_REPACK_NODISK,
a write watchpoint over the span armed AFTER boot (a power-on watch sees the
boot's own clears), every written ADDRESS recorded (never a value, never a PC
-- this is zerobas's own RAM, but the rule costs nothing to keep). The union
over all cases is what the diskless build uses; its complement, by static
name, is the report.

⚠️ WHAT IT CANNOT SEE: anything no case drives. The cassette (CAL_BUF /
CAL_BUF2 / CAS_WBUF: ASCII LOAD / SAVE to tape) needs a tape and is not run --
those buffers are KNOWN diskless users and are reported as such, not as free.
A byte written only at power-on (the boot clear) is not a use either.

Prediction: never written ~1.4 KB: the FAT sector buffers except the cassette
pair, FLD_TAB / FLD_DESC, most disk-only cells; written: everything the
string / array / FOR / graphics / PLAY / trap / DEF FN cases touch.
🔴 FIRST RUN (2026-10-13): MISS -- 3528 B never written, not ~1.4 KB. "Never
written by these cases" is a LOWER BOUND ON USE, not free space: a buffer's tail
stays unwritten unless a case fills it (STRSCR: 13 of 256 B), and cells written
only AT BOOT (before the watch arms: the interrupt trampoline copy, the slot
scan's cells) are read afterwards, never written. So the run's use for lever (2)
is COUNTER-EVIDENCE only: the second report below lists every cell of the
static DISK-ONLY set (the disk map's own cells, and the FAT / FIELD buffers the
basic map names) that the diskless build DID write -- any row there refutes
the classification the re-layout rests on.
"""
import os, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import omsx_repl                                   # noqa: E402
import ram_map                                     # noqa: E402

MACHINE = "C-BIOS_MSX1_EU_REPACK_NODISK"
SPAN = (0xE26A, 0xF37F)
CAS_KNOWN = ("CAL_BUF", "CAL_BUF2", "CAS_WBUF")   # diskless users no case drives
CASES = {
    "control": ["10 END", "RUN"],
    "longline": ["10 A=1:B=2:C=3:D=4:E=5:F=6:G=7:H=8:I=9:J=10:K=11:L=12:M=13", "RUN"],
    "input": ["10 INPUT A$,B:END", "RUN", "HELLO,5"],
    "linput": ["10 LINE INPUT A$:END", "RUN", "HELLO, WORLD"],
    "deffn": ["10 DEF FNA(X,Y)=X*Y+1:B=FNA(2,3)", '20 DEF FNB$(A$)=A$+"!":C$=FNB$("Q"):END', "RUN"],
    "traps": ["10 ON INTERVAL=1 GOSUB 100:INTERVAL ON", "20 ON KEY GOSUB 100:KEY(1) ON",
              "30 ON STOP GOSUB 100:STOP ON", "40 FOR I=1 TO 300:NEXT:END", "100 RETURN", "RUN"],
    "using": ['10 PRINT USING "###.##";3.14159;:PRINT USING "&";"AB";:PRINT USING "+#.##^^^^";12.5:END', "RUN"],
    "numfmt": ["10 PRINT 1/3;12345678;-1.5E+20;1#/3:END", "RUN"],
    "strings": ['10 A$=STRING$(100,"X")+"Y":B$=MID$(A$,5,10):C$=A$+B$', '20 MID$(C$,2,3)="ZZZ":D$=LEFT$(C$,3)+RIGHT$(C$,2)+STR$(5)+HEX$(255)+CHR$(65)', '30 I=INSTR(C$,"Z"):E$=SPACE$(5):END', "RUN"],
    "val": ['10 A=VAL("123.5")+VAL("&H1F")+VAL("1E3"):END', "RUN"],
    "arrays": ['10 DIM A(100),B$(10),C%(5,5):A(5)=1:B$(3)="X":C%(2,2)=7:ERASE A:END', "RUN"],
    "flow": ["10 FOR I=1 TO 3:FOR J=1 TO 2:GOSUB 100:NEXT J,I", "20 ON 2 GOTO 30,40", "30 END", "40 X=1:END", "100 RETURN", "RUN"],
    "errors": ["10 ON ERROR GOTO 100", "20 ERROR 5", "30 A=1/0", "40 END", "100 RESUME NEXT", "RUN"],
    "math": ["10 A=SIN(1)+COS(1)+TAN(1)+ATN(1)+LOG(2)+EXP(1)+SQR(2)+RND(1)+2^0.5+INT(2.5)+FIX(-2.5):END", "RUN"],
    "graphics": ['10 SCREEN 2:PSET(10,10):LINE(0,0)-(50,50),15,BF:CIRCLE(100,100),30', '20 PAINT(100,100),4:DRAW "U10R10D10L10":PUT SPRITE 0,(10,10),15,0', "30 SCREEN 0:END", "RUN"],
    "sound": ['10 PLAY "CDEFG":SOUND 8,10:BEEP:FOR I=1 TO 200:NEXT:END', "RUN"],
    "edit": ["10 PRINT 1", "20 GOTO 10", "30 END", "RENUM 100,10", "DELETE 110", "LIST"],
    "keys": ['KEY 1,"HELLO"', "KEY LIST"],
    "clear": ["10 CLEAR 500:MAXFILES=2:A=FRE(0):B=FRE(\"\"):END", "RUN"],
    "misc": ['10 A=VARPTR(B):POKE &HC000,1:C=PEEK(&HC000):D$=INKEY$:E=TIME:F=STICK(0):END', "RUN"],
}


def run(lines):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="nodiskuse_")
    os.close(fd)
    os.unlink(path)
    pro = (
        "set ::__wseen [dict create]",
        f"set ::__wf {{{path}}}",
        "proc __wrec {} { set a $::wp_last_address; "
        "if {![dict exists $::__wseen $a]} { dict set ::__wseen $a 1; "
        "set f [open $::__wf a]; puts $f $a; close $f } }",
        f"after time 7.5 {{debug set_watchpoint write_mem {{0x{SPAN[0]:04X} 0x{SPAN[1]:04X}}} {{}} {{__wrec}}}}",
    )
    omsx_repl.run_cases(MACHINE, [("direct", ["NEW"] + lines)], batch=False,
                        reset=("", "SCREEN 0"), run_gap=12.0, prologue=pro)
    if not os.path.exists(path):
        return None
    addrs = {int(l) for l in open(path) if l.strip()}
    os.unlink(path)
    return addrs


def ranges(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1] + 1:
            cur[1] = a
        else:
            cur = [a, a]
            out.append(cur)
    return out


def main():
    written, per = set(), {}
    for name, lines in CASES.items():
        got = run(lines)
        per[name] = got
        print(f"{name:9s} {'NONE' if got is None else len(got):>5} addresses", flush=True)
        if got:
            written |= got
    span = SPAN[1] - SPAN[0] + 1
    ctl = per.get("control")
    if ctl is None or len(ctl) > span // 2:
        print(f"INSTRUMENT FAULT: the control wrote "
              f"{'nothing readable' if ctl is None else len(ctl)} of {span} addresses")
        return 2
    maps = {c: ram_map.Map(c, SPAN[0], SPAN[1] + 1) for c in ("basic", "disk")}

    def names_in(lo, hi):
        out = []
        for c, m in maps.items():
            for a in m.addrs:
                w = m.width.get(a) or 1
                if a <= hi and a + w - 1 >= lo:
                    out.append(f"{c[0]}:{'/'.join(m.byaddr[a])}")
        return out

    never = sorted(set(range(SPAN[0], SPAN[1] + 1)) - written)
    print(f"\nwritten by the diskless build over {len(CASES)} cases: {len(written)} of {span} B")
    print(f"NEVER written: {len(never)} B. Runs of 8 B or more, with the static names in them")
    print("(b: = basic map, d: = disk map; a run with NO name is an unattributed span):")
    tot = 0
    for lo, hi in ranges(never):
        n = hi - lo + 1
        if n < 8:
            continue
        tot += n
        nm = names_in(lo, hi)
        cas = [x for x in nm if any(k in x for k in CAS_KNOWN)]
        tag = "  ⚠️ CASSETTE: a known diskless user no case drives" if cas else ""
        print(f"  ${lo:04X}..${hi:04X} {n:5d} B  {', '.join(nm)[:150] or '(no name)'}{tag}")
    print(f"  total in runs >= 8 B: {tot} B")
    open(os.path.join(REPO, "scratchpad", "nodiskuse_written.txt"), "w").write(
        "".join(f"{a:04X}\n" for a in sorted(written)))
    # COUNTER-EVIDENCE: static disk-only cells the diskless build wrote
    basic_names = {n for a in maps["basic"].addrs for n in maps["basic"].byaddr[a]}
    disk_bufs = ("FAT_DBUF", "FAT_MBUF", "FSECTOR_BUF", "FWBUF", "FLD_TAB", "FLD_DESC")
    hits = []
    for c, m in maps.items():
        for a in m.addrs:
            ns = m.byaddr[a]
            disk_only = (c == "disk" and not any(n in basic_names for n in ns)) or \
                        (c == "basic" and any(n in disk_bufs for n in ns))
            if not disk_only or any(k in n for n in ns for k in CAS_KNOWN):
                continue
            w = m.width.get(a) or 1
            got = [x for x in range(a, a + w) if x in written]
            if got:
                hits.append(f"{c}:{'/'.join(ns)} ${a:04X} ({len(got)} of {w} B written)")
    print(f"\nCOUNTER-EVIDENCE -- static disk-only cells the diskless build WROTE: {len(hits)}")
    for h in hits:
        print("  " + h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
