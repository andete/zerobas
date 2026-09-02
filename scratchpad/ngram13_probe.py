#!/usr/bin/env python3
r"""D-NGRAM13 — the disk loader's byte-get/store run, and the ERROR path it hides.

`disk_prog_load` open-codes the same six instructions three times:

    call fat_io_getbyte / jp c,dpl_err_pop / ld hl,(CLPTR) / ld (hl),a /
    inc hl / ld (CLPTR),hl

14 B x 3. Factoring it costs a frame: `dpl_err_pop` pops the ONE value the call
site guarded across `fat_io_getbyte`, and from inside a helper the helper's OWN
return address sits on top of it. The helper's error tail therefore has to drop
two, not one -- and that is a claim NO EXISTING ROW CAN SEE, because the whole
tree has no row that reaches `dpl_err_pop` at all.

🔴 THAT IS THE POINT OF THIS PROBE. A frame fix witnessed by nothing is the
D-NGRAM8 shape (a `call` moved an outward jump one frame deeper and the decline
stopped declining, unseen). So the rows come FIRST:

  d.ok        🟢 CONTROL: a WELL-FORMED tokenised program still loads and lists
  d.body      a file cut off MID-BODY -> EOF inside the body copy (the third
              site, guarded by the remaining-count push)
  d.lineno    a file cut off right after the LINK WORD -> EOF while reading the
              line number (the first two sites, guarded by the body-length push)
  d.alive     🎯 THE FRAME ROW: after the truncated load, does the machine still
              answer? A wrong pop count returns `dpl_err` to a garbage address.
              This is the ONLY row that can see the frame, and it is why the
              error rows are worth building at all.
  ctl.typed   🟢 CONTROL: a program TYPED in, listed -- never touches the loader

The disk image is built in /tmp by tools/make_test_dsk.py's own FAT12 builder.
⚠️ NOT added to the committed test720.dsk: a dozen probes read that image's
`FILES` listing, and an extra directory entry would move all of them for a
question none of them is asking.
"""
import os, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import omsx_repl                                             # noqa: E402
import probe_tmp                                             # noqa: E402
import make_test_dsk as MK                                   # noqa: E402
import basic_probe_runtail as R                              # noqa: E402

SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), missmsg="Device I/O error"),
    "zb":     dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                          "C-BIOS_MSX1_EU_REPACK_DISK"),
                   boot=8.0, step=2.5, reset=("NEW",), missmsg="load error"),
}
FAILED = "<load-failed>"


def build_dsk(path):
    """PROG.BAS (well formed) + BODY.BAS / LNO.BAS (truncated two ways)."""
    img = MK.Fat12Image()
    good = MK.make_basic_file()
    img.add_file("PROG", "BAS", good)
    # cut MID-BODY: keep the marker, link word, line number and two body bytes,
    # and stop -- no line terminator, no $0000 end-link.
    img.add_file("BODY", "BAS", good[:1 + 4 + 2])
    # cut right after the LINK WORD: the loader is mid line-number when EOF hits.
    img.add_file("LNO", "BAS", good[:1 + 2])
    # 🎯 THE FRAME FIXTURE. The value guarded across the failing read is the
    # REMAINING BODY COUNT, and on a botched pop count that is what `dpl_err`'s
    # `ret` uses as an ADDRESS. BODY.BAS's count is 7, so a wrong pop returns to
    # $0007 -- and the machine WANDERS BACK to the prompt, because the stack
    # below is the REPL's own and a stray `ret` finds a plausible address there.
    # K-N13A moved ZERO rows on that fixture. This one claims a 3000-byte line
    # and is cut after five body bytes, so the bogus return address is $0BB3:
    # mid-ROM, and nothing there is a return to anywhere.
    big = bytearray(good)
    big[1:3] = struct.pack("<H", MK.BAS_TXTBASE + 4 + 3000)   # claim a long line
    img.add_file("BIG", "BAS", bytes(big[:1 + 4 + 5]))
    open(path, "wb").write(img.finish())


CASES = [
    ("d.ok",      ['LOAD"A:PROG.BAS"', "LIST"],                    -1),
    ("d.body",    ['LOAD"A:BODY.BAS"'],                            -1),
    ("d.lineno",  ['LOAD"A:LNO.BAS"'],                             -1),
    ("d.alive",   ['LOAD"A:BODY.BAS"', 'PRINT"ZQ6"'],              -1),
    # 🔴 WHAT THE MACHINE IS LEFT HOLDING. The first cut read only the MESSAGE,
    # and the CF-3300 prints none -- which is equally consistent with "it
    # refused quietly" and "it accepted a truncated program". Those are
    # different machines and the message cannot tell them apart.
    ("d.body-l",  ['LOAD"A:BODY.BAS"', "LIST"],                    -1),
    ("d.lineno-l", ['LOAD"A:LNO.BAS"', "LIST"],                    -1),
    # ...and whether a FAILED load is allowed to destroy what was resident.
    ("d.body-res", ['10 PRINT"ZQ1"', 'LOAD"A:BODY.BAS"', "LIST"],  -1),
    ("d.bigalive", ['LOAD"A:BIG.BAS"', 'PRINT"ZQ7"'],              -1),
    ("ctl.typed", ['10 PRINT"ZQ1"', "LIST"],                       -1),
]
# Rows whose agreed reading must carry POSITIVE TEXT: two dead machines agree.
CONTROLS = {"d.ok": ("POKE",), "d.alive": ("ZQ6",), "ctl.typed": ("ZQ1",),
            "d.bigalive": ("ZQ7",)}


def run_side(side):
    cfg = SIDES[side]
    dsk = probe_tmp.tmp(f"zb_ngram13_{side}.dsk")
    build_dsk(dsk)
    cases = [("direct", list(cfg["reset"]) + list(lines))
             for _, lines, _ in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                               boot=cfg["boot"], step=cfg["step"], diska=dsk)
    out = {}
    for (label, lines, subj), raw in zip(CASES, caps):
        out[label] = R.tail_after(raw, lines[subj], cfg["missmsg"])
    return out


# 🔴 THREE ROWS HAVE NO ORACLE, AND THE NEWER PROBE ALREADY SAYS SO.
# `d.body-l`, `d.lineno-l` and `d.body-res` LIST a program stored from a
# TRUNCATED file. Its last line has no `$00` terminator, so relink's forward
# scan stops wherever RAM happens to hold one -- and the two machines reach
# these rows over different RAM history (`$FF` on the CF-3300 vs a preceding
# `NEW`'s zeros here). `10 POKE` against `10` is THE SAME STORE rendered past
# its own end, which D-TRUNCLOAD proved with a PEEK instrument rather than a
# listing.
# The owning item CLOSED 2026-08-30 at 18 scored / 18 agree / 0 diverge, and
# `scratchpad/truncload_probe.py` -- the probe that closed it -- marks six rows
# NO_ORACLE for exactly this reason and still reads 18/18 today.
# 🎯 THIS PROBE IS THE OLDER ONE AND NEVER GOT THE CLASSIFICATION, so it kept
# reporting three history rows as divergences and a scoreboard built from its
# pin counted them as outstanding CORRECTNESS debt. Marked here so the next
# reader does not re-derive it. [[no-oracle-is-about-the-comparison]]
NO_ORACLE = {"d.body-l", "d.lineno-l", "d.body-res"}


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
    res = {s: run_side(s) for s in sides}
    w = max(len(l) for l, _, _ in CASES)
    diff, dead = [], []
    for label, _, _ in CASES:
        vals = [str(res[s].get(label)) for s in sides]
        zb = str(res["zb"].get(label)) if "zb" in res else "-"
        same = len(set(vals)) == 1
        scored = len(sides) > 1
        want = CONTROLS.get(label)
        alive = (not want) or all(any(t in v for t in want) for v in vals)
        if scored and not same and label not in NO_ORACLE:
            diff.append(label)
        if not alive:
            dead.append(label)
        tag = ("--" if not scored
               else ("NO-OR" if label in NO_ORACLE and not same
                     else ("ok" if same else "DIFF")))
        print(f"{tag:<4} {label:<{w}}  "
              + "  ".join(f"{s}={res[s].get(label)!r}" for s in sides)
              + ("   [CONTROL]" if want else "")
              + ("   🔴 CONTROL TEXT MISSING" if not alive else ""))
    n = len(CASES)
    if len(sides) > 1:
        nno = sum(1 for l, _, _ in CASES if l in NO_ORACLE
                  and len({str(res[s].get(l)) for s in sides}) != 1)
        print(f"ROWS: {n} printed, {n - nno} scored — {n - len(diff) - nno} "
              f"agree, {len(diff)} diverge, {nno} NO-ORACLE (RAM history "
              f"decides the listing, not the loader — see truncload_probe)")
    else:
        print(f"ROWS: {n} printed, 0 scored — CHARACTERIZATION (one side)")
    if dead:
        print(f"🔴 {len(dead)} POSITIVE CONTROL(S) CARRY NO TEXT: {' '.join(dead)}"
              f" — a dead machine agrees with a dead machine")
        return 2
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
