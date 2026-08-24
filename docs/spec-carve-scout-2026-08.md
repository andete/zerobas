<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# Carve scout, 2026-08-24 — where main page 1's next bytes are NOT

Status: **📏 MEASUREMENT ONLY. No source file changed, no ROM byte moved**
(`0d04f8b7` / `490ffc49` / `dd90f859`), on `d515707`.

Main page 1 was **2 B free** on 2026-08-24 (`make basic-reloc`), and the open
range-check item ([`spec-basic-himdom.md`](spec-basic-himdom.md) §5) needs
funding before it needs a design. This asks where that funding is, and **the
useful answer is negative**: two of the three standing routes are measured shut.

---

## 1. Route A — the dup-span collapse: **EXHAUSTED, 4 B**

`scratchpad/dupspan_sweep.py` then `tools/dupspan_indep.py`, whole main image,
denominator printed: **1440 non-empty spans, 27 byte-identical groups, 190 B
nominal.**

    nominal 190 B  ->  MEASURED SAFE NET 4 B
    by REGION, before widening: page-0 low 3 B, page 1 6 B; `jr` widening charged 5 B

Every large group is rejected for a reason the byte-equality sweep cannot see —
the three D-DUPSPAN blind spots, now decided mechanically:

| group | nominal | why it is not available |
|---|---|---|
| `esn_p2` / `esn_scan_lp` | 20 B | a relative jump LEAVES the span |
| `ai14_lp` / `ai6_lp` | 14 B | same, and both are page-0 low anyway |
| `eostr_lp` / `eokey_lp` | 13 B | runs off its own end into different code |
| `ee_raise` / `sid_raise` / … ×5 | 12 B | entered by FALLTHROUGH — a `jp` costs what the span costs |
| `combine_add` / `ex_lset` / … ×4 | 9 B | the span IS a relative jump (`xor a / jr +2`) |

🎯 **The seam D-DUPSPAN (+50 B), D-DUPSPAN2 (+122 B) and D-XREG (+46 B) worked
is genuinely worked out.** 4 B is not worth a slice's risk, and the tool says
out loud that its widening figure is an estimate the assembler would have to
confirm.

⚠️ **One candidate is this week's own code.** `ep_missing` (D-PAINTMISS,
`basic/graphics.asm`) is byte-identical to `wid_missing` (`basic/screen.asm`) —
both are `c3 05 62`, `jp loc_missing`. It prices at **NET +1 B**, because
`ep_missing`'s four incoming edges are `jr`s and the canonical is ~1.6 KB away,
so collapsing it widens four jumps to `jp`. **A dup-span sweep sees bytes, never
how a span is ENTERED**, and here the entry cost eats the whole saving.

## 2. Route B — eviction to a page-0 sub-ROM tenant: **STRUCTURALLY CLOSED FOR VERBS**

Sub page 0 has **2563 B free**, so this looked like the large win.
`tools/carve_scout.py` sizes and then tests legality: a page-0 tenant runs with
slot-0 page 0 switched OUT, so neither the BIOS (< `$2812`) nor the main low
region (`$2812–$3FFF`) is there — **and the walk must continue through resident
main page 1**, because the slot configuration persists across that call.

Five candidates, sized by SOURCE FILE and split into what must stay resident:

| file | leaves page 1 | shared (stays) | **private (movable)** | verdict |
|---|---|---|---|---|
| `basic/cload.asm` | 961 B | 199 B | **762 B** | ❌ not evictable |
| `basic/field.asm` | 589 B | 53 B | **536 B** | ❌ |
| `basic/save.asm` | 593 B | 95 B | **498 B** | ❌ |
| `basic/printusing.asm` | 446 B | 40 B | **406 B** | ❌ |
| `basic/playsvc.asm` | 229 B | 21 B | **208 B** | ❌ (untested entries) |
| `basic/list.asm` | 187 B | 10 B | **177 B** | ❌ |

**All refused, and all by the same two mechanisms** — not by anything specific
to the file:

    do_save -> sav_ascii_flag -> pchar -> CHPUT              (printing)
    do_save -> fname_expr -> ... -> raise_error -> BREAKX    (raising)

🎯 **THE GENERAL RULE, and it is why this route is closed rather than merely
difficult: a BASIC verb that can PRINT, or that can RAISE AN ERROR, reaches the
BIOS transitively.** `pchar` ends at `CHPUT`; `raise_error` ends at `BREAKX` /
`CHGET`. Every verb does at least one of those — `list.asm`'s only DIRECT
escapes are re-expressible plumbing (`subrom_call`, `subrom_absent_error`) and
it is still refused, on **313** escapes reached *through* page 1.

⚠️ **This is what the existing tenants already tell you, read backwards.** The
shipped page-0 tenants are the circle generator, the flood fill and the string
heap: pure computation that **reports errors through a slot** (`GFX_RES`,
`GFX_POVF`, `ARY_ERR`) instead of raising, and never prints. That is not a style
choice — it is the only shape the slot configuration permits.

📏 **DENOMINATOR: 5 files of 22 with page-1 content were tested for legality**,
chosen as the largest plausibly-leaf verbs. The blocker is generic, so the
result very likely generalises — **but "very likely" is not measured**, and the
cheap way to settle it is to test whether ANY page-1 entry point avoids both
`pchar` and `raise_error`.

## 3. Route C — the page-1 eval-bounce co-routine: **OPEN, UNPRICED**

Sub page 1 has **1617 B free** and `sub/circleparse.asm` is the proof it can
host a verb's grammar: the tenant cannot call `eval`/`parse_coord` either (main
page 1 is switched out under it), so it walks the token stream in RAM and
REQUESTS each value through `GFX_DREQ`, with a thin resident servicer resolving
the request and re-entering. CIRCLE's resident stub is ~60 B against a ~350–500 B
tenant.

**That is the only route left for a verb, and it is not cheap**: it needs a
request/resume protocol per verb, and the resident stub still costs page-1 bytes
even as it frees more. Unpriced here — pricing it means picking a verb and
counting its value requests, which is a slice.

## 4. What this changes

* **Do not open the range-check slice expecting a dup-span carve to fund it.**
  4 B is the whole seam.
* **Do not open an eviction slice for a printing or erroring verb.** The tool
  refuses it in seconds; the design that would satisfy it is Route C.
* ⚠️ `tools/carve_scout.py --census` **prints nothing and exits 0 without
  `--files`.** It is documented as "with --files", so this is a usage error and
  not a defect — but it is the 0-byte-report-at-rc-0 shape, and it cost a run
  here before the empty log was noticed.
