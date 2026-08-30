#!/usr/bin/env python3
r"""D-TRUNCLOAD — a TRUNCATED tokenised BASIC file: does the reference honour the
directory's byte length, or read to the end of the SECTOR?

Filed 2026-08-30 by D-NGRAM13 (docs/spec-basic-ngram13.md §5): on a file cut off
mid-line the CF-3300 says NOTHING and zerobas says `load error`. Both end up
holding the same partial program, so the divergence is one message and (in the
line-number case) one extra empty line.

🔬 THE HYPOTHESIS THAT WAS FILED UNTESTED: the reference reads whole SECTORS and
therefore never sees a byte-level EOF -- the ZERO PADDING after the file's
recorded length reads as a `$0000` link word, which is the legitimate
end-of-program marker, so the load simply FINISHES. zerobas's `fat_io_getbyte`
honours the directory entry's size and reports EOF instead.

🎯 THE ROW THAT SEPARATES THE TWO RULES. Every fixture so far was zero-padded,
which is exactly the case where "stop at EOF" and "read the sector" produce
almost the same program -- so the readings could not tell them apart.
`GARB.BAS` is byte-for-byte the same truncated file, with the SAME recorded
size, followed by NON-ZERO garbage inside the same sector:

  * honour the length  -> identical to `zero` in every reading
  * read the sector    -> the garbage is read as program bytes and as the next
                          LINK WORD, so the two rows must differ

  t.zero      the zero-padded truncation (the D-NGRAM13 fixture)
  t.garb      the SAME truncation, non-zero padding
  t.zero-l    ...and what each machine is left holding
  t.garb-l
  ctl.ok      🟢 CONTROL: a well-formed file still loads on both
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

SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), missmsg="Device I/O error"),
    "zb":     dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                          "C-BIOS_MSX1_EU_REPACK_DISK"),
                   boot=8.0, step=2.5, reset=("NEW",), missmsg="load error"),
}

CUT = 1 + 4 + 2          # marker + link + lineno + two body bytes
GARBAGE = b"\xAA" * 64   # non-zero, and not a plausible link word


def build_dsk(path):
    img = MK.Fat12Image()
    good = MK.make_basic_file()
    img.add_file("PROG", "BAS", good)
    img.add_file("ZERO", "BAS", good[:CUT])
    # 🔴 THE DIRECTORY SIZE IS WRITTEN DOWN AFTERWARDS, ON PURPOSE. add_file
    # records len(content), so writing the garbage as content would ALSO make
    # the file longer -- and a longer file is a different question. The bytes on
    # the disk differ; the recorded LENGTH is identical to ZERO.BAS, which is
    # what makes this a controlled pair.
    img.add_file("GARB", "BAS", good[:CUT] + GARBAGE)
    _shrink_last_dir_entry(img, CUT)
    # 🔴 THE OTHER THREE PLACES THE READ CAN END, because the loader checks EOF
    # at four distinct sites and a rule read off ONE of them is a rule about
    # that site. LNO/LINK/BARE end the file progressively earlier.
    img.add_file("LNO", "BAS", good[:1 + 2])      # mid LINE NUMBER
    img.add_file("LINK", "BAS", good[:1 + 1])     # mid LINK WORD
    img.add_file("BARE", "BAS", good[:1])         # the marker, and nothing else
    # ...and a ZERO-BYTE file, which is the ONE site whose EOF arm fires before
    # CLPTR/CLINK have been set to TXTBASE at all. A rule read off the other
    # sites cannot be extended to it for free.
    img.add_file("NIL", "BAS", b"")
    open(path, "wb").write(img.finish())


def _shrink_last_dir_entry(img, size):
    off = MK.FIRST_ROOT * MK.SECTOR + (img.dir_index - 1) * 32
    struct.pack_into("<I", img.data, off + 28, size)


CASES = [
    ("t.zero",   ['LOAD"A:ZERO.BAS"'],             -1),
    ("t.garb",   ['LOAD"A:GARB.BAS"'],             -1),
    ("t.zero-l", ['LOAD"A:ZERO.BAS"', "LIST"],     -1),
    ("t.garb-l", ['LOAD"A:GARB.BAS"', "LIST"],     -1),
    ("t.lno",    ['LOAD"A:LNO.BAS"'],              -1),
    ("t.lno-l",  ['LOAD"A:LNO.BAS"', "LIST"],      -1),
    ("t.link",   ['LOAD"A:LINK.BAS"'],             -1),
    ("t.link-l", ['LOAD"A:LINK.BAS"', "LIST"],     -1),
    ("t.bare",   ['LOAD"A:BARE.BAS"'],             -1),
    ("t.bare-l", ['LOAD"A:BARE.BAS"', "LIST"],     -1),
    ("t.nil",    ['LOAD"A:NIL.BAS"'],              -1),
    ("t.nil-l",  ['LOAD"A:NIL.BAS"', "LIST"],      -1),
    ("ctl.ok",   ['LOAD"A:PROG.BAS"', "LIST"],     -1),
]
CONTROLS = {"ctl.ok": ("POKE",)}


def run_side(side):
    cfg = SIDES[side]
    dsk = probe_tmp.tmp(f"zb_truncload_{side}.dsk")
    build_dsk(dsk)
    cases = [("direct", list(cfg["reset"]) + list(lines))
             for _, lines, _ in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                               boot=cfg["boot"], step=cfg["step"], diska=dsk)
    return {label: R.tail_after(raw, lines[subj], cfg["missmsg"])
            for (label, lines, subj), raw in zip(CASES, caps)}


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
    res = {s: run_side(s) for s in sides}
    w = max(len(l) for l, _, _ in CASES)
    diff, dead = [], []
    for label, _, _ in CASES:
        vals = [str(res[s].get(label)) for s in sides]
        same = len(set(vals)) == 1
        scored = len(sides) > 1
        want = CONTROLS.get(label)
        alive = (not want) or all(any(t in v for t in want) for v in vals)
        if scored and not same:
            diff.append(label)
        if not alive:
            dead.append(label)
        tag = "--" if not scored else ("ok" if same else "DIFF")
        print(f"{tag:<4} {label:<{w}}  "
              + "  ".join(f"{s}={res[s].get(label)!r}" for s in sides)
              + ("   [CONTROL]" if want else "")
              + ("   🔴 CONTROL TEXT MISSING" if not alive else ""))
    # 🎯 THE VERDICT THIS PROBE EXISTS FOR, stated per side rather than as an
    # agreement count: whether a machine's zero-padded and garbage-padded
    # readings DIFFER is what says which rule it follows.
    for s in sides:
        for pair, what in ((("t.zero", "t.garb"), "message"),
                           (("t.zero-l", "t.garb-l"), "program")):
            a, b = (str(res[s].get(k)) for k in pair)
            rule = ("READS THE SECTOR" if a != b
                    else "honours the recorded LENGTH")
            print(f"  {s:<7} {what:<8} {a!r} vs {b!r}  -> {rule}")
    n = len(CASES)
    print(f"ROWS: {n} printed, {n if len(sides) > 1 else 0} scored"
          + (f" — {n - len(diff)} agree, {len(diff)} diverge"
             if len(sides) > 1 else " — CHARACTERIZATION (one side)"))
    if dead:
        print(f"🔴 CONTROL CARRIES NO TEXT: {' '.join(dead)}")
        return 2
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
