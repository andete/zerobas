# SPEC — D-XREG: the cross-region aliases, and the gate that was not blind

Status: **✅ LANDED 2026-08-22.** The third funding slice for `DEF FN`, and the
one that answers a question the second slice deliberately did not.

[`spec-basic-dupspan2.md`](spec-basic-dupspan2.md) §6 deferred **43 B** of
position-independent dup-span carve for a reason that was not about bytes:

> Each needs a REACHABILITY proof … and 🔴 **the gate that would answer it may be
> blind to the question**: `check_tenant_closure.py` filters `equ` names as
> VALUES rather than LOCATIONS (D-PINDATA's own rule), so it may not follow an
> alias across the boundary at all. **Testing that gate on a deliberately-bad
> cross-region alias is the next slice, and it is worth more than the 43 B.**

Both halves are now measured. The gate is **not** blind, and the carve is **46 B**.

---

## 1. The numbers

| region | before (`824a1c2`) | after | delta |
|---|---|---|---|
| main page-0 low | **92 B** | **102 B** | **+10 B** |
| main page 1 | **130 B** | **166 B** | **+36 B** |
| sub page 0 | 3075 B | 3075 B | 0 |
| sub page 1 | 1624 B | 1624 B | 0 |

**+46 B of main ROM**, 10 aliases in 7 files, plus 5 `jr` → `jp` widenings.
ROMs `6c2470ef` / `d911acbc` (from `c2f7bba6` / `e7ca18e8`).

📏 **Predicted 51 B gross − 5 widenings = 46 B. Measured 46 B.** The widening
term was exact this time, where D-DUPSPAN2's over-reported by 6 — the tool says
plainly that it cannot tell a `jr` opcode from a data byte, so it is right for
the wrong reason as often as not, and the assembler stays the authority.

**Running total for the arc:** main free **100 B → 268 B** across
D-DUPSPAN2 + D-XREG.

---

## 2. 🔴 The knife, and the first draft that went red for the wrong reason

**K-XR1** aliases the one cross-region label the pre-flight (§3) calls FATAL —
`affn_found equ cal_srv_ret`, a `basic/float-arith.asm` exit moved into page 1,
where a page-1 tenant has main page 1 switched OUT — and requires
`make basic-reloc` to go RED.

⚠️ **DRAFT 1 WENT RED AND TAUGHT NOTHING.** `jr nz,affn_found` cannot reach
`$6760` from `$33xx`, so **pasmo** stopped the build on a relative-jump range
error before `check_tenant_closure.py` ever ran. Red, and not one word about the
gate. **A knife that reddens through a different mechanism than the one under
test is a knife that has not been run.** The widening is now part of the knife,
because it is part of the carve: a cross-region alias has to ASSEMBLE before
anything else can judge it.

🟢 **DRAFT 2, with the caller widened, is decisive:**

    python3 tools/check_tenant_closure.py build/basic-reloc.sym sub/basic-resident-abi.inc
    FAIL: page-1 escapes in the tenant's resident closure — these routines/bytes
    are switched OUT while the page-1 tenant runs, so calling or reading them
    affn_found = 6739  <- called

🎯 **THE SUSPICION IS REFUTED, AND THE REASON GENERALISES.** The gate does not
care what SHAPE a name has in the source: it resolves every callee's ADDRESS out
of `build/basic-reloc.sym`, where an `equ` and a `label:` are indistinguishable
by construction. D-PINDATA's *"an `equ` is a VALUE, only a `label:` is a
LOCATION"* rule is about which references count as EDGES on the way IN, not
about how a target is resolved once it is one. **Every cross-region alias in
this tree is gated on every build.**

⚠️ **And a partial second guard falls out of draft 1**: for a LOW → PAGE-1
alias, any `jr` caller in the low region cannot reach a page-1 target, so pasmo
refuses. That catches some of the class for free — but only the ones with `jr`
callers. A `jp`-only caller sails past the assembler and needs the closure gate.

---

## 3. The pre-flight — [`scratchpad/crossreg_probe.py`](../scratchpad/crossreg_probe.py)

Not a second opinion competing with the gate: a way to know which aliases to
WRITE before spending a build on each. It uses the gate's own graph builders.

    page-1 tenant ABI seeds: 12    main labels reachable from them: 124
    MAIN addresses the sub build is given at all: 12
      (arga_pack_fac=$3389 … penderr_set=$281D … widen_uint_to=$3B8D)
    ...of which are in main PAGE 1 (>= $4000): 0
      -> a page-0 tenant has no main page-1 address to call

🎯 **THE SECOND LINE IS WHY MOST OF THE 43 B WAS SAFE ALL ALONG**, and it is the
same measurement D-DEFFNEV §3.1 made from the other side: **no page-0 tenant in
this tree can reach main page 1 at all**, so a PAGE-1 → LOW alias cannot be
reached by a tenant whose mapping hides the low region. **Nine** of the twelve
candidates are safe for that reason and need no walk. Of the **three** LOW →
PAGE-1 ones, two are outside the 124-label page-1 closure (`inpc_synpop`,
`flt_int_result`) and one — `affn_found` — is inside it.

**The probe and the gate agree exactly, on the one FATAL and on the eleven
others.** That agreement is the calibration.

🔴 **AND THE FIRST DRAFT OF THAT SECOND LINE PRINTED A HARDCODED `0` UNDER A
LOOP THAT APPENDED NOTHING** — a constant wearing the clothes of a reading, with
**eight of the twelve verdicts resting on it**. Caught by re-reading the probe
before committing, not by anything the probe did. It is measured now, and the
measurement is an enumeration rather than a walk: the sub build can only name a
MAIN address that some included file DEFINES for it (anything else is an
undefined symbol and pasmo refuses), so the question is decidable by listing
them — **12 imports, every one below `$4000`, and the tool prints all twelve
with their addresses.** If that set ever gains a page-1 entry the probe now says
so and voids its own premise in the same breath.

---

## 4. What was carved

| alias | canonical | B | direction |
|---|---|---|---|
| `exps_print` (a `jp`, not an `equ` — fallthrough) | `ems_print` | 13 | p1 → low |
| `vsf_wb_int` | `asw_wb_int` | 8 | p1 → low |
| `flt_int_result` | `evsgn_settype` | 6 | low → p1 |
| `elas_err` (and `exf_syn`, already its alias) | `ems_err_pop1` | 4 | p1 → low |
| `exps_fallback` | `ems_fallback` | 4 | p1 → low |
| `inpc_synpop` | `ex_let_err` | 4 | low → p1 |
| `ex_def_err` | `ee_synerr_pop` | 4 | p1 → low |
| `rl_break` | `lgb_eof` | 3 | p1 → low |
| `dc_finish` | `ed_done` | 3 | p1 → low |
| `cut_lp` (a `jp` — fallthrough) | `zf_lp` | 2 | p1 → low |

**Declined, unchanged from D-DUPSPAN2 §6:** `affn_found` (3 B, proved FATAL) and
`dr_stored equ dl_run` (3 B, whose own comment records a deliberately unshipped
future edit that an alias would silently apply to both sites).

---

## 5. And the dup-span family is now measured EMPTY at the cheap end

[`scratchpad/nearspan_sweep.py`](../scratchpad/nearspan_sweep.py) asks the
question between `dupspan_indep` (byte-identical) and `clone_scout` (source-shape
near-clones): **which spans are identical except at ONE byte?** That is the shape
D-DUPSPAN's own carve had — fourteen `ld a,N / jp raise_error` tails differing
only in `N`.

    denominator: 1203 decodable spans >= 4 B; 148 pairs differ in exactly ONE byte
    MEASURED-USABLE at the cheap end: 0 B
    2 pairs whose immediate is MID-SPAN: ~6 B, and a free register

🎯 **ZERO, AND THE ZERO IS THE DELIVERABLE.** Of 148 one-byte-different pairs,
not one has its difference as the immediate of its FIRST instruction with both
spans position-independent — the only arrangement where a caller can set the
value and jump to a shared tail for free. The rest differ in a relative
DISPLACEMENT, in half an ADDRESS, or mid-span. **The `ld a,N / jp tail` supply
that funded `DEF FN`'s first 50 bytes is exhausted, and this says so with a
denominator instead of a shrug.**

---

## 6. Gates

Clean → `make repack-machine` → probe, every `rc=` read one at a time.

**Static (12):** `unit-test` · `deadcode` · `audit-citations` ·
`wall-assertion-check` · `redundant-load-check` · `rowshape-check` ·
`injector-check` · `preflight-check` · `latch-check` · `diskdep-check` ·
`diskdep-selftest` · `kwsweep` (MISSING=1). And `make basic-reloc` itself, which
runs `check_tenant_closure.py` **three ways** — that is the gate this slice
leans on and K-XR1 is why it may.

**Emulator (11), all rc=0:** graphics **383 PASS / 0 FAIL** · graphics-floor
PASS · lineerr **210/210** (`DEFERRED` empty) · namspc **102/102** · strparen
**16/16** · fldwidth **47/47** · cassave **20/20** · castail **31/31 scored** ·
dskmsg **15/15 gated rows** · diskbasic · fat-error.

⚠️ **A DETACHED BATTERY IS A CORRUPTED BATTERY.** An earlier run of this slice's
driver was launched with `... &` inside a backgrounded command — breaking the
tree's own never-detach rule — and when a later run truncated the shared
`RESULTS` file, the older process appended its own tail into it. Two runs, one
result file, and no way to tell whose line was whose. The driver stamps a
per-run directory now (`batt_$$`) and writes a `DONE n targets` sentinel, and
the run above is a single clean one from `rm -rf build`.

---

## 7. What the last 26 B is NOT

`DEF FN` is **294 B against 268 B free** with this carve in
(`scratchpad/deffn_measure_over.py` on `deffn-draft`: `__MEAS_PAGE1_END`
`$8080`, 128 B past the ceiling, 102 B free low). **26 B**, from 350 B when the
verb was written and 72 B when the eviction was built.

The two cheap shaves were PRICED rather than guessed, and both came in under
their filed estimate:

* **`ex_deffn`'s own eviction: 9 B, not the ~10–17 filed.** The stub is 43 B
  against 52 — and the reason it is not smaller is the out-of-memory
  disposition. `var_alloc_or_find` becomes `scv_alloc` sub-side, so main only
  learns about OOM through a status code, and turning that code back into a
  fault needs `ld a,FPERR_OOM / call penderr_set / jp fp_runtime_error` — 8 B
  of main, because `penderr_set` is the interpreter's single set-if-empty
  writer (D-PENDERR) and lives in the low region, which a page-0 tenant cannot
  reach. Writing `FPERR` raw from the tenant would break first-error-wins
  everywhere except here.
* **The servicer's answer in `E`: 5 B, not ~9.** Three sites lose their
  `ld (FN_REQ),a` (3 B each), but two of them must set the register AFTER the
  `call` that would clobber it, which costs the saving back in branch
  restructuring. And it leans on `subrom_call`'s DE pass-through, which is
  documented (*"a tenant may take DE as an arg"*) but unexercised while the
  tenant is a stub.

**14 of 26.** So the remainder is `tools/clone_scout.py`'s ~96 B of genuine
near-clone refactors — a different class, in `expr.asm`'s term and expression
layers and `usr.asm`'s two index parsers, each differing in TWO places (an
operation AND a register convention) rather than one. That is a slice of its
own, in the hottest code in the tree, and it is not this one.
