#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""RAM lever (2) step (b1): WHO writes the disk-only cells on the DISKLESS
build? A census with the writer's PC, from power-on.

nodiskuse_probe.out found fld_init writing FLD_TAB on NEW / RUN, ungated -- but
that watch armed after boot and recorded no writer. Once the disk-only tenants
sit under the diskless ceiling (the channel blocks and the string space live
there), EVERY such write corrupts a running program, so every writer has to be
found and gated on DISKSLOT_OK.

THE DISK-ONLY SET (static, from tools/ram_map.py over $E26A..$F37F): every byte
covered by a disk-map cell that no basic-map cell covers, plus the basic map's
FAT / FIELD buffers (FAT_DBUF, FAT_MBUF, FLD_TAB, FLD_DESC) less the cassette
buffers that live inside them (CAL_BUF, CAL_BUF2 -- diskless users).

METHOD: NODISK machine, a write watchpoint per disk-only run, armed at TIME 0
(the boot counts), recording (PC, primary slot register, address) -- zerobas's
own code addresses on our own machine; no reference is involved. A PC is
symbolised against build/basic-reloc.sym (main, slot 0) or build/sub*.sym (the
sub ROMs, slot 3); slot 0 below the main image's base is C-BIOS.

Prediction: run-time writers fld_init (NEW / RUN) and fld_clear_chan (CLOSE);
at boot one or two initialisers; perhaps a C-BIOS RAM clear.
"""
import bisect, os, re, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                   # noqa: E402
import ram_map                                     # noqa: E402
from nodiskuse_probe import CASES, MACHINE, SPAN   # noqa: E402

BUFS = ("FAT_DBUF", "FAT_MBUF", "FLD_TAB", "FLD_DESC")
CAS = ("CAL_BUF", "CAL_BUF2")


def disk_only():
    maps = {c: ram_map.Map(c, SPAN[0], SPAN[1] + 1) for c in ("basic", "disk")}
    def cover(m, pred):
        s = set()
        for a in m.addrs:
            if pred(m.byaddr[a]):
                s |= set(range(a, a + (m.width.get(a) or 1)))
        return s
    basic_all = cover(maps["basic"], lambda ns: True)
    disk_all = cover(maps["disk"], lambda ns: True)
    bufs = cover(maps["basic"], lambda ns: any(n.split("/")[0] in BUFS or n in BUFS for n in ns))
    cas = cover(maps["basic"], lambda ns: any(n in CAS for n in ns))
    basic_rest = cover(maps["basic"], lambda ns: not any(n in BUFS for n in ns))
    return sorted(((disk_all - basic_all) | bufs) - cas - (basic_rest - bufs))


def runs(addrs):
    out, cur = [], None
    for a in addrs:
        if cur and a == cur[1] + 1:
            cur[1] = a
        else:
            cur = [a, a]
            out.append(cur)
    return out


def syms(path):
    pairs = []
    for ln in open(path):
        m = re.match(r"([a-z_][a-z0-9_]*)\s+EQU\s+0?([0-9A-F]+)H", ln)
        if m:
            pairs.append((int(m.group(2), 16), m.group(1)))
    return sorted(pairs)


def where(pc, a8, tabs):
    prim = (a8 >> (2 * (pc >> 14))) & 3
    tab = tabs["main"] if prim == 0 else tabs["sub"] if prim == 3 else None
    if tab is None:
        return f"slot{prim}:{pc:04X}"
    i = bisect.bisect_right(tab, (pc, "~")) - 1
    if prim == 0 and (i < 0 or pc < 0x2765):
        return f"C-BIOS?:{pc:04X}"
    return f"{'main' if prim == 0 else 'sub'}:{tab[i][1]}+{pc - tab[i][0]}" if i >= 0 else f"{pc:04X}"


def run(lines, watch):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="dowrite_")
    os.close(fd)
    os.unlink(path)
    pro = [
        "set ::__seen [dict create]",
        f"set ::__wf {{{path}}}",
        "proc __wrec {} { set k \"[reg PC] [debug read ioports 0xA8] $::wp_last_address\"; "
        "if {![dict exists $::__seen $k]} { dict set ::__seen $k 1; "
        "set f [open $::__wf a]; puts $f \"$k [machine_info time]\"; close $f } }",
    ]
    pro += [f"debug set_watchpoint write_mem {{0x{lo:04X} 0x{hi:04X}}} {{}} {{__wrec}}"
            for lo, hi in watch]
    omsx_repl.run_cases(MACHINE, [("direct", ["NEW"] + lines)], batch=False,
                        reset=("", "SCREEN 0"), run_gap=12.0, prologue=tuple(pro))
    if not os.path.exists(path):
        return []
    rows = [l.split() for l in open(path) if l.strip()]
    os.unlink(path)
    return [(int(p), int(s), int(a), float(t)) for p, s, a, t in rows]


def main():
    dset = disk_only()
    watch = runs(dset)
    print(f"disk-only set: {len(dset)} B in {len(watch)} run(s): "
          + ", ".join(f"${lo:04X}..${hi:04X}" for lo, hi in watch[:12])
          + (" ..." if len(watch) > 12 else ""))
    tabs = {"main": syms(os.path.join(REPO, "build", "basic-reloc.sym")),
            "sub": syms(os.path.join(REPO, "build", "sub.sym"))}
    writers = {}
    for name, lines in CASES.items():
        got = run(lines, watch)
        for pc, a8, addr, t in got:
            w = where(pc, a8, tabs)
            e = writers.setdefault(w, {"cases": set(), "addrs": set(), "tmin": t})
            e["cases"].add(name)
            e["addrs"].add(addr)
            e["tmin"] = min(e["tmin"], t)
        print(f"{name:9s} {len(got):4d} distinct (PC, slot, address) writes", flush=True)
    print(f"\nWRITERS of the disk-only set on the diskless build: {len(writers)}")
    for w, e in sorted(writers.items(), key=lambda kv: kv[1]["tmin"]):
        rs = runs(sorted(e["addrs"]))
        print(f"  {w:34s} first t={e['tmin']:6.2f}s  {len(e['addrs']):4d} B "
              f"[{', '.join(f'${lo:04X}..${hi:04X}' for lo, hi in rs[:4])}{' ...' if len(rs) > 4 else ''}]"
              f"  cases: {'ALL' if len(e['cases']) == len(CASES) else ','.join(sorted(e['cases']))[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
