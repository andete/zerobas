#!/usr/bin/env python3
"""D-PADSLIDE (2026-11-06): which of disk.rom's still-EMPTY zero pads does anything ENTER?

A `ds $XXXX - $` pad is $00 bytes = NOPs: a caller that jumps into one slides into the
pinned entry after it. MSX-DOS entered $476A..$477C that way, at $4775, never pinned
(D-LOADFAT: scratchpad/hole477_probe.py) -- and a routine moved into that pad broke it.

This lists every empty pad from the assembler's own addresses (a label put before each
pinned `ds` in a temp copy of disk/), writes a TEMPORARY openMSX startup script that arms
a watch ONLY when the env var ZB_PADWATCH is set AND the machine is zerobas's disk
machine (never the reference: the clean-room rule -- our ROM's PC only), runs the given
make targets with it, REMOVES the script, and reports each entry (the lowest PC of a run
with one return address). Page 1 must show the disk ROM (slot 3-1) for a hit to count:
under MSX-DOS page 1 is often RAM, the TPA.

usage: python3 -u scratchpad/padwatch.py [--also=4775-4778] [make-target ...]   (default: the DOS suites)
--also adds a range to the watch: the POSITIVE CONTROL, $4775 (k_4775, the entry MSX-DOS
was measured to use) must show up as an entry under p1dta-acceptance, or the watch is blind.
"""
import glob, os, re, shutil, subprocess, sys, tempfile, collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.expanduser("~/.openMSX/share/scripts/zb_padwatch.tcl")
MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"
TARGETS = ["dosmode-acceptance", "dosdate-acceptance", "strout-acceptance",
           "dosbasic-acceptance", "p1dta-acceptance", "p1vec-acceptance",
           "callsystem-acceptance", "bdos-acceptance", "wrblkalt-acceptance",
           "diskbasic-acceptance"]


def pads():
    T = tempfile.mkdtemp(prefix="padwatch_")
    shutil.copytree(os.path.join(REPO, "disk"), T, dirs_exist_ok=True)
    DS = re.compile(r"\s+ds\s+(\$[0-9A-Fa-f]+)\s*-\s*\$")
    pins, n = {}, 0
    for f in glob.glob(T + "/*.asm"):
        out = []
        for l in open(f).read().split("\n"):
            m = DS.match(l)
            if m:
                n += 1
                pins[f"__PW{n}"] = int(m.group(1)[1:], 16)
                out.append(f"__PW{n}:")
            out.append(l)
        open(f, "w").write("\n".join(out))
    subprocess.run(["pasmo", "-I", T, "--bin", T + "/disk.asm", T + "/t.rom", T + "/t.sym"],
                   cwd=REPO, check=True, capture_output=True)
    sym = {}
    for l in open(T + "/t.sym"):
        m = re.match(r"(\S+)\s+EQU\s+0?([0-9A-F]+)H", l)
        if m:
            sym[m.group(1)] = int(m.group(2), 16)
    rng = sorted((sym[k], v) for k, v in pins.items() if v > sym[k])
    shutil.rmtree(T, ignore_errors=True)
    return rng


def main():
    also = [a for a in sys.argv[1:] if a.startswith("--also=")]
    targets = [a for a in sys.argv[1:] if not a.startswith("--")] or TARGETS
    rng = pads()
    for a in also:
        lo, hi = (int(x, 16) for x in a.split("=", 1)[1].split("-"))
        rng = sorted(rng + [(lo, hi)])
    print(f"{len(rng)} empty pad(s), {sum(b - a for a, b in rng)} B:",
          " ".join(f"${a:04X}-${b - 1:04X}" for a, b in rng))
    # One native BREAKPOINT per pad address, not a Tcl condition: a condition is evaluated
    # on EVERY instruction, and slowed five suites past their wall-clock waits
    # (scratchpad/padwatch_dosmode.out: ZB=[None] on the DIR / MODE rows). A breakpoint is
    # checked by address, and a slide through the NOPs still hits the address it enters at.
    pairs = " ".join(f"0x{a:04X} 0x{b:04X}" for a, b in rng)
    log = os.path.join(tempfile.gettempdir(), "zb_padwatch.log")
    if os.path.exists(log):
        os.remove(log)
    if os.path.exists(SCRIPT):
        sys.exit(f"REFUSED: {SCRIPT} exists -- not ours to overwrite")
    open(SCRIPT, "w").write(f"""# zerobas D-PADSLIDE watch -- TEMPORARY, written and removed by scratchpad/padwatch.py.
# Inert unless ZB_PADWATCH is set, and only on {MACHINE}.
if {{[info exists ::env(ZB_PADWATCH)] && [machine_info config_name] eq "{MACHINE}"}} {{
    set ::zbpw [open $::env(ZB_PADWATCH) a]
    proc zbpw_hit {{}} {{
        if {{[lindex [get_selected_slot 1] 0] == 3 && [lindex [get_selected_slot 1] 1] == 1}} {{
            puts $::zbpw "pc=[format %04X [reg pc]] sp=[format %04X [reg sp]] ret=[format %04X [expr {{[debug read memory [reg sp]] | ([debug read memory [expr {{([reg sp]+1) & 0xFFFF}}]] << 8)}}]]"
            flush $::zbpw
        }}
    }}
    foreach {{a b}} {{{pairs}}} {{
        for {{set x $a}} {{$x < $b}} {{incr x}} {{ debug set_bp $x {{}} zbpw_hit }}
    }}
}}
""")
    rc = {}
    try:
        env = dict(os.environ, ZB_PADWATCH=log)
        for t in targets:
            r = subprocess.run(["make", t], cwd=REPO, env=env, capture_output=True, text=True)
            rc[t] = r.returncode
            out = os.path.join(tempfile.gettempdir(), f"zb_padwatch_{t}.out")
            open(out, "w").write(r.stdout + r.stderr)
            print(f"  {t}: rc={r.returncode}  ({out})", flush=True)
    finally:
        os.remove(SCRIPT)
    print("script removed:", not os.path.exists(SCRIPT))
    hits = [l.split() for l in open(log)] if os.path.exists(log) else []
    print(f"{len(hits)} instruction(s) executed inside an empty pad")
    entries = collections.Counter()
    prev = None
    for h in hits:
        d = dict(x.split("=") for x in h)
        pc = int(d["pc"], 16)
        if not (prev and prev[1] == d["ret"] and pc == prev[0] + 1):
            entries[(d["pc"], d["ret"])] += 1
        prev = (pc, d["ret"])
    for (pc, ret), k in sorted(entries.items()):
        pin = next(b for a, b in rng if a <= int(pc, 16) < b)
        print(f"  ENTRY ${pc}  (return ${ret}) x{k}  -> slides to the pin ${pin:04X}")
    if not entries:
        print("  no entry into any empty pad")
    return 0 if all(v == 0 for v in rc.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
