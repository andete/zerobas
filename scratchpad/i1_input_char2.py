#!/usr/bin/env python3
"""I1 characterization round 4 -- LIVE input: does openMSX `keymatrixdown` drive
STICK(0)/STRIG(0) on the VG-8020, and what does each row-8 bit return?

Feasibility probe for the acceptance gate's teeth: the KEYBUF injection the REPL
driver uses bypasses the key MATRIX entirely, so a STICK/STRIG read (which scans
the matrix) can only be exercised by holding a matrix bit down during the RUN.
"""
from __future__ import annotations
import os, re, subprocess, sys, tempfile, time, signal

REPO = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl as R  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")

# A sampling loop: hold the matrix bit while lines 20-40 spin, latch any nonzero.
PROG = [
    "A=0:C=0",
    "FOR I=1 TO 600",
    "B=STICK(0):IF B<>0 THEN A=B",
    "D=STRIG(0):IF D<>0 THEN C=D",
    "NEXT",
    'PRINT"Z";A;C',
]

CASES = [  # label, row, mask
    ("none",    8, 0x00),
    ("bit0",    8, 0x01),
    ("bit4",    8, 0x10),
    ("bit5",    8, 0x20),
    ("bit6",    8, 0x40),
    ("bit7",    8, 0x80),
    ("bit5+6",  8, 0x60),
]


def run(label: str, row: int, mask: int) -> str | None:
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="km_", delete=False).name
    tcl = out + ".tcl"
    seq = [f"{10*(i+1)} {ln}" for i, ln in enumerate(PROG)]
    body, t = [], 8.0
    for ln in seq:
        body.append(f'after time {t:.1f} {{ __inj {{{ln}}} }}')
        t += 2.0
    body.append(f'after time {t:.1f} {{ __inj {{RUN}} }}')
    t += 1.0
    if mask:
        body.append(f'after time {t:.1f} {{ keymatrixdown {row} {mask} }}')
    t += 12.0                                     # the sampling loop's window
    if mask:
        body.append(f'after time {t:.1f} {{ keymatrixup {row} {mask} }}')
    t += 2.0
    body.append(f'after time {t:.1f} {{ puts $__f "cap=[__hex_v {R.SCR_ADDR} '
                f'{R.SCR_LEN}]"; flush $__f }}')
    t += 2.0
    body.append(f"after time {t:.1f} {{ close $__f; exit }}")
    head = (
        "set throttle off\n"
        f"set __f [open {{{out}}} w]\n"
        "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
        " return $h }\n"
        "proc __key {s} {\n"
        "  set n [string length $s]\n"
        "  for {set i 0} {$i < $n} {incr i} {\n"
        f"    debug write memory [expr {{{R.KEYBUF} + $i}}] "
        "[scan [string index $s $i] %c]\n"
        "  }\n"
        f"  debug write memory {R.GETPNT} [expr {{{R.KEYBUF} & 0xFF}}]\n"
        f"  debug write memory [expr {{{R.GETPNT}+1}}] [expr {{({R.KEYBUF} >> 8) & 0xFF}}]\n"
        f"  set p [expr {{{R.KEYBUF} + $n}}]\n"
        f"  debug write memory {R.PUTPNT} [expr {{$p & 0xFF}}]\n"
        f"  debug write memory [expr {{{R.PUTPNT}+1}}] [expr {{($p >> 8) & 0xFF}}]\n"
        "}\n"
        "proc __inj {s} { append s \"\\r\"; __key $s }\n"
    )
    open(tcl, "w").write(head + "\n".join(body) + "\n")
    cmd = [R.find_omsx(None), "-machine", REF,
           "-command", "set renderer none", "-script", tcl]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    dl = time.time() + 240
    while p.poll() is None and time.time() < dl:
        time.sleep(0.05)
    if p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    raw = None
    if os.path.exists(out):
        for ln in open(out):
            m = re.match(r"cap=([0-9a-f]*)", ln.strip())
            if m and m.group(1):
                data = bytes.fromhex(m.group(1))
                raw = "".join(chr(b) if 32 <= b < 127 else " " for b in data)
        os.unlink(out)
    os.unlink(tcl)
    return raw


if __name__ == "__main__":
    print(f"=== ROUND 4: live key-matrix -> STICK(0)/STRIG(0) on {REF} ===")
    for label, row, mask in CASES:
        raw = run(label, row, mask)
        flat = " ".join((raw or "").split())
        m = re.search(r"Z[ \d\-]*", flat)
        print(f"  {label:8} row{row} mask=${mask:02x} -> {(m.group(0).strip() if m else None)!r}"
              f"   | {flat[-60:]!r}")
