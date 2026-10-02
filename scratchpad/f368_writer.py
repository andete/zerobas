"""D-DOSBASIC: who writes $F368..$F36A (the hook COMMAND.COM's BASIC handler
calls first; stock's jumps to $DF57, ours is a bare RET)? A write watchpoint
from boot, logging the time, the address and the WRITER's PC and slot flags --
never the value (§8.5). Both machines."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"f368w_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    out = probe_tmp.tmp(f"f368w_{tag}.log")
    tcl = (f"set wf [open {{{out}}} w]\n"
           "proc wcb {} { global wf; puts $wf \"[format %.4f [machine_info time]] "
           "[format %04X $::wp_last_address] pc=[format %04X [reg PC]] "
           "slot0=[pc_in_slot 0 0] s31=[pc_in_slot 3 1]\"; flush $wf }\n"
           "set ::wid [debug set_watchpoint write_mem {0xF368 0xF36A} {} wcb]\n"
           "after time 13 { close $wf }\n")
    W.run_once(machine, dsk, 30, 13.5, 600, cmd="", extra_tcl=tcl)
    print(f"== {tag}")
    for ln in open(out):
        print("  " + ln.rstrip())
