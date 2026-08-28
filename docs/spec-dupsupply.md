# D-DUPSUPPLY — the byte-identical-span supply is 5 B, not 403, and the item predicted why

**2026-08-28.** Prices out the item D-DUPSPAN filed on 2026-08-22 as *"53 groups,
403 B NOMINAL, and nominal is not a price."* Re-measured: **26 groups, 163 B
nominal, 5 B same-region net** — and all 5 of it is one alias, now taken.

## 1. The figure had rotted, exactly as the item said it would

The item's own instruction is *"re-run `python3 scratchpad/dupspan_sweep.py` —
never quote this figure, it rots exactly like a wall."* It does:

| | filed 2026-08-22 | measured 2026-08-28 |
|---|---|---|
| groups | 53 | **26** |
| nominal B | 403 | **163** |

Several pairs it named by size have moved too — `sav_ascii_flag`/`sav_cas_flag`
was listed among the "11–20 B pairs" and is now a **3 B** group — and one pair it
does not list, `pn_wr`/`dde_wr` (11 B), has appeared since.

## 2. Nominal is not a price, and the item said why in advance

> **These are LOOP BODIES, not error tails**, so unlike the tails they are not
> obviously position-independent: a relative jump out of the span makes two
> identical spans un-collapsible.

`tools/dupspan_indep.py` decides that from the ROM bytes, and **every single one
of the large pairs dies on exactly that prediction**:

| group | nominal | verdict |
|---|---|---|
| `ai14_lp` / `ai6_lp` | 14 B | relative jump leaves the span (+19 of 14) |
| `eostr_lp` / `eokey_lp` | 13 B | runs off its end |
| `ex_on_strig` / `ex_on_key` | 12 B | runs off its end |
| `asw_single` / `vsf_single` | 11 B | relative jump leaves the span (+18 of 11) |
| `pn_wr` / `dde_wr` | 11 B | relative jump leaves the span (+11 of 11) |
| `vnk_more` / `vst_walk` | 8 B | relative jump leaves the span (+8 of 8) |
| `asw_int` / `vsf_int` | 7 B | runs off its end |

🎯 **The prediction was not just directionally right, it was right about the
mechanism** — "a relative jump out of the span" is the literal verdict string on
five of the seven.

## 3. 🔴 The default run over-prices by including a CROSS-REGION collapse

A plain `dupspan_indep.py` reports **NET 8 B**. That figure is wrong to act on,
and the tool says so itself if you ask it the right way — its fourth check is
opt-in:

> Main low (`$2812-$3FFF`) is switched OUT under a sub page-0 tenant and main
> page 1 (`$4000-$7FFF`) is switched OUT under a sub page-1 tenant. Aliasing a
> LOW label onto a PAGE-1 address hands every page-1 tenant that reaches it an
> address that is not there.

The 8 B includes collapsing **`affn_found` (`$333D`, page-0 low)** onto
**`cal_srv_ret` (`$67A3`, page 1)** — across that boundary. `--samereg` prices
the carve that cannot have the problem at all:

```
nominal 163 B  ->  MEASURED SAFE NET 5 B
by REGION, before widening: page-0 low 0 B, page 1 5 B; `jr` widening charged 0 B
```

⚠️ **The region check is a FLAG, not a default**, so the number a reader gets by
running the tool the obvious way is the one that includes a collapse the tool's
own comment forbids. Recorded here rather than changed: which default is right is
a tool-design call, and the flag is documented in its `--help`.

## 4. The 5 B, taken

`pu_ifc` (`basic/printusing.asm`) was a **ninth** byte-identical copy of
`gb_illegal`'s `ld a,5 / jp raise_error` — a body that already carries eight names
(`eoi_err5`, `fchk_ifc`, `gfx_absent`, `gfx_err5`, `pl_absent`, `snd_illegal`,
`strig_illegal`). It is now `pu_ifc equ gb_illegal`.

It is the clean case on every axis: terminates, no escaping relative jump, no
fallthrough entry, canonical in the **same region**, and its one incoming jump was
**already a `jp`** (`jp nc,pu_ifc`), so nothing widens and the 5 B is net.

**Measured, not predicted:** main page-1 free **89 B → 94 B**. Page-0 low
unchanged at 39 B; both sub islands unchanged. The tool's price was right to the
byte.

## 5. Falsification

`make deadcode` passes — the alias left nothing unreachable, which is the failure
mode this repo has hit before when a body lost its last real definition.

🔴 **NOTHING IN `make gates` NAMES PRINT USING**, so the collapsed arm needed its
own reading ([`scratchpad/puifc_probe.py`](../scratchpad/puifc_probe.py)). The
D-PUSING measurements it implements, re-run on all three machines:

| row | vg8020 | cf3300 | zb |
|---|---|---|---|
| `PRINT USING"abc"` | ERR 2 | ERR 2 | ERR 2 |
| `PRINT USING"abc";` | **ERR 5** | **ERR 5** | **ERR 5** |
| `PRINT USING"abc";5` | **ERR 5** | **ERR 5** | **ERR 5** |
| `PRINT USING"##";5` (control) | prints | prints | prints |

The two middle rows are the `pu_ifc` arm itself; the control says the verb still
works rather than the error tail merely still erroring.

## 6. What is left

**Nothing worth taking.** The remaining 158 B of nominal is refused by the byte
decoder, not by judgement, and the refusals are structural — a loop body with a
`jr` inside it cannot be collapsed at any price. The class is **measured empty**
short of restructuring the loops themselves, which is a different kind of change
from an alias and is not funded by 158 B of nominal that does not exist.
