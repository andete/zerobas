#!/usr/bin/env python3
"""D-DOSBASIC: anchor on COMMAND.COM's BASIC handler ($D06E -- its own command
table points there on both machines) and log the next 3000 PCs on each, with
the main-ROM-slot flag and SP. Same code on both: the first PC where the runs
part is the branch. Registers only; no bytes of any reference code are read."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
from disk_probe_bdos import fat12_add               # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
traces = {}
for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
    dsk = probe_tmp.tmp(f"d06e_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    img = bytearray(open(dsk, "rb").read())
    fat12_add(img, "AUTOEXEC", "BAT", b"BASIC\r\n")
    open(dsk, "wb").write(img)
    out = probe_tmp.tmp(f"d06e_{tag}.log")
    tcl = (f"set tf [open {{{out}}} w]\nset tn 0\n"
           "after time 5 { set ::aid [debug set_condition {[reg PC] == 0xD06E} "
           "{ debug remove_condition $::aid; set ::sid [debug set_condition {1} "
           "{ global tf tn; puts $tf \"[format %04X [reg PC]] [pc_in_slot 0 0] [format %04X [reg SP]] "
           "A=[format %02X [reg A]] HL=[format %04X [reg HL]]\"; incr tn; "
           "if {$tn >= 3000} { debug remove_condition $::sid; flush $tf } }] }] }\n"
           "after time 30 { flush $tf }\n")
    W.run_once(machine, dsk, 14, 31, 900, cmd="BASIC", extra_tcl=tcl)
    rows = [ln.split() for ln in open(out) if ln.strip()]
    runs = []
    for pc, rom, sp, a, hl in rows:
        p = int(pc, 16)
        if runs and 0 <= p - runs[-1][1] <= 4 and runs[-1][2] == rom:
            runs[-1][1] = p
        else:
            runs.append([p, p, rom, sp, a, hl])
    traces[tag] = runs
    print(f"{tag}: {len(rows)} PCs after $D06E, {len(runs)} runs")
s, o = traces["STOCK"], traces["OURS"]
i = 0
while i < min(len(s), len(o)) and (s[i][0], s[i][1]) == (o[i][0], o[i][1]):
    i += 1
print(f"\nidentical for the first {i} runs; from there:")
for k in range(max(0, i - 6), min(i + 25, max(len(s), len(o)))):
    fs = (f"${s[k][0]:04X}..${s[k][1]:04X} rom={s[k][2]} SP={s[k][3]} {s[k][4]} {s[k][5]}" if k < len(s) else "-")
    fo = (f"${o[k][0]:04X}..${o[k][1]:04X} rom={o[k][2]} SP={o[k][3]} {o[k][4]} {o[k][5]}" if k < len(o) else "-")
    print(f"  {k:3d} {'  ' if k < i else '<>'} STOCK {fs:52} OURS {fo}")
