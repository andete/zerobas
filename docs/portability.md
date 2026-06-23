# Portability — building & testing zerobas beyond macOS

zerobas is developed on macOS. This document records what makes it portable to
**Linux** and **Windows**, and the state of each piece. The work here is host-tooling
only — **the `.asm` sources, the provenance logs, and the clean-room firewall are
untouched.**

## Status

| Area | Linux | macOS | Windows |
|------|:-----:|:-----:|:-------:|
| Build the ROMs (`make build/basic.rom disk`) | ✅ | ✅ | ✅¹ |
| Build the patches (`make` / `make patches`) | ✅ | ✅ | ✅¹ |
| Emulator-free unit tests (`make unit-test`) | ✅ | ✅ | ✅¹ |
| Install openMSX machines (`make machines`) | ✅ | ✅ | ✅¹ |
| openMSX oracle probes (`probes/`) | ✅ | ✅ | ✅¹ |
| Automated CI | ✅ | local² | ✅ |

¹ Windows needs a Unix-style `make` + `pasmo` on `PATH` (MSYS2 / Git Bash / WSL).
  No code blocks Windows — there is no shell-script or hardcoded-path dependency.
² macOS is built locally by the author; it is not a CI job (the hosted macOS runners
  bill at 10× on a private repo). See *CI* below.

## What the build actually needs

The **deliverable build** needs only `pasmo` + `python3` + `make` (+ a `/bin/sh`-style
shell for `make`'s recipes). All Python tooling is pure standard library and uses
`os.path.join`, so path separators are already correct on Windows. **No part of the
deliverable build needs openMSX** — that is only for `make machines` and the probes,
and those need *your own* reference ROMs, which are never shipped.

The **unit tests** (`make unit-test`, [`../tests/`](../tests/README.md)) are the
portable regression gate: an embedded Z80 core runs the assembled ROM directly, with
**no emulator and no reference ROMs**. They need only pasmo + python3.

## What was fixed (and how)

The original blockers were hardcoded macOS paths and a `/bin/sh` dependency.

1. **One place for host paths — [`../tools/openmsx_paths.py`](../tools/openmsx_paths.py).**
   Cross-platform discovery of the openMSX share dir, user dir, the `openmsx` binary,
   and the stock C-BIOS ROM — with Linux, macOS, **and Windows** candidates. The
   macOS-only candidate lists that used to be copied across several scripts are gone.

2. **The patch build is now Python, not shell —
   [`../tools/build_patches.py`](../tools/build_patches.py).** It replaces the two
   `build-patches.sh` scripts (deleted), so the patch build runs with no shell on any
   OS. Verified to reproduce all four committed `.ips/.bps` patches byte-for-byte. The
   `Makefile`s call it directly; pass `STOCK=<rom>` or let it auto-detect.

3. **The machine installer
   ([`../tools/install-openmsx-machine.py`](../tools/install-openmsx-machine.py))** now
   imports the shared discovery, gaining Windows `share`/user-dir support.

4. **The openMSX probes are PATH-first.** Every probe now resolves the emulator via
   `$OPENMSX` → `PATH` (`shutil.which`) → platform fallback, instead of hardcoding
   `/opt/homebrew/bin/openmsx`. So `openmsx` on `PATH` just works everywhere.

## CI

[`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) has two jobs, each of
which builds the ROMs, smoke-imports the host tooling, and runs `make unit-test`:

- **`linux`** (ubuntu-latest) — installs pasmo from apt (it is in Ubuntu *universe*).
- **`windows`** (windows-latest) — runs inside **MSYS2**, so the existing Unix-style
  Makefile (`mkdir -p`, `cp`, `rm`, `python3`) works unchanged. pasmo has no Windows
  package, so the job builds it from source (`./configure && make`) in the same
  environment. The repo-wide [`../.gitattributes`](../.gitattributes) forces LF line
  endings so the runner's `autocrlf=true` cannot corrupt the Makefile or the tracked
  binary patches.

Neither job builds the `.ips/.bps` patches (they need a stock C-BIOS ROM, not a pure
build input) or runs the probes (they need your own reference ROMs).

**macOS CI is intentionally omitted**: the author builds macOS locally, and the
hosted macOS runners bill at 10× on a private repo. The macOS toolchain is verified
to work (pasmo 0.5.5 builds from source on macOS); a macOS job can be added later by
building pasmo from source in a `runner.os == 'macOS'` step.

> **First-run note.** The Windows job exercises a toolchain (MSYS2 + a from-source
> pasmo) that cannot be validated without a Windows runner, so its first runs on
> GitHub may need a round or two of adjustment — that is exactly the proof-of-build
> signal it exists to provide.

## Known non-blockers

- The `Makefile` recipes use `mkdir -p`, `cp`, `rm -rf`, and `/tmp` (the `probe`
  target). These are fine under the Unix-style `make` Windows uses (MSYS2 / Git Bash /
  WSL). Making the Makefile cmd.exe-native is out of scope.
- `pasmo` itself has no Windows package; users build it from source or fetch a binary.
  Documented in the README build table.
