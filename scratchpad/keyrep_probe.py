#!/usr/bin/env python3
"""D-KEYREP: what the key scan does with REPCNT when a NEW key goes down.

Black box: the machine boots to BASIC with no disk, sits idle, and the probe
holds keys on the key matrix (openMSX keymatrixdown / keymatrixup), sampling
the work area every 20 ms of emulated time:
  SCNCNT $F3F6, REPCNT $F3F7, PUTPNT $F3F8, GETPNT $F3FA.
No ROM byte is read. Per press it prints REPCNT before and at each change, and
how many characters the press queued: PUTPNT's advance round the 40-byte ring at
KEYBUF $FBF0 (BASIC takes the keys as they come, so the buffer itself says
nothing; the write pointer counts every one queued).

Presses ('P' = row 4 bit 5), each after an idle spell:
  A  120 ms   a human tap after idle
  B  120 ms   again, to see whether A's state carries
  C  1500 ms  held: the initial delay and the repeat rate
  D  120 ms   right after C's release (REPCNT as C left it)
  E  120 ms   after a 3 s idle
  F  120 ms   SHIFT and P down together (what `type` does for a capital)
  G  120 ms   SHIFT 40 ms first, then P

    python3 -u scratchpad/keyrep_probe.py [MACHINE ...]
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
MACHINES = sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]


def ring(h):
    """PUTPNT (little-endian, hex chars 4..8 of the sample) as a ring index."""
    return (int(h[6:8] + h[4:6], 16) - 0xFBF0) % 40


PRESSES = [("A", 14.0, 0.12), ("B", 17.0, 0.12), ("C", 20.0, 1.5), ("D", 21.6, 0.12),
           ("E", 25.0, 0.12), ("F", 28.0, 0.12), ("G", 31.0, 0.12)]
SHIFT = {"F": 0.0, "G": 0.04}    # SHIFT (row 6 bit 0) down this long before P, up with it


def tcl(out):
    L = ["set throttle off", f"set __f [open {{{out}}} w]",
         "proc st {tag} { global __f; binary scan [debug read_block memory 0xF3F6 6] H* h;"
         " puts $__f \"$tag [format %.3f [machine_info time]] $h\"; flush $__f }"]
    for name, t0, hold in PRESSES:
        L.append(f"after time {t0 - 0.1:.3f} {{ st {name}.pre }}")
        if name in SHIFT:
            L.append(f"after time {t0 - SHIFT[name]:.3f} {{ keymatrixdown 6 0x01 }}")
            L.append(f"after time {t0 + hold:.3f} {{ keymatrixup 6 0x01 }}")
        L.append(f"after time {t0:.3f} {{ keymatrixdown 4 0x20 }}")
        L.append(f"after time {t0 + hold:.3f} {{ keymatrixup 4 0x20 }}")
        n = int((hold + 0.3) / 0.02)
        for i in range(n):
            L.append(f"after time {t0 + 0.01 + i * 0.02:.3f} {{ st {name}.{i} }}")
    L.append("after time 34 { close $__f; exit }")
    return "\n".join(L) + "\n"


def run(machine):
    td = tempfile.mkdtemp(prefix="keyrep_")
    out, script = os.path.join(td, "o.txt"), os.path.join(td, "t.tcl")
    open(script, "w").write(tcl(out))
    p = subprocess.Popen(omsx_preflight.guarded([OMSX, "-machine", machine, "-command",
                         "set renderer none; set sound_driver null", "-script", script]),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t = time.time()
    while p.poll() is None and time.time() - t < 120:
        time.sleep(0.2)
    if p.poll() is None:
        p.terminate()
        p.wait()
    rows = [l.split() for l in open(out)] if os.path.exists(out) else []
    shutil.rmtree(td)
    return rows


def main():
    for m in MACHINES:
        rows = run(m)
        print(f"=== {m}")
        if not rows:
            print("  NO READING")
            continue
        for name, t0, hold in PRESSES:
            mine = [r for r in rows if r[0].split(".")[0] == name]
            pre = next(r for r in mine if r[0].endswith(".pre"))
            put0 = ring(pre[2])
            seq, last = [], None
            for r in mine:
                if r[0].endswith(".pre"):
                    continue
                rep, put = int(r[2][2:4], 16), ring(r[2])
                if (rep, put) != last:
                    seq.append(f"{float(r[1]) - t0:+.2f}s rep={rep} q={(put - put0) % 40}")
                    last = (rep, put)
            endput = ring(mine[-1][2])
            print(f"  {name} hold {hold * 1000:.0f} ms  REPCNT before={int(pre[2][2:4], 16)}"
                  f"  queued={(endput - put0) % 40}")
            print("     " + " | ".join(seq))


if __name__ == "__main__":
    main()
