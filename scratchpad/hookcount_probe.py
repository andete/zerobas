#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-HOOKCOUNT: which hook cells does the reference's `LOAD` actually ENTER?

Step 9 of `disk/docs/spec-diskcode-eviction.md` is blocked on the CELL question
(§6.6p) and the POKE method cannot answer it. This does, by asking the opposite
kind of question.

🔴 WHY THE POKE SWEEP FAILED, AND IT IS NOT A BUG IN IT. `hookid_load.py`
un-claims a cell (`POKE <cell>,201`) and watches which verb changes its answer.
That is a NEGATIVE probe: it reports that something broke, not what the cell is
for. Worse, its witness is an ERROR MESSAGE, which travels through the very
subsystem being broken. `$FE5D` is `H.NULO` -- "an operation for file-buffer 0"
in C-BIOS's public hook table -- and `LOAD`, `OPEN` and `MERGE` ALL operate on
file buffer 0, so un-claiming it disturbs all three. Reading that as "they share
a verb entry" is what §6.6j did, and a cell every subject uses cannot separate
them.

🎯 THE POSITIVE MEASUREMENT. A claimed hook holds `F7 <slot> <lo> <hi> C9`. Put
an openMSX BREAKPOINT on the cell ADDRESS and count hits. Shared infrastructure
and a dedicated entry are indistinguishable under un-claiming and completely
different under counting: if `LOAD` has a cell of its own, that cell is entered
during `LOAD` and not during `OPEN`; `H.NULO` is entered by both.

🔴 AND THE WITNESS IS EXTERNAL, WHICH LIFTS THE CONSTRAINT THAT CRIPPLED THE OLD
PROBE. `hookid_load.py` had to use `LOAD"<missing>"` because `LOAD` REPLACES the
program that would print the answer -- so it could only ever see the OPEN phase,
never the data phase where step 9's loop lives (§6.6l). A breakpoint counter does
not live in the guest at all, so a SUCCESSFUL `LOAD` of a real file is readable.

🔴 CLEAN-ROOM. `disk/docs/expansion-protocol.md` §2 permits a hook cell's SLOT
and IDIOM; the target addresses are the reference's internal detail. This reads
NEITHER. It sets a breakpoint on an address in the PUBLISHED hook table
($FD9A..$FFE7 -- MSX2 TH, and C-BIOS's own `hooks.asm` documents each cell's
purpose), counts entries, and never peeks the cell, never follows `<lo> <hi>`,
never single-steps, never captures a register. Observing that `LOAD` enters
`H.NULO` CONFIRMS documented interface behaviour; it decodes nothing. The same
method and the same line are already attested in this tree for the M19 finding
(`disk/kernel.asm`: the callseq / capture / callwatch causal pin, "no stock
routine internals decoded").

WHAT THE ANSWER LOOKS LIKE, decided in advance so a result cannot be read into:
  * a cell entered ONCE per LOAD and NOT by OPEN/FILES -> LOAD's own entry;
  * a cell entered once per LOAD **and** once per OPEN -> shared, as H.NULO is;
  * a cell whose count SCALES with file size -> the reference's read loop is in
    its DISK ROM, which is what step 9 wants to mirror. Per SECTOR is the
    expected shape; per BYTE is already excluded by §6.2c's arithmetic (the
    reference cannot afford an inter-slot crossing per byte at the rate it
    achieves).
  * nothing scales -> the loop is in MAIN, and step 9's premise is wrong.

🔴 THREE CONTROLS, because the last probe died of a missing one:
  quiet      a case that runs NO verb. Every count below is a DELTA against it,
             so boot traffic and the 60 Hz timer hook cannot be mistaken for a
             verb's signature.
  ctrl_file  `FILES` must move `H_FILE $FE7B` -- a cell we have ALREADY named.
             THIS is what proves the counter discriminates at all.
  ctrl_cross that same `H_FILE` must NOT move during `LOAD`. Without it, a cell
             that moves for everything would look like a finding.
  ⚠️ AND A SCALING CONTROL: at least one cell must be SEEN to scale between the
  small and large programs, or "nothing scales" means only that the counter is
  blind and the null result is worthless.
"""
import os
import struct
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                              # noqa: E402
import loadrun_probe as LR                                    # noqa: E402

REF = "National_CF-3300"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 25.0, 8.0

# The PUBLISHED hook table: 5-byte slots from $FD9A to $FFE7. C-BIOS's own
# hook-area init $C9-fills exactly this span (cbios-repack/key-trap-hook.patch
# cites it), which is why every slot is a legitimate breakpoint target and why
# an UNCLAIMED one is a bare `ret` rather than garbage.
HOOK_LO, HOOK_HI, HOOK_STEP = 0xFD9A, 0xFFE7, 5
CELLS = list(range(HOOK_LO, HOOK_HI + 1, HOOK_STEP))

H_FILE = 0xFE7B          # named in disk/equates.inc -- the discriminator control
H_NULO = 0xFE5D          # §6.6p's cell, for the shared-vs-own comparison


def prologue(dump_path):
    """Raw Tcl: count entries to every hook slot, and keep a live dump on disk.

    🔴 THE DUMP IS PERIODIC, NOT FINAL, ON PURPOSE. This probe does not control
    when the timeline exits, and a dump scheduled after it would never run.
    Counts only ever grow, so the last snapshot on disk IS the total.
    """
    cells = " ".join(str(a) for a in CELLS)
    # 🔬 ROUND 2 ALSO RECORDS FIRST-ENTRY ORDER. A monotonic counter is bumped on
    # every hook entry and each cell remembers the value it FIRST saw. For a cell
    # whose quiet baseline is 0 -- never touched during boot -- that first entry
    # necessarily happens inside the verb, so the relative order of those numbers
    # IS the verb's call order. It distinguishes an ENTRY from something the
    # entry CALLS, which counts alone cannot.
    # ⚠️ Still only integers: no register is captured, no memory is read at the
    # breakpoint, nothing is stepped. The clean-room line is where it was.
    return (
        "proc __hcdump {} {\n"
        f"  set f [open {{{dump_path}}} w]\n"
        "  foreach a [lsort -integer [array names ::hc]] "
        "{ set q 0 ; if {[info exists ::hf($a)]} { set q [set ::hf($a)] } ; "
        "puts $f \"$a [set ::hc($a)] $q\" }\n"
        "  close $f\n"
        "  after time 1 __hcdump\n"
        "}\n"
        "set ::seq 0\n"
        f"foreach a {{{cells}}} {{ set ::hc($a) 0 ; "
        "debug set_bp $a {} \"incr ::hc($a) ; incr ::seq ; "
        "if {!\\[info exists ::hf($a)\\]} { set ::hf($a) \\$::seq }\" }\n"
        "after time 1 __hcdump\n",
    )


ORDER: dict = {}


CAPTURE: dict = {}


def run(tag, lines, dsk):
    """One case on its own machine. -> {cell: count}."""
    fd, path = tempfile.mkstemp(prefix=f"hookcount-{tag}-", suffix=".txt")
    os.close(fd)
    caps = omsx_repl.run_cases(REF, [("direct", lines)], batch=False,
                               reset=RESET, boot=BOOT, step=STEP,
                               cap_gap=CAP_GAP, diska=dsk, capture="screen",
                               prologue=prologue(path))
    CAPTURE[tag] = (caps or [None])[0]
    out, first = {}, {}
    try:
        for ln in open(path):
            p = ln.split()
            if len(p) >= 2:
                out[int(p[0])] = int(p[1])
            if len(p) >= 3:
                first[int(p[0])] = int(p[2])
    except OSError:
        pass
    ORDER[tag] = first
    os.unlink(path) if os.path.exists(path) else None
    return out


# 🔬 ROUND 3 FIXTURES. Round 2 showed `LOAD` enters `$FE67` (C-BIOS: H.MERG) and
# `$FE76` (H.BINL), and that the name mapping is trustworthy -- `SAVE` moves
# `$FE6C` (H.SAVE) and `FILES` moves `$FE7B` (H_FILE), two independent
# confirmations. So the decisive question is whether those cells are SHARED with
# the verbs they are named for. That needs a file each verb will actually eat.
#
# Both formats are PUBLIC and already ours: the ASCII program format is
# `basic/docs/spec-ascii-saveload.md`, and the BSAVE header is the documented
# `$FE` + start + end + exec (basic/bload.asm implements it from the same public
# description). Nothing here is derived from a reference ROM.
ASCII_BAS = b"10 REM Z\r\n20 REM Z\r\n"
BIN_START, BIN_LEN = 0xD000, 16
# 🔴 A DISTINCTIVE PAYLOAD, BECAUSE A ZERO ONE CANNOT BE VERIFIED. Round 3 used
# `bytes(BIN_LEN)` and then read `$FE76 = 0` for BLOAD -- a result that could
# equally mean "that cell is not BLOAD's" or "my fixture is malformed and the
# verb failed after opening the file". An all-zero payload makes the readback
# ambiguous too, since unwritten RAM reads zero. $A5 is distinguishable from
# both zero and $FF.
BIN_FILL = 0xA5
BSAVE_BIN = (b"\xFE" + struct.pack("<HHH", BIN_START,
                                    BIN_START + BIN_LEN - 1, BIN_START)
             + bytes([BIN_FILL]) * BIN_LEN)


def main() -> int:
    tmpd = tempfile.mkdtemp(prefix="hookcount-")
    seeded, _n = LR.seed(REF, RESET, tmpd, "ref")
    dsk, sizes, _per = LR.build(seeded, tmpd, "ref",
                                extra={"A       BAS": ASCII_BAS,
                                       "B       BIN": BSAVE_BIN})
    print(f"images: S={sizes['S']} B  M={sizes['M']} B  L={sizes['L']} B")

    cases = [
        ("quiet", ["REM"]),
        ("files", ["FILES"]),
        ("loadS", ['LOAD"S.BAS"']),
        ("loadM", ['LOAD"M.BAS"']),
        ("loadL", ['LOAD"L.BAS"']),
        ("openin", ['OPEN"S.BAS"FOR INPUT AS#1', "CLOSE"]),
        # 🔬 IS $FFCF THE GENERIC SECTOR SERVICE OR LOAD'S OWN? Load S, then SAVE
        # it. Everything above `loadS` in this case is `loadS`, so the DELTA
        # against it is the write's own traffic. If a write also pays per sector,
        # the cell is the sector-level service every disk operation reaches --
        # which is exactly what a per-sector step 9 would be calling.
        ("loadS_saveT", ['LOAD"S.BAS"', 'SAVE"T.BAS"']),
        # 🔴 THE DECISIVE PAIR. If `MERGE` enters `$FE67` and `BLOAD` enters
        # `$FE76`, those cells are SHARED entries -- one cell, several verbs --
        # which is exactly the shape Joost ruled for, at an address that works.
        # If neither does, `LOAD` owns them outright and the selector is
        # unnecessary.
        ("merge", ['MERGE"A.BAS"']),
        # 🔬 THE CASE NOW PROVES ITSELF. `BLOAD` then reads the payload back and
        # prints it behind a CHR$-built marker, so the typed line cannot be
        # mistaken for the result [[trapsvc-echo-fence]]. Until this reads $A5,
        # `$FE76 = 0` for BLOAD means nothing at all.
        ("bload", ['BLOAD"B.BIN"', "PRINT CHR$(64)+CHR$(66);PEEK(&HD000)"]),
    ]
    got = {}
    for tag, lines in cases:
        got[tag] = run(tag, lines, dsk)
        print(f"  {tag:7} {sum(got[tag].values()):7d} total hit(s) over "
              f"{sum(1 for v in got[tag].values() if v):3d} cell(s)")

    # ---- THE PREDICTION, STATED BEFORE THE NUMBERS ARE READ ---------------
    # If $FFCF/$FFD4 are per-SECTOR, the mid image must land ON the line the
    # other two define: sectors = ceil(size/512), overhead = S_count - S_sectors.
    import math
    sec = {k: math.ceil(sizes[k] / 512) for k in ("S", "M", "L")}
    print(f"\nsectors: S={sec['S']}  M={sec['M']}  L={sec['L']}")

    if not got["quiet"]:
        sys.exit("REFUSING: the quiet baseline read NOTHING -- no breakpoint "
                 "ever fired, so every delta below would be against an empty "
                 "map and 'LOAD enters no cell' would be the instrument, not "
                 "the machine.")

    base = got["quiet"]
    print("\n=== DELTA vs the quiet baseline (cell: quiet -> case) ===")
    rows = []
    for cell in CELLS:
        vals = {t: got[t].get(cell, 0) for t, _ in cases}
        if all(v == vals["quiet"] for v in vals.values()):
            continue
        rows.append((cell, vals))
    for cell, vals in rows:
        d = "  ".join(f"{t}={vals[t] - base.get(cell, 0):+d}"
                      for t, _ in cases if t != "quiet")
        mark = ""
        if cell == H_FILE:
            mark = "   <- H_FILE (control)"
        elif cell == H_NULO:
            mark = "   <- H.NULO ($FE5D, §6.6p)"
        print(f"  ${cell:04X}  base={base.get(cell, 0):<6d} {d}{mark}")

    # ---- the prediction, scored --------------------------------------------
    print("\n=== PREDICTION: a per-sector cell must put the MID image ON the "
          "line the other two define ===")
    pred_ok = {}
    for c in (0xFFCF, 0xFFD4):
        b = base.get(c, 0)
        dS = got["loadS"].get(c, 0) - b
        dM = got["loadM"].get(c, 0) - b
        dL = got["loadL"].get(c, 0) - b
        over = dS - sec["S"]
        want = sec["M"] + over
        pred_ok[f"${c:04X} M lands on the line (want {want}, got {dM})"] = \
            dM == want
        print(f"  ${c:04X}  S={dS} (={sec['S']}+{over})  "
              f"M={dM} (predicted {want})  L={dL} (={sec['L']}+{over})")
    for k, v in pred_ok.items():
        print(f"  {'PASS' if v else '🔴 REFUTED'}  {k}")

    print("\n=== IS IT THE GENERIC SECTOR SERVICE? (SAVE's own delta) ===")
    for c in (0xFFCF, 0xFFD4):
        d = got["loadS_saveT"].get(c, 0) - got["loadS"].get(c, 0)
        print(f"  ${c:04X}  SAVE adds {d:+d} on top of the same load")

    # ---- did BLOAD actually succeed? ---------------------------------------
    cap = CAPTURE.get("bload") or ""
    got_fill = None
    for j in range(0, len(cap), 40):
        row = cap[j:j + 40]
        if "@B" in row:
            tok = row.split("@B", 1)[1].strip().split()
            if tok:
                try:
                    got_fill = int(tok[0])
                except ValueError:
                    pass
    print(f"\n=== DID BLOAD SUCCEED? payload byte read back = {got_fill} "
          f"(want {BIN_FILL}) ===")
    bload_ok = got_fill == BIN_FILL
    print(f"  {'PASS' if bload_ok else '🔴 FAIL'}  BLOAD loaded its payload -- "
          f"without this its $FE76 = 0 is UNINTERPRETABLE (a malformed fixture "
          f"and a cell that is not BLOAD's look identical)")

    print("\n=== ROUND 3: IS $FE67 / $FE76 SHARED, OR LOAD'S OUTRIGHT? ===")
    for c, name in ((0xFE67, "H.MERG"), (0xFE76, "H.BINL"),
                    (0xFE6C, "H.SAVE"), (0xFE5D, "H.NULO")):
        b = base.get(c, 0)
        row = "  ".join(f"{t}={got[t].get(c, 0) - b:+d}"
                        for t in ("loadS", "merge", "bload",
                                  "loadS_saveT", "openin"))
        print(f"  ${c:04X} {name:8} {row}")

    print("\n=== FIRST-ENTRY ORDER during LOAD (zero-baseline cells only, so "
          "the first entry is necessarily inside the verb) ===")
    fo = ORDER.get("loadS", {})
    seen = [(fo[c], c) for c in CELLS
            if base.get(c, 0) == 0 and fo.get(c) and
            got["loadS"].get(c, 0) > 0]
    for rank, (q, c) in enumerate(sorted(seen), 1):
        tag = " <- H.NULO" if c == H_NULO else ""
        op = "shared with OPEN" if got["openin"].get(c, 0) > 0 else "LOAD-ONLY"
        print(f"  {rank:2d}. ${c:04X}  (seq {q})  {op}{tag}")

    # ---- the controls -----------------------------------------------------
    print("\n=== CONTROLS ===")
    ok = {}
    ok.update(pred_ok)
    ok["bload fixture is VALID (its payload read back), so its zero counts"] = \
        bload_ok
    fb, lb = base.get(H_FILE, 0), base.get(H_FILE, 0)
    ok["ctrl_file: FILES moves H_FILE"] = got["files"].get(H_FILE, 0) > fb
    ok["ctrl_cross: LOAD does NOT move H_FILE"] = \
        got["loadS"].get(H_FILE, 0) == lb
    scaled = [c for c in CELLS
              if got["loadL"].get(c, 0) - got["loadS"].get(c, 0) >= 4]
    ok["scaling: at least one cell is SEEN to scale S -> L (without this a "
       "null result means the counter is blind, not that nothing scales)"] = \
        bool(scaled)
    for k, v in ok.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    if scaled:
        print("  cells that scale with program size:")
        for c in scaled:
            print(f"    ${c:04X}  S={got['loadS'].get(c, 0) - base.get(c, 0):+d}"
                  f"  L={got['loadL'].get(c, 0) - base.get(c, 0):+d}")
    return 0 if all(ok.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
