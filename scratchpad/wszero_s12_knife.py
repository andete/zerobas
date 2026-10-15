#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S12 knife: do the rows SEE each host's overlay -- and do the guards
and the overlay rows catch a WRONG one?

Positive (one host's guests back at their literal pre-S12 homes):
K-WS37 BUF's guests (PAINT / box / CIRCLE draw cells, RENUM) -> s12gfx, s12dir
K-WS38 the FN-slot guests (PRINT USING, READ / DEFINT, Bresenham, read_line,
       SAVE, PLN, MERGE, TKLNUM)          -> s12gfx, s12num, s12inp, s12dir
K-WS39 the leaf-host guests (TK*, VBUF, the multiply cells, WIDIG, PLF, ISRCH,
       PLAY's parse cells, FP_SHIFTAMT / FP_OPMODE) -> s12gfx, s12num, s12inp
K-WS40 FBUFFR's guests (TKOVF, DIVREM, LHS_FAC / LHS_FACTYP) -> s12num
Negative controls (a placement s12_plan.md REJECTED must be caught):
K-WS52 the Bresenham cells into BUF at LINEBUF+8 -> `ovbuf` DIVERGES (DRAW reads
       an INPUT$ argument IN PLACE in STRSCR = BUF)
K-WS53 FP_OPMODE onto WIDIG's byte -> the BUILD refuses (S12_MUL_PP_ON_FP_OPMODE)
K-WS54 MUL_I inside fp_mul's own product -> the BUILD refuses
       (S12_MUL_I_INSIDE_FP_MULS_OWN_PRODUCT)
(K-WS55, a cell live across an evaluation into the FN slots, needs a COLOR FNA()
row the probe does not have: not run.)
A positive knife disables the S12_* guards (they refuse every group put back --
itself a witness: the first run scored all four NOT SCORED on their own guard).
Each build must MOVE the ROM and pass `make pin-check`; restored, rebuilt CLEAN,
the S12 rows re-run.
"""
import os, re, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s12_knife")
SRC = "basic/sysvars.inc"
OLD = {}
B = {'GFX_POVF': 'ECFF', 'GFX_PTESTX': 'ED00', 'GFX_PTESTY': 'ED01', 'GFX_PFY': 'ED02', 'GFX_PXL': 'ED03', 'GFX_PXR': 'ED04', 'GFX_PSCX': 'ED05', 'GFX_PSCY': 'ED06', 'GFX_PSPA': 'ED07', 'GFX_PSTK': 'ED08', 'GFX_PPITCH': 'ED99', 'GFX_TX1': 'EF81', 'GFX_TY1': 'EF83', 'GFX_TX2': 'EF85', 'GFX_TY2': 'EF87', 'GFX_FILLCNT': 'EF89', 'GFX_YSTEP': 'EF8B', 'GFX_SVX': 'EF97', 'GFX_SVY': 'EF99', 'GFX_EVX': 'EF9B', 'GFX_EVY': 'EF9D', 'GFX_FULLW': 'EF9F', 'GFX_QX': 'EFA0', 'GFX_QY': 'EFA2', 'GFX_QD': 'EFA4', 'GFX_PX': 'EFA6', 'GFX_PY': 'EFA8', 'GFX_CS_AX': 'EFAA', 'GFX_CS_AY': 'EFAC', 'GFX_M': 'EFAE', 'GFX_WS_P': 'EFB0', 'GFX_WS_O': 'EFB2', 'GFX_WE_P': 'EFBD', 'GFX_WE_O': 'EFBF', 'GFX_WRAPF': 'EFC0', 'RN_PTR': 'EE6D', 'RN_OLD': 'EE71'}
F = {'PU_NUM': 'EE9D', 'PU_DIG': 'EECA', 'DEFT_PTR': 'ED8F', 'GFX_CX': 'EF70', 'GFX_CY': 'EF72', 'GFX_ERR': 'EF74', 'GFX_DMAJ': 'EF76', 'GFX_DMIN': 'EF78', 'GFX_CNT': 'EF7A', 'GFX_STEEP': 'EF7C', 'GFX_SMIN': 'EF7D', 'GFX_SDX': 'EF7F', 'GFX_SDY': 'EF80', 'SV_OP': 'EFDD', 'SV_STAT': 'EFDE', 'RL_HL': 'EEFF', 'RL_STAT': 'EF01', 'RL_ROW0': 'EF02', 'RL_COL0': 'EF03', 'RL_LAST': 'EF04', 'RL_KEY': 'EF05', 'PLN_NUM': 'EFE8', 'PLN_PTR': 'EFEA', 'MRG_PTR': 'EEC1', 'TKLNUM': 'EEBF'}
LEAF = {'TKDIG': 'F0AB', 'TKPOS': 'F0C3', 'TKINTLEN': 'F0C4', 'TKHAVESIG': 'F0C5', 'TKEXP': 'F0CA', 'TKEXPD': 'F0CC', 'TKEXPSIGN': 'F0CD', 'TKDEXP': 'F0CF', 'TKSRCSAVE': 'F0D5', 'GFX_VBUF': 'ED08', 'MULCAND': 'F111', 'MULTPLR': 'F113', 'MUL32': 'F115', 'WIDIG': 'F107', 'PLF_RA': 'F11F', 'PLF_RA2': 'F121', 'ISRCH_A': 'ECF8', 'MUL_I': 'F10C', 'MUL_PP': 'F10F', 'PLY_XSP': 'F0A8', 'PLY_NUMOVF': 'EE3A', 'FP_SHIFTAMT': 'F101', 'FP_OPMODE': 'F11D'}
Q = {'TKOVF': 'F09F', 'DIVREM': 'F0D7', 'LHS_FAC': 'F0F9', 'LHS_FACTYP': 'F0F8'}
# the negative controls' WRONG homes
BRES_IN_BUF = {'GFX_CX': 'F566', 'GFX_CY': 'F568', 'GFX_ERR': 'F56A', 'GFX_DMAJ': 'F56C', 'GFX_DMIN': 'F56E', 'GFX_CNT': 'F570', 'GFX_STEEP': 'F572', 'GFX_SMIN': 'F573', 'GFX_SDX': 'F575', 'GFX_SDY': 'F576'}
KNIVES = [
    ("K-WS37", B, ["ctl", "s12gfx", "s12dir"], ["s12gfx", "s12dir"]),
    ("K-WS38", F, ["s12gfx", "s12num", "s12inp", "s12dir"], ["s12gfx", "s12num", "s12inp", "s12dir"]),
    ("K-WS39", LEAF, ["ctl", "s12gfx", "s12num", "s12inp"], ["s12gfx", "s12num", "s12inp"]),
    ("K-WS40", Q, ["ctl", "s12num"], ["s12num"]),
    ("K-WS52", BRES_IN_BUF, ["ctl", "ovbuf"], ["ovbuf"]),
    ("K-WS53", {"FP_OPMODE": "F832"}, [], "BUILDFAIL:S12_MUL_PP_ON_FP_OPMODE"),
    ("K-WS54", {"MUL_I": "F837"}, [], "BUILDFAIL:S12_MUL_I_INSIDE_FP_MULS_OWN_PRODUCT"),
]


def cut(text, names):
    for n, addr in names.items():
        pat = re.compile(rf"^({n}\s+equ\s+)\$[0-9A-F]{{4}}", re.M)
        if len(pat.findall(text)) != 1:
            raise SystemExit(f"anchor {n}: {len(pat.findall(text))}")
        text = pat.sub(lambda m: m.group(1) + "$" + addr, text)
    return text


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    for tag, names, _r, _p in KNIVES:
        cut(text, names)                            # refuses before anything is touched
    only = sys.argv[1:]
    for tag, names, rows, pred in KNIVES:
        if only and tag not in only:
            continue
        before = knife_guard.hashes()
        try:
            cutt = cut(text, names)
            if not isinstance(pred, str):
                # a positive knife puts a group back in the window, which the S12
                # overlay-fit guards REFUSE (first run: all four NOT SCORED on
                # their own S12_* symbol) -- disable them so the ROWS are what
                # is measured; K-WS53 / 54 keep them and test the guards
                cutt = cutt.replace("                db      S12_", "                ; KNIFE db S12_")
            open(SRC, "w").write(cutt)
            log = f"{TMP}/mk_{tag}.log"
            moved, _, brc = knife_guard.build(log, before)
            if isinstance(pred, str):               # a guard must REFUSE this layout
                sym = pred.split(":", 1)[1]
                refused = brc != 0 and sym in open(log).read()
                print(f"{tag}: build rc={brc}, {sym} {'named' if sym in open(log).read() else 'NOT named'}"
                      f" in the log; predicted the guard refuses -> {'HIT' if refused else 'MISS'}", flush=True)
                continue
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
            open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ["ctl", "s12gfx", "s12num", "s12inp", "s12dir", "ovbuf"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
