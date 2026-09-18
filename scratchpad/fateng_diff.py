#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATDIFF: where do the two FAT12 engines actually differ, and which way?

Option 2 (Joost, 2026-09-18) deletes `disk/fat.asm`'s FAT routines and assembles
`basic/fat-prim-body.inc` into `disk.rom` instead. That makes **BDOS run BASIC's
implementation** of every routine both files define. The swap is atomic -- the 53
shared labels collide, so the two cannot coexist even briefly -- and
`bdos-acceptance` would catch a behavioural regression only AFTER the fact, as a
failure that does not say which routine caused it.

So this runs first. It asks, per routine: after normalising the spellings we have
already proved equivalent, what is LEFT, and does BASIC's side do everything
disk's side does?

NORMALISATION -- only differences already established as equivalent:
  * the buffer bases. `disk/fat.asm` says `(DBUF_PTR)`/`(MBUF_PTR)` since D-FATENG
    slices 1-2; the body says `FAT_DBUF`/`FAT_MBUF` since increment 2; both were
    `SECTOR_BUF`/`WBUF` and `FSECTOR_BUF`/`FWBUF` before that. All four spellings
    of each collapse to one token.
  * the write-state cells, whose `FWR_* -> BDOS_WR*` mapping is exact and is now
    an equate in disk/equates.inc.
  * comments and whitespace.

🔴 WHAT IT CANNOT DO, STATED SO THE OUTPUT IS NOT OVER-READ: this is a SOURCE
differential. It shows what the text does differently; it does not execute
either engine. A routine it calls IDENTICAL is identical. A routine it flags is
a question for a human to answer by reading -- the classification below is a
sorting aid, not a verdict.
"""
import difflib, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISK = os.path.join(REPO, "disk/fat.asm")
BODY = os.path.join(REPO, "basic/fat-prim-body.inc")

NORM = [
    (r"\(DBUF_PTR\)|\bFAT_DBUF\b|\bFSECTOR_BUF\b|\bSECTOR_BUF\b", "@DBUF@"),
    (r"\(MBUF_PTR\)|\bFAT_MBUF\b|\bFWBUF\b|\bWBUF\b", "@MBUF@"),
    (r"\bFWR_CLUS\b|\bBDOS_WRCLUS\b", "@WCLUS@"),
    (r"\bFWR_FIRST\b|\bBDOS_WRFIRST\b", "@WFIRST@"),
    (r"\bFWR_SECIDX\b|\bBDOS_WRSECIDX\b", "@WSECIDX@"),
    (r"\bFWR_BUFLEN\b|\bBDOS_WRBUFLEN\b", "@WBUFLEN@"),
    (r"\bFWR_BYTES\b|\bBDOS_WRBYTES\b", "@WBYTES@"),
    (r"\bFWR_DIRSEC\b|\bBDOS_DIRSEC\b", "@WDIRSEC@"),
    (r"\bFWR_DIROFF\b|\bBDOS_DIROFF\b", "@WDIROFF@"),
]


def spans(path):
    out, cur, buf = {}, None, []
    for l in open(path, errors="replace").read().split("\n"):
        m = re.match(r"^([a-z_0-9]+):", l)
        if m:
            if cur:
                out[cur] = buf
            cur, buf = m.group(1), [l]
        elif cur is not None:
            buf.append(l)
    if cur:
        out[cur] = buf
    return out


def norm(lines):
    out = []
    for l in lines:
        c = l.split(";")[0]
        if not c.strip():
            continue
        for pat, rep in NORM:
            c = re.sub(pat, rep, c)
        c = " ".join(c.split())
        # a label line keeps only its own name
        out.append(c)
    return out


def classify(a, b):
    """A sorting aid, never a verdict."""
    sa, sb = set(a), set(b)
    if len(b) > len(a) and sa - sb == set():
        return "BASIC SUPERSET   (every disk line present, plus more)"
    if len(a) > len(b) and sb - sa == set():
        return "🔴 DISK SUPERSET (disk has lines BASIC lacks)"
    only_a = [l for l in a if l not in sb]
    only_b = [l for l in b if l not in sa]
    if not only_a:
        return "BASIC SUPERSET   (no disk-only line)"
    if not only_b:
        return "🔴 DISK SUPERSET (no BASIC-only line)"
    return "🔴 DIVERGENT      (each has lines the other lacks)"


def main():
    A, B = spans(DISK), spans(BODY)
    common = sorted(set(A) & set(B))
    same, diff = [], []
    for k in common:
        (same if norm(A[k]) == norm(B[k]) else diff).append(k)
    print("shared labels: %d   identical after normalisation: %d   differing: %d\n"
          % (len(common), len(same), len(diff)))
    buckets = {}
    for k in diff:
        a, b = norm(A[k]), norm(B[k])
        c = classify(a, b)
        buckets.setdefault(c, []).append(k)
    for c in sorted(buckets):
        print("%-50s %d: %s" % (c, len(buckets[c]), ", ".join(buckets[c])))
    if "--detail" in sys.argv:
        for k in diff:
            a, b = norm(A[k]), norm(B[k])
            print("\n" + "=" * 70)
            print("%s   -- %s" % (k, classify(a, b)))
            print("=" * 70)
            for l in difflib.unified_diff(a, b, "disk", "basic", lineterm="", n=1):
                print("  " + l)
    else:
        print("\nrun with --detail for the per-routine diffs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
