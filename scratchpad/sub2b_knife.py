#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SUB2 stage 2b knives on `make sub2-acceptance` (basic_probe_sub2_ping.py).

K-2B1  both machines installed WITHOUT sub2 (3-3 empty, the pre-D-SUB2 shape).
       Predicted: the four 3-3 rows FAIL (the cell stays $00), 3-2 rows PASS.
       MEASURED (first run): EVERY row reads $FF, SUBSLOT too -- a CALSLT into
       an empty subslot does not return; the runaway overwrites RAM, the
       earlier results with it. A diagnostic on the same machine with only the
       two 3-2 calls read C0 C1 and SUBSLOT $8B: the red is the empty 3-3,
       not a machine that failed to boot. Gate HIT, signature MISS.
K-2B2  sub2's page-0 marker "Z2" -> "ZB", ROM 1's own discovery marker.
       Predicted: discovery records 3-3 ($8F, the later subslot) and the
       SUBSLOT row FAILS on both machines -- the reason sub2 carries "Z2".
       (Unsure: discovery may keep the FIRST hit, in which case only the
       prediction misses and the row stays green -- then "Z2" is defensive,
       not load-bearing, and the docs must say so.)
       MEASURED: SUBSLOT $8F on both -- discovery keeps the LAST hit, so a
       second "ZB" captures it and "Z2" is load-bearing. HIT.
Each cut is built through knife_guard (a cut that did not reach the ROM says
so); the tree is restored and the gate re-run green at the end.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "sub2b_knife")
PROBE = ["python3", "-u", "probes/basic/basic_probe_sub2_ping.py"]
SRC = os.path.join(REPO, "sub2/sub2.asm")
OLD = '                db      "Z2"                    ; $0000: zerobas sub ROM 2 marker\n'
NEW = '                db      "ZB"                    ; $0000: zerobas sub ROM 2 marker\n'


def probe(tag):
    log = f"{TMP}/probe_{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(PROBE, cwd=REPO, stdout=fh, stderr=subprocess.STDOUT,
                             timeout=600)
    rows = [l.rstrip() for l in open(log) if "FAIL" in l or "PASS" in l]
    return rc, rows


def install(with_sub2):
    extra = ["--sub2-rom", "build/sub2.rom"] if with_sub2 else []
    base = ["python3", "tools/install-repack-machine.py", "--merged",
            "build/zerobas-main-eu.rom", "--sub-rom", "build/sub.rom"] + extra
    subprocess.check_call(base + ["--disk-rom", "build/disk.rom"], cwd=REPO,
                          stdout=subprocess.DEVNULL)
    subprocess.check_call(base + ["--no-disk"], cwd=REPO, stdout=subprocess.DEVNULL)


def show(name, rc, rows, pred_red):
    verdict = ("RED" if rc else "GREEN")
    hit = (rc != 0) == pred_red
    print(f"{name}: gate {verdict} (predicted {'RED' if pred_red else 'GREEN'}: "
          f"{'HIT' if hit else 'MISS'})")
    for r in rows:
        if "FAIL" in r:
            print("   " + r)


def main():
    os.makedirs(TMP, exist_ok=True)
    # K-2B1
    install(with_sub2=False)
    try:
        rc, rows = probe("k2b1")
        show("K-2B1 (no sub2 in 3-3)", rc, rows, True)
    finally:
        install(with_sub2=True)
    # K-2B2
    text = open(SRC).read()
    if text.count(OLD) != 1:
        sys.exit("REFUSED: marker anchor not unique")
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(text.replace(OLD, NEW))
        ok, _, brc = knife_guard.build(f"{TMP}/mk_k2b2.log", before)
        if brc or not ok:
            print(f"K-2B2: build rc={brc} reached-ROM={ok} -- NOT SCORED")
        else:
            rc, rows = probe("k2b2")
            show('K-2B2 (sub2 marked "ZB")', rc, rows, True)
    finally:
        open(SRC, "w").write(text)
    # CLEAN: the first run restored sub2.asm in the SAME SECOND the cut ROM was
    # built, make saw equal mtimes and kept the cut "ZB" ROM -- the restore
    # measured the knife again and read RED [[a-knife-can-be-inert-because-the-build-did-not-happen]].
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(),
                                   clean=True)
    rc, rows = probe("restore")
    print(f"restored: build rc={brc}; gate {'GREEN' if not rc else 'RED -- RESTORE BROKEN'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
