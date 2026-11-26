#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKCONTRACT gap 12: WHAT VERIFY ($2E) DOES TO A WRITE -- the FDC's command stream, VERIFY OFF and ON.

docs/disk/port-readiness.md gap 4. VERIFY is a BDOS switch; what it changes (if anything) is what the disk ROM sends
the controller when it writes. Both machines boot the reference DOS disk (dossession's: MSX-DOS 1.03 / COMMAND 1.08,
HELLO.TXT added) and type, at A>:

    VERIFY OFF / COPY HELLO.TXT V1.TXT / VERIFY ON / COPY HELLO.TXT V2.TXT

A write watchpoint on the WD2793 command register ($7FB8, memory-mapped on both machines -- an I/O register, the
permitted side of the clean room; disk_probe_wcache.py's instrument) logs every command with the step it fell in.
Each COPY's stream is reduced to its READ / WRITE sequence (a back-to-back repeat of the same command on the same
track and sector is a driver RETRY and dropped, as wcache does).

Rows:
  copy-off   the command kinds of the COPY under VERIFY OFF -- reported, both machines (not compared: the two disk
             ROMs' read caching differs by design, D-WCACHE)
  copy-on    the same under VERIFY ON -- reported
  effect     what VERIFY ON ADDS: the number of READs issued after a WRITE that the OFF stream did not have, as
             `+R n` -- COMPARED: SAME when both machines add the same verify reads (or both add none)

Clean room: typed keys in; the FDC command register's written values and the cursor/screen out. Microsoft's DOS
files run as they are.
Exit 0 SAME; 1 DIVERGES; 2 no reading.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import disk_probe_dossession as DS  # noqa: E402  -- the session harness, reused
import probe_tmp  # noqa: E402

DS.SESSION = [
    ("boot", None, 14),
    ("date", "", 5),
    ("voff", "VERIFY OFF", 4),
    ("copyoff", "COPY HELLO.TXT V1.TXT", 8),
    ("von", "VERIFY ON", 4),
    ("copyon", "COPY HELLO.TXT V2.TXT", 8),
]
MACHINES = (("CF", "National_CF-3300"), ("ZB", os.environ.get("DOSSESSION_ZB_MACHINE")
                                         or "C-BIOS_MSX1_EU_REPACK_DISK"))


def kind(b):
    return "R" if (b & 0xE0) == 0x80 else "W" if (b & 0xE0) == 0xA0 else None


def streams(log):
    """{step: [R/W, ...]} with back-to-back retries dropped"""
    out, prev = collections.defaultdict(list), None
    for ln in open(log).read().split():
        tag, cmd, trk, sec = ln.split(":")
        k = kind(int(cmd, 16))
        if k is None:
            continue
        key = (tag, cmd, trk, sec)
        if key == prev:
            continue                                  # a retry
        prev = key
        out[tag].append(k)
    return out


def verify_reads(off, on):
    """the READs VERIFY ON added to the same COPY: R(on) - R(off). (A first cut counted W->R adjacencies and read
    the CF-3300 as +5: its read-back follows a multi-sector write as a run, WWW then RRR.)"""
    return on.count("R") - off.count("R")


# 🔴 THE KNOWN DIFFERENCE, PINNED TO ITS EXACT VALUES (D-VERIFYREAD, measured 2026-11-26, scratchpad/AE_verify1.out):
# the CF-3300 READS BACK every sector a write sends under VERIFY ON (9 writes, 9 extra reads); zerobas ignores the
# switch (+0). The disk ROM has no room to fix it today (docs/disk/port-readiness.md row 5). A change on EITHER side
# turns the row red: the reference moving means the instrument did, and zerobas matching means the pin must go.
KNOWN = {"CF": 9, "ZB": 0}


def run(machine):
    log = probe_tmp.tmp(f"verify_fdc_{machine}.txt")
    if os.path.exists(log):
        os.unlink(log)
    orig = DS.tcl

    def tcl(out):
        watch = "\n".join([
            f"set __cf [open {{{log}}} w]",
            "proc __fdc {} { if {[info exists ::cur]} { puts $::__cf [format {%s:%02X:%d:%d} [lindex $::cur 0] "
            "$::wp_last_value [debug read memory 0x7FB9] [debug read memory 0x7FBA]]; flush $::__cf } }",
            "debug set_watchpoint write_mem 0x7FB8 {} { __fdc }", ""])
        return watch + orig(out)
    DS.tcl = tcl
    try:
        lines, _ = DS.run(machine)
    finally:
        DS.tcl = orig
    screens = DS.render(lines)
    return (streams(log) if os.path.exists(log) else None), screens


def main():
    if not os.path.isfile(DS.DOS):
        print(f"INSTRUMENT FAULT: no MSX-DOS 1 system disk at {DS.DOS}")
        return 2
    got = {side: run(m) for side, m in MACHINES}
    blind = [side for side, (s, scr) in got.items()
             if not s or not s.get("copyoff") or not s.get("copyon")
             or "W" not in s["copyoff"] or "W" not in s["copyon"]]
    for side, (s, _) in got.items():
        for tag in ("copyoff", "copyon"):
            print(f"ROW {tag:8s} {side}: {''.join((s or {}).get(tag, [])) or '<none>'}")
    if blind:
        print(f"\nINSTRUMENT FAULT: no WRITE command logged in a COPY on {', '.join(blind)} -- nothing measured")
        return 2
    eff = {side: verify_reads(s["copyoff"], s["copyon"]) for side, (s, _) in got.items()}
    writes = got["CF"][0]["copyon"].count("W")
    if eff["CF"] == eff["ZB"]:
        v = "SAME" + (" -- 🔴 D-VERIFYREAD IS FIXED: drop the KNOWN pin" if KNOWN else "")
    elif eff == KNOWN:
        v = f"KNOWN DIFFERENCE (D-VERIFYREAD): the CF-3300 reads back each of its {writes} written sectors"
    else:
        v = "DIVERGES"
    ok = v.startswith("KNOWN") or (v == "SAME" and not KNOWN)
    print(f"ROW effect   CF=[+R {eff['CF']}] ZB=[+R {eff['ZB']}] {v}")
    print(f"\n{'PASS' if ok else 'FAIL'}: what VERIFY ON adds to a write")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
