"""D-PADTRACE: how does the VG-8020 talk to the touchpad? A PORT trace, windowed.

zerobas's GTPAD (tape/tape.asm, decision D-I-7) carries two filed GUESSES: the
pen SWITCH is read off R14 b4, and the uPD7001's channel-select (address) phase
is omitted, so X and Y read one unaddressed frame. Measured windowed on
2026-09-26 (TODO, "RULING 4's RIG"): with the rig's mouse held on the pad the
VG-8020 reads PAD(3) = -1 and follows the pen on PAD(1)/PAD(2); zerobas reads 0
for all three. Both guesses were made because an UNDRIVEN panel converts to 0;
the rig removes that premise.

🔴 CLEAN ROOM: I/O PORTS ONLY. openMSX I/O watchpoints on $A0 (PSG register
select), $A1 (PSG register write -- R15 carries the port's output lines) and $A2
(PSG register read -- R14 carries its input lines) log every access the
reference makes while ONE `PAD(n)` call runs; a `POKE &HC000,n+1` / `POKE
&HC000,0` pair (a RAM watchpoint on the marker VALUE) brackets the call. No ROM
byte, no code address, no breakpoint in ROM.

The rig (tools/rigfw) holds the pen: idle, the SWITCH (mouse button 2), a TOUCH
(button 1) at one place, then at another. Each call's trace is deduplicated per
phase.

    python3 -u scratchpad/padtrace_probe.py [--headless]
      --headless  no window, no board: checks the apparatus (the marker fires,
                  the read watchpoint carries the value read) on an EMPTY port
⚠️ WINDOWED, IT TAKES OVER THE HOST SCREEN (rigfw_window_probe.py's note).
"""
import collections, os, re, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import rigfw

HERE = os.path.dirname(os.path.abspath(__file__))
MACH = "Philips_VG_8020"
HEADLESS = "--headless" in sys.argv
TRACE = os.path.join(HERE, "padtrace_raw.txt")
TCLF = os.path.join(HERE, "padtrace.tcl")
PROG = ["10 FOR N=0 TO 3",
        "20 POKE &HC000,N+1:V=PAD(N)",
        "30 POKE &HC000,0",
        '40 LOCATE 0,N:PRINT"P";N;V;"  "',
        "50 NEXT:GOTO 10"]
STEPS = [("idle", []), ("switch", ["mbtn2 on"]), ("switch-off", ["mbtn2 off"]),
         ("touch-A", ["mbtn1 on"]), ("touch-B", ["move 60 30", "move 60 30"]),
         ("touch-C", ["move -100 -40"]), ("release", ["mbtn1 off"])]
HOLD = 3.0

TYPES = "\n".join(f'after time {14 + 4 * i:.1f} {{type "' + l.replace('"', '\\"') + '\\r"}'
                  for i, l in enumerate(PROG))
TCL = f'''{"" if HEADLESS else "set grabinput on"}
set throttle on
set touchpad_transform_matrix {{{{256 0 0}} {{0 256 0}}}}
plug joyporta touchpad
set ::out [open "{TRACE}" w]
set ::on 0
set ::reg -1
set ::buf {{}}
# the marker: N+1 opens a call's trace, 0 closes it (a watchpoint fires BEFORE
# the write, so the value is $::wp_last_value; boot's RAM test writes $C000 too,
# which is why only 1..4 and 0-while-open count)
debug set_watchpoint write_mem 0xC000 {{}} {{
  set v $::wp_last_value
  if {{$v >= 1 && $v <= 4}} {{ set ::on $v; set ::buf {{}} }} elseif {{$v == 0 && $::on}} {{
    puts $::out "[clock milliseconds] PAD([expr {{$::on-1}}]) $::buf"; set ::on 0 }} }}
debug set_watchpoint write_io 0xA0 {{}} {{ set ::reg $::wp_last_value
  if {{$::on}} {{ lappend ::buf "S$::wp_last_value" }} }}
debug set_watchpoint write_io 0xA1 {{}} {{
  if {{$::on}} {{ lappend ::buf "W$::reg=[format %02X $::wp_last_value]" }} }}
# 🔴 A READ watchpoint fires BEFORE the read and $::wp_last_value is EMPTY there:
# the first headless run logged every R14 SELECT and not one value, because the
# `format` of "" raised inside the callback and dropped the entry silently. The
# value is taken with a side-effect-free PEEK of the port instead.
debug set_watchpoint read_io 0xA2 {{}} {{
  if {{$::on}} {{ lappend ::buf "R$::reg=[format %02X [debug read ioports 0xA2]]" }} }}
{TYPES}
after time {14 + 4 * len(PROG):.1f} {{type "RUN\\r"}}
after time {14 + 4 * len(PROG) + (8 if HEADLESS else 2 + HOLD * len(STEPS) + 4):.1f} {{
  set s ""; for {{set i 0}} {{$i < 200}} {{incr i}} {{ append s [format %c [debug read VRAM $i]] }}
  puts $::out "SCREEN |$s|"; close $::out; exit }}
'''


def raise_window(pid):
    """🔴 FOCUS BY PROCESS ID, NOT BY APP NAME. The first windowed run
    (2026-09-27) activated `application "openMSX"` once and read PAD 0 in every
    phase, touch and switch alike: `grabinput` only takes while openMSX is the
    frontmost window, and a binary started from a shell is not reliably named
    "openMSX" to AppleScript. Raise the exact process, and again before every
    board step -- focus lost mid-run is a null result, not a reading."""
    subprocess.run(["osascript", "-e", 'tell application "System Events" to set frontmost '
                    f'of (first process whose unix id is {pid}) to true'],
                   capture_output=True, timeout=10)


def main():
    open(TCLF, "w").write(TCL)
    if os.path.exists(TRACE):
        os.unlink(TRACE)
    cmd = ["openmsx", "-machine", MACH, "-command",
           "set save_settings_on_exit false; set sound_driver null"
           + ("; set renderer none" if HEADLESS else ""), "-script", TCLF]
    log = []
    if HEADLESS:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    else:
        port = rigfw.find()
        if not port:
            raise SystemExit("REFUSE: no rigfw board answers")
        rigfw.set_state(port, "centre")
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(3)
            raise_window(p.pid)
            time.sleep(14 + 4 * len(PROG) - 3 + 2)       # typed + RUN + the loop starts
            fd = rigfw._open(port)
            try:
                for label, cmds in STEPS:
                    raise_window(p.pid)
                    for c in cmds:
                        r = rigfw._ask(fd, c)
                        assert r[-1:] == ["OK"], (c, r)
                    log.append((time.time() * 1000, label))
                    time.sleep(HOLD)
            finally:
                for c in ("mbtn1 off", "mbtn2 off"):
                    rigfw._ask(fd, c)
                os.close(fd)
            p.wait(timeout=120)
        finally:
            if p.poll() is None:
                p.terminate()
    lines = open(TRACE).read().splitlines() if os.path.exists(TRACE) else []
    calls = [l for l in lines if " PAD(" in l]
    print(f"{len(calls)} traced calls")
    by = collections.defaultdict(collections.Counter)
    for l in calls:
        ms, rest = l.split(" ", 1)
        ph = "run"
        for t, lab in log:
            if float(ms) >= t:
                ph = lab
        by[ph][rest] += 1
    for ph in [p for p in ["run"] + [s[0] for s in STEPS] if p in by]:
        print(f"=== {ph}")
        for tr, n in sorted(by[ph].items()):
            print(f"  {n:3}x {tr}")
    for l in lines:
        if l.startswith("SCREEN"):
            s = l[8:-1]
            print("\n".join("  |" + s[i:i + 40] + "|" for i in range(0, 200, 40)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
