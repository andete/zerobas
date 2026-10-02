#!/usr/bin/env python3
"""D-DOSBASIC: on OURS, type `BASIC` at the A> prompt and log every PC executed in
OUR disk ROM (slot 3-1, pc_in_slot) from just before the keystrokes, mapped to
the nearest label in build/disk.sym. Our own code only: the condition is limited
to our disk ROM's slot, so nothing of the reference's RAM-resident MSXDOS.SYS is
read or logged."""
import bisect, os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402

syms = []
for ln in open(os.path.join(REPO, "build", "disk.sym")):
    parts = ln.split()
    if len(parts) >= 3 and parts[1] == "EQU":
        v = int(parts[2].rstrip("H"), 16)
        if 0x4000 <= v < 0x8000:
            syms.append((v, parts[0]))
syms.sort()
addrs = [a for a, _ in syms]


def label(pc):
    i = bisect.bisect_right(addrs, pc) - 1
    return f"{syms[i][1]}+{pc - syms[i][0]:X}" if i >= 0 else f"${pc:04X}"


dsk = probe_tmp.tmp("dosbasic.dsk")
shutil.copyfile(RT.DEFAULT_DOS, dsk)
out = probe_tmp.tmp("dosbasic.pcs")
tcl = (f"set pf [open {{{out}}} w]\nset n 0\n"
       "after time 13.8 { set ::cid [debug set_condition {[pc_in_slot 3 1]} "
       "{ global pf n; puts $pf \"[format %.4f [machine_info time]] [format %04X [reg PC]]\"; "
       "incr n; if {$n >= 4000} { debug remove_condition $::cid; flush $pf } }] }\n"
       "after time 30 { flush $pf }\n")
W.run_once(RT.OUR_MACHINE, dsk, 14, 32, 300, cmd="BASIC", extra_tcl=tcl)
rows = [ln.split() for ln in open(out) if ln.strip()]
print(f"{len(rows)} disk-ROM PCs logged (cap 4000)")
prev = None
for t, pc in rows:
    lab = label(int(pc, 16)).split("+")[0]
    if lab.startswith(("cinl_", "conout", "pg0_mainrom")):
        continue                      # the line editor echoing the typed keys
    if lab != prev:
        print(f"  {t}  ${pc}  {label(int(pc, 16))}")
        prev = lab
