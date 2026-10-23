#!/usr/bin/env python3
"""A text-screen timeline of one disk image on several machines (D-DISKRUN triage).

Black box: the image is COPIED to /tmp and booted with the throttle off; at each
time the probe reads the PC, SCRMOD ($FCAF) and the text name table of the mode
(SCREEN 0 at VRAM 0, 40 columns; SCREEN 1 at $1800, 32 columns). The software is
RUN, never decoded; no ROM byte is read.

    DISKCORPUS_DIR=... python3 -u scratchpad/screen_timeline.py IMAGE [cf|eu|zb ...] [--times 3,5,8]
"""
import os, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
MACHINES = {"cf": ("National_CF-3300", []), "eu": ("Philips_VG_8020", ["-ext", "Philips_NMS_1200"]),
            "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", [])}


def run(image, key, times):
    machine, extra = MACHINES[key]
    td = tempfile.mkdtemp(prefix="stl_")
    dsk, out, script = (os.path.join(td, n) for n in ("d" + os.path.splitext(image)[1], "o.txt", "t.tcl"))
    shutil.copy(image, dsk)
    L = ["set throttle off", f"set __f [open {{{out}}} w]",
         "proc cap {tag} { global __f; set m [debug read memory 0xFCAF];"
         " if {$m == 1} { set a 0x1800; set n 768 } else { set a 0; set n 960 };"
         " binary scan [debug read_block VRAM $a $n] H* h;"
         " puts $__f \"$tag [format %04X [reg PC]] $m $h\"; flush $__f }"]
    L += [f"after time {t} {{ cap T{t} }}" for t in times]
    L.append(f"after time {times[-1] + 0.5} {{ close $__f; exit }}")
    open(script, "w").write("\n".join(L) + "\n")
    p = subprocess.Popen(omsx_preflight.guarded([OMSX, "-machine", machine] + extra + ["-diska", dsk,
                         "-command", "set renderer none; set sound_driver null", "-script", script]),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 30 + 3 * times[-1]:
        time.sleep(0.2)
    if p.poll() is None:
        p.terminate(); p.wait()
    rows = open(out).read().splitlines() if os.path.exists(out) else []
    shutil.rmtree(td)
    return rows


def main():
    args = sys.argv[1:]
    times = [3, 5, 8, 12, 16, 20, 30, 45]
    if "--times" in args:
        i = args.index("--times"); times = [float(x) for x in args[i + 1].split(",")]; del args[i:i + 2]
    image, keys = args[0], args[1:] or ["cf", "zb"]
    src = os.path.join(os.environ["DISKCORPUS_DIR"], image)
    for key in keys:
        print(f"=== {key} {MACHINES[key][0]}  {image}")
        for r in run(src, key, times):
            tag, pc, m, h = r.split()
            b = bytes.fromhex(h); w = 32 if m == "1" else 40
            txt = [b[i:i + w].decode("latin1") for i in range(0, len(b), w)]
            txt = ["".join(c if 32 <= ord(c) < 127 else " " for c in x).rstrip() for x in txt]
            shown = [x for x in txt if x.strip()]
            print(f"  {tag:5s} pc={pc} S{m} | " + " / ".join(shown[:6]))


if __name__ == "__main__":
    main()
