# D-EXPBAD — what a MALFORMED exponent marker does, on two MSX1 machines

Companion to [`docs/spec-basic-expbad.md`](spec-basic-expbad.md); the sequel to
[`docs/decblank-msx1-characterization.md`](decblank-msx1-characterization.md),
whose §3 filed the finding this measures.

**Instrument:** `("stored_line", TXTTAB)` — the exact bytes of the stored line,
link word dropped. Probe
[`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
`exp` battery. `make lnblank-characterize ONLY=dec-e…`.

**Two oracles.** Every row asked of the **Philips VG-8020** and the **National
CF-3300**, `--repeat 2` on independent boots, every payload past
`make lnblank-echo` first. **They agree on all 18 rows.** Both rounds were
oracle-locked **before** zerobas was run on any of them.

Token bytes as in the D-DECBLANK companion: `<1D> e m m m` single, `<1F> e m×7`
double, `<1C> lo hi` two-byte integer, `<11>`…`<1A>` the integers 0…9, exponent
biased by 64, mantissa BCD.

---

## 1. Round 1 — is the marker consumed, and what does it carry?

`^` = control

| row | typed | **both references** | zerobas today |
|---|---|---|---|
| `dec-eok` ^ | `20 A=1E1X` | `A<EF><1D>B<10><00><00>X` — 10, then `X` | *agrees* |
| `dec-emark` | `20 A=1E` | `A<EF><1D>A<10><00><00>` — single **1.0**, nothing left | `A<EF><12>E` |
| `dec-esign` | `20 A=1E+` | `A<EF><1D>A<10><00><00>` — the `+` gone too | `A<EF><12>E<F1>` |
| `dec-ebadneg` | `20 A=1E-X` | `A<EF><1D>A<10><00><00>X` | `A<EF><12>E<F2>X` |
| 🔴 `dec-dmark` | `20 A=1D` | `A<EF><1F>A<10><00><00><00><00><00><00>` — a **DOUBLE** | `A<EF><12>D` |
| 🔴 `dec-dbad` | `20 A=1DX` | `A<EF><1F>A<10>…X` — **DOUBLE**, then `X` | `A<EF><12>DX` |
| 🔴 `dec-ebadsfx` | `20 A=1E#` | `A<EF><1D>A<10><00><00>#` — single, `#` **UNEATEN** | `A<EF><12>E#` |
| `dec-ebadsfx2` | `20 A=1EX#` | `A<EF><1D>A<10><00><00>X#` | `A<EF><12>EX#` |
| 🔴 `dec-ebig` | `20 A=12345EX` | `A<EF><1D>E<12>4PX` — a **SINGLE** 12345 | `A<EF><1C>90EX` — a two-byte **INT** |
| `dec-elow` | `20 A=1ex` | `A<EF><1D>A<10><00><00>X` — lowercase counts | `A<EF><12>EX` |
| `dec-eref` ^ | `20 GOTO 1EX` | `<89> <0E><01><00>EX` | *agrees* |
| `dec-edata` ^ | `20 DATA 1EX` | `<84> 1EX` | *agrees* |

### 1.1 🔴 `dec-dmark` — the PRECISION survives a failed exponent

`1D` is a **double** and `1E` a single. So the reference does not merely notice
that *a* marker was there; it remembers **which**. Every row the item was filed
with is an `E` row, and no `E` row can distinguish "a marker was seen" from "this
marker was seen" — the fix would have collapsed both onto single and passed.

### 1.2 🔴 `dec-ebadsfx` — the suffix scan is skipped, so `#` does NOT apply

`1E#` is a **single** followed by a raw `#`, not a double. That is the same quirk
already oracle-pinned for *well-formed* exponents (`1e10#` leaves the `#`,
recorded in `tkf_try_exponent`'s header) — so a consumed-but-digitless marker
sets the same state a successful one does. `1E%` behaves identically, and `%`
normally forces **integer**.

### 1.3 🔴 `dec-ebig` — the marker forces the literal off the INTEGER path

`12345` is int-eligible (D=5, ≤ 32767) and zerobas stores exactly that today
(`<1C>` + `$3039`). The reference stores a **single**. Every filed row has D=1,
where the marker alone decides int-vs-float; this row is the only one where the
two rules disagree for a reason the digit count can produce on its own.

### 1.4 The two scanners this does NOT reach

`20 GOTO 1EX` keeps `EX` on **both references** — the line-number reference
accumulator (`branch_lineno`) has no exponent concept at all, so
blank-transparency is shared between the scanners and marker-consumption is
**not**. A `DATA` body is verbatim. Both already agree with zerobas and are
pinned as controls.

---

## 2. Round 2 — where this rule meets D-DECBLANK's

⚠️ **These cells are created by the fix.** They did not exist while the marker was
never consumed, and they are the reason the obvious implementation is wrong.

| row | typed | **both references** | what it pins |
|---|---|---|---|
| 🔴 `dec-emarkblk` | `20 A=1E X` | `A<EF><1D>A<10><00><00>␣X` | the marker is consumed and **the blank behind it is NOT** |
| `dec-emarkbl2` | `20 A=1E -X` | `A<EF><1D>A<10><00><00>X` | the blank sat before a **consumed** sign, so it went with it |
| 🔴 `dec-esignblk` | `20 A=1E- X` | `A<EF><1D>A<10><00><00>␣X` | the sign is consumed and **its** trailing blank is not |
| `dec-dmarkblk` | `20 A=1D X` | `A<EF><1F>A<10>…␣X` | the same seam on the DOUBLE marker |
| `dec-edot` | `20 A=1.EX` | `A<EF><1D>A<10><00><00>X` | `has_dot` and a failed marker together |
| `dec-ebadpct` | `20 A=1E%` | `A<EF><1D>A<10><00><00>%` | `%` normally forces INT — skipped |

**The rule is unchanged from D-DECBLANK, and that is the finding:** *the cursor a
literal scan reports is one past the last character it actually CONSUMED.* The
marker and its sign simply joined the set of things that can be consumed.

⚠️ An implementation that commits the exponent where the code stands today — after
`tkf_fetch` has already advanced past a blank run — satisfies **every filed row**
and fails `dec-emarkblk` / `dec-esignblk`. Those two rows are the whole reason
the sign lookahead needs the push/accept/reject shape
([`docs/spec-basic-expbad.md`](spec-basic-expbad.md) §4.1).

---

## 3. Summary of the rule

1. **R-E1** the exponent grammar is `[EeDd] [+-]? digit*` — **the digits are
   optional and there is no rollback**.
2. **R-E2** the marker's precision survives: `D` forces **double**, `E` leaves the
   digit count to decide.
3. **R-E3** a consumed marker forces the literal off the **integer** path.
4. **R-E4** with a marker consumed, the **type-suffix scan is skipped** — a
   trailing `!`/`#`/`%` stays as a raw byte.
5. **R-E5** the exponent value is **zero** when no digits follow.
6. **R-E6** consumption obeys D-DECBLANK's cursor rule unchanged: a blank run
   before a consumed character goes with it, one behind the last consumed
   character stays.
7. It does **not** reach `branch_lineno`'s line-number scan or a `DATA` body.
