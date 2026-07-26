#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""`TIME` / `TIME=n` characterization + differential (docs/spec-basic-time.md).

zerobas has no `TIME` yet (it is absent from basic/kwtable.inc, so `TIME` parses
as the variable `TI` and reads 0 forever). This probe is therefore REFERENCE-ONLY
in `--mode characterize`, which is what produced spec §1; `--mode differential`
becomes the `time-acceptance` gate once the slice lands.

Four groups, matching the spec:
  crunch  (§1.1) -- token bytes via the `stored_line` capture, incl. the three
                    greedy-match shadow cases (TIMES / TIME$ / ATIME).
  read    (§1.2) -- TIME is the unsigned word at JIFFY ($FC9E), yielded as a float.
  write   (§1.3) -- the float->word conversion table.
  errors  (§1.4) -- ERR 13 / 24 / 6 / 2 via ON ERROR GOTO.
  clock   (§1.5) -- PER-MACHINE property only (advances, wraps); never an equal
                    jiffy count across machines -- the tick rate belongs to the
                    host BIOS/VDP, exactly as T3's key-repeat constants do.

THE LOAD-BEARING PROTOCOL -- read `write` group cases with `--phases`:
JIFFY can tick between `TIME=x` and the `PRINT TIME` that reads it back, and in a
BATCHED run that phase is REPRODUCIBLE -- so repeating a case does NOT average it
out, and two characterization rounds agreed on a WRONG answer ("TIME= rounds")
before this was caught. Each write case is therefore run at N deliberately shifted
phases (a variable-length FOR delay ahead of the assignment) and reduced by MIN:
the stored value is a lower bound of every reading, so min over enough phases IS
the stored value. See spec §1.3 and [[traps-t2-strig-slice]] (a capture window is
part of the measurement).

Clean-room: observed outputs only. The reference ROM is a black box.
"""
from __future__ import annotations
import argparse, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
TXTTAB = 0xF676          # BASIC text base (both machines)
M = "CHR$(35)"           # '#' marker -- appears only in runtime output, never the echo

# --- §1.1 crunch: (label, source body, expected token bytes) ----------------
CRUNCH = [
    ("read",    "A=TIME",     "41 EF CB"),
    ("assign",  "TIME=0",     "CB EF 11"),
    ("print",   "PRINT TIME", "91 20 CB"),
    ("sh_times","A=TIMES",    "41 EF CB 53"),   # TIME + verbatim 'S'
    ("sh_dol",  "A=TIME$",    "41 EF CB 24"),   # TIME + verbatim '$'
    ("sh_atime","A=ATIME",    "41 EF 41 CB"),   # verbatim 'A' + TIME
    ("sh_ti",   "A=TI",       "41 EF 54 49"),   # plain variable, untouched
]

# --- §1.2 read: (label, body, expected) ------------------------------------
READ = [
    ("is_jiffy", f"POKE&HFC9F,&H30:POKE&HFC9E,0:PRINT{M};TIME;{M}", "12288"),
    ("unsigned", f"TIME=40000:PRINT{M};TIME;{M}",                   "40000"),
    ("max",      f"TIME=65535:PRINT{M};TIME;{M}",                   "65535"),
    ("hex",      f"TIME=&HFFFF:PRINT{M};TIME;{M}",                  "65535"),
    ("expr",     f"TIME=100+50:PRINT{M};TIME;{M}",                  "150"),
    ("in_if",    f"TIME=9:IF TIME>0 THEN PRINT{M};1;{M}",           "1"),
]

# --- §1.3 write: (label, assigned value, expected STORED word) -------------
# read back with the phase-shift + min protocol (see the module docstring).
WRITE = [
    ("trunc_1_4",  "1.4",      1),
    ("trunc_1_5",  "1.5",      1),
    ("trunc_1_6",  "1.6",      1),      # NOT 2 -- the tick-naive reading said 2
    ("trunc_0_5",  "0.5",      0),
    ("trunc_2_5",  "2.5",      2),
    ("trunc_3_5",  "3.5",      3),
    ("plain",      "100",      100),
    ("zero",       "0",        0),
    ("wrap_40000", "40000",    40000),  # -> -25536 -> truncate
    ("wrap_hi_a",  "65534.6",  65535),  # -> -1.4  -> truncate -> -1
    ("wrap_hi_b",  "65535.4",  0),      # -> -0.6  -> truncate -> 0
    ("wrap_hi_c",  "65535.6",  0),      # -> -0.4  -> truncate -> 0
    ("neg_1",      "-1",       65535),
    ("neg_100",    "-100",     65436),
    ("neg_min",    "-32768",   32768),
]

# --- §1.4 errors: (label, statement, expected) -----------------------------
ERRORS = [
    ("ok",        "TIME=5",               "cont"),
    ("str_lit",   'TIME="A"',             "ERR13"),
    ("str_var",   'A$="X":TIME=A$',       "ERR13"),
    ("missing",   "TIME=",                "ERR24"),
    ("missing_c", "TIME=:PRINT 1",        "ERR24"),
    ("ovf_hi",    "TIME=65536",           "ERR6"),
    ("ovf_hi2",   "TIME=99999",           "ERR6"),
    ("ovf_lo",    "TIME=-32769",          "ERR6"),
    ("let",       "LET TIME=5",           "ERR2"),
    ("bare",      "TIME",                 "ERR2"),
    ("juxt",      "TIME 5",               "ERR2"),
    ("for",       "FOR TIME=1 TO 3:NEXT", "ERR2"),
    ("swap",      "SWAP TIME,A",          "ERR2"),
    ("read_stmt", "READ TIME",            "ERR2"),
    ("dim",       "DIM TIME(3)",          "ERR2"),
    ("subscript", "TIME(1)=5",            "ERR2"),
    ("defint",    "DEFINT T-Z:TIME=70000","ERR6"),
    # --- D-TIME-1: TIME is NOT integer-typed above 32767 -------------------
    # `AND` coerces its operands STRICTLY to int16, so it discriminates "holds
    # the value 40000 as a float" (ERR 6) from "holds the bit pattern $9C40 as
    # an int16" (= -25536, AND 255 -> 64). TIME overflows; the int16 control
    # succeeds; the float control overflows identically. Decisive.
    ("t1_time",   "TIME=40000:A=TIME AND 255",  "ERR6"),
    ("t1_flt",    "B=40000:A=B AND 255",        "ERR6"),   # genuine float -> same
    ("t1_int",    "B%=-25536:A=B% AND 255",     "cont"),   # genuine int16 -> 64, ok
    ("t1_small",  "TIME=100:A=TIME AND 255",    "cont"),   # <=32767: works either way
]


# --- the phase-shift apparatus (spec §1.3), REBUILT for the zerobas side ----
# A batched harness makes the JIFFY-tick confound REPRODUCIBLE, so a single
# reading of TIME after an assignment is not a measurement -- the fix is to
# shift the phase deliberately and reduce.
#
# ⚠️ THE ORIGINAL PAD WAS `FORI=1TO{6k+1}:NEXT:` AND IT DOES NOT RUN ON ZEROBAS.
# A DIRECT-MODE `FOR ... NEXT` raises "out of memory" there -- measured
# 2026-07-26, and PRE-EXISTING (a direct FOR with no TIME in it fails
# identically, so it is neither this slice's nor the carve's; logged in
# disk/docs/tier2-review-queue.md). With every phase but k=0 erroring out, the
# min-over-phases reduction silently collapsed to ONE reading and re-imported
# the exact confound the protocol exists to defeat: nine cases read +1.
# A gate whose reduction quietly degrades to a single sample is worse than no
# reduction, because it still prints a number.
#
# The replacement is a statement pad, which needs no FOR. Cost MEASURED rather
# than assumed: ~5 `A=1:` per jiffy on zerobas, ~11 on the VG-8020, so k=0..7 at
# two statements per step spans ~2.8 jiffies on the slow side and ~1.3 on the
# fast one -- more than one full tick either way, which is what makes at least
# one phase tick-free.
def _pad(k: int) -> str:
    return "A=1:" * (2 * k)


def _earliest(nums: list[int]) -> int | None:
    """Reduce phase-shifted readings to the tick-free one.

    Plain MIN is what the spec wrote and it is WRONG AT THE WRAP: the `max` row
    stores 65535, so an extra tick reads 0 and min(65535, 0) picks the corrupted
    sample. Ticks only ever advance, and only by a few counts within a batch, so
    the tick-free reading is the one every other sample is FORWARD of on the
    mod-65536 circle. Pick the candidate minimising the largest forward distance
    -- identical to MIN when no wrap is involved."""
    if not nums:
        return None
    return min(nums, key=lambda v: max((w - v) % 65536 for w in nums))


def _spans(raw: str | None) -> list[str]:
    return re.findall(r"#([^#]*)#", raw or "")


def _last(raw: str | None) -> str:
    """Last NON-EMPTY marker span. The non-empty part is load-bearing: when a case
    errors mid-`PRINT`, line 20's leading CHR$(35) is already on screen and the
    handler's own pair follows, giving `## 6 #` -- a naive "last span" match then
    returns the EMPTY first pair and the real ERR 6 vanishes into a blank column.
    That is how the D-TIME-1 `TIME AND 255` reading nearly got lost."""
    s = [x.strip() for x in _spans(raw) if x.strip()]
    return s[-1] if s else "??" + re.sub(r"\s+", " ", raw or "").strip()[-36:]


# --------------------------------------------------------------------------
def run_crunch(machine: str, **kw) -> list[str]:
    specs = [("direct", [f"1 {body}"]) for _, body, _ in CRUNCH]
    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB), **kw)
    out = []
    for c in caps:
        if not c:
            out.append("<none>")
            continue
        out.append(" ".join(f"{b:02X}" for b in bytes.fromhex(c)[4:-1]))  # strip hdr + 00
    return out


def run_read(machine: str, phases: int = 8, **kw) -> list[tuple[str, list[str]]]:
    """Phase-shifted like the write group, and for the same reason: every row but
    `is_jiffy` sets TIME and reads it straight back, so a tick between the two is
    indistinguishable from a wrong value. The first differential run read
    `unsigned` as 40001 and `max` as 0 for exactly that -- and `max`'s 0 is why
    the reduction has to be wrap-aware (_earliest, not min)."""
    specs, keys = [], []
    for i, (_, body, _) in enumerate(READ):
        for k in range(phases):
            specs.append(("direct", [_pad(k) + body]))
            keys.append(i)
    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW", "CLS"), **kw)
    acc: dict[int, list[str]] = {}
    for i, raw in zip(keys, caps):
        acc.setdefault(i, []).append(_last(raw))
    out = []
    for i in range(len(READ)):
        obs = acc.get(i, [])
        nums = [int(x) for x in obs if x.lstrip("-").isdigit()]
        e = _earliest(nums)
        out.append((str(e) if e is not None else (obs[0] if obs else "??"), obs))
    return out


def run_write(machine: str, phases: int, **kw) -> list[tuple[int | None, list[str]]]:
    """Phase-shifted, min-reduced (see the module docstring). Returns
    [(stored_or_None, all_observations), ...] aligned with WRITE."""
    specs, keys = [], []
    for i, (_, val, _) in enumerate(WRITE):
        for k in range(phases):
            specs.append(("direct", [f"{_pad(k)}TIME={val}:PRINT{M};TIME;{M}"]))
            keys.append(i)
    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW", "CLS"), **kw)
    acc: dict[int, list[str]] = {}
    for i, raw in zip(keys, caps):
        acc.setdefault(i, []).append(_last(raw))
    res = []
    for i in range(len(WRITE)):
        obs = acc.get(i, [])
        nums = [int(x) for x in obs if x.lstrip("-").isdigit()]
        res.append((_earliest(nums), obs))
    return res


def run_errors(machine: str, **kw) -> list[str]:
    specs = [("direct", ["10 ON ERROR GOTO 100", f"20 {stmt}",
                         "30 PRINTCHR$(67);CHR$(35):END",
                         "100 PRINTCHR$(35);ERR;CHR$(35)", "RUN"])
             for _, stmt, _ in ERRORS]
    out = []
    for raw in omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW", "CLS"), **kw):
        s = _spans(raw)
        out.append(("ERR" + s[-1].strip()) if s else
                   ("cont" if "C#" in (raw or "") else _last(raw)))
    return out


def run_clock(machine: str, **kw) -> dict[str, str]:
    """PER-MACHINE property only -- the tick rate belongs to the host BIOS/VDP,
    so an equal jiffy count across machines is NOT the assertion (spec §1.5).

    `step` is 15 emulated seconds, NOT the 2.5 s default: a 3000-iteration FOR is
    ~4.8 s on the VG-8020 and zerobas is ~7x slower, so the default capture fires
    BEFORE the line prints. Caught live -- the first run returned `??` for two of
    these three ([[paint-slow-emulated-budget-trap]]); it reported an unfinished
    program rather than a zero, which is exactly the contract."""
    kw.setdefault("step", 40.0)
    # ⚠️ STORED PROGRAMS, not direct lines: a DIRECT-MODE `FOR ... NEXT` raises
    # "out of memory" on zerobas (pre-existing, see _pad above), so the direct
    # form returned an error string for all three of these on the zerobas side.
    # In a stored program FOR works on both machines -- the same shape every
    # other trap/graphics gate in this tree uses.
    specs = [
        ("direct", ["10 TIME=0", "20 FORI=1TO3000:NEXT",
                    f"30 PRINT{M};TIME;{M}", "RUN"]),                    # advances
        ("direct", ["10 TIME=0:A=TIME", "20 FORI=1TO500:NEXT",
                    f"30 PRINT{M};TIME>=A;{M}", "RUN"]),                 # monotonic
        ("direct", ["10 TIME=65500", "20 FORI=1TO3000:NEXT",
                    f"30 PRINT{M};TIME<1000;{M}", "RUN"]),               # wraps
    ]
    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW", "CLS"), **kw)
    return dict(zip(("advance_jiffies", "monotonic", "wrapped"),
                    (_last(c) for c in caps)))


# --------------------------------------------------------------------------
def run_side(machine: str, label: str, g: str, phases: int) -> bool:
    """Run the selected groups on ONE machine against the SAME pinned wants.

    That is what makes this a differential rather than two characterizations:
    every `want` in CRUNCH/READ/WRITE/ERRORS is a value MEASURED on the VG-8020
    (spec §1), so asserting zerobas against them IS the comparison, and re-running
    the reference against them re-validates the oracle in the same pass. The clock
    group is the exception and is deliberately NOT an equality differential -- the
    tick rate belongs to the host BIOS/VDP, so it is asserted as a per-machine
    PROPERTY (spec §1.5).
    """
    ok = True
    print(f"\n########## {label}: {machine}")

    if "c" in g:
        print("=== crunch (spec §1.1) ===")
        for (lbl, body, want), have in zip(CRUNCH, run_crunch(machine)):
            good = have == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} {lbl:9} {body:12} "
                  f"{have:16} want={want}")

    if "r" in g:
        print(f"\n=== read (spec §1.2, earliest over {phases} phases) ===")
        for (lbl, body, want), (have, obs) in zip(READ, run_read(machine, phases)):
            good = have == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} {lbl:9} {have:10} want={want:8} "
                  f"obs={sorted(set(obs))}")

    if "w" in g:
        print(f"\n=== write (spec §1.3, earliest over {phases} phases) ===")
        for (lbl, val, want), (lo, obs) in zip(WRITE, run_write(machine, phases)):
            good = lo == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} {lbl:11} TIME={val:9} "
                  f"stored={lo!s:6} want={want:<6} obs={sorted(set(obs))}")

    if "e" in g:
        print("\n=== errors (spec §1.4) ===")
        for (lbl, stmt, want), have in zip(ERRORS, run_errors(machine)):
            good = have == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} {lbl:10} {stmt:22} "
                  f"{have:8} want={want}")

    if "k" in g:
        # PROPERTY, not equality: the two machines run BASIC ~7x apart, so the
        # jiffy count over a fixed FOR loop is NOT comparable. `-1` is MSX BASIC's
        # TRUE -- monotonic and wrapped must both be true on each machine.
        print("\n=== clock — per-machine property (spec §1.5) ===")
        clk = run_clock(machine)
        checks = [("advances", clk["advance_jiffies"].lstrip("-").isdigit()
                   and int(clk["advance_jiffies"]) > 0),
                  ("monotonic", clk["monotonic"] == "-1"),
                  ("wraps at 65536", clk["wrapped"] == "-1")]
        for k, v in clk.items():
            print(f"       {k:16} {v}")
        for name, good in checks:
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} clock: {name}")

    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("characterize", "differential"),
                    default="characterize",
                    help="characterize = reference only; differential = both sides "
                         "against the same pinned reference values")
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--groups", default="crwek",
                    help="subset of c(runch) r(ead) w(rite) e(rrors) k=cloc(k)")
    ap.add_argument("--phases", type=int, default=8,
                    help="write-group phase shifts to reduce by MIN (spec §1.3)")
    args = ap.parse_args()

    ok = run_side(args.machine, "reference", args.groups, args.phases)
    if args.mode == "differential":
        ok &= run_side(args.zb_machine, "zerobas", args.groups, args.phases)

    print("\n" + ("ALL PASS" if ok else "SOME FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
