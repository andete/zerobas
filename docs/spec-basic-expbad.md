# D-EXPBAD — a malformed exponent marker

*Status: **LANDED 2026-07-31 — 99/99 at `--repeat 2`, −8 B, all sub-ROM,
falsified on five knives.** `KNOWN_DIVERGE` is now **EMPTY**.*

Split out of [D-DECBLANK](spec-basic-decblank.md) on 2026-07-31, where it was
found by the **denominator** and not by the subject: four rows whose divergence
survives with **no blank anywhere**, so it could not be that slice's defect.

Measurement: [`docs/expbad-msx1-characterization.md`](expbad-msx1-characterization.md).
Gate: `make lnblank-acceptance` (`exp` battery new; the four filed rows are
already live as pinned `KNOWN_DIVERGE` entries and **retiring them is part of
this slice** — after which that allowlist is **EMPTY**).

---

## 0. The headline

```
20 A=1EX    ref -> A <EF> <1D>A<10><00><00> X          a SINGLE 1.0, the `E` EATEN
            zb  -> A <EF> <12> E X                     the INTEGER 1, `E` left
20 A=1D     ref -> A <EF> <1F>A<10><00>×6              a DOUBLE — the PRECISION SURVIVED
20 A=1E#    ref -> A <EF> <1D>A<10><00><00> #          single, and the `#` UNEATEN
20 A=12345EX ref-> A <EF> <1D>E<12>4P X                a SINGLE, not the two-byte int
20 A=1E X   ref -> A <EF> <1D>A<10><00><00> ␣ X        ⚠️ THE BLANK SURVIVES
```

⚠️ **The last row is the one that decides the implementation, and it did not
exist before this fix was contemplated.** Making the marker consumable moves the
boundary D-DECBLANK established (*the cursor reported is one past the last
character actually consumed*), and the obvious implementation — commit
unconditionally once a marker is seen — eats that blank while leaving every
filed row green. See §4.1.

---

## 1. The site

`tkf_try_exponent` in [`sub/tkfloat.asm`](../sub/tkfloat.asm) — sub-ROM page 0,
and the **only** copy: `basic/tokenise.inc` is `include`d by
[`sub/sub.asm:209`](../sub/sub.asm:209) and nothing else, and `basic/float.asm`
keeps no crunch. So this slice does not touch the main ROM at all (§4.2).

`tke_fail` is today's rollback; its header says in as many words that the
lookahead is **own-design, never oracle-pinned** — which is exactly the class of
claim that turns out to be wrong when finally asked.

⚠️ **Not sites, and measured to be so:** `branch_lineno`'s line-number
accumulator (`20 GOTO 1EX` keeps `EX` on *both* references — the reference's
line-number scan has no exponent concept at all) and a `DATA` body.

---

## 2. The rule — measured on two machines that agree on all 18 rows

Two oracle-lock rounds, VG-8020 and CF-3300, `--repeat 2`, every payload past the
echo guard first. Tables in
[`docs/expbad-msx1-characterization.md`](expbad-msx1-characterization.md).

> **R-E1 — the digits are OPTIONAL.** The exponent is
> `[EeDd] [+-]? digit*`, not `…digit+`. A marker is consumed wherever it appears
> at the exponent position, and an immediately following sign with it, whether or
> not any digit follows. There is **no rollback**.

> **R-E2 — and the marker's PRECISION survives the failure.** `1D` is a
> **DOUBLE** (`<1F>`), `1E` a single. So it is not "a marker was seen"; the
> *which* is remembered. ⚠️ Nothing in the filed rows can say this — they are all
> `E`.

> **R-E3 — the consumed marker forces the literal off the INTEGER path.**
> `12345EX` is int-eligible (D=5, ≤32767) and still comes back a **single**. The
> filed rows are all D=1, where the marker alone decides int-vs-float, so they
> cannot isolate this.

> **R-E4 — with a marker consumed the type-suffix scan is SKIPPED**, exactly as
> for a well-formed exponent (the `1e10#` quirk already oracle-pinned in
> `tkf_try_exponent`'s header). `1E#` is a single followed by a raw `#`; `1E%`
> likewise — and `%` normally forces *integer*.

> **R-E5 — the exponent VALUE is zero.** `1E` is 1.0, not 10.

> **R-E6 — consumption obeys D-DECBLANK's cursor rule, unchanged.** A blank run
> *before* a consumed character goes with it (`1E -X` loses its blank, because
> the `-` is consumed); a blank run *behind* the last consumed character stays
> (`1E X` and `1E- X` both keep theirs). This is the rule that makes the fix
> non-trivial.

---

## 3. What zerobas does today — 3/12 on the first round

`make lnblank-characterize ONLY=<exp rows>` before any edit. The three that agree
are exactly the three controls: `dec-eok` (a well-formed exponent then a letter),
`dec-eref` (the line-number reference) and `dec-edata`. Everything else diverges,
including all four already-filed rows.

---

## 4. The fix — DELETE the rollback

The measured grammar has no failure case, so the code that implements one goes
away. `tke_checkdig`'s two range tests and `tke_fail` are removed and the commit
becomes unconditional.

### 4.1 ⚠️ But NOT by committing where the code stands today

`tke_skipsign` currently does `inc hl` / `call tkf_fetch`, and `tke_go`'s sign
lookahead is a bare `call tkf_fetch`. Both leave HL **past any blank run**. Commit
from there and `1E X` stores `…<00><00>X` — the blank eaten — while every filed
row stays green. `dec-emarkblk` / `dec-esignblk` are the only rows that object.

So the sign lookahead gets the same push/accept/reject shape D-DECBLANK gave
every other fetch, and the digit fetch is left to `tke_dloop`, **which already
does it correctly**:

```
tke_go:         inc     hl              ; past E/D -- the last CONSUMED char so far
                xor     a
                ld      (TKEXPSIGN),a
                push    hl              ; sign lookahead: restore if not a sign
                call    tkf_fetch
                cp      '+'
                jr      z,tke_sign
                cp      '-'
                jr      nz,tke_nosign
                ld      a,1
                ld      (TKEXPSIGN),a
tke_sign:       pop     af              ; accept: the blank run went with the sign
                inc     hl
                jr      tke_commit
tke_nosign:     pop     hl              ; not a sign: the run is not ours
tke_commit:     pop     de              ; discard the marker's rollback slot
                …set has_exp [+ expD]…  ; unchanged
tke_accum:      ld      de,0
tke_dloop:                              ; unchanged -- its own push/pop already
                                        ; keeps a trailing blank run
```

Traced against all 18 measured rows plus D-DECBLANK's five well-formed exponent
rows (`1 E2`, `1E- 2`, `1E -2`, `1 E 2`, `1E 2 3`), this predicts every byte.

⚠️ `pop af` **loads A** — the trap that cost D-DECBLANK a catastrophic first cut.
Here A is reloaded from `TKFLAGS` at `tke_commit`, so it is safe; the comment says
so rather than leaving the next reader to re-derive it.

### 4.2 Budget

**Landed at −8 B, exactly as predicted** (28 bytes of new sequence against 36
removed): sub-ROM page 0 went **4018 → 4026 B free**. Main page 1 stayed at
**8 B**, the low region at **23 B**, and `build/basic-reloc.rom` /
`build/zerobas-main-eu.rom` came out **byte-identical** to HEAD (`1d270536…`,
`90403dbb…`) — asserted by hash, not assumed.

A fix that *removes* code is the shape to hope for here: the rollback existed
only to implement a rule the language does not have.

---

## 5. Falsification

Every knife keeps the code **reachable** — `make basic-reloc` runs a hard
dead-code gate (0 dead, both builds) and a knife that orphans a block fails the
build and measures nothing.

| # | knife | prediction | witness |
|---|---|---|---|
| K1 | `tke_mark_d`'s `ld a,1` → `xor a` (D no longer records its precision; the block still runs) | the marker is still eaten but the literal is single | `dec-dmark`, `dec-dbad`, `dec-dmarkblk` red; **every `E` row stays green** — the only knife that separates "a marker was seen" from R-E2 |
| K2 | `tke_commit`'s `or 2` → `or 0` (has_exp never set) | the marker is eaten but nothing is forced | `dec-ebig` red (single → **two-byte int**), `dec-ebadsfx` red (the `#` gets eaten as a suffix), while `dec-emark` stays **green** — one knife, two rules, and a green control |
| K3 | `tke_nosign`'s `pop hl` → `pop af` | a lookahead that found no sign still swallows the blank run | `dec-emarkblk` red **alone**; `dec-emarkbl2` (blank before a *consumed* sign) stays green — the pair is what pins R-E6 |
| K4 | `tke_sign`'s `pop af` → `pop hl` | a consumed sign rewinds over its own blank run | `dec-emarkbl2` red alone, `dec-emarkblk` green — the mirror of K3, so neither can pass for the other |
| K5 | restore `tke_fail` (rollback on no-digit) | today's behaviour returns | all nine filed/new `E` and `D` rows red, `dec-eok`/`dec-eref`/`dec-edata` green — the whole-fix witness |

⚠️ K3 and K4 are **byte-neutral one-instruction swaps** with no symbol witness;
each is chosen to produce a reading the other cannot.

### 5.1 Result — five knives, and one that corrected the spec

Each knife was built (`make basic-reloc` + `make repack-machine`, dead-code 0/0
every time) and measured against the VG-8020, then reverted.

| # | measured | control that stayed GREEN |
|---|---|---|
| K1 | `dec-dmark`, `dec-dbad`, `dec-dmarkblk` red — **double → single** | **every `E` row**: `dec-eok`, `dec-emark`, `dec-ebig`, `dec-emarkblk`, `dec-emarkbl2` |
| K2 | `dec-ebig` red → the two-byte **INT** `<1C>90X`; `dec-ebadsfx` red → a **DOUBLE** (the `#` eaten as a suffix, because the skip is gone) | **the `D` rows**: `dec-dmark`, `dec-dmarkblk` |
| K3 | `dec-emarkblk` red **alone** — the blank behind the marker eaten | `dec-emarkbl2` *and* `dec-esignblk` |
| K4 | `dec-emarkbl2` red — the `-` rewound out of the exponent and re-emitted as the minus **operator** `<F2>`; the well-formed `dec-expsgn2` (`1E -2`) red with it | `dec-emarkblk`, `dec-esignblk`, `dec-expsgn` (`1E- 2`, sign adjacent) |
| K5 | every malformed row back to the pre-fix baseline (`<12>E`, `<12>D`, `<1C>90EX`, `<12>E X`) | `dec-eok`, `dec-eref`, `dec-edata` — well-formed, line-number reference, DATA |

🔴 **K2 REFUTED THIS SPEC'S OWN PREDICTION, and that is the point of aiming a
knife at your justification.** §5 named `dec-emark` as K2's green control. It went
**red**: with `has_exp` never set, `1E` classifies as the *integer* 1, so clearing
bit1 reaches the digitless case too. The real surviving control is the `D` pair —
which makes K1 and K2 exact mirrors over the two flag bits: **K1 kills bit2 and
every `E` row survives; K2 kills bit1 and every `D` row survives.** A predicted
control that turns red is a claim about the spec, not about the code, and it is
corrected here rather than quietly dropped.

K4 likewise reached one row further than predicted (the *well-formed* `1E -2`),
which is consistent: the blank-before-sign seam is shared by the malformed and
well-formed paths, and only the adjacency case (`1E- 2`) is untouched.

---

## 6. Gates

`build/basic-reloc.rom` + `build/zerobas-main-eu.rom` byte-identical · dead-code
0/0 both builds · `make lnblank-acceptance` with **`KNOWN_DIVERGE` empty** ·
`linemax-acceptance` 60/60 (⚠️ it measures crunch expansion byte-for-byte and an
integer literal becoming a single **changes the length** — re-read
[`basic_probe_linemax.py:139`](../probes/basic/basic_probe_linemax.py:139) before
calling a red row a regression) · `unit-test` 55/55 · `badfnum` 93 · `lof` 45 ·
`chancost` 53 · `diskbasic` 34/34 · `bdos` 12/12 · `fat-error` 8/8+dir ·
`error-trap` · `abort` 49/49 · `stop-trap` · `arrdim` 73/73 · `clearpool` 52/52 ·
`array` 149/151 (`ifc.instr.zero`, `ifc.instr.neg` by name).

---

## 7. Out of scope

`&B`, the trailing blank at EOL (not measurable through the keyboard), the
missing `$0E` verbs, `CAS:` 7/8, the README, the `PROVENANCE.md` policy.

One stale pointer found in passing and worth correcting with this slice, since it
names this very routine: `basic/PROVENANCE.md:3134` cites the suffix-after-exponent
quirk as living in `basic/float.asm`'s `tkf_try_exponent` header — it moved to
`sub/tkfloat.asm` in the sub-ROM wave-1 eviction.

---

## 8. Deliverables

1. This spec.
2. [`docs/expbad-msx1-characterization.md`](expbad-msx1-characterization.md) — 18
   oracle-locked rows, two rounds, both machines.
3. The `exp` battery (already written; measurement complete).
4. The fix at `tkf_try_exponent`.
5. `KNOWN_DIVERGE` **emptied**.
6. `TODO.md` item checked off; `PROVENANCE.md` entry appended.
