#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ROMSIZE step 1, (b) BSAVE-to-disk: which hook cells does the reference's
`BSAVE` to a disk file ENTER, and what do the claimed ones RECEIVE?

WHY. Today zerobas's BSAVE-to-disk crosses NO hook: basic/save.asm do_bsave
parses, then `sv_tenant` runs the sub-ROM save tenant (sub/save.asm,
basic/sv-bsvdisk.inc). The move to disk.rom needs the reference's crossing
first. What is ALREADY measured (spec-diskcode-eviction.md §6.6ab / §6.6ad,
expansion-protocol.md §8.2): BSAVE enters $FE5D (H.NULO) with DE = $0002
(OUTPUT), BC = the START ADDRESS as typed, HL = the program-verb file buffer
($DC65 on the CF-3300), IX = the binary-image family. What is NOT measured:
the FULL set of cells BSAVE enters (the census tables cover LOAD / MERGE /
BLOAD / SAVE / OPEN, never BSAVE), whether any cell is entered per BYTE (as
$FE85 H.FILO is for SAVE"x",A, which shares DE = $0002), and the ORDER of the
statement's own errors against the crossing (save.asm: "the reference's order
for BSAVE is unmeasured").

TWO PHASES, two instruments, both precedented:
  (a) COUNT -- scratchpad/hookcount_probe.py's entry counter on every published
      hook slot $FD9A..$FFE7 (never reads a cell, never follows a target, never
      steps), one boot per case, every count a DELTA against `quiet`.
  (b) LOG   -- scratchpad/dget_probe.py's register logger, on the CLAIMED cells
      phase (a) found BSAVE moving (or --cells): registers, 8 stack words and
      published work-area cells. EVERY memory read is guarded: below $8000 ->
      `--` (ROM), AND the hook table $FD9A..$FFE7 and the five measured RAM-code
      clusters (§6.6ac/§6.6z: $F1D9-$F1E1, $F1F4, $F255-$F2A3, $F365-$F36B,
      $F38C-$F399) also print `--`: a hook's bytes name a target, and RAM code
      is relocated reference content. Nothing is stepped, no target followed.

CASES (CF-3300, fresh image per case holding one 16 B D.DAT; `@` markers are
CHR$-built so the typed line cannot be read as the result [[trapsvc-echo-fence]]):
  quiet    PRINT "@Q"                       the baseline
  files    FILES                            control: must move H_FILE $FE7B
  openout  OPEN FOR OUTPUT + CLOSE          the DE = $0002 sibling (control set)
  bs256    BSAVE"B.BIN",&HD000,&HD0FF       263 B file, 1 sector
  bs4k     BSAVE"K.BIN",&HD000,&HDFFF       4103 B, 9 sectors -- the scaling pair
  bsexec   ...,&HD010                       exec address (header word 3)
  bsvram   BSAVE"V.BIN",0,&HFF,S            the ,S (VRAM) flag
  bsjunk   ...,&HD0FF 5                     trailing junk: ERR 2 before/after?
  bssx     ...,SX                           `,S` + junk: ERR 2 before/after?
  bsnoend  BSAVE"N.BIN",&HD000              missing end: ERR 2 before the open?
  bsdrv    BSAVE"C:D.BIN",...               bad drive (62?) -- which side?
  bsnodisk the bs256 statement, drive EMPTY (Disk offline, 70?) -- which side?
The image is read back on the HOST after each case (size + 7-byte header), so a
case that silently failed cannot contribute a row shaped like data.

PREDICTION (written 2026-10-15, BEFORE any run; scored mechanically below where
it can be):
  P1  bs256 enters $FE5D exactly +1 (the measured crossing).
  P2  NO claimed cell scales per BYTE: bs4k - bs256 < 64 on every claimed cell
      (BLOAD, the read mirror, has no per-byte cell; $FE85 is SAVE,A's).
  P3  $FE71 (H.BINS) +0 for every BSAVE case -- it is tokenised SAVE's cell, as
      $FE76 turned out to be tokenised LOAD's and not BLOAD's.
  P4  the per-sector pair $FFCF/$FFD4 rises by 8 (+/-2) from bs256 to bs4k.
  P5  BSAVE's claimed set (minus H.TIMI) is a subset of
      {$FE5D, $FE4E, $FE58, $FE62, $FEB2, $FEB7} -- BLOAD's set plus OPEN's
      $FE58 -- and equals openout's set.
  P6  bsexec and bsvram enter the same claimed cells, same counts, as bs256
      (exec and ,S are main's parse; nothing new crosses).
  P7  bsnoend: ERR 2, $FE5D NOT entered, no N.BIN on the image.
  P8  bsjunk: J.BIN IS written (263 B), THEN ERR 2 -- the statement loop finds
      the junk after the handler returns (zerobas's current order).
  P9  bssx: like bsjunk -- X.BIN written, then ERR 2. (Low confidence. It
      CONTRADICTS disk_probe_option_hygiene.py's docstring, "raised before the
      file is created", which is an ours-only probe and never measured this.)
  P10 bsdrv: ERR 62 (Bad drive name), $FE5D NOT entered, $FEB2 entered.
  P11 bsnodisk: ERR 70 (Disk offline), $FE5D entered +1 -- the disk side finds
      the empty drive.
  P12 (phase b) at $FE5D for bs256: DE = 0002, BC = D000 (re-confirms §6.6ab);
      for bsexec BC is still D000 (the exec does not ride BC); SAVEND $F87D
      reads D0FF at $FE5D (the end is parsed before the crossing).

Run (from the repo root, emulator free, NOT during a gate):
    python3 scratchpad/bsave_hook_probe.py > scratchpad/bsave_hook_run.out 2>&1
    python3 scratchpad/bsave_hook_probe.py --phase a bs256 bs4k   # subset
    python3 scratchpad/bsave_hook_probe.py --phase b --cells FE5D,FE62 bs256
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
import hookcount_probe as HC                                  # noqa: E402

REF = "National_CF-3300"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 25.0, 8.0

MK = "PRINT CHR$(64);"            # `@` built at run time: the echo fence
DUMMY = {"D       DAT": bytes(range(65, 81))}

# name8 is what the host reads back; None = no file is expected to be checked.
# want = (size, start, end, exec) or None.
CASES = {
    "quiet":    (['%s"Q"' % MK], None, None, True),
    "files":    (["FILES"], None, None, True),
    "openout":  (['OPEN"O.DAT"FOR OUTPUT AS#1:CLOSE:%s"K"' % MK],
                 None, None, True),
    "bs256":    (['BSAVE"B.BIN",&HD000,&HD0FF:%s"K"' % MK],
                 "B       BIN", (263, 0xD000, 0xD0FF, 0xD000), True),
    "bs4k":     (['BSAVE"K.BIN",&HD000,&HDFFF:%s"K"' % MK],
                 "K       BIN", (4103, 0xD000, 0xDFFF, 0xD000), True),
    "bsexec":   (['BSAVE"E.BIN",&HD000,&HD0FF,&HD010:%s"K"' % MK],
                 "E       BIN", (263, 0xD000, 0xD0FF, 0xD010), True),
    "bsvram":   (['BSAVE"V.BIN",&H0000,&H00FF,S:%s"K"' % MK],
                 "V       BIN", (263, 0x0000, 0x00FF, 0x0000), True),
    "bsjunk":   (['BSAVE"J.BIN",&HD000,&HD0FF 5:%s"K"' % MK],
                 "J       BIN", (263, 0xD000, 0xD0FF, 0xD000), True),
    "bssx":     (['BSAVE"X.BIN",&HD000,&HD0FF,SX:%s"K"' % MK],
                 "X       BIN", (263, 0xD000, 0xD0FF, 0xD000), True),
    "bsnoend":  (['BSAVE"N.BIN",&HD000:%s"K"' % MK],
                 "N       BIN", None, True),
    "bsdrv":    (['BSAVE"C:D.BIN",&HD000,&HD0FF:%s"K"' % MK],
                 None, None, True),
    "bsnodisk": (['BSAVE"Z.BIN",&HD000,&HD0FF:%s"K"' % MK],
                 None, None, False),      # False = NO image in drive A
}
BSAVE_TAGS = [t for t in CASES if t.startswith("bs")]

# The 35 cells the CF-3300's disk ROM claims, as MEASURED (docs/spec-basic-
# nodisk.md §5.2, scratchpad/hookdiff_probe.py). Taken from the record, NOT
# read from the cells here: reading a cell's bytes is reading its target.
CLAIMED = {
    0xFD9F, 0xFDEF, 0xFDF9, 0xFDFE, 0xFE08, 0xFE12, 0xFE17, 0xFE21, 0xFE26,
    0xFE2B, 0xFE30, 0xFE35, 0xFE3A, 0xFE3F, 0xFE44, 0xFE49, 0xFE4E, 0xFE58,
    0xFE5D, 0xFE62, 0xFE71, 0xFE76, 0xFE7B, 0xFE80, 0xFE85, 0xFE8A, 0xFE99,
    0xFE9E, 0xFEA3, 0xFEAD, 0xFEB2, 0xFEB7, 0xFEFD, 0xFFA7, 0xFFAC,
}
NAMES = {0xFD9F: "H.TIMI", 0xFE4E: "H.GETP", 0xFE58: "H.NOFO",
         0xFE5D: "H.NULO", 0xFE62: "H.NTFL", 0xFE6C: "H.SAVE",
         0xFE71: "H.BINS", 0xFE76: "H.BINL", 0xFE7B: "H.FILE",
         0xFE85: "H.FILO", 0xFE8A: "H.INDS", 0xFEB2: "H.PARD",
         0xFEB7: "H.NODE", 0xFEFD: "H.ERRP", 0xFFCF: "(sector)",
         0xFFD4: "(sector)"}
DEFAULT_DETAIL = (0xFE5D, 0xFE4E, 0xFE58, 0xFE62, 0xFE71, 0xFE85, 0xFEB2,
                  0xFEB7)
DETAIL_CAP_PER_CELL, DETAIL_CAP_TOTAL = 6, 60


def fresh_image(tmpd, tag):
    dsk = os.path.join(tmpd, f"{tag}.dsk")
    LR.write_files(dsk, DUMMY)
    return dsk


def readback(dsk, name8):
    """-> (present, size, header-tuple or None) from the HOST side."""
    if not dsk or not name8 or not os.path.exists(dsk):
        return None
    img = open(dsk, "rb").read()
    blob = LR.read_file(img, LR.geom(bytearray(img)), name8)
    if blob is None:
        return (False, None, None)
    hdr = None
    if len(blob) >= 7 and blob[0] == 0xFE:
        hdr = struct.unpack("<HHH", blob[1:7])
    return (True, len(blob), hdr)


def screen_rows(cap):
    if not cap:
        return "<NO CAPTURE>"
    rows = [cap[i:i + 40].strip() for i in range(0, len(cap), 40)]
    keep = [r for r in rows if r and r != "Ok" and "BSAVE" not in r
            and "PRINT" not in r and not r.startswith("color ")]
    return " | ".join(keep) or "<blank>"


def phase_a(tags, tmpd):
    got, scr, files = {}, {}, {}
    for tag in tags:
        lines, name8, _want, disk = CASES[tag]
        dsk = fresh_image(tmpd, tag) if disk else None
        got[tag] = HC.run(tag, lines, dsk)
        scr[tag] = screen_rows(HC.CAPTURE.get(tag))
        files[tag] = readback(dsk, name8)
        print(f"  {tag:9} {sum(got[tag].values()):7d} hit(s) over "
              f"{sum(1 for v in got[tag].values() if v):3d} cell(s)   "
              f"screen: [{scr[tag]}]   file: {files[tag]}", flush=True)
        if not got[tag]:
            sys.exit(f"REFUSING: case {tag} read an EMPTY count map -- no "
                     f"breakpoint fired, so its deltas would be the instrument")
    if "quiet" not in got:
        sys.exit("REFUSING: phase a needs the `quiet` baseline")
    base = got["quiet"]
    if "files" in got and got["files"].get(HC.H_FILE, 0) - base.get(HC.H_FILE, 0) < 1:
        sys.exit("REFUSING: FILES did not move H_FILE $FE7B -- the counter does "
                 "not discriminate")
    cols = [t for t in tags if t != "quiet"]
    print("\n=== DELTA vs quiet (cells any case moved; * = claimed) ===")
    print("cell          " + " ".join(f"{t[:8]:>8}" for t in cols))
    for cell in HC.CELLS:
        vals = [got[t].get(cell, 0) - base.get(cell, 0) for t in cols]
        if any(vals):
            star = "*" if cell in CLAIMED else " "
            nm = NAMES.get(cell, "")
            print(f"${cell:04X}{star}{nm:8} " + " ".join(f"{v:+8d}" for v in vals))

    def d(tag, cell):
        return got[tag].get(cell, 0) - base.get(cell, 0) if tag in got else None

    def claimed_set(tag):
        return {c for c in CLAIMED - {0xFD9F} if d(tag, c)}

    print("\n=== FILES ON THE IMAGE (host readback: present, size, start/end/exec) ===")
    for tag in tags:
        name8, want = CASES[tag][1], CASES[tag][2]
        if not name8:
            continue
        r = files[tag]
        ok = (r and r[0] and want and r[1] == want[0] and r[2] == want[1:])
        print(f"  {tag:9} {name8!r:16} got {r}  want {want}  "
              f"{'MATCH' if ok else ('ABSENT' if r and not r[0] else 'DIFFERS')}")

    print("\n=== PREDICTIONS (stated in the docstring before the run) ===")
    score = {}
    if "bs256" in got:
        score["P1 bs256 enters $FE5D exactly +1"] = d("bs256", 0xFE5D) == 1
        score["P3 $FE71 H.BINS +0 on every BSAVE case"] = all(
            d(t, 0xFE71) == 0 for t in BSAVE_TAGS if t in got)
        bset = claimed_set("bs256")
        print(f"  bs256 claimed set: {sorted(f'${c:04X}' for c in bset)}")
        score["P5a bs256's claimed set within {FE5D,FE4E,FE58,FE62,FEB2,FEB7}"] = \
            bset <= {0xFE5D, 0xFE4E, 0xFE58, 0xFE62, 0xFEB2, 0xFEB7}
        if "openout" in got:
            oset = claimed_set("openout")
            print(f"  openout claimed set: {sorted(f'${c:04X}' for c in oset)}")
            score["P5b bs256's claimed set == openout's"] = bset == oset
        for t in ("bsexec", "bsvram"):
            if t in got:
                score[f"P6 {t} == bs256 on every claimed cell"] = all(
                    d(t, c) == d("bs256", c) for c in CLAIMED - {0xFD9F})
    if "bs256" in got and "bs4k" in got:
        score["P2 no claimed cell scales per byte (bs4k-bs256 < 64)"] = all(
            abs(d("bs4k", c) - d("bs256", c)) < 64 for c in CLAIMED - {0xFD9F})
        for c in (0xFFCF, 0xFFD4):
            g = d("bs4k", c) - d("bs256", c)
            score[f"P4 ${c:04X} rises 8+/-2 bs256->bs4k (got {g:+d})"] = 6 <= g <= 10
        scaled = [c for c in HC.CELLS
                  if d("bs4k", c) - d("bs256", c) >= 4]
        print(f"  cells that scale bs256 -> bs4k: "
              f"{[f'${c:04X}' for c in scaled]}")
        if not scaled:
            print("  🔴 NOTHING SCALES -- P2's 'no per-byte cell' is then the "
                  "counter's blindness, not the machine's answer")
    if "bsnoend" in got:
        r = files["bsnoend"]
        score["P7 bsnoend: $FE5D not entered, no N.BIN"] = (
            d("bsnoend", 0xFE5D) == 0 and r is not None and not r[0])
    for t, nm in (("bsjunk", "P8"), ("bssx", "P9")):
        if t in got:
            r = files[t]
            score[f"{nm} {t}: file written (263 B) then an error"] = bool(
                r and r[0] and r[1] == 263 and "@K" not in scr[t])
    if "bsdrv" in got:
        score["P10 bsdrv: $FE5D not entered, $FEB2 entered"] = (
            d("bsdrv", 0xFE5D) == 0 and (d("bsdrv", 0xFEB2) or 0) > 0)
    if "bsnodisk" in got:
        score["P11 bsnodisk: $FE5D entered +1"] = d("bsnodisk", 0xFE5D) == 1
    for k, v in score.items():
        print(f"  {'HIT ' if v else 'MISS'}  {k}")
    print("  (P10/P11's ERROR NUMBERS, P8/P9's error word and P12 are read "
          "from the screen column / phase b by hand)")

    moved = set()
    for t in BSAVE_TAGS:
        if t in got:
            moved |= claimed_set(t)
    return sorted(moved)


def prologue_b(path, cells):
    """dget_probe.py's logger, widened: every read guarded (see the docstring)."""
    return (
        "set ::dn 0\nset ::seq 0\n"
        "proc __ok {a} {\n"
        "  if {$a < 0x8000 || $a > 0xFFFF} { return 0 }\n"
        "  if {$a >= 0xFD9A && $a <= 0xFFE7} { return 0 }\n"
        "  if {$a >= 0xF1D9 && $a <= 0xF1E1} { return 0 }\n"
        "  if {$a == 0xF1F4} { return 0 }\n"
        "  if {$a >= 0xF255 && $a <= 0xF2A3} { return 0 }\n"
        "  if {$a >= 0xF365 && $a <= 0xF36B} { return 0 }\n"
        "  if {$a >= 0xF38C && $a <= 0xF399} { return 0 }\n"
        "  return 1 }\n"
        "proc __rd {a} { if {![__ok $a]} { return -- }; "
        "return [format %02X [debug read memory $a]] }\n"
        "proc __rw {a} { if {![__ok $a] || ![__ok [expr {$a+1}]]} { return ---- }; "
        "return [format %04X [expr {[debug read memory $a] + "
        "256*[debug read memory [expr {$a+1}]]}]] }\n"
        "proc __rs {a n} { set o {}; for {set i 0} {$i < $n} {incr i} "
        "{ lappend o [__rd [expr {$a+$i}]] }; return [join $o {}] }\n"
        "proc __dg {cell} {\n"
        "  incr ::seq\n"
        "  if {![info exists ::per($cell)]} { set ::per($cell) 0 }\n"
        "  incr ::per($cell)\n"
        f"  if {{$::per($cell) > {DETAIL_CAP_PER_CELL} || $::dn >= {DETAIL_CAP_TOTAL}}} return\n"
        "  incr ::dn\n"
        "  set sp [reg SP]; set st {}\n"
        "  for {set i 0} {$i < 16} {incr i 2} { lappend st [__rw [expr {$sp+$i}]] }\n"
        "  set hl [reg HL]\n"
        "  set pf [__rw 0xF864]\n"
        "  set pfa [expr {$pf eq {----} ? 0 : \"0x$pf\"}]\n"
        "  set dw [expr {$pfa ? [__rw [expr {$pfa+1}]] : {----}}]\n"
        "  set dwa [expr {$dw eq {----} ? 0 : \"0x$dw\"}]\n"
        f"  set h [open {{{path}}} a]\n"
        "  puts $h \"seq=$::seq cell=[format %04X $cell] n=$::per($cell) "
        "AF=[format %04X [reg AF]] BC=[format %04X [reg BC]] "
        "DE=[format %04X [reg DE]] HL=[format %04X $hl] IX=[format %04X [reg IX]] "
        "IY=[format %04X [reg IY]] SP=[format %04X $sp] stack=$st\"\n"
        "  puts $h \"    PTRFIL=$pf VALTYP=[__rd 0xF663] DAC=[__rs 0xF7F6 8] "
        "SAVEND=[__rw 0xF87D] RUNBNF=[__rd 0xFCBE] SAVENT=[__rw 0xFCBF] "
        "NLONLY=[__rd 0xF87C]\"\n"
        "  puts $h \"    F864..F87F=[__rs 0xF864 28]  F568..F574=[__rs 0xF568 13]\"\n"
        "  puts $h \"    @HL=[__rs $hl 9]  @PTRFIL=[__rs $pfa 9]  "
        "dfcb@$dw=[__rs $dwa 37]\"\n"
        "  close $h\n"
        "}\n"
        + "".join(f"debug set_bp {c} {{}} {{__dg {c}}}\n" for c in cells)
    )


def phase_b(tags, cells, tmpd):
    print(f"\n=== PHASE B: register log at {[f'${c:04X}' for c in cells]} "
          f"(cap {DETAIL_CAP_PER_CELL}/cell, {DETAIL_CAP_TOTAL}/case) ===")
    for tag in tags:
        lines, name8, _want, disk = CASES[tag]
        dsk = fresh_image(tmpd, "b_" + tag) if disk else None
        fd, path = tempfile.mkstemp(prefix=f"bsavehook-{tag}-", suffix=".txt")
        os.close(fd)
        caps = omsx_repl.run_cases(REF, [("direct", lines)], batch=False,
                                   reset=RESET, boot=BOOT, step=STEP,
                                   cap_gap=CAP_GAP, diska=dsk,
                                   capture="screen",
                                   prologue=(prologue_b(path, cells),))
        cap = (caps or [None])[0]
        print(f"== {tag}: {lines[0]}   screen: [{screen_rows(cap)}]   "
              f"file: {readback(dsk, name8)}", flush=True)
        body = open(path).read().splitlines()
        if not body:
            print("  <NO ENTRY LOGGED at any watched cell -- an unnamed outcome; "
                  "for an error case this may BE the finding, for bs256 it is "
                  "the instrument>")
        for ln in body:
            print("  " + ln.rstrip(), flush=True)
        os.unlink(path)


def main() -> int:
    args = sys.argv[1:]
    phase, cells_arg = "both", None
    if "--phase" in args:
        i = args.index("--phase")
        phase = args[i + 1]
        del args[i:i + 2]
    if "--cells" in args:
        i = args.index("--cells")
        cells_arg = [int(x, 16) for x in args[i + 1].split(",")]
        del args[i:i + 2]
    tags = args or list(CASES)
    bad = [t for t in tags if t not in CASES]
    if bad:
        sys.exit(f"unknown case(s) {bad}; known: {list(CASES)}")
    tmpd = tempfile.mkdtemp(prefix="bsavehook-")
    moved = []
    if phase in ("a", "both"):
        a_tags = tags if "quiet" in tags else ["quiet"] + tags
        if "files" not in a_tags:
            a_tags.insert(1, "files")
        moved = phase_a(a_tags, tmpd)
    if phase in ("b", "both"):
        cells = cells_arg or ([c for c in moved if c != 0xFD9F] or
                              list(DEFAULT_DETAIL))
        if 0xFE5D not in cells:
            cells = [0xFE5D] + cells
        b_tags = [t for t in tags if t not in ("quiet", "files")]
        phase_b(b_tags, cells, tmpd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
