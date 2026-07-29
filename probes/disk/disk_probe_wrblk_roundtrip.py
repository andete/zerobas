#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Disk-artifact round-trip for BDOS $26 WRBLK (M28 verification).

The BDOS RAM-capture acceptance gate is BLIND to on-disk write effects. This
probe proves WRBLK's persisted artifact is byte-identical between OURS
(C-BIOS + zerobas-disk) and the STOCK National CF-3300 oracle, per case:

  fresh /tmp copy of a real MSX-DOS-1 disk (PER MACHINE) + inject WRTEST.BIN
  (target) + WRBLK.COM (the wrblk_rt.asm exerciser, params patched per case)
  -> boot openMSX, type WRBLK at A> -> the WRBLK+FCLOSE persist to the /tmp
  image -> pure-Python FAT12 parse of BOTH mutated images -> diff dirent size /
  first cluster / full FAT chain / the written record's bytes.

For the SHRINK case ours intentionally DIVERGES from stock (signed off, §6 Q3):
ours FCLOSE succeeds + frees the tail; stock corrupts the FAT. There we assert
ours is self-consistent, not ours==stock.

CLEAN-ROOM: the CF-3300 is a black box we RUN and whose OUTPUT DISK we READ; its
ROM code is never read/disassembled. Test disks are always /tmp copies.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse, don't duplicate)

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "wrblk_rt.asm")
OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
DEFAULT_DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
OUR_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE")
REF_MACHINE = "National_CF-3300"
TARGET = ("WRTEST", "BIN")


# --------------------------------------------------------------------------- #
# exerciser build + per-case param patch
# --------------------------------------------------------------------------- #
def assemble_com() -> bytes:
    com = "/tmp/wrblk_rt.com"
    subprocess.run(["pasmo", "--bin", ASM, com, "/tmp/wrblk_rt.sym"], check=True)
    return open(com, "rb").read()


def patch_params(com: bytes, recnum: int, rs: int, cnt: int, fillb: int,
                  delflag: int = 0) -> bytes:
    b = bytearray(com)
    b[2] = recnum & 0xFF
    b[3] = (recnum >> 8) & 0xFF
    b[4] = (recnum >> 16) & 0xFF
    struct.pack_into("<H", b, 5, rs)
    struct.pack_into("<H", b, 7, cnt)
    b[9] = fillb & 0xFF
    b[10] = delflag & 0xFF   # M30 del_realloc: nonzero -> BDOS $13 DELETE DELFILE.BIN first
    return bytes(b)


# --------------------------------------------------------------------------- #
# FAT12 reader (pure Python, over a whole .dsk image)
# --------------------------------------------------------------------------- #
class Fat12:
    def __init__(self, path: str):
        self.img = bytearray(open(path, "rb").read())
        b = self.img
        self.bps = struct.unpack_from("<H", b, 11)[0]
        self.spc = b[13]
        self.resv = struct.unpack_from("<H", b, 14)[0]
        self.nfat = b[16]
        self.rootent = struct.unpack_from("<H", b, 17)[0]
        self.spf = struct.unpack_from("<H", b, 22)[0]
        self.root_off = (self.resv + self.nfat * self.spf) * self.bps
        self.root_secs = (self.rootent * 32 + self.bps - 1) // self.bps
        self.first_data_sec = self.resv + self.nfat * self.spf + self.root_secs
        self.fat_off = self.resv * self.bps

    def dirent(self, name: str, ext: str):
        want = (name.ljust(8) + ext.ljust(3)).encode("latin1")
        for i in range(self.rootent):
            e = self.img[self.root_off + i * 32: self.root_off + i * 32 + 32]
            if e[:11] == want:
                return {"idx": i, "cluster": struct.unpack_from("<H", e, 26)[0],
                        "size": struct.unpack_from("<I", e, 28)[0], "attr": e[11]}
        return None

    def fat_get(self, cl: int) -> int:
        off = self.fat_off + cl + (cl >> 1)
        v = struct.unpack_from("<H", self.img, off)[0]
        return (v >> 4) if (cl & 1) else (v & 0x0FFF)

    def chain(self, first: int, limit: int = 4096):
        out, cl = [], first
        while 2 <= cl < 0x0FF8 and len(out) < limit:
            out.append(cl)
            cl = self.fat_get(cl)
        return out, cl  # cl = terminator value (>=0x0FF8 = EOC, 0 = free/broken)

    def cluster_bytes(self, cl: int) -> bytes:
        sec = self.first_data_sec + (cl - 2) * self.spc
        off = sec * self.bps
        return bytes(self.img[off: off + self.spc * self.bps])

    def record_bytes(self, first: int, rec: int, rs: int = 128) -> bytes | None:
        """Bytes of the rs-sized record #rec, following the actual FAT chain."""
        byte_off = rec * rs
        sec_in_file = byte_off // self.bps
        within = byte_off % self.bps
        ch, _ = self.chain(first)
        secs = []
        for cl in ch:
            for s in range(self.spc):
                secs.append((cl, s))
        if sec_in_file >= len(secs):
            return None
        cl, s = secs[sec_in_file]
        data = self.cluster_bytes(cl)
        base = s * self.bps + within
        return data[base: base + rs]


# --------------------------------------------------------------------------- #
# openMSX run (boot DOS, type WRBLK, exit) — writes persist to -diska
# --------------------------------------------------------------------------- #
def run(machine: str, dsk: str, boot_s: int, end_s: int, timeout: float) -> None:
    # Belt AND braces: WRBLK.COM is BOTH auto-run from AUTOEXEC.BAT (which the
    # CF-3300 honours) AND typed at the prompt at several increasing times
    # (which C-BIOS honours). Re-running with identical params is idempotent, so
    # both firing is harmless; this removes all per-machine boot-path/timing
    # dependence (observed: C-BIOS runs typed keys not AUTOEXEC; CF-3300 the
    # reverse).
    types = "\n".join(f'after time {t} {{ type "WRBLK\\r" }}'
                      for t in range(boot_s, end_s - 4, 6))
    tcl = f"""set throttle off
{types}
after time {end_s} {{ exit }}
"""
    tcl_path = dsk + ".tcl"
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk,
           "-command", "set renderer none", "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        raise TimeoutError(f"TIMEOUT running {machine}")


def build_disk(dos: str, out: str, com: bytes, binsize: int, binfill: int,
               del_size: int = 0) -> None:
    shutil.copyfile(dos, out)
    img = bytearray(open(out, "rb").read())
    if del_size:
        # M30 del_realloc: DELFILE.BIN goes in FIRST so it claims the low
        # (first-free) clusters; WRTEST.BIN (added next) is forced past it.
        # The exerciser then DELETEs DELFILE.BIN before WRBLK, so the
        # allocation it triggers must reuse the just-freed low clusters --
        # exactly the "free then allocate, same operation-set" worry §4/§6.2
        # of tier2-m30-alloc-hint-spec.md is designed to be safe against.
        fat12_add(img, "DELFILE", "BIN", bytes([0x99]) * del_size)
    fat12_add(img, TARGET[0], TARGET[1], bytes([binfill]) * binsize)
    fat12_add(img, "WRBLK", "COM", com)
    # AUTOEXEC.BAT auto-runs WRBLK on boot (no keyboard-timing dependence).
    fat12_add(img, "AUTOEXEC", "BAT", b"WRBLK\r\n")
    open(out, "wb").write(img)


# --------------------------------------------------------------------------- #
# cases
# --------------------------------------------------------------------------- #
CASES = {
    # name: dict(binsize, binfill, recnum, rs, cnt, fillb, kind[, checkrec])
    "within":  dict(binsize=2048, binfill=0x11, recnum=3,   rs=128, cnt=1, fillb=0xA5, kind="eq"),
    "extend":  dict(binsize=512,  binfill=0x22, recnum=12,  rs=128, cnt=1, fillb=0xB6, kind="eq"),
    "rr24":    dict(binsize=512,  binfill=0x33, recnum=256, rs=128, cnt=1, fillb=0xC7, kind="eq"),
    "shrink":  dict(binsize=4096, binfill=0x44, recnum=3,   rs=128, cnt=0, fillb=0x00, kind="shrink"),
    # M29 cursor path: ONE wrblk call writing 8 sequential records from record 0 --
    # records 0-3 reuse the first 512B sector (wpe_same, no re-read/re-walk), record
    # 4 advances one step into a freshly allocated cluster (wpe_adv), 5-7 reuse it.
    # Must be byte-identical to stock; checkrec=6 validates a second-sector record.
    "multi":   dict(binsize=512,  binfill=0x55, recnum=0,   rs=128, cnt=8, fillb=0xD8, kind="eq", checkrec=6),
    # M30 (tier2-m30-alloc-hint-spec.md §6.2) del_realloc: ONE run that both
    # FREES a low-cluster file (BDOS $13 DELETE of DELFILE.BIN) and THEN
    # ALLOCATES (WRBLK extends WRTEST.BIN past its tiny seed).
    # FINDING (verified 2026-07-04): ours reuses the just-freed LOW clusters
    # (lowest-free-first); the CF-3300 does NOT. CHARACTERISED 2026-07-05
    # (tier2-alloc-order-findings.md, disk_probe_alloc_order.py): stock is a
    # TAIL-RELATIVE contiguity allocator -- extending a file whose tail cluster is
    # L it takes L-1 if free (walking DOWN: 339,338,...), else the first free
    # scanning UP from L; ours has no tail bias (global lowest-free). Here tail=340,
    # L-1=339 is the just-freed top of the hole, so stock takes 339 and ours 336.
    # PRE-EXISTING -- a HEAD (pre-M30) ROM produces the SAME ours chain, and host
    # test_fat_alloc_hint.py case (c) proves M30's allocator returns the identical
    # sequence to the from-2 (pre-M30) scan. So M30 is byte-identical to today; the
    # ours!=stock order is a separate, ACCEPTED cosmetic divergence (user, 2026-07-05:
    # valid FAT12, identical data) -- NOT an M30 regression. Documented, not
    # asserted ours==stock (like the shrink case).
    "del_realloc": dict(binsize=512, binfill=0x66, recnum=8, rs=128, cnt=1,
                         fillb=0xE9, kind="divergence", delflag=1, del_size=4096),
}


def summarise(tag: str, fp: str, recnum: int, rs: int):
    f = Fat12(fp)
    d = f.dirent(*TARGET)
    if d is None:
        print(f"    {tag}: WRTEST.BIN NOT FOUND")
        return None
    ch, term = f.chain(d["cluster"])
    rec = f.record_bytes(d["cluster"], recnum, rs) if d["cluster"] >= 2 else None
    print(f"    {tag}: size={d['size']} first_clus={d['cluster']} "
          f"chain_len={len(ch)} term={term:#05x}")
    print(f"       chain={ch[:16]}{'...' if len(ch) > 16 else ''}")
    if rec is not None:
        print(f"       rec[{recnum}] first16={rec[:16].hex()} (all==fill? "
              f"{len(set(rec))==1})")
    else:
        print(f"       rec[{recnum}] = <beyond chain>")
    return {"size": d["size"], "cluster": d["cluster"], "chain": ch, "term": term,
            "rec": rec}


def main():
    if not OUR_MACHINE:
        sys.exit("no zerobas machine: set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dos-disk", default=DEFAULT_DOS)
    ap.add_argument("--case", choices=list(CASES) + ["all"], default="all")
    ap.add_argument("--boot", type=int, default=14)
    ap.add_argument("--end", type=int, default=34)
    ap.add_argument("--timeout", type=float, default=90)
    args = ap.parse_args()

    com0 = assemble_com()
    cases = list(CASES) if args.case == "all" else [args.case]
    for name in cases:
        c = CASES[name]
        print(f"\n===== CASE {name} (recnum={c['recnum']} rs={c['rs']} "
              f"cnt={c['cnt']} file={c['binsize']}B) =====")
        com = patch_params(com0, c["recnum"], c["rs"], c["cnt"], c["fillb"],
                           c.get("delflag", 0))
        ours = f"/tmp/wrblk_rt_ours_{name}.dsk"
        stock = f"/tmp/wrblk_rt_stock_{name}.dsk"
        del_size = c.get("del_size", 0)
        build_disk(args.dos_disk, ours, com, c["binsize"], c["binfill"], del_size)
        build_disk(args.dos_disk, stock, com, c["binsize"], c["binfill"], del_size)
        try:
            run(OUR_MACHINE, ours, args.boot, args.end, args.timeout)
            print("  [ours ran]")
        except TimeoutError as e:
            print(f"  OURS {e}")
        try:
            run(REF_MACHINE, stock, args.boot, args.end, args.timeout)
            print("  [stock ran]")
        except TimeoutError as e:
            print(f"  STOCK {e}")
        checkrec = c.get("checkrec", c["recnum"])
        o = summarise("OURS ", ours, checkrec, c["rs"])
        s = summarise("STOCK", stock, checkrec, c["rs"])
        if o and s:
            if c["kind"] == "eq":
                same = (o["size"] == s["size"] and o["chain"] == s["chain"]
                        and o["rec"] == s["rec"])
                print(f"  => {'MATCH' if same else 'DIFFER'} (size/chain/rec)")
            elif c["kind"] == "divergence":
                # Pre-existing allocator-ORDER divergence (NOT M30): ours is
                # lowest-free-first (reuses the freed low clusters), the CF-3300
                # skips higher. size / chain length / EOC / written record all
                # agree -- only the cluster NUMBERS differ. Assert ours is
                # self-consistent + that ours reuses a lower (freed) cluster;
                # document, do NOT require ours == stock.
                shape_ok = (o["size"] == s["size"] and o["term"] >= 0xFF8
                            and len(o["chain"]) == len(s["chain"])
                            and o["rec"] == s["rec"])
                reuses_low = min(o["chain"]) < min(s["chain"])
                print(f"  => divergence(alloc-order, PRE-EXISTING not M30): "
                      f"ours self-consistent={shape_ok}, ours reuses freed-low "
                      f"cluster={reuses_low}")
                print(f"     ours chain={o['chain']} vs stock chain={s['chain']} "
                      f"(same size/len/rec; only cluster numbers differ) -- spec §6.2")
            else:
                print("  => shrink: ours self-consistency below; stock expected broken")
                print(f"     ours term={o['term']:#05x} (EOC>=0xff8 good); "
                      f"ours size={o['size']}")


if __name__ == "__main__":
    main()
