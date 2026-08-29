# D-SPCLAMP — `SPACE$`/`STRING$` do not clamp, and never did

*2026-08-29. `scratchpad/spclamp_probe.py` (new), `basic/PROVENANCE.md`.
**No code change: zerobas already agrees with both references at every point.**
14 rows, 0 DIFF.*

## 1. The question

D-STRLONG made string **concatenation** raise `String too long` where it had
silently clamped. `basic/PROVENANCE.md` justified `SPACE$`/`STRING$`'s clamp as
*"identical to the concat/substring STRMAX-clamp philosophy"* — so that cell was
left citing a sibling that had just gone the other way. The item was filed
`UNMEASURED`, with a warning that the cell's own `STRMAX=64` was already stale.

## 2. The measurement

| row | VG-8020 | CF-3300 | zerobas | |
|---|---|---|---|---|
| `LEN(STRING$(300,"A"))` | ERR 5 | ERR 5 | ERR 5 | SAME |
| `LEN(SPACE$(300))` | ERR 5 | ERR 5 | ERR 5 | SAME |
| `LEN(STRING$(256,"A"))` | ERR 5 | ERR 5 | ERR 5 | SAME |
| `LEN(STRING$(-1,"A"))` | ERR 5 | ERR 5 | ERR 5 | SAME |
| `LEN(SPACE$(32768))` | ERR 6 | ERR 6 | ERR 6 | SAME |
| `CLEAR 600 : LEN(STRING$(255,"A"))` | **255** | **255** | **255** | SAME |
| `CLEAR 600 : LEN(SPACE$(255))` | **255** | **255** | **255** | SAME |
| `CLEAR 600 : LEN(STRING$(256,"A"))` | Illegal function call | ″ | ″ | SAME |

**There is no clamp.** Both verbs raise `Illegal function call` past 255, because
the count coerces to a **byte** and 256 is not representable — which is the
*alternative* the filed item flagged as likelier than the clamp story, and it is
the one that is true. Over int16 the answer is `Overflow`, at the earlier stage.

## 3. 🔴 The boundary row agreed for the wrong reason first

At the **default** pool, `LEN(STRING$(255,"A"))` reads `ERR 14`
(`Out of string space`) on all three sides — a pool answer, not a ceiling one.
Left there, the row would have agreed while saying nothing about whether 255 is
representable, and a wrong ceiling could hide behind it. The `CLEAR 600` rows
separate the two, and only they show 255 building.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

⚠️ Incidentally confirmed by the row shape: the `CLEAR 600` rows report the
message text rather than a trapped `ERR n AT 60`, because `CLEAR` clears the
`ON ERROR` trap. Identical on all three sides, so it is a property of BASIC and
not of the harness — said here so a future reader does not read it as a fault.

## 4. What changed

Only the documentation. The `PROVENANCE.md` cell was wrong **twice over**: there
is no clamp, and `STRMAX` has not been 64 since slice-4a widened it. It moves
from **quarantined** (own design) to **sourced** (reference behaviour, measured).

🎯 The item's own framing is the lesson: *"That is not evidence the verbs are
wrong; it is evidence nobody has asked."* Asked, they were right all along — and
the doc that defended them was describing code that no longer existed.
