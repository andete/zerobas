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
]


def _spans(raw: str | None) -> list[str]:
    return re.findall(r"#([^#]*)#", raw or "")


def _last(raw: str | None) -> str:
    s = _spans(raw)
    return s[-1].strip() if s else "??" + re.sub(r"\s+", " ", raw or "").strip()[-36:]


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


def run_read(machine: str, **kw) -> list[str]:
    specs = [("direct", [b]) for _, b, _ in READ]
    return [_last(r) for r in omsx_repl.run_cases(machine, specs, batch=True,
                                                  reset=("NEW", "CLS"), **kw)]


def run_write(machine: str, phases: int, **kw) -> list[tuple[int | None, list[str]]]:
    """Phase-shifted, min-reduced (see the module docstring). Returns
    [(stored_or_None, all_observations), ...] aligned with WRITE."""
    specs, keys = [], []
    for i, (_, val, _) in enumerate(WRITE):
        for k in range(phases):
            delay = f"FORI=1TO{6*k+1}:NEXT:" if k else ""
            specs.append(("direct", [f"{delay}TIME={val}:PRINT{M};TIME;{M}"]))
            keys.append(i)
    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW", "CLS"), **kw)
    acc: dict[int, list[str]] = {}
    for i, raw in zip(keys, caps):
        acc.setdefault(i, []).append(_last(raw))
    res = []
    for i in range(len(WRITE)):
        obs = acc.get(i, [])
        nums = [int(x) for x in obs if x.lstrip("-").isdigit()]
        res.append((min(nums) if nums else None, obs))
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
    specs = [
        ("direct", [f"TIME=0:FORI=1TO3000:NEXT:PRINT{M};TIME;{M}"]),          # advances
        ("direct", [f"TIME=0:A=TIME:FORI=1TO500:NEXT:PRINT{M};TIME>=A;{M}"]), # monotonic
        ("direct", [f"TIME=65500:FORI=1TO3000:NEXT:PRINT{M};TIME<1000;{M}"]), # wraps
    ]
    caps = omsx_repl.run_cases(machine, specs, batch=True, reset=("NEW", "CLS"), **kw)
    return dict(zip(("advance_jiffies", "monotonic", "wrapped"),
                    (_last(c) for c in caps)))


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("characterize", "differential"),
                    default="characterize",
                    help="characterize = reference only (zerobas has no TIME yet)")
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--groups", default="crwek",
                    help="subset of c(runch) r(ead) w(rite) e(rrors) k=cloc(k)")
    ap.add_argument("--phases", type=int, default=8,
                    help="write-group phase shifts to reduce by MIN (spec §1.3)")
    args = ap.parse_args()
    g, ok = args.groups, True

    if "c" in g:
        print("=== crunch (spec §1.1) ===")
        got = run_crunch(args.machine)
        for (label, body, want), have in zip(CRUNCH, got):
            good = have == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} {label:9} {body:12} "
                  f"{have:16} want={want}")

    if "r" in g:
        print("\n=== read (spec §1.2) ===")
        for (label, body, want), have in zip(READ, run_read(args.machine)):
            good = have == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} {label:9} {have:10} want={want}")

    if "w" in g:
        print(f"\n=== write (spec §1.3, min over {args.phases} phases) ===")
        for (label, val, want), (lo, obs) in zip(WRITE,
                                                 run_write(args.machine, args.phases)):
            good = lo == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} {label:11} TIME={val:9} "
                  f"stored={lo!s:6} want={want:<6} obs={sorted(set(obs))}")

    if "e" in g:
        print("\n=== errors (spec §1.4) ===")
        for (label, stmt, want), have in zip(ERRORS, run_errors(args.machine)):
            good = have == want
            ok &= good
            print(f"  {'PASS' if good else 'FAIL':4} {label:10} {stmt:22} "
                  f"{have:8} want={want}")

    if "k" in g:
        print("\n=== clock — per-machine property (spec §1.5) ===")
        for k, v in run_clock(args.machine).items():
            print(f"       {k:16} {v}")

    if args.mode == "differential":
        print("\nzerobas side: NOT YET IMPLEMENTED — `TIME` is absent from "
              "basic/kwtable.inc (spec §7 is blocked on D-TIME-4 funding).")
        return 2

    print("\n" + ("ALL PASS" if ok else "SOME FAIL") +
          f" — reference characterization ({args.machine})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
