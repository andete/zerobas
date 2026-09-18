#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOADRUN: what does a tokenised `LOAD` cost PER BYTE?  The instrument
spec-diskcode-eviction.md §6.2b specified, built.

WHY A SECOND PROBE. `scratchpad/loadtime_probe.py` asked this question and could
not answer it: its two clock reads sat either side of the LOAD in SEPARATE
INJECTED LINES, so the second one fired on the HARNESS'S TIMETABLE and every
configuration measured the injection gap instead of the work. Its header carries
the diagnosis and the method that would work; this file is that method.

THE METHOD. Two things make the clock read itself honest:

  * **`LOAD"x",R`** -- the loaded program runs the instant the load completes, so
    the second clock read is triggered BY THE WORK. No injection gap intervenes.
  * **`TIME`, not a variable** -- `LOAD,R` does a NEW and clears variables, which
    is why loadtime_probe's header concluded ",R does not help". It helps: TIME
    is a SYSTEM cell, not a BASIC variable, so `TIME=0` before the LOAD survives
    into the loaded program, whose FIRST line prints it.

      driver (typed)          loaded program (on the disk)
      10 TIME=0               10 PRINT "@K";TIME      <- the whole load, in jiffies
      20 LOAD"L.BAS",R        20.. REM padding
                              99 PRINT "@S";<id>      <- which program is resident

    The capture may fire arbitrarily late: the reading is TIME AS PRINTED, so a
    generous `step` costs nothing and cannot distort it. That is the property
    loadtime_probe lacked.

THE HEADLINE IS A DIFFERENCE, NOT AN ABSOLUTE. Three programs are loaded --
small, mid and large -- identical but for the amount of REM padding between the
two marker lines. Per-byte cost is (jiffies_L - jiffies_S) / (bytes_L - bytes_S),
so every FIXED cost -- directory search, open, the first seek, the marker line's
own PRINT -- cancels instead of being estimated. That the fixed cost is worth
cancelling is not a guess: the reference spends 51 jiffies before the first
payload byte and we spend 16.

The MID program exists only to check the assumption the other two cannot see --
that the cost is LINEAR in size. A FAT chain walk that re-read a FAT sector per
cluster would be superlinear, and a slope taken from two endpoints would look
perfectly clean while understating every large load.

⚠️ THE TOKENISED LINES COME FROM THE MACHINE, NOT FROM ME. §6.2b is explicit:
guessing MSX token bytes is not allowed. So PHASE A types the marker lines and
one REM line into the machine, `SAVE`s them, and this probe reads the tokenised
bytes back out of the disk image. Everything the measurement loads is then built
from bytes the machine itself produced -- and the machine's REM line is compared
against loadtime_probe's hand-built generator, which is a free check on a file
that is still in the tree.

⚠️ CONTROLS, so a pass cannot be vacuous:
  * **TIME MUST SURVIVE THE LOAD**, or the reading is the time since some reset
    the probe does not control. Measured, not assumed: a delay case times a bare
    FOR loop, and a fourth case runs the SAME loop and THEN loads the small
    program. The two must COMPOSE -- dly + S == dly_then_S within tolerance --
    and if they do not, the probe refuses and reports no figure;
  * **the large load must exceed the small one**, or nothing was loaded;
  * **the mid-size load must sit on the line joining the other two**, or the
    headline is a chord across a curve and does not mean what it says;
  * **the identity witness** `@S` must read 1 for the small program and 2 for the
    large one, or a failed open left the previous program resident and the
    difference is noise between two runs of the same thing;
  * **the marker must appear at all** in every case, or that case did not run;
  * the seed program must read back with the line numbers it was typed with, or
    the screen editor rejected a line and the padding is not what it seems.
"""
import os, shutil, struct, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                              # noqa: E402
import fatbuf_probe as FB                                     # noqa: E402

TXTTAB = 0x8001
MARK, IDMARK = "@K", "@S"
SMALL_B, MID_B, LARGE_B = 1024, 7168, 14336   # target padding sizes
DELAY = 1500                          # FOR..NEXT iterations in the TIME control

# 🔴 THE MARKERS ARE BUILT WITH CHR$ SO THE TYPED LINE DOES NOT CONTAIN THEM.
# [[trapsvc-echo-fence]]: a probe whose fence appears in the source it echoes
# reads its own typed line as a result. Here it matters twice -- the seed phase
# types these lines on screen, and the driver's own text must not be mistakable
# for the loaded program's output.
SEED_LINES = ['10 PRINT CHR$(64)+CHR$(75);TIME',
              '20 REM XXXXXXXXXXXXXX',
              '30 PRINT CHR$(64)+CHR$(83);1',
              '40 PRINT CHR$(64)+CHR$(83);2',
              '50 PRINT CHR$(64)+CHR$(83);3']

SIDES = [
    ("cf3300", "National_CF-3300", ("", "SCREEN 0", "CLOSE", "NEW", "CLS"), 60),
    ("zb", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"),
     ("CLOSE", "NEW", "CLS"), 50),
]
BOOT, STEP, CAP_GAP = 8.0, 25.0, 8.0


# --------------------------------------------------------------------------
# the disk image: geometry, one reader, one writer
# --------------------------------------------------------------------------
def geom(d):
    bps = struct.unpack("<H", d[11:13])[0]
    spc, rsv = d[13], struct.unpack("<H", d[14:16])[0]
    nf = d[16]
    nroot = struct.unpack("<H", d[17:19])[0]
    spf = struct.unpack("<H", d[22:24])[0]
    root_sec = rsv + nf * spf
    return dict(bps=bps, spc=spc, rsv=rsv, nf=nf, spf=spf, nroot=nroot,
                root_sec=root_sec,
                data_sec=root_sec + (nroot * 32 + bps - 1) // bps)


def read_file(img, g, name8):
    """The bytes of `name8` ('SEED    BAS'), by walking its FAT chain."""
    fat = bytearray(img[g["rsv"] * g["bps"]:
                        (g["rsv"] + g["spf"]) * g["bps"]])
    for i in range(g["nroot"]):
        e = g["root_sec"] * g["bps"] + i * 32
        if img[e:e + 11] != name8.encode():
            continue
        clus = struct.unpack("<H", img[e + 26:e + 28])[0]
        size = struct.unpack("<I", img[e + 28:e + 32])[0]
        out, csz = bytearray(), g["bps"] * g["spc"]
        seen = set()
        while 2 <= clus < 0xFF0:
            if clus in seen:
                sys.exit("REFUSING: %s's FAT chain loops at cluster %d"
                         % (name8, clus))
            seen.add(clus)
            off = (g["data_sec"] + (clus - 2) * g["spc"]) * g["bps"]
            out += img[off:off + csz]
            clus = FB.fat12_get(fat, clus)
        return bytes(out[:size])
    return None


def write_files(path, files):
    """A fresh image carrying `files` = {'NAME    BAS': bytes}."""
    shutil.copyfile(FB.SRC_DSK, path)
    d = bytearray(open(path, "rb").read())
    g = geom(d)
    csz = g["bps"] * g["spc"]
    fat = bytearray(d[g["rsv"] * g["bps"]:
                      (g["rsv"] + g["spf"]) * g["bps"]])
    slot = 0
    for name8, blob in files.items():
        need = (len(blob) + csz - 1) // csz
        free = [c for c in range(2, 600) if FB.fat12_get(fat, c) == 0][:need]
        if len(free) != need:
            sys.exit("REFUSING: %s needs %d clusters, %d free"
                     % (name8, need, len(free)))
        for i, c in enumerate(free):
            FB.fat12_set(fat, c, 0xFFF if i == need - 1 else free[i + 1])
            off = (g["data_sec"] + (c - 2) * g["spc"]) * g["bps"]
            d[off:off + csz] = blob[i * csz:(i + 1) * csz].ljust(csz, b"\x00")
        ent = (name8.encode() + bytes([0x20]) + b"\x00" * 10 +
               struct.pack("<HHHI", 0x6000, 0x5921, free[0], len(blob)))
        assert len(ent) == 32
        while slot < g["nroot"]:
            e = g["root_sec"] * g["bps"] + slot * 32
            slot += 1
            if d[e] in (0x00, 0xE5):
                d[e:e + 32] = ent
                break
        else:
            sys.exit("REFUSING: root directory full")
    for i in range(g["nf"]):
        d[(g["rsv"] + i * g["spf"]) * g["bps"]:
          (g["rsv"] + i * g["spf"]) * g["bps"] + g["spf"] * g["bps"]] = fat
    if len(d) != os.path.getsize(FB.SRC_DSK):
        sys.exit("REFUSING: the built image changed size")
    open(path, "wb").write(bytes(d))


# --------------------------------------------------------------------------
# tokenised programs: take apart what the machine saved, put new ones together
# --------------------------------------------------------------------------
def split_program(blob):
    """[(lineno, body-with-its-$00), ...] from a SAVEd tokenised program.

    ⚠️ THE TWO WAYS OF FINDING A LINE'S END MUST AGREE. The link pointer is
    authoritative; scanning for $00 is what a generator assumes. If they ever
    disagree the file is not shaped the way the padding generator believes, so
    this refuses rather than silently building something else.
    """
    if not blob or blob[0] != 0xFF:
        sys.exit("REFUSING: the saved file has no $FF tokenised-program header "
                 "-- SAVE wrote ASCII, or nothing was saved")
    p, out = 1, []
    while True:
        link = struct.unpack("<H", blob[p:p + 2])[0]
        if link == 0:
            break
        lineno = struct.unpack("<H", blob[p + 2:p + 4])[0]
        q = blob.index(b"\x00", p + 4)
        if link - TXTTAB + 1 != q + 1:
            sys.exit("REFUSING: line %d's link and its $00 disagree (%d vs %d)"
                     % (lineno, link - TXTTAB + 1, q + 1))
        out.append((lineno, blob[p + 4:q + 1]))
        p = q + 1
    return out


def assemble(items):
    out, addr = bytearray(b"\xFF"), TXTTAB
    for lineno, body in items:
        nxt = addr + 4 + len(body)
        out += struct.pack("<HH", nxt, lineno) + body
        addr = nxt
    return bytes(out + b"\x00\x00")


def marks(cap, tag):
    """Every number printed after `tag`, in screen order."""
    out = []
    for j in range(0, len(cap or ""), 40):
        row = cap[j:j + 40]
        if tag in row:
            tok = row.split(tag, 1)[1].strip().split()
            if tok:
                try:
                    out.append(int(tok[0]))
                except ValueError:
                    pass
    return out


# --------------------------------------------------------------------------
def seed(machine, reset, tmpd, tag):
    """PHASE A -- let the MACHINE tokenise the lines, then read them back."""
    dsk = os.path.join(tmpd, "seed_%s.dsk" % tag)
    shutil.copyfile(FB.SRC_DSK, dsk)
    omsx_repl.run_cases(machine, [("direct", SEED_LINES + ['SAVE"SEED.BAS"'])],
                        batch=False, reset=reset, boot=BOOT, step=3.0,
                        cap_gap=CAP_GAP, diska=dsk, capture="screen")
    img = open(dsk, "rb").read()
    blob = read_file(img, geom(bytearray(img)), "SEED    BAS")
    if blob is None:
        sys.exit("REFUSING: %s never wrote SEED.BAS -- nothing was tokenised, "
                 "so every program below would be my guess at MSX tokens, "
                 "which is exactly what §6.2b forbids" % machine)
    items = split_program(blob)
    got = [n for n, _ in items]
    if got != [10, 20, 30, 40, 50]:
        sys.exit("REFUSING: SEED.BAS holds lines %r, not [10, 20, 30, 40, 50] -- "
                 "the screen editor rejected a line and the padding would not "
                 "be what it looks like" % got)
    return dict(items), len(blob)


def build(seeded, tmpd, tag):
    """PHASE B -- two programs differing ONLY in how much REM padding they hold."""
    mark, rem = seeded[10], seeded[20]
    per = 4 + len(rem)                       # link + lineno + body, per REM line
    out, sizes = {}, {}
    for name, target, idline in (("S", SMALL_B, seeded[30]),
                                 ("M", MID_B, seeded[40]),
                                 ("L", LARGE_B, seeded[50])):
        n = max(1, target // per)
        items = ([(10, mark)] +
                 [(20 + 10 * i, rem) for i in range(n)] +
                 [(20 + 10 * n, idline)])
        blob = assemble(items)
        out["%-8s%s" % (name, "BAS")] = blob
        sizes[name] = len(blob)
    dsk = os.path.join(tmpd, "run_%s.dsk" % tag)
    write_files(dsk, out)
    return dsk, sizes, per


def measure(machine, reset, dsk):
    """PHASE C -- four cases; the reading is TIME AS PRINTED BY THE LOADED CODE."""
    cases = [
        ("stored", ["TIME=0", "FOR I=1 TO %d:NEXT" % DELAY,
                    "PRINT CHR$(64)+CHR$(75);TIME"]),
        ("stored", ["TIME=0", 'LOAD"S.BAS",R']),
        ("stored", ["TIME=0", 'LOAD"M.BAS",R']),
        ("stored", ["TIME=0", 'LOAD"L.BAS",R']),
        ("stored", ["TIME=0", "FOR I=1 TO %d:NEXT" % DELAY, 'LOAD"S.BAS",R']),
    ]
    for _, lines in cases:
        for ln in lines:
            if len(ln) > 34:
                sys.exit("REFUSING: stored line %r is %d chars" % (ln, len(ln)))
    return omsx_repl.run_cases(machine, cases, batch=True, reset=reset,
                               boot=BOOT, step=STEP, cap_gap=CAP_GAP,
                               diska=dsk, capture="screen")


def main():
    tmpd = tempfile.mkdtemp(prefix="loadrun_")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    rc, rows, seeds = 0, [], {}
    for tag, machine, reset, hz in SIDES:
        if only and only != tag:
            continue
        print("\n=== %s (%s, %d Hz) ===" % (tag, machine, hz), flush=True)
        seeded, nseed = seed(machine, reset, tmpd, tag)
        seeds[tag] = seeded
        print("  SEED.BAS: %d B, lines %s; REM body = %s"
              % (nseed, sorted(seeded), seeded[20].hex()))
        # 🔬 FREE CHECK ON A FILE STILL IN THE TREE: loadtime_probe builds its
        # REM lines by hand. This is the first time a machine-produced one has
        # been available to compare against.
        hand = bytes([0x8F]) + b"X" * 14 + b"\x00"
        print("  vs loadtime_probe's hand-built REM line: %s"
              % ("IDENTICAL" if hand == seeded[20] else
                 "DIFFERS (machine %d B, hand %d B) -- the machine's is used"
                 % (len(seeded[20]), len(hand))))

        dsk, sizes, per = build(seeded, tmpd, tag)
        print("  built %s (%d B per REM line); spread %d B"
              % (", ".join("%s.BAS %d B" % (n, sizes[n])
                           for n in ("S", "M", "L")),
                 per, sizes["L"] - sizes["S"]))
        caps = measure(machine, reset, dsk)

        # --- the readings, and every control that could void them ------------
        vals, ids = [], []
        for i, cap in enumerate(caps):
            k, s = marks(cap or "", MARK), marks(cap or "", IDMARK)
            if not k:
                for j in range(0, len(cap or ""), 40):
                    if (cap or "")[j:j + 40].strip():
                        print("   | %s" % cap[j:j + 40].rstrip())
                sys.exit("REFUSING: case %d printed no %s witness -- it did not "
                         "run, so there is no reading to report" % (i, MARK))
            vals.append(k[0])
            ids.append(s[0] if s else None)
        dly, s_j, m_j, l_j, dly_s = vals
        print("\n| case | what | jiffies | %s |" % IDMARK)
        print("|---|---|---|---|")
        for nm, v, w in (("dly", "FOR loop only, no LOAD", 0),
                         ("S", "LOAD small", 1), ("M", "LOAD mid", 2),
                         ("L", "LOAD large", 3),
                         ("dly+S", "FOR loop THEN LOAD small", 4)):
            print("| %s | %s | %d | %s |" % (nm, v, vals[w], ids[w]))

        ok = True
        if ids[1:5] != [1, 2, 3, 1]:
            print("🔴 CONTROL FAILED: the identity witnesses are %r, expected "
                  "[None, 1, 2, 3, 1] -- a failed open left the previous program "
                  "resident and the difference is noise" % (ids,))
            ok = False
        if l_j <= s_j:
            print("🔴 CONTROL FAILED: the large load (%d) did not exceed the "
                  "small one (%d) -- nothing was loaded" % (l_j, s_j))
            ok = False
        want, tol = dly + s_j, max(3.0, 0.10 * (dly + s_j))
        print("\nTIME-SURVIVES-LOAD control: dly + S = %d, measured dly+S = %d "
              "(tolerance %.1f) -- %s"
              % (want, dly_s, tol,
                 "COMPOSES" if abs(dly_s - want) <= tol else "🔴 DOES NOT"))
        if abs(dly_s - want) > tol:
            print("🔴 so TIME does not survive the LOAD the way this method "
                  "assumes, and no per-byte figure is reported for %s." % tag)
            ok = False
        if not ok:
            rc = 1
            continue
        db = sizes["L"] - sizes["S"]
        pb = (l_j - s_j) / db
        ms = pb * 1000.0 / hz
        # 🔬 LINEARITY, BECAUSE A TWO-POINT DIFFERENTIAL ASSUMES THE SHAPE IT
        # CANNOT SEE. If walking the FAT chain re-reads a FAT sector per
        # cluster, the cost is superlinear -- and a slope taken from the two
        # endpoints would understate big loads and overstate small ones while
        # looking perfectly clean. The mid-size program is the third point that
        # makes the assumption checkable instead of implicit.
        want_m = s_j + pb * (sizes["M"] - sizes["S"])
        lin, ltol = abs(m_j - want_m), max(2.0, 0.08 * max(1.0, want_m))
        print("linearity: M predicted %.1f from the S-L slope, measured %d "
              "(off by %.1f, tolerance %.1f) -- %s"
              % (want_m, m_j, lin, ltol,
                 "LINEAR" if lin <= ltol else
                 "🔴 NOT LINEAR, so the figure below is a CHORD, not a slope"))
        print("🟢 per byte: (%d - %d) jiffies / %d B = %.5f jiffies = "
              "%.4f ms/byte" % (l_j, s_j, db, pb, ms))
        rows.append((tag, hz, s_j, l_j, db, ms))

    if len(rows) == 2:
        print("\n=== THE ANSWER STEP 9 WAS WAITING FOR ===")
        print("\n| machine | small | large | spread | ms/byte |")
        print("|---|---|---|---|---|")
        for tag, hz, s_j, l_j, db, ms in rows:
            print("| %s | %d | %d | %d B | **%.4f** |" % (tag, s_j, l_j, db, ms))
        ours = [r for r in rows if r[0] == "zb"][0][5]
        XS = 0.156                      # D-XSLOTPRICE, main -> disk
        print("\nOne inter-slot crossing per byte costs %.3f ms (D-XSLOTPRICE)."
              % XS)
        print("Our tokenised LOAD costs %.4f ms/byte, so a per-byte crossing "
              "would make it %.4f ms/byte -- **%.2fx** our current cost."
              % (ours, ours + XS, (ours + XS) / ours if ours else 0))
    if len(seeds) == 2 and seeds["cf3300"] != seeds["zb"]:
        print("\n🔴 THE TWO MACHINES TOKENISE THESE LINES DIFFERENTLY:")
        for n in sorted(seeds["cf3300"]):
            a, b = seeds["cf3300"][n], seeds["zb"].get(n)
            if a != b:
                print("   line %d: cf3300 %s / zb %s"
                      % (n, a.hex(), b.hex() if b else "(absent)"))
    elif len(seeds) == 2:
        print("\n🟢 Both machines tokenised all %d seed lines IDENTICALLY."
              % len(SEED_LINES))
    shutil.rmtree(tmpd, ignore_errors=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
