#!/usr/bin/env python3
"""D-CASRBRK doc edits, anchored on text; refuses a missing or non-unique anchor."""
import re, sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

def status(path):
    s = open(path).read()
    s2, n = re.subn(r"> \*\*Status \(2026-10-\d\d\):\*\*", "> **Status (2026-10-11):**", s, count=1)
    if n != 1:
        sys.exit(f"REFUSE {path}: no status line")
    open(path, "w").write(s2)
    print(f"ok {path} (status)")

COMMON = ("- **Ctrl-STOP could not break a tape read once the file was found** (fixed\n"
          "  2026-10-11, D-CASRBRK). The VG-8020 stops the read and says `Device I/O\n"
          "  error` (19); zerobas read on to the end, because its cassette routines\n"
          "  never looked at the keyboard after the search\n"
          "  ([`casrbrk_diag.out`](../../scratchpad/casrbrk_diag.out)).\n")
FOUND = {
    "LOAD": COMMON + "  A `LOAD \"CAS:\"` broken that way also kept the lines read so far,\n"
                     "  silently. The program is gone from `Found:` on, as on the VG-8020, so the\n"
                     "  error has no handler left and no line number.\n",
    "CLOAD": COMMON,
    "BLOAD": COMMON + "  Broken in the six bytes that give the load addresses, `BLOAD` read\n"
                      "  garbage for them and loaded the tape over the wrong memory — the screen\n"
                      "  came back as noise. Under `ON ERROR` the VG-8020 raises 19 in the line.\n",
    "MERGE": COMMON + "  The lines read before the break were merged and nothing was said.\n",
    "INPUT": ("- **`INPUT #` / `LINE INPUT #` from a tape channel broken with Ctrl-STOP said\n"
              "  `Input past end`** (fixed 2026-10-11, D-CASRBRK). The VG-8020 raises\n"
              "  `Device I/O error` (19) in the line; zerobas took the cut read for the end\n"
              "  of the file.\n"),
}
for kw, text in FOUND.items():
    p = f"docs/keywords/{kw}.md"
    status(p)
    sub(p, "## What we found, and how\n\n", "## What we found, and how\n\n" + text)
    if kw == "INPUT":
        sub(p, "## Tests that cover it\n\n", "## Tests that cover it\n\n"
            "- `make casrbrk-acceptance` — `LINE INPUT #` from tape broken with Ctrl-STOP.\n")
    else:
        sub(p, "- `make kwram` — the RAM-usage comparison.\n",
            "- `make casrbrk-acceptance` — the tape read broken with Ctrl-STOP, in the\n"
            "  header leader and in the data.\n- `make kwram` — the RAM-usage comparison.\n")

K = "docs/concepts/cassette.md"
sub(K, """**Ctrl-STOP during the search** is `Device I/O error` (19), which an
`ON ERROR` handler can trap, for `LOAD`, `CLOAD`, `RUN`, `MERGE`, `BLOAD` and
`OPEN` alike.
""", """**Ctrl-STOP during the search** is `Device I/O error` (19), which an
`ON ERROR` handler can trap, for `LOAD`, `CLOAD`, `RUN`, `MERGE`, `BLOAD` and
`OPEN` alike. **Once the file is found** it is still 19: `BLOAD` and
`LINE INPUT #` raise it in their line, under `ON ERROR` too; `LOAD`, `CLOAD`
and `MERGE` have already let go of the running program at `Found:`, so the
message is printed with no line and no handler sees it.
""")
sub(K, "- **Ctrl-STOP could not break a tape write either**",
    "- **Ctrl-STOP could not break a tape read once the file was found** (fixed\n"
    "  2026-10-11, D-CASRBRK). Every read verb ran to the end of the data; a\n"
    "  `LOAD` or `MERGE` kept the lines read so far without a word, and a `BLOAD`\n"
    "  broken in its address bytes loaded the tape over the wrong memory\n"
    "  ([`casrbrk_gate.out`](../../scratchpad/casrbrk_gate.out)).\n"
    "- **Ctrl-STOP could not break a tape write either**")
sub(K, """`tapout` frames each byte with two stop bits and, before each byte, asks
`BREAKX` whether Ctrl-STOP is down — if it is, it waits for the key to come
up and returns with carry set; `stmotr` drives the relay.
""", """`tapout` frames each byte with two stop bits; `stmotr` drives the relay.
`tapout` and `tapin` before each byte, and `tapion` on each attempt to lock
on, ask `BREAKX` whether Ctrl-STOP is down; if it is, they wait for the key to
come up and return with carry set (`cas_stop`).
""")
sub(K, "- `make caswbrk-acceptance` — Ctrl-STOP during a write: in the data, in the\n  leader, and held after it broke the write.\n",
    "- `make caswbrk-acceptance` — Ctrl-STOP during a write: in the data, in the\n  leader, and held after it broke the write.\n"
    "- `make casrbrk-acceptance` — Ctrl-STOP during a read, in the leader and in\n  the data, for every read verb.\n")
