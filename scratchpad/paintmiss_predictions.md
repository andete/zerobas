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

---

## 🔴 CORRECTION, appended 2026-08-23 AFTER the run — K-PM5 above is NOT the knife that ran

**The K-PM5 entry above describes a knife that could not be built, and it was
left standing rather than edited, because the reason it could not be built is
the finding.**

* **As predicted above:** point `jr z,ep_c_empty` (`:705`) at `ep_missing`.
  🔴 **That orphans the `ep_c_empty` label.** `make deadcode` then reports an
  unreachable span, the build fails, and **no ROM is produced** — a knife that
  cannot be run at all, which is the same class the tree's own rule names as
  *"cut a VALUE, not a CALL"*. **A jump is a call for that rule whenever it is
  the last edge into its target.** Caught while drafting the runner, before the
  build; the entry above is what I had written down first.
* **As actually run:** `ep_c_empty`'s `inc hl` → `nop` (both 1 B, size-neutral).
  The shared comma is no longer consumed, so `ep_parse_b` reads it as a fourth
  argument and answers **ERR 2**, not 24.
  **PREDICTED: exactly 3 rows move — `p.cc` / `p.kcc` / `p.omit` → `2 4`.**
  **MEASURED: exactly those 3.** ✅ EXACT.
* ⚠️ **The amendment paragraph above is therefore reasoning about the wrong
  knife**, even though its conclusion — *`p.omit` is the only row the old
  version could still move, because `p.cc`/`p.kcc` are already 24* — is true and
  is what sent me looking for a cut that reddens all three.
* 🎯 **What this costs:** `p.omit` is pinned by ONE knife, through a mechanism
  (ERR 2) that is not the one it is a detector for (ERR 24). Nothing
  size-neutral points `ep_c_empty`'s own route at the raiser. Recorded in
  `docs/spec-basic-paintmiss.md` §6 as a limit, not as coverage.
