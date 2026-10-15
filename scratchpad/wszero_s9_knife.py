#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S9 knife: does wszero-acceptance SEE each S9 guard?

K-WS22 fld_lookup's `ret z` -> `nop`       -> `fldread` DIVERGES
K-WS23 fld_init_g's `ret z` -> `nop`       -> `fldclr` DIVERGES
K-WS24 aer_fldfix's `ret z` -> `nop` (sub) -> `flderase` DIVERGES
K-WS25 G5 reverted whole (the justify store back in front of the gate, ex_on_key
       back in front of $73E5, lrsetst back to `or a / jr z`) -> `lset` DIVERGES
K-WS26 se_pending's `ret z` -> `nop`       -> `inpeof` DIVERGES
K-WS27 G1 reverted (the store to $EF35 back, the post-scan fld_init_g out)
       -> `valtyp` DIVERGES
(K-WS28, the post-scan call alone: predicted BLIND on openMSX -- the disk
machine's power-on FIELD table holds no key a program can name. Not run.)
The cuts are byte-neutral and the reverts restore the pre-S9 shapes, so no pin
pad moves; each build must still MOVE the ROM (knife_guard) and pass
`make pin-check` -- a negative pad writes an EMPTY binary with rc 0.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s9_knife")
F, LR, AR, SV, ST, IN = ("basic/field.asm", "sub/lrsetst.asm", "sub/arrays.asm",
                         "basic/sysvars.inc", "basic/strvar.asm", "basic/interp.asm")
KNIVES = [
    ("K-WS22", [(F, "                ret     z                   ; CF=0 (the `or a`): not fielded\n",
                 "                nop                         ; KNIFE K-WS22\n")],
     ["ctl", "fldread"], ["fldread"]),
    ("K-WS23", [(F, "fld_init_g:\n                call    diskslot_test\n                ret     z\n",
                 "fld_init_g:\n                call    diskslot_test\n                nop\n")],
     ["ctl", "fldclr"], ["fldclr"]),
    ("K-WS24", [(AR, "                ret     z                   ; BC/DE/HL; A and the flags are free)\n",
                 "                nop                         ; KNIFE K-WS24\n")],
     ["ctl", "flderase"], ["flderase"]),
    ("K-WS25", [
        (F, """ex_lset:
                ld      de,H_LSET           ; (left / right is the TOKEN's bit 0,
                jr      lrset_common        ; read by lrset_tgt -- D-WSZERO S9)
    IF BASICINT_PINS
; D-WSZERO S9: moved here from in front of the $73E5 pin below -- the 6 B that
; came out of this segment (the justify store) are refilled with it, so the
; $73AC pin does not move (tools/pin_plan.py). A `jp z` target only.
ex_on_key:
                ld      bc,10*256+0         ; B = slot limit, C = slot index 0..9
                jp      eon_trap_in         ; (program.asm's ex_on_key has the story)
    ENDIF
ex_rset:
                ld      de,H_RSET
""", """ex_lset:
                xor     a
                ld      de,H_LSET
                jr      lrset_common
ex_rset:
                ld      a,1
                ld      de,H_RSET
"""),
        (F, "                inc     hl                  ; past the LSET/RSET token\n",
            "                ld      (LRSET_JUST),a\n                inc     hl                  ; past the LSET/RSET token\n"),
        (F, """                dec     hl
                ld      a,(hl)
                inc     hl
                ld      (LRSET_JUST),a
""", ""),
        (F, "                ds      $73E5 - $, $00\n",
            "ex_on_key:\n                ld      bc,10*256+0\n                jp      eon_trap_in\n                ds      $73E5 - $, $00\n"),
        (LR, "                rra                         ; bit 0: the RSET token's (D-WSZERO S9)\n                jr      nc,lrst_copy",
             "                or      a\n                jr      z,lrst_copy")],
     ["ctl", "lset"], ["lset"]),
    ("K-WS26", [(F, "se_pending:\n                call    diskslot_test\n                ret     z ",
                 "se_pending:\n                call    diskslot_test\n                nop       ")],
     ["ctl", "inpeof"], ["inpeof"]),
    ("K-WS27", [(ST, "                ld      a,1                 ; (VALTYP's store went in D-WSZERO S9:\n",
                 "                ld      a,1\n                ld      ($EF35),a           ; KNIFE K-WS27\n"),
                (IN, "                call    fld_init_g\n                ; D-KEYSTR", "                ; D-KEYSTR")],
     ["ctl", "valtyp"], ["valtyp"]),
]


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    files = sorted({p for _t, cuts, _r, _p in KNIVES for p, _o, _n in cuts})
    orig = {p: open(p).read() for p in files}
    for tag, cuts, _r, _p in KNIVES:
        for p, old, _new in cuts:
            if orig[p].count(old) != 1:
                print(f"{tag}: REFUSED, anchor count {orig[p].count(old)} in {p} for {old[:50]!r}")
                return 2
    for tag, cuts, rows, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            text = dict(orig)
            for p, old, new in cuts:
                text[p] = text[p].replace(old, new)
            for p in files:
                open(p, "w").write(text[p])
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            red = suite(tag, rows)
            print(f"{tag}: rows {rows} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            for p in files:
                open(p, "w").write(orig[p])
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ["ctl", "fldread", "fldclr", "flderase", "lset", "inpeof", "valtyp"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
