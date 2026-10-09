<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# About the keyword pages

← [Keyword pages](README.md)

The rest of `docs/` is mostly the working record the findings came from —
probe notes, specifications, characterisations; these pages are the distilled
result. This page is for people who maintain them.

## The rules

- **A keyword gets a page once it reaches level 3**: the happy path, a
  reasonable time and the common errors are all proven. Below that its
  behaviour is still moving. When a page's own checking finds a happy-path
  difference, the keyword drops below level 3 and its page stays, saying so
  in its status line (`READ` and `DATA` on 2026-10-09, until D-READFLT
  was fixed the same day; `FILES`).
- **A page changes only when an error at a lower tier is found and fixed**, or
  when a ruling changes what the keyword should do. It is not a log.
- **No speed figures** until on-par speed is established for every keyword.
- **Every example is run on zerobas and on the reference**, and the page shows
  what both printed: [`scratchpad/kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)
  reads each page's `<!-- example: … -->` line and its `## Example` block, types
  the program on both machines and compares the screens. Six examples need
  hardware the check cannot drive (a cassette, a printer, `AUTO`'s line entry);
  those pages say so and name the gate that covers them instead.
- **Each page has the same sections:** status, summary, syntax, details,
  example, differences from the reference, what we found and how, where it
  lives, and the tests that cover it.


## The status line

The status line names the rungs of the per-keyword ladder in
[`docs/tier-status.md`](../tier-status.md), which is generated from
measurements: the happy path (T1), a reasonable time (T2), the common errors
(T3), RAM usage (T4) and every error (T6). A keyword's level is its unbroken
run of proven rungs from T1. Speed (T5) is left out on purpose.

## The example check

Each page's first comment line tells the checker how to run its example:

```
<!-- example: reference=VG-8020 disk=no -->
<!-- example: reference=CF-3300 disk=yes run=LIST answers="5|JOOST" wait=12 -->
<!-- example: verify=no reason="needs a cassette" -->
```

`python3 -u scratchpad/kwdoc_examples.py [--dir DIR] [--write] [KEYWORD …]`
types the `## Example` block on both machines (each typed line at most 39
characters; disk examples on a copy of `disk/test720.dsk`) and compares both
screens with each other and with the page. Each run's screens are kept as
`scratchpad/kwdoc_<keyword>.out`, which the page links to.
