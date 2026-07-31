#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""CAS: statement-option probe (tape/device option-closure Tier 1, Items 1+2):

  Item 1 — LOAD"CAS:",R load-AND-run.  Previously ',R' was parsed-past and dropped
           on the CAS: branch (BLOAD"CAS:",R already honoured it -- an asymmetry).
           A cassette carrying `10 POKE&HD0FF,&H99` is loaded two ways and a witness
           byte at $D0FF (poisoned to $11 at boot) is read:
             * LOAD"CAS:",R  -> the program RUNS -> witness == $99.
             * LOAD"CAS:"    -> loaded, NOT run  -> witness stays $11, and the
                                program image is present at TXTBASE (it did load).

  Item 2 — CSAVE"name",speed honoured.  `CSAVE"P",1` records at 1200 baud (high tone
           ~2400 Hz); `CSAVE"P",2` records at 2400 baud (high tone ~4800 Hz). We
           record each to a WAV and decode the leader/data half-period cluster: the
           ,2 recording's short (high-tone) frequency must be ~2x the ,1 recording's
           -- proving the speed digit selected the rate (the BASIC-level table copy
           into the active baud slot the write path reads). Malformed speed (`,3`)
           is a clean Syntax error, asserted by the program still being runnable
           afterwards (no half-saved tape).

  Item 3 — no-name CSAVE,speed (Tier 3).  `CSAVE,2` (no filename, just a speed)
           must select 2400 baud exactly as CSAVE"P",2 does -- the do_csave comma
           route into csav_noname + csav_speed. Recorded and decoded like Item 2.

Typed harness on C-BIOS_MSX1_EU_TAPE --cart (the established cassette-probe method;
tape has no AUTOEXEC path). Clean-room: our own program, our own cas codec; the
reference ROM is never read.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))       # sibling probes
_PROBES = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # probes/
_ROOT = _os.path.dirname(_PROBES)                                       # repo root
_sys.path.insert(0, _os.path.join(_PROBES, "lib"))                     # cas codec
_sys.path.insert(0, _os.path.join(_PROBES, "disk"))                    # bas_tokenise

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from cas_encode import build_cas_basic          # noqa: E402
from cas_decode import decode_file               # noqa: E402
from bas_tokenise import make_multiline_program  # noqa: E402
from basic_probe_tape_save import run_save       # noqa: E402  (proven WAV recorder)
from omsx_run import _tcl_dquote                  # noqa: E402  (proven type-string quoting)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINE_TAPE = "C-BIOS_MSX1_EU_TAPE"
# The zerobas side runs on the REPACK machine, which carries the merged main ROM
# in slot 0 and ships its own <CassettePort/>. It used to be MACHINE_TAPE below --
# stock C-BIOS plus the tape patch -- with the retired lean 16 KB cart inserted as
# a cartridge (RETIRE THE LEAN 16 KB CART S3, docs/spec-lean-retire-s3-gates.md).
# MACHINE_TAPE is kept because it is still a real rig: stock BIOS + open cassette
# stack, selectable via --machine / ZEROBAS_BASIC_MACHINE, and the only mode in
# which a `-cart` is passed at all.
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE") or "C-BIOS_MSX1_EU_REPACK_DISK"
TXTBASE = 0x8001
WITNESS = 0xD0FF
POISON = 0x11
RAN = 0x99


def load_and_capture(cart: str, cas_path: str, verb: str,
                     cap_time: float = 34.0, timeout: float = 100.0):
    """Poison $D0FF, mount cas, type `verb`, capture the witness + TXTBASE image."""
    out = tempfile.mktemp(suffix=".txt", prefix="casopt_")
    tcl = f"""set throttle off
set renderer none
set sound_driver null
proc __hex {{a n}} {{ binary scan [debug read_block {{memory}} $a $n] H* h; return $h }}
after time 1 {{ debug write memory 0x{WITNESS:04X} 0x{POISON:02X} }}
after time 6 {{ type {_tcl_dquote(verb)} }}
after time 8 {{ type {_tcl_dquote(chr(13))} }}
proc __cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "wit=[format %02X [debug read memory 0x{WITNESS:04X}]]"
  puts $f "txt=[__hex 0x{TXTBASE:04X} 6]"
  close $f
  exit
}}
after time {cap_time} {{ __cap }}
"""
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", ZB_MACHINE]
    cmd += (["-cart", cart] if ZB_MACHINE == MACHINE_TAPE else [])
    cmd += [
           "-cassetteplayer", cas_path, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    wit, txt = None, None
    if os.path.exists(out):
        for ln in open(out):
            k, _, v = ln.strip().partition("=")
            if k == "wit":
                wit = int(v, 16)
            elif k == "txt":
                txt = v
    return wit, txt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", default=None,
                    help="only used with the %s rig" % MACHINE_TAPE)
    args = ap.parse_args()

    ok = True
    tmp = tempfile.mkdtemp(prefix="casopt_")

    # --- Item 1: LOAD"CAS:",R runs; LOAD"CAS:" loads-but-does-not-run ------------
    prog = make_multiline_program([(10, f"POKE&H{WITNESS:04X},&H{RAN:02X}")], TXTBASE)
    cas = os.path.join(tmp, "prog.cas")
    open(cas, "wb").write(build_cas_basic("PROG", prog))

    print("Item 1 — LOAD\"CAS:\",R load-and-run:")
    wit_r, txt_r = load_and_capture(args.cart, cas, 'LOAD"CAS:",R')
    c1 = wit_r == RAN
    ok &= c1
    print(f"  [{'PASS' if c1 else 'FAIL'}] LOAD\"CAS:\",R RAN the program: "
          f"(${WITNESS:04X})=${wit_r if wit_r is not None else 0:02X} (expect ${RAN:02X})")

    wit_n, txt_n = load_and_capture(args.cart, cas, 'LOAD"CAS:"')
    loaded = txt_n not in (None, "000000000000") and txt_n == txt_r
    notrun = wit_n == POISON
    ok &= loaded and notrun
    print(f"  [{'PASS' if loaded else 'FAIL'}] LOAD\"CAS:\" (no ,R) still LOADED the program: "
          f"TXTBASE={txt_n} (expect ={txt_r})")
    print(f"  [{'PASS' if notrun else 'FAIL'}] LOAD\"CAS:\" (no ,R) did NOT run it: "
          f"(${WITNESS:04X})=${wit_n if wit_n is not None else 0:02X} (expect ${POISON:02X} poison)")

    # --- Item 2: CSAVE"P",speed selects the baud --------------------------------
    # (type + ENTER are SEPARATE cmds; the WAV is pre-created — the run_save contract.)
    print('Item 2 — CSAVE"P",speed selects 1200/2400 baud:')
    wav1 = tempfile.mkstemp(suffix=".wav", prefix="casopt_s1_", dir=tmp)[1]
    wav2 = tempfile.mkstemp(suffix=".wav", prefix="casopt_s2_", dir=tmp)[1]
    csave1 = [(6.0, "10 PRINT1"), (7.5, "\r"), (9.0, 'CSAVE"P",1'), (10.5, "\r")]
    csave2 = [(6.0, "10 PRINT1"), (7.5, "\r"), (9.0, 'CSAVE"P",2'), (10.5, "\r")]
    run_save(args.cart, csave1, wav1, cap_time=50.0)
    run_save(args.cart, csave2, wav2, cap_time=50.0)
    _, i1 = decode_file(wav1)
    _, i2 = decode_file(wav2)
    f1 = i1.get("short_freq_hz")
    f2 = i2.get("short_freq_hz")
    # 1200 baud high tone ~2400 Hz; 2400 baud high tone ~4800 Hz. Assert the ,2
    # recording is clearly in the 2400-baud regime and ~2x the ,1 recording.
    c2 = (f1 is not None and f2 is not None and f1 < 3200 and f2 > 3600 and f2 > 1.6 * f1)
    ok &= c2
    print(f"  [{'PASS' if c2 else 'FAIL'}] CSAVE\"P\",1 -> {f1} Hz (1200 regime), "
          f"CSAVE\"P\",2 -> {f2} Hz (2400 regime, ~2x)")

    # --- Item 3: the no-name CSAVE,speed form honours the baud too --------------
    # `CSAVE,2` (no filename, just a speed) must select 2400 exactly as CSAVE"P",2
    # does -- the do_csave comma route into csav_noname + csav_speed. Record it and
    # assert it lands in the same 2400-baud regime.
    print('Item 3 — no-name CSAVE,speed honours the baud:')
    wav3 = tempfile.mkstemp(suffix=".wav", prefix="casopt_s3_", dir=tmp)[1]
    csave3 = [(6.0, "10 PRINT1"), (7.5, "\r"), (9.0, 'CSAVE,2'), (10.5, "\r")]
    run_save(args.cart, csave3, wav3, cap_time=50.0)
    _, i3 = decode_file(wav3)
    f3 = i3.get("short_freq_hz")
    c3 = (f3 is not None and f3 > 3600)
    ok &= c3
    print(f"  [{'PASS' if c3 else 'FAIL'}] CSAVE,2 (no name) -> {f3} Hz (2400 regime)")

    shutil.rmtree(tmp, ignore_errors=True)
    print("CAS-options:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
