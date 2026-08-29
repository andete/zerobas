# D-NUMSTR — a string where a numeric factor is required, and the guard the refcache had switched off

*2026-08-29. `basic/expr.asm` (`ev_f_missop`), `probes/lib/omsx_repl.py`
(preflight ordering). Probe `scratchpad/numstr_probe.py`, arms
`scratchpad/numstr_knives.py`.*

**Cost: +6 B of main page 1.** **Rows: 26, DIFF 8 → 2** (2 filed, with the
blocker measured).

## 1. The mirror of D-STRTM

D-STRTM asked what a string-taking verb does with a number. This asks the
reverse — what the numeric evaluator does with a string — because D-STRTM's one
unfixed row was exactly that shape. It found **eight** divergent rows in the core
expression evaluator, in two classes:

| | zerobas | references |
|---|---|---|
| `5+"AB"`, `5-"AB"`, `5*"AB"`, `5/"AB"`, `-"AB"`, `5+LEFT$("AB",1)` | ERR 24 | **ERR 13** |
| `5+`, `5*` | ERR 24 | **ERR 2** |

Both classes land on `ev_f_missop`, reached from `ev_f_var`'s `is_letter`
failure — the one site D-MISSOP created.

## 2. 🔴 D-MISSOP's rule was measured at slots it does not only serve

`ev_f_missop`'s header says both references answer `Missing operand` (24) *"at
every such slot, measured at 16 of them"*. **All sixteen were statement-argument
slots**, and the label serves **every** factor position, expression-internal ones
included. Measured here:

| slot | all three sides |
|---|---|
| `POKE &HE000,` | **24** ✓ |
| `LOCATE ,` | **24** ✓ |
| `POKE ,1` | 2 ✓ |
| `PRINT TAB();1` | 2 ✓ |
| `5+` *(expression-internal)* | **references 2, zerobas 24** ✗ |

So D-MISSOP is right where it was measured, and over-general one layer down.
[[two-rules-that-coincide-on-every-row-you-have]]

⚠️ **I wrote the wrong version of this into the probe's own header before running
it** — *"`5+` really is 24 on all three sides"*. It is not. The claim is deleted
rather than softened. [[a-justification-parenthesis-is-an-unrun-claim]]

## 3. Fixed: the string half

```
                cp      '"'
                jr      z,ev_f_tmm          ; -> ERR 13
                ld      e,FPERR_MISSOP
```

🎯 **And it fixes `5+LEFT$("AB",1)` without touching it.** That row reaches
`ev_ff_strnum`, whose D-LEFTTM arm evaluates the argument numerically — and that
**inner** eval is what lands on the `"` here and deferred 24, which
first-error-wins then kept over the type mismatch. K-NS1 confirms it: cutting
this test moves a row whose code is two layers away.

🔴 **Measured, and worth stating plainly: that row was ERR 2 before D-LEFTTM and
ERR 24 after.** Both wrong, but D-LEFTTM moved it — and no row saw it, because
that slice's probe had no string function nested inside a numeric expression.

⚠️ A literal cannot carry a pending fault, so unlike D-LEFTTM / D-INSTRTM /
D-STRTM there is nothing to evaluate first; `ev_f_defer` is still
first-error-wins, so `(0*(1/0)+1)+"AB"` keeps its Division by zero.

⚠️ **Sited at `ev_f_missop`, not in the dispatch chain, and that is not style.**
Five bytes up there pushed **two** neighbouring `jr` arms out of relative range —
the same thing D-PLAYFN's 5-byte arm did to the ERL arm, written up two screens
above. That chain is at its limit; assume any insertion between it and `ev_f`'s
tail costs +1 B per surviving `jr`. Two had to be widened even from here.

## 4. Filed: the missing-operand half, with its blocker measured

`5+` and `5*` want ERR 2. Changing `ev_f_missop`'s code was tried as an
experiment, not shipped:

| row | with `ld e,4` |
|---|---|
| `5+`, `5*` | **2** ✓ fixed |
| `LOCATE ,` | **24** ✓ held — it has its own `req_operand` guard (D-NGRAM2) |
| `POKE &HE000,` | **2** ✗ broken — POKE *depends* on `ev_f_missop` for its 24 |

So the fix is real but not local: every statement slot that still leans on
`ev_f_missop` needs its own `req_operand` guard first.

### 4.1 The enumeration, run 2026-08-29 — and it prices the item out

Planting `ld e,4` and re-running the full D-MISSOP row set on zerobas gives the
list directly, rather than by reading call sites:

| | slots |
|---|---|
| **Independent** — keep their 24 through the cut | `PLAY`, `PRINT USING`, `WIDTH`, `LOCATE` |
| **Depend** — lose their 24 | `POKE`, `DRAW` (SCREEN 2), `FIELD`, `INPUT#`, `OPEN`, `PRINT#`, and three string-assignment shapes: `A$=`, `A$=+`, `MID$(A$,2)=` |

🎯 **The independent four are exactly D-NGRAM2's own sites.** `req_operand`
already guards LOCATE, PLAY, PRINT USING and SCREEN, and those are precisely the
slots the cut cannot touch — which is a pleasing confirmation that the helper is
the right shape, and the reason the remaining work is *more of it* rather than
something new.

**Price: 6 statement slots × 3 B ≈ 18 B, plus an unpriced route for the three
string-assignment shapes, to correct 2 rows** (`5+`, `5*` — a trailing binary
operator with nothing after it). Against a page 1 that was 343 B free on
2026-08-29 (`make basic-reloc`; do not quote this), that is affordable but a poor
trade, and it puts a rule that took a whole slice to establish back in motion.

⚠️ **That is a judgement about what a scarce page is for, not a measurement** —
so the item is re-marked 🙋 with the price attached rather than taken. The
measuring in front of the decision is done.

## 5. 🔴 The apparatus finding: a warm cache switched the preflight off

`omsx_preflight.guarded()` is applied at the `Popen` call **inside**
`_run_cases_impl`. A fully-cached `run_cases` returns before that — so **the
refcache silently disabled the staleness guard.**

**It bit twice in ten minutes.** A `make repack-machine` failed on an assembler
error; pasmo fails cleanly, leaving the *previous* ROM in place; the cache hit
every row because it keys on the ROM's identity, which had not changed; and the
probe printed a complete, self-consistent, entirely plausible table of the edit
that had just failed to build. It was caught only by happening to read the
build's exit code.

The preflight now runs at `run_cases` entry, ahead of the cache. Falsified both
ways: with a touched source a **fully-cached** run refuses (`rc=2`, `STALE`), and
after a rebuild the same run measures normally (the green control — a guard that
refuses everything is worthless). [[apparatus-is-part-of-the-measurement]]

### 5.1 ⚠️ An attempted follow-up, withdrawn — and the hypothesis behind it was refuted

A follow-up moved the check from `run_cases` **entry** to the cache-**hit** path,
on the theory that the entry placement had broken the full battery: five emulator
units came back `rc=2` at 400–1000 s, and `make gates` runs units in parallel
while several of them mutate tracked sources to self-test, which makes `make -q`
transiently report the ROM STALE.

🔴 **That hypothesis is refuted, and by something that was already true when I
formed it.** The emulator tier forces `ZEROBAS_REFCACHE=0`, so it *never takes
the cached path at all* — neither placement can affect it. Moving the check could
not have caused those failures and did not fix them: the next battery failed the
same way.

**The actual cause was host CPU starvation**, and the apparatus says so in its own
words:

> the stall watchdog killed it after 989 s wall … a host-clock deadline CANNOT
> separate a frozen emulator from one starved of CPU … check host load before
> calling this REAL

The host was carrying load ~6 from four other users; `math-acceptance` fails in
4 s under that contention and **passes solo**. Two batteries I killed while
diagnosing made it worse.

**The follow-up was withdrawn unshipped that night** — an apparatus change
without a green battery is not evidence of anything — and **re-applied and
validated on 2026-08-30 once the host went quiet: 47/47 green**, three units
flaking and all three adjudicated green on serial retry.

🟢 **That result also confirms the starvation diagnosis rather than assuming it:**
the same change on the same tree went red under load ~6 and green under load
~2.5. The move itself is justified by **cost, not safety** — a miss goes on to
`Popen`, which is already guarded, so an entry check buys no extra cover and adds
a `make -q` to every one of the thousands of `run_cases` calls a batched probe
makes.

🎯 Twice in one evening a plausible causal story survived until it was checked
against a fact already in hand. [[a-justification-parenthesis-is-an-unrun-claim]]

## 6. Falsification

| arm | requires | measured |
|---|---|---|
| K-NS1 | remove the test → all 6 string rows return to 24, D-MISSOP's slots hold | **exactly those 6** |
| K-NS2 | same test, `ev_f_empty` instead → the same 6 go to 2 | **exactly those 6** |
| preflight | a cached run on a stale ROM refuses; a fresh one measures | ✅ both |

Two arms over one row set on purpose: K-NS1 says the site is **reached**, K-NS2
says 13 was **chosen** rather than inherited. And what must *not* move is half
the point — `k.poke` and `k.locate` come through this very label and held at 24
under both cuts.
