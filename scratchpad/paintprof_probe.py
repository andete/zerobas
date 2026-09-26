"""T5 profiler: PC samples of zerobas during a SCREEN 2 PAINT flood.

Types `SCREEN 2:LINE(20,20)-(230,170),15,B:PAINT(100,100),15` into the diskless
zerobas machine, samples the Z80 PC and the slot register every 2 ms of
emulated time, and maps each sample to the nearest symbol of OUR OWN ROMs
(build/basic-reloc.sym, build/sub.sym; C-BIOS code is reported as `cbios`).
Found gfx_calc_addr's mask loop (2026-09-26). The tail of the window also
catches the prompt after the fill -- read the graphics routines, not `cbios`.
Clean room: registers and slot state of our own ROM only.
"""
import subprocess, os, bisect, collections, re
SP = os.path.dirname(os.path.abspath(__file__))
ZB = "/Users/joost/projects/zerobas/build"
out = f"{SP}/paintprof.txt"
TCL = f'''
after time 14 {{type "SCREEN 2:LINE(20,20)-(230,170),15,B:PAINT(100,100),15:GOTO 10\\r"}}
set ::f [open "{out}" w]
proc samp {{}} {{
  puts $::f "[format %04X [reg pc]] [format %02X [debug read ioports 0xA8]]"
  if {{[machine_info time] < 30}} {{ after time 0.002 samp }} else {{ close $::f; exit }}
}}
after time 17 samp
'''
open(f"{SP}/paintprof.tcl","w").write(TCL)
subprocess.run(["openmsx","-machine","C-BIOS_MSX1_EU_REPACK_NODISK","-command","set save_settings_on_exit false; set renderer none; set sound_driver null","-script",f"{SP}/paintprof.tcl"],capture_output=True,timeout=300)
def syms(path):
    o=[]
    for l in open(path):
        m=re.match(r"(\S+)\s+EQU\s+0?([0-9A-F]+)H",l)
        if m and not m.group(1).isupper(): o.append((int(m.group(2),16),m.group(1)))
    return sorted(o)
main=syms(f"{ZB}/basic-reloc.sym"); sub=syms(f"{ZB}/sub.sym")
def name(tab,pc):
    i=bisect.bisect_right([a for a,_ in tab],pc)-1
    return tab[i][1] if i>=0 else "?"
c=collections.Counter(); n=0
for l in open(out):
    pc,a8=l.split(); pcv=int(pc,16); page=pcv>>14; slot=(int(a8,16)>>(2*page))&3
    if slot==0:
        w = "cbios" if pcv < 0x2812 and not (0x160<=pcv<0x200 or 0x1ADB<=pcv<0x1BBF) else "main:"+name(main,pcv)
    elif slot==3: w="sub:"+name(sub,pcv)
    else: w="ram"
    c[w]+=1; n+=1
print("samples",n)
for k,v in c.most_common(25): print(f"{v*100/n:5.1f}% {k}")
