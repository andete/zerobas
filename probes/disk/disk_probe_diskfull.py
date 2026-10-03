# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DISKFULL (gate: diskfull-acceptance): a full disk is `Disk full` (ERR 66)
on ours as on the CF-3300, in its four faces, and what a mid-write one leaves on the disk, each on a fresh disk with every
free cluster marked used (full_disk, below):

  CLOSE  OPEN FOR OUTPUT + PRINT#1,"HELLO" + CLOSE#1: the first cluster is
         allocated AT close, so CLOSE fails with 66 and the channel STAYS OPEN
         (a re-OPEN is File already open, 54); a second CLOSE frees it silently.
  SAVE   a tokenised SAVE: 66.
  PRINT# a loop of 22 B lines: stops with 66. 🔴 THIS FACE HUNG on ours before
         the fix (no prompt in a 60 s window); a hang must FAIL by the run
         window, so the verdict is read off a sentinel line the loop's
         successor prints, never assumed.
  BSAVE  16 KB: 66. 🔴 The sub-ROM SAVE tenant RESUMED its loop after a
         failure (D-DISKFULLRETRY), retrying the doomed flush on every
         remaining byte -- no answer in a 900 s emulated window. Like PRINT#,
         a regression fails by the window.
  SSTAMP tokenised SAVE of a ~2 KB program, ONE cluster free
         (D-SAVEFULLSTAMP): the CF-3300 refuses it WHOLE too -- SF.BAS = the
         $FF marker alone, size 1, one cluster, and NO Ctrl-Z.
  ASTAMP the same program SAVEd ,A (D-ASAVEFULLSTAMP): the CF-3300 STREAMS
         it, so SA.BAS keeps the first 1024 B, stamped; ours left a lost
         cluster.
  BSTAMP the same BSAVE with ONE cluster free, and the directory read back
         (D-DISKFULLSTAMP): the CF-3300 writes the header, refuses the block
         whole and CLOSES -- BF.BIN = header + Ctrl-Z, size 8, in that one
         cluster. Ours streamed 1 KB in and aborted unclosed: a LOST cluster.

Each case is boot-per-case with its own disk and ends in ONE summary line
(`R a b c #`, `S e #`, `P e i #`) because the screen holds 24 rows and the
early rows scroll away. Every field is compared with the CF-3300's, live,
except PRINT#'s I: the CF-3300 fails at its first 256 B RECORD flush (I = 12)
and ours at its first 512 B SECTOR flush (I = 24) -- a pinned divergence that
S10.B (PRINT# on the channel's 256 B record) is expected to move; when it does,
this pin goes red ON PURPOSE.

Exit 0 when every face agrees; 1 on a divergence; 2 when the CF-3300 itself
did not answer (no reference).
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402
import struct                                       # noqa: E402

PRINT_I_PIN = {"STOCK": 12, "OURS": 24}             # 256 B record vs 512 B sector

CASES = {
    "close": (['OPEN"CF.TXT"FOR OUTPUT AS#1', 'PRINT#1,"HELLO"', 'CLOSE#1',
               'A=ERR', 'OPEN"CG.TXT"FOR OUTPUT AS#1', 'B=ERR',
               'CLOSE#1:PRINT"[C2]"', 'PRINT"R";A;B;ERR;"#"'], None),
    "save": (['10 REM', 'SAVE"SF.BAS"', 'PRINT"S";ERR;"#"'], None),
    "print": (['OPEN"PF.TXT"FOR OUTPUT AS#1',
               'FOR I=1TO40:PRINT#1,STRING$(20,65):NEXT',
               'PRINT"P";ERR;I;"#"'], 30.0),
    "bsave": (['BSAVE"BF.BIN",&H8000,&HBFFF', 'PRINT"V";ERR;"#"'], 30.0),
    # ONE free cluster left (STAMP below): what the directory says afterwards
    "bstamp": (['BSAVE"BF.BIN",&H8000,&HBFFF', 'PRINT"W";ERR;"#"'], 30.0),
    # a ~2 KB program (30 REM lines) onto ONE free cluster (D-SAVEFULLSTAMP)
    "sstamp": ([f"{100 + i} REM " + "X" * 60 for i in range(30)]
               + ['SAVE"SF.BAS"', 'PRINT"T";ERR;"#"'], 30.0),
    # the same program as an ASCII listing (D-ASAVEFULLSTAMP)
    "astamp": ([f"{100 + i} REM " + "X" * 60 for i in range(30)]
               + ['SAVE"SA.BAS",A', 'PRINT"U";ERR;"#"'], 30.0),
}
# case -> (free clusters to leave, the file whose entry and content are compared)
STAMP = {"bstamp": (1, "BF", "BIN"), "sstamp": (1, "SF", "BAS"), "astamp": (1, "SA", "BAS")}


def full_disk(path):
    """Mark every free FAT12 cluster used (EOC), in every FAT copy."""
    b = bytearray(open(path, "rb").read())
    bps = struct.unpack_from("<H", b, 11)[0]
    resv = struct.unpack_from("<H", b, 14)[0]
    nfat = b[16]
    spf = struct.unpack_from("<H", b, 22)[0]
    rootent = struct.unpack_from("<H", b, 17)[0]
    spc = b[13]
    total = struct.unpack_from("<H", b, 19)[0]
    first_data = resv + nfat * spf + (rootent * 32 + bps - 1) // bps
    nclus = (total - first_data) // spc + 2
    fat = resv * bps

    def get(c):
        i = fat + c * 3 // 2
        v = b[i] | b[i + 1] << 8
        return v >> 4 if c & 1 else v & 0xFFF

    def put(c, val):
        i = fat + c * 3 // 2
        v = b[i] | b[i + 1] << 8
        v = (v & 0x000F) | (val << 4) if c & 1 else (v & 0xF000) | val
        b[i], b[i + 1] = v & 0xFF, v >> 8

    freed = 0
    for c in range(2, nclus):
        if get(c) == 0:
            put(c, 0xFFF)
            freed += 1
    for k in range(1, nfat):
        b[(resv + k * spf) * bps:(resv + (k + 1) * spf) * bps] = b[fat:fat + spf * bps]
    open(path, "wb").write(b)
    return freed


def run(machine, tag, name):
    lines, run_gap = CASES[name]
    dsk = probe_tmp.tmp(f"diskfull_{name}_{tag}.dsk")
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    full_disk(dsk)
    if name in STAMP:
        free_last(dsk, STAMP[name][0])
    kw = {"run_gap": run_gap} if run_gap else {}
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=("", "SCREEN 0"), boot=14.0, step=4.0,
                              diska=dsk, **kw)[0] or ""
    return re.sub(r"\s+", " ", raw), dsk


def geometry(b):
    bps = struct.unpack_from("<H", b, 11)[0]
    resv = struct.unpack_from("<H", b, 14)[0]
    nfat, spc = b[16], b[13]
    spf = struct.unpack_from("<H", b, 22)[0]
    rootent = struct.unpack_from("<H", b, 17)[0]
    total = struct.unpack_from("<H", b, 19)[0]
    first_data = resv + nfat * spf + (rootent * 32 + bps - 1) // bps
    return bps, resv, nfat, spf, spc, first_data, (total - first_data) // spc + 2


def free_last(path, n):
    """Free the LAST n data clusters again, in every FAT copy."""
    b = bytearray(open(path, "rb").read())
    bps, resv, nfat, spf, spc, first_data, nclus = geometry(b)
    fat = resv * bps
    for c in range(nclus - n, nclus):
        i = fat + c * 3 // 2
        v = b[i] | b[i + 1] << 8
        v = (v & 0x000F) if c & 1 else (v & 0xF000)
        b[i], b[i + 1] = v & 0xFF, v >> 8
    for k in range(1, nfat):
        b[(resv + k * spf) * bps:(resv + (k + 1) * spf) * bps] = b[fat:fat + spf * bps]
    open(path, "wb").write(b)


def stamp(path, stem, ext):
    """The file's entry and its first `size` bytes (at most 16) -- its CONTENT,
    never the slack after it (the CF-3300 leaves FF there, ours 00)."""
    ent = RT.Fat12(path).dirent(stem, ext)
    if not ent:
        return None
    out = {"cluster": ent["cluster"], "size": ent["size"]}
    if ent["cluster"]:
        b = open(path, "rb").read()
        bps, resv, nfat, spf, spc, first_data, nclus = geometry(b)
        off = (first_data + (ent["cluster"] - 2) * spc) * bps
        out["bytes"] = b[off:off + min(ent["size"], 16)].hex(" ")
    return out


def verdict(name, scr):
    """The face's fields, read off the screen; None where the summary line never
    printed (a hang, or a capture that came too early)."""
    key = {"close": "R", "save": "S", "print": "P", "bsave": "V", "bstamp": "W", "sstamp": "T", "astamp": "U"}[name]
    m = re.search(r"\b" + key + r" ?((?:-?\d+ ?)+)#", scr)
    v = {"summary": [int(x) for x in m.group(1).split()] if m else None,
         "disk_full": scr.count("Disk full")}
    if name == "close":
        v["already_open"] = scr.count("File already open")
        v["c2"] = "[C2]" in scr.replace('"[C2]"', "")
    return v


def main():
    got = {}
    for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
        for name in CASES:
            scr, dsk = run(machine, tag, name)
            got[(tag, name)] = verdict(name, scr)
            if name in STAMP:
                got[(tag, name)]["stamp"] = stamp(dsk, *STAMP[name][1:])
            print(f"== {tag} {name}: {got[(tag, name)]}")
            print(f"   screen tail: {scr[-260:]}")
    if any(got[("STOCK", n)]["summary"] is None for n in CASES):
        print("\nINSTRUMENT FAULT: the CF-3300 did not print every summary line -- no reference")
        return 2
    bad = []
    for name in CASES:
        s, o = dict(got[("STOCK", name)]), dict(got[("OURS", name)])
        if name == "print":
            # the record-vs-sector divergence, pinned on each side
            for tag, d in (("STOCK", s), ("OURS", o)):
                summ = d["summary"]
                if summ is None or len(summ) != 2 or summ[1] != PRINT_I_PIN[tag]:
                    bad.append(f"print: {tag} I = {summ and summ[1:]} where the pin says {PRINT_I_PIN[tag]}")
            s["summary"] = s["summary"][:1]
            o["summary"] = o["summary"][:1] if o["summary"] else None
        if s != o:
            bad.append(f"{name}: CF-3300 {s} vs ours {o}")
    for b in bad:
        print("DIVERGES " + b)
    print(f"\n{'PASS' if not bad else 'FAIL'}: a full disk is Disk full in all four faces, and BSAVE, SAVE and SAVE ,A leave the CF-3300's file")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
