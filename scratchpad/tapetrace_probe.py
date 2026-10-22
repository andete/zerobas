#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TAPELOAD triage: autorun a tape (openMSX's own `autoruncassettes`), then once a
second read the published work-area pointers and walk the program's line links --
on the VG-8020 and on zerobas. Black box: RAM cells and the link chain the BASIC
program itself carries, never a ROM byte and never the tape's machine code.

Per tick: CURLIN, SP, TXTTAB / VARTAB / ARYTAB / STREND / FRETOP / MEMSIZ / STKTOP,
the number of linked lines, the last line number, the address of the end link, and
whether the end link sits below VARTAB-2 (a chain that ENDS EARLY -- lines lost).

    TAPECORPUS_DIR=... python3 -u scratchpad/tapetrace_probe.py TITLE \
        [--start 40] [--end 130] [--machines ref,zb] [--keys 'T:text' ...]
--keys types `text` (+ RETURN) at second T, e.g. '60: ' for a space at T60.
--watch LO-HI logs every write to LO..HI with the PC and stack -- on zerobas ONLY:
its own code may be traced; the reference's may not (clean room).
"""
import argparse, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import omsx_preflight  # noqa: E402  (no settings saved, autorun un-armed)
import tapecorpus_run as T  # noqa: E402

CELLS = (("TXTTAB", 0xF676), ("VARTAB", 0xF6C2), ("ARYTAB", 0xF6C4), ("STREND", 0xF6C6),
         ("FRETOP", 0xF69B), ("MEMSIZ", 0xF672), ("STKTOP", 0xF674))


def tcl(cas, out, start, end, keys, watch=None):
    w = lambda a: f"[expr {{[debug read memory {a:#x}] + 256*[debug read memory {a + 1:#x}]}}]"
    fmt = " ".join(f"{n}=%04X" for n, _ in CELLS)
    vals = " ".join(w(a) for _, a in CELLS)
    lines = ["after time 0.3 {",
             "  trace remove execution cassetteplayer leave ::__zb_unarm",
             "  set autoruncassettes on",
             f"  cassetteplayer insert {{{cas}}}",
             "}",
             "set throttle off",
             "proc __w {a} { expr {[debug read memory [expr {$a & 0xFFFF}]] + 256*[debug read memory [expr {($a+1) & 0xFFFF}]]} }",
             "proc __chain {} {",
             "  set p [__w 0xF676]; set n 0; set last -1",
             "  while {$n < 4000} {",
             "    set nx [__w $p]",
             "    if {$nx == 0} break",
             "    set last [__w [expr {$p+2}]]; incr n",
             "    if {$nx <= $p || $nx > [__w 0xF6C2]} { return \"$n $last [format %04X $p] WILD\" }",
             "    set p $nx",
             "  }",
             "  return \"$n $last [format %04X $p] ok\"",
             "}",
             "proc __h {tag} {",
             f"  set f [open {{{out}}} a]",
             "  set c [__chain]",
             f"  set s [format \"{fmt}\" {vals}]",
             "  set vt [__w 0xF6C2]",
             "  scan [lindex $c 2] %x endp",
             "  set early [expr {$endp + 3 < $vt ? \"EARLY\" : \"\"}]",
             "  puts $f [format \"%s CURLIN=%5d SP=%04X %s lines=%s last=%s end=%s %s %s\" $tag"
             " [__w 0xF41C] [reg sp] $s [lindex $c 0] [lindex $c 1] [lindex $c 2] [lindex $c 3] $early]",
             "  close $f",
             "}",
             "proc __tick {t} {",
             f"  if {{[catch {{__h T$t}} e]}} {{ set f [open {{{out}}} a]; puts $f \"T$t ERR $e\"; close $f }}",
             "  after time 1 [list __tick [expr {$t+1}]]",
             "}",
             f"after time {start} {{ __tick {start} }}"]
    for t, text in keys:
        esc = text
        for ch in '\\"$[]':
            esc = esc.replace(ch, "\\" + ch)
        lines.append(f'after time {t} {{ type "{esc}\\r" }}')
    if watch:
        # zerobas ONLY (its own code): who writes the watched bytes -- PC, CURLIN, SP,
        # the value, and the top of the stack (return addresses into zerobas)
        lines += ["set __wn 0",
                  "proc __wp {} {",
                  "  global __wn; incr __wn; if {$__wn > 40} return",
                  f"  set f [open {{{out}}} a]",
                  "  set sp [reg sp]; set st {}",
                  "  for {set i 0} {$i < 8} {incr i} { lappend st [format %04X [__w [expr {$sp + 2*$i}]]] }",
                  "  puts $f [format \"WRITE %04X=%02X PC=%04X CURLIN=%d SP=%04X stack=%s\" "
                  "$::wp_last_address $::wp_last_value [reg pc] [__w 0xF41C] $sp $st]",
                  "  close $f",
                  "}",
                  f"after time {start} {{ debug set_watchpoint write_mem {{{watch[0]:#x} {watch[1]:#x}}} {{}} __wp }}"]
    lines.append(f"after time {end} {{ exit }}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title")
    ap.add_argument("--start", type=float, default=40)
    ap.add_argument("--end", type=float, default=130)
    ap.add_argument("--machines", default="ref,zb")
    ap.add_argument("--keys", nargs="*", default=[])
    ap.add_argument("--watch", help="LO-HI (hex): log writes there; zerobas only")
    a = ap.parse_args()
    keys = [(float(k.split(":", 1)[0]), k.split(":", 1)[1]) for k in a.keys]
    td = tempfile.mkdtemp(prefix="ttrace_")
    try:
        cas = T.unpack(os.path.join(os.environ["TAPECORPUS_DIR"], a.title + ".zip"), td)
        for m in a.machines.split(","):
            machine = T.REF if m == "ref" else T.ZB
            out = os.path.join(td, m + ".txt")
            s = os.path.join(td, m + ".tcl")
            w = None
            if a.watch and m == "zb":
                w = [int(x, 16) for x in a.watch.split("-")]
            open(s, "w").write(tcl(cas, out, int(a.start), a.end, keys, w))
            subprocess.run(omsx_preflight.guarded([T.OMSX, "-machine", machine, "-command",
                            "set renderer none; set sound_driver null", "-script", s]),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=120 + 3 * a.end)
            print(f"### {m} ({machine})")
            print(open(out).read().rstrip() if os.path.exists(out) else "<NO OUTPUT>")
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    main()
