# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CALLSYSTEM (2026-10-09): does `CALL SYSTEM` look at the disk in the drive
NOW, or at what was booted at power-on? Swaps the disk mid-session (openMSX
`diska`), which omsx_repl cannot do.

  late    boot a data disk (test720) into Disk BASIC, insert the MSX-DOS disk,
          CALL SYSTEM
  gone    boot the MSX-DOS disk into DOS, BASIC, insert test720, CALL SYSTEM

Clean-room: typed keys in, the SCREEN 0 name table out (VRAM 0..959).
usage: callsystem_swap.py DOSDISK [machine]
"""
import os, shutil, signal, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"


def script(steps, out):
    body = ["set throttle off",
            "proc __cap {} { set m [debug read memory 0xFCAF]; "
            "set cells [list [debug read memory 0xF3B1] [debug read memory 0xF3DE] [debug read memory 0xF3B0] [debug read memory 0xF3DC] [debug read memory 0xF3DD] [debug read memory 0xF3AE]]; "
            "if {$m == 1} { set a 0x1800; set n 768 } else { set a 0; set n 960 }; "
            "binary scan [debug read_block VRAM $a $n] H* h; "
            f"set f [open {{{out}}} w]; puts $f \"$m $h [join $cells ,]\"; close $f; exit }}"]
    t = 0.0
    for kind, arg, wait in steps:
        t += wait
        if kind == "type":
            body.append(f'after time {t:.1f} {{ type "{arg}\\r" }}')
        else:
            body.append(f'after time {t:.1f} {{ diska {{{arg}}} }}')
    body.append(f"after time {t + 8:.1f} {{ __cap }}")
    return "\n".join(body) + "\n", t + 8


def run(machine, boot_dsk, steps, tag):
    out = probe_tmp.tmp(f"callsystem_swap_{tag}.hex")
    tcl, tend = script(steps, out)
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine, "-diska", boot_dsk,
           "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 120
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        return ["<TIMEOUT>"]
    if not os.path.exists(out):
        return ["<NO CAPTURE>"]
    mode, hx, cells = open(out).read().split()
    b = bytes.fromhex(hx)
    w = 32 if mode == "1" else 40
    s = "".join(chr(c) if 32 <= c < 127 else " " for c in b)
    return [f"(SCRMOD {mode}; CRTCNT,CNSDFG,LINLEN,CSRY,CSRX,LINL40 = {cells})"] + [s[i:i + w].rstrip() for i in range(0, len(s), w) if s[i:i + w].strip()]


def main():
    dos = sys.argv[1]
    machine = sys.argv[2] if len(sys.argv) > 2 else "National_CF-3300"
    data = probe_tmp.tmp("callsystem_swap_test720.dsk")
    dosc = probe_tmp.tmp("callsystem_swap_dos.dsk")
    cases = {
        "late": (data, [("type", "SCREEN 0:WIDTH 40", 24), ("disk", dosc, 4),
                        ("type", "CALL SYSTEM", 2), ("type", "", 10), ("type", "", 4),
                        ("type", "MODE 40", 4), ("type", "DIR", 4)]),
        "gone": (dosc, [("type", "", 14), ("type", "", 4), ("type", "BASIC", 4),
                        ("type", "SCREEN 0:WIDTH 40", 10), ("disk", data, 4),
                        ("type", "CALL SYSTEM", 2), ("type", "PRINT 12345", 10)]),
    }
    auto = probe_tmp.tmp("callsystem_swap_auto.dsk")
    cases["sysscreen"] = (dosc, [("type", "", 14), ("type", "", 4), ("type", "BASIC", 4),
                                 ("type", "SCREEN 0:WIDTH 40", 10), ("type", "CALL SYSTEM", 4)])
    cases["sysauto"] = (auto, [("type", "BASIC", 24), ("type", "SCREEN 0:WIDTH 40", 10),
                               ("type", "CALL SYSTEM", 4)])
    for name in sys.argv[3:] or list(cases):
        if name == "sysauto":
            shutil.copyfile(os.environ["CS_AUTO"], auto)
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), data)
        shutil.copyfile(dos, dosc)
        boot, steps = cases[name]
        print(f"== {name} {machine}", flush=True)
        for r in run(machine, boot, steps, name):
            print(f"   |{r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
