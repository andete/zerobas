# SPEC — D-DUPSPAN2: the rest of the byte-identical spans, priced by a tool

Status: **✅ LANDED 2026-08-22.** A pure **funding** slice for `DEF FN`: no BASIC
behaviour changes, and that is the whole claim. Baseline `b61d350`, clean:
low **46 B** / main page 1 **54 B** / sub page 0 **3075 B** / sub page 1 **1624 B**.

D-DUPSPAN spent the two `ld a,N / jp raise_error` families out of
[`scratchpad/dupspan_sweep.py`](../scratchpad/dupspan_sweep.py)'s table for a
measured **+50 B**, and left the remainder with a warning attached: the sweep
prints a "recoverable" total *it says out loud it cannot justify*, because three
things decide a collapse and it can see none of them.

This slice reads the remainder — **by building the instrument, not by eye.**

---

## 1. 🎯 The finding: the filed supply does not exist

The estimate carried into this slice was *"roughly 200 B of SAFE dup-span
carve"*, read by hand off a tool that prints **403 B**
([`deffn-impl-2026-08-22.md`](deffn-impl-2026-08-22.md) §7). Measured:

| reading | B | what it is |
|---|---|---|
| `dupspan_sweep.py` nominal | **403** | every byte of every duplicate, if collapsing were free |
| position-independent | **162** | ends in a terminator · no escaping `jr` · not entered by fallthrough |
| …and same-region | **119** | *and* does not alias across the low / page-1 boundary |
| **shipped** | **+122** | 28 aliases, built |

🔴 **THE HAND READING WAS WRONG IN BOTH DIRECTIONS, AND ON NAMED GROUPS.** Two
of the groups the previous session listed as *"judged safe-looking and
unspent"* are not safe at all, and the tool says why in one line each:

* **`sav_ascii_flag` / `sav_cas_flag`, 20 B** — the span ends
  `jp nz,$64AB`. A CONDITIONAL jump is not a terminator: the span runs off its
  own end into different code in each copy.
* **`eostr_lp` / `eokey_lp`, 13 B** — ends `ld de,$0000`, no terminator at all,
  *and* its `jr c` at offset 8 targets offset 13, one past the span.

That is 33 B of the ~200 B estimate that was never there. Against that, the
tool also found the widening charge over-stated (below).

---

## 2. The instrument — [`tools/dupspan_indep.py`](../tools/dupspan_indep.py)

The sweep's own header names three things it cannot decide. Each is decided
here **from `build/basic-reloc.rom` + `.sym`**, by decoding Z80 instructions:

1. **Does the span end in a real terminator?** `ret`, `jp nn`, `jr d`, `jp (hl)`,
   `reti/retn`. `ret nz` and `jp nc,X` are not.
2. **Do its relative jumps land inside it?** A `jr`/`djnz` encodes a
   DISPLACEMENT, so two byte-identical spans with a `jr` leaving the span jump
   to two DIFFERENT addresses.
3. **Is the label entered by fallthrough?** Decided by decoding the PREDECESSOR
   span and asking whether IT terminates. Then the collapse needs a `jp` left in
   place: recovery is `len-3`, and at `len <= 3` it is worth nothing.

🎯 **AND A FOURTH THE SWEEP'S AUTHOR HAD NOT NAMED: THE REGION CONTRACT.** Main
low (`$2812-$3FFF`) is switched OUT under a sub page-0 tenant and main page 1
(`$4000-$7FFF`) is switched out under a page-1 tenant. Aliasing a LOW label onto
a PAGE-1 address hands every page-1 tenant that reaches it an address that is
not mapped — `affn_found equ cal_srv_ret` would move a `float-arith.asm` exit
into page 1, and CIRCLE's page-1 tenant calls the float pack. This is not a byte
property and no amount of decoding finds it; `--samereg` prices the carve that
cannot have the problem at all. **43 B of otherwise-safe carve is deferred to
§6 for exactly this reason.**

A span whose instructions do not TILE EXACTLY to its end is reported UNKNOWN and
never counted safe: a mis-decode may not produce a green answer. 9 of the 1455
spans are UNKNOWN.

### 2.1 🔴 Calibration, and the plant that was wrong

`--selftest` runs two halves and exits non-zero if either fails.

**Synthetic**, 8 planted spans with known answers — one per verdict, so a
checker that says "safe" by construction cannot pass. ⚠️ **The first draft of
one vector was mislabelled and the checker was right**: `18 fe` is a self-loop,
whose target is offset 0 — *inside* the span — so `SAFE` was the correct
verdict for a plant named `p_relout`. The vector is now `18 05` and the
self-loop is a ninth plant, asserting `SAFE`.

**Real, known-answer**: the `3 B ×6` bare `jp raise_error` group, which
D-DUPSPAN read by hand and recorded as **five of six entered by fallthrough
from a different `ld a,N`** ([`spec-basic-dupspan.md`](spec-basic-dupspan.md)
§2.1). The tool reproduces the 5, names them, and names `pl_parse_err` as the
one reached only by jump. **A calibration on a hand reading is what makes the
tool's disagreements in §1 worth believing.**

---

## 3. What was carved — 28 aliases in 16 files

| region | before | after | delta |
|---|---|---|---|
| main page-0 low | 46 B | **92 B** | **+46 B** |
| main page 1 | 54 B | **130 B** | **+76 B** |
| sub page 0 | 3075 B | 3075 B | 0 |
| sub page 1 | 1624 B | 1624 B | 0 |

**Total +122 B of main ROM.**

⚠️ **`build/sub.rom` MOVED, AND THAT IS CORRECT HERE** — unlike D-DUPSPAN, whose
carve was page-1 only. `sub/basic-resident-abi.inc` is GENERATED from
`build/basic-reloc.sym`; this carve moves the low region (`__MEAS_LOW_END`
`$3FD2` → `$3FA4`), so the addresses the sub-ROM imports change. Both images are
re-hashed in §5.

Every name survives as an `equ` on `gfx_absent equ gfx_err5`'s precedent, and no
call site was retargeted. The only call-site edits are **21 `jr` → `jp`
widenings** forced by distance.

### 3.1 The prediction, and the 3 B it missed by

The tool predicted **119 B** net (148 B gross − 27 B of estimated widening,
including `dr_stored`'s 3 B which was then declined — see §6). Measured
**+122 B**.

🎯 **THE WHOLE 6 B DELTA IS THE WIDENING TERM, AND THE TOOL SAID IT WOULD BE.**
It prices widening by scanning the ROM for `jr`-opcode bytes that target an
aliased address — a scan that cannot tell a `jr` opcode from a data byte, so it
OVER-reports, and its own output says the assembler is the authority. Predicted
27 B, the assembler demanded **21**. `119 − 3 (declined) + 6 (widening) = 122`,
exactly.

---

## 4. Why the collapse is observable-free

Same argument as D-DUPSPAN §3, extended to spans that are not error tails: a
span that (a) is byte-identical, (b) ends in an unconditional terminator, (c)
contains no relative jump leaving itself and (d) is not entered by fallthrough
**has no way to tell which of its copies it is**. Its inputs are its registers
and RAM, which the collapse does not touch; its only exit is an address encoded
absolutely, identical in both copies. Points (b)–(d) are what `dupspan_indep.py`
decides, and every alias below carries a verdict line from it.

---

## 5. Gates

Run clean → `make repack-machine` → probe, every `rc=` read individually — no
pipe and no `&&` chain, because `make` exits 2 for any failed recipe.

**Static (12):** `unit-test` · `deadcode` · `audit-citations` ·
`wall-assertion-check` · `redundant-load-check` · `rowshape-check` ·
`injector-check` · `preflight-check` · `latch-check` · `diskdep-check` ·
`diskdep-selftest` · `kwsweep` (MISSING=1, unchanged — this slice adds no verb).

**Emulator (11), all rc=0:**

| gate | reading |
|---|---|
| `graphics-acceptance` | **383 PASS / 0 FAIL** — the tally at `b1a01be` |
| `graphics-floor-acceptance` | PASS (page-0 tenant under EI; 0 VDP latch mismatches) |
| `lineerr-acceptance` | **210/210**, `DEFERRED` empty |
| `namspc-acceptance` | **102/102** |
| `strparen-acceptance` | **16/16** |
| `fldwidth-acceptance` | **47/47** |
| `cassave-acceptance` | 20/20 |
| `castail-acceptance` | 31/31 scored, 1 pinned divergence |
| `dskmsg` / `diskbasic` / `fat-error` | green |

**ROM identities after the carve:** `basic-reloc.rom` **`c2f7bba6`**,
`sub.rom` **`e7ca18e8`** (from `834c45b5` / `b91622a9`). 🔴 **The four knife
suites' pinned baselines move with them** — `scratchpad/dupspan_knives.py`,
`paintbord_knives.py`, `paintmc_knives.py`, `paints2seed_knives.py` are pinned
against `('834c45b5','b91622a9')` and must be re-baselined deliberately, not
edited into agreement.

### 5.1 🎯 What these gates CANNOT say, and it is the same thing D-DUPSPAN said

A green battery says the collapse **broke nothing**. It cannot say the collapse
was **observable at all**: an aliased site nothing exercises stays green through
any mistake made to it. D-DUPSPAN answered that with a per-site row set whose
knife cut the canonical VALUE, so a site that did not redden was a site the
battery could not see.

**This slice does not have that row set, and the substitute is stated rather
than implied**: every alias here carries a MACHINE-CHECKED verdict from
`dupspan_indep.py` — decoded terminator, decoded relative jumps, decoded
predecessor — which D-DUPSPAN's hand reading did not have, and which is
calibrated against that hand reading (§2.1). That is an argument about the
MECHANISM where a row set is an argument about the OBSERVABLE, and they are not
substitutes. **The per-site row set is FILED, not folded in.**

### 5.2 A 0-byte apparatus fix carried by this slice

`tools/gen_resident_abi.py` hardcoded `LOW_CEILING = 0x3FE5` under a comment,
and a docstring, that both called it `__MEAS_LOW_END`. The build MEASURES that
label every run: it read `$3FD2` before this carve and `$3FA4` after, so the
constant was 19 B and then 65 B too high, and the guard was that much weaker
than it claimed. It now reads the label out of the sym file the tool already
loads. 🎯 **Calibrated on a known positive**: `fp_add` planted at `$3FD0` — a
value the old constant PASSED — is flagged. Both ROMs byte-identical across it.
⚠️ `make wall-assertion-check` could not have caught this: its stated SCOPE is
TODO.md's `- [ ]` items, where a stale figure misleads the next SLICE. A stale
figure inside a GATE misleads the gate, and nothing reads it.

---

## 6. Declined, with reasons rather than numbers

* 🔴 **`dr_stored equ dl_run` (3 B) — DECLINED, and the reason is in the tree's
  own prose.** Both are `jp run_prog`. But `dr_stored`'s comment records a
  DELIBERATELY UNSHIPPED one-line change (`jp run_prog_top`) that D-RUNLINE
  left standing because the form it fixes cannot be rowed
  ([`spec-basic-runline.md`](spec-basic-runline.md) §4). An `equ` would make
  that future edit silently apply to BOTH sites. **An alias erases an identity,
  and here the tree says in writing that the identity is wanted.**
* **43 B of cross-region carve — DEFERRED, not declined.** `exps_print` (12 B),
  `vsf_wb_int` (7), `elas_err`/`exf_syn` (8), `ex_def_err` (3),
  `exps_fallback` (3), `inpc_synpop` (3), `flt_int_result` (3), `dc_finish` (3),
  `rl_break` (2), `affn_found` (2), `cut_lp` (1). Each needs a REACHABILITY
  proof (is this label reached from a tenant of the opposite kind?), and
  🔴 **the gate that would answer it may be blind to the question**:
  `check_tenant_closure.py` filters `equ` names as VALUES rather than
  LOCATIONS (D-PINDATA's own rule), so it may not follow an alias across the
  boundary at all. **Testing that gate on a deliberately-bad cross-region alias
  is the next slice, and it is worth more than the 43 B.**
* Everything the tool marks UNSAFE / WORTHLESS: 241 B of the 403 B nominal, each
  with a one-line machine-checked reason in `tools/dupspan_indep.py`'s output.
