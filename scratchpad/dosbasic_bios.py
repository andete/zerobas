"""D-DOSBASIC on OURS: after typing BASIC at A>, every hit on the main-ROM BIOS
entry table ($0000..$015F, slot 0) with A, HL, DE, C -- which slot calls and
reads COMMAND.COM makes before it gives up. Registers only, our own machine."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
NAMES = {0x0C: "RDSLT", 0x14: "WRSLT", 0x1C: "CALSLT", 0x24: "ENASLT", 0x30: "CALLF",
         0x9F: "CHGET", 0xA2: "CHPUT", 0x9C: "CHSNS", 0x156: "KILBUF", 0x0159: "CALBAS"}
dsk = probe_tmp.tmp("dosbasic_b.dsk")
shutil.copyfile(RT.DEFAULT_DOS, dsk)
out = probe_tmp.tmp("dosbasic_b.log")
tcl = (f"set bf [open {{{out}}} w]\nset bn 0\n"
       "after time 14.40 { set ::bid [debug set_condition {[pc_in_slot 0 0] && [reg PC] < 0x0160} "
       "{ global bf bn; puts $bf \"[format %.4f [machine_info time]] [format %04X [reg PC]] "
       "A=[format %02X [reg A]] HL=[format %04X [reg HL]] DE=[format %04X [reg DE]] C=[format %02X [reg C]]\"; "
       "incr bn; if {$bn >= 3000} { debug remove_condition $::bid; flush $bf } }] }\n"
       "after time 15.4 { catch { debug remove_condition $::bid }; flush $bf }\n")
W.run_once(RT.OUR_MACHINE, dsk, 14, 16, 300, cmd="BASIC", extra_tcl=tcl)
rows = [ln.split() for ln in open(out) if ln.strip()]
print(f"{len(rows)} BIOS-entry hits")
skip = {"CHGET", "CHPUT", "CHSNS"}
for r in rows:
    pc = int(r[1], 16)
    nm = NAMES.get(pc, f"${pc:04X}")
    if nm in skip:
        continue
    print("  " + " ".join([r[0], nm] + r[2:]))
