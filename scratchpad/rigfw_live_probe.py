"""D-RIGFW (1b): does the rig drive a RUNNING headless openMSX?

One boot; openMSX polls port A every 0.25 s of real time while the board steps
through up / trig1 on / right / centre / trig1 off. The load-bearing reading is
that a held trigger SURVIVES direction changes (rigstick's rule). Same binding
and settings guard as rigfw_joy_probe.py.
"""
import os, termios, time, select, subprocess
SP = os.path.dirname(os.path.abspath(__file__))
PORT = "/dev/cu.usbmodem1101"
fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd); a[3] &= ~(termios.ECHO | termios.ICANON); termios.tcsetattr(fd, termios.TCSANOW, a)
def rig(c):
    os.write(fd, (c + "\n").encode()); out = b""; t = time.time()
    while time.time() - t < 1.5 and not out.endswith(b"\n"):
        r, _, _ = select.select([fd], [], [], 0.1)
        if r: out += os.read(fd, 256)
    assert out.strip() == b"OK", (c, out)
CFG = "UP {{joy1 -axis1}} DOWN {{joy1 +axis1}} LEFT {{joy1 -axis0}} RIGHT {{joy1 +axis0}} A {{joy1 button0}} B {{joy1 button1}}"
TCL = ('set ::out [open "' + SP + '/rigfw_live_probe.txt" w]\n'
       'set msxjoystick1_config {' + CFG + '}\n'
       'proc poll {n} { puts $::out "[format %.1f [expr {[clock milliseconds]/1000.0}]] [debug read joystickports 0]"; flush $::out\n'
       '  if {$n > 0} { after realtime 0.25 [list poll [expr {$n-1}]] } else { close $::out; exit } }\n'
       'after realtime 3 {poll 40}\n')
open(SP + "/rigfw_live_probe.tcl", "w").write(TCL)
rig("centre"); rig("trig1 off"); rig("trig2 off")
p = subprocess.Popen(["openmsx", "-machine", "C-BIOS_MSX1_EU", "-command",
                      "set save_settings_on_exit false; set renderer none; set sound_driver null",
                      "-script", SP + "/rigfw_live_probe.tcl"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(4.5)
log = []
for c in ["up", "trig1 on", "right", "centre", "trig1 off"]:
    rig(c); log.append(f"{time.time():.1f} {c}"); time.sleep(1.5)
p.wait(timeout=60)
os.close(fd)
print("\n".join(log)); print("---"); print(open(SP + "/rigfw_live_probe.txt").read())
