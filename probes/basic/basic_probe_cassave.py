#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-CASSAVE — WHAT FORMAT each cassette SAVE verb actually WRITES.

The residual D-DOTGAPS filed (docs/dotgaps-msx1-characterization.md §3.2):
`SAVE"CAS:name"` writes a TOKENISED ($D3) tape on zerobas and an ASCII ($EA) one
on the reference. On an MSX1 `CSAVE` is the tokenised cassette write and
`SAVE"CAS:"` is the ASCII one, `,A` or not.

🔴 THE SCREEN IS NOT A WITNESS HERE, AND NEITHER IS `.`. Every one of these verbs
prints nothing at all, whatever it writes. D-DOTGAPS found the divergence only
because the FORMAT leaks into a `.` reading -- `SAVE"CAS:E"` writes `.` on both
references and not on zerobas -- and then had to record a WAV and decode it to
learn that the `.` row was a symptom and not the defect. This battery reads the
format DIRECTLY: each row runs on a fresh recording tape (`cassetteplayer new`)
and probes/lib/cas_decode.py turns the WAV back into bytes. Signal edges only,
the same decoder on all three sides, no reference ROM disassembled.

WHAT THE ROWS ASK. Every row is one boot, one recording, and three readings:

  `:id`    the file-type id -- the ten-byte run that opens the header block.
           `EA` = ASCII listing, `D3` = tokenised image, `D0` = binary.
  `:name`  the 6-char, space-padded filename field that follows it.
  `:text`  the printable runs (>= 3 chars) of the DATA block, joined.

  `sav-cas`       `SAVE"CAS:PA"`     -- THE SUBJECT. Reference: `EA`.
  `sav-cas-a`     `SAVE"CAS:PB",A`   -- the same verb WITH the flag.
  `csave`         `CSAVE"PC"`        -- 🟢 THE CONTROL THAT KEEPS THE CLAIM
                                        NARROW: `D3`. Without it, "SAVE"CAS:" is
                                        ASCII" reads as "every cassette save is
                                        ASCII", which is measurably false.
  `sav-cas-bare`  `SAVE"CAS:"`       -- no name: what goes in the name field?

🔴 `:text` IS WHY THE TOKENISED AND ASCII ROWS CAN BE SCORED THE SAME WAY.
A tokenised image cannot be compared byte-for-byte across machines -- its line
LINKS are absolute addresses and TXTTAB differs between a VG-8020, a CF-3300
booting Disk BASIC and zerobas. The printable RUNS do not: `REM`'s argument is
stored verbatim after the `$8F` token, so a tokenised save yields ` ZQ8 / ZQ9`
(the text, without the line numbers) while an ASCII save yields
`10 REM ZQ8 / 20 REM ZQ9` (the whole listing). Both are stable cross-side, and
the DIFFERENCE between them is exactly the format question. The `>= 3` run
threshold is what keeps a stray printable link byte out: line links and line
numbers are 2-byte binary and cannot reach it.

🟢 EVERY ROW CARRIES POSITIVE TEXT, and it has to. `:id` alone is satisfied by a
machine that wrote a header and then died, and `<NO TAPE>` on two dead sides is
not agreement. `:text` must contain ZQ8 and ZQ9 -- proof the PROGRAM reached the
tape -- and `:alive` must contain ZQ6 -- proof the save returned to a prompt.

⚠️ ONE ROW PER `run_cases` CALL, and that is not tidiness. `cassetteplayer new`
is a PROLOGUE, a prologue applies to the whole batch, and it TRUNCATES the file
at every boot -- two recording rows sharing one call would leave one recording on
disk and both rows would read it. Same shape as `basic_probe_lnblank`'s
`tape-save` rows and `basic_probe_castail`'s `cas-openout*` rows.

🟢 THE VG-8020 IS A FULL SIDE. Every MSX1 has a cassette port; the CF-3300 gets a
throwaway disk copy because it boots Disk BASIC, but every verb here is a
main-ROM verb on both.

Clean-room: typed inputs and a decoded recording of the machine's own cassette
output. No reference-ROM disassembly. See CONTRIBUTING.md.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402
import probe_tmp                                                 # noqa: E402
import cas_decode                                                # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
TEST_DSK = os.environ.get("ZEROBAS_TEST_DSK", "disk/test720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=True),
}

# The program every row saves. REM keeps the text VERBATIM in the tokenised image
# (the `$8F` token then the argument bytes), which is what makes `:text`
# comparable between an ASCII save and a tokenised one.
PROG = ['10 REM ZQ8', '20 REM ZQ9']
ALIVE = "ZQ6"

W_SAVE = "@WAIT20"       # a cassette save of a two-line program, leader included

ROWS = 24
COLS = 40

# (label, the SAVE line, the name it should carry)
CASES = [
    ("sav-cas",      'SAVE"CAS:PA"'),
    ("sav-cas-a",    'SAVE"CAS:PB",A'),
    ("csave",        'CSAVE"PC"'),
    ("sav-cas-bare", 'SAVE"CAS:"'),
]

# 🟢 The positive controls. A row whose whole answer is a two-character id is
# satisfied by a machine that wrote ten bytes and stopped; these are the
# readings that say the PROGRAM reached the tape and the verb came back.
CONTROLS = {f"{lab}:text": ("ZQ8", "ZQ9") for lab, _ in CASES}
CONTROLS |= {f"{lab}:alive": (ALIVE,) for lab, _ in CASES}

# The three file-type ids this tree can write, named so a reading is readable.
IDS = {0xEA: "EA", 0xD3: "D3", 0xD0: "D0"}


def printable_runs(blob, minlen=3):
    """Maximal runs of printable ASCII, >= minlen, joined. See the docstring:
    this is what makes a tokenised image comparable across machines whose
    TXTTAB -- and therefore whose line LINKS -- differ."""
    out, cur = [], bytearray()
    for b in blob:
        if 0x20 <= b <= 0x7E:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("ascii"))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(cur.decode("ascii"))
    return " / ".join(out) if out else "<nothing>"


def tape_readback(wav):
    """(id, name, text) as WRITTEN, decoded off the recording.

    Apparatus sentinels all start `<NO ` / `<BAD ` so the scorer's own rule --
    an apparatus sentinel is NEVER agreement -- catches them: two sides that both
    fail to record must not read as a reading they share."""
    if not os.path.exists(wav) or os.path.getsize(wav) < 1024:
        return ("<NO TAPE>",) * 3
    try:
        data, _info = cas_decode.decode_file(wav)
    except Exception as exc:                                # pragma: no cover
        return (f"<BAD WAV {exc}>",) * 3
    blob = bytes(data)
    for byte, name in IDS.items():
        i = blob.find(bytes([byte] * 10))
        if i >= 0:
            j = i + 10
            return name, blob[j:j + 6].decode("latin-1"), printable_runs(blob[j + 6:])
    return ("<NO HEADER>",) * 3


def tail_after(raw, cmdline):
    """What `cmdline` printed: the rows between its echo and the next prompt."""
    if raw is None:
        return "<NO CAPTURE>"
    rows = [raw[r * COLS:(r + 1) * COLS].strip() for r in range(ROWS)][:-1]
    key = cmdline.strip()
    idx = None
    for i, r in enumerate(rows):
        if r == key or r.endswith(key):
            idx = i                                # keep the LAST occurrence
    if idx is None:
        return "<NO ECHO>"
    out = []
    for r in rows[idx + 1:]:
        if any(r == p or r.startswith(p) for p in omsx_repl.PROMPTS):
            break
        if r:
            out.append(r)
    return " / ".join(out) if out else "<nothing>"


def run_row(side, label, saveline, out):
    cfg = SIDES[side]
    kw = {}
    if cfg["diska"]:
        if not os.path.exists(TEST_DSK):
            for k in ("", ":alive", ":id", ":name", ":text"):
                out[f"{label}{k}" if k else label] = "<NO DISK FIXTURE>"
            return out
        dsk = probe_tmp.tmp(f"zb_cassave_{side}_{label}.dsk")
        shutil.copy(TEST_DSK, dsk)
        kw["diska"] = dsk
    wav = os.path.join(tempfile.mkdtemp(prefix=f"zb_cassave_{side}_"),
                       f"{label}.wav")
    lines = list(PROG) + [saveline, W_SAVE, f'PRINT"{ALIVE}"']
    caps = omsx_repl.run_cases(
        cfg["machine"], [("direct", list(cfg["reset"]) + lines)],
        batch=False, reset=(), boot=cfg["boot"], step=cfg["step"],
        prologue=(f"cassetteplayer new {{{wav}}}",), **kw)
    raw = caps[0]
    out[label] = tail_after(raw, saveline)            # the verb prints NOTHING
    out[f"{label}:alive"] = tail_after(raw, f'PRINT"{ALIVE}"')
    fid, name, text = tape_readback(wav)
    out[f"{label}:id"] = fid
    out[f"{label}:name"] = name
    out[f"{label}:text"] = text
    return out


def labels_of(label):
    return [label, f"{label}:id", f"{label}:name", f"{label}:text",
            f"{label}:alive"]


def run_side(side, only):
    out = {}
    for label, saveline in CASES:
        if only and not any(label.startswith(o) for o in only):
            continue
        run_row(side, label, saveline, out)
    return out


# The label pad for every report row this probe prints, on every exit path.
# docs/spec-probe-rowshape.md: ONE grammar, so a knife runner's baseline taken
# on one path can be read against another.
LABEL_W = 20


def main() -> int:
    ap = argparse.ArgumentParser(description="D-CASSAVE")
    ap.add_argument("--sides", default="cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {}
    for s in sides:
        for r in range(a.repeat):
            got = run_side(s, only)
            if r and got != results[s]:
                sys.stderr.write(
                    f"⚠️  {s}: repeat {r + 1} disagrees with repeat 1 -- the "
                    "reading is not stable, so no verdict is possible\n")
                for k in sorted(set(got) | set(results[s])):
                    if got.get(k) != results[s].get(k):
                        sys.stderr.write(
                            f"    {k}: {results[s].get(k)!r} vs {got.get(k)!r}\n")
                return 2
            results[s] = got

    present = [lab for label, _ in CASES for lab in labels_of(label)
               if any(lab in results[s] for s in sides)]

    print("D-CASSAVE — what FORMAT each cassette SAVE verb writes   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    bad = []
    for lab, want in CONTROLS.items():
        for s in sides:
            got = results[s].get(lab)
            if got is None:
                continue
            miss = [w for w in want if w not in got]
            if miss:
                bad.append((lab, s, got, miss))
    if bad:
        for lab, s, got, miss in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {miss} in the reading")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    Every subject row here answers with a TWO-CHARACTER file-type "
              "id, which a\n"
              "    machine that wrote ten bytes and stopped produces for free, "
              "and two sides\n"
              "    that both failed to record agree perfectly on `<NO TAPE>`. "
              "The `:text`\n"
              "    controls are the proof the PROGRAM reached the tape and the "
              "`:alive`\n"
              "    controls the proof the verb returned. Check build/*.rom, "
              "`make\n"
              "    repack-machine`, and that openMSX can WRITE the recording "
              "path. Exit 2\n"
              "    (not 1) = the instrument was broken, NOT a regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    if len(sides) < 2:
        n = 0
        for lab in present:
            for s in sides:
                if lab in results[s]:
                    print(probe_report.row("--", lab, LABEL_W,
                                           {s: results[s][lab]}))
                    n += 1
        print(probe_report.footer(n, 0, "CHARACTERIZATION (one side)"))
        print("=" * 78)
        print(f"{len(present)} reading(s) on {sides[0]} — CHARACTERIZATION, "
              "no agreement verdict is possible from one side")
        if a.gate:
            sys.stderr.write("cassave: --gate needs at least two sides\n")
            return 2
        return 0

    agree = dis = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v.startswith("<NO ") or v.startswith("<BAD ")
               for v in vals.values()):
            ok = False                    # an apparatus sentinel is NEVER agreement
        agree += ok
        dis += not ok
        note = "   [CONTROL]" if lab in CONTROLS else ""
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W,
                               vals, note))
    print(probe_report.footer(len(present), len(present),
                              f"{agree} agree, {dis} diverge"))

    print("=" * 78)
    print(f"{agree}/{agree + dis} readings agree "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls)")
    print("SIDES: vg8020,cf3300,zb — every MSX1 has a CASSETTE PORT, so the "
          "VG-8020 is a full reference here")
    print("READ OFF THE TAPE, not off the screen: every verb here prints "
          "nothing whatever it writes, so each row records to a fresh "
          "`cassetteplayer new` WAV and probes/lib/cas_decode.py decodes it")
    if a.gate and dis:
        sys.stderr.write(f"cassave: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
