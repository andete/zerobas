# SPEC — D-PAINTBORD: PAINT's border argument has a domain, and it depends on the mode

Status: **✅ LANDED 2026-08-22.**
Filed by [`spec-basic-paintmc.md`](spec-basic-paintmc.md) §7 the same day, priced
there at ~21 B of main page 1 against 10 B free and **declined pending a carve**.
Baseline `333b6ec`: low **46 B** / main page 1 **10 B** / sub page 0 **3075 B** /
sub page 1 **1624 B**.

---

## 1. The rule

> **`B` is 0..255 in SCREEN 2 and 0..15 in MULTICOLOUR. Outside that domain,
> `Illegal function call` (ERR 5) — raised as `B` is parsed, above the grammar.**

Measured on the **VG-8020** and the **CF-3300**, which agree on every row.

| `B` | SCREEN 2 refs | SCREEN 3 refs | zerobas before | zerobas after |
|---|---|---|---|---|
| 15 | floods | floods | floods | floods ✅ |
| 16 | floods | **ERR 5** | floods | ✅ both |
| 17 | — | **ERR 5** | floods | ✅ |
| 255 | floods | **ERR 5** | floods | ✅ both |
| 256 | **ERR 5** | **ERR 5** | floods | ✅ both |
| −1 | **ERR 5** | **ERR 5** | floods | ✅ both |

Rows `bd2.*` / `bd3.*` in [`scratchpad/paintmc_probe.py`](../scratchpad/paintmc_probe.py).

`ep_parse_b` did `ld a,e / ld (GFX_B),a` and checked **nothing**.

---

## 2. 🔴 Two defects with different ages, and only one of them is D-PAINTMC's

⚠️ **The SCREEN-2 half is PRE-EXISTING** and has nothing to do with multicolour.
It has been wrong since G5, and it was invisible because the one shipped row that
touches this argument — `border16_flood_ok`, `PAINT(5,5),1,16` — uses **16, which
is INSIDE the SCREEN-2 domain**. A row cannot see a boundary it sits well short of.

What D-PAINTMC changed is that the **SCREEN-3 half stopped agreeing by accident**.
Before it, *every* multicolour PAINT was ERR 5, so `PAINT(10,10),9,16` printed the
right answer for the wrong reason — [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
in its purest form. The moment PAINT joined SCREEN 3, that row's second cause of
green evaporated and the divergence became visible.

🔴 **And the source said so in prose.** `ep_parse_b` carried

> *given B: eval only, NOT range-checked (spec §3/§5 — a border of 16+ is legal,
> just a comparison value no pixel hits)*

which is right about what a border of 16 **does** in SCREEN 2 and wrong about the
**domain**, and was never right in multicolour at all.
[`spec-basic-graphics-g5.md`](spec-basic-graphics-g5.md) §3, §5 and §11 say the
same thing three more times. All four are **inverted, not deleted**.

---

## 3. 🎯 The check reads the full int16, not the stored byte

`GFX_B` is one byte and `gfx_eval_int16` leaves the value in **DE**. `256` is
`$0100`, whose **low byte is `$00`** — a byte-only test would wave it straight
through and store a border of 0. `PAINT(10,10),9,256` is ERR 5 on both references
in **both** modes (`bd2.256` / `bd3.256`), so that case is real and the high byte
has to be part of the test. `−1` is `$FFFF`, which the byte test would store as
255 — legal in SCREEN 2 — so it too is only caught by `D`.

---

## 4. 🎯 WHERE the check sits is itself a claim, and it was measured

D-LINERR's whole finding is that the ORDER of a parse's faults is behaviour.
`ep_parse_b` already ends with a grammar test — a third comma is a 4th argument
and raises ERR 2 — so an out-of-domain border **behind** a 4th argument separates
the hypotheses, and nothing else does: every other fault that could race the
border (off-screen seed, wrong mode, out-of-range `C`) also raises ERR 5.

| program | SCREEN | both refs | zerobas before |
|---|---|---|---|
| `PAINT(10,10),9,16,` | 3 | **ERR 5** | ERR 2 |
| `PAINT(10,10),9,15,` | 3 | ERR 2 | ERR 2 |
| `PAINT(10,10),9,256,` | 2 | **ERR 5** | ERR 2 |
| `PAINT(10,10),9,16,` | 2 | ERR 2 | ERR 2 |

Rows `od3.b16c` / `od3.b15c` / `od2.b256c` / `od2.b16c`.

> **The domain beats the grammar.** The check therefore replaces the inline store,
> above the trailing-comma test — not below it.

⚠️ **The in-domain twins are what make the other two mean anything.** They run the
SAME programs with a border that is legal in that mode and read ERR 2, so the
trailing comma really is a 4th argument and the parse really does reach the
grammar. Without them an ERR 2 would agree with *"the check is missing"* and with
*"the parse never got that far"* alike.

---

## 5. 💰 Price — measured, and it is a third of the filed estimate

| wall | before | after | spent |
|---|---|---|---|
| main page 1 | 10 B | **4 B** | **6** |
| main page-0 low | 46 B | 46 B | 0 |
| sub page 0 | 3075 B | 3075 B | 0 |
| sub page 1 | 1624 B | 1624 B | 0 |

`build/sub.rom` is **byte-identical** — a `basic/*.asm` edit moves only the main
image, exactly as the two-ROM rule predicts.

🔴 **THE FILED PRICE WAS ~21 B AND A DECLINE; THE MEASURED PRICE IS 6 B.** The
filed shape was a standalone `gfx_store_border_checked` bolted on beside the
existing `gfx_store_colour_checked`. The difference is that the two checks turn
out to be **one leaf with a different constant**, plus one carve:

| item | B |
|---|---|
| `gfx_chk_dom` — the new shared domain leaf | +7 |
| `gfx_store_colour_checked` rewritten onto it | **−5** |
| `ep_parse_b` — the border domain, inline | +12 |
| `g8_fn` (`VDP(n)`/`BASE(n)`) rewritten onto it | **−3** |
| `gfx_absent` → an alias of `gfx_err5` (the carve) | **−5** |
| **net** | **+6** |

### 5.1 🎯 The mask is why this is one leaf and not two

Every domain in this file is *"the value fits in `k` low bits"*:

```
gfx_chk_dom:                ; A = high-nibble mask, DE = value -> A = E
                and     e   ;   A = $F0 -> 0..15   (a colour nibble)
                or      d   ;   A = $00 -> 0..255  (a byte)
                jp      nz,gfx_err5
                ld      a,e
                ret
```

`or d` folds the negative/`>255` half in for **free**, because an int16 outside
0..255 is precisely one with a non-zero high byte — so §3's requirement costs
nothing rather than 5 B. The colour rule (0..15, always), the border rule (0..15
in multicolour, 0..255 in SCREEN 2) and `VDP(n)`/`BASE(n)`'s index rule (a byte,
then a variable ceiling) differ **only in the mask**.

The border site is then the mask selection and nothing else:

```
                ld      a,(SCRMOD)
                cp      3               ; MULTICOLOUR?
                ld      a,$F0           ; ...then B is a nibble, 0..15
                jr      z,ep_b_dom      ; (`ld a,n` does not touch the flags)
                xor     a               ; SCREEN 2: B is a whole byte, 0..255
ep_b_dom:       call    gfx_chk_dom
                ld      (GFX_B),a
```

⚠️ A 4 B cheaper form exists (`rrca / sbc a,a` in place of `cp 3` + the branch,
reading `SCRMOD`'s **bit 0** to tell 2 from 3, which is sound because the mode
gate has already refused 0 and 1 and MSX1 has no mode 4). It was **declined**: an
error domain is the last place to encode a mode test as a bit trick, and page 1
had the room.

### 5.2 The carve

`gfx_absent` — the defensive *"`subrom_call` reported the tenant missing"* tail,
which cannot fire on the merged build — was `ld a,5 / jp raise_error`, i.e.
**byte-identical to `gfx_err5` directly above it**. It is now `gfx_absent equ
gfx_err5`, on the precedent `interp.asm` sets for `err_illegal_fn` (*"they were
byte-identical and one had to go"*). The NAME survives because the two are
different **claims**: a later slice wanting a distinct face for an absent tenant
un-aliases it and no call site moves. 5 B, and all seven `jp c,gfx_absent` sites
are untouched.

---

## 6. 🔬 Falsification — [`scratchpad/paintbord_knives.py`](../scratchpad/paintbord_knives.py)

Four knives, predictions written before the run, each cutting a **value**; the
runner rebuilds from clean, hashes both images and refuses a knife whose cut did
not move one, restores by writing the bytes in a `finally`, and calibrates its
parser on a clean / planted / row-deleted log **before** the baseline runs.

| knife | cut | pins |
|---|---|---|
| **K-PB1** | the MC arm's mask `$F0` → `$00` | the **multicolour** bound |
| **K-PB2** | `gfx_chk_dom`'s `or d` → `or a` | the **byte** bound |
| **K-PB3** | `cp 3` → `cp 2` | the mode **selection** |
| **K-PB4** | the grammar test moved **above** the domain check | §4's **ordering** |

🟢 K-PB1 and K-PB2 have **disjoint** predicted sets and each carries the other
half's rows as green controls. K-PB3 reddens both halves in **opposite**
directions, which is what a swapped domain looks like and what a merely-absent
one does not.

🎯 **K-PB2's set had to be DERIVED, and deriving it is what makes it a claim.**
Removing `or d` does *not* redden all four out-of-range rows: `−1` is `$FFFF`, so
in multicolour `and $F0` still sees `$F0` and raises anyway — `bd3.neg` stays
**green**. `256` is `$0100`, whose low byte is `$00`, so the mask sees nothing and
`bd3.256` **reddens**. Two rows that look like one class part company under the
knife, and that is exactly §3's point restated as a prediction.

---

## 7. ✅ The rows ship

[`probes/basic/basic_probe_graphics.py`](../probes/basic/basic_probe_graphics.py)
`PAINT_BEHAV` (PHASE J — batched, pre-tenant, fast) gains **ten** rows: the
out-of-domain values in both modes, and the four ordering rows of §4.

🔴 **A second cause of "ERR 5" exists and is excluded by construction.** A
SCREEN-3 PAINT refused outright — the pre-D-PAINTMC behaviour — gives ERR 5 on
every multicolour row here. `b_mc_15_comma` reads ERR **2**, which is only
reachable by a parse that got past the mode gate, so the ERR 5s are the domain
and not the mode.

⚠️ **`border16_flood_ok` was WEAK and is strengthened here**, because this is the
slice that makes it load-bearing. Its `PAINT(5,5),1,16` paints with `C = 1`, which
under `LINIT`'s `COLOR15,1,1` **is the background** — so by
[`spec-basic-paints2seed.md`](spec-basic-paints2seed.md)'s rule the reference
refuses the seed outright and all four sample points read 1 whether anything was
painted or not. It gated *"a border of 16 does not raise"* (the program aborts
before its `PRINT`, so the row fails) and nothing else: a coverage row whose
geometry could not reach its own case. `C = 9` makes the flood real — the undrawn
seed reads the background 1, which is neither `C` nor `B`, so it is admitted and
the whole screen goes to 9. D-PAINTS2SEED left this row alone deliberately
(*"changing a pinned row is its own claim"*); the claim is made here, with the
reason, and the row stays a pure differential.

---

## 8. What is NOT claimed

* **Nothing about SCREEN 0/1**, where PAINT raises ERR 5 before `B` is looked at.
* **Nothing about a border's EFFECT beyond its domain.** That 16..255 in SCREEN 2
  is a comparison value no 0..15 pixel matches is unchanged and still gated by
  `border16_flood_ok`; only the claim that the domain is unbounded is retracted.
* **The `,B` colour-group clash (`nt2.wall`) is untouched** and stays filed in
  `TODO.md`: a `,B` wall sharing an 8-pixel colour group with the fill is
  recoloured ("border eaten") on both references and left alone here, while the
  fill's extent agrees.
* **Nothing about `GFX_B`'s WIDTH.** It is still one byte and still stores the low
  byte; what changed is that a value whose high byte is non-zero can no longer
  reach the store.
