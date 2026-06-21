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

## The two demonstrator tests

| Test | Tier | Stubs | Asserts against |
|------|------|-------|-----------------|
| `test_tokenise.py` | pure logic (no BIOS, no I/O) | none | the oracle-validated token format (constants pulled from the symbol file) |
| `test_getdpb.py` | I/O-bound, via dependency mocking | `fat_mount`, `fat_total_clusters` | the 18-byte DPB, byte-for-byte vs the National CF-3300 oracle |

`test_getdpb.py` shows the key technique: GETDPB reads the disk through the FDC,
so its two I/O dependencies are trapped and replaced by callbacks that leave
exactly the scratch a real 720 KB mount would — then GETDPB's own field assembly
runs for real and is checked against the oracle.

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
   (Tests assemble to `/tmp` so they never touch committed ROMs.)
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
