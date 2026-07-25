# cbios-repack — tracked patches that repack C-BIOS to free page-0 space

Part of the C-BIOS repack arc ([`../docs/spec-cbios-repack-tooling.md`](../docs/spec-cbios-repack-tooling.md)).
These are **our own 0BSD patches** against a pinned C-BIOS source tag — they describe
edits to BSD-2-clause C-BIOS source, so **no C-BIOS bytes live in this repo** (decision
D1). The build applies a patch to the user's `~/projects/cbios` checkout, rebuilds, and
diffs the result vs pristine stock to emit the shipping IPS. A patch is a description of
a diff, not a merge — the provenance firewall holds. The full firewall argument for
the merged main-ROM deliverable (source side + output side, with the empirical proof
against the shipped IPS) is [`../docs/cbios-repack-provenance.md`](../docs/cbios-repack-provenance.md).

## Pinned base

- Checkout: `~/projects/cbios`, tag **`v0.29-3-gb5ad9cb`**
- Stock `cbios_main_msx1_eu.rom` sha1 `baf2e9c69252fd9b350b488d89c71887b9d05eec`

## Patches

| Patch | Variant | Effect | Repacked sha1 |
|---|---|---|---|
Applied **in order** by [`tools/build_repacked_cbios.py`](../tools/build_repacked_cbios.py);
the `Repacked sha1` column is the ROM after **all patches up to and including that row**.

| # | Patch | Variant | Effect | Repacked sha1 |
|---|---|---|---|---|
| 1 | `eu-drop-statements.patch` | `main_msx1_eu` | Comments out `include "statements.asm"` (C-BIOS's placeholder for a ROM BASIC it never ships — `multiple`/`rombas`/`rombas_niy` + the dead runloop/statement dispatch tables; zero external references). Frees `$2812–$3FFF` (6126 B) in page 0, contiguous with page 1. | `edb0844053a3d428aaef95fcd9106972079bde34` |
| 2 | `key-trap-hook.patch` | `main_msx1_eu` | Adds the **function-key delivery hook** BASIC's `KEY` trap needs: `H_ZKEY` (`$FFCF`, in the span the hook-area init already `$C9`-fills) plus a 5-byte `call`/`jr c` at `put_key_fnk`. `A` in/out = the fn-key index, `CF=1` ⇒ swallow the delivery. Deliberately thin — no trap-table knowledge in the BIOS, so semantic changes never re-pin this sha1. See [`docs/spec-traps-t3-key.md`](../docs/spec-traps-t3-key.md) §4 and [`basic/keytrap.asm`](../basic/keytrap.asm). | `557aed9352cf8367eabb9a3cc081c83252579ab9` |

**Why patch #2 exists at all.** No published MSX hook can see the current frame's
`KEYBUF` insertion — both `H.KEYI` and `H.TIMI` run *before* the keyboard scan, measured
on C-BIOS *and* on a Philips VG-8020, and a sweep of all ~112 hook slots with a program
running found no post-scan seam. A real MSX needs no hook because there BASIC *is* the
BIOS and its `KEY` trap sits inside the scan; zerobas has no such seam, so it adds one.

Patch #1 alone makes the repacked ROM differ from stock in **exactly 363 bytes**, all within `$3193–$3A70`,
all zeroed (the removed dead code) — jump table, font, `CGTABL`, and the page-1 region
stay byte-identical. Boundary is `$2812` (proven achievable), not the `$23BF` the sizing
analysis first estimated (its pre-font-gap figure was optimistic — see the spec §6).

## Reproduce

```sh
git -C ~/projects/cbios worktree add /tmp/cbios-repro v0.29-3-gb5ad9cb
cd /tmp/cbios-repro
git apply /path/to/zerobas/cbios-repack/eu-drop-statements.patch
git apply /path/to/zerobas/cbios-repack/key-trap-hook.patch
make derived/bin/cbios_main_msx1_eu.rom
shasum derived/bin/cbios_main_msx1_eu.rom   # -> 557aed9352...
```
