"""D-DOSBASIC on OURS: every PC from 14.4527 s (the last DCOMPR before the RST 38h
storm) until the storm, to see where COMMAND.COM's BASIC jumps. PCs are registers;
our own machine. Consecutive PCs are collapsed into runs."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
dsk = probe_tmp.tmp("dosbasic_p.dsk")
shutil.copyfile(RT.DEFAULT_DOS, dsk)
out = probe_tmp.tmp("dosbasic_p.log")
tcl = (f"set pf [open {{{out}}} w]\nset pn 0\n"
       "after time 14.4527 { set ::pid [debug set_condition {1} "
       "{ global pf pn; puts $pf \"[format %04X [reg PC]] [format %04X [reg SP]] C=[format %02X [reg C]] DE=[format %04X [reg DE]] HL=[format %04X [reg HL]]\"; "
       "incr pn; if {$pn >= 20000 || [reg PC] == 0x0038} { debug remove_condition $::pid; flush $pf } }] }\n"
       "after time 14.47 { catch { debug remove_condition $::pid }; flush $pf }\n")
W.run_once(RT.OUR_MACHINE, dsk, 14, 15, 300, cmd="BASIC", extra_tcl=tcl)
rows = [ln.split() for ln in open(out) if ln.strip()]
print(f"{len(rows)} PCs until the first $0038 (or the cap)")
runs = []
for pc, sp, *regs in rows:
    if pc == '0005':
        print('  BDOS call at $0005:', ' '.join(regs))
    p = int(pc, 16)
    if runs and 0 <= p - runs[-1][1] <= 4:
        runs[-1][1] = p
        runs[-1][2] = sp
    else:
        runs.append([p, p, sp])
for a, b, sp in runs[-40:]:
    print(f"  ${a:04X}..${b:04X}  SP={sp}")
