# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WCACHE (gate: wcache-acceptance): how many FDC sector commands a sequential
PRINT# + CLOSE costs, and that the file still reads back whole. The design and
its four slices are in docs/spec-diskwcache.md.

The workload is D-FDCDI's: `OPEN "X" FOR OUTPUT AS 1`, 200 x `PRINT#1` of 19
characters, `CLOSE`. A write watchpoint on the WD2793 command register ($7FB8,
memory-mapped on both machines -- an I/O register, the permitted side of the
clean room) counts READ and WRITE commands while the program's marker
(POKE &HD000) reads 1. The file is then read back with LINE INPUT#.

Rows:
  content   `<lines read> <the last line> <EOF(1) after it>` -- both machines, SAME
  zb-reads  zerobas's READ commands  <= READ_BUDGET   (zb only: a budget, not a
  zb-writes zerobas's WRITE commands <= WRITE_BUDGET   comparison; the CF-3300
                                                       is printed beside it)
The budgets are the slice's measured figures. A slice that saves commands
lowers them; a change that adds commands back turns them red.
  W1 (2026-10-10): 28 -> 23 reads (the boot sector is no longer re-read per
  cluster -- the cluster count is fat_mount's). Writes 36.

Prints `ROW <name> CF=[...] ZB=[...] <verdict>`; exit 0 all pass, 1 a failure,
2 no reading. CF-3300 vs zerobas DISK.
"""
import collections, os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

READ_BUDGET, WRITE_BUDGET = 23, 36
LINES = ['OPEN "X" FOR OUTPUT AS 1',
         'POKE &HD000,1:FOR I=1 TO 200:PRINT#1,"ABCDEFGHIJKLMNOPQRS":NEXT:CLOSE#1:POKE &HD000,2',
         'OPEN "X" FOR INPUT AS 1:N=0',
         'FOR I=1 TO 200:LINE INPUT#1,A$:N=N+1:NEXT',
         'PRINT "[";N;A$;EOF(1);"]":CLOSE#1']
SIDES = [("CF", "National_CF-3300", ("", "SCREEN 0:WIDTH 40", "POKE &HD000,0")),
         ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK", ("", "SCREEN 0:WIDTH 40", "POKE &HD000,0"))]


def kind(b):
    return ("READ" if (b & 0xE0) == 0x80 else "WRITE" if (b & 0xE0) == 0xA0 else "other")


def main():
    got = {}
    for side, m, reset in SIDES:
        log = probe_tmp.tmp(f"wcache_{side}.txt")
        if os.path.exists(log):
            os.unlink(log)
        dsk = probe_tmp.tmp(f"wcache_{side}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        pro = (f"set __cf [open {{{log}}} w]",
               "proc __fdc {} { if {[debug read memory 0xD000] == 1} "
               "{ puts $::__cf [format %02X $::wp_last_value]; flush $::__cf } }",
               "debug set_watchpoint write_mem 0x7FB8 {} { __fdc }")
        scr = omsx_repl.run_cases(m, [("direct", LINES)], batch=False, diska=dsk, boot=14.0,
                                  reset=reset, step=14.0, run_gap=40.0, prologue=pro)[0] or ""
        # step 14: the PRINT# + CLOSE line keeps both machines busy for seconds, and
        # the next typed line was lost on the CF-3300 at 4 (keys typed during disk
        # work -- D-FDCDI's own subject; the harness refused the mangled echo)
        v = open(log).read().split() if os.path.exists(log) else []
        c = collections.Counter(kind(int(x, 16)) for x in v)
        m2 = re.findall(r"\[([^\]\"]*)\]", scr.replace("\n", ""))
        got[side] = (c["READ"], c["WRITE"], " ".join(m2[-1].split()) if m2 else None)
    bad, blind = [], []
    cf, zb = got["CF"], got["ZB"]
    rows = [("content", cf[2], zb[2], None),
            ("zb-reads", cf[0], zb[0], READ_BUDGET),
            ("zb-writes", cf[1], zb[1], WRITE_BUDGET)]
    for name, c, z, budget in rows:
        if c is None or z is None or (budget is not None and z == 0):
            v = "NO-READING"
            blind.append(name)
        elif budget is None:
            v = "SAME" if c == z else "DIVERGES"
        else:
            v = f"WITHIN {budget}" if z <= budget else f"OVER {budget}"
        if v.startswith(("DIVERGES", "OVER")):
            bad.append(name)
        print(f"ROW {name} CF=[{c}] ZB=[{z}] {v}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: the write path's commands "
          f"({len(rows) - len(bad)}/{len(rows)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
