"""D-DOSBASIC: which slot BIOS calls (RDSLT $000C, WRSLT $0014, CALSLT $001C,
ENASLT $0024, CALLF $0030) happen from boot to the A> prompt, with A/HL/DE/IY --
on both machines. Registers at the BIOS entry only (call-target + register
observation); no bytes of any ROM or RAM-resident code are read."""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import disk_probe_wrblk_alt as W                    # noqa: E402
import probe_tmp                                    # noqa: E402
NAMES = {0x0C: "RDSLT", 0x14: "WRSLT", 0x1C: "CALSLT", 0x24: "ENASLT", 0x30: "CALLF"}
for tag, machine, t1 in (("STOCK", RT.REF_MACHINE, 12.6), ("OURS", RT.OUR_MACHINE, 14.0)):
    dsk = probe_tmp.tmp(f"dosboot_b_{tag}.dsk")
    shutil.copyfile(RT.DEFAULT_DOS, dsk)
    out = probe_tmp.tmp(f"dosboot_b_{tag}.log")
    tcl = (f"set bf [open {{{out}}} w]\n"
           "after time 2 { set ::bid [debug set_condition "
           "{[reg PC] == 0x000C || [reg PC] == 0x0014 || [reg PC] == 0x001C || [reg PC] == 0x0024 || [reg PC] == 0x0030} "
           "{ global bf; puts $bf \"[format %.4f [machine_info time]] [format %04X [reg PC]] "
           "A=[format %02X [reg A]] HL=[format %04X [reg HL]] DE=[format %04X [reg DE]] "
           "IY=[format %04X [reg IY]] IX=[format %04X [reg IX]] SP=[format %04X [reg SP]]\" }] }\n"
           f"after time {t1} {{ catch {{ debug remove_condition $::bid }}; close $bf }}\n")
    W.run_once(machine, dsk, 30, t1 + 1, 600, cmd="", extra_tcl=tcl)
    rows = [ln.split() for ln in open(out) if ln.strip()]
    print(f"== {tag}: {len(rows)} slot calls, 2 s .. {t1} s")
    for r in rows:
        print("  " + " ".join([r[0], NAMES.get(int(r[1], 16), r[1])] + r[2:]))
