<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-JRSLICE — the `jp`→`jr` peephole seam, banked: +51 B of main page 1

Status: **✅ SHIPPED. +51 B of main page 1** (free **2 → 53 B**), on `469a820`.
`basic-reloc.rom` `0d04f8b7 -> f213a97d`, merged `dd90f859 -> f9eeae8f`,
`sub.rom` unchanged `490ffc49`. Route D of [`spec-carve-scout-2026-08.md`](spec-carve-scout-2026-08.md) §3b,
turned from a measurement into bytes.

---

## 1. The seam, and why it is the safest carve class in the tree

A `jp cc,X` whose target is already within `jr` range is a `jr cc,X` at −1 B.
`scratchpad/peephole_catalog.py` walked the assembled image and found **155
convertible sites, 120 in page 1** (the full control-transfer catalog is 172 B
nominal / 126 in page 1; the `jp`→`ret` class is **0** — already exploited).

🎯 **`jp` and `jr` are flag-identical and control-flow-identical.** The only
difference is range, and pasmo *enforces* range — a too-far `jr` fails the build.
So **"it assembles" ≡ "it is correct"**: no flag-liveness, no
position-independence proof, no differential needed to *establish* safety. The
battery here is confirmation, not the safety argument.

## 2. What landed — 51 of the clean 52, and the one the assembler caught

`scratchpad/peephole_apply.py` located each page-1 site by its target LABEL
(resolved from the `.sym`), converting only where `jp <cc,>label` is UNIQUE in
source — 52 sites. 15 files, exact `jp`→`jr` swaps, alignment and comments
preserved.

🔴 **ONE OF THE 52 WAS REVERTED BY THE ASSEMBLER, AND IT IS THE MEMORY LESSON
LANDING AGAIN.** `basic/pdfcb-body.inc` is a body shared BYTE-IDENTICALLY
between the main image and a sub-ROM tenant. The conversion was in range in
main (which is what the ROM walk measured on `basic-reloc.rom`) and **out of
range in sub**, where the same source sits at a different address — so the
*sub* build failed `Relative jump out of range`. The apply tool checked one of
the two builds; the assembler checked both. **A shared `*-body.inc` has two
answers, and only the assembler knows the second** ([[fnexpr2-slice]],
[[rom-region-structure-review]]). Reverted; the other 51 assemble in every
build they appear in.

## 3. The layout shifts — so the ABI is the gate that matters

Converting 51 page-1 instructions moves every label after each one, which
re-addresses most of page 1. The load-bearing check is therefore not any
functional gate but **`subrom-abi-check` / `subrom-closure-check`**: the sub-ROM
calls into main by address, and those addresses all moved.

    OK: sub/basic-resident-abi.inc matches a fresh regen from build/basic-reloc.sym
        (12 resident-ABI addresses, sub.rom is not stale)
    OK: 586 routines in the closure of 24 page-1 tenants ... No main-page-1 escape.

Both green: the ABI regenerates from the main `.sym`, so the sub→main surface
followed the shift intact.

⚠️ **Three gates timed out on the first battery and passed clean on re-run**
(`tmfp-acceptance`, `array-acceptance`, `graphics-acceptance`). The tell that it
was apparatus, not this change: two timed out on a *reference* machine
(`National_CF-3300`, `Philips_VG_8020`) — which a zerobas edit cannot affect —
and `array`'s 16 blank rows were CONTIGUOUS and then RECOVERED (rows 152/154
passed after the stall). Host load near the end of a hours-long run. Re-run:
`array` 146/146, `tmfp`/`graphics` PASS, identical ROM hash. Read the screen
before believing a red row ([[apparatus-is-part-of-the-measurement]]).

## 4. What is NOT banked, and why

* **68 more page-1 sites** — the `jp`s whose target label is a shared tail
  (`raise_error` ×3, `str_eval_no` ×6, `fp_runtime_error` ×2, …), not uniquely
  locatable by `(mnemonic,label)` text. Those need address-precise mapping (a
  listing pasmo 0.5.5 does not emit), so they are a follow-up, not a decline.
  The catalog says they are worth ~69 B more in page 1.
* **The 35 low-region sites** — convertible, but they fund the *low* wall
  (10 B), not page 1. Deferred with the page-1 remainder.
* **Speed.** `jr` is 12/7 cyc vs `jp` 10, so a hot loop would keep its `jp`. None
  of the 51 sites is a measured hot path (they are verb-grammar and error edges);
  a per-site speed review was not needed for correctness and was not done.

## 5. The other tricks in the family, measured

Prompted by a series of Z80 size-trick suggestions; each measured for THIS tree:

* **`SLA A` → `ADD A,A`** and the shift/rotate class: **0 candidates, already
  exhausted** — 17 `add a,a`, 149 `xor a`, 13 `rlca` already in place
  (`scratchpad/peephole_scan.py`, calibrated non-blind).
* **`LD A,0` → `XOR A`**: 9 sites, ≤9 B, and **not mechanical** — `xor a`
  clobbers every flag where `ld a,0` clobbers none, so each needs flag-liveness.
* **The opcode-swallow multi-entry trick** (`db 0x01`/`0x21` hiding a `ld r,n`
  in a `ld rr,nn` operand to merge entry points): **measured 10 mergeable
  groups, ~40 B, and DECLINED WITH NUMBERS** — see §6.

## 6. 🔴 The opcode-swallow trick: applicable, and declined

`scratchpad/skipbyte_scan.py` found 10 groups of ≥2 trampoline preambles
(`ld r,const` / `jr shared`) that could chain through a byte-swallowing fake
opcode — ~40 B nominal. The biggest are the cleanest tables in the codebase:
`fatprim_bounce` (12 disk selectors), `dop_emit` / `tk_op_emit` (8 operator
entries each), `raise_error` (6 error raisers).

**Declined, on two grounds the earlier classes do not carry:**

1. 🔴 **It widens clobber contracts.** Swallowing a 2-byte `ld a,n` requires
   `db 0x01`/`0x21` (`ld bc,nn` / `ld hl,nn`), so all 12 disk primitives would
   newly trash BC or HL. That is a SEMANTIC change to each routine's clobber
   set — the opposite of `jp`→`jr`'s safety-by-construction — and any caller
   relying on the register breaks silently, catchable only by the differential.
2. ⚠️ **It trades the project's co-equal deliverable.** These groups are
   self-documenting dispatch tables; the swallow turns each into a fall-through
   chain no disassembler reads and no maintainer safely reorders, for 1 B apiece.

Same shape as the de-eviction decline ([[rom-region-structure-review]]):
measurable bytes, weighed on the scale the project actually optimizes, and lost.
The `jp`→`jr` seam banks more (51 vs 40 B) at zero clarity or clobber cost, so it
is strictly the better spend and this one is filed as measured-not-taken.
