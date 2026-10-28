#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""err_verify / brk_msg (Joost 2026-10-27: "Measure first, then decide"): after a
CLOAD? mismatch, what does ERR hold? `Verify error` is printed by verify_error
(basic/cload.asm) with no ERRFLG store; adding one would move the message out of
main ROM but also make PRINT ERR read the code -- so the reference decides.

Our own program and our own tape (basic_probe_cas_verify.py's B2: memory POKEs $98,
the tokenised tape $99), then `PRINT "E";ERR` in direct mode. VG-8020 and zerobas.
Typed keys in, the text screen out. ⚠️ run_typed_scr pkills openmsx first: run ALONE.
    python3 -u scratchpad/cloadverr_probe.py
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_cas_verify as V  # noqa: E402

for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
    V.ZB_MACHINE = m
    tmp = tempfile.mkdtemp(prefix="cloadverr_")
    cas = os.path.join(tmp, "v_diff.cas")
    open(cas, "wb").write(V.build_cas_basic("V", V.prog(V.RAN)))
    scr, _ = V.run_typed_scr(None, cas, V.type_prog(0x98) +
                             [(12.0, "CLOAD?"), (14.0, "\r"),
                              (34.0, 'PRINT "E";ERR'), (36.0, "\r")], cap_time=40.0)
    print(f"{m:28s} ...{scr[-120:].strip()}", flush=True)
