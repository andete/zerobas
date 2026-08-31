#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Cassette ASCII LOAD timing probe — the inter-block leader IS the CPU budget.

Diagnostic instrument for the multi-block `LOAD"CAS:"` truncation logged in
disk/docs/tier2-review-queue.md. It answers, per data block, one question:

    did the tokenise+store of the block we just read finish before the NEXT
    block's data started?

WHY THIS EXISTS (the thing the failure looks like, and isn't). Cassette read is
real-time: during a block's 256 data bytes the CPU is pinned inside
`cal_refill`'s tight TAPIN*256 loop, so the ONLY CPU time available for
`ascii_read_lines` is the leader that precedes the next block. Overrun it and
`cal_refill`'s TAPION runs after the next block's data has already begun -- and
**TAPION returns CF=0**, false-locking on high-frequency cycles inside the data.
Nothing errors at the lock; the first TAPIN grinds to the end of that block and
only then fails. The visible symptom is a clean truncation at an exact block
boundary with no error for ~2.4 s, which reads like a format bug and is not one.

WHAT IT MEASURES, AND WHY IT IS TRUSTWORTHY

  * The BUDGET comes from the tape, not from us: the recorded WAV is decoded to
    byte-level timestamps (probes/lib/cas_decode.py primitives) and the leader is
    the measured gap between one block's last byte and the next block's first.
  * The SPEND comes from the BIOS tape entries -- TAPION ($00E1) / TAPIN ($00E4)
    -- which sit at the SAME addresses on the lean cart and on a merged/repack
    machine. One harness, no symbol file, both sides directly comparable.
  * Both sides run the SAME cached WAV, so the read path is the only variable.

  ⚠️ openMSX breakpoints are ADDRESS-ONLY. The sub-ROM shares page-1 addresses
  with resident BASIC, so a bp on a page-1 address MUST carry `[pc_in_slot 0]`
  or sub-ROM code trips it -- the first cut of this instrument had `le_tok_skip`
  (sub $68E6) masquerading as `cal_fill_fail` (resident $68E6) and produced a
  confident, entirely fictional "TAPIN short read" trace. The BIOS entries used
  here are page-0 and unambiguous; `--symbols` adds the page-1 attribution
  breakpoints and slot-qualifies every one of them.

IT IS A THRESHOLD, NOT A BUILD PROPERTY. `store_line`'s insert walk is O(lines)
per line, so the per-block window cost GROWS with the program already stored --
which is why `--lines` is the interesting knob and why a green multi-block case
only proves the fixture was small enough. Measured 2026-07-26: lean cart 20.1 ->
36.7 ms/line, failing at block 4 of a 90-line program; repack ~2x that per line
(23.58 ms in the tokenise CALSLT alone), failing at block 2 of 40 lines.

    python3 probes/basic/basic_probe_cas_leader_budget.py --lines 90
    python3 probes/basic/basic_probe_cas_leader_budget.py \\
        --machine C-BIOS_MSX1_EU_REPACK_DISK --lines 40 --symbols

Exit status is about the MEASUREMENT, not about the bug: 0 when every block was
measured, 1 when the instrument could not get a reading (no trace, no capture).
The truncation itself is reported, not asserted -- this is a characterisation
probe, and the gate that owns the assertion is basic_probe_tape_save.py.

Clean-room: inputs / outputs and our own recordings only. No disassembly.
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import re
import signal
import subprocess
import tempfile
import time

import cas_decode as CD                                # noqa: E402
import basic_probe_tape_save as TS                     # noqa: E402
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = TS.OMSX
MACHINE_TAPE = TS.MACHINE_TAPE
TXTBASE = TS.TXTBASE

TAPION, TAPIN, TAPIOF = 0x00E1, 0x00E4, 0x00E7


# ---------------------------------------------------------------------------
# The budget: decode the recorded WAV to byte-level timestamps
# ---------------------------------------------------------------------------

def wav_timeline(path: str, gap_s: float = 0.05):
    """[(nbytes, first_byte_t, last_byte_t)] per block, from the signal itself.

    Same edge/threshold primitives cas_decode.decode_file uses, but each decoded
    byte keeps the sample index of its start bit, so the LEADER between two
    blocks is measured rather than assumed. A run of >gap_s with no byte is a
    leader (or the pre-file silence)."""
    s, fr = CD.read_samples(path)
    xs = CD.zero_crossings(s)
    hp = CD.half_periods(xs)
    if not hp:
        return [], 0
    thr = CD.auto_threshold(hp)
    sym = ["L" if h > thr else "S" for h in hp]

    bits, i, n = [], 0, len(sym)
    while i < n:                                  # cas_decode.decode_bits, tagged
        if sym[i] == "L":
            if i + 1 < n and sym[i + 1] == "L":
                bits.append((0, xs[i])); i += 2
            else:
                i += 1
        else:
            if i + 3 < n and sym[i + 1] == sym[i + 2] == sym[i + 3] == "S":
                bits.append((1, xs[i])); i += 4
            else:
                i += 1

    out, i, n = [], 0, len(bits)
    while i < n:                                  # cas_decode.frame_bytes, tagged
        if bits[i][0] != 0:
            i += 1; continue
        if i + 9 > n:
            break
        val = sum(b << k for k, (b, _) in enumerate(bits[i + 1:i + 9]))
        out.append((val, bits[i][1] / fr))
        i += 10
    if not out:
        return [], fr

    blocks, cur = [], [out[0]]
    for prev, nxt in zip(out, out[1:]):
        if nxt[1] - prev[1] > gap_s:
            blocks.append(cur); cur = []
        cur.append(nxt)
    blocks.append(cur)
    return [(len(g), g[0][1], g[-1][1]) for g in blocks], fr


# ---------------------------------------------------------------------------
# The spend: trace the BIOS tape calls through a real LOAD"CAS:"
# ---------------------------------------------------------------------------

def trace_load(machine: str, cart: str, wav: str, want_len: int,
               symbols: str | None, main_slot: str, cap_time: float,
               timeout: float):
    """Run LOAD"CAS:" under breakpoints; return (events, program image).

    events = [(emulated_t, tag)]. With `symbols`, the page-1 attribution points
    (dispatch_line / tokenise trampoline / store_line / cal_refill) are added,
    qualified to primary slot `main_slot` -- on a merged machine the sub-ROM
    lives at the SAME page-1 addresses, so an unqualified bp measures the wrong
    ROM. `main_slot="any"` drops the qualifier, which is correct ONLY on a
    machine with no sub-ROM (the lean cart)."""
    log_fd, log_path = tempfile.mkstemp(suffix=".log", prefix="casbudget_")
    os.close(log_fd)
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="casbudget_")
    os.close(out_fd)

    extra = ""
    if symbols:
        sym = {}
        for line in open(symbols):
            m = re.match(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", line)
            if m:
                sym[m.group(1)] = int(m.group(2), 16)
        missing = [k for k in ("dispatch_line", "store_line", "tokenise",
                               "cal_refill") if k not in sym]
        if missing:
            raise SystemExit(f"{symbols}: missing symbols {missing}")
        # MS = the slot qualifier. Without it the sub-ROM trips these. See the
        # module docstring -- this exact mistake produced a fictional trace.
        qual = "{}" if main_slot == "any" else "{[pc_in_slot %s]}" % main_slot
        extra = "\n".join([
            f"set MS {qual}",
            f"debug set_bp 0x{sym['dispatch_line']:04X} $MS {{ lg dispatch_line }}",
            f"debug set_bp 0x{sym['tokenise']:04X}      $MS {{ lg tokenise }}",
            f"debug set_bp 0x{sym['store_line']:04X}    $MS {{ lg store_line }}",
            f"debug set_bp 0x{sym['cal_refill']:04X}    $MS {{ lg cal_refill }}",
        ])

    tcl = f"""
set throttle off
set lf [open {{{log_path}}} w]
proc lg {{msg}} {{ global lf; puts $lf "[format %.5f [machine_info time]] $msg"; flush $lf }}
debug set_bp 0x{TAPION:04X} {{}} {{ lg TAPION }}
debug set_bp 0x{TAPIN:04X}  {{}} {{ lg TAPIN }}
debug set_bp 0x{TAPIOF:04X} {{}} {{ lg TAPIOF }}
{extra}
proc __hex {{dbg addr len}} {{ binary scan [debug read_block $dbg $addr $len] H* h; return $h }}
after time 6 {{ type {TS._tcl_dquote('load"CAS:"')} }}
after time 8 {{ type {TS._tcl_dquote(chr(13))} }}
proc __cap {{}} {{
  set f [open {{{out_path}}} w]
  puts $f "mem=[__hex {{memory}} {TXTBASE} {want_len}]"
  close $f
  close $::lf
  exit
}}
after time {cap_time} {{ __cap }}
"""
    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="casbudget_")
    os.write(fd, tcl.encode()); os.close(fd)

    args = [OMSX, "-machine", machine]
    if machine == MACHINE_TAPE:
        args += ["-cart", cart]
    args += ["-cassetteplayer", wav, "-command", "set renderer none; set sound_driver null",
             "-script", tcl_path]
    try:
        proc = subprocess.Popen(omsx_preflight.guarded(args), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)

    events = []
    if os.path.exists(log_path):
        for line in open(log_path):
            t, _, tag = line.partition(" ")
            try:
                events.append((float(t), tag.strip()))
            except ValueError:
                pass
        os.unlink(log_path)
    got = None
    if os.path.exists(out_path):
        for line in open(out_path):
            if line.startswith("mem="):
                got = bytes.fromhex(line[4:].strip())
        os.unlink(out_path)
    return events, got


def count_lines(img: bytes) -> list[int]:
    """Line numbers of the stored program image (link/lineno/body/00)."""
    i, out = 0, []
    while i + 1 < len(img) and int.from_bytes(img[i:i + 2], "little") != 0:
        out.append(int.from_bytes(img[i + 2:i + 4], "little"))
        j = i + 4
        while j < len(img) and img[j] != 0:
            j += 1
        i = j + 1
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def report(blocks, events, got, want, symbols_used: bool) -> bool:
    data_blocks = [b for b in blocks if b[0] > 16]
    leaders = [b[1] - a[2] for a, b in zip(blocks, blocks[1:])]
    leader = min(leaders) if leaders else None
    print("\n-- tape geometry (measured from the recording) --")
    for k, (n, t0, t1) in enumerate(blocks):
        lead = f"   leader before = {blocks[k][1] - blocks[k-1][2]:.3f}s" if k else ""
        print(f"   block {k}: {n:4d} bytes  {t0:7.3f}..{t1:7.3f}s ({t1-t0:.3f}s){lead}")
    if leader is None:
        print("   !! fewer than two blocks -- nothing to time")
        return False
    print(f"   -> per-block CPU budget (shortest leader) = {leader:.3f}s")

    print("\n-- LOAD\"CAS:\" spend (BIOS TAPION/TAPIN trace) --")
    tape = [(t, tag) for t, tag in events if tag in ("TAPION", "TAPIN", "TAPIOF")]
    if not tape:
        print("   !! no BIOS tape calls traced")
        return False
    i, blk, last_end, verdicts, attributed = 0, 0, None, [], True
    while i < len(tape):
        t, tag = tape[i]
        if tag != "TAPION":
            i += 1; continue
        j, n = i + 1, 0
        while j < len(tape) and tape[j][1] == "TAPIN":
            n += 1; j += 1
        note = ""
        if last_end is not None:
            gap = t - last_end
            ok = gap <= leader
            verdicts.append((blk, ok))
            note = (f"   window={gap:.4f}s  "
                    f"{'FITS' if ok else 'OVERRUN'} vs {leader:.3f}s"
                    f"  ({100*gap/leader:.0f}% of budget)")
        print(f"   block {blk}: TAPION @{t:8.4f}  {n:4d} TAPIN{note}")
        if n:
            last_end = tape[j - 1][0]
        blk += 1
        i = j

    if symbols_used:
        per = [t for t, tag in events if tag == "dispatch_line"]
        print("\n-- per-line cost (page-1 attribution) --")
        if len(per) < 3:
            # NOT a soft miss. The tape trace above still fired, so the machine
            # ran fine -- a silent empty attribution means the .sym does not
            # describe the ROM this machine actually boots, and every number
            # derived from it would be fiction. Verified the hard way: a --sym
            # and a merged ROM with matching mtimes were still a stale pair
            # (dispatch_line's address did not execute even UNCONDITIONALLY).
            print(f"   !! {len(per)} dispatch_line hits -- the symbol file does NOT"
                  f" match the ROM this machine boots.\n"
                  f"      Rebuild the pair and re-run; do not read the timings"
                  f" above as attributed.")
            attributed = False
        else:
            # Only gaps INSIDE a tokenise window are per-line costs. A larger
            # gap spans a 2.4 s block fill (or the REPL's own `load"CAS:"`
            # line, which is a dispatch_line too and would otherwise be
            # reported as a 5-second first line).
            gaps = [b - a for a, b in zip(per, per[1:]) if b - a <= leader]
            if gaps:
                print(f"   {len(gaps)} lines timed in-window: "
                      f"first={gaps[0]*1000:.2f}ms  last={gaps[-1]*1000:.2f}ms  "
                      f"mean={sum(gaps)/len(gaps)*1000:.2f}ms")
                print("   (the growth across them is store_line's O(lines) "
                      "insert walk -- this is what moves the threshold)")

    print("\n-- result --")
    if got is None:
        print("   !! no program capture")
        return False
    lines = count_lines(got)
    exact = got == want
    print(f"   stored lines = {len(lines)}"
          + (f" (last {lines[-1]})" if lines else "")
          + f"   round-trip exact = {exact}")
    bad = [b for b, ok in verdicts if not ok]
    if bad:
        print(f"   TRUNCATED at block {bad[0]}: the leader window before it was "
              f"overrun, so TAPION false-locked inside that block's data.")
    elif not exact:
        print("   every window FITS -- the truncation is NOT this mechanism.")
    return attributed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lines", type=int, default=40,
                    help="lines in the generated program (default 40; the "
                         "threshold knob -- 90 breaks the lean cart too)")
    ap.add_argument("--cart", default=None,
                    help="zerobas basic.rom (ignored when --machine names a "
                         "machine whose built-in ROM is already zerobas)")
    ap.add_argument("--machine", default=None,
                    help=f"run the zerobas side on this machine instead of the "
                         f"lean cart on {MACHINE_TAPE}; also $ZEROBAS_BASIC_MACHINE")
    ap.add_argument("--symbols", nargs="?", const="build/basic-reloc.sym",
                    help="add slot-qualified page-1 attribution breakpoints from "
                         "this pasmo .sym (default build/basic-reloc.sym)")
    ap.add_argument("--main-slot", default=None,
                    help="primary slot holding zerobas BASIC, for the --symbols "
                         "breakpoints (default: 0 on a merged machine, 'any' on "
                         "the lean cart machine, which has no sub-ROM to confuse "
                         "an address-only breakpoint)")
    ap.add_argument("--wav", help="reuse a previously recorded WAV (skips SAVE)")
    ap.add_argument("--keep-wav", help="write the recorded WAV here and keep it")
    args = ap.parse_args()

    machine = args.machine or os.environ.get("ZEROBAS_BASIC_MACHINE") or MACHINE_TAPE
    TS.ZB_MACHINE = machine
    # 🔴 THE TAPE RIG NEEDS A CART, AND THE LEAN ONE IS RETIRED. This probe's
    # default machine is MACHINE_TAPE, which carries no BASIC -- so without
    # `--cart` it used to hand openMSX a literal `None` and the preflight
    # reported `MISSING None`, an accurate refusal with a useless name in it.
    # The cart it was written for is `build/basic.rom`, removed by
    # docs/spec-lean-retire-s1..s3 ("there is no `build/basic.rom` rule any
    # more"), so a bare run can no longer work at all and should say WHY.
    # Found 2026-08-31 by D-PROBEREACH4, the third probe with this shape after
    # basic_probe_cas_verify and basic_probe_cas_match -- all three invisible
    # because no `make` target runs them.
    if machine == MACHINE_TAPE and not args.cart:
        print(f"no cart for {machine}: that rig carries no BASIC, so it needs "
              f"--cart. The lean 16 KB cart this probe was written for is "
              f"RETIRED (docs/spec-lean-retire-s1..s3); pass a cartridge "
              f"explicitly, or --machine C-BIOS_MSX1_EU_REPACK_DISK to run "
              f"against the merged build instead.")
        return 2
    # The qualifier exists to keep the sub-ROM out of page-1 breakpoints; the
    # lean cart machine has no sub-ROM (and its cart is not in slot 0 anyway).
    main_slot = args.main_slot or ("any" if machine == MACHINE_TAPE else "0")
    print(f"cassette leader-budget probe: {args.lines} lines on {machine}"
          + (f"  -cart {args.cart}" if machine == MACHINE_TAPE else "  (built-in ROM)"))

    program = TS.build_program_n(args.lines)
    want = TS.expected_relinked_image(program)

    wav, tmp_wav = args.wav, None
    if wav is None:
        wav = args.keep_wav
        if wav is None:
            fd, tmp_wav = tempfile.mkstemp(suffix=".wav", prefix="casbudget_")
            os.close(fd)
            wav = tmp_wav
        # SAVE side: inject the program, SAVE"CAS:",A, record. The write side is
        # not under test here (basic_probe_tape_save.py owns that) -- this only
        # needs a well-formed multi-block tape.
        pre = [(5.0, f"debug write_block memory 0x{TXTBASE:04X} "
                     f"[binary decode hex {program.hex()}]")]
        cmds = [(7.0, 'save"CAS:MB",A'), (9.0, "\r")]
        secs = 30.0 + 0.9 * args.lines
        TS.run_save(args.cart, cmds, wav, cap_time=secs, timeout=2.5 * secs,
                    pre_cmds=pre)
        if not os.path.exists(wav) or os.path.getsize(wav) == 0:
            print("!! no WAV recorded -- the SAVE side failed, nothing to time")
            return 1

    try:
        blocks, _ = wav_timeline(wav)
        cap = 20.0 + 4.0 * max(1, len([b for b in blocks if b[0] > 16]))
        events, got = trace_load(machine, args.cart, wav, len(want),
                                 args.symbols, main_slot,
                                 cap_time=cap, timeout=3.0 * cap)
        ok = report(blocks, events, got, want, bool(args.symbols))
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            os.unlink(tmp_wav)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
