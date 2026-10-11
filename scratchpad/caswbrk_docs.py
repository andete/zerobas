#!/usr/bin/env python3
"""D-CASWBRK doc edits, anchored on text; refuses a missing or non-unique anchor."""
import sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

FOUND = ("- **Ctrl-STOP could not break a tape write** (fixed 2026-10-11, D-CASWBRK).\n"
         "  On the VG-8020 a `CSAVE`, `BSAVE`, `SAVE` or `PRINT #` to tape broken in its\n"
         "  data raises `Device I/O error` (19) in the line, which `ON ERROR` traps;\n"
         "  zerobas wrote on to the end. The first try at measuring it broke each save\n"
         "  a second in, inside the long leader that opens a file, where the VG-8020\n"
         "  does not look at the keyboard — both machines ran on, which looked like\n"
         "  agreement ([`caswbrk_diag4.out`](../../scratchpad/caswbrk_diag4.out)).\n")

C = "docs/keywords/CSAVE.md"
sub(C, "> **Status (2026-10-09):**", "> **Status (2026-10-11):**")
sub(C, """The one rung not yet proven is **RAM usage**. Not measured: what happens if
the recording is broken with Ctrl-STOP — a try with the current rig gave no
usable reading on either machine.
""", """The one rung not yet proven is **RAM usage**.

**Ctrl-STOP held after it broke the save.** The VG-8020 runs the `ON ERROR`
handler at once and breaks it if the key is still down about 0.7 s later;
zerobas waits for the key to come up and then runs the handler, so a key held
that long does not break it here. A short press gives the same screen on both.
""")
sub(C, "## What we found, and how\n\n- **A tape zerobas wrote could not be loaded",
    "## What we found, and how\n\n" + FOUND + "- **A tape zerobas wrote could not be loaded")
sub(C, "- `make tapetail-acceptance` — the speed and tail errors.\n",
    "- `make tapetail-acceptance` — the speed and tail errors.\n"
    "- `make caswbrk-acceptance` — Ctrl-STOP during the save, typed and under\n"
    "  `ON ERROR`.\n")

B = "docs/keywords/BSAVE.md"
sub(B, "> **Status (2026-10-10):**", "> **Status (2026-10-11):**")
sub(B, "## What we found, and how\n\n- **The clock stopped while the disk worked** (fixed 2026-10-10, D-BLDI):",
    "## What we found, and how\n\n" + FOUND + "\n- **The clock stopped while the disk worked** (fixed 2026-10-10, D-BLDI):")
sub(B, "- `make bsavevar-acceptance` — a variable as the exec address, and `,SX`.\n",
    "- `make bsavevar-acceptance` — a variable as the exec address, and `,SX`.\n"
    "- `make caswbrk-acceptance` — a tape `BSAVE` broken with Ctrl-STOP.\n")

S = "docs/keywords/SAVE.md"
sub(S, "## What we found, and how\n\n- **The clock stopped while the disk worked** (fixed 2026-10-10, D-HOOKDI):",
    "## What we found, and how\n\n" + FOUND +
    "  A tape `SAVE` in a program reports it in line 65535 on the VG-8020, the\n"
    "  direct-mode line, because the save leaves the run before it writes; its\n"
    "  handler is still taken. zerobas does the same now.\n"
    "\n- **The clock stopped while the disk worked** (fixed 2026-10-10, D-HOOKDI):")
sub(S, "- `make cassave-acceptance` — what a cassette `SAVE` writes.\n",
    "- `make cassave-acceptance` — what a cassette `SAVE` writes.\n"
    "- `make caswbrk-acceptance` — a tape `SAVE` broken with Ctrl-STOP.\n")

O = "docs/keywords/OPEN.md"
sub(O, "## What we found, and how\n\n- **`INPUT #` / `LINE INPUT #` from a disk that had gone said `Input past end`**",
    "## What we found, and how\n\n"
    "- **`PRINT #` to a tape channel could not be broken with Ctrl-STOP** (fixed\n"
    "  2026-10-11, D-CASWBRK). The VG-8020 raises `Device I/O error` (19) in the\n"
    "  line when the key lands in a block's data; zerobas wrote every block. See\n"
    "  [`CSAVE`](CSAVE.md) for the measurement.\n"
    "- **`INPUT #` / `LINE INPUT #` from a disk that had gone said `Input past end`**")
sub(O, "- `make castail-acceptance`, `make casprdir-acceptance`,\n  `make nodiskopen-acceptance` — the cassette and the diskless machine.\n",
    "- `make castail-acceptance`, `make casprdir-acceptance`,\n  `make nodiskopen-acceptance` — the cassette and the diskless machine.\n"
    "- `make caswbrk-acceptance` — `PRINT #` to tape broken with Ctrl-STOP.\n")

K = "docs/concepts/cassette.md"
sub(K, """> **Status (2026-10-09):** every measured tape behaviour agrees with the
> VG-8020, and with the CF-3300 where a row was run there too: the recorded
> bytes, the search and its messages, the type filter, Ctrl-STOP. Open: a
> failing tape write and a damaged ASCII program still print `load error`
> instead of raising a code (part of D-LOADERRRET, TIER 3; the references'
> answer there is not measured).""", """> **Status (2026-10-11):** every measured tape behaviour agrees with the
> VG-8020, and with the CF-3300 where a row was run there too: the recorded
> bytes, the search and its messages, the type filter, Ctrl-STOP while
> reading and while writing. Open: a damaged ASCII program still prints `load
> error` instead of raising a code (part of D-LOADERRRET, TIER 3; the
> references' answer there is not measured).""")
sub(K, """**Ctrl-STOP during the search** is `Device I/O error` (19), which an
`ON ERROR` handler can trap, for `LOAD`, `CLOAD`, `RUN`, `MERGE`, `BLOAD` and
`OPEN` alike.
""", """**Ctrl-STOP during the search** is `Device I/O error` (19), which an
`ON ERROR` handler can trap, for `LOAD`, `CLOAD`, `RUN`, `MERGE`, `BLOAD` and
`OPEN` alike.

**Ctrl-STOP during a write** is 19 too, for `CSAVE`, `BSAVE`, `SAVE` and
`PRINT #`, when it lands in the data. In the long leader that opens a file
nothing happens and the save completes, and STOP without CTRL never breaks a
write. A tape `SAVE` in a program reports the error in line 65535, because it
leaves the run before writing; the handler is still taken.
""")
sub(K, """- **A failing tape write, and an ASCII program with a line that has no
  number**, print `load error` here and do not raise a code (part of
  D-LOADERRRET, TIER 3). Ctrl-STOP during a write gave no usable reading on
  either machine with the present rig.
""", """- **An ASCII program with a line that has no number** prints `load error`
  here and does not raise a code (part of D-LOADERRRET, TIER 3).
- **Ctrl-STOP still held after it broke a write.** The VG-8020 runs the
  `ON ERROR` handler at once and breaks it if the key is still down about
  0.7 s later; zerobas waits for the key to come up, then runs the handler,
  which that key no longer breaks. A short press reads the same on both.
""")
sub(K, "- **Ctrl-STOP printed `load error` and the program ran on** (fixed\n  2026-10-08, D-CASBRK); the VG-8020 raises 19.\n",
    "- **Ctrl-STOP printed `load error` and the program ran on** (fixed\n  2026-10-08, D-CASBRK); the VG-8020 raises 19.\n"
    + FOUND.replace("could not break a tape write", "could not break a tape write either"))
sub(K, "`tapout` frames each byte with two stop bits; `stmotr` drives the relay.\n",
    "`tapout` frames each byte with two stop bits and, before each byte, asks\n"
    "`BREAKX` whether Ctrl-STOP is down — if it is, it waits for the key to come\n"
    "up and returns with carry set; `stmotr` drives the relay.\n")
sub(K, "- `make casbrk-acceptance` — Ctrl-STOP during the search, under `ON ERROR`.\n",
    "- `make casbrk-acceptance` — Ctrl-STOP during the search, under `ON ERROR`.\n"
    "- `make caswbrk-acceptance` — Ctrl-STOP during a write: in the data, in the\n"
    "  leader, and held after it broke the write.\n")
