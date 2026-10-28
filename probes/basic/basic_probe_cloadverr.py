#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""CLOAD? mismatch is ERROR 20 (gate: cloadverr-acceptance; Joost 2026-10-27: "Measure
first, then decide" -- the err_verify item). On the VG-8020 a CLOAD? that does not
match the program in memory prints `Verify error` AND sets ERR: `PRINT ERR` reads 20
(scratchpad/cloadverr_run.out). zerobas printed the text through print_msg and left ERR
at 0; sub2/tapeprog.asm's ctp_verify_error now raises 20.

Our own program (`10 POKE&HD0FF,&H98`) and our own tokenised tape of a one-byte-
different program (basic_probe_cas_verify.py's B2 fixture), CLOAD? in direct mode,
then `PRINT "E";ERR`. Both machines; typed keys in, the text screen out.
🔴 NOT basic_probe_cas_verify.run_typed_scr: that one starts with `pkill -9 openmsx`,
which would kill every other suite's emulator in a parallel battery. This launches
its own and kills only its own process group.
Prints `ROW cloadverr VG=[...] ZB=[...] <SAME|DIVERGES>`; exit 0 agree, 1 a divergence,
2 the reference gave no reading.
"""
import os, re, shutil, signal, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "disk"))
# 🔴 NOT `import basic_probe_cas_verify`: tools/check_no_hostkill.py follows imports, and
# that module carries `pkill -9 openmsx` (it RAN red on 2026-10-28). Its B2 fixture is
# four lines, restated here; the builders come from the shared libraries it uses too.
from cas_encode import build_cas_basic      # noqa: E402
from bas_tokenise import make_multiline_program  # noqa: E402
from omsx_run import _tcl_dquote            # noqa: E402
import omsx_preflight                       # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
TXTBASE, WITNESS = 0x8001, 0xD0FF
MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))
KEYS = [(6.0, f"10 POKE&H{WITNESS:04X},&H98"), (9.0, "\r"),          # memory POKEs $98
        (12.0, "CLOAD?"), (14.0, "\r"), (34.0, 'PRINT "E";ERR'), (36.0, "\r")]


def prog(val):
    return make_multiline_program([(10, f"POKE&H{WITNESS:04X},&H{val:02X}")], TXTBASE)


def run(machine, cas, cap_time=40.0, timeout=110.0):
    out = tempfile.mktemp(suffix=".txt", prefix="cloadverr_")
    lines = ["set throttle off", "set renderer none; set sound_driver null"]
    lines += [f"after time {d} {{ type {_tcl_dquote(t)} }}" for d, t in KEYS]
    lines += ["proc cap {} {", f"  set f [open {{{out}}} w]",
              "  binary scan [debug read_block {VRAM} 0x0000 960] H* h0; puts $f \"s0=$h0\"",
              "  close $f; exit }", f"after time {cap_time} {{ cap }}"]
    tcl = out + ".tcl"
    open(tcl, "w").write("\n".join(lines) + "\n")
    p = subprocess.Popen(omsx_preflight.guarded([OMSX, "-machine", machine, "-cassetteplayer", cas,
                                                 "-script", tcl]),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    dl = time.time() + timeout
    while p.poll() is None and time.time() < dl:
        time.sleep(0.1)
    if p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    if not os.path.exists(out):
        return None
    v = open(out).read().strip().partition("=")[2]
    scr = re.sub(r"\s+", " ", "".join(chr(c) if 32 <= c < 127 else " " for c in bytes.fromhex(v)))
    m = re.search(r"(Verify error).*?PRINT \"E\";ERR (E \d+)", scr)
    return f"{m.group(1)} | {m.group(2)}" if m else scr[-60:].strip()


def main():
    tmp = tempfile.mkdtemp(prefix="cloadverr_")
    cas = os.path.join(tmp, "v_diff.cas")
    open(cas, "wb").write(build_cas_basic("V", prog(0x99)))         # the tape POKEs $99
    got = {side: run(m, cas) for side, m in MACHINES}
    if not got["VG"]:
        print(f"ROW cloadverr VG=<none> ZB=[{got['ZB']}] NO-REFERENCE")
        return 2
    v = "SAME" if got["VG"] == got["ZB"] else "DIVERGES"
    print(f"ROW cloadverr VG=[{got['VG']}] ZB=[{got['ZB']}] {v}")
    return 0 if v == "SAME" else 1


if __name__ == "__main__":
    sys.exit(main())
