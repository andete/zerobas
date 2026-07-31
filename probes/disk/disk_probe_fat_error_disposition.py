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

FALSIFICATION RECORD (this is the evidence the gate measures its subject).  With
the error tail neutered, four of the cases below SILENTLY REPORT NOTHING --
load-missing, run-missing, open-missing, merge-missing.  Restoring the tail
restores `load error` on all of them.  (`append-missing` was added 2026-07-31 by
D-APPMISS and postdates that experiment; it shares open-missing's disposition.)
If you change fatprim_bounce, re-run that experiment rather than trusting a green
here.

  python3 probes/disk/disk_probe_fat_error_disposition.py [--machine NAME]
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
    ("kill-missing",  'KILL"A:NOSUCH.BAS"'),
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
    ("name-missing",  'NAME"A:NOSUCH.BAS" AS "B.BAS"'),
    ("merge-missing", 'MERGE"A:NOSUCH.BAS"'),
]
WANT = "load error"

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

    specs = [("direct", [line]) for _, line in CASES]
    raws = omsx_repl.run_cases(args.machine, specs,
                               batch=not args.boot_per_case,
                               reset=("NEW", "CLS"), capture="screen",
                               diska=dsk)

    ok = True
    print("=" * 72)
    print("FAT-primitive ERROR disposition (Cy=1 out of fatprim_bounce)")
    print("=" * 72)
    for (key, line), raw in zip(CASES, raws):
        tail = omsx_repl.screen_tail(raw, line)
        got = " | ".join(t.strip() for t in str(tail or "").split("\n") if t.strip())
        good = WANT in (tail or "")
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {key:14} {line:38} -> {got[:60]!r}")
        if not good:
            print(f"        want {WANT!r} -- a SILENT return here is the exact "
                  f"signature of a broken error tail")

    npass = sum(1 for (k, l), r in zip(CASES, raws)
                if WANT in (omsx_repl.screen_tail(r, l) or ""))

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
          f"+ directory check =====")
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
