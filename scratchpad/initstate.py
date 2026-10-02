"""Ours: the CPU/slot state when the BIOS enters main's cartridge INIT ($4010) at a
normal boot -- what BASENT must recreate. Our own machine only."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
dsk = probe_tmp.tmp("initstate.dsk")
shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)   # a non-system disk: BASIC
out = probe_tmp.tmp("initstate.txt")
tcl = (f"set ::bid [debug set_condition {{[reg PC] == 0x4010 && [pc_in_slot 0 0]}} "
       f"{{ set f [open {{{out}}} a]; puts $f \"t=[format %.4f [machine_info time]] SP=[format %04X [reg SP]] "
       "A8=[format %02X [debug read {ioports} 0xA8]] FFFF=[format %02X [debug read memory 0xFFFF]] "
       "IFF=[reg iff] IM=[reg im] HL=[format %04X [reg HL]] DE=[format %04X [reg DE]]\"; close $f }]\n")
W.run_once(RT.OUR_MACHINE, dsk, 30, 6, 300, cmd="", extra_tcl=tcl)
print(open(out).read() if os.path.exists(out) else "never entered $4010")
