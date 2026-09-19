#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CROSSABI: the REGISTER CONTRACT at the main->disk crossing.

D-LOADPROTO (§6.6u) settled the control flow: main calls `$FE67` once and the
disk ROM runs the whole sector loop on its own side. The next thing a faithful
implementation needs is the ARGUMENTS -- what main puts in which register before
that call, and what it hands back. This measures that.

🎯 BOTH ENDS, AND BOTH BREAKPOINTS ARE IN THE PUBLISHED HOOK TABLE. A claimed
cell holds `F7 <slot> <lo> <hi> C9` (5 bytes, RAM). A breakpoint on the CELL
fires before the `F7` runs -- that is the IN contract. A breakpoint on CELL+4,
the trailing `C9`, fires after the handler has returned and before control goes
back to main -- that is the OUT contract. Both addresses are RAM cells in the
published table, so nothing here reaches into the reference ROM.

🔑 AND POINTERS ARE IDENTIFIED BY CONTENT, NOT BY A GUESSED NAME. For any
register holding a RAM address the probe reads the bytes there and renders them
printable. If a register points at the file name the user typed, the DUMP SAYS
SO -- which is evidence, where "HL is probably FILNAM" would be a guess. The
tree has no MSX work-area symbol table to match against, and inventing one would
be exactly the "a documented name is narrower than its class" error §6.6s paid
for at four cells.

🔬 THE CASE SET SEPARATES NAME FROM SIZE, which two cases cannot.
  loadS / loadL  tokenised, 3 vs 29 data sectors -- but the NAMES differ too, so
                 a register that moves between them is unattributable.
  loadA / loadQ  the SAME BYTES under two names, one short and one 8 characters.
                 Identical content, different name: whatever moves here is the
                 name, and whatever moves between S and L but not here is size.
  mergeA         does `MERGE` hand over the same way at the same cell?
  saveT          `SAVE` goes through `$FE6C` (D-HOOKCOUNT: only SAVE enters it).
                 Same test, other verb, so the shape can be compared.

🔴 CONTROLS. K1 and K3 are carried over from D-LOADPROTO because they are what
make a caller region credible at all; K5-K7 are new and K5 is the one the loop
asked for -- an arm that goes red if a capture happens at the wrong moment.
  K1 DISCRIM   `H.TIMI $FD9F`'s caller is the BIOS interrupt handler in main
               page 0. A classifier that cannot say that says nothing.
  K3 NEGATIVE  the `quiet` case types no verb; the trace must be empty.
  K5 TIMING    🔴 a breakpoint on CELL+1 -- the SLOT BYTE -- must NEVER fire. It
               is an inline operand of `RST 30h`, consumed by the CALLF handler
               as DATA and never fetched as an instruction. If it fires, the
               "a breakpoint fires BEFORE the instruction at that address runs"
               model is wrong, and every register in this probe was sampled at
               an unknown moment. This is the arm that makes the captures mean
               anything.
  K6 CLAIMED   the cell must actually read `F7 .. .. .. C9`. An entry capture on
               an UNCLAIMED cell (a bare `C9`) would be a capture of nothing.
               §2 of `disk/docs/expansion-protocol.md` permits reading a cell for
               its slot and idiom, which is all this reads.
  K7 PAIRING   every entry must have exactly one matching exit. An unmatched
               pair means the handler left by a route the probe cannot see, and
               the OUT contract would be a guess.

🔴 CLEAN ROOM. Registers, RAM (the hook cells, the stack top, and whatever a
register points at) and the slot-select state -- the surface
`disk/docs/expansion-protocol.md` §7 already operates on. No ROM byte is read, no
hook target is followed, nothing is single-stepped into ROM, nothing is
disassembled. Reference-internal addresses are never printed; registers that hold
them are reported as a REGION.
"""
import argparse
import os
import struct
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))

# 🎯 REUSE THE CLASSIFIER D-LOADPROTO ALREADY MUTATION-PROVED rather than
# writing a second one that could drift from it.
from loadproto_probe import region, _sub                      # noqa: E402

REF = "National_CF-3300"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 30.0, 8.0

# 🔴 THE CELLS THIS TRAPS CHANGED AFTER THE FIRST RUN, AND THE REASON IS THE
# FINDING. `$FE67` and `$FE6C` hold a bare `C9`: main calls them, they RET, and
# NOTHING crosses. An entry counter cannot see that -- an offered extension point
# nobody took and a real crossing are both "entered" once. The cells that are
# CLAIMED (`F7 <slot> <lo> <hi> C9`) and that `LOAD` enters are `$FE5D` and
# `$FE76`, so those are where a register contract can exist at all.
C_NULO = 0xFE5D          # CLAIMED; entered by LOAD, MERGE, BLOAD, SAVE and OPEN
C_BINL = 0xFE76          # CLAIMED; entered by LOAD (and NOT by BLOAD, §6.6s)
C_VERB = 0xFE67          # unclaimed -- kept trapped so the 1-entry/0-exit
C_SAVE = 0xFE6C          # signature of an unclaimed cell stays on the record
C_TIMI = 0xFD9F          # K1
CELLS = (C_NULO, C_BINL, C_VERB, C_SAVE)
CLAIMED_EXPECTED = (C_NULO, C_BINL)
REGS = ("AF", "BC", "DE", "HL", "IX", "IY")
DUMPREGS = ("BC", "DE", "HL", "IX", "IY")
CAP = 400

ASCII_BAS = b"10 REM Z\r\n20 REM Z\r\n"
# The BSAVE header is the documented `$FE` + start + end + exec (basic/bload.asm
# implements it from the same public description); $A5 is distinguishable from
# unwritten RAM and from $FF (D-BLOADARM).
BIN_START, BIN_LEN, BIN_FILL = 0xD000, 16, 0xA5
BSAVE_BIN = (b"\xFE" + struct.pack("<HHH", BIN_START, BIN_START + BIN_LEN - 1,
                                    BIN_START) + bytes([BIN_FILL]) * BIN_LEN)


TCL = r'''
proc __w16 {a} { expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]} }
set ::n 0
set ::bad 0
set ::lf [open {@OUT@} w]
proc __lg {s} { puts $::lf $s ; flush $::lf }
proc __caller {} {
    set c [__w16 [reg SP]]
    set p [expr {$c >> 14}]
    set s [get_selected_slot $p]
    set sec [lindex $s 1]
    if {$sec eq ""} { set sec 0 }
    return "$c [lindex $s 0] $sec"
}
# 12 bytes at a RAM pointer, hex; "-" when the value is not in RAM
proc __dump {v} {
    if {$v < 32768} { return "-" }
    set o ""
    for {set i 0} {$i < 32} {incr i} {
        append o [format %02X [debug read memory [expr {($v + $i) & 0xFFFF}]]]
    }
    return $o
}
proc __cap {tag} {
    if {$::n >= @CAP@} return
    incr ::n
    set r ""
    foreach x {@REGS@} { append r " $x=[reg $x]" }
    foreach x {@DUMPREGS@} { append r " M$x=[__dump [reg $x]]" }
    __lg "$::n $tag [__caller] SP=[reg SP]$r"
}
# K5: the SLOT BYTE is an inline operand, never an opcode fetch. If this fires,
# every capture above was taken at an unknown moment.
proc __k5 {a} { incr ::bad ; __lg "K5FIRED $a" }
# 🔴 ITS OWN COUNTER. The first run shared one cap between the timer hook and
# the verb captures, and 400 timer samples were spent before the verb ran: IN=0
# and OUT=0 read exactly like "the verb never crossed" when it meant "the probe
# stopped logging". A control that is allowed to starve the subject is not a
# control.
set ::tn 0
proc __timi {} {
    if {$::tn >= 40} return
    incr ::tn
    __lg "T$::tn TIMI [__caller] SP=[reg SP]"
}
proc __meta {} {
    set f [open {@SUM@} w]
    puts $f "BAD $::bad EVENTS $::n"
    # 🔑 THE WHOLE PUBLISHED TABLE, NOT JUST THE CELLS THIS PROBE TRAPS. A cell
    # that is ENTERED but holds a bare `C9` is an offered extension point that
    # nobody took -- not a crossing. Telling those apart needs the bytes, and §2
    # permits reading a cell for its slot and idiom, which is all this reads.
    for {set a 64922} {$a <= 65511} {incr a 5} {
        set b ""
        for {set i 0} {$i < 5} {incr i} {
            append b [format %02X [debug read memory [expr {$a + $i}]]]
        }
        puts $f "CELL $a $b"
    }
    close $f
    after time 1 __meta
}
foreach a {@CELLS@} {
    debug set_bp $a {} "__cap IN$a"
    debug set_bp [expr {$a + 4}] {} "__cap OUT$a"
    debug set_bp [expr {$a + 1}] {} "__k5 $a"
}
debug set_bp @TIMI@ {} { __timi }
after time 1 __meta
'''


def prologue(out_path, sum_path):
    t = TCL
    for k, v in (("@OUT@", out_path), ("@SUM@", sum_path), ("@CAP@", str(CAP)),
                 ("@REGS@", " ".join(REGS)),
                 ("@DUMPREGS@", " ".join(DUMPREGS)),
                 ("@CELLS@", " ".join(str(a) for a in CELLS)),
                 ("@TIMI@", str(C_TIMI))):
        t = t.replace(k, v)
    return (t,)


def run(tag, lines, dsk):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="crossabi-%s-" % tag, suffix=".txt")
    os.close(fd)
    fd, summ = tempfile.mkstemp(prefix="crossabi-%s-sum-" % tag, suffix=".txt")
    os.close(fd)
    caps = omsx_repl.run_cases(REF, [("direct", lines)], batch=False,
                               reset=RESET, boot=BOOT, step=STEP,
                               cap_gap=CAP_GAP, diska=dsk, capture="screen",
                               prologue=prologue(out, summ))
    events, meta, cells = [], {}, {}
    try:
        for ln in open(out):
            p = ln.split()
            if p and p[0] == "K5FIRED":
                events.append(dict(tag="K5FIRED"))
                continue
            e = parse_event(p)
            if e is not None:
                events.append(e)
    except OSError:
        pass
    try:
        for ln in open(summ):
            p = ln.split()
            if p and p[0] == "BAD":
                meta = dict(bad=int(p[1]), events=int(p[3]))
            elif len(p) >= 3 and p[0] == "CELL":
                cells[int(p[1])] = p[2]
    except OSError:
        pass
    for f in (out, summ):
        if os.path.exists(f):
            os.unlink(f)
    return events, meta, cells, (caps or [None])[0]


def parse_event(p):
    """One log line's fields -> an event dict. Extracted so it can be TESTED.

    🔴 BOTH OF THIS PROBE'S PARSING BUGS LIVED HERE AND BOTH WERE SILENT.
    (1) A 32-byte memory dump that happens to contain only DIGITS passes
    `isdigit()`; stored as an int it then printed as no contents at all --
    identical to a non-RAM value. One case's filename pointer vanished that way
    while the next case's identical register printed fine.
    (2) The dump prefix was `D`, and `DE` is a register. `DE=12345` was stored
    as a string and printed `?` in every single row, while its five siblings --
    none of which begin with D -- were correct. A prefix that can collide with a
    member of the set it tags is not a prefix.
    ⚠️ AND THE FIRST SELFTEST ARM WRITTEN FOR (2) WAS VACUOUS: it built the dict
    by hand, so it never ran this code. An arm must call the function that held
    the bug.
    """
    if len(p) < 6:
        return None
    e = dict(n=p[0], tag=p[1], caller=int(p[2]), pri=int(p[3]), sec=_sub(p[4]))
    for x in p[5:]:
        if "=" not in x:
            continue
        k, v = x.split("=", 1)
        e[k] = v if k.startswith("M") else (int(v) if v.isdigit() else v)
    return e


def printable(hexs: str) -> str:
    if hexs in ("-", "", None):
        return ""
    out = []
    for i in range(0, len(hexs), 2):
        c = int(hexs[i:i + 2], 16)
        out.append(chr(c) if 32 <= c < 127 else ".")
    return "".join(out)


def describe(e, key):
    """A register's value as a REGION, plus what it points at if that is RAM.

    🔴 THE SLOT RECORDED IN AN EVENT IS THE CALLER'S PAGE, NOT THIS REGISTER'S.
    So `region()` is only used where it needs no slot -- pages 2 and 3 are RAM on
    this machine whatever the slot register says. A value in page 0 or 1 is
    reported as a PAGE and nothing more: naming it main-ROM or disk-ROM would be
    attributing a slot that was never sampled, which is the exact ambiguity
    D-LOADPROTO's classifier exists to refuse.
    """
    v = e.get(key)
    if not isinstance(v, int):
        return "?"
    if (v >> 14) < 2:
        return "page%d(slot not sampled)" % (v >> 14)
    r = region(v, e["pri"], e["sec"])
    d = e.get("M" + key)
    if isinstance(d, str) and d != "-":
        return "%s [%s]" % (r, printable(d))
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        return selftest()

    import loadrun_probe as LR
    tmpd = tempfile.mkdtemp(prefix="crossabi-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ref")
    # 🔑 A.BAS and QQQQQQQQ.BAS hold the SAME BYTES under two names. That pair is
    # what separates "this register follows the file NAME" from "this register
    # follows the file's SIZE or content" -- S vs L cannot, because both differ.
    dsk, sizes, _per = LR.build(seeded, tmpd, "ref",
                                extra={"A       BAS": ASCII_BAS,
                                       "QQQQQQQQBAS": ASCII_BAS,
                                       "B       BIN": BSAVE_BIN})
    print("images: S=%d B  L=%d B  A=Q=%d B" % (sizes["S"], sizes["L"],
                                                len(ASCII_BAS)))

    cases = [
        ("quiet",  ["REM"]),
        ("loadS",  ['LOAD"S.BAS"']),
        ("loadL",  ['LOAD"L.BAS"']),
        ("loadA",  ['LOAD"A.BAS"']),
        ("loadQ",  ['LOAD"QQQQQQQQ.BAS"']),
        ("mergeA", ['MERGE"A.BAS"']),
        ("saveT",  ['SAVE"T.BAS"']),
        # 🔬 THE PREDICTION TEST. Stated BEFORE this run: if DE carries the
        # operation's MODE rather than its verb, then every READ must show the
        # value LOAD and MERGE share and every WRITE the value SAVE shows.
        # `BLOAD` and `OPEN...FOR INPUT` are reads; `OPEN...FOR OUTPUT` is a
        # write. Three new points against a hypothesis fitted to three old ones.
        ("bloadB",  ['BLOAD"B.BIN"']),
        ("openIn",  ['OPEN"A.BAS"FOR INPUT AS#1', "CLOSE"]),
        ("openOut", ['OPEN"Z.DAT"FOR OUTPUT AS#1', "CLOSE"]),
    ]
    res = {}
    for tag, lines in cases:
        ev, meta, cells, cap = run(tag, lines, dsk)
        res[tag] = (ev, meta, cells)
        ins = [e for e in ev if str(e.get("tag", "")).startswith("IN")]
        outs = [e for e in ev if str(e.get("tag", "")).startswith("OUT")]
        print("\n=== %s === events=%s bad=%s  IN=%d OUT=%d"
              % (tag, meta.get("events"), meta.get("bad"), len(ins), len(outs)))
        for e in ins + outs:
            print("  %-10s caller=%-8s %s" % (
                e["tag"], region(e["caller"], e["pri"], e["sec"]),
                "  ".join("%s=%s" % (r, describe(e, r)) for r in REGS)))
        if cap:
            tail = [x for x in str(cap).splitlines() if x.strip()]
            print("  screen: %s" % (tail[-1][:70] if tail else "?"))

    print("\n=== CONTROLS ===")
    ok = True
    if any(e for e in res["quiet"][0] if str(e.get("tag")).startswith(("IN", "OUT"))):
        print("K3 NEGATIVE  RED: the quiet case captured a verb crossing")
        ok = False
    else:
        print("K3 NEGATIVE  green: quiet captured no verb crossing")

    timi = [e for e in res["loadS"][0] if e.get("tag") == "TIMI"]
    treg = {region(e["caller"], e["pri"], e["sec"]) for e in timi}
    if timi and treg == {"MAIN-P0"}:
        print("K1 DISCRIM   green: H.TIMI's caller is MAIN-P0 in all %d samples"
              % len(timi))
    else:
        print("K1 DISCRIM   RED: H.TIMI classified as %s" % (treg or "nothing"))
        ok = False

    bad = sum(res[t][1].get("bad", 0) for t, _ in cases)
    if bad == 0:
        print("K5 TIMING    green: the slot byte (CELL+1) never fired in any "
              "case -- breakpoints precede the instruction, so every register "
              "above was sampled before the crossing ran")
    else:
        print("K5 TIMING    RED: the slot byte fired %d time(s) -- the capture "
              "moment is not what this probe assumes" % bad)
        ok = False

    # 🔑 K6 IS A PRECONDITION, AND WHEN IT FAILS THE FAILURE IS THE RESULT.
    # A cell holding `F7 <slot> <lo> <hi> C9` is CLAIMED and calling it crosses
    # slots. A cell holding a bare `C9` is an offered extension point nobody
    # took: main calls it, it returns, and NOTHING crosses. Both are "entered"
    # under a breakpoint counter, which is why D-HOOKCOUNT could not tell them
    # apart -- and why an entry count alone can never locate a crossing.
    claimed = {}
    for t, _ in cases:
        for a, b in res[t][2].items():
            claimed.setdefault(a, set()).add(b)
    nclaim = sum(1 for a, vs in claimed.items()
                 if all(v.startswith("F7") for v in vs))
    print("K6 CENSUS    %d of %d published hook slots are CLAIMED (`F7 ...`)"
          % (nclaim, len(claimed)))
    NAMED = ((0xFD9F, "H.TIMI"), (0xFFA7, "HPHYD"), (0xFDEF, "HDSKO"),
             (0xFE5D, "H.NULO"), (0xFE67, "the LOAD/MERGE cell"),
             (0xFE6C, "H.SAVE"), (0xFE76, "H.BINL"),
             (0xFFCF, "sector service A"), (0xFFD4, "sector service B"))
    for a, nm in NAMED:
        vs = claimed.get(a, set())
        v = sorted(vs)[0] if vs else "??"
        st = ("CLAIMED" if v.startswith("F7")
              else "unclaimed (bare RET)" if v.startswith("C9") else "other")
        print("    $%04X %-20s %s" % (a, nm, st))
    for a in CLAIMED_EXPECTED:
        vs = claimed.get(a, set())
        if not (vs and all(v.startswith("F7") and v.endswith("C9") for v in vs)):
            print("K6 PRECOND   RED: $%04X was expected CLAIMED and is not -- "
                  "there is no crossing at it to capture" % a)
            ok = False
    # 🔴 AND THE CLAIM STATE MUST BE STATIC. If a cell's five bytes differ
    # between cases, the table is being rewritten while verbs run and a single
    # census reading would be a snapshot of an unknown moment.
    drift = {a: vs for a, vs in claimed.items() if len(vs) > 1}
    if drift:
        print("K6 STATIC    RED: %d cell(s) changed their bytes between cases"
              % len(drift))
        ok = False
    else:
        print("K6 STATIC    green: every cell's five bytes are identical across "
              "all %d cases" % len(cases))

    # 🔑 K7 IS NOW PER CELL, AND AN UNCLAIMED CELL IS EXPECTED TO SHOW
    # 1 ENTRY / 0 EXITS: its `C9` at offset 0 returns before offset 4 is ever
    # reached. That asymmetry is a second, independent witness that the cell is
    # not a crossing -- it agrees with the bytes without being derived from them.
    # 🔑 K7 REPORTS THE PATTERN AND CONTROLS ITS CONSISTENCY -- it does not
    # assume 1:1. An UNCLAIMED cell must show entries and no exits (its `C9` at
    # offset 0 returns before offset 4 is reached), which is a second witness
    # for the census that is not derived from the bytes. A CLAIMED cell that
    # pairs is a call-and-return crossing; a claimed cell entered with NO exit
    # is a ONE-WAY transfer, which is a finding, not a fault. What would be a
    # fault is the same cell behaving differently between cases.
    pat: dict = {}
    for t, _ in cases:
        for a in CELLS:
            ins = len([e for e in res[t][0] if e.get("tag") == "IN%d" % a])
            outs = len([e for e in res[t][0] if e.get("tag") == "OUT%d" % a])
            if ins:
                pat.setdefault(a, {}).setdefault((ins, outs), []).append(t)
    for a in CELLS:
        if a not in pat:
            print("K7 SHAPE     $%04X never entered" % a)
            continue
        shapes = pat[a]
        desc = "; ".join("%d in/%d out in %s" % (k[0], k[1], ",".join(v))
                         for k, v in sorted(shapes.items()))
        kind = ("pairs (call and return)" if all(k[0] == k[1] for k in shapes)
                else "ONE-WAY (entered, never returns through the cell)"
                if all(k[1] == 0 for k in shapes) else "MIXED")
        print("K7 SHAPE     $%04X %-46s %s" % (a, desc, kind))
        if kind == "MIXED":
            print("K7 SHAPE     RED: $%04X behaves differently between cases"
                  % a)
            ok = False
    for a in CELLS:
        if a in CLAIMED_EXPECTED or a not in pat:
            continue
        if any(k[1] for k in pat[a]):
            print("K7 SHAPE     RED: unclaimed $%04X produced an EXIT, which a "
                  "bare `C9` at offset 0 cannot do" % a)
            ok = False

    print("\n=== WHAT THE REGISTERS CARRY ===")
    if not ok:
        print("WITHHELD: a control is red.")
        return 1
    # invariant vs varies-with-name vs varies-with-size
    def inreg(tag):
        for e in res[tag][0]:
            if str(e.get("tag", "")) == "IN%d" % C_NULO:
                return e
        return None
    # 🔴 ACROSS VERBS, NOT JUST ACROSS FILES. The four-load comparison below
    # answers "does a register carry the FILE"; it cannot answer "does a register
    # carry the VERB", because every one of its cases IS a LOAD. D-SELECTOR
    # needed that second question and it was never asked here.
    print("\n=== DOES A REGISTER CARRY THE VERB? (at the crossing $FE5D) ===")
    vcases = ("loadA", "mergeA", "saveT", "bloadB", "openIn", "openOut")
    vregs = {t: inreg(t) for t in vcases}
    if all(vregs.values()):
        for r in REGS:
            vals = {t: vregs[t].get(r) for t in vcases}
            if len(set(vals.values())) == 1:
                print("  %-3s identical across every verb" % r)
                continue
            # 🔴 PRINT A VALUE ONLY WHEN IT CANNOT BE A REFERENCE-INTERNAL
            # ADDRESS: a scalar below $0100, or a pointer into RAM. Anything in
            # page 0 or 1 is reported as differing and nothing more.
            shown = {}
            for t, v in vals.items():
                shown[t] = ("$%04X" % v if isinstance(v, int)
                            and (v < 0x100 or (v >> 14) >= 2) else "differs")
            print("  %-3s DIFFERS: %s" % (r, shown))
    else:
        print("  (a case is missing)")

    S, L, A, Q = (inreg(t) for t in ("loadS", "loadL", "loadA", "loadQ"))
    if all(x is not None for x in (S, L, A, Q)):
        for r in REGS:
            same_name = A.get(r) == Q.get(r)      # same bytes, different name
            same_size = S.get(r) == L.get(r)      # different name AND size
            allsame = len({S.get(r), L.get(r), A.get(r), Q.get(r)}) == 1
            if allsame:
                verdict = "INVARIANT across all four loads"
            elif not same_name:
                verdict = "VARIES with the file NAME (A vs Q differ, same bytes)"
            elif not same_size:
                verdict = "constant under a name change, VARIES S vs L"
            else:
                verdict = "varies, unattributed"
            print("  %-3s %s" % (r, verdict))
    return 0


def selftest() -> int:
    """The PARSING and RENDERING halves, with a negative control on each."""
    ok = True
    if printable("41424300") != "ABC.":
        print("SELFTEST RED: printable() mis-rendered a known string")
        ok = False
    if printable("-") != "":
        print("SELFTEST RED: a non-RAM dump must render empty, not as text")
        ok = False
    # 🔴 NEGATIVE: a register in page 0/1 must NOT be given a slot-based region.
    # Sampling the CALLER's slot and reporting it as the REGISTER's would invent
    # a DISK/MAIN verdict out of an address alone.
    e = dict(pri=3, sec=1, HL=0x6000, MHL="-")
    got = describe(e, "HL")
    if "DISK" in got or "MAIN" in got:
        print("SELFTEST RED: describe() attributed a slot it never sampled (%s)"
              % got)
        ok = False
    # positive: a RAM pointer is rendered with its contents
    e2 = dict(pri=0, sec=0, HL=0xF000, MHL="532E424153000000000000FF")
    if "S.BAS" not in describe(e2, "HL"):
        print("SELFTEST RED: a RAM pointer's contents were not rendered")
        ok = False
    # 🔴 THE ARM THAT WOULD HAVE CAUGHT THE PREFIX COLLISION. `DE` is the one
    # register whose NAME begins with the letter the dump prefix used, so it is
    # the only one a prefix test can fail on -- and it failed silently, printing
    # `?` in every row while its five siblings printed fine. A selftest that
    # only exercised HL could never see it.
    e3 = parse_event("7 IN1 40000 0 0 SP=1 AF=1 BC=2 DE=61696 HL=4 IX=5 "
                     "IY=6 MBC=- MDE=4F4B0000000000000000000000000000 "
                     "MHL=- MIX=- MIY=-".split())
    if not isinstance(e3.get("DE"), int):
        print("SELFTEST RED: the parser lost the register DE to the dump "
              "prefix -- it stored %r" % (e3.get("DE"),))
        ok = False
    if not isinstance(e3.get("MDE"), str):
        print("SELFTEST RED: a dump that is all digits was stored as a number")
        ok = False
    e4 = parse_event("8 IN1 40000 0 0 SP=1 HL=40000 "
                     "MHL=00000000000000000000000000000000".split())
    if not isinstance(e4.get("MHL"), str):
        print("SELFTEST RED: an ALL-DIGIT dump was coerced to a number -- the "
              "case that made one pointer print as nothing")
        ok = False
    g3 = describe(e3, "DE")
    if g3 == "?" or "OK" not in g3:
        print("SELFTEST RED: describe() lost the register DE (%s) -- a dump "
              "prefix that collides with a register name" % g3)
        ok = False
    # negative: openMSX's `X` subslot must fold to 0, not crash or become other
    if _sub("X") != 0 or _sub("1") != 1:
        print("SELFTEST RED: subslot token handling is wrong")
        ok = False
    print("SELFTEST GREEN" if ok else "SELFTEST RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
