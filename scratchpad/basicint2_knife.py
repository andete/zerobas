#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BASICINT2 / D-BIOSREGS knives: does each gate row see its own fix?

The two tape entries (basic/field.asm, gate basicint-acceptance):
  K-TP1 $72D4's body restores HL from the DE slot (`pop hl` / `pop de` swapped)
        -> `tap_read` DIVERGES: the probe's stub keeps its pointer in HL
  K-TP2 $72E9's error exit raises Syntax error instead of ERR 19 -> `tap_brk`
The C-BIOS contracts (cbios-repack/*.patch, gate biosregs-acceptance) -- a `+`
line of the patch replaced line for line, so the diff still applies; the repack's
sha1 pin is skipped for the knife build only (tools/build_repacked_cbios.py):
  K-BR1 CALATR returns 4*A again                   -> `atr`
  K-BR2 CALPAT leaves PATBAS in DE again            -> `pat8`, `pat16`
  K-BR3 LDIRMV without its final `ex de,hl`         -> `ldirmv`
  K-BR4 LDIRVM without `ld c,b`                     -> `ldirvm`
  K-BR5 DCOMPR with `cp` again                      -> `dcmp_h`, `dcmp_l`
Each cut must prove it BUILT (the ROM moved) and keep the pins (`make pin-check`).
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "basicint2_knife")
SHA = ("            if got != REPACKED_SHA1:", "            if False:")
BI = "probes/basic/basic_probe_basicint.py"
BR = "probes/basic/basic_probe_biosregs.py"
KNIVES = [
    ("K-TP1", {"basic/field.asm": [("                call    TAPIN\n                pop     hl\n"
                                    "                pop     de\n",
                                    "                call    TAPIN\n                pop     de\n"
                                    "                pop     hl\n")]},
     BI, ["tap_read", "tap_brk"], ["tap_read"]),
    ("K-TP2", {"basic/field.asm": [("                jp      c,dpl_dio           ; motor off, ERR 19\n",
                                    "                jp      c,stmt_error        ; motor off, ERR 19\n")]},
     BI, ["tap_read", "tap_brk"], ["tap_brk"]),
    ("K-BR1", {"cbios-repack/bios-regs.patch": [
        ("+                ld      l,a\n+                ld      h,0\n+                add     hl,hl\n"
         "+                add     hl,hl\n+                ex      de,hl\n",
         "+                add     a,a\n+                add     a,a\n+                ld      d,0\n"
         "+                ld      e,a\n+                nop\n")],
        "tools/build_repacked_cbios.py": [SHA]},
     BR, None, ["atr"]),
    ("K-BR2", {"cbios-repack/calpat-de.patch": [
        ("+                ex      de,hl\n+                ld      hl,(PATBAS)\n",
         "+                ld      de,(PATBAS)\n+                ; knife K-BR2\n")],
        "tools/build_repacked_cbios.py": [SHA]},
     BR, None, ["pat8", "pat16"]),
    ("K-BR3", {"cbios-repack/bios-regs.patch": [
        ("+                ex      de,hl           ; HL = the VRAM start, DE = the RAM end\n",
         "+                nop\n")],
        "tools/build_repacked_cbios.py": [SHA]},
     BR, None, ["ldirmv"]),
    ("K-BR4", {"cbios-repack/bios-regs.patch": [
        ("+                ld      c,b             ; B = 0 here\n", "+                nop\n")],
        "tools/build_repacked_cbios.py": [SHA]},
     BR, None, ["ldirvm"]),
    ("K-BR5", {"cbios-repack/bios-regs.patch": [
        ("+                sub     d\n", "+                cp      d\n"),
        ("+                sub     e\n", "+                cp      e\n")],
        "tools/build_repacked_cbios.py": [SHA]},
     BR, None, ["dcmp_h", "dcmp_l"]),
]


def cut(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"anchor x{text.count(old)}: {old[:60]!r}")
        text = text.replace(old, new)
    return text


def rows(tag, probe, only):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", probe] + (only or []),
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    files = sorted({f for _t, fe, _p, _o, _r in KNIVES for f in fe})
    saved = {f: open(f).read() for f in files}
    for _t, fe, _p, _o, _r in KNIVES:          # every anchor first, before any build
        for f, edits in fe.items():
            cut(saved[f], edits)
    for tag, fe, probe, only, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            for f, edits in fe.items():
                open(f, "w").write(cut(saved[f], edits))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} "
                      f"-- NOT SCORED", flush=True)
                continue
            red = rows(tag, probe, only)
            print(f"{tag}: diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = rows("restore_br", BR, None) + rows("restore_bi", BI, ["tap_read", "tap_brk"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
