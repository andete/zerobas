#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DOSSESSION (gate: dossession-acceptance): MSX-DOS commands typed at A>, the National CF-3300 against zerobas.

Joost 2026-11-23 (the order "3, 2, 1"): MSX-DOS's commands are an INTEGRATION suite, not spec pages --
COMMAND.COM and MSXDOS.SYS are Microsoft's, loaded from the user's disk; zerobas supplies the disk ROM, the BDOS
and the boot, and every command reaches the disk through them.

Both machines boot a private copy of the reference DOS disk (test.dsk: MSX-DOS 1.03 / COMMAND 1.08) with one known
text file added (HELLO.TXT), answer the date prompt, then type each step of SESSION and snapshot after it: the
text screen (the current mode's name table) and the cursor. After the session the disk image the machine wrote is
read back -- the root directory (name, extension, attribute, size) and every file's bytes -- and compared too. The
directory's date / time fields are left out: neither machine has a clock, so a stamp records when the probe ran.

Clean-room: typed keys in; work-area RAM, VRAM and the disk image the machine wrote out. Microsoft's DOS files run
as they are; nothing of theirs is read.
Each snapshot is a row: `ROW <step> SAME|DIVERGES`, the two screens printed under a divergence.
Exit 0 all agree; 1 a divergence; 2 no reading / no DOS disk.
usage: disk_probe_dossession.py [DOSDISK]
"""
import hashlib
import os
import shutil
import signal
import struct
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402
from disk_probe_bdos import fat12_add               # noqa: E402  (reuse, don't duplicate)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
DOS = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
MACHINES = (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))
HELLO = b"HELLO FROM THE SESSION\r\nSECOND LINE\r\n\x1a"

# (tag, the line typed -- None: nothing, wait only -- and the seconds to wait after it)
SESSION = [
    ("boot", None, 14),
    ("date", "", 5),
    ("dir", "DIR", 8),
    ("dirw", "DIR /W", 8),
    ("type", "TYPE HELLO.TXT", 5),
    ("copy", "COPY HELLO.TXT COPY1.TXT", 8),
    ("dircopy", "DIR COPY1.TXT", 6),
    ("ren", "REN COPY1.TXT COPY2.TXT", 6),
    ("dirren", "DIR COPY?.TXT", 6),
    ("concat", "COPY HELLO.TXT+HELLO.TXT CAT.TXT", 8),
    ("typecat", "TYPE CAT.TXT", 5),
    ("del", "DEL COPY2.TXT", 6),
    ("dirdel", "DIR COPY?.TXT", 6),
    ("delnone", "DEL NOSUCH.TXT", 5),
    ("typenone", "TYPE NOSUCH.TXT", 5),
    ("verify", "VERIFY ON", 4),
    ("datecmd", "DATE", 4),
    ("dateset", "11-23-87", 4),
    ("rem", "REM A REMARK", 3),
    ("bad", "NOSUCHCMD", 5),
]


def tcl(out):
    """The session as a chain of Tcl callbacks: type a step's line, then poll every 0.25 s until the machine is
    back at the prompt -- the cursor at column 3 of a row reading `A>`, and the screen unchanged for 1 s -- then
    snapshot and go on. The two machines run at different speeds (a 42-file DIR scrolls for longer on one), so a
    fixed delay types the next command into a machine still busy with the last one."""
    steps = " ".join("{%s %s %d}" % (tag, "{}" if typed is None else "{" + typed + "}", wait)
                     for tag, typed, wait in SESSION)
    return "\n".join([
        "set throttle off",
        "proc rd {a} { debug read memory $a }",
        "proc rd16 {a} { expr {[rd $a] + 256*[rd [expr {$a+1}]]} }",
        "proc screen {} {",
        "  set m [rd 0xFCAF]",
        "  if {$m == 0} { set base [rd16 0xF3B3]; set w 40 } else { set base [rd16 0xF3BD]; set w 32 }",
        "  binary scan [debug read_block VRAM $base [expr {$w*24}]] H* h",
        "  return [list $w $h] }",
        "proc snap {tag} {",
        "  lassign [screen] w h",
        f"  set f [open {{{out}}} a]",
        "  puts $f \"$tag W=$w CSR=[rd 0xF3DD],[rd 0xF3DC] $h\"",
        "  close $f }",
        "proc atprompt {} {",
        "  lassign [screen] w h",
        "  set y [rd 0xF3DC]; set x [rd 0xF3DD]",
        "  set row [string range $h [expr {($y-1)*$w*2}] [expr {($y-1)*$w*2+3}]]",
        "  return [expr {$x == 3 && $row eq \"413e\"}] }",
        f"set ::steps {{{steps}}}",
        "set ::last {}; set ::still 0; set ::tries 0",
        "proc next {} {",
        "  if {[llength $::steps] == 0} { exit }",
        "  set ::cur [lindex $::steps 0]; set ::steps [lrange $::steps 1 end]",
        "  lassign $::cur tag typed wait",
        "  if {$tag ne \"boot\"} { type \"$typed\\r\" }",
        "  set ::last {}; set ::still 0; set ::tries 0",
        "  after time $wait poll }",
        "proc poll {} {",
        "  lassign $::cur tag typed wait",
        "  incr ::tries",
        "  set s [screen]",
        "  if {$s eq $::last} { incr ::still } else { set ::still 0; set ::last $s }",
        "  set prompt [expr {$tag in {boot datecmd} ? 1 : [atprompt]}]",
        "  if {($prompt && $::still >= 4) || $::tries > 240} { snap $tag; next; return }",
        "  after time 0.25 poll }",
        "next", ""])


def disk_listing(img):
    """The root directory (name.ext, attribute, size) and each file's sha1, from the image the machine wrote.
    Date / time fields are not read: neither machine has a clock."""
    bps = struct.unpack_from("<H", img, 11)[0]
    spc = img[13]
    resv = struct.unpack_from("<H", img, 14)[0]
    nfat = img[16]
    nroot = struct.unpack_from("<H", img, 17)[0]
    fatsz = struct.unpack_from("<H", img, 22)[0]
    root = (resv + nfat * fatsz) * bps
    data = root + nroot * 32
    fat = img[resv * bps:(resv + fatsz) * bps]

    def nxt(c):
        v = struct.unpack_from("<H", fat, c * 3 // 2)[0]
        return (v >> 4) if c & 1 else (v & 0xFFF)
    out = []
    for i in range(nroot):
        e = img[root + i * 32:root + i * 32 + 32]
        if e[0] == 0:
            break
        if e[0] == 0xE5 or e[11] & 0x08:
            continue
        name = e[0:8].decode("latin-1").rstrip() + "." + e[8:11].decode("latin-1").rstrip()
        size = struct.unpack_from("<I", e, 28)[0]
        c, body, guard = struct.unpack_from("<H", e, 26)[0], b"", 0
        while 2 <= c < 0xFF0 and len(body) < size and guard < 4096:
            off = data + (c - 2) * spc * bps
            body += img[off:off + spc * bps]
            c, guard = nxt(c), guard + 1
        out.append(f"{name} attr={e[11]:02X} size={size} sha1={hashlib.sha1(body[:size]).hexdigest()[:12]}")
    return sorted(out)


# HELLO.TXT's directory date: 1990-05-05, not 0 -- so a COPY shows whether the copy keeps the SOURCE's date or is
# stamped with the current one (the CF-3300 keeps it: D-COPYDATE)
HELLO_DATE = ((1990 - 1980) << 9) | (5 << 5) | 5


def _date(img, name11, date):
    bps = struct.unpack_from("<H", img, 11)[0]
    resv = struct.unpack_from("<H", img, 14)[0]
    root = (resv + img[16] * struct.unpack_from("<H", img, 22)[0]) * bps
    for i in range(struct.unpack_from("<H", img, 17)[0]):
        off = root + i * 32
        if bytes(img[off:off + 11]) == name11:
            struct.pack_into("<H", img, off + 24, date)
            return
    raise SystemExit(f"dossession: {name11!r} not in the root directory")


def run(machine):
    out = probe_tmp.tmp(f"dossession_{machine}.txt")
    dsk = probe_tmp.tmp(f"dossession_{machine}.dsk")
    img = bytearray(open(DOS, "rb").read())
    fat12_add(img, "HELLO", "TXT", HELLO)
    _date(img, b"HELLO   TXT", HELLO_DATE)
    open(dsk, "wb").write(img)
    if os.path.exists(out):
        os.unlink(out)
    script = probe_tmp.tmp(f"dossession_{machine}.tcl")
    open(script, "w").write(tcl(out))
    proc = subprocess.Popen(omsx_preflight.guarded(
        [OMSX, "-machine", machine, "-diska", dsk, "-command",
         "set renderer none; set sound_driver null", "-script", script]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 300
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    lines = open(out).read().splitlines() if os.path.exists(out) else []
    return lines, disk_listing(bytearray(open(dsk, "rb").read()))


def render(lines):
    out = {}
    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            continue
        tag, w, csr, hx = parts[0], int(parts[1][2:]), parts[2], parts[3]
        txt = "".join(chr(c) if 32 <= c < 127 else " " for c in bytes.fromhex(hx))
        rows = [txt[i:i + w].rstrip() for i in range(0, len(txt), w)]
        while rows and not rows[-1]:
            rows.pop()
        out[tag] = (f"W={w} {csr}", rows)
    return out


def main():
    if not os.path.isfile(DOS):
        print(f"INSTRUMENT FAULT: no MSX-DOS 1 system disk at {DOS}")
        return 2
    got = {}
    for side, m in MACHINES:
        lines, listing = run(m)
        got[side] = (render(lines), listing)
    bad, blind = [], []
    for tag, typed, _ in SESSION:
        cf, zb = got["CF"][0].get(tag), got["ZB"][0].get(tag)
        if cf is None:
            verdict = "NO-REFERENCE"
            blind.append(tag)
        elif cf == zb:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(tag)
        print(f"ROW {tag:9s} {typed if typed is not None else '(wait)'!r:40s} {verdict}", flush=True)
        if verdict == "DIVERGES":
            for side, v in (("CF", cf), ("ZB", zb)):
                print(f"   {side} {v[0] if v else None}")
                for r in (v[1] if v else []):
                    print(f"   {side} |{r}")
    cfl, zbl = got["CF"][1], got["ZB"][1]
    same_disk = cfl == zbl
    print(f"ROW {'disk':9s} {'(the directory and file bytes after)':40s} {'SAME' if same_disk else 'DIVERGES'}")
    if not same_disk:
        for side, lst in (("CF", cfl), ("ZB", zbl)):
            for e in lst:
                print(f"   {side} {e}")
        bad.append("disk")
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    n = len(SESSION) + 1
    print(f"\n{'PASS' if not bad else 'FAIL'}: MSX-DOS commands typed at A> ({n - len(bad)}/{n})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
