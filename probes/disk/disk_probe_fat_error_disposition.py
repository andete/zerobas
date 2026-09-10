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

⚠️ THE WANT IS PER CASE, AND AS OF 2026-08-21 EVERY ONE OF THE EIGHT CARRIES
`File not found`.  It got there in three steps, each waiting for its own code:
`kill-missing` (D-DSKMSG, docs/spec-basic-dskmsg.md §4.3) and `name-missing`
(D-DKNAME, docs/spec-basic-dkname.md §3.3) on 2026-08-07 (R-DK1/R-DK2), five
more on 2026-08-20 (D-LOADERR, docs/loaderr-fix-notes.md), and `bload-missing`
on 2026-08-21 (D-BLNF).  A row that carries its own want is printed with
`[reference-exact: ...]` so the report never reads as if the whole battery had
been re-pinned at once -- which is now what the SET says, but never what any one
slice's evidence said.

⚠️ `WANT` (zerobas's own `load error`) IS THEREFORE NO LONGER THE DEFAULT OF ANY
SCORED VERB ROW, and it is deliberately still here: the MOUNT-arm row below is
pinned to it, the whole no-disk / mount / I-O class still answers it, and the
report prints it as the thing a row is NOT pinned to.  An empty CASES-side use
is not a dead constant -- deleting it would delete the contrast.

⚠️ AND THE TWO STILL DID NOT MOVE TOGETHER.  Both readings were taken in one
session; `kill-missing` moved a slice earlier because `do_kill`'s no-match arm
was reachable on its own once the tenant separated the mount, while `do_name`'s
shared `nm_fail` had to be SPLIT first.  A pin that drifts verb by verb on its
neighbours' evidence stops being a pin -- so each one waited for its own code.

FALSIFICATION RECORD (this is the evidence the gate measures its subject).  With
the error tail neutered, four of the cases below SILENTLY REPORT NOTHING --
load-missing, run-missing, open-missing, merge-missing.  Restoring the tail
restores the message on all of them.  (✅ Since D-LOADERR, 2026-08-20, that
message is `File not found`, raised, not `load error`, printed -- for every one
of those four; `bload-missing` joined them on 2026-08-21, D-BLNF.)  (`append-missing` was added 2026-07-31 by
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
import probe_report  # noqa: E402

# zerobas's own lowercase wording for the whole no-disk / mount / I-O class -- the
# quarantined divergence, and the default `want` for a row that has not been
# measured on the reference.  Defined BEFORE the table that cites it.
WANT = "load error"

# ✅ D-LOADERR, 2026-08-20 (docs/loaderr-msx1-characterization.md). The
# MISSING-FILE half of that class is no longer unmeasured: `File not found` is
# what BOTH references answer for LOAD / RUN"f" / MERGE / OPEN..FOR INPUT /
# OPEN..FOR APPEND, and zerobas now raises it too.  So those five pins move --
# in the same commit as the code, exactly as `kill-missing`'s did.
#
# 🔴 AND THEY WERE A GREEN ORACLE FOR THE DEFECT UNTIL TODAY. Five rows in this
# file asserted `load error` and PASSED for as long as the defect lived; the fix
# is what turned them red. That is the shape this project keeps finding
# [[a-green-oracle-can-assert-the-defect]] -- and it is not a criticism of the
# pin, which was honest: it said "not measured on the reference", and the
# remedy was to measure, which is what happened.
#
# ✅ AND `bload-missing` MOVED THE DAY ITS OWN CODE DID (D-BLNF, 2026-08-21).
# It was held at `load error` on the previous line's rule -- its reference
# reading existed and its FIX did not, and a pin that drifts on a NEIGHBOUR's
# evidence stops being a pin. It did not drift: BLOAD's tenant now tells a
# missing NAME from a missing VOLUME at fat_io_open's own mount/find boundary
# and files BL_STAT = 2, which the resident stub raises as ERR 53. So this pin
# moves in the same commit as that code, exactly as `kill-missing`'s and the
# five above did.
#
# ⚠️ THE OTHER SEVEN ARE STILL UNTOUCHED AND STILL `load error` -- the
# quarantined wording divergence for the no-disk / mount / I-O class, which
# nothing has measured. BLOAD's own mount failure is in THAT class and stays
# there; only the not-found arm moved.
NOTFOUND = "File not found"

# Each verb must route a "not found" through the FAT primitive shim layer and
# surface zerobas's load_error.  Kept to DIRECT-mode one-liners so the failure
# lands on the line right below the echoed command.
CASES = [
    ("load-missing",  'LOAD"A:NOSUCH.BAS"', NOTFOUND, "load-alive"),
    ("run-missing",   'RUN"A:NOSUCH.BAS"', NOTFOUND, "run-alive"),
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
    # ⚠️ WHEN THIS WAS WRITTEN THE OTHER SEVEN WERE UNTOUCHED AND STAYED
    # `load error` -- the quarantined wording divergence basic/PROVENANCE.md
    # records for the whole no-disk / mount / I-O class, which NOTHING in
    # D-DSKMSG measured. A pin that drifts verb by verb on its neighbours'
    # evidence stops being a pin, so they waited. ✅ All seven have since been
    # measured for THEMSELVES and moved with their own code: five on 2026-08-20
    # (D-LOADERR), `name-missing` on 2026-08-07 (D-DKNAME), `bload-missing` on
    # 2026-08-21 (D-BLNF). The rule is what made that take three slices.
    ("kill-missing",  'KILL"A:NOSUCH.BAS"', "File not found", "kill-alive"),
    ("bload-missing", 'BLOAD"A:NOSUCH.BIN"', NOTFOUND, "bload-alive"),
    ("open-missing",  'OPEN"A:NOSUCH.DAT" FOR INPUT AS #1', NOTFOUND,
     "open-alive"),
    # D-APPMISS (docs/spec-basic-append-missing-refuse.md §5c). APPEND used to
    # CREATE the missing file -- `fat_io_append` jumped into `fat_io_create` on a
    # `fat_find` miss -- where the CF-3300 raises `File not found`, opens no
    # channel and writes no directory entry. This is the row that says the refusal
    # lands on the SAME class as its INPUT sibling directly above: the LOF battery
    # reads the LAST error on screen and so reads `File not open` from the trailing
    # statement whatever OPEN raised, and `err_class` there deliberately does not
    # know zerobas's `load error` wording. `append-missing` red with `open-missing`
    # green means the APPEND path reached a different class.
    ("append-missing", 'OPEN"A:NOSUCH.DAT" FOR APPEND AS #1', NOTFOUND,
     "append-alive"),
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
    ("merge-missing", 'MERGE"A:NOSUCH.BAS"', NOTFOUND, "merge-alive"),
]

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

# --- THE MOUNT GROUP (D-MOUNTROW, docs/spec-fat-error-mount-row.md) ----------
# Every row above runs with a disk MOUNTED, and reaches `fat_find`. These two run
# in a SECOND boot with NO disk at all, so they reach only `fat_mount` -- the arm
# D-DSKMSG's K-KILL2 and D-DKNAME's K-NAME2 both re-pointed while reddening
# NOTHING, because no row in this tree drove it. They are the reason those two
# written-down predicted misses are now real cuts.
#
# 🔴 A SEPARATE GROUP, NEVER A WIDENED `CASES`. Until 2026-07-31 this probe ran
# with no disk mounted at all, so EVERY case failed in `fat_mount` and never
# reached `fat_find`: the battery measured the MOUNT miss while its docstring
# claimed the FIND miss, and the two are indistinguishable by their answer
# (`load error` either way). Mounting a disk is what fixed that. Re-introducing
# an unmounted boot as anything but its own labelled group would rebuild exactly
# the conflation that history removed.
#
# 🎯 AND THE POSITIVE EVIDENCE IS THE CONTRAST, WHICH COSTS NOTHING. `twin` names
# the MOUNTED row typing the same verb: measured, `KILL"A:NOSUCH.BAS"` answers
# `File not found` with a disk and `load error` without one. A verb that always
# errors -- and a dead disk ROM -- produce ONE answer, so two different answers
# from one verb is evidence no dead subject can fake
# ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).
#
# 🎯 AND THE THIRD ROW IS THE ONE ITS OWN FIX CREATED (D-BLNF, 2026-08-21).
# BLOAD's tenant now splits fat_io_open at the mount/find boundary and routes
# ONE side at ERR 53. Nothing in this tree drove BLOAD's MOUNT arm, so moving
# that `jp c,bl_load_error` to `bl_notfound` -- making a machine with no disk in
# it answer `File not found` -- reddened NOTHING. That is the same hole
# `kill-nodisk` and `name-nodisk` were added to close, in the same verb family,
# opened again by the same shape of fix. A new arm needs its own mount row the
# day the arm lands, not the day someone breaks it.
MOUNT_CASES = [
    ("kill-nodisk", 'KILL"A:NOSUCH.BAS"', "kill-missing"),
    ("name-nodisk", 'NAME"A:NOSUCH.BAS" AS "B.BAS"', "name-missing"),
    ("bload-nodisk", 'BLOAD"A:NOSUCH.BIN"', "bload-missing"),
]

# ⚠️ THE BATTERY'S OWN PRECONDITION CANNOT RUN IN THAT BOOT -- `FILES"A:HI.TXT"`
# is precisely what an empty drive cannot do. So the mount group carries its own
# liveness control, chosen to need no disk: if the machine did not boot, or the
# harness delivered nothing, this reads `<none>` and the group is NOT MEASURED
# rather than passing on two rows of silence.
MOUNT_LIVE = ("mount-live", "PRINT 6*7", "42")

assert {t for _, _, t in MOUNT_CASES} <= {k for k, *_ in CASES}, \
    "a MOUNT_CASES twin names a row that is not in CASES"


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
#
# ⚠️ KILL IS THE ASYMMETRIC ONE, and it is why `absent` exists. NAME's success is
# POSITIVE on screen -- a name that was not there before is. KILL's success is an
# ABSENCE, and an absence is satisfied by a machine that cannot list a directory
# at all. So `kill-alive` asserts the SURVIVORS by name (positive text, the
# listing demonstrably ran) AND the casualty gone, which together are evidence;
# either half alone is not. Same reasoning `dsk-killhit` carries in
# basic_probe_dskmsg.py, and the directory instrument settles it independently.
#
# ⚠️ EVERY LINE BELOW WAS SCOUTED ON THE MACHINE BEFORE IT WAS WRITTEN DOWN, and
# one candidate was refused by the reading: `MERGE"A:PROG.BAS"` (the TOKENISED
# fixture) raises `Syntax error` and merges nothing -- MERGE wants an ASCII-saved
# file -- so `merge-alive` does the SAVE",A" round trip instead. Designing a
# control from what a verb is assumed to print is how a control ends up asserting
# something no build ever produces.
#
# ⚠️ RAM IS PRE-POISONED WHERE THE EVIDENCE IS A PEEK. The battery is BATCHED --
# one boot, `NEW`/`CLS` between cases -- so page-3 RAM SURVIVES from case to case
# and a landmark left by an earlier case would read as this one's success.
# `run-alive` and `bload-alive` write 0 to their landmark first; scouted at `'0'`.
#
# ⚠️ dir_present/dir_absent are OPTIONAL (None = no directory instrument). The
# read-only verbs -- LOAD, RUN, BLOAD, OPEN -- change no directory entry, so
# there is nothing for a second instrument to read and their evidence is
# screen-only. Said out loud rather than implied by a missing column.
#
# ⚠️ THREE CONTROLS LEAN ON A SECOND VERB: `merge-alive` on `SAVE",A"`,
# `append-alive` on OPEN/OUTPUT + OPEN/INPUT, and `kill-alive` on FILES. If one
# of those breaks, the control reds for a reason that is not its own verb. That
# is acceptable HERE and only here, because the failure is LOUD: the row prints
# NOT MEASURED at exit 2 -- an instrument fault, which is exactly what it is --
# and never a silent PASS.
VERB_CONTROLS = {
    # --- read-only / creating controls run FIRST; the two MUTATING ones last ---
    "load-alive": dict(
        lines=['LOAD"A:PROG.BAS"', "LIST"],
        shown='LOAD"A:PROG.BAS" : LIST',
        want=("POKE", "123"),                 # the fixture line, detokenised
        absent=(),
        dir_present=None, dir_absent=None,
        guards="load-missing",
    ),
    "run-alive": dict(
        lines=["POKE &HD002,0", 'RUN"A:PROG.BAS"', "PRINT PEEK(&HD002)"],
        shown='POKE 0 : RUN"A:PROG.BAS" : PRINT PEEK',
        want=("123",),                        # PROG.BAS is `10 POKE &HD002,123`
        absent=(),
        dir_present=None, dir_absent=None,
        guards="run-missing",
    ),
    "bload-alive": dict(
        lines=["POKE &HC000,0", 'BLOAD"A:PROG.BIN"', "PRINT PEEK(&HC000)"],
        shown='POKE 0 : BLOAD"A:PROG.BIN" : PRINT PEEK',
        want=("62",),                         # $3E = the blob's first opcode
        absent=(),
        dir_present=None, dir_absent=None,
        guards="bload-missing",
    ),
    "open-alive": dict(
        lines=['OPEN"A:HI.TXT" FOR INPUT AS #1', "LINE INPUT#1,A$", "CLOSE",
               "PRINT A$"],
        shown='OPEN"A:HI.TXT" INPUT : LINE INPUT# : PRINT',
        want=("Hello", "zerobas-disk"),       # HI.TXT's actual first line
        absent=(),
        dir_present=None, dir_absent=None,
        guards="open-missing",
    ),
    "append-alive": dict(
        lines=['OPEN"A:AP.TXT" FOR OUTPUT AS #1', 'PRINT#1,"AA"', "CLOSE",
               'OPEN"A:AP.TXT" FOR APPEND AS #1', 'PRINT#1,"BB"', "CLOSE",
               'OPEN"A:AP.TXT" FOR INPUT AS #1', "LINE INPUT#1,A$",
               "LINE INPUT#1,B$", "CLOSE", "PRINT A$;B$"],
        shown='OUTPUT "AA" : APPEND "BB" : read both back',
        want=("AABB",),                       # APPEND kept AA and added BB
        absent=(),
        dir_present=b"AP      TXT", dir_absent=None,
        # 🎯 D-FATSIZE: THE SIZE IS THE WITNESS THAT NEEDS NO SECOND VERB, and it
        # is DISCRIMINATING rather than decorative. `AA\r\n` + `BB\r\n` + the
        # `$1A` EOF marker is 9; an APPEND that behaved like OUTPUT would have
        # truncated to `BB\r\n` + EOF = 5. So this number separates the two
        # outcomes on its own, and it does so from the directory sector -- §8.6's
        # gap (2) was that the readback goes through OPEN FOR INPUT, a second
        # verb whose failure marks this row NOT MEASURED for a reason that is not
        # APPEND's.
        # ⚠️ MEASURED, NOT DERIVED: reasoning it out gives 8, because the EOF byte
        # is easy to forget. The probe printed `dir size 9` in observe-only mode
        # first and the pin was written from that.
        dir_size=9,
        guards="append-missing",
    ),
    "merge-alive": dict(
        # MERGE's DISTINGUISHING property is that it merges INTO an existing
        # program where LOAD replaces it. So line 20 is typed AFTER the NEW and
        # must SURVIVE the merge: `MG` proves the file arrived, `ZQ` proves the
        # resident program was not replaced. A control asserting only `MG` would
        # be green on a MERGE that behaved like LOAD.
        lines=["10 REM MG", 'SAVE"A:M.BAS",A', "NEW", "20 REM ZQ",
               'MERGE"A:M.BAS"', "LIST"],
        shown='SAVE",A" : NEW : 20 REM ZQ : MERGE : LIST',
        want=("MG", "ZQ"),
        absent=(),
        dir_present=b"M       BAS", dir_absent=None,
        guards="merge-missing",
    ),
    "name-alive": dict(
        lines=['NAME"A:PROG2.BAS" AS "REN2.BAS"', 'FILES"A:REN2.BAS"'],
        shown='NAME"A:PROG2.BAS" AS "REN2.BAS" : FILES',
        want=("REN2", "BAS"),                 # screen: positive text
        absent=(),
        dir_present=b"REN2    BAS",           # directory: the rename LANDED
        dir_absent=b"PROG2   BAS",            # directory: and the old one went
        guards="name-missing",
    ),
    "kill-alive": dict(
        lines=['KILL"A:PROG.BIN"', 'FILES"*.BIN"'],
        shown='KILL"A:PROG.BIN" : FILES"*.BIN"',
        want=("TEST", "BIN"),                 # screen: the survivor, by name
        absent=("PROG    .BIN",),             # screen: the casualty, 8.3-rendered
        dir_present=b"TEST    BIN",           # directory: the volume still has files
        dir_absent=b"PROG    BIN",            # directory: the delete LANDED
        guards="kill-missing",
    ),
}

# 🔴 THE ORDER IS LOAD-BEARING, SO IT IS ASSERTED RATHER THAN COMMENTED.
# `bload-alive` READS PROG.BIN; `kill-alive` DELETES it. Reordering the dict
# would make bload-alive red for a reason that is not BLOAD -- loudly (exit 2),
# but for the wrong reason. This turns a silent reorder into an import-time stop.
assert (list(VERB_CONTROLS).index("bload-alive")
        < list(VERB_CONTROLS).index("kill-alive")), \
    "bload-alive reads PROG.BIN, which kill-alive DELETES -- order is load-bearing"

# Every case that names a control must name one that exists, and vice versa: a
# typo would silently leave a row ungated while the denominator counted it.
assert {v for *_, v in CASES if v} == set(VERB_CONTROLS), \
    "CASES' verb-control names and VERB_CONTROLS disagree"

# The file `append-missing` must NOT leave behind, and where to look for it.
SRC_DSK = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "disk", "test720.dsk")
MUST_NOT_EXIST = b"NOSUCH  DAT"


def dir_sizes(dsk_path: str):
    """{11-byte name: size in bytes} from the FAT12 root directory, or None.

    🎯 D-FATSIZE: THE SIZE IS THE EVIDENCE `append-alive` ACTUALLY WANTS.
    APPEND's distinguishing property is that it KEEPS what was there and adds to
    it -- an APPEND that behaved like OUTPUT would truncate. Today the row proves
    that by re-reading the file through `OPEN FOR INPUT`, which is a SECOND VERB:
    §8.6's gap (2), where a break in OPEN/INPUT marks this row NOT MEASURED for a
    reason that is not APPEND's. The directory entry carries the length already,
    32 bytes from the same sector `dir_names` is walking, and it answers the
    question without asking another verb anything.
    ⚠️ It does NOT replace the readback. The readback proves the BYTES are right;
    the size proves the file GREW. Two witnesses of one claim, and the coupling
    now costs only the weaker one if OPEN/INPUT breaks.
    """
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
    out = {}
    for i in range(nroot):
        e = d[root + i * 32: root + i * 32 + 32]
        if len(e) < 32 or e[0] == 0:
            break
        if e[0] != 0xE5 and not (e[11] & 0x18):
            out[bytes(e[:11])] = struct.unpack("<I", e[28:32])[0]
    return out


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
    # docs/spec-probe-rowshape.md I3: every exit path that prints report rows
    # ends with ONE terminator stating how many, so a knife runner reads a
    # COUNT instead of guessing this report's layout. The rows themselves are
    # deliberately NOT touched -- this probe already satisfied I1 and I2 before
    # the slice that added them, and is the gate's positive control for both.
    nrows = 0
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

    # --- the MOUNT group: a SECOND boot, with NO disk (D-MOUNTROW §3) --------
    # `diska` is omitted entirely rather than pointed at a blank image: an empty
    # DRIVE is the configuration the residual names, and a blank-but-valid image
    # would reach fat_mount successfully and measure the find miss again.
    mspecs = ([("direct", [MOUNT_LIVE[1]])]
              + [("direct", [line]) for _, line, _ in MOUNT_CASES])
    mraws = omsx_repl.run_cases(args.machine, mspecs,
                                batch=not args.boot_per_case,
                                reset=("NEW", "CLS"), capture="screen")
    mlive_tail = omsx_repl.screen_tail(mraws[0], MOUNT_LIVE[1])
    mlive_ok = MOUNT_LIVE[2] in (mlive_tail or "")
    mraws = mraws[1:]

    ok = True
    print("=" * 72)
    print("FAT-primitive ERROR disposition (Cy=1 out of fatprim_bounce)")
    print("=" * 72)

    ctl_tail = omsx_repl.screen_tail(ctl_raw, CONTROL[1])
    ctl_got = " | ".join(t.strip() for t in str(ctl_tail or "").split("\n") if t.strip())
    ctl_ok = all(w in (ctl_tail or "") for w in CONTROL_WANT)
    print(f"  {'PASS' if ctl_ok else 'FAIL'}  {CONTROL[0]:14} {CONTROL[1]:38} "
          f"-> {ctl_got[:60]!r}   [PRECONDITION]")
    nrows += 1
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
            nrows += 1
        print("\n===== FAT error disposition: NOT MEASURED (precondition failed) =====")
        print(probe_report.footer(nrows, 0,
                                  "NOT MEASURED (the precondition failed)"))
        if tmp:
            os.unlink(tmp)
        return 2

    # ONE read of the machine's own image, after openMSX exited. It is the
    # second instrument for BOTH the per-verb controls (did the rename reach the
    # sector?) and `append-missing` (was the file created anyway?).
    names = dir_names(dsk)
    sizes = dir_sizes(dsk) or {}

    # --- the per-verb controls (D-FEVERB §2.2), screen AND directory ----------
    vok = {}
    for k in vkeys:
        vc = VERB_CONTROLS[k]
        tail = omsx_repl.screen_tail(vraws[k], vc["lines"][-1])
        got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
        scr = (all(w in (tail or "") for w in vc["want"])
               and not any(u in (tail or "") for u in vc["absent"]))
        # The directory instrument is OPTIONAL: a read-only verb changes no
        # directory entry, so there is nothing for a second instrument to read.
        # `None` means "not applicable", never "passed".
        dpres = (names is not None and vc["dir_present"] in names
                 if vc["dir_present"] else None)
        dabs = (names is not None and vc["dir_absent"] not in names
                if vc["dir_absent"] else None)
        # D-FATSIZE: the SIZE witness. `None` means "not applicable" for this
        # control, exactly like dir_present/dir_absent above -- never "passed".
        want_sz = vc.get("dir_size")
        got_sz = sizes.get(vc["dir_present"]) if vc["dir_present"] else None
        dsz = None if want_sz is None else (got_sz == want_sz)
        vok[k] = (scr and dpres is not False and dabs is not False
                  and dsz is not False)
        szinfo = ""
        if vc["dir_present"] and got_sz is not None:
            szinfo = (f"  dir size {got_sz}"
                      + ("" if want_sz is None else f" (want {want_sz})"))
        print(f"  {'PASS' if vok[k] else 'FAIL'}  {k:14} {vc['shown']:38} "
              f"-> {got[:60]!r}{szinfo}   [VERB CONTROL for {vc['guards']}]")
        nrows += 1
        if not vok[k]:
            # ⚠️ EVERY FIELD HERE IS OPTIONAL, AND THIS BRANCH ONLY RUNS WHEN THE
            # CONTROL FAILS. An earlier version formatted `dir_present.decode()`
            # unconditionally and crashed with AttributeError on the read-only
            # controls, whose dir fields are None -- a latent traceback on the one
            # path that matters, invisible to every green run. The knives found it.
            why = [f"screen wanted {' + '.join(vc['want'])}"
                   + (f" and NOT {' / '.join(vc['absent'])}" if vc["absent"] else "")
                   + f": {'ok' if scr else 'MISSING'}"]
            if vc["dir_present"]:
                why.append(f"directory wanted {vc['dir_present'].decode()!r} "
                           f"present: {'ok' if dpres else 'ABSENT'}")
            if vc["dir_absent"]:
                why.append(f"directory wanted {vc['dir_absent'].decode()!r} "
                           f"absent: {'ok' if dabs else 'STILL THERE'}")
            if names is None:
                why.append("the image was unreadable")
            print("        " + ";  ".join(why))
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
            nrows += 1
            continue
        good = want in (tail or "")
        ok &= good
        scored += 1
        guard = f"   [verb control: {vc_key}]" if vc_key else ""
        print(f"  {'PASS' if good else 'FAIL'}  {key:14} {line:38} "
              f"-> {got[:60]!r}{pin}{guard}")
        nrows += 1
        if not good:
            print(f"        want {want!r} -- a SILENT return here is the exact "
                  f"signature of a broken error tail")

    npass = sum(1 for (k, l, w, v), r in zip(CASES, raws)
                if (not v or vok[v]) and w in (omsx_repl.screen_tail(r, l) or ""))

    # --- the MOUNT group, scored (D-MOUNTROW §3) -----------------------------
    # ORDER IS LOAD-BEARING. A tail that is not the pinned string is a real
    # disposition REGRESSION (exit 1) and is checked FIRST; only a row that still
    # reads the pin can then fail the CONTRAST, which means the machine cannot
    # tell a mount miss from a find miss -- the dead-disk-ROM signature (exit 2).
    # Reversed, the knives this group exists for (K-KILL2 / K-NAME2, which move
    # the mount arm to `File not found`) would be reported as an instrument fault
    # instead of as the regression they are.
    mtails = {}
    print(f"\n  {'PASS' if mlive_ok else 'FAIL'}  {MOUNT_LIVE[0]:14} "
          f"{MOUNT_LIVE[1]:38} -> "
          f"{str(mlive_tail or '<none>').strip()[:60]!r}   "
          f"[LIVENESS for the no-disk boot]")
    if not mlive_ok:
        print(f"        want {MOUNT_LIVE[2]!r} -- the no-disk boot never reached "
              f"a working interpreter, so the mount rows below are two rows of\n"
              f"        silence, not a measurement. Exit 2, not 1.")
    mscored = mpass = 0
    for (key, line, twin), raw in zip(MOUNT_CASES, mraws):
        tail = omsx_repl.screen_tail(raw, line)
        got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
        twin_tail = omsx_repl.screen_tail(
            raws[[c[0] for c in CASES].index(twin)],
            [c[1] for c in CASES][[c[0] for c in CASES].index(twin)])
        mtails[key] = got
        pinned = WANT in (tail or "")
        if not mlive_ok:
            print(f"  ....  {key:14} {line:38} -> {got[:60]!r}"
                  f"   NOT MEASURED (liveness failed)")
            nrows += 1
            continue
        if not pinned:
            mscored += 1
            ok = False
            print(f"  FAIL  {key:14} {line:38} -> {got[:60]!r}"
                  f"   [MOUNT arm, pinned {WANT!r}]")
            nrows += 1
            print(f"        want {WANT!r} at an EMPTY DRIVE -- this row exists "
                  f"because K-KILL2/K-NAME2 reddened nothing without it")
            continue
        differs = (tail or "") != (twin_tail or "")
        if not differs:
            print(f"  ....  {key:14} {line:38} -> {got[:60]!r}"
                  f"   NOT MEASURED (reads the same as {twin!r})")
            nrows += 1
            print(f"        the mounted twin answers the SAME string, so this "
                  f"machine cannot distinguish a MOUNT miss from a FIND miss --\n"
                  f"        which is what a dead disk ROM looks like. Exit 2, "
                  f"not 1.")
            continue
        mscored += 1
        mpass += 1
        print(f"  PASS  {key:14} {line:38} -> {got[:60]!r}"
              f"   [MOUNT arm; twin {twin!r} answers differently]")
        nrows += 1
    mount_fault = (not mlive_ok) or mscored < len(MOUNT_CASES)

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
            if not (vc["dir_present"] or vc["dir_absent"]):
                continue                    # read-only verb: no second instrument
            bits, good = [], True
            if vc["dir_present"]:
                hit = vc["dir_present"] in names
                good &= hit
                bits.append(f"{vc['dir_present'].decode()!r} "
                            f"{'present' if hit else 'ABSENT'}")
            if vc["dir_absent"]:
                gone = vc["dir_absent"] not in names
                good &= gone
                bits.append(f"{vc['dir_absent'].decode()!r} "
                            f"{'gone' if gone else 'STILL THERE'}")
            print(f"\n  {'PASS' if good else 'FAIL'}  {k} (directory) "
                  f"-> {', '.join(bits)}"
                  f"   [{vc['guards'].split('-')[0].upper()} reached the SECTOR, "
                  f"not just the screen]")
        made = MUST_NOT_EXIST in names
        print(f"\n  {'FAIL' if made else 'PASS'}  append-missing (directory) "
              f"-> {MUST_NOT_EXIST.decode()!r} "
              f"{'WAS CREATED' if made else 'absent, as on the CF-3300'}")
        ok &= not made
    if tmp:
        os.unlink(tmp)

    ndirs = 1 + sum(1 for k in vkeys
                    if VERB_CONTROLS[k]["dir_present"]
                    or VERB_CONTROLS[k]["dir_absent"])
    print(f"\n===== FAT error disposition: {npass}/{scored} FIND scored "
          f"({len(CASES)} rows, {len(CASES) - scored} NOT MEASURED) "
          f"+ {mpass}/{mscored} MOUNT scored ({len(MOUNT_CASES)} rows) "
          f"+ {ndirs} directory checks, over a LIVE FAT layer =====")

    # 🔴 THE DENOMINATOR, PRINTED EVERY RUN (D-FEVERB §4). Closing one hole and
    # saying ALL PASS louder is how a gate stops describing itself. A row with no
    # verb control is satisfied by a verb that ALWAYS errors -- measured, not
    # supposed: K-NAMECTL scored this battery 8/8 at exit 0 over a NAME that
    # renamed nothing, back when name-missing had no control either.
    # ⚠️ EVERY CLAUSE OF THIS PARAGRAPH IS DERIVED, none of it typed. The first
    # version hard-coded "'kill-missing' among them is the other reference-exact
    # row" -- true when it was written, FALSE one commit later when kill-missing
    # got a control, and printed by the gate as if measured. That is the same
    # defect as a NOT-GATED list holding a non-exclusion, inverted: a footnote
    # naming a row that has LEFT the list it annotates.
    uncovered = [k for k, _, _, v in CASES if not v]
    exact = [k for k, _, w, v in CASES if not v and w != WANT]
    nodir = [k for k in vkeys if not (VERB_CONTROLS[k]["dir_present"]
                                      or VERB_CONTROLS[k]["dir_absent"])]
    print(f"VERB-SUCCESS CONTROLS: {len(CASES) - len(uncovered)} of {len(CASES)} "
          f"rows.")
    if not uncovered:
        # ⚠️ The all-covered branch is written out rather than left to a format
        # string that would print "The other 0 are satisfied by:" and an empty
        # list. A denominator line that degrades into nonsense at its own
        # boundary is not a denominator line.
        print(f"  (every row's verb is shown reaching a SUCCESS disposition in "
              f"this same run. {len(nodir)} of the {len(vkeys)} controls are "
              f"SCREEN-ONLY --\n   {', '.join(nodir)} -- because a read-only verb "
              f"changes no directory entry for a second instrument to read.)")
    else:
        print(f"  The other {len(uncovered)} are satisfied by a verb that always "
              f"errors:\n  {', '.join(uncovered)}")
        if exact:
            note = ("REFERENCE-EXACT and still uncovered: " + ", ".join(exact)
                    + " -- pinned to a MEASURED reference answer with no control "
                      "behind the verb, which is the pairing that matters most")
        else:
            note = (f"none of the {len(uncovered)} is reference-exact -- every one "
                    f"is pinned to zerobas's own {WANT!r}, the quarantined "
                    f"divergence")
        print(f"  ({note}. TODO.md / docs/spec-fat-error-verb-control.md §4)")

    # 🔴 THE MOUNT GROUP'S OWN DENOMINATOR (D-MOUNTROW). Its rows have no
    # VERB_CONTROLS entry and cannot have one: at an empty drive neither verb can
    # reach a SUCCESS disposition, which is the whole point of the
    # configuration. What stands in for it is stated here rather than left to be
    # assumed -- one liveness row for the boot, and a per-row CONTRAST against
    # the mounted twin.
    print(f"MOUNT-ARM ROWS: {len(MOUNT_CASES)} ({', '.join(k for k, _, _ in MOUNT_CASES)}), "
          f"at an EMPTY DRIVE, pinned to zerobas's own {WANT!r}.")
    print(f"  (no verb control is possible there -- neither verb CAN succeed at "
          f"an empty drive. In its place: {MOUNT_LIVE[0]!r} proves the boot, and "
          f"each row\n   must answer DIFFERENTLY from its mounted twin "
          + ", ".join(f"{k}<>{t}" for k, _, t in MOUNT_CASES)
          + ". These rows are what make D-DSKMSG's K-KILL2 and\n   D-DKNAME's "
          "K-NAME2 real cuts instead of predicted misses -- "
          "docs/spec-fat-error-mount-row.md)")

    print(probe_report.footer(nrows, scored + mscored,
                              "ALL PASS" if ok else "SOME FAILED"))
    if instrument_fault or mount_fault:
        print("SOME NOT MEASURED -- exit 2 = the instrument was broken, NOT an "
              "error-disposition regression")
        return 2
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
