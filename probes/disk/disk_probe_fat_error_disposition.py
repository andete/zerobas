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

  python3 probes/disk/disk_probe_fat_error_disposition.py [--machine NAME]

Exit codes: 0 = all rows converged; 1 = a real error-disposition regression;
2 = the PRECONDITION failed, so nothing below it was measured.
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
    ("name-missing",  'NAME"A:NOSUCH.BAS" AS "B.BAS"', "File not found"),
    ("merge-missing", 'MERGE"A:NOSUCH.BAS"'),
]
WANT = "load error"

# A row is `(key, line)` -- pinned to WANT -- or `(key, line, want)` when its
# disposition has been MEASURED on the reference and is reference-exact.
# Normalised here so the default stays visible in the table above rather than
# being repeated eight times.
CASES = [c if len(c) == 3 else (c[0], c[1], WANT) for c in CASES]

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

    # The control runs FIRST, in the same batch: same machine, same mounted
    # image, same boot -- so a green control is evidence about the run the eight
    # rows below were measured in, not about a separate one.
    specs = [("direct", [CONTROL[1]])] + [("direct", [line]) for _, line, _ in CASES]
    raws = omsx_repl.run_cases(args.machine, specs,
                               batch=not args.boot_per_case,
                               reset=("NEW", "CLS"), capture="screen",
                               diska=dsk)
    ctl_raw, raws = raws[0], raws[1:]

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
        for (key, line, _), raw in zip(CASES, raws):
            tail = omsx_repl.screen_tail(raw, line)
            got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
            print(f"  ....  {key:14} {line:38} -> {got[:60]!r}  (not scored)")
        print("\n===== FAT error disposition: NOT MEASURED (precondition failed) =====")
        if tmp:
            os.unlink(tmp)
        return 2

    for (key, line, want), raw in zip(CASES, raws):
        tail = omsx_repl.screen_tail(raw, line)
        got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
        good = want in (tail or "")
        ok &= good
        pin = "" if want == WANT else f"   [reference-exact: {want!r}]"
        print(f"  {'PASS' if good else 'FAIL'}  {key:14} {line:38} -> {got[:60]!r}{pin}")
        if not good:
            print(f"        want {want!r} -- a SILENT return here is the exact "
                  f"signature of a broken error tail")

    npass = sum(1 for (k, l, w), r in zip(CASES, raws)
                if w in (omsx_repl.screen_tail(r, l) or ""))

    # THE SECOND INSTRUMENT, for `append-missing` only: a refusal that still
    # created the file is not a refusal. The screen alone cannot say this -- a
    # build that printed `load error` and created the entry anyway would pass the
    # text check above -- so the machine's own image is parsed after it exits.
    names = dir_names(dsk)
    if names is None:
        print(f"\n*** could not read the directory of {dsk} -- the "
              f"created-anyway check did not run")
        ok = False
    else:
        made = MUST_NOT_EXIST in names
        print(f"\n  {'FAIL' if made else 'PASS'}  append-missing (directory) "
              f"-> {MUST_NOT_EXIST.decode()!r} "
              f"{'WAS CREATED' if made else 'absent, as on the CF-3300'}")
        ok &= not made
    if tmp:
        os.unlink(tmp)

    print(f"\n===== FAT error disposition: {npass}/{len(CASES)} "
          f"+ directory check, over a LIVE FAT layer =====")
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
