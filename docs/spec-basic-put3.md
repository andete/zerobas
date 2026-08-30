# D-PUT3 — the third `PUT` of a session hangs, untrappably — and D-RECLEN's straddle premise is refuted

*2026-08-30. Probe `scratchpad/reclen_probe.py`, 15 rows, National CF-3300 vs the
repack. **Measurement only — no code change.** Two findings, one of which was not
the question being asked.*

## 0. What this set out to do

`TODO.md`'s D-RECLEN item records that `OPEN"TS.DAT"AS #1 LEN=100` is
`Syntax error` on zerobas and `OK` on the CF-3300, because `oo_parse_reclen`
([`basic/files.asm`](basic/files.asm)) requires a power of two in 1..256 *"so
records tile the 512-byte sector with no straddle"*. The item names its own next
step and warns against the shortcut:

> *the straddle argument is a REAL design constraint, so "just widen the
> validator" is exactly the cheap wrong answer — what the reference DOES with a
> straddling record is unmeasured, and `GET`/`PUT` round-trip rows come before
> any byte.*

These are those rows. **The premise did not survive them, and a worse defect
turned up on the way.**

## 1. 🔴 The finding nobody was looking for: the third `PUT` hangs

| row | CF-3300 | zerobas |
|---|---|---|
| `p.put1` · `p.put2` — one, two `PUT`s | OK | **OK** |
| `p.put3` — three `PUT`s | OK | **`<NO OUTPUT>`** |
| `p.same3` — three `PUT`s to the **same** record | OK | **`<NO OUTPUT>`** |
| `p.close3` — two, `CLOSE`, reopen, one more | OK | **`<NO OUTPUT>`** |
| `p.trap3` — three, with a reachable `ON ERROR` | OK | **`<NO OUTPUT>`** |
| `p.trap2` — the same shape, one `PUT` shorter | OK | **OK** |

Three facts fall out, and each has its own row rather than an argument:

- 🎯 **It is the `PUT` COUNT and nothing else.** `p.same3` writes record 6 three
  times — same record, same offset, no straddle, no layout question — and dies.
- 🎯 **It is CUMULATIVE ACROSS THE SESSION, not per handle.** `p.close3` closes
  the file and reopens it between the second and third write, and still dies.
  Whatever is being consumed is not released by `CLOSE`.
- 🔴 **It is not a trappable error.** With a handler the interpreter can actually
  reach, `p.trap3` prints nothing at all — no code, no message, the handler never
  runs. `p.trap2` proves the fixture works.

**A random-access write loop is an ordinary MSX BASIC program**, so this outranks
the `LEN=` question it was found under.

⚠️ **`p.trap3`'s first draft measured my own fixture.** It said
`ON ERROR GOTO 100` while the harness numbers statements 10, 20, 30…, so **both**
sides answered `Undefined line number`. The handler has to be the last statement
and the `ON ERROR` has to name its position.

## 1a. 🔴 And the first write-up conflated two rules — the separation, done

Every row in §1 pairs an `LSET A$=STRING$(128,…)` with each `PUT`, so **"the
third `PUT`" and "the third `LSET`" coincided on all of them**. That is two rules
on one row set, and it was filed as fact before being separated.
[[two-rules-that-coincide-on-every-row-you-have]]

| row | zerobas | CF-3300 |
|---|---|---|
| `x.l3p1` — three `LSET`s, **one** `PUT` | OK | OK |
| `x.l3p0` — three `LSET`s, **no** `PUT` | OK | OK |
| `x.l1p3` — one `LSET`, **three** `PUT`s | **dies** | OK |
| **`x.l0p3` — no `LSET` at all, three `PUT`s** | **dies** | OK |
| `x.l2p2` — two and two | OK | OK |

🟢 **The claim survives and gets sharper.** It is the `PUT`, with no string
handling involved at all, and the reproducer is three statements:

```
OPEN"TS.DAT"AS #1 LEN=128 : FIELD#1,128 AS A$
PUT#1,1 : PUT#1,1 : PUT#1,1
```

⚠️ `x.str3` (three 128-byte string variables, no file at all) answers
`Out of string space` on **both** sides — a fixture limit, identical everywhere,
and not a divergence. It is kept so the next reader does not re-derive it.

## 1b. 🟢 The positive control the "untrappable" claim needed

§1 concluded *"not a trappable error"* from `p.trap3` printing **nothing** with a
handler in place. That is an **absence**, and an absence is exactly what a broken
fixture also looks like — this arc has produced five of those.

| row | zerobas | CF-3300 |
|---|---|---|
| `k.puttrap` — handler, two `PUT`s, then a **known** `ERROR 7` | **`ERR 7 AT 60`** | `ERR 7 AT 60` |
| `k.put3` — the same program, third `PUT` instead of the error | **`<NO OUTPUT>`** | OK |

The handler is **demonstrably armed and live after two `PUT`s**, and the third
`PUT` kills the program anyway. The claim now rests on a live handler rather than
on silence.

⚠️ **AND THE FIXTURE CAVEAT THAT COST A WHOLE PROBE: `MAXFILES=n` DISARMS
`ON ERROR`** — on **both** machines (`k.mfwipes`; `k.mfctl` is the same shape
without it and traps normally). It is correct behaviour, not a divergence. An
earlier run put `MAXFILES=2` between the handler and the subject, got an
untrapped error, and I read it as a finding about the machine.

## 2. The straddle premise, refuted

| row | CF-3300 |
|---|---|
| `s.100.r6` — bytes 500..599, **crosses the 512 boundary** | **BBB** |
| `s.100.r5` / `s.100.r7` — the neighbours of that write | AAA / CCC |
| `s.96.r6` — a second non-tiling length | BBB |
| `s.100.r1` — non-tiling, no straddle | DDD |

Disk BASIC **straddles correctly and damages neither neighbour**. The constraint
`oo_parse_reclen`'s comment asserts is not one the reference has, so the
power-of-two validator is zerobas's own invention and refuses programs the
reference runs.

🔴 **Record 6 is the only row that could have said so.** At `LEN=100` records 1
and 5 lie wholly inside the first sector and would round-trip on an
implementation that cannot straddle at all. A probe that stopped at record 5
would have reported a clean round trip and settled nothing.
[[a-coverage-row-whose-geometry-cannot-reach-the-case]]

⚠️ **This is NOT a licence to widen the validator yet.** What is refuted is the
*stated reason*. `GET`/`PUT` round-trip rows on zerobas at a non-tiling length
cannot be taken while §1 stands — the third write never happens — so zerobas's
own straddling behaviour remains **unmeasured**, and it is what the fix has to be
designed against.

## 3. ⚠️ Why the zerobas column is blind above, and what that cost

The `ctl.128.*` rows exist to prove the round-trip machinery on **both** sides
before any `s.*` row is believed. They read `<NO OUTPUT>` on zerobas — because
they write three records, which is §1. They are therefore **not evidence about
record layout**, and are labelled so in the probe.

🔴 **My first explanation was wrong, and a ladder is what refuted it.** I read the
blind controls as string-pool exhaustion (three 128-byte `LSET` temps against the
default pool) and added `CLEAR 1000`. **Nothing changed.** A rung-per-statement
ladder then showed every step passing alone — `GET#1,6` included — which is what
pointed at the count. Guessing a cause and patching it would have left a
`CLEAR 1000` in the fixture forever, hiding a hang behind an explanation.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

⚠️ **ONE REFERENCE.** Disk BASIC; a diskless VG-8020 cannot express any of this.

## 3a. The characterisation, extended 2026-08-30 — and what still is NOT known

| question | row | answer |
|---|---|---|
| disk ops generally, or `PUT`s? | three `GET`s | **`PUT`s** — three `GET`s are fine |
| does a `GET` between reset it? | `P,P,G,P` | **no** — still dies |
| does `CLOSE` + `CLEAR` reset it? | `P,P,CLOSE,CLEAR,reopen,P` | **no** |
| does the count move with record length? | `LEN=64`, `LEN=128` | **no** — three either way |
| does it need the fixture's existing file? | a file that does not exist yet | **no** — dies the same |
| same record, or different ones? | `1,1,1` and `1,2,3` | **both die** |

So: **the third `PUT` of a run, unconditionally**, with nothing yet found that
resets it.

🔴 **STILL OPEN, AND NAMED RATHER THAN GUESSED: is the count PER-CHANNEL or
GLOBAL?** The row that answers it — four `PUT`s spread two-and-two over two
channels — has not run. Four fixture faults in one sitting is what stopped it,
and the fourth is unresolved: `MAXFILES=2` on its own is **`OK` on both sides**
(measured), so the two-channel fixture fails for some other reason, and until
that is isolated any reading from it would be about my fixture.
⚠️ **Three of the four faults produced a plausible wrong answer rather than an
obvious break** — `ON ERROR GOTO 100` on a harness that numbers 10,20,30…;
`OPEN … AS #2` with the default `MAXFILES=1` (`Bad file number`); and the
two-channel fixture's `Syntax error`. Each looked briefly like a finding.

⚠️ **Also seen, not filed:** `OPEN … LEN=256` answers `Illegal function call` on
zerobas — a power of two inside the validator's stated 1..256 range. Whether the
refusal is the `OPEN` or the `FIELD#1,256` behind it is unmeasured; it belongs
with D-FLDWIDTH's domain rows, not here.

## 4. What comes next

1. **Find what the third `PUT` consumes** — the `CLOSE`-survives clue says a
   cumulative resource, not per-`FCB` state. The path is narrowed but not read:
   `ex_put` ([`basic/field.asm`](basic/field.asm)) is stack-balanced, so the
   subject is inside `fat_rand_put`
   ([`basic/randio-body.inc`](basic/randio-body.inc)) and its chain —
   `frnd_locate`, which extends the cluster chain with `GP_FLAGS=1`, and the
   `fat_dir_update` tail.
2. Only then re-take §2's rows on zerobas at `LEN=100`, and price the validator.
