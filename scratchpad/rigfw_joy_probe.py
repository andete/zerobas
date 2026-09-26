"""D-RIGFW (1a): does a HEADLESS openMSX read the RP2040-Zero rig as a joystick?

tools/rigfw/rigfw.ino makes the board a USB HID joystick (+ mouse) driven over
its CDC serial port. For each board state, boot a fresh C-BIOS MSX1 with
`renderer none`, bind msxjoystick1 to joy1 (openMSX 21's msxjoystick1_config is
EMPTY on this install, so nothing is bound by default), and read port A's pins
from the `joystickports` debuggable (I/O state; no ROM read). 63 = released;
active-low bits 0..3 = up/down/left/right, 4/5 = triggers. `centre` is the
control. save_settings_on_exit is off: the battery's settings.xml is untouched.
"""
import os, termios, time, select, subprocess, sys
SP = os.path.dirname(os.path.abspath(__file__))
PORT = "/dev/cu.usbmodem1101"
def rig(cmds):
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd); a[3] &= ~(termios.ECHO | termios.ICANON); termios.tcsetattr(fd, termios.TCSANOW, a)
    for c in cmds:
        os.write(fd, (c + "\n").encode()); out = b""; t = time.time()
        while time.time() - t < 1.5 and not out.endswith(b"\n"):
            r, _, _ = select.select([fd], [], [], 0.1)
            if r: out += os.read(fd, 256)
        assert out.strip() == b"OK", (c, out)
    os.close(fd)
CFG = "UP {{joy1 -axis1}} DOWN {{joy1 +axis1}} LEFT {{joy1 -axis0}} RIGHT {{joy1 +axis0}} A {{joy1 button0}} B {{joy1 button1}}"
TCL = ("set ::out [open \"" + SP + "/rigfw_joy_probe.txt\" w]\n"
       "puts $::out \"cfgset => [catch {set msxjoystick1_config {" + CFG + "}} m] $m\"\n"
       "after time 3 {\n"
       "  puts $::out \"ports => [debug read joystickports 0]\"\n"
       "  close $::out\n  exit\n}\n")
open(f"{SP}/rigfw_joy_probe.tcl", "w").write(TCL)
for state in ["centre", "up", "right", "downleft"] + ["trig1 on", "trig2 on"]:
    rig(["centre", "trig1 off", "trig2 off"] + ([state] if state != "centre" else []))
    subprocess.run(["openmsx", "-machine", "C-BIOS_MSX1_EU", "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null", "-script", f"{SP}/rigfw_joy_probe.tcl"],
                   capture_output=True, timeout=60)
    print(f"--- rig: {state}")
    print(open(f"{SP}/rigfw_joy_probe.txt").read().rstrip())
rig(["centre", "trig1 off", "trig2 off"])
