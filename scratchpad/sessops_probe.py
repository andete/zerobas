#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW Q5 (Disk BASIC) + Q6 (drive B:) -- dosops_probe.py's instrument with another session (Joost 2026-11-28
"as much info as possible before ... any code"). Every FDC command logged by step; every track-0 READ's 512 B landing
window (a RAM write watch armed only during that read, 64-byte blocks: ADDRESSES ONLY, no byte, no PC).
    SESS=driveb python3 -u scratchpad/sessops_probe.py [MACHINE ...]   DIR A:, DIR B: (swap prompt, a key), DIR A: again
    SESS=basic2 ...   SAVE, FILES, NEW, FILES -- where the SAVE's writes land
    SESS=basic  python3 -u scratchpad/sessops_probe.py [MACHINE ...]   Disk BASIC (`BASIC` at A>): SAVE,
                                                                        NEW, LOAD, FILES
"""
import struct
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import disk_probe_dossession as D  # noqa: E402
import omsx_preflight  # noqa: E402

machines = sys.argv[1:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
SRC = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
SESS = os.environ.get("SESS", "driveb")
# STABLE: steps that end at a prompt that is not A> -- the driver then waits for a still screen only
if SESS == "driveb":
    STEPS = [("dira", "DIR MSX*.*"), ("dirb", "DIR B:MSX*.*"), ("keyb", ""), ("dira2", "DIR A:MSX*.*"), ("keya", "")]
    STABLE = ["dirb", "dira2"]
    D.SESSION = [("boot", None, 14), ("date", "", 5), ("mode", "MODE 40", 4)] + [(t, x, 3) for t, x in STEPS]
    FIRST = "mode"
else:
    STEPS = [("prog", '10 PRINT "HI"'), ("save", 'SAVE "T.BAS"'), ("new", "NEW"), ("load", 'LOAD "T.BAS"'),
             ("files", 'FILES "T*.*"')]
    if SESS == "basic2":   # where does the CF-3300's SAVE write land: in FILES (next disk op) or NEW?
        STEPS = [("prog", '10 PRINT "HI"'), ("save", 'SAVE "T.BAS"'), ("files", 'FILES "T*.*"'), ("new", "NEW"),
                 ("files2", 'FILES "T*.*"')]
    if SESS == "basic3":   # SAVE, then 20 s with no input: a timer flushes it inside "save"; a key-triggered one does not
        STEPS = [("prog", '10 PRINT "HI"'), ("save", 'SAVE "T.BAS"'), ("files", 'FILES "T*.*"')]
    STABLE = [t for t, _ in STEPS]
    # Disk BASIC from MSX-DOS's `BASIC`: a disk with MSXDOS.SYS and COMMAND.COM deleted host-side STILL came up at the
    # MSX-DOS date prompt on both machines (2026-11-28, unexplained, not chased) -- so boot the intact disk
    D.SESSION = [("boot", None, 14), ("date", "", 5), ("basic", "BASIC", 6)] + [
        (t, x, 20 if (SESS == "basic3" and t == "save") else 3) for t, x in STEPS]
    FIRST = "basic"


def host_delete(path, fname):
    """Delete fname from the image as DOS does (entry E5, clusters freed in every FAT copy)."""
    img = bytearray(open(path, "rb").read())
    bps, spc, res, nf, nroot, _t, _m, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    root = (res + nf * spf) * bps
    for i in range(nroot):
        o = root + 32 * i
        if img[o:o + 11].decode("latin1") == fname:
            c = struct.unpack_from("<H", img, o + 26)[0]
            img[o] = 0xE5
            while 2 <= c < 0xFF8:
                nxt = None
                for k in range(nf):
                    fo = (res + k * spf) * bps + c * 3 // 2
                    v = struct.unpack_from("<H", img, fo)[0]
                    if nxt is None:
                        nxt = v >> 4 if c & 1 else v & 0xFFF
                    struct.pack_into("<H", img, fo, v & 0x000F if c & 1 else v & 0xF000)
                c = nxt
            open(path, "wb").write(img)
            return
    raise SystemExit(f"{fname!r} not on the image")
CMD = ("set ::step none; set ::wid {}; set ::fcur {}; set ::b [dict create]\n"
       "proc __cmd {base} { if {!$::counting} return; "
       "if {$::wid ne {}} { debug remove_watchpoint $::wid; set ::wid {} }; "
       "if {$::fcur ne {}} { puts $::fl \"B $::fcur $::b\" }; set ::fcur {}; "
       "set c [expr {$::wp_last_value >> 4}]; set t [peek [expr {$base + 1}]]; set s [peek [expr {$base + 2}]]; "
       "puts $::fl \"C $::step $c $t $s\"; "
       "if {$c == 8 && $t == 0} { set ::fcur \"$::step:$s\"; set ::b [dict create]; "
       "set ::wid [debug set_watchpoint write_mem {0x8000 0xFFFF} {} { set a $::wp_last_address; "
       "if {$a < 0xBF80 || $a > 0xBFBF} { dict incr ::b [expr {$a >> 6}] } }] } }\n"
       "debug set_watchpoint write_mem {0x7F80 0x7FBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0x7FB8}}\n"
       "debug set_watchpoint write_mem {0xBF80 0xBFBF} {$::counting} {if {($::wp_last_address & 7) == 0} {__cmd 0xBFB8}}\n")
order = [FIRST] + [t for t, _ in STEPS]
for m in machines:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", SRC, dsk], check=True)
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "cmd.txt")
    tcl = D.tcl(out)
    tcl = tcl.replace("set throttle off", "set throttle off\nset ::counting 0\n"
                      f"set ::fl [open {{{fl}}} w]\n" + CMD, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    hook = f"  if {{$tag eq \"{FIRST}\"}} {{set ::counting 1}}\n"
    for k, v in zip(order, order[1:]):
        hook += f"  if {{$tag eq \"{k}\"}} {{set ::step {v}}}\n"
    hook += f"  if {{$tag eq \"{order[-1]}\"}} {{set ::counting 0; flush $::fl}}\n"
    tcl = tcl.replace(a, hook + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    b = "{boot datecmd basic basicmem}"
    assert tcl.count(b) == 1
    tcl = tcl.replace(b, "{boot datecmd basic basicmem " + " ".join(STABLE) + "}")
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=open(os.path.join(td, "err.txt"), "w"), stderr=subprocess.STDOUT, timeout=2400)
    print(f"== {m}   (log {td})")
    lines = open(fl).read().splitlines()
    if not any(ln.startswith("C ") for ln in lines):
        print("   NO FDC COMMANDS RECORDED -- instrument failed, not a finding")
    cnt, wins = {}, {}
    for ln in lines:
        p = ln.split()
        if p[0] == "C":
            step, c, t, s = p[1], int(p[2]), int(p[3]), int(p[4])
            if c not in (8, 10):
                continue
            k = ("FAT" if 2 <= s <= 7 else "t0") if t == 0 else "data"
            k += "r" if c == 8 else "w"
            cnt.setdefault(step, {}).setdefault(k, 0)
            cnt[step][k] += 1
        elif p[0] == "B":
            step, sec = p[1].split(":")
            blk = {int(p[i]): int(p[i + 1]) for i in range(2, len(p) - 1, 2)}
            full = sorted(k for k, v in blk.items() if v >= 48)
            # one window = a run of full blocks; its start from the partial block before it
            runs, st, prev = [], None, None
            for k in full:
                if st is None or k != prev + 1:
                    if st is not None:
                        runs.append((st, prev))
                    st = k
                prev = k
            if st is not None:
                runs.append((st, prev))
            desc = [f"${a * 64 - blk.get(a - 1, 0):04X}" for a, b in runs if b - a >= 5] or ["none"]
            wins.setdefault(step, {}).setdefault(f"s{sec}->" + ",".join(desc), 0)
            wins[step][f"s{sec}->" + ",".join(desc)] += 1
    for step in order[1:]:
        print(f"   {step:5s} " + "  ".join(f"{k}={v}" for k, v in sorted(cnt.get(step, {}).items())))
        if step in wins:
            print("         track-0 reads land: " + "  ".join(f"{k} x{v}" for k, v in sorted(wins[step].items())))
    snaps = {ln.split()[0]: ln for ln in open(out).read().splitlines()}
    if order[-1] in snaps:
        p = snaps[order[-1]].split()
        wd = int(p[1][2:])
        b = bytes.fromhex(p[3])
        rows = [b[k * wd:(k + 1) * wd].decode("latin1").rstrip() for k in range(24)]
        print("   final screen: " + " / ".join(r for r in rows if r.strip())[-300:])
