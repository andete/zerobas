#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end functional probe: BSAVE -> BLOAD DATA round-trip, via a `.bas`-on-disk
AUTOEXEC test program, ZERO typed keyboard input.

Spec: disk/docs/diskbasic-bas-harness-spec.md. This REPLACES the fragile openMSX
`type`-injection approach for the BSAVE/BLOAD round-trip in disk_probe_save.py's
`rt_bsave_bload` (round-trip 1): that probe drives the REPL by emulated keystrokes
at fixed emutimes, and openMSX can double the first keypress in narrow
machine-specific windows -- a real false-positive bug hunt (see
disk/docs/openmsx-probing-toolbox.md §8 GOTCHA). Here the round-trip logic runs
from a tokenised AUTOEXEC.BAS program on the boot disk, auto-run at Disk-BASIC
cold start (disk_probe_autoexec.py's feature, commit c4c7d68) -- no keystrokes at
all. The probe only reads final state and judges it; it never drives the REPL.

PILOT SCOPE (signed off): BSAVE -> BLOAD DATA round-trip only (the case that
flaked). ,R-exec and SAVE -> RUN stay on disk_probe_save.py's type-injection path
for now; this is an ADDITIONAL gate cell, not a replacement of that probe/file.

The `.bas` test program (readable BASIC, tokenised by OUR OWN ROM crunch via
bas_tokenise.py -- never hand-assembled token bytes):

    10 FORI=0TO16:POKE&HC000+I,I*3+7:NEXT   ' position-varying pattern (not all-equal)
    20 BSAVE"A:SV.BIN",&HC000,&HC010
    30 FORI=0TO16:POKE&HC000+I,&HA5:NEXT     ' wipe with nonzero sentinel
    40 BLOAD"A:SV.BIN"
    50 POKE&HD0FF,&H99                       ' DONE sentinel

Pattern formula (reproduced in Python -- PATTERN below): byte[i] = (i*3+7) & 0xFF
for i in 0..16, i.e. 17 bytes, all distinct, none equal to the $A5 wipe sentinel.

BOTH captures (per spec) on a FRESH /tmp disk (disk/test720.dsk is NEVER touched):
  1. RAM $C000..$C010 after settling == PATTERN -> BLOAD read-path fidelity (proven
     by the fact that we wiped the region with $A5 first: a no-op BLOAD would leave
     $A5, not the pattern).
  2. Offline FAT12 parse of the .dsk: SV.BIN's on-disk BSAVE payload (7-byte header
     + 17 data bytes) == PATTERN -> BSAVE write-path fidelity, independent of BLOAD
     (SV.BIN could be written correctly and never re-read, or vice versa -- this
     checks both directions separately).
  3. VACUITY GUARD: $D0FF == $99 (the .bas program actually ran to completion, in
     BOTH captures above) -- a stuck/aborted run must never masquerade as a pass.
  4. DIFFERENTIAL: the identical disk image, black-box booted on the real
     National_CF-3300 reference, must produce the SAME RAM state AND the same
     on-disk SV.BIN payload. Ours must match stock.

TEST DISK SAFETY: every disk here is a FRESH /tmp image built by this probe (via
tools/make_test_dsk.py's Fat12Image) -- the committed disk/test720.dsk is never
touched (git status stays clean).

Clean-room: `.bas` source is our own program, tokenised by our own ROM; the disk
image is built per the public FAT12/MSX-BASIC-file-format specs (same class as
tools/make_test_dsk.py / disk_probe_autoexec.py); National_CF-3300 is exercised
ONLY black-box (boot + observe RAM / read the .dsk it wrote -- never disassembled).

Prerequisites (CURRENT zerobas tree):
  * `make all` (build/basic.rom + build/disk.rom under test), then
    `python3 tools/install-openmsx-machine.py --disk-rom build/disk.rom --real-bios-disk`
    (or `make machines-oracle`) so C-BIOS_MSX1_EU_BASIC_DISK reflects the build
    under test and National_CF-3300 is available.

    python3 probes/disk/disk_probe_save_bas.py
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_sys.path.insert(0, _os.path.join(_ROOT, "tools"))  # make_test_dsk.py (Fat12Image)

import argparse
import os
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time

from make_test_dsk import Fat12Image  # noqa: E402  (path set up above)
from bas_tokenise import make_basic_file  # noqa: E402  (our-ROM tokeniser helper)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"

OURS_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE")
REF_MACHINE = "National_CF-3300"          # the genuine reference, booted black-box

TXTBASE = 0x8001

# --- the `.bas` test program (readable BASIC; tokenised by OUR ROM crunch) ---
BIN_START = 0xC000
BIN_END = 0xC010                          # inclusive -> 17 bytes
WIPE_BYTE = 0xA5                          # nonzero sentinel: a no-op BLOAD stays visible
DONE_ADDR = 0xD0FF
DONE_BYTE = 0x99
DONE_POISON = 0x11                        # pre-boot poison for the done-sentinel

AUTOEXEC_LINES = [
    (10, "FORI=0TO16:POKE&HC000+I,I*3+7:NEXT"),
    (20, 'BSAVE"A:SV.BIN",&HC000,&HC010'),
    (30, f"FORI=0TO16:POKE&HC000+I,&H{WIPE_BYTE:02X}:NEXT"),
    (40, 'BLOAD"A:SV.BIN"'),
    (50, f"POKE&H{DONE_ADDR:04X},&H{DONE_BYTE:02X}"),
]

# Reproduced in Python: byte[i] = (i*3+7) & 0xFF for i in 0..16 -- position-
# varying (not all-equal), matches line 10's `I*3+7` formula exactly, and stays
# in 0..255 (kept as 1-byte INT1 literals by the tokeniser). None of the 17
# values equals WIPE_BYTE ($A5), so a stuck wipe is distinguishable from a
# correct restore.
PATTERN = bytes(((i * 3 + 7) & 0xFF) for i in range(BIN_END - BIN_START + 1))
assert WIPE_BYTE not in PATTERN, "wipe sentinel collides with the pattern"

# --- SV.BIN on-disk BSAVE layout (MSX-BASIC file formats, public spec; same
# 7-byte header tools/make_test_dsk.py's build_bsave_payload/make_bsave_file and
# disk_probe_save.py's BSAVE fixtures use): $FE, start, end, exec (all LE),
# then the raw data bytes [start..end] inclusive.
BSAVE_ID = 0xFE


def autoexec_disk_file() -> bytes:
    """The tokenised AUTOEXEC.BAS disk file (our own ROM crunch, not hand-built
    token bytes -- see bas_tokenise.py)."""
    return make_basic_file(AUTOEXEC_LINES, TXTBASE)


def build_disk() -> str:
    """A fresh /tmp FAT12 image whose only file is our tokenised AUTOEXEC.BAS.
    A blank FAT12 image has ample free space for BSAVE"A:SV.BIN" (17 data bytes)
    to land in a second file alongside it."""
    img = Fat12Image()
    img.add_file("AUTOEXEC", "BAS", autoexec_disk_file())
    fd, path = tempfile.mkstemp(suffix=".dsk", prefix="save_bas_probe_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(img.finish())
    return path


# --- offline FAT12 parse of the resulting .dsk (mirrors disk_fat_*_oracle.py /
# make_test_dsk.py's own geometry constants -- public Microsoft FAT spec) ------
def parse_bpb(img: bytes) -> dict:
    def rd16(b, o):
        return b[o] | (b[o + 1] << 8)
    bps = rd16(img, 11)
    spc = img[13]
    rsvd = rd16(img, 14)
    nfat = img[16]
    root_ent = rd16(img, 17)
    spf = rd16(img, 22)
    fat_start = rsvd
    root_start = fat_start + nfat * spf
    root_secs = (root_ent * 32 + bps - 1) // bps
    data_start = root_start + root_secs
    return dict(bps=bps, spc=spc, root_ent=root_ent, root_start=root_start,
               root_secs=root_secs, data_start=data_start)


def read_file_from_dsk(dsk_path: str, name8: str, ext3: str) -> bytes | None:
    """Find `name8.ext3` in the root dir and return its RAW cluster-chain bytes
    truncated to the directory-entry file size (independent of BLOAD -- this
    reads the .dsk exactly as a FAT12 client would, per the public spec)."""
    img = open(dsk_path, "rb").read()
    bpb = parse_bpb(img)
    clus_bytes = bpb["spc"] * bpb["bps"]
    root_off = bpb["root_start"] * bpb["bps"]
    want = (name8.encode("ascii").ljust(8)[:8] + ext3.encode("ascii").ljust(3)[:3]).upper()
    entry = None
    for i in range(bpb["root_ent"]):
        off = root_off + i * 32
        e = img[off:off + 32]
        if not e or e[0] in (0x00, 0xE5):
            continue
        if bytes(e[0:11]).upper() == want:
            entry = e
            break
    if entry is None:
        return None
    first_cluster = entry[26] | (entry[27] << 8)
    size = struct.unpack("<I", entry[28:32])[0]
    # SV.BIN is tiny (one cluster is ample); a straight single-cluster read
    # matches how it was written (Fat12Image.add_file always chains forward,
    # and 24 bytes << clus_bytes for this image's geometry).
    first_sec = bpb["data_start"] + (first_cluster - 2) * bpb["spc"]
    raw = img[first_sec * bpb["bps"]: first_sec * bpb["bps"] + clus_bytes]
    return raw[:size]


def parse_bsave(payload: bytes) -> tuple[int, int, int, bytes]:
    """[$FE][start][end][exec][data...] -> (start, end, exec, data)."""
    assert payload[0] == BSAVE_ID, f"not a BSAVE file: id=${payload[0]:02X}"
    start, end, exec_ = struct.unpack("<HHH", payload[1:7])
    data = payload[7:7 + (end - start + 1)]
    return start, end, exec_, data


# --- boot + capture (zero typed input; poison-then-settle, per
# disk_probe_autoexec.py's t=1 lesson: a t=0 write can silently no-op) --------
def cold_boot_and_capture(machine: str, dsk: str, out_path: str,
                          timeout: float = 60.0) -> dict:
    tcl = f"""set throttle off
set renderer none
set sound_driver null
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc poison {{}} {{
  debug write memory 0x{DONE_ADDR:04X} 0x{DONE_POISON:02X}
}}
after time 1 {{ poison }}
proc cap {{}} {{
  set f [open {{{out_path}}} w]
  puts $f "done=[format %02X [debug read memory 0x{DONE_ADDR:04X}]]"
  puts $f "region=[__hex 0x{BIN_START:04X} {BIN_END - BIN_START + 1}]"
  close $f
  exit
}}
after time 25 {{ cap }}
"""
    tcl_path = out_path + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out_path):
        os.unlink(out_path)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT cold-booting {machine} with {dsk}")
    if not os.path.exists(out_path):
        sys.exit(f"no capture from {machine} (ROMs/machine missing?)")
    d = {}
    for ln in open(out_path):
        k, _, v = ln.strip().partition("=")
        d[k] = v
    if "done" not in d or "region" not in d:
        sys.exit(f"capture from {machine} missing expected keys: {d!r}")
    return d


def run_one(machine: str, label: str) -> tuple[bool, str]:
    """Boot `machine` on a fresh disk, capture, and check the vacuity guard +
    RAM fidelity + on-disk artifact. Returns (all_ok, report_text)."""
    dsk = build_disk()
    lines = []
    try:
        cap = cold_boot_and_capture(machine, dsk, f"/tmp/save_bas_{label}.txt")
        done = int(cap["done"], 16)
        region = bytes.fromhex(cap["region"])

        # VACUITY GUARD: the .bas program must have run to completion.
        r_done = done == DONE_BYTE
        lines.append(f"  [{'PASS' if r_done else 'FAIL'}] done-guard: "
                     f"(${DONE_ADDR:04X})=${done:02X} (expect ${DONE_BYTE:02X} -- "
                     f"program ran to completion, poisoned ${DONE_POISON:02X} pre-boot)")

        # RAM: BLOAD read-path fidelity (region was wiped to $A5 by line 30).
        r_ram = region == PATTERN
        lines.append(f"  [{'PASS' if r_ram else 'FAIL'}] RAM [{BIN_START:04X}..{BIN_END:04X}] "
                     f"after BLOAD = {'the saved pattern' if r_ram else 'DIFFERS'}")
        if not r_ram:
            lines.append(f"        got {region.hex()}\n        exp {PATTERN.hex()}")

        # On-disk artifact: SV.BIN's BSAVE payload independent of BLOAD.
        sv_bin = read_file_from_dsk(dsk, "SV", "BIN")
        r_artifact = False
        if sv_bin is None:
            lines.append("  [FAIL] on-disk SV.BIN: not found in root directory")
        else:
            try:
                start, end, exec_, data = parse_bsave(sv_bin)
                r_artifact = (start == BIN_START and end == BIN_END and data == PATTERN)
                lines.append(f"  [{'PASS' if r_artifact else 'FAIL'}] on-disk SV.BIN "
                             f"BSAVE payload (start=${start:04X} end=${end:04X}) "
                             f"{'matches' if r_artifact else 'DIFFERS from'} the saved pattern")
                if not r_artifact:
                    lines.append(f"        got {data.hex()}\n        exp {PATTERN.hex()}")
            except Exception as e:
                lines.append(f"  [FAIL] on-disk SV.BIN: malformed BSAVE payload ({e})")
        ok = r_done and r_ram and r_artifact
    finally:
        os.unlink(dsk)
    return ok, "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ours-machine", default=OURS_MACHINE)
    ap.add_argument("--ref-machine", default=REF_MACHINE)
    args = ap.parse_args()
    if not args.ours_machine:
        sys.exit("no zerobas machine: pass --ours-machine or set $ZEROBAS_BASIC_MACHINE; there is no\n"
                 "default, one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    ok = True

    print(f"AUTOEXEC.BAS BSAVE\"A:SV.BIN\",&H{BIN_START:04X},&H{BIN_END:04X}  ->  "
          f"BLOAD\"A:SV.BIN\"  (cold-boot auto-run, zero typed input)")
    print(f"pattern: byte[i] = (i*3+7) & 0xFF, i=0..16 -> {PATTERN.hex()}")

    print(f"\n[ours: {args.ours_machine}]")
    r_ours, rep_ours = run_one(args.ours_machine, "ours")
    print(rep_ours)
    ok = ok and r_ours

    print(f"\n[STOCK reference: {args.ref_machine}] (CF-3300 differential)")
    r_ref, rep_ref = run_one(args.ref_machine, "ref")
    print(rep_ref)
    ok = ok and r_ref

    print("\n" + ("ALL PASS -- BSAVE/BLOAD DATA round-trip via .bas-on-disk "
                  "auto-run matches the National_CF-3300 stock reference "
                  "(RAM read-path AND on-disk write-path both fidelity-checked)"
                  if ok else "FAIL -- see per-check results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
