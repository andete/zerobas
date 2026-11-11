"""Host test for D-LOADDIRECT (2026-11-07), which replaced D-LOADRUN: LOAD reads
the file IN PLACE, as the CF-3300 does, then walks it there (disk/runtime.asm
hdl_direct, disk/kernel.asm hdl_walk; hk_dpload hands over after the marker).

The CF-3300's read commands land each full sector at its final address -- HL steps
$200 a command -- and only the first (the $FF marker's) and the last partial sector
pass through a buffer (scratchpad/fdccmd_cf1107.out). Before this, zerobas parsed
the file a byte at a time out of the sector buffer (hdl_line / hdl_body, with
D-LOADRUN's hdl_run and D-LOADBASE's hdl_scan), which the walk replaces.

The walk must give the STREAM'S answer. `stream()` below is that parser's rules,
transcribed from the removed code: the link-delta body length, the first line (and
any $FFFF delta) scanned to its $00 over the constants' payloads, every EOF a loaded
program with CLPTR where the last store left it -- at the line start for an EOF in
the link (the link-low byte was never stored) or for the $0000 link, else past
every byte read. Each row compares status, CLPTR and the stored bytes with it:
  * a 3.7 KB (8-sector) program whose bodies (1..250 B) straddle its sector edges;
  * the same file ENDING EARLY (a directory size cut inside a body, on and around a
    sector edge, inside a header);
  * corrupt links: a $FFFF delta (scanned), a delta under 4 (a 64 KB line: EOF),
    a delta far past the file's end;
  * a sector read that FAILS mid-file: an EOF at that sector, as the stream's was;
  * TXTMAX around the file's end -- the one place the answer CHANGES: a file that
    ends past TXTMAX is out of memory BEFORE anything is read (the stream loaded
    up to TXTMAX and then said so; both leave main an empty program, dpl_oom).
D-LOADFAT's rows stay: a chain across the FAT-sector straddle loads exactly, with
one FAT read per FAT sector the chain enters. And the design is witnessed directly:
every full data sector's read lands at its final address, $200 apart.
Fragmented chains (one and three breaks) load exactly, each full sector still at its
own final address. (D-LOADRUNS read runs of consecutive clusters in one DSKIO, as the
CF-3300 does; measured slower here and removed -- disk/runtime.asm hd_full.)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_hk_dpbload as D  # noqa: E402  (the FAT12 model and the disk build)

TXTTAB_CELL = 0xF676
BODIES = [1, 7, 250, 33, 128, 200, 5, 90, 250, 250, 17, 64, 3, 180]
PAYLOAD = {0x0B: 2, 0x0C: 2, 0x0D: 2, 0x0E: 2, 0x0F: 1, 0x1C: 2, 0x1D: 4, 0x1F: 8}


def program(base=0x8001, nlines=34):
    """A tokenised image (after the $FF marker) linked from `base`: no $00 inside a
    body (the first line is SCANNED for its $00), then the $0000 end link."""
    out, addr = bytearray(), base
    for k in range(nlines):
        body = bytes((0x41 + (k + i) % 26) for i in range(BODIES[k % len(BODIES)]))
        rec = (10 * (k + 1)).to_bytes(2, "little") + body + b"\x00"
        nxt = addr + 2 + len(rec)
        out += nxt.to_bytes(2, "little") + rec
        addr = nxt
    return bytes(out) + b"\x00\x00"


def stream(data, at):
    """The removed byte parser's answer for `data` (after the marker) stored from
    `at`, when nothing reaches TXTMAX: (status, CLPTR, the bytes stored)."""
    n, pos, clink = len(data), 0, 0
    while True:
        if pos + 2 > n:
            return 0, at + pos, data[:pos]
        link = data[pos] | data[pos + 1] << 8
        if link == 0:
            return 0, at + pos, data[:pos]
        de = 0xFFFF if clink == 0 else (link - clink - 4) & 0xFFFF
        clink = link
        if pos + 4 > n:
            return 0, at + n, data
        pos += 4
        if de == 0xFFFF:
            e = 0
            while True:
                if pos >= n:
                    return 0, at + n, data
                b = data[pos]
                pos += 1
                if e:
                    e -= 1
                elif b == 0:
                    break
                else:
                    e = PAYLOAD.get(b, 0)
        else:
            if pos + de > n:
                return 0, at + n, data
            pos += de


def machine(data, size, at, fail=()):
    d = D.Disk()
    d.add_file("P.BAS", data, size)
    m = D.machine(d)
    s = m.sym
    d.fail_read.update(fail)
    m.poke(s["DISK_FCB_NAME"], D.name83("P.BAS"))
    m.poke(s["FOPEN_SEL"], s["FOPEN_SEL_LOAD"])
    m.poke_w(TXTTAB_CELL, at)
    return m, d


def load(data, size, at, fail=()):
    m, _ = machine(data, size, at, fail)
    s = m.sym
    m.call("hk_dpload")
    clptr = m.mem[s["CLPTR"]] | m.mem[s["CLPTR"] + 1] << 8
    return m.mem[s["DISKOP_STATUS"]], clptr, bytes(m.mem[at:max(at, clptr)])


def corrupt(delta):
    """program() with line 2's link set to line 1's + `delta`."""
    p = bytearray(program())
    l1 = p[0] | p[1] << 8
    off2 = l1 - 0x8001
    v = (l1 + delta) & 0xFFFF
    p[off2:off2 + 2] = v.to_bytes(2, "little")
    return bytes(p)


def run():
    D.build()
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    img = b"\xff" + program()
    n = len(img)
    sym = D.machine(D.Disk()).sym
    txtmax = sym["TXTMAX"]

    rows = [("whole file", img, None, 0x8001, ())]
    for cut in (1, 2, 3, 5, 200, 511, 512, 513, 1023, 1024, 1025, 1536, 2047, 2048,
                2600, 3000, n - 3, n - 1):
        if cut < n:
            rows.append((f"file ends at byte {cut}", img, cut, 0x8001, ()))
    for delta, what in ((3, "a $FFFF delta: scanned"), (2, "a delta under 4: a 64 KB line"),
                        (1, "a delta of 1"), (0x3000, "a delta far past the end")):
        rows.append((f"line 2's link {what}", b"\xff" + corrupt(delta), None, 0x8001, ()))
    rows.append(("from $C001 (D-LOADBASE: the first line scanned)", b"\xff" + program(0xC001),
                 None, 0x8001, ()))
    # a failure on the file's 3rd data sector (the file starts at cluster 2)
    rows.append(("a read failing on the 3rd sector", img, None, 0x8001, (D.FIRSTDATA + 2,)))

    for label, data, size, at, fail in rows:
        got = load(data, size, at, fail)
        body = data[1:size] if size else data[1:]
        if fail:
            body = body[:2 * D.SECSIZE - 1]
        want = stream(body, at)
        ok = got[0] == want[0] and got[1] == want[1] and got[2] == bytes(want[2][:got[1] - at])
        check(ok, f"{label}: status {got[0]} / {want[0]}, CLPTR ${got[1]:04X} / ${want[1]:04X}"
                  f"{'' if got[2] == bytes(want[2][:max(0, got[1] - at)]) else ', BYTES DIFFER'}"
                  f" (as built / the stream's rules)")

    # TXTMAX: in place iff the file's end is at or below it; else out of memory, nothing read
    plen = n - 1
    for room in (plen + 40, plen + 1, plen, plen - 1, plen - 200, 300):
        at = txtmax - room
        m, d = machine(img, None, at)
        s = m.sym
        reads = []
        orig = m.traps[s["read_sector"]]

        def counting(mm, orig=orig, reads=reads):
            reads.append(mm.cpu.de)
            orig(mm)
        m.traps[s["read_sector"]] = counting
        if "read_sector_nh" in s:   # D-LOADHOLD: frs_to's door past the check
            m.traps[s["read_sector_nh"]] = counting
        guard = bytes(m.mem[txtmax:txtmax + 16])
        m.call("hk_dpload")
        st = m.mem[s["DISKOP_STATUS"]]
        clptr = m.mem[s["CLPTR"]] | m.mem[s["CLPTR"] + 1] << 8
        untouched = bytes(m.mem[txtmax:txtmax + 16]) == guard
        if room >= plen:
            want = stream(img[1:], at)
            ok = st == 0 and clptr == want[1] and untouched
        else:
            ok = st == 4 and untouched and len(reads) <= 4     # mount, dir, FAT -- no data
        check(ok, f"the file ends {plen - room:+d} B past TXTMAX: status {st} "
                  f"({'loaded' if room >= plen else 'out of memory, nothing read'}), "
                  f"{len(reads)} sector reads, TXTMAX..+16 {'untouched' if untouched else 'WRITTEN'}")

    # --- D-LOADFAT: a chain across the FAT-sector edge, and the reads counted ---
    big = b"\xff" + program(nlines=120)
    for first, label in ((2, "contiguous from cluster 2"), (338, "from cluster 338, across the straddle")):
        d = D.Disk()
        d.next_clus = first
        d.add_file("P.BAS", big)
        m = D.machine(d)
        s = m.sym
        fatreads, dests = [], []
        orig = m.traps[s["read_sector"]]

        def counting(mm, orig=orig, fatreads=fatreads, dests=dests):
            if D.RESERVED <= mm.cpu.de < D.RESERVED + D.SPF:
                fatreads.append(mm.cpu.de)
            else:
                dests.append(mm.cpu.hl)
            orig(mm)
        m.traps[s["read_sector"]] = counting
        if "read_sector_nh" in s:   # D-LOADHOLD: frs_to's door past the check
            m.traps[s["read_sector_nh"]] = counting
        m.poke(s["DISK_FCB_NAME"], D.name83("P.BAS"))
        m.poke(s["FOPEN_SEL"], s["FOPEN_SEL_LOAD"])
        m.poke_w(TXTTAB_CELL, 0x8001)
        m.call("hk_dpload")
        end = m.mem[s["CLPTR"]] | m.mem[s["CLPTR"] + 1] << 8
        nclus = -(-len(big) // (D.SPC * D.SECSIZE))
        secs = sorted(set((c * 3 // 2) // D.SECSIZE for c in range(first, first + nclus)))
        ok = (m.mem[s["DISKOP_STATUS"]] == 0 and bytes(m.mem[0x8001:end]) == program(nlines=120)[:-2]
              and not m.mem[s["FAT_DEFER"]] & 0x80)
        check(ok, f"{label}: status {m.mem[s['DISKOP_STATUS']]}, {end - 0x8001} B = the program's "
                  f"bytes, cache off after (FAT_DEFER ${m.mem[s['FAT_DEFER']]:02X})")
        straddle = any((c * 3 // 2) % D.SECSIZE == D.SECSIZE - 1 for c in range(first, first + nclus - 1))
        want = 1 + len(secs) + straddle
        check(len(fatreads) == want,
              f"{label}: {len(fatreads)} FAT-sector reads (want {want}: the mount's, one per FAT "
              f"sector {secs}{', the straddle' if straddle else ''}) for {nclus} clusters")
        # the design: the data sectors after the first land IN PLACE, $200 apart
        buf = s["FAT_DBUF"]
        full = (len(big) - D.SECSIZE) // D.SECSIZE
        inplace = [h for h in dests if h != buf]
        want_in = [0x8001 + (D.SECSIZE - 1) + k * D.SECSIZE for k in range(full)]
        check(inplace == want_in,
              f"{label}: {len(inplace)} data sectors read in place at "
              f"${inplace[0] if inplace else 0:04X}..${inplace[-1] if inplace else 0:04X} step $200 "
              f"(want {len(want_in)}), {len(dests) - len(inplace)} through FAT_DBUF")
    # --- fragmented chains: exact, every full sector at its final address ---
    def frag_disk(data, moves):
        """`data` laid out from cluster 2, then each cluster in `moves` relocated
        (old -> new): its sectors copied, the chain relinked around it."""
        d = D.Disk()
        d.add_file("P.BAS", data)
        nclus = -(-len(data) // (D.SPC * D.SECSIZE))
        chain = list(range(2, 2 + nclus))
        for old, new in moves.items():
            for k in range(D.SPC):
                d.sec[D.FIRSTDATA + (new - 2) * D.SPC + k] = d.sec.pop(D.FIRSTDATA + (old - 2) * D.SPC + k)
            d.set_fat(old, 0)
            chain[chain.index(old)] = new
        for a, b in zip(chain, chain[1:] + [0xFFF]):
            d.set_fat(a, b)
        d.sync_fat()
        return d, chain

    big = b"\xff" + program(nlines=120)
    for moves, label in (({}, "a contiguous file"),
                         ({7: 40, 8: 41}, "two clusters moved away (one gap, rejoined)"),
                         ({5: 60, 9: 30, 12: 50}, "three scattered clusters")):
        d, chain = frag_disk(big, moves)
        m = D.machine(d)
        s = m.sym
        dests = []
        orig = m.traps[s["read_sector"]]

        def logged(mm, orig=orig, dests=dests):
            if mm.cpu.de >= D.FIRSTDATA:
                dests.append((mm.cpu.de, mm.cpu.hl))
            orig(mm)
        m.traps[s["read_sector"]] = logged
        if "read_sector_nh" in s:   # D-LOADHOLD: frs_to's door past the check
            m.traps[s["read_sector_nh"]] = logged
        m.poke(s["DISK_FCB_NAME"], D.name83("P.BAS"))
        m.poke(s["FOPEN_SEL"], s["FOPEN_SEL_LOAD"])
        m.poke_w(TXTTAB_CELL, 0x8001)
        m.call("hk_dpload")
        end = m.mem[s["CLPTR"]] | m.mem[s["CLPTR"] + 1] << 8
        ok = m.mem[s["DISKOP_STATUS"]] == 0 and bytes(m.mem[0x8001:end]) == program(nlines=120)[:-2]
        # the full sectors after the first: each from its chain position to its own address
        full = (len(big) - D.SECSIZE) // D.SECSIZE
        secs = [D.FIRSTDATA + (c - 2) * D.SPC + k for c in chain for k in range(D.SPC)][1:1 + full]
        want = [(x, 0x8001 + (D.SECSIZE - 1) + k * D.SECSIZE) for k, x in enumerate(secs)]
        got = [g for g in dests if g[1] != s["FAT_DBUF"]]
        check(ok and got == want,
              f"{label}: status {m.mem[s['DISKOP_STATUS']]}, program {'exact' if ok else 'WRONG'}; "
              f"{len(got)} full sectors each read from its chain position to its own address "
              f"(want {len(want)})")
    return fails


if __name__ == "__main__":
    f = run()
    print(f"{'OK' if not f else 'FAILED'}: {f} failure(s)")
    sys.exit(1 if f else 0)
