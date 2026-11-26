#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BUFINCTL: WHAT EACH LINE-EDITING KEY LEAVES IN THE BDOS $0A (BUFIN) BUFFER, CF-3300 vs zerobas.

The on-screen behaviour is measured (scratchpad/AE_bufinctl_keys.out); this reads the BUFFER the
call returns. BUFINX.COM (probes/disk/bufinx.asm) runs from AUTOEXEC.BAT and calls BUFIN with a
10-character buffer at $0404; it stores its exit registers at $0400 and loops. At 30 s the harness
types `AB`, the key (CTRL held in the keyboard matrix, row 6 bit 1; ESC = row 7 bit 2), `CD`, Enter.
At 45 s it reads RAM $0400-$041F (the program's own block) and the screen's text rows.

Clean room: typed keys in; the program's RAM block and the screen out. Microsoft's DOS files run as
they are.
"""
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import build_bufinx_disk as B  # noqa: E402
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
MACHINES = (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))
KEYS = sys.argv[1:] or ["X", "E", "R", "N", "S", "U", "ESC", "H", "P", "C", "XX"]


def key_tcl(k, t):
    """Tcl that presses one key at emulated time t; returns (tcl, next t)."""
    if k == "ESC":
        return (f"after time {t:.2f} {{keymatrixdown 7 4}}\n"
                f"after time {t + 0.3:.2f} {{keymatrixup 7 4}}\n", t + 0.8)
    return (f"after time {t:.2f} {{keymatrixdown 6 2}}\n"
            f"after time {t + 0.1:.2f} {{type {k.lower()}}}\n"
            f"after time {t + 0.5:.2f} {{keymatrixup 6 2}}\n", t + 1.0)


def run(machine, dsk, key):
    out = probe_tmp.tmp(f"bufinctl_{machine}_{key}.txt")
    if os.path.exists(out):
        os.unlink(out)
    t = 30.0
    prn = probe_tmp.tmp(f"bufinctl_prn_{machine}_{key}.txt")
    if os.path.exists(prn):
        os.unlink(prn)
    # the printer plugged (openMSX's logger) on every run: Ctrl-P with NO printer aborted the
    # CF-3300's program (first run, scratchpad/AE_bufinctl_buf.out)
    tcl = ["set throttle off", f"set printerlogfilename {{{prn}}}", "plug printerport logger",
           f'after time {t:.2f} {{type "AB"}}']
    t += 1.0
    for k in ([key[0], key[1]] if key == "XX" else [key]):     # XX: Ctrl-X twice
        s, t = key_tcl(k, t)
        tcl.append(s)
    tcl.append(f'after time {t:.2f} {{type "CD\\r"}}')
    tcl.append(f"""after time 45 {{
  set f [open {{{out}}} w]
  binary scan [debug read_block memory 0x0400 32] H* m
  puts $f "MEM $m"
  binary scan [debug read_block VRAM 0 960] H* v
  puts $f "VRAM $v"
  close $f
  exit
}}""")
    script = tempfile.mktemp(suffix=".tcl", dir=probe_tmp.ROOT)
    open(script, "w").write("\n".join(tcl) + "\n")
    cmd = ["openmsx", "-machine", machine, "-diska", dsk, "-command",
           "set renderer none; set sound_driver null", "-script", script]
    subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=180)
    os.unlink(script)
    if not os.path.exists(out):
        return None
    d = dict(l.split(" ", 1) for l in open(out).read().splitlines())
    mem = bytes.fromhex(d["MEM"])
    v = bytes.fromhex(d["VRAM"])
    rows = [v[i:i + 40].decode("latin1") for i in range(0, 960, 40)]
    rows = [r.rstrip() for r in rows if r.strip()]
    return mem, (open(prn, "rb").read() if os.path.exists(prn) else None)


def show(mem):
    regs, buf = mem[:8], mem[8:]
    called_back = regs != b"\xEE" * 8
    n = buf[1]
    chars = buf[2:2 + n] if n <= 10 else buf[2:12]
    return (f"returned={'yes' if called_back else 'NO'} count={n:#04x} "
            f"chars={chars.hex(' ')} ({''.join(chr(c) if 32 <= c < 127 else '.' for c in chars)})")


def main():
    with tempfile.TemporaryDirectory(dir=probe_tmp.ROOT) as td:
        dsk = os.path.join(td, "bufinx.dsk")
        B.build(DOS, dsk, td)
        for key in KEYS:
            for side, m in MACHINES:
                c = os.path.join(td, f"{side}.dsk")
                with open(dsk, "rb") as a, open(c, "wb") as b:
                    b.write(a.read())
                got = run(m, c, key)
                if got is None:
                    print(f"{key:4s} {side}: NO READING")
                    continue
                mem, prn = got
                print(f"{key:4s} {side}: {show(mem)}  printer={prn!r}")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
