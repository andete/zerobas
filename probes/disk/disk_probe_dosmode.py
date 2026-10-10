# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DOSMODE40 (gate: dosmode-acceptance): `MODE 40` / `MODE 32` at MSX-DOS's A>
switch the screen as on the CF-3300. Found 2026-10-09 by D-CALLSYSTEM's probe:
zerobas stored the width and nothing else -- its page-0 CALSLT jumped to the
BIOS address (INITXT, $006C) in DOS's RAM instead of calling the BIOS.

Boots the BDOS gates' MSX-DOS 1 disk (a private copy), answers the date prompt,
then types each step and SNAPSHOTS after it: the documented work-area cells
SCRMOD, LINL40, LINL32, LINLEN, CRTCNT, CSRY, CSRX, CNSDFG and the text screen
(the mode's own name table: SCREEN 0 40 cols at TXTNAM, SCREEN 1 32 at T32NAM).

Clean-room: typed keys in; work-area RAM and VRAM out.
Each snapshot is a row: `ROW <step> CF=[cells | screen] ZB=[...] <SAME|DIVERGES>`.
Exit 0 all agree; 1 a divergence; 2 no reading / no DOS disk.
usage: disk_probe_dosmode.py [DOSDISK]
"""
import os, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
DOS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
STEPS = [("boot", None, 16), ("date", "", 5), ("mode40", "MODE 40", 5), ("dir", "DIR MSXDOS.SYS", 6),
         ("mode32", "MODE 32", 5), ("dir32", "DIR MSXDOS.SYS", 6)]


def tcl(out):
    b = ["set throttle off",
         "proc rd {a} { debug read memory $a }",
         "proc rd16 {a} { expr {[rd $a] + 256*[rd [expr {$a+1}]]} }",
         "proc snap {tag} {",
         "  set m [rd 0xFCAF]",
         "  if {$m == 0} { set base [rd16 0xF3B3]; set w 40 } else { set base [rd16 0xF3BD]; set w 32 }",
         "  binary scan [debug read_block VRAM $base [expr {$w*24}]] H* h",
         f"  set f [open {{{out}}} a]",
         "  puts $f \"$tag SCRMOD=$m LINL40=[rd 0xF3AE] LINL32=[rd 0xF3AF] LINLEN=[rd 0xF3B0] "
         "CRTCNT=[rd 0xF3B1] CSRY=[rd 0xF3DC] CSRX=[rd 0xF3DD] CNSDFG=[rd 0xF3DE] W=$w $h\"",
         "  close $f }"]
    t = 0.0
    for tag, typed, wait in STEPS:
        if typed is not None:
            b.append(f'after time {t:.1f} {{ type "{typed}\\r" }}')
        t += wait
        b.append(f"after time {t:.1f} {{ snap {tag} }}")
    b.append(f"after time {t + 1:.1f} exit")
    return "\n".join(b) + "\n"


def run(machine):
    out = probe_tmp.tmp(f"dosmode_{machine}.txt")
    dsk = probe_tmp.tmp(f"dosmode_{machine}.dsk")
    shutil.copyfile(DOS, dsk)
    if os.path.exists(out):
        os.unlink(out)
    script = probe_tmp.tmp(f"dosmode_{machine}.tcl")
    open(script, "w").write(tcl(out))
    proc = subprocess.Popen(omsx_preflight.guarded(
        [OMSX, "-machine", machine, "-diska", dsk, "-command",
         "set renderer none; set sound_driver null", "-script", script]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 150
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    return open(out).read().splitlines() if os.path.exists(out) else ["<NO OUTPUT>"]



def render(lines):
    out = {}
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        tag, cells, hx = parts[0], " ".join(parts[1:-1]), parts[-1]
        w = 40 if "W=40" in cells else 32
        txt = "".join(chr(c) if 32 <= c < 127 else " " for c in bytes.fromhex(hx))
        rows = [txt[i:i + w].rstrip() for i in range(0, len(txt), w) if txt[i:i + w].strip()]
        out[tag] = cells + " | " + " | ".join(rows)
    return out


def main():
    if not os.path.isfile(DOS):
        print(f"INSTRUMENT FAULT: no MSX-DOS 1 system disk at {DOS}")
        return 2
    got = {side: render(run(m)) for side, m in (("CF", "National_CF-3300"),
                                                 ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))}
    bad, blind = [], []
    for tag, _, _ in STEPS:
        cf, zb = got["CF"].get(tag), got["ZB"].get(tag)
        if cf is None:
            verdict = "NO-REFERENCE"
            blind.append(tag)
        elif cf == zb:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(tag)
        print(f"ROW {tag} CF=[{cf}] ZB=[{zb}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: MODE at the A> prompt "
          f"({len(STEPS) - len(bad)}/{len(STEPS)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
