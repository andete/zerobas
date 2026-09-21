#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-MERGESHAPE: does the reference's `MERGE` share `LOAD`'s whole shape?

`disk/docs/expansion-protocol.md` §8.9 carries exactly one unmeasured line after
§6.6ad closed `IX`:

    * Whether `SAVE` and `MERGE` share the whole shape, or only the crossing.

§8.6 traced `LOAD`'s shape end to end: main fills the name block, calls `$FE5D`
ONCE, the disk ROM owns mount + directory + the whole sector loop, and main
enters `$FE76` afterwards for the tokenised-program path only. §8.2 already
proves `MERGE` arrives at the crossing with registers IDENTICAL to `LOAD`'s --
`AF`, `BC`, `DE`, `HL`, `IX` and `IY` all agree. So the crossing is shared; what
is unmeasured is everything AROUND it.

🎯 WHY THIS IS THE STEP THE PORT NEEDS. `spec-diskcode-eviction.md` step 11 is
blocked on a design question, not on bytes: `MERGE` must TOKENISE each line, and
tokenising is main's job (the sub-ROM's, via main). If the disk side owned the
line loop it would need a call-back into main PER LINE, which `FOPEN_SEL`'s
aliasing onto `DISKOP_OP` forbids. If main owns the line loop -- the disk side
only opening the file and handing back a channel, exactly as our own `ascii_load`
does when `DISKOP_STATUS` reads 2 -- then step 11 needs no call-back at all and
is the same one-crossing shape steps 9 and 12 already shipped.

🔬 THE DISCRIMINATOR IS A COUNT AGAINST A LINE COUNT, not a register. Registers
cannot separate `LOAD` from `MERGE` (§8.2 measured that and it is the finding).
Counts can:

  * `$FE5D` entered ONCE for a 2-line file AND once for a 100-line file
        -> the crossing is per-FILE, as it is for `LOAD`;
  * `$FE5D` entered once PER LINE
        -> main owns the line loop and re-crosses for each one;
  * some OTHER cell scaling with the file's SECTOR count during `MERGE`
        -> the disk side is doing the transfer, and the question becomes whether
           that cell is the same one an ordinary sequential channel read uses.

🔴 CLEAN ROOM. Identical to D-HOOKCOUNT's, which this reuses rather than copies:
breakpoints on addresses in the PUBLISHED hook table ($FD9A..$FFE7, MSX2 TH and
C-BIOS `hooks.asm`), counting entries. No cell is peeked, no `<lo> <hi>` is
followed, nothing is single-stepped into ROM, no register is captured here, and
no byte of the reference's ROM or of its RAM-resident code is read. Counts and
the relative order of first entries only.

🔴 EVERY ARM PROVES ITSELF ON SCREEN, because §6.6-era lesson 1 says a FAILED
case contributes a row that looks like data. Each fixture's lines increment `A`,
and its last line prints `A` behind a `CHR$`-built marker, so an arm that read
`n` lines says so in its own output and an arm whose verb errored prints nothing
at all. An arm whose self-proof does not match its fixture is REFUSED, not read.

--- THE PREDICTIONS, STATED BEFORE THE RUN -------------------------------------
  P1  `MERGE` enters `$FE5D` exactly ONCE, at both 2 lines and 100 lines
      (constant, like `LOAD`).
  P2  ASCII `LOAD` and `MERGE` enter the SAME SET of hook cells: the two are one
      mechanism with a different disposition of the lines it reads.
  P3  Some cell scales with the ASCII file's SECTOR count during `MERGE`, and it
      is a cell a sequential `LINE INPUT#` loop over the SAME file also moves --
      i.e. `MERGE` reads through the ordinary channel path.
  P4  tokenised `SAVE` enters `$FE5D` once and does NOT enter `$FE76`
      (§8.6 step 8 says the binary-format path is `LOAD`'s alone).
  P5  ASCII `SAVE"...",A` enters the same cell set as tokenised `SAVE`.
"""
from __future__ import annotations

import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import probe_tmp                                              # noqa: E402,F401
import hookcount_probe as HC                                  # noqa: E402
import loadrun_probe as LR                                    # noqa: E402

REF = HC.REF
RESET = HC.RESET
CELLS = HC.CELLS
H_NULO = HC.H_NULO                     # $FE5D -- the crossing (§8.2)
H_BINL = 0xFE76                        # the binary-FORMAT path (§8.6 step 8)
H_SAVE = 0xFE6C
H_FILE = HC.H_FILE                     # the discriminator control
SECTOR = 512

SMALL_N, LARGE_N = 2, 100
MARK = 64, 66                          # CHR$(64)+CHR$(66) == "@B", HC's fence


# ---------------------------------------------------------------- pure helpers
def ascii_program(n: int) -> bytes:
    """An ASCII-format BASIC program that COUNTS ITS OWN LINES when run.

    `basic/docs/spec-ascii-saveload.md` §2: `<lineno> <space> <text> CR LF` per
    record, `$1A` soft-EOF. `n` incrementing lines then one print line, so a
    successful LOAD/MERGE followed by RUN puts `n` on the screen behind the
    fence. A truncated read prints a SMALLER number -- it does not print `n`
    anyway, which is the whole reason the fixture counts rather than flags.
    """
    if n < 1:
        raise ValueError("a fixture with no lines cannot prove itself")
    recs = [b"%d A=A+1" % (10 * i) for i in range(1, n + 1)]
    recs.append(b"9000 PRINT CHR$(%d)+CHR$(%d);A" % MARK)
    return b"\r\n".join(recs) + b"\r\n\x1a"


def sectors(nbytes: int) -> int:
    return (nbytes + SECTOR - 1) // SECTOR


def read_fence(screen: str, width: int = 40) -> int | None:
    """The integer printed after the `@B` fence, or None if it never printed."""
    got = None
    for j in range(0, len(screen or ""), width):
        row = (screen or "")[j:j + width]
        if "@B" in row:
            tok = row.split("@B", 1)[1].strip().split()
            if tok:
                try:
                    got = int(tok[0])
                except ValueError:
                    pass
    return got


def deltas(base: dict, case: dict) -> dict:
    """Per-cell entry count of ONE case above the quiet baseline, nonzero only."""
    out = {}
    for c in set(base) | set(case):
        d = case.get(c, 0) - base.get(c, 0)
        if d:
            out[c] = d
    return out


def classify(small: dict, large: dict, cell: int,
             n_small: int, n_large: int) -> str:
    """Is `cell` absent, CONSTANT, per-LINE, or merely growing, small -> large?

    The two named answers are the ones the port turns on, so they are the ones
    that must be earned rather than inferred: `constant` needs the SAME count at
    both sizes, `per-line` needs the count to equal the LINE COUNT at both. A
    cell that grows some other way is `grows` -- named, not silently folded into
    either, because a wrong fold here picks step 11's design.
    """
    a, b = small.get(cell, 0), large.get(cell, 0)
    if a == 0 and b == 0:
        return "absent"
    if a == b:
        return "constant"
    if a == n_small and b == n_large:
        return "per-line"
    return "grows" if b > a else "shrinks"


def cellset(d: dict) -> frozenset:
    return frozenset(c for c, v in d.items() if v > 0)


def compare_sets(a: dict, b: dict) -> tuple:
    """(shared, only_a, only_b) as sorted address lists."""
    sa, sb = cellset(a), cellset(b)
    return (sorted(sa & sb), sorted(sa - sb), sorted(sb - sa))


def scored(name: str, ok: bool | None) -> str:
    return f"  {name}: " + ("HIT" if ok else ("unscored" if ok is None
                                              else "🔴 MISS"))


# --------------------------------------------------------------------- fixtures
def fixtures() -> dict:
    return {
        "A2      BAS": ascii_program(SMALL_N),
        "A100    BAS": ascii_program(LARGE_N),
    }


def cases(dsk_note: str = "") -> list:
    """(tag, typed lines, expected fence value or None).

    ⚠️ Direct-mode exec lines stay <=38 columns and stored lines <=34, which is
    why the sequential arm's program is split the way it is.
    """
    seq = [
        '10 OPEN"%s"FOR INPUT AS#1',
        "20 IF EOF(1)THEN 40",
        "30 LINE INPUT#1,A$:N=N+1:GOTO 20",
        "40 CLOSE:PRINT CHR$(64)+CHR$(66);N",
        "RUN",
    ]
    return [
        ("quiet",     ["REM"],                                      None),
        ("loadTokS",  ['LOAD"S.BAS"'],                              None),
        ("loadTokL",  ['LOAD"L.BAS"'],                              None),
        ("asciiL2",   ['LOAD"A2.BAS"', "RUN"],                      SMALL_N),
        ("asciiL100", ['LOAD"A100.BAS"', "RUN"],                    LARGE_N),
        ("merge2",    ['MERGE"A2.BAS"', "RUN"],                     SMALL_N),
        ("merge100",  ['MERGE"A100.BAS"', "RUN"],                   LARGE_N),
        ("saveTok",   ['LOAD"A100.BAS"', 'SAVE"T.BAS"', "RUN"],     LARGE_N),
        ("saveAsc",   ['LOAD"A100.BAS"', 'SAVE"U.BAS",A', "RUN"],   LARGE_N),
        ("seq2",      [s % "A2.BAS" if "%s" in s else s for s in seq],
                      SMALL_N + 1),
        ("seq100",    [s % "A100.BAS" if "%s" in s else s for s in seq],
                      LARGE_N + 1),
    ]


# ------------------------------------------------------------------- selftest
def selftest() -> int:
    ok = {}

    p = ascii_program(3)
    ok["A1 fixture has n+1 records and the $1A terminator"] = (
        p.count(b"\r\n") == 4 and p.endswith(b"\x1a"))
    ok["A2 fixture's line numbers are 10,20,30"] = (
        p.startswith(b"10 A=A+1\r\n20 A=A+1\r\n30 A=A+1\r\n"))
    try:
        ascii_program(0)
        ok["A3 a zero-line fixture is REFUSED"] = False
    except ValueError:
        ok["A3 a zero-line fixture is REFUSED"] = True

    ok["A4 sectors() rounds UP and 512 is one sector"] = (
        sectors(1) == 1 and sectors(512) == 1 and sectors(513) == 2)

    scr = " " * 40 + "@B 100" + " " * 34
    ok["A5 read_fence reads the marked integer"] = read_fence(scr) == 100
    ok["A6 NEGATIVE: an unmarked screen reads None"] = (
        read_fence("Ok" + " " * 78) is None)
    ok["A7 NEGATIVE: a fence with no number reads None"] = (
        read_fence(" " * 40 + "@B" + " " * 38) is None)

    base = {0x1000: 5, 0x2000: 3}
    case = {0x1000: 5, 0x2000: 9, 0x3000: 1}
    d = deltas(base, case)
    ok["A8 deltas drops the unchanged cell and keeps the rest"] = (
        d == {0x2000: 6, 0x3000: 1})

    sm, lg = {1: 1, 2: 2, 3: 4}, {1: 1, 2: 100, 3: 9}
    ok["A9 constant is only for EQUAL counts"] = (
        classify(sm, lg, 1, 2, 100) == "constant")
    ok["A10 per-line needs BOTH counts to equal the line count"] = (
        classify(sm, lg, 2, 2, 100) == "per-line")
    ok["A11 NEGATIVE: a cell that merely grows is NOT per-line"] = (
        classify(sm, lg, 3, 2, 100) == "grows")
    ok["A12 NEGATIVE: an unseen cell is absent, not constant"] = (
        classify(sm, lg, 9, 2, 100) == "absent")

    sh, oa, ob = compare_sets({1: 1, 2: 1}, {2: 1, 3: 1})
    ok["A13 compare_sets splits shared / only-a / only-b"] = (
        sh == [2] and oa == [1] and ob == [3])
    ok["A14 NEGATIVE: a zero count is not membership"] = (
        compare_sets({1: 0, 2: 1}, {2: 1})[1] == [])

    cs = cases()
    tags = [t for t, _l, _e in cs]
    ok["A15 every arm has a unique tag and quiet is first"] = (
        len(set(tags)) == len(tags) and tags[0] == "quiet")
    seq100 = dict((t, l) for t, l, _e in cs)["seq100"]
    ok["A16 the sequential arm interpolated its file name"] = (
        'OPEN"A100.BAS"FOR INPUT AS#1' in seq100[0] and "%s" not in seq100[0])
    ok["A17 every typed exec line is <=38 columns"] = all(
        len(ln) <= 38 for _t, lines, _e in cs for ln in lines)
    ok["A18 every STORED line is <=34 columns"] = all(
        len(ln) <= 34 for _t, lines, _e in cs for ln in lines
        if ln[:1].isdigit())

    for k, v in ok.items():
        print(f"  {'PASS' if v else '🔴 FAIL'}  {k}")
    bad = [k for k, v in ok.items() if not v]
    print(f"selftest: {'🔴 RED' if bad else 'GREEN'} "
          f"({len(ok) - len(bad)}/{len(ok)})")
    return 1 if bad else 0


# ----------------------------------------------------------------------- main
def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    only = None
    for a in sys.argv[1:]:
        if a.startswith("--arms="):
            only = set(a.split("=", 1)[1].split(","))

    tmpd = tempfile.mkdtemp(prefix="mergeshape-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ms")
    dsk, sizes, _per = LR.build(seeded, tmpd, "ms", extra=fixtures())
    fx = fixtures()
    a2, a100 = len(fx["A2      BAS"]), len(fx["A100    BAS"])
    print(f"tokenised images: S={sizes['S']} B  L={sizes['L']} B")
    print(f"ASCII fixtures:   A2={a2} B ({sectors(a2)} sector) "
          f"A100={a100} B ({sectors(a100)} sectors)")
    if sectors(a100) < 2:
        sys.exit("REFUSING: the LARGE ASCII fixture fits in ONE sector, so a "
                 "per-sector cell and a per-file cell would be numerically "
                 "identical and §8.9's question could not be answered")

    got, fence = {}, {}
    for tag, lines, want in cases():
        if only and tag not in only:
            continue
        got[tag] = HC.run(f"ms-{tag}", lines, dsk)
        fence[tag] = read_fence(HC.CAPTURE.get(f"ms-{tag}") or "")
        n = sum(got[tag].values())
        note = "" if want is None else f"  fence={fence[tag]} (want {want})"
        print(f"  {tag:10} {n:7d} hit(s) over "
              f"{sum(1 for v in got[tag].values() if v):3d} cell(s){note}")

    if "quiet" not in got:
        sys.exit("REFUSING: no quiet baseline was run; every delta below would "
                 "be an absolute count including boot and the 60 Hz timer hook")
    if not got["quiet"]:
        sys.exit("REFUSING: the quiet baseline read NOTHING -- no breakpoint "
                 "ever fired, so 'MERGE enters no cell' would be the "
                 "instrument, not the machine")

    # --- every self-proving arm must have proved itself, BEFORE any reading ---
    print("\n=== SELF-PROOF: did each verb actually do its job? ===")
    proved = {}
    for tag, _lines, want in cases():
        if tag not in got or want is None:
            continue
        proved[tag] = fence[tag] == want
        print(f"  {'PASS' if proved[tag] else '🔴 FAIL'}  {tag}: read "
              f"{fence[tag]} line(s), fixture has {want}")
    if proved and not all(proved.values()):
        print("🔴 AT LEAST ONE ARM'S VERB DID NOT SUCCEED. Its counts are the "
              "shape of a FAILURE, which looks like data. Nothing below is "
              "read until that arm is fixed.")
        return 1

    base = got["quiet"]
    d = {t: deltas(base, g) for t, g in got.items() if t != "quiet"}

    print("\n=== PER-CELL DELTA vs quiet ===")
    for cell in CELLS:
        row = {t: v.get(cell, 0) for t, v in d.items()}
        if not any(row.values()):
            continue
        mark = {H_NULO: " <- $FE5D the crossing", H_BINL: " <- $FE76 H.BINL",
                H_SAVE: " <- $FE6C H.SAVE",
                H_FILE: " <- H_FILE (control)"}.get(cell, "")
        print(f"  ${cell:04X}  " +
              "  ".join(f"{t}={row[t]:+d}" for t in row if row[t]) + mark)

    print("\n=== P1: IS THE CROSSING PER-FILE OR PER-LINE? ===")
    verdicts = {}
    for name, (s, l) in (("MERGE", ("merge2", "merge100")),
                         ("ASCII LOAD", ("asciiL2", "asciiL100")),
                         ("seq channel", ("seq2", "seq100"))):
        if s not in d or l not in d:
            continue
        v = classify(d[s], d[l], H_NULO, SMALL_N, LARGE_N)
        verdicts[name] = v
        print(f"  {name:12} $FE5D: {d[s].get(H_NULO, 0)} at {SMALL_N} lines, "
              f"{d[l].get(H_NULO, 0)} at {LARGE_N} lines -> {v}")

    print("\n=== P2: IS MERGE THE SAME MECHANISM AS ASCII LOAD? ===")
    if "merge100" in d and "asciiL100" in d:
        sh, om, oa = compare_sets(d["merge100"], d["asciiL100"])
        print(f"  shared cells      : {' '.join('$%04X' % c for c in sh)}")
        print(f"  MERGE only        : {' '.join('$%04X' % c for c in om) or '(none)'}")
        print(f"  ASCII LOAD only   : {' '.join('$%04X' % c for c in oa) or '(none)'}")

    print("\n=== P3: WHAT SCALES, AND DOES THE CHANNEL PATH SCALE THE SAME? ===")
    for tag in ("merge100", "asciiL100", "seq100", "loadTokL"):
        if tag not in d:
            continue
        sm = {"merge100": "merge2", "asciiL100": "asciiL2",
              "seq100": "seq2", "loadTokL": "loadTokS"}[tag]
        if sm not in d:
            continue
        grew = [(c, d[sm].get(c, 0), d[tag].get(c, 0)) for c in CELLS
                if d[tag].get(c, 0) - d[sm].get(c, 0) >= 2]
        print(f"  {tag:10} cells that grow vs {sm}: " +
              ("  ".join(f"${c:04X} {a}->{b}" for c, a, b in grew) or "(none)"))

    print("\n=== P4/P5: SAVE ===")
    for tag in ("saveTok", "saveAsc"):
        if tag not in d:
            continue
        print(f"  {tag:8} $FE5D={d[tag].get(H_NULO, 0):+d}  "
              f"$FE6C={d[tag].get(H_SAVE, 0):+d}  "
              f"$FE76={d[tag].get(H_BINL, 0):+d}")
    if "saveTok" in d and "saveAsc" in d:
        sh, ot, oa = compare_sets(d["saveTok"], d["saveAsc"])
        print(f"  tokenised-only cells: "
              f"{' '.join('$%04X' % c for c in ot) or '(none)'}")
        print(f"  ASCII-only cells    : "
              f"{' '.join('$%04X' % c for c in oa) or '(none)'}")

    print("\n--- PREDICTIONS SCORED ---")
    print(scored("P1 MERGE's crossing is CONSTANT across line count",
                 verdicts.get("MERGE") == "constant"
                 if "MERGE" in verdicts else None))
    p2 = None
    if "merge100" in d and "asciiL100" in d:
        p2 = cellset(d["merge100"]) == cellset(d["asciiL100"])
    print(scored("P2 MERGE and ASCII LOAD enter the same cell SET", p2))
    p3 = None
    if "merge100" in d and "merge2" in d and "seq100" in d and "seq2" in d:
        mg = {c for c in CELLS if d["merge100"].get(c, 0)
              - d["merge2"].get(c, 0) >= 2}
        sq = {c for c in CELLS if d["seq100"].get(c, 0)
              - d["seq2"].get(c, 0) >= 2}
        p3 = bool(mg) and bool(mg & sq)
        print(f"     MERGE scales on {sorted('$%04X' % c for c in mg)}; "
              f"the channel loop scales on {sorted('$%04X' % c for c in sq)}")
    print(scored("P3 MERGE scales on a cell the channel path also moves", p3))
    # 🔴 THE SAVE ARMS LOAD A FILE FIRST, SO THEIR RAW DELTA IS TWO OPERATIONS.
    # Round 1 scored P4 against `d["saveTok"]` directly and read $FE5D = +2 as a
    # MISS. It is not: one of those two crossings is the `LOAD"A100.BAS"` the arm
    # needs in order to have a program to save. `asciiL100` runs exactly that
    # load and nothing else, so subtracting it leaves the SAVE's own traffic.
    # The claim was right and the PREDICATE was wrong -- which is its own lesson:
    # a prediction is scored by the quantity it names, and naming the arm rather
    # than the operation put a second verb inside it.
    def save_only(tag):
        return {c: d[tag].get(c, 0) - d["asciiL100"].get(c, 0) for c in CELLS}

    p4 = p5 = None
    if "saveTok" in d and "asciiL100" in d:
        so = save_only("saveTok")
        print(f"  saveTok MINUS its own load: $FE5D={so[H_NULO]:+d}  "
              f"$FE6C={so[H_SAVE]:+d}  $FE76={so[H_BINL]:+d}  "
              f"$FE8A={so[0xFE8A]:+d} (per-byte)  $FFCF={so[0xFFCF]:+d}")
        p4 = so[H_NULO] == 1 and so[H_BINL] == 0
    print(scored("P4 tokenised SAVE crosses ONCE (net of its own load) and "
                 "skips $FE76", p4))
    if "saveTok" in d and "saveAsc" in d:
        p5 = cellset(d["saveTok"]) == cellset(d["saveAsc"])
    print(scored("P5 ASCII SAVE enters the same cell set as tokenised SAVE", p5))

    print("\n=== CONTROLS ===")
    ctl = {}
    ctl["ctrl_cross: a tokenised LOAD does NOT move H_FILE"] = (
        d.get("loadTokS", {}).get(H_FILE, 0) == 0
        if "loadTokS" in d else True)
    ctl["ctrl_scale: SOMETHING is seen to scale S -> L on the tokenised "
        "control, or the counter is blind and every 'constant' below is "
        "the instrument"] = (
        any(d.get("loadTokL", {}).get(c, 0) - d.get("loadTokS", {}).get(c, 0)
            >= 2 for c in CELLS) if "loadTokL" in d and "loadTokS" in d
        else True)
    ctl["ctrl_cross2: the crossing $FE5D moved AT ALL for MERGE"] = (
        d.get("merge100", {}).get(H_NULO, 0) > 0 if "merge100" in d else True)
    for k, v in ctl.items():
        print(f"  {'PASS' if v else '🔴 FAIL'}  {k}")
    return 0 if all(ctl.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
