"""Host test for D-LOADRUN: LOAD copies a line body a SECTOR RUN at a time
(disk/runtime.asm hdl_run, called from disk/kernel.asm hk_dpload's hdl_body).

hdl_run must change nothing but the speed. Each row runs the disk LOAD twice on
the same FAT12 model (test_hk_dpbload's): once as built, once with hdl_run
trapped to return at once -- the byte-by-byte path every LOAD took before -- and
the two must leave the same status, the same CLPTR and the same bytes in RAM
from the text base up past TXTMAX. The rows are the edges hdl_run hands back to
the byte path:
  * a 3.7 KB (8-sector) program whose bodies (1..250 B) straddle its sector edges;
  * the same file ENDING EARLY (a directory size cut inside a body, on and around
    a sector edge, inside a header) -- FREAD_LEFT bounds the run;
  * a text base so high the program meets TXTMAX inside a body -- the run must
    not write past it, and the byte path raises out of memory where it did.
D-LOADFAT (2026-11-06) adds LOAD's one-sector FAT read cache (FAT_FCACHE, the FAT
sector in FAT_MBUF while hk_dpload reads): the program stored from cluster 338, so
its chain crosses cluster 341 -- the entry that STRADDLES FAT sectors 1 and 2 --
and the next FAT sector, must load to the exact bytes; and the FAT sectors LOAD
reads are counted: one read per FAT sector the chain enters (plus the straddle's
next-sector read), where the uncached walk read one per cluster.
A two-sided control proves the as-built LOAD is not the byte path by accident: on
a step budget the byte path cannot meet, the as-built LOAD finishes with the
program's bytes, and the trapped one runs out.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_hk_dpbload as D  # noqa: E402  (the FAT12 model and the disk build)

TXTTAB_CELL = 0xF676
BODIES = [1, 7, 250, 33, 128, 200, 5, 90, 250, 250, 17, 64, 3, 180]


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


def machine(data, size, at, run):
    d = D.Disk()
    d.add_file("P.BAS", data, size)
    m = D.machine(d)
    s = m.sym
    m.poke(s["DISK_FCB_NAME"], D.name83("P.BAS"))
    m.poke(s["FOPEN_SEL"], s["FOPEN_SEL_LOAD"])
    m.poke_w(TXTTAB_CELL, at)
    if not run:
        m.trap("hdl_run", lambda mach: None)    # the byte path, as before D-LOADRUN
    return m


def load(data, size, at, run):
    m = machine(data, size, at, run)
    s = m.sym
    m.call("hk_dpload")
    top = s["TXTMAX"] + 16
    return (m.mem[s["DISKOP_STATUS"]], m.mem[s["CLPTR"]] | m.mem[s["CLPTR"] + 1] << 8,
            bytes(m.mem[at:top]))


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

    rows = [("whole file", img, None, 0x8001)]
    for cut in (1, 3, 5, 200, 511, 512, 513, 1023, 1024, 1025, 1536, 2047, 2048,
                2600, 3000, n - 3, n - 1):
        if cut < n:
            rows.append((f"file ends at byte {cut}", img, cut, 0x8001))
    for room in (300, 700, 1200, 2000):
        rows.append((f"TXTMAX {room} B above the base", img, None, txtmax - room))

    for label, data, size, at in rows:
        a = load(data, size, at, run=True)
        b = load(data, size, at, run=False)
        same = a[:3] == b[:3]
        check(same, f"{label}: status {a[0]} / {b[0]}, CLPTR ${a[1]:04X} / ${b[1]:04X}"
                    f"{'' if a[2] == b[2] else ', RAM DIFFERS'} (as built / byte path)")

    # --- D-LOADFAT: a chain across the FAT-sector edge, and the reads counted ---
    big = b"\xff" + program(nlines=120)
    for first, label in ((2, "contiguous from cluster 2"), (338, "from cluster 338, across the straddle")):
        d = D.Disk()
        d.next_clus = first
        d.add_file("P.BAS", big)
        m = D.machine(d)
        s = m.sym
        fatreads = []
        orig = m.traps[s["read_sector"]]

        def counting(mm, orig=orig, fatreads=fatreads):
            if D.RESERVED <= mm.cpu.de < D.RESERVED + D.SPF:
                fatreads.append(mm.cpu.de)
            orig(mm)
        m.traps[s["read_sector"]] = counting
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
        # fat_mount's own media read (fat_geom_read) is one; then ONE per FAT sector the
        # chain enters, and one more where an entry straddles two (it is read into
        # FAT_DBUF, unchanged) -- scratchpad/loadfat_reads.out logged each with its caller
        straddle = any((c * 3 // 2) % D.SECSIZE == D.SECSIZE - 1 for c in range(first, first + nclus - 1))
        want = 1 + len(secs) + straddle
        check(len(fatreads) == want,
              f"{label}: {len(fatreads)} FAT-sector reads (want {want}: the mount's, one per FAT "
              f"sector {secs}{', the straddle' if straddle else ''}) for {nclus} clusters -- "
              f"uncached it read one per cluster boundary, {nclus - 1}")

    # the two-sided control: a step budget the byte path cannot meet
    budget = 60_000
    m = machine(img, None, 0x8001, run=True)
    s = m.sym
    m.call("hk_dpload", max_steps=budget)
    end = m.mem[s["CLPTR"]] | m.mem[s["CLPTR"] + 1] << 8
    check(m.mem[s["DISKOP_STATUS"]] == 0 and bytes(m.mem[0x8001:end]) == program()[:-2],
          f"as built, {budget} steps: status {m.mem[s['DISKOP_STATUS']]}, {end - 0x8001} B "
          f"stored = the program's {len(program()) - 2}")
    m = machine(img, None, 0x8001, run=False)
    try:
        m.call("hk_dpload", max_steps=budget)
        check(False, f"byte path, {budget} steps: it finished -- the budget proves nothing")
    except RuntimeError:
        check(True, f"byte path, {budget} steps: runs out (the control is live)")
    return fails


if __name__ == "__main__":
    f = run()
    print(f"{'OK' if not f else 'FAILED'}: {f} failure(s)")
    sys.exit(1 if f else 0)
