#!/usr/bin/env python3
r"""D-OOMTAIL — the two store-overflow exits (`dpl_oom`, `ctp_oom`) after the
carve that makes the cassette one JUMP to the disk one.

The carve: ctp_oom's seven-instruction tail was byte-for-byte dpl_oom's whole
body (its own comment said "mirrors dpl_oom"), so it is now `jp dpl_oom`.
13 B of main page 1. The witness question is REACHABILITY AND BEHAVIOUR, per
path, because a shared tail serves ALL its jumps:

  ctl.ok    🟢 a small LOAD lists fine on both machines
  d.oom     disk overflow: LOAD of a ~17 KB tokenised file (dpl_oom's row)
  d.oom-l   ...and what each machine is left HOLDING (the new_prog contract)
  c.oom     cassette overflow, zerobas only: CLOAD of the same program from
            tape (ctp_oom's row -- the references HANG on tokenised tape,
            castail characterization §6/§7, so no oracle)
  c.ctl     🟢 a small CLOAD still says Ok

🔴 THE FIRST CUT USED `CLEAR 200,&H8300` AND A 5 KB FILE, AND ITS ONE GREEN ROW
WAS GREEN FOR THE WRONG REASON. Both loaders bound the store against TXTMAX --
a fixed $BB00 (sysvars.inc: the repack text ceiling) -- NOT against the CLEAR
ceiling, so a 5 KB load "overflows" nothing: d.oom printed <nothing> because
the load SUCCEEDED. And c.oom still printed `Out of memory`... from the CLEAR
itself, which on the disk machine refuses a floor under the DOS work area. A
row can only witness the oom exits by exceeding the bound the CODE tests:
$BB00 - $8001, so the fixture is ~17 KB and there is no CLEAR anywhere.
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import omsx_repl                                             # noqa: E402
import probe_tmp                                             # noqa: E402
import make_test_dsk as MK                                   # noqa: E402
import basic_probe_runtail as R                              # noqa: E402
from basic_probe_cas_verify import run_typed_scr             # noqa: E402
from cas_encode import build_cas_basic                       # noqa: E402

SIDES = {
    # 🔴 step is per TYPED LINE, and a 17 KB load runs long in EMULATED time
    # (~70 sectors through the FDC on the reference). At truncload's 2.5 s the
    # capture fired MID-LOAD: d.oom read <nothing> and d.oom-l read <NO ECHO>,
    # both of which are what "the machine was still busy" looks like. 25 s.
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=25.0,
                   reset=("", "SCREEN 0", "NEW"), missmsg="Device I/O error"),
    "zb":     dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                          "C-BIOS_MSX1_EU_REPACK_DISK"),
                   boot=8.0, step=25.0, reset=("NEW",), missmsg="load error"),
}


def big_image(n=1300):
    """An n-line tokenised program image (~13 B/line): the same POKE body on
    every line, ascending line numbers, correct final $0000 end-link."""
    body = MK.prog_bas_body()
    img = b""
    base = MK.BAS_TXTBASE
    for i in range(n):
        line = struct.pack("<HH", base + len(img) + 4 + len(body), 10 + i) + body
        img += line
    return img + b"\x00\x00"


def build_dsk(path):
    img = MK.Fat12Image()
    img.add_file("PROG", "BAS", MK.make_basic_file())
    img.add_file("BIG", "BAS", bytes([0xFF]) + big_image())
    open(path, "wb").write(img.finish())


CASES = [
    ("ctl.ok",  ['LOAD"A:PROG.BAS"', "LIST"], -1),
    ("d.oom",   ['LOAD"A:BIG.BAS"'],          -1),
    ("d.oom-l", ['LOAD"A:BIG.BAS"', "LIST"],  -1),
]
CONTROLS = {"ctl.ok": ("POKE",)}
# ⚠️ ADJUDICATED DIVERGENCE, NOT A DEFECT: TXTMAX is the repack's own $BB00
# text ceiling (basic/sysvars.inc, D-LINEMAX/D-FCH -- program capacity 14079 B,
# "CHOSEN BY MEASUREMENT", funding DETOKBUF the way the reference funds its
# file-channel buffers out of FRE(0)). A ~17 KB program therefore loads on the
# CF-3300 (~29 KB capacity) and raises Out of memory here BY DESIGN. These two
# rows print with their own tag and do not fail the run; the same rows are
# pinned in tools/filed-row-known.txt so the D-FILEDROT sweep sees them as
# measured-and-known.
ADJUDICATED = {"d.oom", "d.oom-l"}


def run_disk(side):
    cfg = SIDES[side]
    dsk = probe_tmp.tmp(f"zb_oomtail_{side}.dsk")
    build_dsk(dsk)
    cases = [("direct", list(cfg["reset"]) + list(lines))
             for _, lines, _ in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                               boot=cfg["boot"], step=cfg["step"], diska=dsk)
    return {label: R.tail_after(raw, lines[subj], cfg["missmsg"])
            for (label, lines, subj), raw in zip(CASES, caps)}


def run_cas():
    """The ctp_oom rows, zerobas only (no cassette oracle for tokenised tape)."""
    tmp = probe_tmp.tmp("zb_oomtail_cas")
    os.makedirs(tmp, exist_ok=True)
    out = {}
    big = os.path.join(tmp, "big.cas")
    open(big, "wb").write(build_cas_basic("BIGP", big_image()))
    # ~17 KB at openMSX's 3744-baud synthesis is ~50 emulated s of tape, and
    # the bound fires ~15 KB in -- the capture must sit past THAT, not past the
    # typing.
    scr, _ = run_typed_scr(None, big, [(6.0, "CLOAD"), (8.0, "\r")],
                           cap_time=100.0, timeout=180.0)
    low = scr.lower()
    # 🔴 REQUIRE THE Found: LINE TOO. The first cut scored "out of memory"
    # alone, and that message can come from a REJECTED COMMAND (the CLEAR-floor
    # detour this docstring records) -- the Found: is what proves the TAPE LOAD
    # produced it.
    out["c.oom"] = ("Out of memory" if "found:bigp" in low
                    and "out of memory" in low
                    else f"<UNEXPECTED: ...{scr[-80:].strip()}>")
    small = os.path.join(tmp, "small.cas")
    open(small, "wb").write(build_cas_basic("SM", MK.wrap_basic_line(
        MK.prog_bas_body())))
    # 🔴 at (6.0, cap 40) this row twice captured the C-BIOS BOOT SCREEN while
    # the identical rig one call earlier read BASIC text -- boot-time jitter on
    # a freshly killed emulator. Type later, capture later.
    scr, _ = run_typed_scr(None, small, [(10.0, "CLOAD"), (12.0, "\r")],
                           cap_time=60.0, timeout=140.0)
    low = scr.lower()
    # 🟢 the control: the tape is Found and NEITHER the overflow message nor
    # any error follows.
    # 🔴 THE FIRST CUT LOOKED FOR "Ok" AND THIS MACHINE'S READY PROMPT IS "ZB"
    # -- the row failed twice on a word the screen never contains, and the
    # capture's tail was s1 (VRAM $1800), which still holds the SCREEN-1 boot
    # banner on every capture: "boot text present" means nothing, a NAMED
    # positive word is the only honest check here.
    out["c.ctl"] = ("loaded" if "found:sm" in low
                    and "out of memory" not in low and "error" not in low
                    else f"<UNEXPECTED: ...{scr[-80:].strip()}>")
    return out


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
    res = {s: run_disk(s) for s in sides}
    diff, dead = [], []
    for label, _, _ in CASES:
        vals = [str(res[s].get(label)) for s in sides]
        same = len(set(vals)) == 1
        want = CONTROLS.get(label)
        alive = (not want) or all(any(t in v for t in want) for v in vals)
        if len(sides) > 1 and not same and label not in ADJUDICATED:
            diff.append(label)
        if not alive:
            dead.append(label)
        tag = ("ok" if same or len(sides) < 2
               else ("ADJ" if label in ADJUDICATED else "DIFF"))
        print(f"{tag:<4} {label:<8} "
              + "  ".join(f"{s}={res[s].get(label)!r}" for s in sides)
              + ("   [CONTROL]" if want else ""))
    if "zb" in sides:
        for label, val in run_cas().items():
            bad = val.startswith("<UNEXPECTED")
            print(f"{'FAIL' if bad else 'ok':<4} {label:<8} zb={val!r}"
                  + ("   [zb-only: references hang on tokenised tape]"))
            if bad:
                dead.append(label)
    print(f"\nDIFF vs references: {len(diff)}/{len(CASES) if len(sides) > 1 else 0}"
          + ("  " + " ".join(diff) if diff else ""))
    if dead:
        print(f"🔴 {len(dead)} row(s) FAILED/dead-control: {' '.join(dead)}")
        return 2
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
