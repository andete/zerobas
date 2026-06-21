# Host-side unit tests (no emulator)

Fast, emulator-free unit tests for zerobas ROM routines. They execute the **real
assembled Z80 machine code** against a flat 64 KB memory using a small embedded
Z80 core — no openMSX, no machine ROM, no VDP/PSG/slots/timing. Each test runs in
tens of milliseconds (including a full `pasmo` assemble) and is deterministic, so
this is the fast regression layer beneath the differential openMSX probes in the
sibling `msx-preservation` repo.

## Run

```sh
make unit-test            # from the repo root
# or individually:
python3 tests/test_getdpb.py
python3 tests/test_tokenise.py
```

No dependencies beyond Python 3 and `pasmo` (already required to build).

## Coverage

```sh
make coverage             # or: python3 tests/coverage.py
```

`tests/coverage.py` monkeypatches the Z80 core's `step()` to log every executed
opcode address (no change to `z80.py`), runs the tests in-process per ROM group,
and buckets the executed addresses against the symbol table to report, for each
labelled routine, whether any test entered it. It's region-*entry* coverage —
"is this routine tested?" — not a byte/line metric. Constants (UPPERCASE) and
named data tables are excluded so they don't masquerade as un-executed code.
Routines behind real disk/FDC/cassette I/O show as uncovered because they're
Tier-3 (openMSX-probe territory), not host-testable.

## How it works

- **`z80.py`** — an embeddable Z80 CPU core (instructions + flags only). Any
  opcode a tested routine reaches is implemented; an unimplemented one raises with
  the PC and byte, so a new test that hits a gap fails loudly and names the opcode
  to add. Swappable for a full core behind the same interface.
- **`msxtest.py`** — the harness. Loads a ROM + the `pasmo` symbol file into
  memory, lets a test `call()` any internal routine **by label**, `trap()`s BIOS
  or in-ROM dependency entry points (each becomes a Python callback), runs to the
  routine's `RET`, and exposes registers + memory for assertions.

A BIOS call (`CHPUT`, `RDVRM`, `DSKIO`, …) or an I/O-bound dependency
(`fat_mount`, …) becomes a Python stub that models the *documented contract*
(MSX2 TH / MSX Assembly Page / datasheet — no disassembly). The test asserts the
routine honours its side; the stub supplies the other side.

## Coverage

| Test | Tier | Stubs | Asserts against (oracle) |
|------|------|-------|--------------------------|
| `test_tokenise.py` | 1 (pure) | none | the token format (constants from the symbol file) |
| `test_expr.py` | 1 + 2 | `RDVRM`, `io_in` (VPEEK/INP) | pure math; MSX-BASIC `TRUE=-1`; the documented div-by-zero contract |
| `test_vars.py` | 1 (pure) | none | the documented 2-char keying / no-alias design; round-trip |
| `test_strvar.py` | 1 + 2 | `CHPUT` | the `[len][bytes]` descriptor layout; ASCII; the CHPUT contract |
| `test_print.py` | 2 | `CHPUT` | base-10 conversion + the documented PRINT-integer framing; CR/LF |
| `test_list.py` | 2 | `CHPUT` | the detok-inverts-tokenise round-trip (self-justifying) |
| `test_screen.py` | 2 | `CHGMOD`/`CHGCLR`/`CLS`/`ERAFNK`/`DSPFNK` | the BIOS-call contracts + the colour sysvars |
| `test_vdpio.py` | 2 | `WRTVRM`, `io_out` | WRTVRM(HL,A) / OUT(port,val) against the fed operands |
| `test_poke.py` | 1 (pure) | none | `mem[addr]=val`; the error-path ERRMARK |
| `test_usr.py` | 2 | the USR target address | the USRTAB vector store; `ev_usr` calls it with `HL=arg` |
| `test_program.py` | 1 (pure) | `CHPUT`/`BREAKX` (neutralised) | the documented line-link layout; insert/replace/delete/relink |
| `test_tape.py` | 1 + 2 | PSG/PPI ports (`io_in`/`io_out`) | the documented FSK frame + STMOTR/PPI/PSG contracts; `tapin` decodes a synthetic waveform |
| `test_getdpb.py` | 2/3 (dep-mock) | `fat_mount`, `fat_total_clusters` | the 18-byte DPB, byte-for-byte vs the National CF-3300 oracle |

`test_getdpb.py` shows the dependency-mock technique: GETDPB reads the disk
through the FDC, so its two I/O dependencies are trapped and replaced by
callbacks that leave exactly the scratch a real 720 KB mount would — then
GETDPB's own field assembly runs for real and is checked against the oracle.

Every expected value is justified by an independent oracle (math, the documented
MSX-BASIC / BIOS contract, a round-trip property, or a symbol-file constant) and
cited in the test — not copied from the ROM's own output. FAT/FDC sector I/O is
genuinely Tier-3 (it needs a disk-controller model) and stays in the openMSX
probes; `test_getdpb.py` already covers the DPB-builder slice of it.

## Scope and limits

- **Establishing truth vs locking it in.** These tests *lock in* behaviour the
  differential probes already established as oracle-true; they can't *discover*
  truth (no reference machine here). Workflow: differential probe (openMSX, slow)
  proves a routine matches real hardware → freeze the bytes → unit test guards
  them fast. Complementary layers, not a replacement.
- **Contract, not BIOS.** A stubbed BIOS validates *zerobas's* side of the call.
  Faithfulness of the stub to the real entry point is the test author's
  responsibility (cite the source, as the code does).
- **Good fits:** the tokeniser, expression evaluator, detokeniser, line-link
  editor, FAT12 math, the DPB builder, PRINT formatting (capture the CHPUT
  stream). **Poor fits (leave in openMSX):** FDC register timing, inter-slot
  CALLF, VDP/interrupt behaviour, the combined-machine integration.

## Adding a test

Drop a new `tests/test_<thing>.py` in place — `tests/run.py` (what `make
unit-test` calls) auto-discovers every `test_*.py`, so there's no runner or
Makefile to edit. Each file assembles its own ROM to `/tmp` and exits 0 on pass.

1. Build to a scratch path and load it: `Machine("/tmp/x.rom", "/tmp/x.sym")`.
   (Tests assemble to `/tmp` so they never touch committed ROMs.) A page-0 patch
   such as `tape/tape.asm` assembles to an image whose first byte is its lowest
   `org`; load it with the matching base, e.g. `Machine(rom, sym, rom_base=0x00E1)`
   — the pasmo symbols are absolute, so they line up regardless.
2. `m.trap("some_bios_or_dependency", callback)` for anything that does I/O.
3. `cpu = m.call("routine", hl=…, de=…)`, then assert on `m.mem[...]` / `cpu.*`.
4. Build expected values from `m.sym[...]` named constants where possible, so the
   test can't drift from `sysvars.inc`.

### Tier-2 helpers (BIOS-stub tests)

The harness has shortcuts for the common console/BIOS patterns:

- `out = m.capture_chput()` — traps `CHPUT` and accumulates every emitted byte;
  read `out` after the call. For `PRINT`/`LIST`/string output.
- `log = m.record("CHGMOD")` — traps a BIOS entry and logs a register snapshot
  per call (`[{'a':…, 'hl':…}, …]`) without modelling an effect. For calls whose
  contract is "invoked with these args" (`CHGMOD`, `WRTVRM`, `CHGCLR`, …).
- `log = m.record_out()` — captures every `OUT (port, val)` (for the `OUT`
  statement). The core also has `cpu.io_in` for `IN`/`INP`.
