#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BUFINCTL: WHAT EACH LINE-EDITING KEY DOES TO A BDOS $0A (BUFIN) LINE UNDER MSX-DOS -- CF-3300 vs zerobas.

BUFINX.COM (probes/disk/bufinx.asm) runs from AUTOEXEC.BAT and calls BUFIN with a 10-character buffer; it
stores its exit registers at $0400, the buffer follows at $0408, and it loops. At 30 s the harness types `AB`,
the key (CTRL held in the keyboard matrix, row 6 bit 1; ESC is row 7 bit 2), `CD` and Enter, with openMSX's
printer logger plugged; at 45 s it reads RAM $0400-$041F -- the program's own block -- and the printer log.

Each row is one of
    RETURNED <count> <chars>   BUFIN came back: the line it stored
    ABANDONED                  the program was left (Ctrl-C): COMMAND.COM reloaded over its block
    HUNG                       the block is still the program's untouched $EE fill
plus what reached the printer. A row is SAME when both machines read alike.

Measured 2026-11-26 (scratchpad/AE_bufinctl_buf.out, _buf2.out, _buf3.out): Ctrl-X drops itself and the next
key; Ctrl-E / Ctrl-S are stored; Ctrl-R / Ctrl-N are dropped; Ctrl-U / ESC erase the line; Ctrl-P turns the
printer echo on (the rest of the line, `CD` CR, reaches the printer); Ctrl-C abandons the program.

Clean room: typed keys in; the program's RAM block and the printer port's bytes out. Microsoft's DOS files run
as they are. Exit 0 all SAME; 1 a divergence; 2 no reading.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import build_bufinx_disk as B  # noqa: E402
import omsx_preflight  # noqa: E402
import probe_refcache  # noqa: E402
import probe_tmp  # noqa: E402

OMSX = os.environ.get("OPENMSX", shutil.which("openmsx") or "/opt/homebrew/bin/openmsx")
DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
MACHINES = (("CF", "National_CF-3300"), ("ZB", os.environ.get("BUFINCTL_ZB_MACHINE")
                                         or "C-BIOS_MSX1_EU_REPACK_DISK"))
# XX is Ctrl-X twice: the second ^X is the key the first one drops
KEYS = ("X", "XX", "E", "S", "R", "N", "U", "ESC", "H", "P", "C")


def key_tcl(k, t):
    if k == "ESC":
        return (f"after time {t:.2f} {{keymatrixdown 7 4}}\n"
                f"after time {t + 0.3:.2f} {{keymatrixup 7 4}}\n", t + 0.8)
    return (f"after time {t:.2f} {{keymatrixdown 6 2}}\n"
            f"after time {t + 0.1:.2f} {{type {k.lower()}}}\n"
            f"after time {t + 0.5:.2f} {{keymatrixup 6 2}}\n", t + 1.0)


def run(machine, dsk, key, td):
    out = os.path.join(td, f"mem_{machine}_{key}.txt")
    prn = os.path.join(td, f"prn_{machine}_{key}.txt")
    t = 31.0
    tcl = ["set throttle off", f"set printerlogfilename {{{prn}}}", "plug printerport logger",
           'after time 30.00 {type "AB"}']
    for k in (["X", "X"] if key == "XX" else [key]):
        s, t = key_tcl(k, t)
        tcl.append(s)
    tcl.append(f'after time {t:.2f} {{type "CD\\r"}}')
    tcl.append(f"after time 45 {{ set f [open {{{out}}} w]; binary scan [debug read_block memory 0x0400 32] H* m; "
               f'puts $f $m; close $f; exit }}')
    script = os.path.join(td, f"s_{machine}_{key}.tcl")
    open(script, "w").write("\n".join(tcl) + "\n")
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-command",
           "set renderer none; set sound_driver null", "-script", script]

    def spawn():
        p = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        try:
            p.wait(timeout=180)
            return "OK"
        except subprocess.TimeoutExpired:
            p.kill()
            return "TIMEOUT"
    probe_refcache.cached_run(cmd, [out, prn], spawn, media=[dsk], ok=lambda v: v != "TIMEOUT",
                              optional=(prn,))
    if not os.path.exists(out) or not open(out).read().strip():
        return None
    mem = bytes.fromhex(open(out).read().strip())
    return reading(mem), (open(prn, "rb").read() if os.path.exists(prn) else b"")


def reading(mem):
    if mem == b"\xEE" * 8 + bytes([10]) + b"\xEE" * 23:
        return "HUNG"
    buf = mem[8:]
    n = buf[1]
    if buf[0] == 10 and n <= 10 and buf[2 + n] == 0x0D:
        return f"RETURNED {n} {buf[2:2 + n].hex(' ')}"
    return "ABANDONED"


def main():
    if not os.path.isfile(DOS):
        print(f"INSTRUMENT FAULT: no MSX-DOS 1 disk at {DOS}")
        return 2
    td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
    try:
        base = os.path.join(td, "bufinx.dsk")
        B.build(DOS, base, td)
        bad, blind = [], []
        for key in KEYS:
            got = {}
            for side, m in MACHINES:
                dsk = os.path.join(td, f"{side}_{key}.dsk")
                shutil.copyfile(base, dsk)
                got[side] = run(m, dsk, key, td)
            if None in got.values():
                blind.append(key)
                print(f"ROW {key:4s} NO-READING {[s for s, v in got.items() if v is None]}")
                continue
            v = "SAME" if got["CF"] == got["ZB"] else "DIVERGES"
            if v != "SAME":
                bad.append(key)
            print(f"ROW {key:4s} {v:8s} CF=[{got['CF'][0]}; printer {got['CF'][1]!r}]"
                  + ("" if v == "SAME" else f"  ZB=[{got['ZB'][0]}; printer {got['ZB'][1]!r}]"))
            sys.stdout.flush()
    finally:
        shutil.rmtree(td, ignore_errors=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: BUFIN's control keys under MSX-DOS"
          + (f" -- diverging: {', '.join(bad)}" if bad else f" ({len(KEYS)} rows SAME)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
