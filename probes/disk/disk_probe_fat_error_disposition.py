#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""FAT-primitive ERROR-disposition gate — the path `diskbasic-acceptance` misses.

WHY THIS EXISTS.  The repack build reaches every FAT12 primitive through resident
shims that bounce into the sub-ROM tenant (`fatprim_bounce`, basic/fat.asm) and
marshal the primitive's disposition back over the DISKOP result block: Cy=1 on a
tenant error, Cy=0 on success.  On 2026-07-27 the thirteen duplicated shim bodies
were collapsed into that one shared body, and the collapse was checked by
DELIBERATELY NEUTERING the error tail (`scf` -> `or a`) and re-running the gates:

    make diskbasic-acceptance-repack   ->  34/34 CONVERGED, with the error
                                           disposition provably broken.

All 34 oracle-differential verbs exercise the SUCCESS path only.  A gate that
stays green while the code under test is broken is measuring nothing
(the standing lesson), so this probe measures the other half.

WHAT IT MEASURES.  Eight verb/mode combinations driven at a filename that does not
exist, each of which must reach `fat_find` (or `fat_io_open`) and take the
STATUS != 0 return.
zerobas answers with its OWN lowercase `load error` (a DOCUMENTED divergence from
the reference's "File not found" -- see basic/PROVENANCE.md / load_error), so this
is deliberately a SELF-CHECK against zerobas's pinned wording, not an oracle
differential: an oracle comparison here would fail on the divergence, not on the
disposition.

⚠️ SIX OF THE EIGHT.  `kill-missing` (D-DSKMSG, docs/spec-basic-dskmsg.md §4.3)
and `name-missing` (D-DKNAME, docs/spec-basic-dkname.md §3.3) are pinned to
`File not found` since 2026-08-07, because those two verbs' no-match disposition
was MEASURED on the CF-3300 (R-DK1/R-DK2) and made reference-exact; the other six
remain the quarantined divergence.  The want is therefore PER CASE, and a row
that carries its own is printed with `[reference-exact: ...]` so the report never
reads as if the whole battery had been re-pinned.

⚠️ AND THE TWO STILL DID NOT MOVE TOGETHER.  Both readings were taken in one
session; `kill-missing` moved a slice earlier because `do_kill`'s no-match arm
was reachable on its own once the tenant separated the mount, while `do_name`'s
shared `nm_fail` had to be SPLIT first.  A pin that drifts verb by verb on its
neighbours' evidence stops being a pin -- so each one waited for its own code.

FALSIFICATION RECORD (this is the evidence the gate measures its subject).  With
the error tail neutered, four of the cases below SILENTLY REPORT NOTHING --
load-missing, run-missing, open-missing, merge-missing.  Restoring the tail
restores `load error` on all of them.  (`append-missing` was added 2026-07-31 by
D-APPMISS and postdates that experiment; it shares open-missing's disposition.)
If you change fatprim_bounce, re-run that experiment rather than trusting a green
here.

🔴 AND THAT FALSIFICATION RECORD WAS NOT ENOUGH (D-DSKJUDGE 2026-08-05,
docs/spec-rom-gate-diskrom.md §2.2).  It proves the rows go red when the error
TAIL breaks.  It says nothing about the rows going red when the disk SUBSYSTEM
breaks -- and they do not: on an all-$00 build/disk.rom this probe scored
`ALL PASS 8/8` at exit 0, as it did on five further corrupted images.  A battery
whose expected answer is an error passes a dead subject.  Closed with the
PRECONDITION row below (CONTROL), which asserts the FAT layer can reach a SUCCESS
disposition before any of the eight failures is believed.

🔴 AND THE PRECONDITION WAS NOT ENOUGH EITHER -- IT IS BATTERY-SCOPED, AND TWO
ROWS HERE PIN ONE VERB'S MESSAGE (D-FEVERB 2026-08-07,
docs/spec-fat-error-verb-control.md).  `fat-alive` proves the FAT LAYER is alive.
It never runs NAME, whose failure path and success path share almost nothing --
so D-DKNAME's knife K-NAMECTL (NAME reports success and renames NOTHING) scored
this whole battery `8/8 ALL PASS` at exit 0, precondition green.  A verb-scoped
claim needs a verb-scoped control, so a case may now name one (VERB_CONTROLS): if
it fails, THAT case prints NOT MEASURED and the run exits 2, while the others are
still scored.

⚠️ 1 OF 8 ROWS HAS ONE, AND THE GATE PRINTS THAT COUNT ON EVERY RUN.  The other
seven -- `kill-missing`, the second reference-exact row, among them -- are still
satisfied by a verb that always errors.  Closing one hole and saying ALL PASS
louder is how a gate stops describing itself; the denominator is the deliverable
next to the fix ([[a-hand-listed-denominator-is-a-scope-claim]]).

  python3 probes/disk/disk_probe_fat_error_disposition.py [--machine NAME]

Exit codes: 0 = every scored row converged; 1 = a real error-disposition
regression; 2 = an instrument failure and nothing below it was measured -- the
PRECONDITION failed (no row measured), or a VERB CONTROL failed (its row not
measured).  2 dominates 1: a run that is part measurement and part noise must say
so before anything in it is read.
"""
from __future__ import annotations
import argparse, os, shutil, struct, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "lib"))
import omsx_repl  # noqa: E402

# Each verb must route a "not found" through the FAT primitive shim layer and
# surface zerobas's load_error.  Kept to DIRECT-mode one-liners so the failure
# lands on the line right below the echoed command.
CASES = [
    ("load-missing",  'LOAD"A:NOSUCH.BAS"'),
    ("run-missing",   'RUN"A:NOSUCH.BAS"'),
    # 🔴 THE ONE ROW THAT IS NOT PINNED TO `load error`, SINCE 2026-08-07
    # (D-DSKMSG, docs/spec-basic-dskmsg.md §4.3). This row pinned KILL's no-match
    # to zerobas's own `load error` ON PURPOSE while the message was UNMEASURED
    # for KILL -- basic/files.asm said `File not found` in a comment and
    # load_error in the code, and moving it on the strength of D-LFILES's reading
    # for a DIFFERENT verb is the thing this project does not do. The reading was
    # then taken for KILL itself (R-DK1,
    # docs/dskmsg-msx1-characterization.md): the CF-3300 answers `File not
    # found`, so the pin moved in the same commit as the code.
    #
    # ⚠️ THE OTHER SEVEN ARE UNTOUCHED AND STAY `load error`. They are the
    # quarantined wording divergence basic/PROVENANCE.md records for the whole
    # no-disk / mount / I-O class, and NOTHING in D-DSKMSG measured them. A pin
    # that drifts verb by verb on its neighbours' evidence stops being a pin.
    ("kill-missing",  'KILL"A:NOSUCH.BAS"', "File not found"),
    ("bload-missing", 'BLOAD"A:NOSUCH.BIN"'),
    ("open-missing",  'OPEN"A:NOSUCH.DAT" FOR INPUT AS #1'),
    # D-APPMISS (docs/spec-basic-append-missing-refuse.md §5c). APPEND used to
    # CREATE the missing file -- `fat_io_append` jumped into `fat_io_create` on a
    # `fat_find` miss -- where the CF-3300 raises `File not found`, opens no
    # channel and writes no directory entry. This is the row that says the refusal
    # lands on the SAME class as its INPUT sibling directly above: the LOF battery
    # reads the LAST error on screen and so reads `File not open` from the trailing
    # statement whatever OPEN raised, and `err_class` there deliberately does not
    # know zerobas's `load error` wording. `append-missing` red with `open-missing`
    # green means the APPEND path reached a different class.
    ("append-missing", 'OPEN"A:NOSUCH.DAT" FOR APPEND AS #1'),
    # 🔴 THE SECOND ROW OFF `load error`, SINCE 2026-08-07 (D-DKNAME,
    # docs/spec-basic-dkname.md). Same reading as `kill-missing` and taken in the
    # same CF-3300 session (R-DK2) -- but it moved one slice LATER, because
    # `nm_fail` (basic/files.asm, do_name) was a SHARED exit for the fat_mount
    # failure and the fat_find miss. Re-pointing it would have moved a
    # disk-offline NAME to a trappable ERR 53 on no reading at all, so the arm
    # was SPLIT first (nm_notfound) and only the measured half moved.
    #
    # ⚠️ WHAT DID NOT MOVE: a NAME at an unmounted or unreadable volume still
    # answers `load error`, and no row here or anywhere drives it.
    ("name-missing",  'NAME"A:NOSUCH.BAS" AS "B.BAS"', "File not found",
     "name-alive"),
    ("merge-missing", 'MERGE"A:NOSUCH.BAS"'),
]
WANT = "load error"

# A row is `(key, line)` -- pinned to WANT, no verb control -- or
# `(key, line, want)` when its disposition has been MEASURED on the reference and
# is reference-exact -- or `(key, line, want, verb_control)` when a control in
# THIS run must show the verb reaching a SUCCESS disposition before the row is
# scored at all (D-FEVERB, docs/spec-fat-error-verb-control.md §2.1).
# Normalised here so the defaults stay visible in the table above rather than
# being repeated eight times.
CASES = [(c[0], c[1],
          c[2] if len(c) > 2 else WANT,
          c[3] if len(c) > 3 else None) for c in CASES]

# --- THE PRECONDITION (D-DSKJUDGE, docs/spec-rom-gate-diskrom.md §3.2) --------
# 🔴 EVERY ROW ABOVE PASSES ON A DEAD DISK ROM.  Measured: with `build/disk.rom`
# replaced by 16384 bytes of $00 -- no disk ROM at all -- this probe reported
# `ALL PASS  8/8 + directory check` at exit 0.  It does so on all six corrupted
# images D-DSKJUDGE tried (all-$00, all-$FF, truncated to 50 % and 99 %, and a
# byte flipped at each of the $4010 / $5006 canonical entries), while `probe`,
# `bdos-acceptance` and `diskbasic-acceptance` between them caught all six.
#
# The reason is structural, not a bug in any row: the battery's expected
# observable is an ERROR, and when the disk subsystem is dead EVERY file is
# missing, so all eight report `load error` for a reason that has nothing to do
# with the disposition under test.  The directory check passes too -- a machine
# that cannot write cannot create NOSUCH.DAT either.
#
# ⚠️ THE COMMENT IN main() BELOW ALREADY NAMED THIS CLASS AND CLOSED ONE INSTANCE
# OF IT.  D-APPMISS found the battery running with NO DISK MOUNTED, every case
# failing in `fat_mount` and never reaching `fat_find`, and fixed it by mounting a
# disk.  But mounting a disk only removes ONE reason `fat_mount` can fail; a dead
# disk ROM, an unhooked HPHYD and a pageenv regression are others, and the answer
# is `load error` for all of them.  Instances are endless; the PRECONDITION is one
# thing ([[precondition-is-the-instrument]]).
#
# So: prove the FAT layer can reach a SUCCESS disposition on this machine before
# believing eight failures.  `HI.TXT` is on disk/test720.dsk (26 B), and listing
# it needs `fat_mount` (a real boot-sector read through DSKIO), the root-directory
# walk, and a `fat_find` HIT -- the Cy=0 half of `fatprim_bounce` that all eight
# rows above are the Cy=1 half of.
#
# ⚠️ THE ASSERTION IS POSITIVE TEXT ON SCREEN, NOT "no `load error`".  The
# docstring above records that a broken error tail returns SILENTLY, so
# absence-of-error is precisely the reading a broken build also produces -- a row
# whose PASS condition can be met by silence is not a control.
CONTROL = ("fat-alive", 'FILES"A:HI.TXT"')
# Both tokens, not the rendered `HI      .TXT` string: the 8.3 column layout is
# FILES' business and is gated by disk_probe_files_wildcard.py, so pinning it here
# would red this gate on someone else's slice.  A `load error` tail -- or an empty
# one -- contains neither token, which is all this row has to separate.
CONTROL_WANT = ("HI", "TXT")

# --- THE PER-VERB CONTROLS (D-FEVERB, docs/spec-fat-error-verb-control.md) ----
# 🔴 THE PRECONDITION ABOVE IS BATTERY-SCOPED AND CANNOT COVER A ROW THAT PINS
# ONE VERB'S MESSAGE.  `fat-alive` proves the FAT LAYER reaches a success
# disposition -- the volume mounts, the walk runs, fat_find hits.  It says
# nothing about any particular verb, and NAME's failure path (fat_mount ->
# fat_find miss -> nm_notfound) shares almost nothing with NAME's success path
# (the DISKOP_SEL_NAME_STAMP tenant: read the sector, LDIR the 8.3 field, write
# it back).
#
# MEASURED, not argued (D-DKNAME's knife K-NAMECTL, docs/spec-basic-dkname.md
# §6.4): with `tnt_name_stamp` re-reading the directory sector instead of writing
# it back -- NAME reports success and renames NOTHING -- this whole battery
# scored `8/8 ALL PASS` at exit 0, `fat-alive` green, directory check green.
# `basic_probe_dskmsg.py` caught that build through its own per-verb control;
# this one did not have one.
#
# So a case may now name a control that must SUCCEED in this same run before the
# case is scored at all.  The control's blast radius is its VERB: if it fails,
# that one case prints NOT MEASURED and the run exits 2, while the other cases
# are still scored.  Making it a second PRECONDITION was rejected -- that would
# blank all eight rows on a NAME bug, over-claiming in the other direction.
#
# ⚠️ TWO INSTRUMENTS, and the second is the one a convincing screen cannot fool.
# The SCREEN half asserts positive text (a NAME that renamed nothing prints
# `File not found` here, which holds neither token).  The DIRECTORY half is
# parsed by the host from the machine's own image after openMSX exits, and is
# what says the sector was actually written back.
#
# ⚠️ PROG2.BAS, NOT HI.TXT.  The battery is BATCHED on one image, and `fat-alive`
# lists HI.TXT -- renaming it would break the precondition on the very run this
# control is evidence about.  PROG2.BAS is on disk/test720.dsk (TEST.BIN, HI.TXT,
# PROG.BIN, PROG.BAS, PROG2.BAS) and no row here reads it; `REN2` appears nowhere
# else in the tree, so the screen assertion cannot match by accident.
VERB_CONTROLS = {
    "name-alive": dict(
        lines=['NAME"A:PROG2.BAS" AS "REN2.BAS"', 'FILES"A:REN2.BAS"'],
        shown='NAME"A:PROG2.BAS" AS "REN2.BAS" : FILES',
        want=("REN2", "BAS"),                 # screen: positive text
        dir_present=b"REN2    BAS",           # directory: the rename LANDED
        dir_absent=b"PROG2   BAS",            # directory: and the old one went
        guards="name-missing",
    ),
}

# The file `append-missing` must NOT leave behind, and where to look for it.
SRC_DSK = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "disk", "test720.dsk")
MUST_NOT_EXIST = b"NOSUCH  DAT"


def dir_names(dsk_path: str):
    """The 11-byte names in the FAT12 root directory, or None if unreadable."""
    try:
        with open(dsk_path, "rb") as fh:
            d = fh.read()
    except OSError:
        return None
    if len(d) < 512 or struct.unpack("<H", d[11:13])[0] != 512:
        return None
    res = struct.unpack("<H", d[14:16])[0]
    nfat, nroot = d[16], struct.unpack("<H", d[17:19])[0]
    spf = struct.unpack("<H", d[22:24])[0]
    root = (res + nfat * spf) * 512
    out = []
    for i in range(nroot):
        e = d[root + i * 32: root + i * 32 + 32]
        if len(e) < 32 or e[0] == 0:
            break
        if e[0] != 0xE5 and not (e[11] & 0x18):
            out.append(bytes(e[:11]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="C-BIOS_MSX1_EU_REPACK_DISK")
    ap.add_argument("--diska", default=None,
                    help="disk image; default = a /tmp COPY of disk/test720.dsk")
    ap.add_argument("--boot-per-case", action="store_true",
                    help="isolation escape hatch when a batched case looks wrong")
    args = ap.parse_args()

    # ⚠️ A DISK MUST BE MOUNTED, and this probe ran WITHOUT ONE until 2026-07-31.
    # With an empty drive every case fails in `fat_mount` and never reaches
    # `fat_find` at all -- so the whole battery measured the MOUNT miss while the
    # docstring above claimed the FIND miss, and the two are indistinguishable by
    # their answer (`load error` either way). D-APPMISS caught it the only way it
    # could be caught: `append-missing` was added, the code under test was
    # DELETED (fat_io_append's refusal reverted to `jp c,fat_io_create`), and the
    # row stayed GREEN -- a gate green over a provably broken subject. With a disk
    # mounted the same knife build turns it RED (silent, no error at all) while
    # the other seven still pass.
    # ⚠️ AND IT MUST BE A /tmp COPY. `append-missing` on a build where APPEND
    # still creates actually WRITES `NOSUCH.DAT` into the mounted image (measured
    # -- the directory readout below is how that was seen). Mounting the
    # committed disk/test720.dsk would mutate it.
    dsk, tmp = args.diska, None
    if dsk is None:
        if not os.path.isfile(SRC_DSK):
            print(f"missing test image: {SRC_DSK}")
            return 2
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="faterr_",
                                          delete=False).name
        shutil.copy(SRC_DSK, tmp)
        dsk = tmp

    # The controls run FIRST, in the same batch: same machine, same mounted
    # image, same boot -- so a green control is evidence about the run the eight
    # rows below were measured in, not about a separate one.
    vkeys = list(VERB_CONTROLS)
    specs = ([("direct", [CONTROL[1]])]
             + [("direct", VERB_CONTROLS[k]["lines"]) for k in vkeys]
             + [("direct", [line]) for _, line, _, _ in CASES])
    raws = omsx_repl.run_cases(args.machine, specs,
                               batch=not args.boot_per_case,
                               reset=("NEW", "CLS"), capture="screen",
                               diska=dsk)
    ctl_raw = raws[0]
    vraws = dict(zip(vkeys, raws[1:1 + len(vkeys)]))
    raws = raws[1 + len(vkeys):]

    ok = True
    print("=" * 72)
    print("FAT-primitive ERROR disposition (Cy=1 out of fatprim_bounce)")
    print("=" * 72)

    ctl_tail = omsx_repl.screen_tail(ctl_raw, CONTROL[1])
    ctl_got = " | ".join(t.strip() for t in str(ctl_tail or "").split("\n") if t.strip())
    ctl_ok = all(w in (ctl_tail or "") for w in CONTROL_WANT)
    print(f"  {'PASS' if ctl_ok else 'FAIL'}  {CONTROL[0]:14} {CONTROL[1]:38} "
          f"-> {ctl_got[:60]!r}   [PRECONDITION]")
    if not ctl_ok:
        want = " + ".join(CONTROL_WANT)
        print(f"\n*** THE PRECONDITION FAILED: {CONTROL[1]} did not list "
              f"{want!r}.\n"
              f"    The FAT layer never reached a SUCCESS disposition on this "
              f"machine, so the\n"
              f"    eight error rows below are VACUOUS -- on a dead disk ROM "
              f"every file is\n"
              f"    missing and all eight report {WANT!r} for the wrong reason "
              f"(measured:\n"
              f"    an all-$00 build/disk.rom scored 8/8 here). Check "
              f"build/disk.rom, the\n"
              f"    mounted image, and `make repack-machine`, THEN re-read the "
              f"rows.\n"
              f"    Exit 2 (not 1) = the instrument was broken, NOT an "
              f"error-disposition regression.")
        for (key, line, _, _), raw in zip(CASES, raws):
            tail = omsx_repl.screen_tail(raw, line)
            got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
            print(f"  ....  {key:14} {line:38} -> {got[:60]!r}  (not scored)")
        print("\n===== FAT error disposition: NOT MEASURED (precondition failed) =====")
        if tmp:
            os.unlink(tmp)
        return 2

    # ONE read of the machine's own image, after openMSX exited. It is the
    # second instrument for BOTH the per-verb controls (did the rename reach the
    # sector?) and `append-missing` (was the file created anyway?).
    names = dir_names(dsk)

    # --- the per-verb controls (D-FEVERB §2.2), screen AND directory ----------
    vok = {}
    for k in vkeys:
        vc = VERB_CONTROLS[k]
        tail = omsx_repl.screen_tail(vraws[k], vc["lines"][-1])
        got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
        scr = all(w in (tail or "") for w in vc["want"])
        dpres = names is not None and vc["dir_present"] in names
        dabs = names is not None and vc["dir_absent"] not in names
        vok[k] = scr and dpres and dabs
        print(f"  {'PASS' if vok[k] else 'FAIL'}  {k:14} {vc['shown']:38} "
              f"-> {got[:60]!r}   [VERB CONTROL for {vc['guards']}]")
        if not vok[k]:
            print(f"        screen wanted {' + '.join(vc['want'])}: "
                  f"{'ok' if scr else 'MISSING'};  directory wanted "
                  f"{vc['dir_present'].decode()!r} present "
                  f"({'ok' if dpres else 'ABSENT'}) and "
                  f"{vc['dir_absent'].decode()!r} absent "
                  f"({'ok' if dabs else 'STILL THERE'})"
                  + ("  [the image was unreadable]" if names is None else ""))
            print(f"        => the verb never reached a SUCCESS disposition, so "
                  f"{vc['guards']!r} below is NOT a measurement: its error is "
                  f"what a\n        DEAD verb prints too. Exit 2, not 1.")

    instrument_fault = not all(vok.values())

    scored = 0
    for (key, line, want, vc_key), raw in zip(CASES, raws):
        tail = omsx_repl.screen_tail(raw, line)
        got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
        pin = "" if want == WANT else f"   [reference-exact: {want!r}]"
        if vc_key and not vok[vc_key]:
            print(f"  ....  {key:14} {line:38} -> {got[:60]!r}"
                  f"   NOT MEASURED (verb control {vc_key!r} failed)")
            continue
        good = want in (tail or "")
        ok &= good
        scored += 1
        guard = f"   [verb control: {vc_key}]" if vc_key else ""
        print(f"  {'PASS' if good else 'FAIL'}  {key:14} {line:38} "
              f"-> {got[:60]!r}{pin}{guard}")
        if not good:
            print(f"        want {want!r} -- a SILENT return here is the exact "
                  f"signature of a broken error tail")

    npass = sum(1 for (k, l, w, v), r in zip(CASES, raws)
                if (not v or vok[v]) and w in (omsx_repl.screen_tail(r, l) or ""))

    # THE SECOND INSTRUMENT, for `append-missing`: a refusal that still created
    # the file is not a refusal. The screen alone cannot say this -- a build that
    # printed `load error` and created the entry anyway would pass the text check
    # above -- so the machine's own image is parsed after it exits.
    if names is None:
        print(f"\n*** could not read the directory of {dsk} -- the "
              f"created-anyway check did not run")
        ok = False
    else:
        for k in vkeys:
            vc = VERB_CONTROLS[k]
            dpres, dabs = vc["dir_present"] in names, vc["dir_absent"] not in names
            print(f"\n  {'PASS' if dpres and dabs else 'FAIL'}  {k} (directory) "
                  f"-> {vc['dir_present'].decode()!r} "
                  f"{'present' if dpres else 'ABSENT'}, "
                  f"{vc['dir_absent'].decode()!r} "
                  f"{'gone' if dabs else 'STILL THERE'}"
                  f"   [the rename reached the SECTOR, not just the screen]")
        made = MUST_NOT_EXIST in names
        print(f"\n  {'FAIL' if made else 'PASS'}  append-missing (directory) "
              f"-> {MUST_NOT_EXIST.decode()!r} "
              f"{'WAS CREATED' if made else 'absent, as on the CF-3300'}")
        ok &= not made
    if tmp:
        os.unlink(tmp)

    ndirs = 1 + len(vkeys)
    print(f"\n===== FAT error disposition: {npass}/{scored} scored "
          f"({len(CASES)} rows, {len(CASES) - scored} NOT MEASURED) "
          f"+ {ndirs} directory checks, over a LIVE FAT layer =====")

    # 🔴 THE DENOMINATOR, PRINTED EVERY RUN (D-FEVERB §4). Closing one hole and
    # saying ALL PASS louder is how a gate stops describing itself. A row with no
    # verb control is satisfied by a verb that ALWAYS errors -- measured, not
    # supposed: K-NAMECTL scored this battery 8/8 at exit 0 over a NAME that
    # renamed nothing, back when name-missing had no control either.
    uncovered = [k for k, _, _, v in CASES if not v]
    print(f"VERB-SUCCESS CONTROLS: {len(CASES) - len(uncovered)} of {len(CASES)} "
          f"rows. The other {len(uncovered)} are satisfied by a verb that always "
          f"errors:\n  {', '.join(uncovered)}\n"
          f"  ('kill-missing' among them is the other REFERENCE-EXACT row, so it "
          f"carries the same\n   weight 'name-missing' does and has the same "
          f"hole. TODO.md / docs/spec-fat-error-verb-control.md §4)")

    if instrument_fault:
        print("SOME NOT MEASURED -- exit 2 = the instrument was broken, NOT an "
              "error-disposition regression")
        return 2
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
