# cbios-repack — tracked patches that repack C-BIOS to free page-0 space

Part of the C-BIOS repack arc ([`../docs/spec-cbios-repack-tooling.md`](../docs/spec-cbios-repack-tooling.md)).
These are **our own 0BSD patches** against a pinned C-BIOS source tag — they describe
edits to BSD-2-clause C-BIOS source, so **no C-BIOS bytes live in this repo** (decision
D1). The build applies a patch to the user's `~/projects/cbios` checkout, rebuilds, and
diffs the result vs pristine stock to emit the shipping IPS. A patch is a description of
a diff, not a merge — the provenance firewall holds.

## Pinned base

- Checkout: `~/projects/cbios`, tag **`v0.29-3-gb5ad9cb`**
- Stock `cbios_main_msx1_eu.rom` sha1 `baf2e9c69252fd9b350b488d89c71887b9d05eec`

## Patches

| Patch | Variant | Effect | Repacked sha1 |
|---|---|---|---|
| `eu-drop-statements.patch` | `main_msx1_eu` | Comments out `include "statements.asm"` (C-BIOS's placeholder for a ROM BASIC it never ships — `multiple`/`rombas`/`rombas_niy` + the dead runloop/statement dispatch tables; zero external references). Frees `$2812–$3FFF` (6126 B) in page 0, contiguous with page 1. | `edb0844053a3d428aaef95fcd9106972079bde34` |

The repacked ROM differs from stock in **exactly 363 bytes**, all within `$3193–$3A70`,
all zeroed (the removed dead code) — jump table, font, `CGTABL`, and the page-1 region
stay byte-identical. Boundary is `$2812` (proven achievable), not the `$23BF` the sizing
analysis first estimated (its pre-font-gap figure was optimistic — see the spec §6).

## Reproduce

```sh
git -C ~/projects/cbios worktree add /tmp/cbios-repro v0.29-3-gb5ad9cb
cd /tmp/cbios-repro
git apply /path/to/zerobas/cbios-repack/eu-drop-statements.patch
make derived/bin/cbios_main_msx1_eu.rom
shasum derived/bin/cbios_main_msx1_eu.rom   # -> edb0844053...
```
