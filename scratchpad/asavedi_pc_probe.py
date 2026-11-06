# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ASAVEDI: what runs during the long frame-interrupt holes of an ASCII SAVE /
RUN / MERGE on disk. The program-ladder harness with its gap watch (JIFFY writes)
plus a 1 ms sampler of PC, IFF, the primary-slot register and CURLIN; when a gap
over 150 ms ends, the samples taken inside it are written out. zerobas only: the
PCs are named against OUR builds' symbols (build/*.sym), never the reference's.
Clean-room: registers, I/O state and work-area RAM only.

    python3 -u scratchpad/asavedi_pc_probe.py [L5_house]
"""
import collections, os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs as r  # noqa: E402
import probe_tmp  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
name = args[0] if args else "L5_house"
dump = probe_tmp.tmp("asavedi_samples.txt")
if os.path.exists(dump):
    os.unlink(dump)
MINGAP = next((a.split("=")[1] for a in sys.argv if a.startswith("--min=")), "0.15")
r.GAP_TCL = r.GAP_TCL.replace("set ::__gaps {}", """set ::__gaps {}
set ::__smp {}
set ::__df [open {%s} w]
proc __samp {} {
  set st ""
  if {[info exists ::__stk] && $::__stk} {
    set sp [reg SP]
    for {set k 0} {$k < 12} {incr k} { append st " [format %%04X [__rd16 [expr {($sp + 2*$k) & 0xFFFF}]]]" }
  }
  lappend ::__smp "[format %%04X [reg PC]] [reg iff] [format %%02X [debug read ioports 0xA8]] [format %%04X [__rd16 0xF41C]]$st"
  after time 0.001 __samp
}
after time 1 __samp
set ::__stk %d
set ::__all %d""" % (dump, 1 if "--stack" in sys.argv else 0, 1 if "--all" in sys.argv else 0)).replace(
    """    if {$g > 0.03} { lappend ::__gaps [format %.3f $g] }""",
    """    if {$g > 0.03} { lappend ::__gaps [format %.3f $g] }
    if {$g > MINGAP || $::__all} { puts $::__df "GAP [format %.3f $g]"; foreach s $::__smp { puts $::__df $s }; flush $::__df }""").replace(
    """  set ::__jt $t""", """  set ::__jt $t
  if {$::__all && !($run && $::__jrun)} { puts $::__df "GAP 0"; foreach s $::__smp { puts $::__df $s }; flush $::__df }
  set ::__smp {}""")
r.GAP_TCL = r.GAP_TCL.replace("MINGAP", MINGAP)  # --min=S: dump gaps over S s
_pp = os.path.join(REPO, "probes", "programs", name + ".bas")
text = open(_pp if os.path.exists(_pp) else os.path.join(REPO, "scratchpad", name + ".bas")).read()
res = r.run(r.DISK_ZB[0], "asavedi", text, gaps=True)
print(res[0])
syms = []
for f in ("build/basic-reloc.sym", "build/sub.sym", "build/disk.sym"):
    tag = os.path.basename(f).split(".")[0]
    for line in open(os.path.join(REPO, f)):
        p = line.split()
        if len(p) >= 3 and p[1] == "EQU":
            try:
                syms.append((int(p[2].rstrip("H"), 16), p[0], tag))
            except ValueError:
                pass
syms.sort()


def names(pc):
    best = {}
    for a, n, t in syms:
        if a <= pc and (t not in best or a > best[t][0]):
            best[t] = (a, n)
    return " | ".join(f"{t}:{n}+{pc - a}" for t, (a, n) in sorted(best.items()) if pc - a < 0x200)


gaps, cur = [], None
for line in open(dump):
    if line.startswith("GAP"):
        cur = (float(line.split()[1]), [])
        gaps.append(cur)
    elif cur:
        f = line.split()
        pc, iff, a8, cl = f[:4]
        cur[1].append((int(pc, 16), int(iff), a8, cl, f[4:]))
if "--all" in sys.argv:
    every = [x for _, smp in gaps for x in smp]
    by = collections.Counter(x[3] for x in every)
    print("samples by CURLIN:", dict(by.most_common(6)))
    cl = next((a.split("=")[1] for a in sys.argv if a.startswith("--curlin=")), "000A")
    want = [x for x in every if x[3] == cl]
    print(f"\nCURLIN {cl}: {len(want)} samples, IFF=0 in {sum(1 for x in want if x[1] == 0)}")
    for (pc, a8), n in collections.Counter((x[0] & 0xFFF0, x[2]) for x in want).most_common(14):
        print(f"  {n:5d}  PC ~{pc:04X}  A8={a8}  {names(pc)}")
    sys.exit(0)
for g, smp in gaps:
    di = sum(1 for s in smp if s[1] == 0)
    hist = collections.Counter((s[0] & 0xFFF0, s[2]) for s in smp)
    print(f"\nGAP {g:.3f} s: {len(smp)} samples, IFF=0 in {di}; CURLIN {smp[0][3] if smp else '?'}")
    for (pc, a8), n in hist.most_common(8):
        print(f"  {n:4d}  PC ~{pc:04X}  A8={a8}  {names(pc)}")
    if smp and smp[len(smp) // 2][4]:
        print("  stack at the middle sample (each word named against our builds):")
        for w in smp[len(smp) // 2][4]:
            a = int(w, 16)
            print(f"    {w}  {names(a)}")
