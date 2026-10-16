#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14g-c knife: INPUT$'s count on the stack, PRDEST at PTRFIL's low
byte, PRDEV in BUF. Do the rows see each move, and the PRDEV placement hazards?

K-WS82/83 the two reverts TOGETHER: basic/strvar.asm and basic/save.asm from
       HEAD (the INDLR_N RAM counter; the one 16-bit store that needs PRDEV right
       after PRDEST), INDLR_N back at $EEC0 and PRDEV at $F865 (PTRFIL+1, the
       plan's rejected P1 home). Paired because each alone moves the segment in
       front of the $6CF3 pin (+2 / -2 B) and cannot build under the pins; the
       rows still attribute: `ovinpd` reads only INPUT$, `ovprdev` only PTRFIL.
       -> s14gc (INDLR_N back in the window), ovinpd (the nested INPUT$ raises 5
       again) and ovprdev (PEEK(&HF865) reads the CRT: sink, 2) DIVERGE
K-WS84 NEGATIVE CONTROL: PRDEV at PU_TYPE (BUFTX+8), guard off -- PRINT # USING
       writes 0 (a numeric field) there while PRDEV is live: the disk sink on a
       CRT: channel -> `ovprusg` DIVERGES
K-WS84g the same layout WITH the guard: the build must be refused, naming
       S14GC_PRDEV_OUTSIDE_THE_BUF_GAP
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s14gc_knife")
SYS = "basic/sysvars.inc"
ROWS = ["ctl", "s14gc", "ovinpd", "ovprdev", "ovprusg"]
GUARD = "                db      S14GC_PRDEV_OUTSIDE_THE_BUF_GAP"
GUARD_OFF = "                ; KNIFE db S14GC_PRDEV_OUTSIDE_THE_BUF_GAP"
# (tag, {name: new value}, add INDLR_N?, files restored from HEAD, guard off?, prediction)
KNIVES = [
    ("K-WS82/83", {"PRDEV": "$F865"}, True, ["basic/strvar.asm", "basic/save.asm"], True,
     ["s14gc", "ovinpd", "ovprdev"]),
    ("K-WS84", {"PRDEV": "BUFTX + 8"}, False, [], True, ["ovprusg"]),
    ("K-WS84g", {"PRDEV": "BUFTX + 8"}, False, [], False, "BUILDFAIL:S14GC_PRDEV_OUTSIDE_THE_BUF_GAP"),
]


def cut_sys(text, names, add_indlr, guard_off):
    for n, val in names.items():
        pat = re.compile(rf"^({n}\s+equ\s+)(\$[0-9A-F]{{4}})(?=\s)", re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"anchor {n}: {len(pat.findall(text))}")
        text = pat.sub(lambda m: m.group(1) + val, text)
    if add_indlr:
        a = "MRG_PTR         equ"
        if text.count(a) != 1 or re.search(r"^INDLR_N\s+equ", text, re.M):
            raise SystemExit("anchor INDLR_N")
        text = text.replace(a, "INDLR_N         equ     $EEC0   ; KNIFE: the RAM counter back\n" + a)
    if guard_off:
        if text.count(GUARD) != 1:
            raise SystemExit("anchor guard")
        text = text.replace(GUARD, GUARD_OFF)
    return text


def suite(tag, rows):
    log = f"{TMP}/{tag.replace('/', '_')}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    saved = {p: open(p).read() for p in [SYS, "basic/strvar.asm", "basic/save.asm"]}
    for _t, names, add, _f, goff, _p in KNIVES:
        cut_sys(saved[SYS], names, add, goff)       # refuses before anything is touched
    only = sys.argv[1:]
    for tag, names, add, files, goff, pred in KNIVES:
        if only and tag not in only:
            continue
        before = knife_guard.hashes()
        try:
            open(SYS, "w").write(cut_sys(saved[SYS], names, add, goff))
            for f in files:
                open(f, "w").write(subprocess.check_output(["git", "show", f"HEAD:{f}"], text=True))
            log = f"{TMP}/mk_{tag.replace('/', '_')}.log"
            moved, _, brc = knife_guard.build(log, before)
            if isinstance(pred, str):               # a guard must REFUSE this layout
                sym = pred.split(":", 1)[1]
                named = sym in open(log).read()
                print(f"{tag}: build rc={brc}, {sym} {'named' if named else 'NOT named'} in the log; "
                      f"predicted the guard refuses -> {'HIT' if brc != 0 and named else 'MISS'}",
                      flush=True)
                continue
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            red = suite(tag, ROWS)
            print(f"{tag}: rows {ROWS} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ROWS)
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
