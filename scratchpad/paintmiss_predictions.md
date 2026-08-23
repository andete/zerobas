# D-PAINTMISS — predictions, written BEFORE the after-run

Fix: `basic/graphics.asm` `ex_paint`, 4 of `ep_default_b`'s 6 jump instructions
(the four reached only AFTER a comma has been consumed) retargeted to a new
`ep_missing: jp loc_missing`. 3 B of main page 1 (4 B free -> 1 B free).
Baseline = `docs/spec-basic-clrtrap.md` §2, `scratchpad/circmiss_sib2.out`.

## The 16-row after-run (`scratchpad/circmiss_sib2.py`)

| row | before zb | PREDICTED zb after | why |
|---|---|---|---|
| `p.colour`  | `0 15` | `24 4` | site :707, C slot, terminator |
| `p.kcolour` | `0 15` | `24 4` | site :709, C slot, COLON |
| `p.b`       | `0 15` | `24 4` | site :726 via the comma that ends a given C |
| `p.kb`      | `0 15` | `24 4` | site :728, same route, COLON |
| `p.cc`      | `0 15` | `24 4` | site :726 via ep_c_empty's shared comma |
| `p.kcc`     | `0 15` | `24 4` | site :728, same route |
| `p.none`    | `0 15` | `0 15` UNMOVED | site :701 kept on ep_default_b |
| `p.omit`    | `0 15` | `0 15` UNMOVED | never touches ep_default_b at all |
| `p.plain`   | `0 15` | `0 15` UNMOVED | site :718 kept on ep_default_b |
| `p.ok`      | `0 15` | `0 15` UNMOVED | reaches ep_draw directly |
| `q.*`/`t.*` | as filed | UNMOVED | CLEAR is a different file; 6 rows |

**6 DIFF -> 0 DIFF. Every PAINT row unanimous with both references.**
The four `q.*`/`t.*` CLEAR divergences stay open and are NOT this slice.

## The knives (`scratchpad/paintmiss_knives.py`), 10 PAINT rows each

* **K-PM1** — site :701 (`jr nz,ep_default_b`, "no fields at all") -> `ep_missing`.
  PREDICT exactly **1** row moves: `p.none` `0 15` -> `24 4`.
  Nothing else reaches :701 — every other row has a comma.
* **K-PM2** — site :718 (`jr nz,ep_default_b`, "no ,B") -> `ep_missing`.
  PREDICT exactly **1** row moves: `p.plain` `0 15` -> `24 4`.
  `p.ok`/`p.b` have a comma there and fall through.
* **K-PM3** — site :707 back to `ep_default_b` (one defect site reverted).
  PREDICT exactly **1** row moves: `p.colour` `24 4` -> `0 15`.
* **K-PM4** — site :726 back to `ep_default_b`.
  PREDICT exactly **2** rows move: `p.b` AND `p.cc` -> `0 15`.
  🎯 This is the knife that MEASURES the two-routes claim: one instruction,
  two rows, and they arrive by different paths.
* **K-PM5** — `jr z,ep_c_empty` (:705) -> `jr z,ep_missing`.
  PREDICT exactly **3** rows move: `p.cc`/`p.kcc` stay `24 4` (already 24, so
  they do NOT move) ... **AMENDED**: `p.cc`/`p.kcc` are already `24 4`, so the
  only row that MOVES is `p.omit` `0 15` -> `24 4`. Exactly **1**.
  That is the row nothing else pins — the legal C-omitted-BETWEEN-commas form.

## Confidence

* K-PM1/K-PM2/K-PM3: HIGH (single-site, single-row).
* K-PM4: HIGH on the count, and it is the interesting one.
* K-PM5: MEDIUM — the amendment above was made while writing this file, which
  is itself the finding that `p.cc`/`p.kcc` cannot detect K-PM5 any more once
  the fix has landed. If a second row moves, the routing model is wrong.
