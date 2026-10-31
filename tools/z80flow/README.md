<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# z80flow — register contracts for zerobas

Static Z80 control-flow and liveness analysis of the built images (the main
ROM, `sub.rom`, `sub2.rom`, `disk.rom`). For every routine it infers its
**contract**: what it reads on entry, what it changes, how it exits, and which
of the registers it changes its callers actually read afterwards. Comparing the
contracts of two builds finds the interface breaks a rewrite can introduce
("`cmp16_bits` now changes B, and `fp_cmp` reads B after the call").

It checks interfaces only — registers, flags, the stack, how a routine exits —
not memory and not arithmetic. It complements the test battery; it does not
replace it. Python 3, standard library only, no emulator.

Developed in a separate repository (z80flow, up to commit `22ac83a`, with the
measurement runs and the D-REREAD experiment that motivated bringing it here);
this copy is the maintained one from here on.

Clean-room note: the tool reads only zerobas's own build (`build/`) and
sources, and C-BIOS (open source) inside the merged main ROM. It decodes
those images and nothing else.

## Use

```sh
make contract NAME=cmp16_bits      # one routine's contract (all contexts it runs in)
make contract-diff BASE=<rev>      # what changed since <rev>: builds <rev> in /tmp/zerobas, diffs
make contracts                     # every routine -> build/contracts.json
make z80flow-report                # the full measurement report -> build/z80flow/
make z80flow-selftest              # the tool's own tests
```

Each analysis takes about a minute. `make contract` prints, per context:

```
cmp16_bits [main]  inferred
  reads on entry:   DE HL
  changes:          HL A F
  callers read after it: BC DE IX IY ... A F(C)
  outputs callers use:    A F(C)
  a rewrite must keep:    BC DE IX IY ... unchanged
  callers (3): check_preexp_bounds ex_next fp_cmp
```

**The rework workflow** (docs/dev-workflow.md): before changing a routine,
`make contract NAME=...` for it; keep the `; z80flow:` markers on the lines you
edit true; before committing, `make contract-diff BASE=<the commit you started
from>`. Its categories:

| category | meaning | action |
|---|---|---|
| `broken` | the routine now changes a register a caller reads after it on a normal path | fix the routine or the caller (exit status 1) |
| `broken_unwind_only` | the same, but read only after an error reset / restart | usually harmless; look |
| `wider_in` (`_unwind_only`) | it now reads a register on entry it did not before | check every caller sets it |
| `status` | it became harder (or easier) to analyse | a new stack trick may need a marker |
| `exits` | its exit shape changed (returns elsewhere, leaves a frame) | intended? |
| `more_clob`, `fewer_clob`, `narrower_in` | changes no caller notices | confirmations |

Annotation MISMATCH / unused / errors are listed too and also give exit
status 1: a marker that no longer fits its code is reported, never silently
applied. `contract-diff` needs `BASE` to have the markers (any commit from the
one that added this tool on).

## Markers: `; z80flow: KIND ARGS`

The facts static analysis cannot settle are written next to the code they
describe:

```
                ; USR: user machine code in RAM; the published convention hands it HL = DAC,
                ; A = VALTYP (the argument itself is in DAC, memory)
                ; z80flow: targets external reads=HL,A
                ret                         ; -> routine; its RET -> usr_ret
```

- On a comment-only line, a marker applies to the next code line below; on an
  instruction's line, to that instruction; on a label line, to the routine; on
  an `equ` line, to the cell it defines (`stack-anchor`).
- Its justification is the comment block directly above (and any text before
  `z80flow:` on its own line). It is required. Markers directly below one
  another share it.
- Its address is the nearest label above plus the sizes of the instructions in
  between, decoded from the build — and every one of those instructions must
  match its source line's mnemonic, with no `db` / `ds` / `include` / `IF` in
  between. Otherwise it is an error ("put a label closer"), never a guess.
- A file assembled into several images (main and a sub-ROM) gets its markers
  applied in each.

The kinds (full reference: `z80flow/annotate.py`):

| kind | for |
|---|---|
| `inline` (on a routine) | analyse it inside each caller: a small shared dispatcher whose target depends on the caller |
| `stack-effect N\|var` (on a routine) | it returns with SP changed by N for its caller (`var`: data-dependent) |
| `noreturn` / `same-as-callee T` (on a routine) | calls never come back / its contract is T's |
| `targets T.. [external] [reads=REGS] [in=R,..]` | where a `jp (rr)` / computed `ret` (or a `call`) goes; `external` = code in no image (user code), reading only REGS |
| `table ADDR N [stride= offset= inplace]` | the same, from a table of N words (or of `jp`s) |
| `depth N` | the stack depth here is N bytes (the tool checks it where it can) |
| `return` | this `jp (rr)` is a return (the address went through memory) |
| `abort [reads=REGS] [unwind]` | the path ends here and never comes back to this routine's caller |
| `ld-sp N\|same` | this `ld sp` leaves depth N, or moved the stack whole |
| `values PAIR ADDR N ... hi=H` | a register pair holds one of a table's values here |
| `call-never-returns` | this call does not come back |
| `stack-anchor [unwind]` (on an `equ`) | a cell holding an SP saved at a routine's entry depth |

`in=R,..` limits a site marker to the analysis of the named routines.
C-BIOS's few annotations stay in `annotations/cbios-in-zerobas.ann` (its source
is not in this tree).

## What a contract can get wrong

- **Too wide** (it says more is read or changed than really is): safe; the cost
  is a false alarm or a routine left `conservative-boundary`. The report names
  the path; usually a missing marker or a known limit of the tool (below).
- **Too narrow** (it says a register is kept when it is not): the dangerous
  direction. It comes from a wrong marker (an `abort` that does return, an
  `external reads=` that is too small) or a tool bug. Markers are checked where
  the tool can (`checked` / `MISMATCH`); most are `trusted`, resting on their
  justification. A wrong one found: fix it, add a test, and re-run
  `contract-diff` over the recent rewrites.

## Layout

| module | knows about |
|---|---|
| `decode.py`, `analysis.py`, `program.py`, `annotate.py`, `inline.py`, `report.py` | Z80 only (and pasmo source syntax, for the markers) |
| `platform_msx.py` | MSX: the BIOS entries, inter-slot calls, hooks |
| `program_zerobas.py` | zerobas: the ROM layout, the sub/disk ROMs as address contexts, the call-backs, the source images and their include dirs |
| `contracts.py` | `show` / `dump` / `diff` / `diff-rev` |
| `run_zerobas.py` | the full measurement report |

## Known limitations

- Context sensitivity only where an `inline` marker asks for it; any other
  shared routine's summary is the union over its callers.
- Carry and zero are followed where an instruction fixes them; other flags
  and counted loops are not, which is why some `depth` markers exist.
- Hooks: by default a hook is its boot `ret` (except the interrupt hooks);
  `make z80flow-report` also runs with every hook open and lists the routines
  whose contract depends on that.
- Memory is coarse (read / written, yes / no); self-modifying code is not
  detected.
