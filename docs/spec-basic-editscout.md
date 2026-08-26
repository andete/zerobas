# Scout: where can the screen-editor REPL live?

**D-EDITSCOUT, 2026-08-26.** A placement scout, not an implementation. Probes:
`scratchpad/editscout_layout.py`, `scratchpad/editscout_reentry.py`,
`scratchpad/editscout_reentry2.py`, `scratchpad/editscout_wrap.py`.
Reference: `Philips_VG_8020`. ⚠️ `National_CF-3300` NOT run — one reference only.

[`TODO.md`](../TODO.md) files the screen-editor REPL as open, and
[`docs/decision-phase3-space-strategy.md`](decision-phase3-space-strategy.md)
§3 prices it at **0.6–0.9 KB, classified "in-window"**. Main page 1 has 89 B free
(measured, `make basic-reloc`), so on that classification it is hard-blocked.
**That classification was signed off 2026-07-11, before the sub-ROM tenant
architecture existed** — the sub-ROM now carries 15 page-0 and 24 page-1
tenants, one of which (`lineedit_tenant`) is already the line-editing code. This
scout asks what the feature actually needs and at what granularity.

## 1. The instrument, established before any row was believed

The REPL driver injects DECODED bytes into `KEYBUF`, so an MSX cursor key is
just its control code — `$1C`/`$1D`/`$1E`/`$1F` for right/left/up/down. It
works, and the harness cannot verify that it works:

⚠️ **DELIVERY VERIFICATION IS STRUCTURALLY BLIND TO THIS ENTIRE PAYLOAD CLASS.**
`omsx_repl`'s delivery guard marks any payload outside `0x20..0x7E`
`BLIND/unprintable`, and it says why in its own comment: the ROM renders such a
byte as *cursor movement*, so the typed text can never be a substring of the
screen. Every row here is cursor movement. **So each question carries its own
control whose consequence is printable**, and the instrument was proven before
the subject was asked anything.

**The instrument control** (`editscout_layout.py`): `CLS`, cursor-down ×3,
`PRINT"Z"`.

| | typed line lands at |
|---|---|
| VG-8020 | **r05** — the three downs moved the cursor |
| zerobas | **r01** — they did nothing |

That is the delivery proof and the first divergence in one row.

## 2. What zerobas does with a cursor key

Drops it. [`basic/repl.asm`](../basic/repl.asm)'s `read_line` has
`cp 32 / jr c,rl_loop` — *"other control characters are ignored"* — so `$1E`
never reaches `CHPUT`. Enter then submits the (empty) `LINEBUF` and the REPL
prints another prompt, which is exactly what the captures show.

## 3. Q1 — the feature: Enter re-reads the line FROM THE SCREEN

🔴 **THE FIRST ROW WAS BLIND BY CONSTRUCTION, AND IT READ AS "NO FEATURE".**
`PRINT"AAA"`, re-entered from the screen, reprints `AAA` over the `AAA` already
there and `Ok` over the `Ok` already there: **a working re-entry leaves the
screen byte-identical to no re-entry at all.** The row scored 2 AAA occurrences
on both sides and looked like agreement.

What proved the mechanism was the **wrong-row control** — cursor-up ×1 lands on
an `Ok` row, and re-entering it raises `Syntax error` on the reference. The
control was written to rule out *"Enter just re-runs the last line"*; it ended up
being the only row that could see anything at all.

The fix is a payload whose re-execution CHANGES what it prints —
`A=A+1:PRINT A` (`editscout_reentry2.py`):

| re-entries | VG-8020 prints | zerobas prints |
|---|---|---|
| 0 (control) | `1` | `1` |
| 1 | **`2`** | `1` |
| 2 | **`3`** | `1` |

**The value scales with the number of re-entries**, so the row cannot agree for
the wrong reason. The screen editor is live on the reference and absent here.

## 4. Q2 — the price: who moves the cursor?

`PRINT CHR$(31);CHR$(31);"Z"` asks `CHPUT` directly, with no editor involved.

| | Z without the control bytes | Z with two `$1F` | moved |
|---|---|---|---|
| VG-8020 | r02 | r04 | **+2 rows** |
| **zerobas** | r01 | r03 | **+2 rows** |

🟢 **C-BIOS's `CHPUT` ALREADY HONOURS CURSOR-MOTION CODES ON THE ZEROBAS
MACHINE.** The *output* half of a screen editor is already present and costs
zerobas nothing. What is missing is purely on the *input* side — `read_line`
throwing the byte away before `CHPUT` ever sees it.

## 5. The re-read unit is the LOGICAL LINE, not the row

A 46-character payload wraps onto two rows (`editscout_wrap.py`). Entering from
**either** row re-executes the whole statement:

| cursor lands on | result |
|---|---|
| r02, the CONTINUATION row | counter → **2** |
| r01, the FIRST row | counter → **2** |
| r00, the `Ok` row above | `Syntax error`, counter stays 1 |

So a reader must walk **back** to the logical line's start and **forward**
through its continuations. That is the real complexity driver, and it is now
measured rather than assumed.

## 6. What this means for placement

The per-keystroke path is `CHPUT` — BIOS, no sub-ROM crossing, already working.
The novel work happens **once per Enter**: read the logical line at the cursor
out of VRAM into `LINEBUF` instead of using the accumulated buffer. **That is
`lineedit_tenant`'s exact granularity** — `le_store` is likewise one call per
entered line.

🎯 So the worry that a screen editor means a sub-ROM crossing per keystroke is
**refuted by measurement**, and the 2026-07-11 "in-window" classification is a
judgement taken before the tenant architecture and before this measurement.
Sub page 1 has 1622 B free and sub page 0 has 2464 B (measured today).

⚠️ **THIS IS A PLACEMENT SCOUT AND IT HAS NOT PRICED ANYTHING.** Still
unmeasured, and each could move the answer:

* **The byte cost of the VRAM logical-line reader.** Not estimated here. The
  0.6–0.9 KB figure is the 2026-07-11 estimate and is not re-derived.
* **How the reader knows where a logical line STARTS.** The reference keeps
  per-row continuation bookkeeping; zerobas has none, and whether it can infer
  the boundary (a predecessor row filled to `LINLEN`) is unmeasured.
* **`INS` mode, `HOME`, `CTRL`+key, the `CLS`/`SELECT` keys**, and the function-key
  row at r23 — none touched.
* **`CF-3300` was not run.** One reference only, so nothing here separates
  "MSX1 BASIC" from "this VG-8020".
* Whether the tenant may read VRAM directly (it is port I/O, so it can in
  principle) has not been demonstrated from inside a tenant.
