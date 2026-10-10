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
  content-x on a disk whose clusters 9..339 are pre-marked used, a 140-line file
            (2941 B, THREE clusters: 340, 341, 342) -- read back, both machines
  fat-x     that file's FAT chain, read from the IMAGE afterwards: `340>341>342
            EOC` on both. The chain crosses FAT sectors 0/1 (341's entry
            straddles them), so 342's mark is DEFERRED (W3a) and the 341->342
            link loads sector 0: the held sector must be written first. A lost
            mark on the LAST cluster reads back fine (readers stop at the size)
            and shows only here, as the chain ending in a FREE cluster -- the
            first cut of this row read content alone and K-WC4 moved nothing.
  zb-reads  zerobas's READ commands  <= READ_BUDGET   (zb only: a budget, not a
  zb-writes zerobas's WRITE commands <= WRITE_BUDGET   comparison; the CF-3300
                                                       is printed beside it)
The budgets are the slice's measured figures. A slice that saves commands
lowers them; a change that adds commands back turns them red.
  W1 (2026-10-10): 28 -> 23 reads (the boot sector is no longer re-read per
  cluster -- the cluster count is fat_mount's). Writes 36.
  W2 (2026-10-10): 23 -> 14 reads (marking a cluster and linking the previous
  one no longer re-read the FAT sector the allocation just loaded).
  W3a (2026-10-11): 36 -> 28 writes (a chain extension's mark waits for the link,
  which writes that FAT sector once with both entries).

Prints `ROW <name> CF=[...] ZB=[...] <verdict>`; exit 0 all pass, 1 a failure,
2 no reading. CF-3300 vs zerobas DISK.
"""
import collections, os, re, shutil, struct, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

READ_BUDGET, WRITE_BUDGET = 14, 28
LINES = ['OPEN "X" FOR OUTPUT AS 1',
         'POKE &HD000,1:FOR I=1 TO 200:PRINT#1,"ABCDEFGHIJKLMNOPQRS":NEXT:CLOSE#1:POKE &HD000,2',
         'OPEN "X" FOR INPUT AS 1:N=0',
         'FOR I=1 TO 200:LINE INPUT#1,A$:N=N+1:NEXT',
         'PRINT "[";N;A$;EOF(1);"]":CLOSE#1']
SIDES = [("CF", "National_CF-3300", ("", "SCREEN 0:WIDTH 40", "POKE &HD000,0")),
         ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK", ("", "SCREEN 0:WIDTH 40", "POKE &HD000,0"))]


LINES_X = [l.replace("FOR I=1 TO 200", "FOR I=1 TO 140") for l in LINES]


def chain(path, name83=b"X          "):
    """The directory entry's first cluster, then the FAT12 chain from the image:
    `340>341>342 EOC`, or `... FREE` / `... BAD` where it does not end properly."""
    d = open(path, "rb").read()
    bps, _spc, rsv, nf, ents = struct.unpack_from("<HBHBH", d, 11)
    spf = struct.unpack_from("<H", d, 22)[0]
    root = (rsv + nf * spf) * bps
    first = None
    for i in range(ents):
        e = d[root + 32 * i: root + 32 * i + 32]
        if e[:11] == name83:
            first = struct.unpack_from("<H", e, 26)[0]
    if first is None:
        return "NO ENTRY"
    fat = d[rsv * bps:(rsv + spf) * bps]
    out, n = [], first
    for _ in range(20):
        out.append(str(n))
        v = (fat[n * 3 // 2] | fat[n * 3 // 2 + 1] << 8)
        v = v >> 4 if n & 1 else v & 0xFFF
        if v >= 0xFF8:
            return ">".join(out) + " EOC"
        if v in (0, 1) or v >= 0xFF0:
            return ">".join(out) + (" FREE" if v == 0 else f" BAD{v:03X}")
        n = v
    return ">".join(out) + " LOOP"


def prefill(path, first=9, last=339):
    """Mark clusters first..last used ($FFF, each its own chain end -- lost
    clusters, in no directory entry) in every FAT copy, so the next allocation
    starts at last + 1. FAT12 packing (Microsoft FAT spec section 3.2)."""
    d = bytearray(open(path, "rb").read())
    bps, _spc, rsv, nf = struct.unpack_from("<HBHB", d, 11)
    spf = struct.unpack_from("<H", d, 22)[0]
    for k in range(nf):
        base = (rsv + k * spf) * bps
        for n in range(first, last + 1):
            o = base + n * 3 // 2
            v = d[o] | d[o + 1] << 8
            v = (v & 0x000F) | (0xFFF << 4) if n & 1 else (v & 0xF000) | 0xFFF
            d[o], d[o + 1] = v & 0xFF, v >> 8
    open(path, "wb").write(d)


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
        # the cross-sector run: a second boot, its own image, no counting
        dsx = probe_tmp.tmp(f"wcache_x_{side}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsx)
        prefill(dsx)
        scx = omsx_repl.run_cases(m, [("direct", LINES_X)], batch=False, diska=dsx, boot=14.0,
                                  reset=reset, step=14.0, run_gap=40.0)[0] or ""
        mx = re.findall(r"\[([^\]\"]*)\]", scx.replace("\n", ""))
        got[side] = (c["READ"], c["WRITE"], " ".join(m2[-1].split()) if m2 else None,
                     " ".join(mx[-1].split()) if mx else None, chain(dsx))
    bad, blind = [], []
    cf, zb = got["CF"], got["ZB"]
    rows = [("content", cf[2], zb[2], None),
            ("content-x", cf[3], zb[3], None),
            ("fat-x", cf[4], zb[4], None),
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
