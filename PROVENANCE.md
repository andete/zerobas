# Provenance log

Every constant, address, data table, and algorithm in zerobas must appear here
with an independent **allowed** source, or be explicitly **quarantined**. An
unexplained magic value blocks release.

- **sourced** — traced to an allowed source (see README.md for the list).
- **quarantined** — no allowed source found; derived from spec or stubbed,
  **never copied** from a reference ROM or any MSX-BASIC / GW-BASIC disassembly.

The behavioural source `spec-bload-r.md` is this project's own black-box oracle
observation, captured in the `msx-preservation` repo
(`cbios-basic/docs/spec-bload-r.md`).

## first light: `BLOAD"CAS:",R` (src/main.asm, src/bload.asm, src/sysvars.inc)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Cartridge ROM header layout (`AB`, INIT, STATEMENT, DEVICE, TEXT, 6 reserved) | 16 bytes at $4000 | MSX2 Technical Handbook, cartridge ROM format | sourced |
| ROM page span | $4000–$7FFF (16 KB) | MSX2 Technical Handbook, memory map | sourced |
| TAPION entry point | $00E1 | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| TAPIN entry point | $00E4 | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| TAPIOF entry point | $00E7 | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| TAPION/TAPIN failure convention | CF set = fail | MSX Assembly Page BIOS call list | sourced |
| TAPIN trashes all registers | — | MSX Assembly Page BIOS call list ("Changes: all") | sourced |
| Binary-file id byte | $D0 | MSX2 Technical Handbook, BSAVE file format | sourced |
| File-header block size | 16 bytes (10× id + 6 filename) | spec-bload-r.md §1 (oracle) + MSX2 Tech Handbook | sourced |
| Data-header layout | start(LE), end(LE), exec(LE) | spec-bload-r.md §1 (oracle) + MSX2 Tech Handbook | sourced |
| Load is verbatim into start..end | — | spec-bload-r.md §2 (oracle) | sourced |
| `,R` handoff = jump to exec address | — | spec-bload-r.md §3 (oracle) | sourced |
| Two tape header tones (one per block ⇒ two TAPION calls) | — | spec-bload-r.md §1 (.cas block layout) + oracle-confirmed (probe PASS on VG-8020) | sourced |
| RAM scratch addresses ($E020–$E025), error marker ($E010) | — | own choice (free page-3 RAM, avoids demo regions) | sourced |

No quarantined items.

## tokeniser + executor (src/interp.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| `BLOAD` keyword token | $CF | spec-tokenise.md (oracle KBUF dump); cross-checks MSX Assembly Page token table | sourced |
| Keywords crunch to one token byte, case-folded | — | spec-tokenise.md §1–2 (oracle) | sourced |
| Non-keyword bytes (strings, punctuation, options) kept verbatim | — | spec-tokenise.md §3 (oracle) | sourced |
| Crunched-line terminator | $00 | spec-tokenise.md §4 (oracle) | sourced |
| Leading spaces skipped at execution | — | spec-tokenise.md §5 (oracle) | sourced |
| `'a'`..`'z'` → uppercase via `− $20` (upcase) | — | ASCII (public) | sourced |
| `RUNFLAG` ($E02F), `TOKBUF` ($E030) | — | own choice (free page-3 RAM) | sourced |

No quarantined items. Note: this build's keyword table holds a single entry
(`BLOAD`→$CF); the in-quote verbatim copy means keyword substrings inside string
literals are not mis-crunched.

## startup header (src/title.asm)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| INITXT entry point | $006C | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| CHPUT entry point | $00A2 | MSX Assembly Page BIOS call list / MSX2 Tech Handbook | sourced |
| Header text ("zerobas version 0.1 / clean-room MSX-BASIC cartridge loader") | — | **own content** (project branding). Same *role* as MSX-BASIC's top-of-screen header before its prompt; **no** reference header text copied (that would be a clean-room violation and a false copyright claim) | sourced |
| CR/LF control codes ($0D/$0A) for CHPUT | — | ASCII / MSX2 Tech Handbook (console control codes) | sourced |

No quarantined items.
