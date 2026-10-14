#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO slice 2, measure first: who writes the published trap cells, and how.

Slice 2 moves zerobas's trap state out of $E98A-$F37F (ZTRAP $EDD1, ZINTVAL /
ZINTCNT $EE07, TRAPPEND $EE1F ...) to the published cells for the same job:
TRPTBL $FC4C-$FC99 (26 x [status][handler:2]), INTVAL $FCA0, INTCNT $FCA2,
ONGSBF $FBD8. Two questions: (1) does C-BIOS write any of them itself (then
zerobas must cooperate, not fight it); (2) what does the VG-8020 write there
when traps run -- the entry layout and how INTCNT counts.

A write watchpoint over the three spans, armed after boot, records each distinct
(address, new value) -- work-area RAM contents, no ROM byte, no PC. Cases: idle;
ON INTERVAL=5 GOSUB with INTERVAL ON; ON KEY GOSUB + KEY(1) ON with F1 pressed
(keyboard row 6 bit 5).
Prediction (2026-10-14): C-BIOS writes none of them idle; on the VG-8020 the
INTERVAL case writes INTVAL = 5 and INTCNT counting down, TRPTBL's INTERVAL entry
(index 17) gets a status byte and the handler address, and ONGSBF goes nonzero;
zerobas writes none of these cells.
"""
import os, sys, tempfile
os.environ["ZEROBAS_REFCACHE"] = "0"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
SPANS = ((0xFBD8, 0xFBD8, "ONGSBF"), (0xFC4C, 0xFC99, "TRPTBL"), (0xFCA0, 0xFCA3, "INTVAL/INTCNT"))
CASES = {
    "idle": (["10 FOR I=1 TO 300:NEXT:END", "RUN"], None),
    "interval": (["10 ON INTERVAL=5 GOSUB 100:INTERVAL ON", "20 FOR I=1 TO 300:NEXT:END",
                  "100 RETURN", "RUN"], None),
    "key": (["10 ON KEY GOSUB 100:KEY(1) ON", "20 FOR I=1 TO 1500:NEXT:END",
             '100 PRINT "K";:RETURN', "RUN"], (6, 0x20)),
}


def run(machine, lines, hold):
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="trapcells_")
    os.close(fd)
    os.unlink(path)
    arms = " ; ".join(f"debug set_watchpoint write_mem {{0x{lo:04X} 0x{hi:04X}}} {{}} {{__tw}}"
                      for lo, hi, _ in SPANS)
    pro = (
        "set ::__tseen [dict create]", f"set ::__tf {{{path}}}", "set ::__tn 0",
        "proc __tw {} { set a $::wp_last_address; set v [debug read memory $a]; "
        "set k \"$a $v\"; if {[dict exists $::__tseen $k] || $::__tn > 400} return; "
        "dict set ::__tseen $k 1; incr ::__tn; "
        "set f [open $::__tf a]; puts $f \"[format %.2f [machine_info time]] $a $v\"; close $f }",
        f"after time 7.5 {{ {arms} }}",
    )
    kw = {"holds": [hold], "hold_secs": 3.0} if hold else {}
    omsx_repl.run_cases(machine, [("direct", ["NEW"] + lines)], batch=False,
                        reset=("", "SCREEN 0"), run_gap=15.0, prologue=pro, **kw)
    if not os.path.exists(path):
        return []
    out = [l.split() for l in open(path) if l.strip()]
    os.unlink(path)
    return [(float(t), int(a), int(v)) for t, a, v in out]


def name(a):
    for lo, hi, n in SPANS:
        if lo <= a <= hi:
            return n if lo == hi else f"{n}+{a - lo}"
    return f"${a:04X}"


def main():
    for case, (lines, hold) in CASES.items():
        for m in MACHINES:
            got = run(m, lines, hold)
            by = {}
            for t, a, v in got:
                by.setdefault(a, []).append(v)
            desc = "; ".join(f"{name(a)}:{','.join(str(x) for x in vs[:8])}{'...' if len(vs) > 8 else ''}"
                             for a, vs in sorted(by.items()))
            print(f"{case:9s} {m[:10]:10s} {len(got):3d} writes  {desc or '-'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
