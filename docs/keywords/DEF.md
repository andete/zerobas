<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DEF` — the start of `DEF FN` and `DEF USR`

> **Status (2026-10-09):** `DEF` has no form of its own; it only ever starts
> `DEF FN` or `DEF USR`, and each is tracked and documented as that statement.

## Summary

`DEF` defines something for later use: a one-line function (`DEF FN`) or the
address of a machine-code routine (`DEF USR`). Typed alone it is
`Syntax error` on both machines (the example below).

| statement | what it does | page |
|---|---|---|
| `DEF FNA(X)=X*X+1` | define a function, called later as `FNA(3)` | [`FN`](FN.md) |
| `DEF USR3=&HD000` | store a routine's address, called later as `USR3(n)` | [`USR`](USR.md) |

`DEFINT`, `DEFSNG`, `DEFDBL` and `DEFSTR` look related but are keywords of
their own, each a single word, which give variables a type by their first
letter: [`DEFINT`](DEFINT.md), [`DEFSNG`](DEFSNG.md), [`DEFDBL`](DEFDBL.md),
[`DEFSTR`](DEFSTR.md).

## Example

```
10 ON ERROR GOTO 50
20 DEF FNA(X)=X*X+1:PRINT FNA(3)
30 DEF
40 END
50 PRINT "Error";ERR:RESUME NEXT
RUN
 10
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_def.out`](../../scratchpad/kwdoc_def.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)). More on each
statement: [`FN`](FN.md), [`USR`](USR.md).

## Differences from the reference

The open items filed against `DEF` all belong to one of its two statements,
and are described on those pages: a `DEF FN` whose parameter is not a variable
name (`DEF FNA(5)=1`) is accepted here, two parameters of one call can share
a value ([`FN`](FN.md)), and `DEF USR` accepts an address past 65535
([`USR`](USR.md)).
