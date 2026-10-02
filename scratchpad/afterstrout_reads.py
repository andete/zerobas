#!/usr/bin/env python3
"""D-DOSBASIC: between the STROUT of the command buffer returning and the next
event (stock: ENASLT into BASIC at 12.6584 s; ours: COMMAND.COM's reload at
14.49 s), what does COMMAND.COM's transient code (PC $C000..$D5FF) read
anywhere in RAM? The same code runs on both, so the branch rests on data.
Stock: ADDRESS and PC only (§8.5); ours: the value too. Stack reads dropped."""
import collections, os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
got = {}
for tag, machine, t0, t1 in (("STOCK", RT.REF_MACHINE, 12.6575, 12.6600), ("OURS", RT.OUR_MACHINE, 14.4370, 14.4900)):
    dsk = probe_tmp.tmp(f"as_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "AUTOEXEC", "BAT", b"BASIC\r\n")
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"as_{tag}.log")
    val = "[format %02X [debug read memory $::wp_last_address]]" if tag == "OURS" else "--"
    tcl = (f"set wf [open {{{out}}} w]\n"
           "proc wcb {} { global wf; set pc [reg PC]; if {$pc >= 0xC000 && $pc < 0xD600 && "
           "($::wp_last_address < [reg SP] - 0x20 || $::wp_last_address > [reg SP] + 0x20) && "
           "($::wp_last_address < $pc - 4 || $::wp_last_address > $pc + 4)} { "
           "puts $wf \"[format %.6f [machine_info time]] [format %04X $::wp_last_address] " + val +
           " [format %04X $pc]\" } }\n"
           f"after time {t0} {{ set ::wid [debug set_watchpoint read_mem {{0x0000 0xFFFF}} {{}} wcb] }}\n"
           f"after time {t1} {{ debug remove_watchpoint $::wid; close $wf }}\n")
    W.run_once(machine, dsk, 14, t1 + 0.5, 900, cmd="BASIC", extra_tcl=tcl)
    rows = [ln.split() for ln in open(out) if ln.strip()]
    got[tag] = rows
    print(f"== {tag} ({t0}..{t1} s): {len(rows)} reads by COMMAND.COM's transient code")
    seen = set()
    for t, a, v, pc in rows:
        if a in seen:
            continue
        seen.add(a)
        print(f"  {t}  ${a}  {v}  pc=${pc}")
