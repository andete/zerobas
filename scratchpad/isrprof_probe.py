"""D-LOADRUNS: what runs between two sector transfers on ZEROBAS (our own ROM; not
for a reference -- PC sampling is only clean-room on our code). From the first
READ command aimed at $8200, sample PC every 0.1 ms for 0.6 s, then print the PCs
by symbol (main + disk symbol tables), and the time spent per symbol.

    python3 -u scratchpad/isrprof_probe.py
"""
import os, sys, collections, bisect
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs as r  # noqa: E402
import probe_tmp  # noqa: E402

dump = probe_tmp.tmp("isrprof.txt")
if os.path.exists(dump):
    os.unlink(dump)
r.GAP_TCL = r.GAP_TCL + """
set ::__pf [open {%s} w]
set ::__on 0
proc __samp {n} {
  puts $::__pf "[format %%.5f [machine_info time]] [format %%04X [reg PC]] [format %%02X [reg iff]] [__rd16 0xFC9E]"
  if {$n > 0} { after time 0.0001 "__samp [expr {$n - 1}]" }
}
proc __fc {} {
  if {!$::__on && [reg hl] == 0x8200 && ($::wp_last_value & 0xE0) == 0x80} { set ::__on 1; __samp 6000 }
  puts $::__pf "[format %%.5f [machine_info time]] CMD [format %%02X $::wp_last_value]"
}
debug set_watchpoint write_mem 0x7FB8 {[pc_in_slot 3]} __fc
""" % dump
text = open(os.path.join(REPO, "scratchpad", "loadspeed_prog.bas")).read()
res = r.run(r.DISK_ZB[0], "isrprof", text, gaps=True)
rows = open(dump).read().splitlines()

def syms(path, lo, hi):
    out = []
    for line in open(path):
        p = line.split()
        if len(p) >= 3 and p[1] == "EQU":
            try:
                v = int(p[2].rstrip("Hh"), 16)
            except ValueError:
                continue
            if lo <= v < hi:
                out.append((v, p[0]))
    return sorted(out)
low = syms(os.path.join(REPO, "build", "basic-reloc.sym"), 0, 0x4000)
dsk = syms(os.path.join(REPO, "build", "disk.sym"), 0x4000, 0x8000)
def name(pc):
    tab = low if pc < 0x4000 else dsk if pc < 0x8000 else None
    if not tab:
        return f"RAM ${pc:04X}"
    i = bisect.bisect_right([v for v, _ in tab], pc) - 1
    return tab[i][1] if i >= 0 else f"${pc:04X}"
cnt = collections.Counter()
for line in rows:
    p = line.split()
    if p[1] != "CMD":
        cnt[name(int(p[1], 16))] += 1
print(res[0])
for k, v in cnt.most_common(40):
    print(f"{v * 0.1:7.1f} ms  {k}")
print("--- timeline (from the first sample, 2500 rows)")
first = next(i for i, l in enumerate(rows) if l.split()[1] != "CMD")
for line in rows[max(0, first - 2):first + 2500]:
    p = line.split()
    print(line if p[1] == "CMD" else f"{p[0]} {p[1]} {name(int(p[1], 16))} iff={p[2]} jiffy={p[3]}")
