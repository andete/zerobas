"""D-RIGFW (3): does a WINDOWED openMSX take the rig's USB mouse -- PAD's switch?

Headless, the board's mouse reaches nothing (rigfw_mouse_probe.py): openMSX
takes touchpad/paddle input from mouse events on its own WINDOW. This run gives
it one: VG-8020, the default renderer, `grabinput on` (so the pointer is held
inside the window and every motion goes to the emulator), throttle ON (the
board acts in wall time). A typed BASIC loop prints a pass counter (the control
that it runs) and the reading on row 0; openMSX snapshots row 0 every 0.5 s of
real time while the board steps through a scripted sequence.

  touchpad (port A): mouse button 1 = touch -> PAD(0); button 2 = the pen's
                     switch -> PAD(3), THE FORM THE TIER SHEET LACKS;
                     position -> PAD(1)/PAD(2) (the whole window is the pad).
  paddle   (port A): horizontal motion -> PDL(1).

Usage: rigfw_window_probe.py touchpad|paddle [machine]   (default Philips_VG_8020)
⚠️ IT TAKES OVER THE HOST SCREEN: a window opens, grabs the pointer until
openMSX exits, and the board moves the real cursor. Joost's rule (2026-09-26):
after 08:00, not while he is playing a game.
"""
import os, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "probes", "lib"))
import rigfw

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = sys.argv[1]
MACH = sys.argv[2] if len(sys.argv) > 2 else "Philips_VG_8020"
SNAP = os.path.join(HERE, f"rigfw_window_{DEV}.txt")
TCLF = os.path.join(HERE, f"rigfw_window_{DEV}.tcl")
# SHORT LINES, EACH TYPED ON ITS OWN (see the timing note at TCL). No line
# here wraps at width 37.
PROG = {
    "touchpad": ["10 A=PAD(0):B=PAD(3):N=N+1",
                 "20 C=PAD(1):D=PAD(2)",
                 '30 LOCATE 0,0:PRINT"M";N;A;B;C;D;"  "',
                 "40 GOTO 10"],
    "paddle": ["10 N=N+1:P=PDL(1)",
               '20 LOCATE 0,0:PRINT"M";N;P;"  "',
               "30 GOTO 10"],
}[DEV]
STEPS = {
    # (label, [board commands]) -- each step then holds for HOLD seconds
    "touchpad": [("idle", []), ("switch on", ["mbtn2 on"]), ("switch off", ["mbtn2 off"]),
                 ("touch on", ["mbtn1 on"]), ("touch+move", ["move 40 20", "move 40 20"]),
                 ("touch+move", ["move -60 -30"]), ("touch off", ["mbtn1 off"])],
    "paddle": [("idle", []), ("right", ["move 30 0", "move 30 0"]),
               ("left", ["move -60 0", "move -60 0", "move -60 0"]), ("still", [])],
}[DEV]
HOLD = 2.0

TYPES = "\n".join(
    f'after time {14 + 4 * i:.1f} {{type "' + l.replace('"', '\\"') + '\\r"}'
    for i, l in enumerate(PROG))
TCL = f'''set grabinput on
set throttle on
# the DEFAULT matrix, for this session only: Joost's saved one offsets X by
# +200, which saturated every X reading at 255 in the first run
set touchpad_transform_matrix {{{{256 0 0}} {{0 256 0}}}}
plug joyporta {DEV}
set ::out [open "{SNAP}" w]
{TYPES}
# 🔴 ONE LINE PER 4 s, FROM 14 s. openMSX's `type` delivers ~70 ms per key on
# every machine, and a second `type` QUEUES behind the first -- so a line typed
# too soon lands while zerobas is still tokenising the previous one, in the sub-
# ROM, with the keyboard scan not running (the keys pressed then are LOST:
# `NT 5`, `RRUN`). Filed as its own item; this probe must not depend on it.
# RUN is typed on its own, after the last program line.
after time {14 + 4 * len(PROG):.1f} {{type "RUN\\r"}}
proc snap {{n}} {{
  set s ""; for {{set i 0}} {{$i < 40}} {{incr i}} {{ append s [format %c [debug read VRAM $i]] }}
  puts $::out "[format %.1f [expr {{[clock milliseconds]/1000.0}}]] |$s|"; flush $::out
  if {{$n > 0}} {{ after realtime 0.5 [list snap [expr {{$n-1}}]] }} else {{
    # the whole screen once at the end: a run whose program never started must
    # show WHY, not just an unchanged row 0
    set s ""; for {{set i 0}} {{$i < 960}} {{incr i}} {{ append s [format %c [debug read VRAM $i]] }}
    for {{set r 0}} {{$r < 24}} {{incr r}} {{ puts $::out "screen [format %02d $r] |[string range $s [expr {{$r*40}}] [expr {{$r*40+39}}]]|" }}
    close $::out; exit }}
}}
after time {14 + 4 * len(PROG) + 2:.1f} {{snap 50}}
'''
open(TCLF, "w").write(TCL)
port = rigfw.find()
assert port, "no rigfw board"
rigfw.set_state(port, "centre")
before = open(os.path.expanduser("~/.openMSX/share/settings.xml"), "rb").read()
p = subprocess.Popen(["openmsx", "-machine", MACH,
                      "-command", "set save_settings_on_exit false; set sound_driver null",
                      "-script", TCLF], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    # focus the window: grab only takes effect while openMSX is the key window
    time.sleep(3)
    subprocess.run(["osascript", "-e", 'tell application "openMSX" to activate'],
                   capture_output=True, timeout=10)
    t0 = time.time()
    while not (os.path.exists(SNAP) and os.path.getsize(SNAP) > 10):
        time.sleep(0.2)
        if time.time() - t0 > 60:
            break
    time.sleep(1.5)                     # let the BASIC loop start
    fd = rigfw._open(port)
    log = []
    try:
        for label, cmds in STEPS:
            for c in cmds:
                r = rigfw._ask(fd, c)
                assert r[-1:] == ["OK"], (c, r)
            log.append(f"{time.time():.1f} {label} {cmds}")
            time.sleep(HOLD)
    finally:
        for c in ("mbtn1 off", "mbtn2 off"):
            rigfw._ask(fd, c)
        os.close(fd)
    p.wait(timeout=120)
finally:
    if p.poll() is None:
        p.terminate()
print("\n".join(log))
print("---")
print(open(SNAP).read().rstrip())
after = open(os.path.expanduser("~/.openMSX/share/settings.xml"), "rb").read()
print("settings.xml", "UNCHANGED" if before == after else "CHANGED")
