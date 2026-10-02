#!/usr/bin/env python3
"""D-DOSBASIC: what does COMMAND.COM itself read ($8000..$FFFF, reader PC in
$0100..$3FFF) while it starts, banner to prompt -- on both machines? On the
CF-3300 the ADDRESS and PC only (no values: §8.5); on ours the value too.
An address only stock reads, or one ours reads with a telling value, is where
'BASIC available?' would come from."""
import collections, os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
got = {}
# windows: the banner appears / the prompt is up (stock 11..12.2 s, from
# stock_timeline.py; ours from its own screen dumps: banner by ~12, prompt ~13.5)
for tag, machine, t0, t1 in (("STOCK", RT.REF_MACHINE, 10.8, 12.3), ("OURS", RT.OUR_MACHINE, 7.5, 9.5)):
    dsk = probe_tmp.tmp(f"cmdinit_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    out = probe_tmp.tmp(f"cmdinit_{tag}.log")
    val = "[format %02X [debug read memory $::wp_last_address]]" if tag == "OURS" else "--"
    tcl = (f"set wf [open {{{out}}} w]\n"
           "proc wcb {} { global wf; if {[reg PC] >= 0x0100 && [reg PC] < 0x4000 && ![pc_in_slot 0 0]} { "
           "puts $wf \"[format %.4f [machine_info time]] [format %04X $::wp_last_address] "
           + val + " [format %04X [reg PC]]\" } }\n"
           f"after time {t0} {{ set ::wid [debug set_watchpoint read_mem {{0x8000 0xFFFF}} {{}} wcb] }}\n"
           f"after time {t1} {{ debug remove_watchpoint $::wid; close $wf }}\n")
    W.run_once(machine, dsk, 30, t1 + 0.5, 900, cmd="", extra_tcl=tcl)
    agg = collections.OrderedDict()
    for ln in open(out):
        t, a, v, pc = ln.split()
        e = agg.setdefault(a, [t, 0, set(), pc])
        e[1] += 1
        e[2].add(v)
    got[tag] = agg
    print(f"{tag}: {sum(e[1] for e in agg.values())} COMMAND.COM reads over {len(agg)} addresses")
s, o = got["STOCK"], got["OURS"]
print("\naddresses COMMAND.COM reads on the CF-3300 but NOT on ours:")
for a, (t, n, _, pc) in s.items():
    if a not in o and not (0x8000 <= int(a, 16) < 0xC000):
        print(f"  ${a}  t={t} n={n} pc=${pc}")
print("\naddresses COMMAND.COM reads on OURS but not on the CF-3300 (with ours' values):")
for a, (t, n, vals, pc) in o.items():
    if a not in s and not (0x8000 <= int(a, 16) < 0xC000):
        print(f"  ${a}  t={t} n={n} pc=${pc} values={','.join(sorted(vals))[:20]}")
