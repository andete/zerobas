#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end functional probe: BSAVE",S" -> BLOAD",S" VRAM round-trip, via a
`.bas`-on-disk AUTOEXEC test program, ZERO typed keyboard input.

Closure-spec item 1 (disk/docs/spec-diskbasic-option-closure.md): the ",S" option
on BSAVE/BLOAD interprets the start/end/exec addresses as VRAM and streams the data
bytes to/from VRAM (RDVRM/WRTVRM) instead of RAM. This probe proves the VRAM
save-path AND load-path round-trip byte-identically, matching the National_CF-3300
stock reference. It is the keyboard-free sibling of disk_probe_save_bas.py (the RAM
BSAVE/BLOAD round-trip), reusing that probe's `.bas`-on-disk AUTOEXEC harness so no
emulated keystrokes are involved (disk/docs/diskbasic-bas-harness-spec.md).

The `.bas` test program (readable BASIC, tokenised by OUR OWN ROM crunch via
bas_tokenise.py -- never hand-assembled token bytes):

    10 FORI=0TO16:VPOKE&H1000+I,I*3+7:NEXT   ' fill VRAM $1000..$1010 with a pattern
    20 BSAVE"A:SV.SC",&H1000,&H1010,S        ' VRAM save (,S): addrs are VRAM
    30 FORI=0TO16:VPOKE&H1000+I,&HA5:NEXT     ' wipe the VRAM region (nonzero sentinel)
    40 BLOAD"A:SV.SC",S                        ' VRAM load (,S): restore from disk
    50 FORI=0TO16:POKE&HC000+I,VPEEK(&H1000+I):NEXT  ' mirror VRAM -> RAM for capture
    60 POKE&HD0FF,&H99                          ' DONE sentinel

VRAM $1000..$1010 is UNUSED in both SCREEN 0 (40-col: name $0000-$03BF, pattern
$0800-$0FFF) and SCREEN 1 (32-col: pattern $0000-$07FF, name $1800-$1AFF), so the
display refresh and the KEYINT handler never perturb it between the wipe and the
readback, regardless of the mode the machine cold-booted into. VPEEK is used to
mirror the VRAM region back into RAM $C000 so the same `debug read_block` capture
path as disk_probe_save_bas.py can read it.

Pattern formula (reproduced in Python -- PATTERN below): byte[i] = (i*3+7) & 0xFF
for i in 0..16, i.e. 17 bytes, all distinct, none equal to the $A5 wipe sentinel.

FOUR checks, both on OUR machine and on the stock CF-3300 (must agree):
  1. VACUITY GUARD: $D0FF == $99 -- the .bas program ran to completion (poisoned
     $11 pre-boot). A stuck/aborted run must never masquerade as a pass.
  2. RAM $C000..$C010 (the VRAM mirror) after the round-trip == PATTERN -> the
     BLOAD",S" VRAM load-path restored the wiped region (a RAM-targeted or no-op
     BLOAD would leave $A5, or miss VRAM entirely).
  3. On-disk SV.SC's BSAVE payload (7-byte header + 17 data bytes) == PATTERN with
     start=$1000/end=$1010 -> the BSAVE",S" VRAM save-path read from VRAM and
     stored the VRAM addresses verbatim in the $FE header (independent of BLOAD).
  4. DIFFERENTIAL: the identical disk image, black-box booted on the real
     National_CF-3300, must produce the SAME RAM mirror AND the same on-disk
     SV.SC payload. Ours must match stock.

TEST DISK SAFETY: every disk here is a FRESH /tmp image built by this probe (via
tools/make_test_dsk.py's Fat12Image) -- the committed disk/test720.dsk is never
touched (git status stays clean).

Clean-room: `.bas` source is our own program, tokenised by our own ROM; the disk
image is built per the public FAT12/MSX-BASIC-file-format specs; the ",S" VRAM
grammar is the published MSX-BASIC syntax (spec-diskbasic-option-closure.md §1);
National_CF-3300 is exercised ONLY black-box (boot + observe RAM / read the .dsk it
wrote -- never disassembled).

Prerequisites (CURRENT zerobas tree): `make all` then `make machines-oracle` so
C-BIOS_MSX1_EU_BASIC_DISK reflects the build under test and National_CF-3300 is
available.

    python3 probes/disk/disk_probe_vram_saveload.py
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

OURS_MACHINE = "C-BIOS_MSX1_EU_BASIC_DISK"
REF_MACHINE = "National_CF-3300"          # the genuine reference, booted black-box

TXTBASE = 0x8001

# --- the `.bas` test program (readable BASIC; tokenised by OUR ROM crunch) ---
VRAM_START = 0x1000                        # unused in SCREEN 0 AND SCREEN 1
VRAM_END = 0x1010                          # inclusive -> 17 bytes
MIRROR = 0xC000                            # RAM landing for the VPEEK mirror
WIPE_BYTE = 0xA5                           # nonzero sentinel: a no-op BLOAD stays visible
DONE_ADDR = 0xD0FF
DONE_BYTE = 0x99
DONE_POISON = 0x11                         # pre-boot poison for the done-sentinel

AUTOEXEC_LINES = [
    (10, f"FORI=0TO16:VPOKE&H{VRAM_START:04X}+I,I*3+7:NEXT"),
    (20, f'BSAVE"A:SV.SC",&H{VRAM_START:04X},&H{VRAM_END:04X},S'),
    (30, f"FORI=0TO16:VPOKE&H{VRAM_START:04X}+I,&H{WIPE_BYTE:02X}:NEXT"),
    (40, 'BLOAD"A:SV.SC",S'),
    (50, f"FORI=0TO16:POKE&H{MIRROR:04X}+I,VPEEK(&H{VRAM_START:04X}+I):NEXT"),
    (60, f"POKE&H{DONE_ADDR:04X},&H{DONE_BYTE:02X}"),
]

# Reproduced in Python: byte[i] = (i*3+7) & 0xFF for i in 0..16 -- position-
# varying (not all-equal), matches line 10's `I*3+7` formula exactly. None of the
# 17 values equals WIPE_BYTE ($A5), so a stuck wipe is distinguishable from a
# correct restore.
PATTERN = bytes(((i * 3 + 7) & 0xFF) for i in range(VRAM_END - VRAM_START + 1))
assert WIPE_BYTE not in PATTERN, "wipe sentinel collides with the pattern"

# --- SV.SC on-disk BSAVE layout: $FE, start, end, exec (all LE), then the raw
# data bytes [start..end] inclusive. For a ",S" save the addresses are VRAM.
BSAVE_ID = 0xFE


def autoexec_disk_file() -> bytes:
    """The tokenised AUTOEXEC.BAS disk file (our own ROM crunch, not hand-built
    token bytes -- see bas_tokenise.py)."""
    return make_basic_file(AUTOEXEC_LINES, TXTBASE)


def build_disk() -> str:
    """A fresh /tmp FAT12 image whose only file is our tokenised AUTOEXEC.BAS."""
    img = Fat12Image()
    img.add_file("AUTOEXEC", "BAS", autoexec_disk_file())
    fd, path = tempfile.mkstemp(suffix=".dsk", prefix="vram_saveload_probe_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(img.finish())
    return path


# --- offline FAT12 parse of the resulting .dsk (public Microsoft FAT spec) ----
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
    truncated to the directory-entry file size (independent of BLOAD)."""
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
    first_sec = bpb["data_start"] + (first_cluster - 2) * bpb["spc"]
    raw = img[first_sec * bpb["bps"]: first_sec * bpb["bps"] + clus_bytes]
    return raw[:size]


def parse_bsave(payload: bytes) -> tuple[int, int, int, bytes]:
    """[$FE][start][end][exec][data...] -> (start, end, exec, data)."""
    assert payload[0] == BSAVE_ID, f"not a BSAVE file: id=${payload[0]:02X}"
    start, end, exec_ = struct.unpack("<HHH", payload[1:7])
    data = payload[7:7 + (end - start + 1)]
    return start, end, exec_, data


# --- boot + capture (zero typed input; poison-then-settle) --------------------
def cold_boot_and_capture(machine: str, dsk: str, out_path: str,
                          timeout: float = 60.0) -> dict:
    tcl = f"""set throttle off
set renderer none
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc poison {{}} {{
  debug write memory 0x{DONE_ADDR:04X} 0x{DONE_POISON:02X}
}}
after time 1 {{ poison }}
proc cap {{}} {{
  set f [open {{{out_path}}} w]
  puts $f "done=[format %02X [debug read memory 0x{DONE_ADDR:04X}]]"
  puts $f "region=[__hex 0x{MIRROR:04X} {VRAM_END - VRAM_START + 1}]"
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
    VRAM-mirror fidelity + on-disk artifact. Returns (all_ok, report_text)."""
    dsk = build_disk()
    lines = []
    try:
        cap = cold_boot_and_capture(machine, dsk, f"/tmp/vram_saveload_{label}.txt")
        done = int(cap["done"], 16)
        region = bytes.fromhex(cap["region"])

        # VACUITY GUARD: the .bas program must have run to completion.
        r_done = done == DONE_BYTE
        lines.append(f"  [{'PASS' if r_done else 'FAIL'}] done-guard: "
                     f"(${DONE_ADDR:04X})=${done:02X} (expect ${DONE_BYTE:02X} -- "
                     f"program ran to completion, poisoned ${DONE_POISON:02X} pre-boot)")

        # VRAM mirror: BLOAD",S" load-path fidelity (region was wiped to $A5 in VRAM).
        r_ram = region == PATTERN
        lines.append(f"  [{'PASS' if r_ram else 'FAIL'}] VRAM [{VRAM_START:04X}..{VRAM_END:04X}] "
                     f"after BLOAD\",S\" = {'the saved pattern' if r_ram else 'DIFFERS'} "
                     f"(via VPEEK mirror at ${MIRROR:04X})")
        if not r_ram:
            lines.append(f"        got {region.hex()}\n        exp {PATTERN.hex()}")

        # On-disk artifact: SV.SC's BSAVE",S" payload independent of BLOAD.
        sv = read_file_from_dsk(dsk, "SV", "SC")
        r_artifact = False
        if sv is None:
            lines.append("  [FAIL] on-disk SV.SC: not found in root directory")
        else:
            try:
                start, end, exec_, data = parse_bsave(sv)
                r_artifact = (start == VRAM_START and end == VRAM_END and data == PATTERN)
                lines.append(f"  [{'PASS' if r_artifact else 'FAIL'}] on-disk SV.SC "
                             f"BSAVE\",S\" payload (start=${start:04X} end=${end:04X}) "
                             f"{'matches' if r_artifact else 'DIFFERS from'} the VRAM pattern")
                if not r_artifact:
                    lines.append(f"        got {data.hex()}\n        exp {PATTERN.hex()}")
            except Exception as e:
                lines.append(f"  [FAIL] on-disk SV.SC: malformed BSAVE payload ({e})")
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

    ok = True

    print(f"AUTOEXEC.BAS BSAVE\"A:SV.SC\",&H{VRAM_START:04X},&H{VRAM_END:04X},S  ->  "
          f"BLOAD\"A:SV.SC\",S  (VRAM round-trip, cold-boot auto-run, zero typed input)")
    print(f"pattern: byte[i] = (i*3+7) & 0xFF, i=0..16 -> {PATTERN.hex()}")

    print(f"\n[ours: {args.ours_machine}]")
    r_ours, rep_ours = run_one(args.ours_machine, "ours")
    print(rep_ours)
    ok = ok and r_ours

    print(f"\n[STOCK reference: {args.ref_machine}] (CF-3300 differential)")
    r_ref, rep_ref = run_one(args.ref_machine, "ref")
    print(rep_ref)
    ok = ok and r_ref

    print("\n" + ("ALL PASS -- BSAVE\",S\"/BLOAD\",S\" VRAM round-trip via .bas-on-disk "
                  "auto-run matches the National_CF-3300 stock reference (VRAM load-path "
                  "AND on-disk save-path both fidelity-checked)"
                  if ok else "FAIL -- see per-check results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
