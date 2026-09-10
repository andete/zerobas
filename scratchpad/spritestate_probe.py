#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SPRSTATE — read SPRITE's trap STATE across a `CLEAR`, from the DEBUGGER.

TODO.md's trap-coverage entry closed its conversion 4 of 4 and left exactly one
thing open, twice refusing to guess it:

    "`CLEAR` WIPES THE ENTRY TO OFF AND ZEROES BOTH COUNTERS [for KEY and
     STRIG] ... SPRITE re-fires 250x through the same `CLEAR`, so its entry is
     NOT left OFF: the verbs differ at the level of STATE.
     ⚠️ THE MECHANISM FOR SPRITE IS STILL NOT ESTABLISHED AND STILL NOT GUESSED
     AT. Its state cannot be read the same way: the re-enabled trap fires once
     per frame and the program STARVES before any reporting line."

\U0001f3af SO STOP ASKING THE GUEST. D-TRAPSTATE read `ZTRAP` with BASIC `PEEK`s,
which needs the program to reach a reporting line -- exactly what starvation
prevents. openMSX's own debugger has no such problem, and
`basic_probe_sprite_trap` already reads memory that way (`debug read_block
memory`). A self-rescheduling `after time` dump samples the trap table on the
EMULATED clock no matter what the guest is doing, so the starvation that blocked
the measurement is invisible to the instrument.

\U0001f534 AND THE INJECTION IS IMPORTED, NOT INVENTED. A first cut drove this
through `omsx_repl.run_cases` with a hand-picked `step`, and the harness refused
it outright: "boot-per-case delivery was mangled; nothing was measured" -- the
machine stored 201, 305, 4010 where 20, 30, 40 were typed, because the screen
editor rejected the mangled echoes. `basic_probe_sprite_trap`'s `_INJECT_TCL`,
`_schedule` and `_launch` already deliver this exact program correctly, so they
are reused verbatim, the same discipline the STOP conversion used ("imported, not
copied -- a second copy would sit outside `make latch-check`").

The dump is a SEQUENCE, not a single reading, and that is deliberate: scheduling
one sample at the right instant would need the `CLEAR` to land at a predicted
emulated time, which is exactly the kind of timing assumption this tree keeps
paying for. Sampling every 2 emulated seconds shows the entry BEFORE the `CLEAR`,
across it, and after -- so the transition is read rather than timed.

⚠️ WHAT THIS CAN AND CANNOT SETTLE. It observes the STATE; it does not explain
WHY the state is what it is. If SPRITE's entry survives the `CLEAR` where KEY's
is wiped, that is a reading about the entry, and the cause is then a question for
the CODE -- not something to infer from this table
[[a-mechanism-inferred-from-one-observation]].

State bits (basic/sysvars.inc:1225): 1-0 = 00 OFF / 01 ON / 10 STOP(user) /
11 SERVICING; bit 7 = PENDING. Entry order: 0 INTERVAL, 1 STOP, 2 SPRITE,
3..7 STRIG 0..4, 8..17 KEY 1..10.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_sprite_trap as SP                              # noqa: E402
import probe_sides                                                # noqa: E402
import probe_tmp                                                  # noqa: E402
import clrtrapstk_sprite_probe as S                                     # noqa: E402

ZTRAP, ENTSZ, NENT = 0xE1D1, 3, 18
TRAPENA, TRAPSVC = 0xE20B, 0xE20C
# \U0001f3af THE FIRE COUNTER, SAMPLED BESIDE THE STATE. The first cut dumped the
# trap table alone and showed the entry OFF with both counters zero -- while the
# 2x2 says the handler ran 250 times. Those two readings cannot be placed against
# each other without a common clock, so `$D000` (the handler's own counter, per
# basic_probe_sprite_trap) is now in every row. WHEN the fires happen relative to
# the `CLEAR` is the whole question, and only a shared time series can answer it.
CNT = 0xD000
ZTI_SPRITE = 2
NAMES = (["INTERVAL", "STOP", "SPRITE"]
         + [f"STRIG{n}" for n in range(5)] + [f"KEY{n}" for n in range(1, 11)])
STATE = {0: "OFF", 1: "ON", 2: "STOP", 3: "SERVICING"}


def dump_proc(path: str, every: float = 2.0) -> str:
    """Raw Tcl: a self-rescheduling debugger-side dump of the whole trap table.

    Mirrors the heartbeat's shape (`omsx_repl` HB_*): write, then re-arm. It uses
    `after time` (EMULATED seconds) rather than `after realtime`, because the
    subject is what the machine has done, not how long the host took.
    """
    addrs = " ".join(str(ZTRAP + ENTSZ * i) for i in range(NENT))
    return (
        f"proc zbtrapdump {{}} {{\n"
        f"  set f [open {{{path}}} a]\n"
        f"  set row {{}}\n"
        f"  foreach a {{{addrs}}} {{ lappend row [debug read memory $a] }}\n"
        f"  puts $f \"[machine_info time] [debug read memory {TRAPENA}]"
        f" [debug read memory {TRAPSVC}] [debug read memory {CNT}] $row\"\n"
        f"  close $f\n"
        f"  after time {every:g} zbtrapdump\n"
        f"}}")


def read_dump(path: str):
    rows = []
    if not os.path.exists(path):
        return rows
    for ln in open(path, errors="replace"):
        f = ln.split()
        if len(f) < 4 + NENT:
            continue
        rows.append((float(f[0]), int(f[1]), int(f[2]), int(f[3]),
                     [int(x) for x in f[4:4 + NENT]]))
    return rows


def face(st: int) -> str:
    return STATE[st & 3] + ("+PEND" if st & 0x80 else "")


def run(label: str, do_clear: bool, kill: bool, boot=8.0, step=3.0,
        deadline=600.0, timeout=900):
    """`basic_probe_sprite_trap`'s own injection and schedule, plus our dump."""
    machine = probe_sides.sides("zb")["zb"]["machine"]
    path = probe_tmp.tmp(f"zb_sprstate_{label.replace(' ', '_')}.txt")
    if os.path.exists(path):
        os.unlink(path)
    prog = S.program(do_clear, kill)
    lines = ["set throttle off", dump_proc(path)] + list(SP._INJECT_TCL)
    sched, t = SP._schedule(prog, boot, step)
    lines += sched
    # Start dumping once the program is typed and RUNning, and stop the machine
    # at a bounded emulated instant -- the guest may never finish (that IS the
    # starvation), so the run cannot be allowed to depend on it exiting.
    lines.append(f"after time {t + 1:g} {{ zbtrapdump }}")
    lines.append(f"after time {t + deadline:g} {{ exit }}")
    # \U0001f534 `_launch` OWNS ITS out_path AND `os.unlink`s IT. Handing it our
    # dump path deleted the dump before it could be read, and every row reported
    # "NO DUMP" -- indistinguishable from Tcl that never ran. Diagnosed by
    # running the same Tcl standalone with stderr VISIBLE (`_launch` sends both
    # streams to DEVNULL): it wrote a perfect table, which located the fault in
    # the plumbing rather than the script. Give it a throwaway of its own.
    SP._launch(machine, lines, timeout, probe_tmp.tmp(f"zb_sprstate_sink_{label}"))
    return read_dump(path)


def summarise(label, rows):
    if not rows:
        print(f"  {label:24s} \U0001f534 NO DUMP — the Tcl never wrote; nothing "
              f"is concluded from this row.")
        return None
    # The SPRITE entry's distinct states over the run, in order of first sight,
    # each stamped with the fire count at the moment it was first seen -- so a
    # state and the firing that goes with it are read on ONE clock.
    seq, seen = [], set()
    for t, _, _, cnt, ent in rows:
        f = face(ent[ZTI_SPRITE])
        if f not in seen:
            seen.add(f)
            seq.append(f"{f}@t={t:.0f},cnt={cnt}")
    first_t, _, _, first_cnt, _ = rows[0]
    last_t, ena, svc, cnt, ent = rows[-1]
    others = {NAMES[i]: face(ent[i]) for i in range(NENT)
              if i != ZTI_SPRITE and (ent[i] & 3) != 0}
    print(f"  {label:24s} {len(rows):3d} samples, emulated {first_t:.0f}s.."
          f"{last_t:.0f}s   fires {first_cnt} -> {cnt}")
    print(f"  {'':24s} SPRITE saw: {' -> '.join(seq)}")
    print(f"  {'':24s} final: SPRITE={face(ent[ZTI_SPRITE])}  "
          f"TRAPENA={ena} TRAPSVC={svc}"
          + (f"  other live: {others}" if others else "  (no other entry live)"))
    return ent[ZTI_SPRITE], ena, svc, first_cnt, cnt


def main() -> int:
    print("D-SPRSTATE — SPRITE's trap state across CLEAR, read from the debugger\n")
    out = {}
    for label, do_clear, kill in (("CLEAR, still SERVICING", True, False),
                                  ("no-CLEAR (control)", False, False),
                                  ("CLEAR, trap killed", True, True)):
        out[label] = summarise(label, run(label, do_clear, kill))
        print()
    if out["no-CLEAR (control)"] is None:
        print("\U0001f534 THE CONTROL PRODUCED NO DUMP — the instrument, not the "
              "machine, is what this run measured. Nothing is concluded.")
        return 2
    live = out["CLEAR, still SERVICING"]
    if live is None:
        return 2
    st, ena, svc, first_cnt, cnt = live
    print("\U0001f3af THE READING: after a `CLEAR` taken while the SPRITE trap "
          f"was SERVICING, its entry is **{face(st)}** with TRAPENA={ena}, "
          f"TRAPSVC={svc}.")
    if (st & 3) == 0 and ena == 0 and svc == 0:
        print("   That MATCHES what D-TRAPSTATE read for KEY and STRIG (entry "
              "wiped OFF, both counters zero) — so the divergence is NOT the "
              "entry surviving the CLEAR, and the mechanism lies elsewhere.")
    else:
        print("   KEY and STRIG were left OFF with both counters zero "
              "(D-TRAPSTATE). SPRITE is NOT, which locates the divergence in the "
              "entry's survival across `CLEAR` rather than in the fire count.")
    print(f"\n\U0001f3af AND THE FIRE COUNT IS THE OTHER HALF: the handler had "
          f"already run {first_cnt} time(s) at the FIRST sample and {cnt} by the "
          f"last.")
    if cnt == first_cnt:
        print("   It does not advance while the entry is OFF — so the 250 fires "
              "the 2x2 counted happened BEFORE this window, and the `CLEAR` cell "
              "is not counting post-CLEAR dispatches at all.")
    else:
        print("   It ADVANCES with the entry reading OFF and TRAPENA=0 — which is "
              "the dispatch path the entry cannot explain, and the thing to find "
              "in the code.")
    print("\n⚠️ This observes STATE and COUNT. The CAUSE is a question for the "
          "code and is deliberately not inferred here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
