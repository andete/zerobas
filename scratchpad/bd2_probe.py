#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BD2FRAGILE, measure first (2026-10-31): why Boulder Dash II stops at line 10
on a zerobas build whose INT / FIX are identical in value and RAM.

The tape is RUN, never decoded. Registers and RAM ADDRESSES only: this script
samples PC / SP / CURLIN every 0.25 s and writes the RAM image ($8000-$FFFF) at a
few times to a PRIVATE directory (--dump, never inside the repo -- the bytes are
the game's). `--compare A B` then reports only WHICH addresses differ between two
such runs, never their contents.

    TAPECORPUS_DIR=... python3 -u scratchpad/bd2_probe.py run LABEL --dump DIR [--machine M]
    python3 -u scratchpad/bd2_probe.py compare DIR/LABEL_A DIR/LABEL_B
"""
import argparse, os, shutil, signal, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import omsx_preflight  # noqa: E402
import tapecorpus_run as TC  # noqa: E402

TITLE = "Boulder Dash II"
SAMPLE = (40.0, 200.0, 0.25)
DUMPS = (60, 90, 120, 150, 180)
ROMCALLS = (95.0, 150.0)
ROMREADS = (52.0, 150.0)


def run(machine, cas, outdir, watches=True):
    os.makedirs(outdir, exist_ok=True)
    samples = os.path.join(outdir, "samples.txt")
    lines = ["after time 0.3 {",
             "  trace remove execution cassetteplayer leave ::__zb_unarm",
             "  set autoruncassettes on",
             f"  cassetteplayer insert {{{cas}}}",
             omsx_preflight.AUTORUN_FIX,
             "}",
             "set throttle off",
             "proc __s {t} {",
             f"  set f [open {{{samples}}} a]",
             "  binary scan [debug read_block memory 0xF41C 2] su cl",
             "  puts $f \"$t [reg pc] [reg sp] $cl\"",
             "  close $f",
             "}",
             "proc __d {t} {",
             f"  set f [open [file join {{{outdir}}} ram_$t.bin] w]",
             "  fconfigure $f -translation binary",
             "  puts -nonewline $f [debug read_block memory 0x8000 0x8000]",
             "  close $f",
             "}"]
    if watches:
        lines += [
             # ROM addresses executed while the game's own stack is live (SP >= $FF00):
             # zerobas's addresses, counted -- the game's code is never read
             "proc __rc {} {",
             "  set p [reg pc]",
             "  if {[info exists ::rc($p)]} { incr ::rc($p) } else { set ::rc($p) 1 }",
             "}",
             f"after time {ROMCALLS[0]} {{ set ::__c [debug set_condition "
             "{[reg sp] >= 0xFF00 && [reg pc] < 0x8000} __rc] }",
             # ROM BYTES READ BY CODE IN RAM (the game reading the BASIC ROM as data):
             # the zerobas address read and the reader's PC, counted
             "proc __rr {} {",
             "  set k \"[reg pc] $::wp_last_address\"",
             "  if {[info exists ::rr($k)]} { incr ::rr($k) } else { set ::rr($k) 1 }",
             "}",
             f"after time {ROMREADS[0]} {{ set ::__w [debug set_watchpoint read_mem "
             "{0x0000 0x7FFF} {[reg pc] >= 0x8000} __rr] }",
             # POSITIVE CONTROL for the watch above: the same kind of watch on RAM
             # the game certainly reads. An empty romreads.txt means nothing unless
             # this count is non-zero (a watch that never ran looks like "no reads").
             "set ::ctl 0",
             f"after time {ROMREADS[0]} {{ set ::__wc [debug set_watchpoint read_mem "
             "{0xC000 0xCFFF} {[reg pc] >= 0x8000} {incr ::ctl}] }",
             f"after time {ROMREADS[1]} {{",
             "  debug remove_watchpoint $::__wc",
             f"  set f [open [file join {{{outdir}}} control.txt] w]",
             "  puts $f $::ctl",
             "  close $f",
             "}",
             f"after time {ROMREADS[1]} {{",
             "  debug remove_watchpoint $::__w",
             f"  set f [open [file join {{{outdir}}} romreads.txt] w]",
             "  foreach k [array names ::rr] { puts $f \"$k $::rr($k)\" }",
             "  close $f",
             "}",
             f"after time {ROMCALLS[1]} {{",
             "  debug remove_condition $::__c",
             f"  set f [open [file join {{{outdir}}} romcalls.txt] w]",
             "  foreach k [lsort -integer [array names ::rc]] { puts $f \"$k $::rc($k)\" }",
             "  close $f",
             "}"]
    if watches:
        # TAPE CALLS (D-TAPLEAD's method): every TAPION -- time, caller, and on its
        # return CF and LOWLIM ($FCA4, documented work area) -- and every TAPIN that
        # returns CF set; TAPIN calls counted per caller. Registers and RAM only.
        tl = os.path.join(outdir, "tapelog.txt")
        lines += [
            "proc __tl {s} {",
            f"  set f [open {{{tl}}} a]; puts $f $s; close $f",
            "}",
            "proc __caller {} { binary scan [debug read_block memory [reg sp] 2] su r; return $r }",
            "proc __tion {} {",
            "  set c [__caller]",
            "  __tl \"[format %.3f [machine_info time]] TAPION_IN caller=[format %04X $c] sp=[format %04X [reg sp]]\"",
            "  set ::tion_bp [debug set_bp $c {} __tion_ret]",
            "}",
            "proc __tion_ret {} {",
            "  debug remove_bp $::tion_bp",
            "  binary scan [debug read_block memory 0xFCA4 2] cucu lo ww",
            "  __tl \"[format %.3f [machine_info time]] TAPION_RET cf=[expr {[reg f] & 1}] lowlim=$lo winwid=$ww\"",
            "}",
            "proc __tin {} {",
            "  set c [__caller]",
            "  if {[info exists ::tin($c)]} { incr ::tin($c) } else {",
            "    set ::tin($c) 1",
            "    debug set_bp $c {} [list __tin_ret $c]",
            "  }",
            "}",
            "proc __tin_ret {c} {",
            "  if {[reg f] & 1} {",
            "    __tl \"[format %.3f [machine_info time]] TAPIN_CF caller=[format %04X $c] n=$::tin($c)\"",
            "  }",
            "}",
            "debug set_bp 0x00E1 {} __tion",
            "debug set_bp 0x00E4 {} __tin",
            f"after time {max(DUMPS)} {{ foreach c [array names ::tin] {{ __tl \"TAPIN_TOTAL caller=[format %04X $c] n=$::tin($c)\" }} }}",
        ]
    t = SAMPLE[0]
    while t <= SAMPLE[1]:
        lines.append(f"after time {t} {{ __s {t} }}")
        t += SAMPLE[2]
    for d in DUMPS:
        lines.append(f"after time {d} {{ __d {d} }}")
    lines.append(f"after time {max(DUMPS) + 0.5} {{ exit }}")
    td = tempfile.mkdtemp(prefix="bd2_")
    try:
        tcl = os.path.join(td, "s.tcl")
        open(tcl, "w").write("\n".join(lines) + "\n")
        cmd = [TC.OMSX, "-machine", machine,
               "-command", "set renderer none; set sound_driver null", "-script", tcl]
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + 60 + max(DUMPS) * 2
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    n = sum(1 for _ in open(samples)) if os.path.exists(samples) else 0
    print(f"{machine}: {n} samples, dumps {[d for d in DUMPS if os.path.exists(os.path.join(outdir, f'ram_{d}.bin'))]}")


def summary(d):
    """Per run: when CURLIN first changes after 10, the PC / SP ranges per CURLIN."""
    rows = [ln.split() for ln in open(os.path.join(d, "samples.txt"))]
    by = {}
    for t, pc, sp, cl in rows:
        by.setdefault(int(cl), []).append((float(t), int(pc), int(sp)))
    for cl, v in sorted(by.items(), key=lambda kv: kv[1][0][0]):
        ts = [x[0] for x in v]; pcs = [x[1] for x in v]; sps = [x[2] for x in v]
        print(f"  CURLIN {cl:5d}: T{min(ts):6.2f}-{max(ts):6.2f}  PC ${min(pcs):04X}-${max(pcs):04X}"
              f"  SP ${min(sps):04X}-${max(sps):04X}  ({len(v)} samples)")


def spans(addrs):
    out = []
    for a in addrs:
        if out and a == out[-1][1] + 1:
            out[-1][1] = a
        else:
            out.append([a, a])
    return out


def romcalls(d):
    p = os.path.join(d, "romcalls.txt")
    if not os.path.exists(p):
        return {}
    return {int(a): int(n) for a, n in (ln.split() for ln in open(p))}


def compare(a, b):
    for d in (a, b):
        print(d)
        summary(d)
    ra, rb = romcalls(a), romcalls(b)
    for name, r in (("A", ra), ("B", rb)):
        pages = {}
        for k, n in r.items():
            pages[k >> 8] = pages.get(k >> 8, 0) + n
        print(f"ROM executed, SP >= $FF00, T{ROMCALLS[0]:.0f}-{ROMCALLS[1]:.0f}, {name}: "
              f"{len(r)} addresses; per page " + " ".join(f"${p:02X}:{n}" for p, n in sorted(pages.items())))
    for t in DUMPS:
        fa, fb = (os.path.join(x, f"ram_{t}.bin") for x in (a, b))
        if not (os.path.exists(fa) and os.path.exists(fb)):
            continue
        ra, rb = open(fa, "rb").read(), open(fb, "rb").read()
        diff = [0x8000 + i for i in range(len(ra)) if ra[i] != rb[i]]
        sp = spans(diff)
        print(f"T{t}: {len(diff)} byte(s) differ in {len(sp)} span(s)")
        for lo, hi in sp[:24]:
            print(f"    ${lo:04X}-${hi:04X} ({hi - lo + 1})")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("label")
    r.add_argument("--dump", required=True)
    r.add_argument("--machine", default=TC.ZB)
    r.add_argument("--dir", default=os.environ.get("TAPECORPUS_DIR"))
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    a = ap.parse_args()
    if a.cmd == "compare":
        compare(a.a, a.b)
        return
    if os.path.realpath(a.dump).startswith(os.path.realpath(os.path.dirname(HERE))):
        raise SystemExit("REFUSING: --dump must be outside the repo (the bytes are the game's)")
    td = tempfile.mkdtemp(prefix="bd2cas_")
    try:
        cas = TC.unpack(os.path.join(a.dir, TITLE + ".zip"), td)
        # the watches count ROM addresses: zerobas's only. On the reference only
        # PC / SP / CURLIN are sampled (clean room: never trace its ROM).
        run(a.machine, cas, os.path.join(a.dump, a.label), watches=(a.machine == TC.ZB))
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    main()
