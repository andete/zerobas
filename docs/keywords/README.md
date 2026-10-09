<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Keyword pages

One page per BASIC keyword, written for a person: what the keyword does, how
zerobas behaves, an example, where it differs from the reference machine, and
what we found out about it along the way. The rest of `docs/` is mostly the
working record those findings came from; these pages are the distilled result.

| keyword | reference | page |
|---|---|---|
| `CHR$` | Philips VG-8020 | [CHR$.md](CHR$.md) |
| `COPY` | National CF-3300 | [COPY.md](COPY.md) |

*(Pilot, 2026-10-09: two pages, to settle the shape before writing the rest.)*

## The rules for these pages

- **A keyword gets a page once it reaches level 3**: the happy path, a
  reasonable time and the common errors are all proven. Below that its
  behaviour is still moving.
- **A page changes only when an error at a lower tier is found and fixed**, or
  when a ruling changes what the keyword should do. It is not a log.
- **No speed figures** until on-par speed is established for every keyword.
- **Every example is run on zerobas and on the reference**, and the page shows
  what both printed: [`scratchpad/kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py).
- **Each page has the same sections:** status, summary, syntax, details,
  example, differences from the reference, what we found and how, where it
  lives, and the tests that cover it.
