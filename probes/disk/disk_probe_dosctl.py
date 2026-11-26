#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKCONTRACT gap 5: THE CONSOLE'S CONTROL KEYS AT A> -- Ctrl-C and Ctrl-P, against the CF-3300.

docs/disk/port-readiness.md gap 4. Under MSX-DOS 1 the console's line input (BUFIN) and its output belong to the disk
ROM's BDOS, so what Ctrl-C and Ctrl-P do at the prompt is its contract. Both machines boot the reference DOS disk
(dossession's harness, HELLO.TXT added) with the printer plugged (openMSX's printer logger), and at A>:

    ctrlc    `DIR` typed WITHOUT Enter, then Ctrl-C: the line is abandoned (the screen after)
    ctrlp    Ctrl-P: printer echo on
    dirp     `DIR` -- on the screen, and (with echo on) on the printer too
    ctrlp2   Ctrl-P again: echo off
    type2    `TYPE HELLO.TXT` -- the screen only

Rows: each step's screen (SAME / DIVERGES), and the printer log at the end (SAME / DIVERGES).
A control key is typed by holding CTRL in the keyboard matrix (row 6, bit 1) around the letter's `type`.
Ctrl-S (pause) is not here: it races the output it pauses, so a screen snapshot cannot score it.

Clean room: typed keys in; the screen, the cursor and the printer port's bytes out. Microsoft's DOS files run as
they are. Exit 0 all SAME; 1 a divergence; 2 no reading.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import disk_probe_dossession as DS  # noqa: E402  -- the session harness, reused
import probe_tmp  # noqa: E402

# `~TEXT` types TEXT with no Enter and does not wait for the prompt; `^X` is Ctrl-X
DS.SESSION = [
    ("boot", None, 14),
    ("date", "", 5),
    ("mode", "MODE 40", 4),             # dossession's reason: both machines at one width before anything scored
    ("partial", "~DIR", 2),
    ("ctrlc", "^C", 4),
    ("ctrlp", "^P", 3),
    ("dirp", "DIR", 8),
    ("ctrlp2", "^P", 3),
    ("type2", "TYPE HELLO.TXT", 5),
]
NOPROMPT = {"partial", "ctrlp", "ctrlp2"}     # steps after which the screen need not show a fresh A>
MACHINES = (("CF", "National_CF-3300"), ("ZB", os.environ.get("DOSSESSION_ZB_MACHINE")
                                         or "C-BIOS_MSX1_EU_REPACK_DISK"))
# D-BUFINCTL (measured 2026-11-26, scratchpad/AE_dosctl2.out): zerobas's line input stored Ctrl-C and Ctrl-P as
# characters; FIXED the same day (scratchpad/AE_bufctl_dosctl4.out) -- every row SAME, the four pins dropped.
# (A pin set here again would be a new KNOWN difference: its rows must DIVERGE.)
KNOWN = set()
TYPEKEYS = "\n".join([
    "proc typekeys {s} {",
    "  if {[string index $s 0] eq \"^\"} {",
    "    keymatrixdown 6 2",
    "    after time 0.1 [list type [string tolower [string index $s 1]]]",
    "    after time 0.5 {keymatrixup 6 2}",
    "  } elseif {[string index $s 0] eq \"~\"} {",
    "    type [string range $s 1 end]",
    "  } else { type \"$s\\r\" } }", ""])


def run(machine):
    log = probe_tmp.tmp(f"dosctl_prn_{machine}.txt")
    if os.path.exists(log):
        os.unlink(log)
    orig = DS.tcl

    def tcl(out):
        t = orig(out)
        a = 'if {$tag ne "boot"} { type "$typed\\r" }'
        if t.count(a) != 1:
            raise SystemExit("dosctl: dossession's Tcl changed -- the type line was not found once")
        t = t.replace(a, 'if {$tag ne "boot"} { typekeys $typed }')
        b = "$tag in {boot datecmd basic basicmem}"
        if t.count(b) != 1:
            raise SystemExit("dosctl: dossession's Tcl changed -- the no-prompt test was not found once")
        t = t.replace(b, "$tag in {boot " + " ".join(sorted(NOPROMPT)) + "}")
        return (f"set printerlogfilename {{{log}}}\nplug printerport logger\n" + TYPEKEYS + t)
    DS.tcl = tcl
    try:
        lines, _ = DS.run(machine)
    finally:
        DS.tcl = orig
    prn = open(log, "rb").read() if os.path.exists(log) else None
    return DS.render(lines), prn


def main():
    if not os.path.isfile(DS.DOS):
        print(f"INSTRUMENT FAULT: no MSX-DOS 1 system disk at {DS.DOS}")
        return 2
    got = {side: run(m) for side, m in MACHINES}
    bad, blind = [], []
    for tag, typed, _ in DS.SESSION[3:]:
        cf, zb = got["CF"][0].get(tag), got["ZB"][0].get(tag)
        if cf is None or zb is None:
            v = "NO-READING"
            blind.append(tag)
        else:
            v = "SAME" if cf == zb else "DIVERGES"
        if tag in KNOWN:
            v = "KNOWN DIFFERENCE (D-BUFINCTL)" if v == "DIVERGES" else (
                "SAME -- 🔴 D-BUFINCTL row FIXED: drop it from KNOWN" if v == "SAME" else v)
            if v.startswith("SAME"):
                bad.append(tag)
        print(f"ROW {tag:8s} {typed!r:22s} {v}")
        if v == "DIVERGES":
            bad.append(tag)
            for side, s in (("CF", cf), ("ZB", zb)):
                for r in [r for r in s[1] if r.strip()][-8:]:
                    print(f"   {side} |{r}")
        elif v == "SAME":
            for r in [r for r in cf[1] if r.strip()][-2:]:
                print(f"   == {r}")
    pc, pz = got["CF"][1], got["ZB"][1]
    if pc is None or pz is None or not pc.strip():
        print("ROW printer  NO-READING (no printer log, or the CF-3300 printed nothing: echo never came on)")
        blind.append("printer")
    else:
        v = "SAME" if pc == pz else "DIVERGES"
        if "printer" in KNOWN:
            v = "KNOWN DIFFERENCE (D-BUFINCTL)" if v == "DIVERGES" else "SAME -- 🔴 FIXED: drop it from KNOWN"
            if v.startswith("SAME"):
                bad.append("printer")
        print(f"ROW printer  {len(pc)} B / {len(pz)} B  {v}")
        if v == "DIVERGES":
            bad.append("printer")
            print(f"   CF {pc!r}\n   ZB {pz!r}")
        else:
            print(f"   == {pc[:120]!r}")
    if blind:
        print(f"\nINSTRUMENT FAULT: no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: Ctrl-C / Ctrl-P at A> ({('every other row SAME, ' + str(len(KNOWN)) + ' known differences pinned') if not bad else ', '.join(bad)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
