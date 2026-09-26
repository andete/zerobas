"""D-RIGFW (2): does the rig's USB MOUSE reach PDL/PAD in a headless openMSX?

Usage: rigfw_mouse_probe.py none paddle|touchpad. VG-8020 (MSX1: PDL = paddle,
PAD(0..7) = touchpad; PAD(12..) is MSX2 and raises Illegal function call), the
pluggable in port A, a typed BASIC loop printing a pass counter (the control
that the loop runs) and the reading; the board holds mouse button 1 and sends
four relative moves. ⚠️ The board is a real HID mouse: it moves the HOST cursor.
"""
import os, termios, time, select, subprocess, sys
SP = os.path.dirname(os.path.abspath(__file__))
RENDER = sys.argv[1]
DEV = sys.argv[2]
fd = os.open("/dev/cu.usbmodem1101", os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd); a[3] &= ~(termios.ECHO | termios.ICANON); termios.tcsetattr(fd, termios.TCSANOW, a)
def rig(c):
    os.write(fd, (c + "\n").encode()); out = b""; t = time.time()
    while time.time() - t < 1.5 and not out.endswith(b"\n"):
        r, _, _ = select.select([fd], [], [], 0.1)
        if r: out += os.read(fd, 256)
    assert out.strip() == b"OK", (c, out)
PROG = {'paddle': r'10 N=N+1:LOCATE 0,0:PRINT "M";N;PDL(1);"  ":GOTO 10\rRUN\r',
        'touchpad': r'10 N=N+1:A=PAD(0):LOCATE 0,0:PRINT "M";N;A;PAD(1);PAD(2);"  ":GOTO 10\rRUN\r'}[DEV]
TCL = ('set ::out [open "' + SP + '/rigfw_mouse_probe.txt" w]\n'
       'plug joyporta ' + DEV + '\n'
       'after time 12 {type "' + PROG.replace('"', '\\"') + '"}\n'
       'proc snap {n} { set s ""; for {set i 0} {$i < 40} {incr i} { append s [format %c [debug read VRAM $i]] }\n'
       '  puts $::out "[format %.1f [expr {[clock milliseconds]/1000.0}]] |$s|"; flush $::out\n'
       '  if {$n > 0} { after realtime 1 [list snap [expr {$n-1}]] } else { close $::out; exit } }\n'
       'after time 16 {snap 8}\n')
open(SP + "/rigfw_mouse_probe.tcl", "w").write(TCL)
p = subprocess.Popen(["openmsx", "-machine", "Philips_VG_8020", "-command",
                      f"set save_settings_on_exit false; set renderer {RENDER}; set sound_driver null",
                      "-script", SP + "/rigfw_mouse_probe.tcl"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
t0 = time.time()
while not os.path.exists(SP + "/rigfw_mouse_probe.txt") or os.path.getsize(SP + "/rigfw_mouse_probe.txt") < 10:
    time.sleep(0.2)
    if time.time() - t0 > 60: break
log = []
rig("mbtn1 on")
for i in range(4):
    rig("move 15 8"); log.append(f"{time.time():.1f} move 15 8"); time.sleep(0.7)
rig("mbtn1 off")
p.wait(timeout=90); os.close(fd)
print("\n".join(log)); print("---"); print(open(SP + "/rigfw_mouse_probe.txt").read())
