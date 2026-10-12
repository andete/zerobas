#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMBUF knives: LINEBUF moved to the reference's BUF ($F55E), which crosses
a page, so the page-aligned idioms had to change. Does the battery SEE each one?

K-R1  basic/files.asm ascii_read_lines: the cap test back to `jr nc` (an ORDER
      test on the low byte). With LINEBUF at $F55E every low byte from $5E up
      compares >= the cap's $5C, so each line keeps nothing: predicted
      diskascii-acceptance and cas-ascii-acceptance RED.
K-R2  basic/input.asm linebuf_getbyte: the cursor advance dropped (`inc hl`
      -> `nop`), i.e. a cursor that never moves: predicted input-acceptance RED.
Built through knife_guard; restored on a CLEAN build and the targets re-run.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "rambuf_knife")
TARGETS = ("input-acceptance", "diskascii-acceptance", "cas-ascii-acceptance")
CUTS = [
    ("K-R1", "basic/files.asm",
     "                jr      z,arl_charloop      ;  255 B, so EQUALITY is exact; line full ->\n",
     "                jr      nc,arl_charloop     ; KNIFE K-R1\n",
     {"diskascii-acceptance", "cas-ascii-acceptance"}),
    ("K-R2", "basic/input.asm",
     "                inc     hl\n                ld      (INP_CURSOR),hl     ; advance the cursor past this byte\n",
     "                nop                         ; KNIFE K-R2\n                ld      (INP_CURSOR),hl     ; advance the cursor past this byte\n",
     {"input-acceptance"}),
]


def gate(tag):
    red = set()
    for t in TARGETS:
        log = f"{TMP}/{tag}_{t}.log"
        with open(log, "w") as fh:
            rc = subprocess.call(["make", t], cwd=REPO, stdout=fh,
                                 stderr=subprocess.STDOUT, timeout=2400)
        if rc:
            red.add(t)
    return red


def main():
    os.makedirs(TMP, exist_ok=True)
    for tag, path, old, new, want in CUTS:
        src = os.path.join(REPO, path)
        text = open(src).read()
        if text.count(old) != 1:
            print(f"{tag}: REFUSED, anchor count {text.count(old)}")
            continue
        before = knife_guard.hashes()
        try:
            open(src, "w").write(text.replace(old, new))
            ok, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not ok:
                print(f"{tag}: build rc={brc} reached-ROM={ok} -- NOT SCORED")
                continue
            red = gate(tag)
            print(f"{tag}: red {sorted(red)}; predicted {sorted(want)}: "
                  f"{'HIT' if red == want else 'MISS'}", flush=True)
        finally:
            open(src, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    red = gate("restore")
    print(f"restored: build rc={brc}; {'GREEN' if not red else 'RED ' + str(sorted(red))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
