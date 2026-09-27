#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""SOUND acceptance — VG-8020 differential (docs/spec-basic-audio-play.md, Slice 1).

Two halves, both black-box against the Philips VG-8020 reference (no disassembly;
the reference ROM is a black box — CONTRIBUTING.md clean-room firewall):

  1. ERROR SURFACE — give SOUND out-of-range / out-of-domain register+value args
     and check the trapped ERR matches the reference. The reference SOUND accepts
     registers 0..13 only (14..255 -> Illegal function call, ERR 5 — the draft
     spec's "14/15 silently masked" was WRONG); the register+value coercion is the
     D-F2-2 byte domain (>int16 -> Overflow ERR 6; in-int16 but >255/negative ->
     ERR 5). Same KEYBUF-inject `run()` as basic_probe_intarg.py.

  2. PSG REGISTER WRITE — run `SOUND reg,value` on a fresh boot, then read the
     openMSX "PSG regs" debuggable and compare the TARGET register's resulting
     byte between zerobas and the reference. Registers 0..6, 8..13 take the whole
     value byte; register 7 (mixer) keeps its top two I/O-direction bits from the
     current R7 and takes only bits 0..5 from the value (R7' = (curR7 & C0) |
     (val & 3F)). Only the WRITTEN register is compared — the untouched envelope
     registers differ at boot between C-BIOS-repack and the real BIOS (a GICINI
     boot-state difference, not a SOUND defect), so a full-block compare would
     false-fail.

Heavy + oracle-dependent (boots openMSX per case; needs your VG-8020 reference
ROM). Scope with `--only <substr>`. The emulator-free fast layer is
tests/test_sound.py under `make unit-test`."""
from __future__ import annotations
import argparse, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
OMSX_RUN = os.path.join(os.path.dirname(__file__), "..", "lib", "omsx_run.py")

# The repack machine boots slower (disk ROM scan + zerobas init) than the real
# VG-8020, so its keyboard injection must land later. Pair delay/time per machine.
BOOT = {  # machine -> (type_delay, run_time) seconds of emulated time
    REF_MACHINE: (4.0, 7.0),
}
DEFAULT_BOOT = (9.0, 13.0)  # repack / anything else

# --- ERROR SURFACE (differential; want == reference == zerobas) ----------------
ERR_CASES = [
    ("reg_ok",     "SOUND 0,255",   "cont"),   # reg 0, value 255 -> ok
    ("reg_13",     "SOUND 13,15",   "cont"),   # reg 13 (envelope shape) -> ok
    ("reg_14",     "SOUND 14,0",    "ERR5"),   # reg 14 (PSG I/O port) -> Illegal fn call
    ("reg_15",     "SOUND 15,0",    "ERR5"),   # reg 15 (PSG I/O port) -> Illegal fn call
    ("reg_16",     "SOUND 16,0",    "ERR5"),   # reg >13 -> Illegal fn call
    ("reg_255",    "SOUND 255,0",   "ERR5"),   # reg 255 (<=byte) -> Illegal fn call
    ("reg_256",    "SOUND 256,0",   "ERR5"),   # reg >255, <=int16 -> ERR5
    ("reg_neg",    "SOUND -1,0",    "ERR5"),    # negative reg -> ERR5
    ("reg_ovf",    "SOUND 99999,0", "ERR6"),   # reg >int16 -> Overflow
    ("val_255",    "SOUND 0,255",   "cont"),   # value 255 -> ok
    ("val_256",    "SOUND 0,256",   "ERR5"),   # value >255, <=int16 -> ERR5
    ("val_neg",    "SOUND 0,-1",    "ERR5"),    # negative value -> ERR5
    ("val_ovf",    "SOUND 0,99999", "ERR6"),   # value >int16 -> Overflow
]

# --- PSG REGISTER WRITE (differential; the written register's byte must match) --
# (label, statement, register-index-written)
PSG_CASES = [
    ("r0_ff",   "SOUND 0,255",  0),
    ("r1_2a",   "SOUND 1,42",   1),
    ("r6_1f",   "SOUND 6,31",   6),
    ("r7_ff",   "SOUND 7,255",  7),   # mixer: top 2 bits preserved -> low 6 = 3F
    ("r7_c0",   "SOUND 7,192",  7),   # value 192 (11000000): its top 2 bits dropped
    ("r8_ff",   "SOUND 8,255",  8),   # amplitude A (full byte stored)
    ("r13_ff",  "SOUND 13,255", 13),  # envelope shape (full byte)
    # 🔴 D-SNDVAR (2026-09-27): every row above is a LITERAL, and ex_sound kept the
    # register in C across the value's eval -- which only a literal leaves alone.
    # A variable value wrote nowhere near R8 (zerobas R8 = 0, the VG-8020 12;
    # scratchpad/sndvar_probe.py). These three are the rows that can see it.
    ("r8_var",  "V=12:SOUND 8,V",     8),   # value from a variable
    ("r8_rv",   "R=8:V=13:SOUND R,V", 8),   # register AND value from variables
    ("r7_var",  "V=63:SOUND 7,V",     7),   # the mixer's masked path, by variable
]


def run(machine, stmt):
    """ERROR-surface capture: 'ERR<n>' (trapped) or 'cont' (ran on)."""
    prog = ["10 ON ERROR GOTO 100", f"20 {stmt}",
            "30 PRINTCHR$(67);CHR$(35):END", "100 PRINTCHR$(35);ERR;CHR$(35)", "RUN"]
    raw = omsx_repl.run_case(machine, "direct", prog) or ""
    e = re.findall(r"#([^#]*)#", raw)
    if e:
        return f"ERR{e[-1].strip()}"
    return "cont" if "C#" in raw else f"?({re.sub(r'\s+', ' ', raw).strip()[-30:]!r})"


def psg_after(machine, stmt):
    """Boot `machine`, type `stmt`+Enter, return the 14 PSG register bytes (a list
    of ints R0..R13) read from the openMSX 'PSG regs' debuggable, or None."""
    delay, secs = BOOT.get(machine, DEFAULT_BOOT)
    with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False) as f:
        out = f.name
    try:
        cmd = [sys.executable, OMSX_RUN, "--machine", machine,
               "--type", stmt + "\r", "--type-delay", str(delay),
               "--time", str(secs), "--mem", "PSG regs:0:14", "--out", out]
        # 🔴 KEEP THE SUB-RUN'S OWN WORDS. Discarding stderr and then reading a
        # file that may not exist turned every failure into the SAME misleading
        # traceback -- see the `finally` below.
        r = subprocess.run(omsx_preflight.guarded(cmd), capture_output=True,
                           text=True)
        if not os.path.exists(out):
            sys.stderr.write(
                f"\n--- {OMSX_RUN} wrote no capture (rc={r.returncode}) ---\n"
                + ((r.stderr or r.stdout or "").strip()[-1500:] or
                   "(and it said nothing)") + "\n")
            return None
        with open(out) as fh:
            for line in fh:
                m = re.search(r"mem\.PSG regs:0x0000:14=([0-9a-f]+)", line)
                if m:
                    b = bytes.fromhex(m.group(1))
                    return list(b) if len(b) == 14 else None
    finally:
        # 🔴 THE CLEANUP MUST NOT REPLACE THE FAILURE (2026-09-02). A bare
        # `os.unlink` here raised FileNotFoundError out of the `finally` and
        # MASKED the real exception, so a run that produced no capture reported
        # itself as a missing temp file during teardown -- a traceback pointing
        # at the one line that was never the problem. Seen live as a
        # "recovered flake" on sound-acceptance.
        # 🎯 Same lesson as D-PASMOSAY: when PASS is "nothing happened", spend
        # the evidence the run already holds instead of throwing it away.
        try:
            os.unlink(out)
        except OSError:
            pass
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    args = ap.parse_args()
    ok = True

    print("--- SOUND error surface (differential vs VG-8020) ---")
    for label, stmt, want in ERR_CASES:
        if args.only and args.only not in label:
            continue
        ref = run(args.machine, stmt)
        zb = run(args.zb_machine, stmt)
        good = (zb == want) and (ref == want)
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} {label:10} {stmt:16} "
              f"zb={zb:7} ref={ref:7} want={want}")

    print("\n--- SOUND PSG register write (differential vs VG-8020) ---")
    for label, stmt, reg in PSG_CASES:
        if args.only and args.only not in label:
            continue
        ref = psg_after(args.machine, stmt)
        zb = psg_after(args.zb_machine, stmt)
        rv = ref[reg] if ref else None
        zv = zb[reg] if zb else None
        good = rv is not None and zv is not None and rv == zv
        ok = ok and good
        rvs = f"{rv:02x}" if rv is not None else "??"
        zvs = f"{zv:02x}" if zv is not None else "??"
        print(f"{'PASS' if good else 'FAIL':5} {label:10} {stmt:16} "
              f"R{reg:<2} zb={zvs} ref={rvs}")

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
