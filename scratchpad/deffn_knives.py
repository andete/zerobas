#!/usr/bin/env python3
"""D-DEFFNKNIFE — the knife suite `deffn-acceptance` did not have.

69 subject rows agree with two reference machines and NOT ONE OF THEM had been
shown capable of disagreeing about the shipping implementation. `deffn-selftest`
mutation-tests the CLASSIFIER against planted face tables (18/18); that is a
claim about the instrument's arithmetic, not about whether the ROW SET would
catch a defect in `basic/deffn.asm` or `sub/deffn.asm`. K-DE1
(`scratchpad/deffn_de_knife.py`) was the only knife that existed. This is the
rest.

EVERY PREDICTION BELOW WAS WRITTEN BEFORE THE RUN, and the misses are scored.

House rules, each of which has cost this project a measurement:
  * the PROBE is the subject, never `make <gate>` -- make exits 2 for ANY failed
    recipe, so a runner shelling out to a target cannot tell a tree fault from
    an instrument fault [[injjudge-slice]];
  * restore by WRITING THE BYTES, never shutil.copy2 (copy2 preserves mtime and
    make then rebuilds nothing);
  * `rm -rf build` before EVERY build, because a write landing in the same mtime
    tick as the previous restore can still leave make deciding nothing changed;
  * hash ALL THREE artefacts and assert the RIGHT ONE moved. This is a two-ROM
    tree: a `sub/*.asm` cut moves `build/sub.rom` and leaves `basic-reloc.rom`
    byte-identical; a `basic/*.asm` cut does the mirror (and also moves the
    merged `zerobas-main-eu.rom`). Getting that expectation the wrong way round
    is how a perfect cut reads as "the knife did not take";
  * cut a VALUE, not a CALL -- deleting the only call to a routine fails
    `make deadcode` and so builds no ROM;
  * parse with `probe_report.parse()`, the supported entry point (D-ROWSHAPE),
    and CALIBRATE it on a clean / planted / truncated report before the baseline;
  * 🔴 A BLANK IS NOT A DIVERGENCE. The probe scores `<NO OUTPUT>` as `....`,
    not `DIFF`, so a knife whose failure mode is "nothing happened" reddens
    NOTHING. K-SF1 exists to find out whether that is this row set's condition.

⚠️ PAGE 1 HAS ~2 B FREE. Every main-side cut here is SIZE-NEUTRAL by
construction (`ld d,b`->`ld d,h`, `jp z,X`->`jp z,Y`, `cp N`->`cp M`); the
sub-side ones may shrink but never grow. A knife that cannot be built is not a
knife.

--------------------------------------------------------------------------
THE KNIVES, and what each claims

K-DF1  the falsified compare, RESTORED.  sub/deffn.asm's ceiling was
       `cp low FN_PAREA_END` and D-DEFFNLAND §3.1 measured that form at 44 of
       69 rows red, because FN_CELLS 3->11 had slid FN_PAREA_END to $EB00 and
       `low` of it was 0.  🔴 PREDICTION: **REDDENS NOTHING TODAY.** The same
       slice that fixed the compare also deleted FN_REQ (FN_CELLS 11 -> 10,
       §4.1), which slid FN_PAREA back down to $EA9C and FN_PAREA_END to
       $EAFF -- so `low FN_PAREA_END` is $FF again and the old form is once
       more EXACTLY right on every reachable FN_SLOTP ($9C + 11k, k=0..9).
       The 44-row defect is not reproducible on this layout. That makes the
       handoff's "a knife restoring that old compare reddens o.p3" a claim
       about a LAYOUT that no longer exists, and it is scored as a miss of
       MINE if o.p3 does redden.
K-CE1  the ceiling one slot too LOW  (`cp FN_AREA` -> `cp FN_AREA-FN_SLOTSZ`).
       PREDICT {o.p9}: eight formals still bind, the ninth does not. o.p8 is
       the separating control on one side, o.p10..o.p16 (already ERR 5) on the
       other.
K-CE2  the ceiling one slot too HIGH (`cp FN_AREA` -> `cp FN_AREA+FN_SLOTSZ`).
       PREDICT {o.p10}: a tenth formal is accepted, which is the direction the
       OLD test also got wrong (a wrapped FN_SLOTP read as legal) and the one
       a single knife here would have left uncertified.
K-DE2  fn_leave's DE (`ld d,b / ld e,c` -> `ld d,h / ld e,l`). An INT-typed
       factor returns its value in DE with FAC unwritten, so the epilogue hands
       back a text cursor instead. PREDICT the SIX rows whose FUNCTION resolves
       INT -- {o.defint, o.dynaddr, o.fnpct, o.realcell, o.suffn, o.varptr} --
       which is a DIFFERENT set from K-DE1's 31, because K-DE1 destroys the
       ACTUAL's value (an integer literal is FACTYP=2 too) and this destroys
       the RESULT's. Same class, disjoint evidence.
K-PR1  PRINT's item classification (`jp z,exp_strvar` -> `jp z,exp_num`). The
       arm that sends a `$DE` item down the string path. PREDICT
       {b.str, o.defstr, o.quotedcolon} -- the three rows print.asm's own
       comment names. 🔴 o.numstr must stay GREEN AND IS NOT EVIDENCE: it wants
       ERR 13 and the knife produces ERR 13 for a different reason
       [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
K-RT1  "the FN's own type IS its result type" (dfn_bodydone's
       `ld a,(FN_RTYPE)` -> `ld a,4` at the $FFFF result slot). PREDICT
       {o.defint, o.fnpct}: the two rows whose result is INT-coerced and whose
       body is fractional. o.fnbang / o.defintbang are the single-typed twins
       and must stay green -- that is the o.fnpct 2 / o.fnbang 2.5 pair the
       handoff names, cut from the type side.
K-FE1  raise_error's FN_FEND reset (`ld (FN_FEND),a` -> `ld (FN_TYP),a`). A
       fault inside an FN body must not leave the shadow frame standing.
       🔴 RUN 1 PREDICTED {o.errrestore} AND MISSED: the knife reddened
       NOTHING. o.errrestore is the row `basic/interp.asm` and
       `sub/arrays.asm` both named as "the row that says so", and it is BLIND
       to the reset -- `X/0` is a DEFERRED error (fp_runtime_error's header:
       the float ops "have no mid-expression unwind, only SET FPERR and yield
       a defined value (0)", the abort "realized at the statement boundary"),
       so `Y=FNA(2)` returns NORMALLY, fn_leave restores the frame the
       ordinary way, and raise_error runs with nothing stale to reset.
       The row set had NO row for this guard. o.errfend18 / o.errfend13 were
       then measured on both references (scratchpad/deffn_fend_probe.out) and
       added: an IMMEDIATE `jp raise_error` from inside a LIVE frame, where
       the trap path resets SP and fn_leave never runs. PREDICT
       {o.errfend13, o.errfend18} -- and o.errrestore staying green is the
       separating control, since the two differ only in WHICH error the body
       raises.
K-SF1  fn_enter's FN_STK_FLOOR, removed (`cp high FN_STK_FLOOR` -> `cp 0`;
       CF is never set by `cp 0`). 🔴 RUN 1 PREDICTED **NO DIFF AT ALL** and
       b.recurse going BLANK -- the reasoning being that the failure mode of
       an unbounded recursion is a machine that says nothing, and the probe
       scores a blank as `....` NOT MEASURED rather than as a divergence.
       THAT MISSED, in the good direction: b.recurse came back `DIFF`. The
       runaway produces a READING, not a silence, so the floor IS pinned by a
       scored row. PREDICT {b.recurse}.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "probes" / "lib"))
import probe_report                                               # noqa: E402

SRCS = [ROOT / p for p in ("basic/deffn.asm", "basic/print.asm",
                           "basic/interp.asm", "sub/deffn.asm")]
ROMS = [ROOT / "build/basic-reloc.rom", ROOT / "build/sub.rom",
        ROOT / "build/zerobas-main-eu.rom"]
RNAMES = ["basic-reloc.rom", "sub.rom", "zerobas-main-eu.rom"]
ORIG = {p: p.read_text() for p in SRCS}
PROBE = ["python3", "probes/basic/basic_probe_deffn.py", "--gate", "--strict"]

MAIN_MOVES = {"basic-reloc.rom", "zerobas-main-eu.rom"}
SUB_MOVES = {"sub.rom"}

# (name, file, old, new, predicted DIFF labels, predicted BLANK labels, moves)
KNIVES = [
    ("K-DF1  the falsified compare restored: `cp low FN_PAREA_END`",
     ROOT / "sub/deffn.asm",
     "                ld      c,a                 ; C = the header type\n"
     "                ld      a,(FN_SLOTP)\n"
     "                sub     low FN_PAREA        ; A = the next slot's byte offset\n"
     "                jp      c,dfn_err5          ; ...wrapped off the top of the page\n"
     "                cp      FN_AREA\n"
     "                jp      nc,dfn_err5         ; past the ninth formal\n",
     "                ld      c,a                 ; C = the header type\n"
     "                ld      a,(FN_SLOTP)\n"
     "                cp      low FN_PAREA_END    ; K-DF1\n"
     "                jp      nc,dfn_err5\n",
     set(), set(), SUB_MOVES),

    ("K-CE1  ceiling one slot too LOW:  cp FN_AREA -> cp FN_AREA-FN_SLOTSZ",
     ROOT / "sub/deffn.asm",
     "                cp      FN_AREA\n"
     "                jp      nc,dfn_err5         ; past the ninth formal\n",
     "                cp      FN_AREA-FN_SLOTSZ   ; K-CE1\n"
     "                jp      nc,dfn_err5         ; past the ninth formal\n",
     {"o.p9"}, set(), SUB_MOVES),

    ("K-CE2  ceiling one slot too HIGH: cp FN_AREA -> cp FN_AREA+FN_SLOTSZ",
     ROOT / "sub/deffn.asm",
     "                cp      FN_AREA\n"
     "                jp      nc,dfn_err5         ; past the ninth formal\n",
     "                cp      FN_AREA+FN_SLOTSZ   ; K-CE2\n"
     "                jp      nc,dfn_err5         ; past the ninth formal\n",
     {"o.p10"}, set(), SUB_MOVES),

    ("K-DE2  fn_leave's DE: `ld d,b / ld e,c` -> `ld d,h / ld e,l`",
     ROOT / "basic/deffn.asm",
     "                ld      d,b\n"
     "                ld      e,c                 ; DE = the result, intact\n",
     "                ld      d,h                 ; K-DE2\n"
     "                ld      e,l                 ; K-DE2\n",
     {"o.defint", "o.dynaddr", "o.fnpct", "o.realcell", "o.suffn", "o.varptr"},
     set(), MAIN_MOVES),

    ("K-PR1  PRINT's FN item arm: `jp z,exp_strvar` -> `jp z,exp_num`",
     ROOT / "basic/print.asm",
     "                cp      FN_TOKEN            ; $DE FN<name>[$] -> maybe a string\n"
     "                jp      z,exp_strvar\n",
     "                cp      FN_TOKEN            ; $DE FN<name>[$] -> maybe a string\n"
     "                jp      z,exp_num           ; K-PR1\n",
     {"b.str", "o.defstr", "o.quotedcolon"}, set(), MAIN_MOVES),

    ("K-RT1  the result slot's type: `ld a,(FN_RTYPE)` -> `ld a,4`",
     ROOT / "sub/deffn.asm",
     "                inc     hl\n"
     "                ld      a,(FN_RTYPE)\n"
     "                ld      (hl),a\n"
     "                ld      (FN_TYP),a\n",
     "                inc     hl\n"
     "                ld      a,4                 ; K-RT1\n"
     "                ld      (hl),a\n"
     "                ld      (FN_TYP),a\n",
     {"o.defint", "o.fnpct"}, set(), SUB_MOVES),

    ("K-FE1  raise_error's frame reset: `ld (FN_FEND),a` -> `ld (FN_TYP),a`",
     ROOT / "basic/interp.asm",
     "                ld      a,low FN_PAREA\n"
     "                ld      (FN_FEND),a\n"
     "                call    record_errline\n",
     "                ld      a,low FN_PAREA\n"
     "                ld      (FN_TYP),a          ; K-FE1\n"
     "                call    record_errline\n",
     {"o.errfend13", "o.errfend18"}, set(), MAIN_MOVES),

    ("K-SF1  fn_enter's stack floor: `cp high FN_STK_FLOOR` -> `cp 0`",
     ROOT / "basic/deffn.asm",
     "                ld      a,h\n"
     "                cp      high FN_STK_FLOOR\n"
     "                jp      c,fn_deep",
     "                ld      a,h\n"
     "                cp      0                   ; K-SF1: CF is never set\n"
     "                jp      c,fn_deep",
     {"b.recurse"}, set(), MAIN_MOVES),
]


def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def hashes():
    return tuple(hashlib.sha256(r.read_bytes()).hexdigest()[:8] if r.exists()
                 else "<none>" for r in ROMS)


def moved(base, now):
    return {n for n, b, c in zip(RNAMES, base, now) if b != c}


def restore():
    for p, t in ORIG.items():
        p.write_text(t)


def read(out):
    """(gate DIFFs, control FAILs, blank subject rows, failed address claims).

    Returns None if the report cannot be trusted -- which is a statement about
    the APPARATUS and must never be scored as "the knife reddened nothing"."""
    try:
        rows = probe_report.parse(out)
    except probe_report.ReportTruncated as e:
        print(f"        APPARATUS: {e}")
        return None
    diff, fail, blank, claim = set(), set(), set(), set()
    for r in rows:
        if r.label.startswith("claim:"):
            if r.tag == "FAIL":
                claim.add(r.label)
            continue
        if r.tag == "DIFF":
            diff.add(r.label)
        elif r.tag == "FAIL":
            fail.add(r.label)
        elif r.tag == "....":
            blank.add(r.label)
    return diff, fail, blank, claim


def calibrate():
    """The parser, on a clean report, a planted one and a truncated one."""
    W = 16
    good = [probe_report.row("ok", "o.p9", W, {"ref": "1", "zb": "1"}),
            probe_report.row("PASS", "b.ctl", W, {"ref": "6", "zb": "6"}),
            probe_report.row("--", "z.addr", W, {"ref": "-2325", "zb": "-5473"}),
            probe_report.row("PASS", "claim:z.addr", W, {"zb:z.addr": "-5473"})]
    clean = "\n".join(good) + "\n" + probe_report.footer(4, 3, "clean")
    if read(clean) != (set(), set(), set(), set()):
        print("CALIBRATION FAILED: a clean report did not read clean")
        return False
    planted = "\n".join(
        [probe_report.row("DIFF", "o.p9", W, {"ref": "1", "zb": "ERR 5 AT 60"}),
         probe_report.row("FAIL", "b.ctl", W, {"ref": "6", "zb": "7"}),
         probe_report.row("....", "o.p10", W, {"ref": "x", "zb": "<NO OUTPUT>"}),
         probe_report.row("FAIL", "claim:z.addr", W, {"zb:z.addr": "0"})]
    ) + "\n" + probe_report.footer(4, 4, "planted")
    if read(planted) != ({"o.p9"}, {"b.ctl"}, {"o.p10"}, {"claim:z.addr"}):
        print("CALIBRATION FAILED: a planted report did not read as planted")
        return False
    truncated = "\n".join(good)                      # no footer at all
    if read(truncated) is not None:
        print("CALIBRATION FAILED: a footerless report did not read as broken")
        return False
    short = "\n".join(good) + "\n" + probe_report.footer(9, 9, "lying footer")
    if read(short) is not None:
        print("CALIBRATION FAILED: a short report did not read as broken")
        return False
    print("parser calibrated: clean / planted / footerless / short all correct")
    return True


def build():
    sh(["rm", "-rf", "build"])
    r = sh(["make", "repack-machine"])
    if r.returncode:
        print("        BUILD OUTPUT (tail):")
        for l in (r.stdout + r.stderr).splitlines()[-12:]:
            print(f"          {l}")
    return r.returncode == 0


def probe(tag: str):
    """Run the probe and KEEP its report. A knife's faces are the evidence; a
    runner that only records LABELS can say a row moved and not what it said."""
    out = sh(PROBE).stdout
    (ROOT / "scratchpad" / f"knife_{tag}.out").write_text(out)
    return read(out), out


def faces_of(out: str, labels) -> dict:
    try:
        rows = probe_report.parse(out)
    except probe_report.ReportTruncated:
        return {}
    return {r.label: (r.vals.get("ref", "?"), r.vals.get("zb", "?"))
            for r in rows if r.label in labels}


def main() -> int:
    if not calibrate():
        return 3
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    knives = [k for k in KNIVES if not want or any(w in k[0] for w in want)]
    if want and not knives:
        print(f"no knife matches {want}")
        return 3
    rows = []
    try:
        print("== clean build BEFORE the baseline ==", flush=True)
        if not build():
            print("APPARATUS: repack failed on a clean tree")
            return 3
        base_h = hashes()
        got, _ = probe("base")
        print(f"baseline roms={dict(zip(RNAMES, base_h))}", flush=True)
        if got is None:
            print("APPARATUS: the baseline report is not whole")
            return 3
        if got != (set(), set(), set(), set()):
            print(f"APPARATUS: the baseline is not clean: "
                  f"diff={sorted(got[0])} ctl={sorted(got[1])} "
                  f"blank={sorted(got[2])} claim={sorted(got[3])}")
            return 3
        print("baseline: 0 DIFF, 0 control FAIL, 0 blank, 0 claim FAIL\n",
              flush=True)

        for name, src, old, new, pdiff, pblank, pmoves in knives:
            restore()
            if ORIG[src].count(old) != 1:
                print(f"APPARATUS: {name}: anchor matched "
                      f"{ORIG[src].count(old)}x in {src.name}")
                return 3
            src.write_text(ORIG[src].replace(old, new))
            if not build():
                print(f"{name}\n        BUILD FAILED -- a knife that cannot "
                      f"be run is not a knife", flush=True)
                rows.append((name, False, "build failed"))
                continue
            h = hashes()
            mv = moved(base_h, h)
            if mv != pmoves:
                print(f"{name}\n        🔴 WRONG IMAGE MOVED: {sorted(mv)}, "
                      f"expected {sorted(pmoves)} -- scoring nothing", flush=True)
                rows.append((name, False, f"moved {sorted(mv)}"))
                continue
            got, out = probe(name.split()[0])
            if got is None:
                rows.append((name, False, "report not whole"))
                print(f"{name}\n        APPARATUS: report not whole", flush=True)
                continue
            diff, fail, blank, claim = got
            ok = (diff == pdiff and blank == pblank and not fail)
            rows.append((name, ok, ""))
            print(f"{'EXACT' if ok else 'MISS '}  {name}\n"
                  f"        moved={sorted(mv)}\n"
                  f"        DIFF  want={sorted(pdiff)}\n"
                  f"              got ={sorted(diff)}\n"
                  f"        BLANK want={sorted(pblank)}  got={sorted(blank)}\n"
                  f"        control FAIL={sorted(fail)}  "
                  f"claim FAIL={sorted(claim)}", flush=True)
            for lbl, (ref, zb) in sorted(faces_of(out, diff | blank).items()):
                print(f"          {lbl:<14} ref={ref!r}  zb={zb!r}", flush=True)
    finally:
        restore()
        sh(["rm", "-rf", "build"])
        sh(["make", "repack-machine"])
        for p, t in ORIG.items():
            assert p.read_text() == t, f"{p} was not restored!"
        back = hashes()
        print(f"\nrestored: roms={dict(zip(RNAMES, back))}  "
              f"all four sources byte-identical", flush=True)

    n = sum(1 for _, ok, _ in rows if ok)
    print(f"\n{n}/{len(rows)} knife rows EXACT")
    for name, ok, why in rows:
        print(f"  {'EXACT' if ok else 'MISS '}  {name}{('  -- ' + why) if why else ''}")
    return 0 if n == len(rows) else 1


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main())
