#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATBUF: does the CF-3300 hold file DATA and FAT METADATA in RAM at the same
time, or in one buffer it re-reads?  Observed as BYTES IN RAM, not guessed.

Joost asked it on 2026-09-18, against the eviction spec's §0.1 ruling that there
must be ONE FAT12 engine: *"unless bdos actually uses the same buf as disk basic
-- on the reference"*.  zerobas uses TWO buffers -- FSECTOR_BUF ($E5C0) for file
data and FWBUF ($E7C0) for FAT/dir metadata -- a choreography invented HERE so a
record survives a chain walk (basic/field.asm header, D-FIELDFIX).  Nothing has
ever checked it against the reference.  If the reference uses ONE, there is no
buffer parameter to design and our split is the thing to reconsider.

🔴 NO DISASSEMBLY.  No instruction of the reference is read or recorded.  This
reads RAM -- data the machine wrote -- the line D-CFARCH and the hook census
already work on.

=== WHY THIS IS NOT A DIFF ===

The FIRST cut of this probe diffed RAM against an idle control and REFUSED,
correctly, with `FILES` disturbing only 27 bytes.  The reason is worth keeping:
**an MSX with a disk reads that disk during BOOT** (the boot sector, then the
root directory looking for AUTOEXEC.BAS), so the sector buffer ALREADY holds
directory content in every case including the control.  A later `FILES` re-reads
the same sector over itself and changes almost nothing.  A diff against an idle
control cannot see a buffer whose content the control already has.

So this cut uses GROUND TRUTH instead.  The probe builds its own disk, so it
knows exactly what every sector contains, and then searches RAM for those exact
bytes.  Residency is read directly rather than inferred from change.

=== METHOD ===

  1. Copy disk/test720.dsk and inject RND.BIN -- 1536 B of deterministic
     pseudo-random bytes, which is 2 clusters of 1024 B, so reading past offset
     1024 MUST walk the cluster chain.  Its content is distinctive, unlike
     TEST.BIN, whose first 64 bytes are all one value and would match anywhere.
  2. Boot the CF-3300 with it and run one case.
  3. Dump $8000-$FFFF and search for four known 64-byte windows:
        W_dat0   RND.BIN at file offset 0      (first cluster)
        W_dat1   RND.BIN at file offset 1024   (second cluster)
        W_fat    the FAT sector
        W_dir    the root-directory sector
  4. Cases:
        dat   read 16 B    -- one data sector, no walk
        wlk   read 1120 B  -- past the cluster, so the FAT is read WITH file
                              data live, which is exactly the case our two-buffer
                              choreography exists to survive

=== THE DISCRIMINATION ===

After `wlk`, is W_fat resident AT A DIFFERENT ADDRESS alongside W_dat1?

  both resident   -> the reference keeps metadata separate from file data, as
                     zerobas does, and §0.1's buffer parameter has a counterpart
  only W_dat1     -> one buffer, re-read: the FAT content was overwritten by the
                     data sector that followed it, which a separate metadata
                     buffer would have preserved

⚠️ THE ASYMMETRY IS REAL AND IS NOT HIDDEN.  "Both resident" proves two regions.
"Only W_dat1" is consistent with one buffer AND with a metadata buffer that
something later overwrote -- nothing else reads the FAT after the walk, which is
why the second reading is unlikely, but it is not excluded by this measurement.
Reported as evidence about REGION COUNT, never about the engine.

⚠️ IT REFUSES RATHER THAN PRINTING A PLAUSIBLE TABLE
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]:
  * POSITIVE CONTROL -- W_dat0 must be resident after `dat`.  A file read whose
    bytes are nowhere in RAM did not happen, and every other row would then
    agree for the wrong reason.
  * NEGATIVE CONTROL -- a 64-byte window that is NOT on the disk must be found
    NOWHERE.  Without it, a matcher that matches everything reads as a discovery.
  * Every search window must carry >= 16 distinct byte values, or it is too
    degenerate to locate anything and the run stops.
"""
import os, shutil, struct, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MACHINE = "National_CF-3300"
OPENMSX = "/opt/homebrew/bin/openmsx"
SRC_DSK = os.path.join(REPO, "disk", "test720.dsk")

LO, HI = 0x8000, 0xFFFF
WIN = 64                      # bytes per search window
MIN_DISTINCT = 16             # a window flatter than this cannot locate anything
FILESZ = 1536                 # 2 clusters of 1024 -> the walk is forced
FILL_SLACK = 6                # clusters left unallocated after the fillers
T_BOOT, T_TYPE, T_RUN = 14.0, 1.6, 8.0

# 🔴 THE TYPING IS NOT THIS PROBE'S JOB. Five separate injection defects were
# hit before this was accepted: Tcl substituting `$` out of `A$=INPUT$(...)`,
# the CF-3300's boot date prompt eating every line, a SCREEN-0 scraper reading
# SCREEN 1 as garbage, dropped characters from injecting faster than the key
# scan, and a lost CR merging two lines into a syntax error. probes/lib has a
# hardened injector for exactly this -- it writes at GETPNT, defers while the
# buffer is non-drained, and VERIFIES DELIVERY (D-LATCH, D-LATCH2, D-DELIVER).
# Reinventing it produced five plausible-looking wrong answers in a row.
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                          # noqa: E402

# CF-3300 settings, copied from probes/basic/basic_probe_lptverb.py:90. The
# leading "" answers the boot date prompt and SCREEN 0 puts it in the 40-column
# mode the scrape reads; with batch=False the reset must live INSIDE each case.
BOOT, STEP = 14.0, 4.5
RESET = ["", "SCREEN 0", "NEW"]

# 🔑 THE MARKER IS BUILT AT RUN TIME so it cannot match the screen ECHO of the
# line that prints it [[a-probes-fence-is-also-in-the-source-it-echoes]], and it
# carries LOC(1) so the two cases are distinguishable by how far each actually
# read -- a case that silently did nothing cannot borrow the other's witness.
MARK_SRC = "CHR$(64)+CHR$(75)"
MARK = "@K"

# Direct mode, every line <= 39 chars. The file is left OPEN: CLOSE could flush
# or re-read and would disturb the very buffers being measured.
CASES = {
    "dat": RESET + ['OPEN"RND.BIN"FOR INPUT AS#1',
                    'A$=INPUT$(16,#1)',
                    'PRINT %s;LOC(1)' % MARK_SRC],
    "wlk": RESET + ['OPEN"RND.BIN"FOR INPUT AS#1',
                    'FOR I=1 TO 70:A$=INPUT$(16,#1):NEXT',
                    'PRINT %s;LOC(1)' % MARK_SRC],
}
ORDER = ["dat", "wlk"]


def prng(n, seed=0x2691):
    """Deterministic bytes, so the expectation is regenerable, not recorded."""
    out, x = bytearray(), seed
    while len(out) < n:
        x = (x * 1103515245 + 12345) & 0xFFFFFFFF
        out.append((x >> 16) & 0xFF)
    return bytes(out)


def fat12_get(fat, n):
    o = n * 3 // 2
    return (fat[o] | ((fat[o + 1] & 0x0F) << 8)) if n % 2 == 0 \
        else ((fat[o] >> 4) | (fat[o + 1] << 4))


def fat12_set(fat, n, v):
    o = n * 3 // 2
    if n % 2 == 0:
        fat[o] = v & 0xFF
        fat[o + 1] = (fat[o + 1] & 0xF0) | ((v >> 8) & 0x0F)
    else:
        fat[o] = (fat[o] & 0x0F) | ((v << 4) & 0xF0)
        fat[o + 1] = (v >> 4) & 0xFF


def build_disk(path, payload):
    """Inject RND.BIN into a copy of the test disk. Returns the geometry."""
    shutil.copyfile(SRC_DSK, path)
    d = bytearray(open(path, "rb").read())
    bps = struct.unpack("<H", d[11:13])[0]
    spc, rsv = d[13], struct.unpack("<H", d[14:16])[0]
    nf = d[16]
    nroot = struct.unpack("<H", d[17:19])[0]
    spf = struct.unpack("<H", d[22:24])[0]
    total = struct.unpack("<H", d[19:21])[0]
    csz = bps * spc
    root_sec = rsv + nf * spf
    root_secs = (nroot * 32 + bps - 1) // bps
    data_sec = root_sec + root_secs
    maxclus = (total - data_sec) // spc + 2

    fat = bytearray(d[rsv * bps: rsv * bps + spf * bps])
    # 🔑 CONFINED TO THE FIRST FAT SECTOR'S ENTRIES. A 12-bit entry for cluster n
    # lives at byte n*3/2, so sector 0 of the FAT covers n < bps*2/3. Every
    # cluster allocated here -- fillers AND the subject -- comes from that range:
    # the sector searched for is the one the walk must actually READ, and filling
    # it densely is what gives it the entropy to be found by. A mostly-empty
    # FAT12 sector carried SEVEN distinct byte values and matched cleared RAM.
    fat_sec0_max = min(maxclus, bps * 2 // 3)
    avail = [c for c in range(2, fat_sec0_max) if fat12_get(fat, c) == 0]

    rng, order = 0x51ED, list(avail)
    for i in range(len(order) - 1, 0, -1):
        rng = (rng * 1103515245 + 12345) & 0xFFFFFFFF
        j = (rng >> 16) % (i + 1)
        order[i], order[j] = order[j], order[i]

    def take(n):
        if len(order) < n:
            sys.exit("REFUSING: disk has %d free clusters left, need %d"
                     % (len(order), n))
        return [order.pop(0) for _ in range(n)]

    def place(name, body):
        chain = take((len(body) + csz - 1) // csz)
        for k, c in enumerate(chain):
            fat12_set(fat, c, 0xFFF if k == len(chain) - 1 else chain[k + 1])
            off = (data_sec + (c - 2) * spc) * bps
            d[off:off + csz] = body[k * csz:(k + 1) * csz].ljust(csz, b"\x00")
        return chain

    need = (len(payload) + csz - 1) // csz
    k = 0
    while len(order) > need + FILL_SLACK:    # dense entropy for the FAT sector
        place("FILL%d" % k, prng(csz * 3, seed=0x1000 + k))
        k += 1
    chain = place("RND", payload)            # the subject, on scattered clusters

    for i in range(nf):                      # both FAT copies, as a real write would
        d[(rsv + i * spf) * bps:(rsv + i * spf) * bps + spf * bps] = fat

    ro = root_sec * bps
    # ⚠️ EXACTLY 32 BYTES. The first cut emitted THIRTY (it omitted the time/date
    # pair), and assigning 30 bytes into a 32-byte slice of a bytearray SHRINKS
    # IT -- every sector after the root directory shifted down by 2 and the
    # payload landed at byte 14334 instead of 14336.
    ent = (b"RND     BIN" + bytes([0x20]) + b"\x00" * 10 +
           struct.pack("<HHHI", 0x6000, 0x5921, chain[0], len(payload)))
    assert len(ent) == 32, "directory entry must be 32 bytes, got %d" % len(ent)
    for i in range(nroot):
        e = ro + i * 32
        if d[e] in (0x00, 0xE5):
            d[e:e + 32] = ent
            break
    else:
        sys.exit("REFUSING: root directory is full")
    if len(d) != len(open(SRC_DSK, "rb").read()):
        sys.exit("REFUSING: the built image changed size -- a slice assignment "
                 "was not the width it replaced, so every sector after it moved")
    open(path, "wb").write(bytes(d))
    return dict(bps=bps, spc=spc, rsv=rsv, data_sec=data_sec,
                root_sec=root_sec, first=chain[0], chain=chain, fillers=k)


def window(img, sector, bps, label):
    """A 64-byte window from a sector, refused if too flat to locate anything."""
    b = img[sector * bps: sector * bps + bps]
    best, bestn = None, -1
    for o in range(0, bps - WIN, 16):
        n = len(set(b[o:o + WIN]))
        if n > bestn:
            best, bestn = b[o:o + WIN], n
    if bestn < MIN_DISTINCT:
        sys.exit("REFUSING: the %s window carries only %d distinct byte values -- "
                 "too flat to locate in RAM, so an absence would mean nothing"
                 % (label, bestn))
    return bytes(best)


def drive(dsk, capture):
    """One boot per case through the hardened harness. Returns a capture list."""
    cases = [("direct", CASES[k]) for k in ORDER]
    for k in ORDER:
        for ln in CASES[k]:
            if len(ln) > 39:
                sys.exit("REFUSING: case %s line %r is %d chars; direct mode "
                         "takes at most 39" % (k, ln, len(ln)))
    return omsx_repl.run_cases(MACHINE, cases, batch=False, reset=(),
                               boot=BOOT, step=STEP, diska=dsk, capture=capture)


def find_all(hay, needle):
    out, i = [], hay.find(needle)
    while i >= 0:
        out.append(LO + i)
        i = hay.find(needle, i + 1)
    return out


def main():
    if not os.path.exists(SRC_DSK):
        sys.exit("REFUSING: %s is missing" % SRC_DSK)
    tmpd = tempfile.mkdtemp(prefix="fatbuf_disk_")
    dsk = os.path.join(tmpd, "rnd.dsk")
    payload = prng(FILESZ)
    g = build_disk(dsk, payload)
    img = open(dsk, "rb").read()
    bps, spc = g["bps"], g["spc"]
    def sec_of(clus):
        return g["data_sec"] + (clus - 2) * spc

    # ⚠️ CLUSTER 2 IS NOT AT s0 + spc. The clusters are deliberately SCATTERED,
    # so the second cluster's sector must come from the CHAIN. Assuming
    # contiguity here pointed the second window at an unrelated empty sector,
    # which the builder's self-check caught as "1 distinct byte value".
    s0 = sec_of(g["chain"][0])
    s1 = sec_of(g["chain"][1])
    print("disk built: RND.BIN %d B, chain %s -> sectors %d,%d; %d B clusters; "
          "%d filler files" % (FILESZ, g["chain"], s0, s1, bps * spc, g["fillers"]))

    # 🔴 ONE WINDOW PER SECTOR WAS TOO NARROW. `LOC(1)` reports 256 and 768, so
    # the channel buffers in 256-BYTE units while a sector is 512 -- a 64-byte
    # window picked from an arbitrary offset in the sector lands in the half that
    # is never buffered about half the time, and reads as "not resident". So the
    # whole payload and the whole FAT sector are scanned in 64-byte steps and the
    # probe reports WHICH OFFSETS are resident. That answers a strictly larger
    # question than the original windows did, with no extra emulator time.
    def grid(buf, base_label, required=True):
        out = {}
        for k in range(0, len(buf) - WIN + 1, WIN):
            w = bytes(buf[k:k + WIN])
            if len(set(w)) >= MIN_DISTINCT:
                out["%s+%d" % (base_label, k)] = w
        if not out and required:
            sys.exit("REFUSING: every %s window is too flat to locate in RAM, so "
                     "an absence would mean nothing" % base_label)
        return out

    W_file = grid(payload, "file")
    W_fat = grid(img[g["rsv"] * bps:(g["rsv"] + 1) * bps], "fat")
    # ⚠️ THE DIRECTORY IS INFORMATIONAL, NOT PART OF THE DISCRIMINATION, and a
    # root directory is a few ASCII entries followed by zeros -- often with NO
    # 64-byte window distinctive enough to locate. That is a property of the
    # data, not a failure, so it is allowed to be empty. Only the file and FAT
    # grids gate the run.
    W_dir = grid(img[g["root_sec"] * bps:(g["root_sec"] + 1) * bps], "dir",
                 required=False)
    W = {}
    W.update(W_file)
    W.update(W_fat)
    W.update(W_dir)
    print("windows: %d file, %d fat, %d dir (64 B each, >= %d distinct values)"
          % (len(W_file), len(W_fat), len(W_dir), MIN_DISTINCT))

    W_absent = prng(WIN, seed=0x7F41)                     # NEGATIVE CONTROL
    if W_absent in img:
        sys.exit("REFUSING: the negative-control window occurs on the disk")

    # --- drive twice: once for the WITNESS, once for the BYTES ---------------
    # The harness returns ONE capture spec per batch, so the screen (which proves
    # each case ran) and the RAM (which answers the question) are two runs of the
    # same deterministic cases rather than one run reporting both.
    print("  driving for the witness (screen) ...", flush=True)
    scr_caps = drive(dsk, "screen")
    print("  driving for the bytes (mem_abs $%04X..$%04X) ..." % (LO, HI), flush=True)
    mem_caps = drive(dsk, ("mem_abs", [(LO, HI - LO + 1)]))

    marks, snaps = {}, {}
    for i, name in enumerate(ORDER):
        txt = scr_caps[i] or ""
        hit = [w for w in txt.split() if MARK in w]
        # LOC(1) follows the marker on the same printed line
        line = ""
        for ln in [txt[j:j + 40] for j in range(0, len(txt), 40)]:
            if MARK in ln:
                line = ln.strip()
                break
        marks[name] = line or (hit[0] if hit else None)
        print("      %-4s witness: %s" % (name, marks[name] or "<NONE ON SCREEN>"))
        if mem_caps[i] is None:
            sys.exit("REFUSING: case %s returned no memory capture" % name)
        snaps[name] = bytes.fromhex(mem_caps[i])
        if len(snaps[name]) != HI - LO + 1:
            sys.exit("REFUSING: case %s captured %d bytes, expected %d"
                     % (name, len(snaps[name]), HI - LO + 1))

    # --- THE CASE-RAN CONTROL, before anything is read out of RAM -------------
    for name in ORDER:
        if marks[name] is None:
            print("\n--- %s screen ---" % name)
            t = scr_caps[ORDER.index(name)] or ""
            for j in range(0, len(t), 40):
                if t[j:j + 40].strip():
                    print("  | %s" % t[j:j + 40].rstrip())
            sys.exit("REFUSING: case %s printed no %r witness. Its lines did not "
                     "run -- so its RAM is the state of a machine that did nothing, "
                     "and a buffer count read out of it would be noise."
                     % (name, MARK))
    if marks["dat"] == marks["wlk"]:
        sys.exit("REFUSING: both cases report the SAME witness (%r), so the walk "
                 "case read no further than the plain one -- the chain was never "
                 "walked and the FAT row would mean nothing." % marks["dat"])

    print()
    hits = {}
    for name in ORDER:
        ram = snaps[name]
        hits[name] = {k: find_all(ram, w) for k, w in W.items()}
        hits[name]["NEG"] = find_all(ram, W_absent)

    def live(name, pref):
        return {k: v for k, v in hits[name].items()
                if k.startswith(pref) and v}

    print("| case | witness | file offsets resident | FAT windows | DIR windows |")
    print("|---|---|---|---|---|")
    for name in ORDER:
        f, ft, dr = live(name, "file"), live(name, "fat"), live(name, "dir")
        offs = sorted(int(k.split("+")[1]) for k in f)
        rng = ("%d..%d (%d win)" % (offs[0], offs[-1] + WIN, len(offs))) if offs else "—"
        addrs = sorted({a for v in f.values() for a in v})
        print("| %s | %s | %s%s | %d at %s | %d at %s |"
              % (name, marks[name], rng,
                 (" @ " + ", ".join("$%04X" % a for a in addrs[:4])) if addrs else "",
                 len(ft), ", ".join("$%04X" % a for v in ft.values() for a in v)[:40] or "—",
                 len(dr), ", ".join("$%04X" % a for v in dr.values() for a in v)[:40] or "—"))

    for name in ORDER:
        if hits[name]["NEG"]:
            sys.exit("REFUSING: the negative-control window was FOUND in %s at %s. "
                     "The matcher matches bytes that are not on the disk, so every "
                     "hit above is worthless." % (name, hits[name]["NEG"]))
    if not live("dat", "file"):
        sys.exit("REFUSING: after reading 16 bytes of RND.BIN, NO part of it is in "
                 "$%04X-$%04X. The read did not happen, and every other row would "
                 "agree for the wrong reason." % (LO, HI))

    # --- the discrimination ---------------------------------------------------
    f_w = live("wlk", "file")
    t_w = live("wlk", "fat")
    f_addr = {a for v in f_w.values() for a in v}
    t_addr = {a for v in t_w.values() for a in v}
    print()
    print("=" * 72)
    print("THE QUESTION: after a chain walk, is FAT content resident in RAM")
    print("ALONGSIDE the file data -- at a DIFFERENT address?")
    print("zerobas says yes: FSECTOR_BUF $E5C0 holds the record, FWBUF $E7C0 the")
    print("metadata, deliberately, so the record survives the walk.")
    print()
    if f_w and t_w and not (f_addr & t_addr):
        print("ANSWER: TWO REGIONS, BOTH LIVE AFTER THE WALK.")
        print("  file data at %s" % ", ".join("$%04X" % a for a in sorted(f_addr)))
        print("  FAT  data at %s" % ", ".join("$%04X" % a for a in sorted(t_addr)))
        print("-> the reference holds metadata separately from file data, as")
        print("   zerobas does. spec §0.1's buffer parameter has a counterpart.")
    elif f_w and not t_w:
        print("ANSWER: ONE REGION.")
        print("  file data at %s ; NO FAT content anywhere in RAM"
              % ", ".join("$%04X" % a for a in sorted(f_addr)))
        print("-> the FAT sector the walk must have read was overwritten by the")
        print("   data that followed it. A separate metadata buffer would have")
        print("   preserved it, so zerobas' FSECTOR_BUF/FWBUF split is OUR design.")
    elif t_w and not f_w:
        print("ANSWER: UNDETERMINED -- FAT content is resident but NO part of the")
        print("file is, after a walk that read %s. The channel's data buffer is"
              % marks["wlk"])
        print("somewhere this window does not cover, or is not held as raw bytes.")
    else:
        print("ANSWER: UNDETERMINED -- neither file data nor FAT content is")
        print("resident after the walk. Re-check the case before reading anything")
        print("into either row.")
    print("=" * 72)
    print()
    # --- coalesce the hits into REGIONS, which is what the answer is about ----
    def regions(addrs):
        out = []
        for a in sorted(addrs):
            if out and a == out[-1][1]:
                out[-1][1] = a + WIN
            else:
                out.append([a, a + WIN])
        return out

    print("resident regions after the WALK (contiguous runs of matched windows):")
    for lbl, ad in (("file data", f_addr), ("FAT sector", t_addr)):
        for a, b in regions(ad):
            print("  %-10s $%04X .. $%04X  (%d B)" % (lbl, a, b - 1, b - a))
    print()
    print("⚠️  ASYMMETRY, STATED: 'both resident' PROVES two regions. 'only file")
    print("    data' is consistent with one buffer AND with a metadata buffer that")
    print("    something later overwrote. Nothing reads the FAT after the walk, so")
    print("    the second reading is unlikely -- but it is not excluded here.")
    print("⚠️  And this reads WHICH BYTES ARE RESIDENT, not which routine put them")
    print("    there. It is evidence about REGION COUNT, never about the engine.")
    shutil.rmtree(tmpd, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
