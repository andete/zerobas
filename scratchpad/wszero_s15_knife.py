#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S15 knife: the diskless ceiling at $F380, and the three FAT-tenant
cells that had to leave the floor with it.

K-WS94 TXTMAX_NODISK back at $ECF8 -> `noclear3` (a no-CLEAR load at $E000..$F07F,
       just under the VG-8020's stack) DIVERGES, alone among the no-CLEAR rows
K-WS95 DISKOP_A / DISKOP_HL / DISKOP_ERR back at $EE3A / $EE3B / $EF06 ->
       floorcensus-acceptance FAILS, naming fatprim_tenant and fp_stash_ok
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s15_knife")
SRC = "basic/sysvars.inc"
KNIVES = [
    ("K-WS94", {"TXTMAX_NODISK": "$ECF8"}, "rows", ["ctl", "noclear", "noclear2", "noclear3"],
     ["noclear3"]),
    ("K-WS95", {"DISKOP_A": "$EE3A", "DISKOP_HL": "$EE3B", "DISKOP_ERR": "$EF06"}, "census",
     None, ["fatprim_tenant", "fp_stash_ok"]),
]


def cut(text, names):
    for n, addr in names.items():
        pat = re.compile(rf"^({n}\s+equ\s+)(\$[0-9A-F]{{4}})(?=\s)", re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"anchor {n}: {len(pat.findall(text))}")
        text = pat.sub(lambda m: m.group(1) + addr, text)
    return text


def rows(tag, names):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *names],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def census(tag):
    log = f"{TMP}/{tag}_census.log"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_floorcensus.py"],
                             stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    named = [ln.split()[2] for ln in open(log) if ln.startswith("UNLISTED WRITER")]
    return rc, [n.split(":", 1)[1].split("+")[0] for n in named]


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    for _t, names, _k, _r, _p in KNIVES:
        cut(text, names)                            # refuses before anything is touched
    for tag, names, kind, rws, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            open(SRC, "w").write(cut(text, names))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            if kind == "rows":
                red = rows(tag, rws)
                print(f"{tag}: rows {rws} diverging {red}; predicted {pred} -> "
                      f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
            else:
                rc, named = census(tag)
                hit = rc == 1 and sorted(set(named)) == sorted(pred)
                print(f"{tag}: census rc={rc}, unlisted writers {sorted(set(named))}; predicted "
                      f"FAIL naming {pred} -> {'HIT' if hit else 'MISS'}", flush=True)
        finally:
            open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = rows("restore", ["ctl", "noclear3"])
    rc, named = census("restore")
    print(f"restored: build rc={brc}; rows {'DIVERGE ' + str(red) if red else 'SAME'}; "
          f"census rc={rc} {named or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
