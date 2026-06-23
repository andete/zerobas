# Feasibility: a clean-room "game-loader" MSX-BASIC for C-BIOS

C-BIOS deliberately ships **no MSX-BASIC** — that is its defining gap. Most
cartridge games never touch BASIC (which is why omitting it is viable), but the
small `.BAS` *loader stubs* that boot many disk and tape titles do need an
interpreter. This note records whether a clean-room reimplementation is feasible,
at what scope, and how it would be staged.

## Verdict

**Yes — legally sound and, at the chosen scope, practically tractable.**

- **Legal.** Clean-room is proven by C-BIOS itself. This project already practises
  the required discipline: the reference ROM is an *oracle, not an answer key*, and
  anything only matchable by looking at the original is **quarantined**, not copied
  (see `docs/openmsx-harness.md`).
- **Scope.** This is **not** full-language compatibility. The target is *enough
  interpreter to run the typical small programs that boot games*. That deliberately
  defers the single nastiest sub-component — the Microsoft Binary Format (MBF)
  floating-point package — because loaders are dominated by integer / hex-address
  math, `POKE`/`CALL`/`BLOAD`, not `SIN`/`RND`.
- **Method.** Spec-driven, optionally LLM-assisted, with **contamination avoided at
  any cost** (see `CONTRIBUTING.md`).

In zerobas the clean-room implementation and its provenance live **together**: the
BASIC `.asm` (`basic/`), this feasibility note and the behavioural specs
(`basic/docs/`), and the oracle probes + harness (`probes/`). The locally-supplied
oracle corpus of game-loader `.BAS` files stays out of the tree, like reference ROMs.

## Keep it a separate project from C-BIOS

For all the reasons above — public disassemblies, the GW-BASIC lineage, and the
fact that the implementation is only ever "clean" to the extent its provenance
holds up — the BASIC ROM should be a **completely separate project** (its own repo,
its own release), **not merged into C-BIOS**.

The point is a legal firewall. C-BIOS is mature, widely distributed, and uncontested;
folding an experimental BASIC reimplementation into it would put that standing at
risk if a provenance or IP challenge to the BASIC code ever arose. As an independent
component, BASIC is combined with C-BIOS **at runtime** (it occupies the BASIC ROM
region the BIOS hands off to via `CALBAS $0159`), never in C-BIOS's source tree. A
legal problem with BASIC then stays contained to the BASIC project and cannot
contaminate C-BIOS. This subdirectory is a staging area for the spec/oracle work;
the implementation graduates to its own repo, not upstream.

## What "boot a game" actually requires

Loader stubs lean on a narrow slice of the language:

- **Interpreter core:** tokeniser / detokeniser, line storage (linked-list program
  text), direct + program execution loop, expression evaluator with precedence.
- **Statements:** `PRINT CLS SCREEN COLOR WIDTH KEY CLEAR DEFUSR POKE VPOKE OUT
  WAIT LET DIM DATA READ RESTORE IF/THEN/ELSE GOTO GOSUB/RETURN FOR/NEXT END STOP
  REM CALL` (and the `_` extended-statement form) `BLOAD BSAVE RUN LOAD SAVE`.
- **Functions:** `PEEK VPEEK INP USR VAL STR$ CHR$ ASC LEN LEFT$ RIGHT$ MID$
  INKEY$ ABS INT SGN`, plus `&H` / `&O` / `&B` literals.
- **Types:** integer + string + **minimal** single-precision float; full MBF
  double-precision math deferred.
- **Device I/O is out of scope.** `BLOAD`/`LOAD` delegate to the cassette BIOS and
  the Disk ROM through existing hooks (`PHYDIO $0144`, the `H.*` hooks). The
  interpreter reaches the handoff and lets those perform the transfer.

## Three things that decide it

1. **MBF float is deferrable.** Loaders rarely need it, so it is pushed to a later
   phase, keeping the tractable core small. This is the biggest single win.
2. **The token table is a documented *interface*, not free design.** A tokenised
   `.BAS` file must detokenise byte-compatibly. The keyword→token map is public
   (MSX2 Technical Handbook, MSX Assembly Page) and independently confirmable by
   black-box oracle (type a known program, `SAVE`, read the bytes). It is treated as
   an interface specification — reconstructed, never copied from a disassembly.
3. **Contamination is the live risk.** Annotated MSX-BASIC disassemblies are public,
   and Microsoft's **GW-BASIC** source (same Microsoft-BASIC lineage) is online but
   still copyrighted. Either would poison provenance — for human readers *and* for
   any LLM context. The firewall in `CONTRIBUTING.md` is the
   load-bearing safeguard.

## Phased roadmap

Each phase ships something useful and stands alone.

- **Phase 0 — Feasibility note + policy.** This document plus
  `CONTRIBUTING.md`. Pure docs; no code. **Done.**
- **Phase 1 — First light: `BLOAD"name",R`.** *Before assembling any corpus*, the
  very first engineering step is a minimal vertical slice (a tracer bullet) that
  makes a single `BLOAD"FILE",R` work: just enough tokeniser + execution loop to run
  that one statement, the `BLOAD` handler delegating to the cassette/Disk hooks, and
  the `,R` handoff that transfers control to the loaded binary's entry. No full line
  editor or boot-to-`Ok` is needed — the line is injected via the oracle harness
  (`CALBAS $0159` / direct-line injection). This one idiom boots a large share of
  disk/tape titles and proves the entire pipeline — tokenise → execute → device hook
  → handoff — end to end before any breadth work. Validated against the oracle.
- **Phase 2 — Data-driven scoping (corpus + oracle).** *Now* collect a corpus of
  *real* game-boot `.BAS` loaders from a locally-supplied corpus (
  git-ignored like `roms/`). Mechanically catalogue the exact statement / function /
  token surface they use, to confirm or narrow the list above. Broaden the
  interpreter oracle probes under `probes/basic/` (built in Phase 1) to cover
  it, dumping the documented work-area sysvars (`TXTTAB`, `VARTAB`, `ARYTAB`,
  `STREND`, …). Reuse the `Cart` and encoder helpers in `probes/lib/z80probe.py`.
- **Phase 3 — Interpreter breadth.** Flesh out the statement / function set the
  corpus actually demands (integer + string + minimal single float, `&H` literals,
  control flow, `POKE/PEEK/VPOKE/OUT/INP`, `DEFUSR/USR`, `CALL` dispatch), plus the
  line editor / boot-to-`Ok` where a loader needs interactive entry. Tokeniser /
  detokeniser against the documented token table; program storage.
- **Phase 4 — Full load/save set.** `BSAVE/RUN/LOAD/SAVE` (beyond the Phase 1
  `BLOAD`) wired to the cassette BIOS and Disk ROM hooks.
- **Phase 5 — Differential validation.** Run the loader corpus under openMSX on the
  new BASIC versus a reference oracle; byte / behaviour diff per the established
  classification (pass / quarantine / bug), tracked in `CONTRIBUTING.md`.
- **Later (out of subset).** The MBF floating-point package and the full statement
  set.

## Open decision

Whether to keep the methodology pure spec-driven or go hybrid (LLM-assisted) is
deferred to the end of Phase 1: the corpus scoping will reveal how much surface
there actually is, which determines whether LLM assistance is worth its guardrail
cost.
