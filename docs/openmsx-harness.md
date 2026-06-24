# openMSX driving harness

A small, reproducible way to **boot a machine in openMSX headlessly, optionally
insert a cartridge, run to a deterministic point, and dump CPU registers and
memory to a file.** It is the foundation for the (parked) behavioural comparison
of **C-BIOS MSX1** against a real MSX1 BIOS (Philips VG-8020) — see the
"oracle, not answer key" note at the end.

## Why

To find where C-BIOS *behaves* differently from a real BIOS we want to treat the
real ROM as a **black box**: feed identical inputs, observe outputs, never read
its code. That needs a repeatable way to drive openMSX and read machine state
back out. This harness is that capability, proven on both machines.

## Pieces

| File | Role |
|------|------|
| `probes/lib/omsx_run.py` | boot a machine (± cartridge), run to an event, dump regs/memory to a file |
| `probes/lib/probe_cart.py` | mint a tiny **self-authored** test cartridge (Phase-1 sentinel; reused by Phase 2) |

openMSX binary defaults to a local `openMSX.app/Contents/MacOS/openmsx` build;
override with `--omsx` or `$OPENMSX`.

## Quick start

```sh
# 1. mint the sentinel cartridge (INIT writes "JONG" to 0xE000, jumps to DONE 0x7FF0)
python3 probes/lib/probe_cart.py --out /tmp/sentinel.rom

# 2. boot it under C-BIOS, run until the DONE landmark, read the marker back
python3 probes/lib/omsx_run.py --machine C-BIOS_MSX1 --cart /tmp/sentinel.rom \
    --bp 0x7FF0 --reg PC --reg A --mem memory:0xE000:4 --out /tmp/cap.txt

# 3. same cartridge, real MSX1 BIOS
python3 probes/lib/omsx_run.py --machine Philips_VG_8020 --cart /tmp/sentinel.rom \
    --bp 0x7FF0 --reg PC --mem memory:0xE000:4 --out /tmp/cap_vg.txt
```

Both print `mem.memory:0xE000:4=4a4f4e47` (`"JONG"`), proving insert → run →
observe end to end.

`--mem` takes `DEBUGGABLE:ADDR:LEN`; useful debuggables include `memory` (CPU
address space), `VRAM`, `Main RAM`, `VDP regs`, `slotted memory`. List them with
a one-off `puts $f "[debug list]"`.

## The three rules that make it reliable

1. **Headless** = `set renderer none` + `set throttle off`. `omsx_run.py` passes
   the first via `-command` and the second in its generated Tcl.
2. **Capture to a file, never stdout.** openMSX's Tcl `puts` writes to its own
   console, not the host terminal, so all output goes through an `open`/`puts`/
   `close` to a file the wrapper then reads.
3. **Sync on an event, not on emulated time.** Prefer `--bp ADDR` (a breakpoint).
   A real BIOS boots *slower* than C-BIOS: with a fixed `--time 3`, the VG-8020's
   cartridge INIT had **not run yet** while C-BIOS's already had (`0xE000` still
   held the power-on RAM pattern `ff ff 00 00`). Breaking on the cartridge's
   fixed `DONE` landmark (`0x7FF0`) captures exactly when the cart has finished,
   regardless of per-machine boot time. `--time` remains as a fallback and
   defaults to a generous 6 s.

## Keyboard injection (`--type`) and the Enter trap

`--type STRING` schedules `type STRING` in openMSX at the paired `--type-delay`
(emulated seconds). Two things bite repeatedly:

**1. The Enter key must be a *real* carriage-return byte (`0x0D`), not the two
characters `\` `r`.** `omsx_run.py` escapes a literal CR into the Tcl `\r` that
openMSX's `type` turns into an Enter keystroke (see `_tcl_dquote`). If you instead
hand it the backslash-r *text*, it gets escaped to `\\r` and openMSX types a
literal backslash and `r` onto the line — the command is never submitted, and
the symptom is a silent hang/timeout with the line sitting unentered on screen
(e.g. `zb>bload"cas:",r\r` visible in a VRAM dump).

- **From Python** (the probes): a string literal `"\r"` already *is* a CR byte —
  correct. `build_cas(...)`, `basic_probe_bload.py`, etc. all do this.
- **From the shell** (ad-hoc `omsx_run.py` runs): `'\r'` and `"\r"` are the
  literal two characters — WRONG. Get a real CR with `$(printf '\r')`:

  ```sh
  CR=$(printf '\r')
  python3 probes/lib/omsx_run.py --machine C-BIOS_MSX1_EU_BASIC --cassette x.cas \
      --type 'bload"cas:",r' --type-delay 10 \
      --type "$CR"          --type-delay 14 \
      --time 22 --mem ... --out cap.txt
  ```

  To check it landed, dump the screen (`--mem VRAM:0x0000:960`) and decode bytes
  32–127 as ASCII: you should see the typed line *without* a trailing `\r`.

**2. Send Enter as its own later `--type`, not glued to the command.** Under
`set throttle off` a trailing CR in the same burst is often dropped (keys inject
faster than the BIOS keyboard ISR scans), so the line never commits. Put the
command in one `--type` and the CR in a second `--type` a few emulated seconds
later (as the example above does). For a slow-booting REPL target (zerobas
patched into page 1), also push the *first* delay out far enough that INIT has
run `EI` and the prompt is reading keys, or the keystrokes are simply lost.

## Determinism

openMSX is deterministic given the same machine + inputs: two identical runs
produce **byte-identical** dumps (verified with a 32-byte work-area + 32-byte
VRAM capture). The differential comparison depends on this — any byte that
differs between the C-BIOS run and the VG-8020 run is a real behavioural
difference, not noise.

## Machine availability

* `C-BIOS_MSX1` ships with openMSX (its ROMs are bundled) and boots as-is.
* `Philips_VG_8020` resolves too: openMSX's filepool already indexes
  a local `share/systemroms/.../vg8020_basic-bios1.rom`
  (sha1 `829c00c3…`), so `-machine Philips_VG_8020` works with no extra setup.
  If a fresh machine ever fails to resolve its BIOS, drop the systemrom into
  `~/.openMSX/share/systemroms/machines/<vendor>/`.

No copyrighted ROMs are committed — they live only on this machine and are
git-ignored, the same policy as `reference/`.

### Which machine each probe needs

The oracle machine a probe drives is its `MACHINE` / `--machine` default. Four
families are in use across the current probe set (verify the live list with
`grep -rn 'MACHINE *=\|--machine' probes/`):

| Machine | Who provides it | Used by |
|---|---|---|
| `Philips_VG_8020` | **openMSX-shipped**, ROM in the filepool — *no install* | most `probes/basic/*` differential probes (crunch, tokens, print, controlflow, loops, data, statements, screen, vdpio, usr, bload, cload) **and** `probes/tape/cas_baud_oracle.py` + `bios_probe_winwid_idle.py` |
| `C-BIOS_MSX1` | ships with openMSX | a few basic functional probes (cont, list, strvar) |
| `C-BIOS_MSX1[_EU]_TAPE` / `_BASIC` | `make machines` (this repo; C-BIOS + zerobas/tape IPS) | `probes/tape/*` (realtape, the open-stack/tapfile paths) + `basic_probe_*_ondevice`/openstack |
| `C-BIOS_MSX1[_EU]_BASIC_DISK` | `make machines` | `probes/disk/*` zerobas-side (our DSKIO/BDOS/Disk-BASIC) |
| `National_CF-3300` | **user-supplied** proprietary CF-3300 BIOS | `probes/disk/*` reference side (`--ref-machine`) + the `disk_probe_dosboot_*` stock-oracle baseline |
| `National_CF-3300_ZEROBASDISK` | `make machines-oracle` (real CF-3300 BIOS + zerobas-disk in slot 3-1) | the Tier-1 `disk_probe_dosboot_*` provider-oracle runs |

So `make machines` + `make machines-oracle` plus your own `Philips_VG_8020` and
`National_CF-3300` ROMs (already-installed openMSX reference ROMs) cover the whole
set. The VG-8020 needs nothing installed; the CF-3300 BIOS is the one proprietary
oracle you must supply. openMSX version in use: **21.0**. (`probes/README.md`
names the reference machines; this table is the per-probe mapping.)

## Clean-room posture for the parked Phase 2

When this harness is used to compare against the VG-8020, the real ROM is an
**oracle, not an answer key**: it is only ever observed as a black box (inputs →
outputs). Each behavioural difference is recorded as a *bug report* and must be
resolved from an **independent specification** (MSX Assembly Page, MSX2 Technical
Handbook, the TMS9918 / AY-3-8910 / i8255 datasheets) — never by reading or
copying the Philips ROM. Anything that can only be matched by looking at the
original (font bitmaps, data tables, magic constants, exact work-area init
values) is **quarantined**, not copied.

## Idea: probe results as a C-BIOS unit-test suite

The probes are deterministic (same machine + inputs → byte-identical dumps) and
each carries an expected output. That makes them reusable as a **regression test
suite for C-BIOS itself**: re-run every probe against a freshly built C-BIOS and
assert each `pass` still passes, each known `bug` still reproduces (until fixed),
and no new differences appear. Worth doing at some point — it would turn the
one-off differential findings (and the BASIC oracle probes in
`probes/basic/`) into a standing guard against regressions in C-BIOS.
