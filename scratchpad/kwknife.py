#!/usr/bin/env python3
"""🔪 IS THIS ROW LOAD-BEARING? Break the keyword and see whether its row notices.

Joost ruled 2026-09-13 that every keyword is TIER 0 — no tier established — because
a `SUPPORTED` verdict is ONE AGREEMENT POINT and agreement can be vacuous. This is
the non-vacuity half of what establishing a tier needs: disable a statement's
handler in the BUILT ROM and re-run only its kwsweep row. A row still SUPPORTED
with the handler dead is BLIND, and its keyword's evidence is worth nothing.

⚠️ A KNIFE CAN BE SILENTLY INERT because the plant never happened, and it reports
that the same way a keyword with no defect reports (TODO.md: 13 runners lacked the
guard). So the plant is VERIFIED here: the ROM bytes are read back after writing,
and the run refuses if they are not what was written.

The statement dispatch is a table (`db token / dw handler`), so a knife is a
two-byte write to one entry — no rebuild, and no risk of hitting a handler some
OTHER keyword shares, which is why the table entry is cut and not the handler.
"""
import io, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import knife_guard  # D-KNIFEROM: prove the cut reached the INSTALLED images
ROM = os.path.join(ROOT, "build", "zerobas-main-eu.rom")
SYM = os.path.join(ROOT, "build", "basic-reloc.sym")

def syms():
    out = {}
    for line in io.open(SYM, errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out

def token_of(name):
    """The token byte for a statement keyword, from sysvars.inc's own equate."""
    src = io.open(os.path.join(ROOT, "basic", "sysvars.inc"), encoding="utf-8").read()
    m = re.search(r"^%s_TOKEN\s+equ\s+\$([0-9A-Fa-f]+)" % name, src, re.M)
    if not m:
        sys.exit(f"knife: no {name}_TOKEN equate — nothing was measured")
    return int(m.group(1), 16)

def plant(tok, dead):
    """Point the statement's table entry at `dead`. Returns (offset, original)."""
    s = syms()
    base = s["stmt_table"]
    rom = bytearray(io.open(ROM, "rb").read())
    for i in range(0, 3 * 120, 3):
        if rom[base + i] == tok:
            off = base + i + 1
            orig = bytes(rom[off:off + 2])
            rom[off] = dead & 0xFF
            rom[off + 1] = dead >> 8
            io.open(ROM, "wb").write(bytes(rom))
            # 🔴 READ IT BACK: an unplanted knife and a keyword with no defect
            # report identically, so the plant is proved before the run.
            back = io.open(ROM, "rb").read()[off:off + 2]
            if back != bytes([dead & 0xFF, dead >> 8]):
                sys.exit("knife: the plant did NOT take — nothing was measured")
            return off, orig
    sys.exit(f"knife: token ${tok:02X} is not in stmt_table — nothing was measured")

def install(before=None):
    """Re-install, and PROVE the images moved when a cut is in place.

    🔴 Verifying the bytes I wrote is not enough: the probe reads the INSTALLED
    machine, and an install that silently did not happen reports exactly like a
    keyword with nothing to find. `knife_guard.hashes()` is the shared
    implementation the tree already uses for this, and `knife-guard-check` refuses
    a runner that invokes repack-machine without it -- it refused THIS one, and was
    right [[a-knife-can-be-inert-because-the-build-did-not-happen]]."""
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "install-repack-machine.py"),
                    "--merged", ROM, "--disk-rom", os.path.join(ROOT, "build", "disk.rom"),
                    "--sub-rom", os.path.join(ROOT, "build", "sub.rom")],
                   check=True, capture_output=True)
    after = knife_guard.hashes()
    if before is not None and not knife_guard.moved(before, after):
        sys.exit("knife: the installed images did NOT move -- nothing was measured")
    return after

def run_row(row):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "probes", "basic", "basic_probe_kwsweep.py"),
                        "--zb-machine", "C-BIOS_MSX1_EU_REPACK_DISK", "--only", row],
                       capture_output=True, text=True)
    for line in r.stdout.split("\n"):
        if line.startswith(("SUPPORTED", "DIVERGENT", "MISSING", "SILENT-GAP", "UNREADABLE")):
            return line.split()[0]
    return "NO-VERDICT"

TARGETS = [("POKE", "poke"), ("VPOKE", "vpoke"), ("SOUND", "sound"),
           ("RESTORE", "restorekw"), ("ERASE", "erase"), ("SWAP", "swapctl")]
if len(sys.argv) > 1:
    TARGETS = [tuple(a.split(":")) for a in sys.argv[1:]]

dead = syms()["stmt_error"]
print("knife: statement handlers -> stmt_error $%04X; a row still SUPPORTED is BLIND\n" % dead)
for kw, row in TARGETS:
    tok = token_of(kw)
    before = knife_guard.hashes()
    off, orig = plant(tok, dead)
    try:
        install(before)
        v = run_row(row)
    finally:
        rom = bytearray(io.open(ROM, "rb").read())
        rom[off:off + 2] = orig
        io.open(ROM, "wb").write(bytes(rom))
        install()
    flag = "LOAD-BEARING" if v != "SUPPORTED" else "🔴 BLIND"
    print("  %-8s row %-10s knifed -> %-12s %s" % (kw, row, v, flag))
    sys.stdout.flush()
