"""D-ERRKEEP2: where does SAVE's `Disk write protected` go? (zerobas only)

scratchpad/errkeep2_probe.py: `SAVE "X.BAS"` on a write-protected disk traps
ERR 68 on the CF-3300 and reads `ERR 0 ERL 0` on zerobas -- with NOTHING open,
so it is not chan_gate's restore. The driver does detect write protect (FDC
status bit 6 -> DSKIO code 0, disk/driver.asm) and dc_fail maps 0 -> 68
(basic/fat-prim-body.inc). So something between the failing write and main's
disk_error puts 0 back. This watches OUR OWN RAM cell DISKOP_ERR ($E098) on
zerobas's own ROMs and logs every write: the value, the PC, and the primary slot
register so the PC can be named against the right one of our three symbol files.
Only zerobas is traced; nothing of the reference's is read.

    python3 -u scratchpad/wpsave_trace.py
"""
import os, re, stat, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

DISKOP_ERR = 0xE098
ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
BPS = ["ex_save", "fopen_cross", "chan_gate", "cg_unclaimed", "disk_error",
       "load_error", "sav_ascii_flag", "disk_write_begin", "diskslot_test"]
DBPS = ["hk_dpsave", "sav_disk_write"]
PROG = ["NEW", "10 ON ERROR GOTO 90", '30 SAVE "X.BAS":PRINT"[OK]":END',
        '90 PRINT"[";ERR;ERL;"]":END', "RUN"]


def syms(path):
    out = []
    for l in open(path):
        p = l.split()
        if len(p) >= 3 and p[1].upper() == "EQU":
            try:
                out.append((int(p[2].rstrip("Hh"), 16), p[0]))
            except ValueError:
                pass
    return sorted(out)


def near(tab, pc):
    best = None
    for a, n in tab:
        if a <= pc:
            best = (a, n)
        else:
            break
    return f"{best[1]}+{pc - best[0]}" if best and pc - best[0] < 0x400 else "?"


def main():
    img = t._disk_image()
    os.chmod(img, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    log = tempfile.mkstemp(suffix=".log")[1]
    tcl = (f'set ::ek [open "{log}" w]\n'
           f'debug set_watchpoint write_mem 0x{DISKOP_ERR:04X} {{}} '
           '{ puts $::ek "w [format %04X [reg pc]] $::wp_last_value '
           '[format %02X [debug read ioports 0xA8]]"; flush $::ek }\n')
    # breakpoints on OUR OWN main labels along SAVE's path (addresses from our
    # own symbol file); each logs the label and the page-1 slot register
    main_sym = dict((n, a) for a, n in syms(os.path.join(REPO, "build", "basic-reloc.sym")))
    disk_sym = dict((n, a) for a, n in syms(os.path.join(REPO, "build", "disk.sym")))
    for lab in BPS:
        a = main_sym.get(lab)
        if a is not None:
            tcl += (f'debug set_bp 0x{a:04X} {{}} {{ puts $::ek "b {lab} '
                    '[format %02X [debug read ioports 0xA8]]"; flush $::ek }\n')
    for lab in DBPS:
        a = disk_sym.get(lab)
        if a is not None:
            tcl += (f'debug set_bp 0x{a:04X} {{}} {{ puts $::ek "b disk:{lab} '
                    '[format %02X [debug read ioports 0xA8]]"; flush $::ek }\n')
    raw = omsx_repl.run_cases(ZB, [("direct", PROG)], batch=False, reset=("CLS",),
                              boot=8.0, capture="screen", diska=img, step=8.0,
                              cap_gap=20.0, prologue=(tcl,))[0] or ""
    r = re.findall(r"\[[^\]\"]*\]", raw)
    print("reading:", " ".join(r[-1].split()) if r else "NO READING")
    tabs = {n: syms(os.path.join(REPO, "build", f)) for n, f in
            (("main", "basic-reloc.sym"), ("sub", "sub.sym"), ("disk", "disk.sym"))}
    for l in open(log):
        if l.startswith("b "):
            print("  bp", l.split()[1], "A8=" + l.split()[2])
    lines = [l.split() for l in open(log) if l.startswith("w ")]
    print(f"{len(lines)} write(s) to DISKOP_ERR (value, pc, A8, candidates):")
    for _, pc, val, a8 in lines:
        pc = int(pc, 16)
        cands = " | ".join(f"{n}:{near(tb, pc)}" for n, tb in tabs.items())
        print(f"  {int(val):3d}  pc={pc:04X}  A8={a8}  {cands}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
