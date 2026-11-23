# cbios-repack — tracked patches that repack C-BIOS to free page-0 space

Part of the C-BIOS repack arc ([`../docs/spec-cbios-repack-tooling.md`](../docs/spec-cbios-repack-tooling.md)).
C-BIOS's licence, which applies to the C-BIOS code these patches edit and to the
compiled result shipped in the root `.ips` / `.bps`: [`LICENSE.C-BIOS`](LICENSE.C-BIOS).

These are **our own BSD-2-Clause patches** against a pinned C-BIOS source tag — they describe
edits to BSD-2-clause C-BIOS source, so **no C-BIOS bytes live in this repo** (decision
D1). The build applies a patch to the user's `~/projects/cbios` checkout, rebuilds, and
diffs the result vs pristine stock to emit the shipping IPS. A patch is a description of
a diff, not a merge — the provenance firewall holds. The full firewall argument for
the merged main-ROM deliverable (source side + output side, with the empirical proof
against the shipped IPS) is [`../docs/cbios-repack-provenance.md`](../docs/cbios-repack-provenance.md).

## Pinned base

- Checkout: `~/projects/cbios`, commit **`c0c0b31`** on `prepare-0.33` ("DSPFNK and ERAFNK: keep HL in SCREEN 2"; C-BIOS
  keeps that branch fast-forward only). Rebased 2026-11-22 (D-CBIOS032) from tag `v0.31` onto fff98e8, and
  2026-11-23 (D-CBIOSC0C0) onto c0c0b31.
- Stock `cbios_main_msx1_eu.rom` sha1 `e21fc321623187ee101feaa57b9dd5206b9e1f44`
- Repacked (the three patches below, in order): sha1 `c918e86e98aa0ce3b2477c110bcf25934b631adf`
  (tools/build_repacked_cbios.py pins both)

🔁 **Rebased on C-BIOS fff98e8 (2026-11-22, D-CBIOS032).** C-BIOS 0.32 and its `prepare-0.33` branch took over what
zerobas had carried as patches: the tape, the function-key line, the INLIN editor, the music player, CHRGTR,
the fixes zerobas proved against the VG-8020 (CLRSPR, PUTQ, TUPC / TDOWNC, the boot key flush) and the
function-key trap -- and, as c0c0b31 (2026-11-23), the last four fixes zerobas carried: the slot in A at a ROM's
INIT, DSPFNK clearing GRPHED (in SCREEN 0 / 1 only, as the VG-8020 and NMS 8250), INLIN's A = $0D after Enter, and
DSPFNK / ERAFNK keeping HL in SCREEN 2. Every behaviour patch is therefore RETIRED -- C-BIOS's own body passes the spec page
(zerobas `tools/cbios_review.py`; scratchpad/AE_cbios_review_d23.out, AE_cbiosd23_vs_zerobas.out). The 39-row
v0.31 table, with each patch's reasoning and measurements, is in this file's git history (before 2026-11-22).

## Patches

Applied **in order** by [`tools/build_repacked_cbios.py`](../tools/build_repacked_cbios.py).

| # | Patch | Effect |
|---|---|---|
| 1 | `eu-drop-statements.patch` | Drops the cartridge statements (`CALL ...`; `include "statements.asm"`): zerobas's BASIC is the only BASIC. |
| 2 | `eu-drop-dead-strings.patch` | `str_basic` / `str_nocart` (173 B after the font) never print on the merged machine -- the boot scan reaches zerobas's BASIC first -- so they alias `str_error_prompt` and BASIC starts 173 B lower. |
| 3 | `dead-bodies-main.patch` | Cuts what the merged ROM never reaches (zerobas `scratchpad/cbios_reach.py`): the bodies zerobas overlays -- SYNCHR / CHRGTR / GETYPR / OUTDO (BASIC's own text contracts), ISCNTC / CKCNTC, ISFLIO, CALBAS (they need BASIC) -- each jump-table slot a `ret`; the US GRAPH / CODE scan tables nothing reads (192 B); the debug hex printers. 200 B after the font, the rest widens the pads the islands use. |

zerobas overlays a few more bytes at merge time (tools/build_mainrom.py PATCH_SPEC, guarded by C-BIOS's own
labels): the RST $08 / $10 / $18 / $28 vectors and ISCNTC / CKCNTC / ISFLIO / OUTDLP / CALBAS / SETC's slots point at
zerobas's bodies, and CHPUT's TTYPOS store (chput+27) keeps BASIC's 0-based column.

## Reproduce

```sh
git -C ~/projects/cbios worktree add /tmp/cbios-repro c0c0b31
cd /tmp/cbios-repro
for p in eu-drop-statements eu-drop-dead-strings dead-bodies-main; do
  git apply /path/to/zerobas/cbios-repack/$p.patch
done
make derived/bin/cbios_main_msx1_eu.rom
shasum derived/bin/cbios_main_msx1_eu.rom   # -> c918e86e98...
```
