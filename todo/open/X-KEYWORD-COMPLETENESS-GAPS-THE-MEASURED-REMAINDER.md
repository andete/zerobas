- [ ] **Keyword-completeness gaps — the measured remainder of MSX1 BASIC.**
      **The coverage denominator now exists** (2026-07-26,
      [`docs/kwsweep-msx1-coverage.md`](../../docs/kwsweep-msx1-coverage.md), probe
      [`probes/basic/basic_probe_kwsweep.py`](../../probes/basic/basic_probe_kwsweep.py),
      `make kwsweep`).
      🔴 **THE HEADLINE THAT STOOD HERE — *"of 162 MSX1 reserved words, 124
      tokenise and 34 are genuinely absent"* — IS A 2026-07-27 SNAPSHOT, AND THIS
      ITEM'S OWN `TAB(` STORY IS THE REASON THAT MATTERS.** That story is about a
      claim of *"already faithful (NO work)"* that a differential agreed with for
      the wrong reason; a stale tally in the item that tells it is the same defect
      one level up. 🔴 **AND A COUNT IN PROSE IS UNRUNNABLE BY CONSTRUCTION** — it
      cannot go red when it stops being true, which is why the replacement is a
      COMMAND and not a number:
      * `python3 tools/tier_table.py --keywords` (or `make tiers ARGS=--keywords`)
        — the `kwtable.inc` denominator, the per-keyword reached tier, and the
        **"no known gap"** list, computed through the consumer's own parser.
      * `make kwsweep` — the two-layer measurement itself, whose summary line
        carries SUPPORTED / DIVERGENT / MISSING / SILENT-GAP and the crunch-only
        exclusions with their reasons.
      **Never quote either from here** [[a-justification-parenthesis-is-an-unrun-claim]].
      **Why a sweep existed at all:** `TIME` and `TAB(` were both found *by
      accident*, six days apart, with the same silent shape — the word parses as
      an ordinary variable, nothing errors, the program computes the wrong
      answer. `TAB(` was worse: it had been written down as *"Already faithful
      (NO work)"* in
      [`docs/spec-basic-df2-2-intarg-coercion.md`](../../docs/spec-basic-df2-2-intarg-coercion.md)
      §1.2 because `PRINT TAB(99999)` raises ERR 6 on **both** sides — for
      structurally different reasons (absent `TAB(` ⇒ `TAB` is an *array*, and
      the subscript bound-check yields the same code). **The differential passed
      and the feature did not exist.** That §1.2 claim is doc debt and is
      corrected in this commit.
      - ✅ **SILENT-GAP (was 8) — THE CLASS IS EMPTY (2026-07-27).** The worst
        class: a wrong answer with no error, a live landmine in a user program.
        All eight are now implemented and gated —
        `EQV`/`IMP` (`ef098e9`, 156/156), `TAB(`/`SPC(`/`CSRLIN`/`POS`
        (`99c0f6d`, 67/67), `FRE`/`BIN$` (`2facfc0`, 83/83) — plus `TIME`
        (`2026-07-26`), which was the ninth and which the sweep picked up with
        no edit to the probe. **No MSX1 reserved word silently computes a wrong
        answer.** That was the keyword arc's exit criterion (D-KW-3).
      - ✅ **MISSING (6) — THE CLASS IS EMPTY (2026-07-28).** All five words plus
        D-MISS-1: `LOCATE` · `TRON` · `TROFF` · `MOTOR` landed 2026-07-27, and
        **`SWAP` landed 2026-07-28** once two clone collapses funded it (+45 B
        `fat_rand_*` onto the existing `fatprim_bounce`, +41 B the five TOTAL math
        calls onto one table — neither of them SWAP's own code). Gated by
        `make missing-acceptance` at **214/214 as recorded**.
        `DEF FN`/`FN` stays out — it is an arc, not a slice (D-MC-3).
      - ~~**NO-ORACLE (5).** `MKI$` `MKS$` `MKD$` `CVS` `CVD` ... the probe routes
        these to `National_CF-3300`, which does not yet give a readable SCREEN-0
        capture under `omsx_repl`~~ 🟢 **DEAD (D-KWORACLE, 2026-09-03): the
        oracle READS.** A 14 s boot and a `SCREEN 0` prologue were the whole
        fix; all five, plus `CVI` added later, return real verdicts against that
        machine. The class is EMPTY.
      - ~~**18 crunch-only** — destructive (`DSKO$`, `IPL`), interactive (`AUTO`,
        `INPUT$(n)`), non-terminating (`WAIT`), printer-bound with the known
        unplugged-`LSTOUT` hang hazard (`LPRINT`, `LLIST`, `LPOS`, `LFILES`),
        disk-fixture-dependent (`COPY`, `SET`, `ATTR$`, `DSKI$`, `LOC`)~~
        🟢 **MOSTLY DEAD (D-KWDISK / D-KWRIG / D-KWTAPE, 2026-09-12), and every
        category above was a claim about the PROBE rather than about the verb:**
        `DSKO$` is a round trip through a private copy of the image, `IPL` is
        `Illegal function call` on the CF-3300 too (it was never destructive
        here), `COPY` `SET` `DSKI$` `LOC` `ATTR$` all execute against the mounted
        fixture, `WAIT` has a mask chosen from a measured port, and `LPRINT`/
        `LPOS` read the head COLUMN back off the SCREEN with a plugged printer —
        the LSTOUT hang is real and is what the `NEEDS-PRINTER:` rig exists for.
        🔴 **WHAT SURVIVES IS `AUTO`, `INPUT$(n)`, `LLIST` and `RENUM`**, each
        with a measured reason recorded in the drain block, not a suspected one.
        ⚠️ **AND THE PROBE'S OWN "NOT EXECUTED — N words, crunch-only" FOOTER
        OVERSTATES THE HOLE**: several of those rows are SUPERSEDED by executed
        rows added beside them (`lprint`/`lpos`/`delete`/`wait` each have a
        `*kw` twin), so the row count and the count of keywords with no support
        evidence are different numbers. The second one is the honest one and only
        `tier_table --keywords` computes it [[readout-blind-to-its-own-subject]].
      - ⚠️ **`INPUT$` is the one to watch:** it crunches *identically* to the
        reference (`INPUT` is a keyword and `$` follows), so layer 1 says
        "present" while support is untested — the exact `INTERVAL` shape. Open
        under the **I/O** item above; the sweep has **not** settled it.
      **Scope boundary:** reserved words only. Statement *option* surfaces
      (`SCREEN 3`, `KEY LIST`, argument forms of words that *are* present) are
      not covered — a word can be present and still wrong in its third argument.
      **✅ SLICED + COSTED 2026-07-27** —
      [`docs/decision-kwgaps-slicing.md`](../../docs/decision-kwgaps-slicing.md),
      **awaiting sign-off** (D-KW-1..3). The sweep was **re-pinned** against a
      clean-built HEAD first (`git=e9843c4`,
      `zerobas-main-eu.rom=05f43b…`→`4ea7a2…`): **every tally unchanged**, so the
      8/6/5 finding was not an artifact of the stale over-ceiling build. All 14
      reference tokens are now **oracle-measured** from Layer 1's own crunch diff
      (table in the coverage doc) rather than read off Table 2.20.
      ⚠️ **The funding premise in the line this replaces was stale AND wrong.**
      Page 1 is no longer 14 B over — it is **375 B free** (low region 5 B) after
      the FAT tenant-shim collapse (`6f8ac0f`, +367 B: thirteen byte-identical
      34 B shims onto one shared body), which answered D-KW-1 "carve first". More importantly the item is not blocked on *funding* but on
      **placement**: `sub.rom` had **≈8 KB free** on 2026-07-26
      (4509 B page-0 + 3497 B page-1)
      and `kwtable.inc` entries + leaf compute already live there, so the only
      number that matters per keyword is its **main-ROM dispatch glue** —
      and `exec_stmt` is a 67-entry linear `cp`/`jp z` chain charging **5 B per
      statement token before it does anything**. Recommended first slice:
      **`EQV`/`IMP` via a table-driven logical layer** — `ev_xor`/`ev_or`/`ev_and`
      are uniform at 34 B each (measured), so one generic 5-entry layer lands both
      words for **≈ 0 net bytes**.

      ✅ **Steps 1, 2 and 4 are DONE and the exit criterion is MET** — the
      SILENT-GAP class is empty (see above). Each slice was funded by collapsing
      a clone group it was itself a member of, and each one's calibration battery
      turned up pre-existing silent divergences nobody was looking for (two per
      slice, three slices running).

      **What remains of this arc, in order:**
      - **The MISSING class (6)** — ✅ **LANDED 2026-07-27 except `SWAP`.**
        `LOCATE` · `TRON`/`TROFF` · `MOTOR` + D-MISS-1 are in and gated
        (163/163 as recorded, 20 expected-divergent, every marker carrying a
        reason). Spec, as-built costs and the two places the spec turned out to
        be WRONG:
        [`docs/spec-basic-missing-class.md`](../../docs/spec-basic-missing-class.md).
        ✅ **`SWAP` LANDED 2026-07-28** — 183 B (re-measured from clean; the
        split had recorded 186 B), funded by two repack-only clone collapses and
        leaving 44 B banked (SWAP + its dispatch arm + the two operand guards =
        198 B against the 242 B the carves freed). **"Flipping the flag plus one probe line is the whole
        of the wiring" was WRONG**: `SWAP_RESIDENT` guarded only two of the three
        sites the spec claimed — there was no `stmt_table` dispatch arm at all, so
        the first run had all 20 `swap` rows reporting `syntax error`,
        indistinguishable from SWAP being absent. The gate also found that SWAP
        accepted non-name operands (`SWAP A,1` → `Illegal function call` plus
        trailing output, where the reference says `Syntax error`) — fixed with an
        `is_letter` guard at the *handler's own depth*, because sw_operand is
        `call`ed and the abort chain returns into its caller (D-CUR-D).
        ✅ **CHARACTERISED 2026-07-27**,
        [`docs/missing-vg8020-characterization.md`](../../docs/missing-vg8020-characterization.md),
        probe [`probes/basic/basic_probe_missing.py`](../../probes/basic/basic_probe_missing.py),
        `make missing-characterize` (`BOOTPC=1` for the confirmation run) —
        175 cases, 8 batteries, every number boot-per-case. **SLICED + COSTED**,
        [`docs/decision-missing-class-slicing.md`](../../docs/decision-missing-class-slicing.md),
        **awaiting sign-off (D-MC-1..4)**.
        ✅ **D-MC-2 SIGNED OFF 2026-07-27**: D-MISS-1 folds into this slice,
        D-MISS-2 gets its own. ✅ **D-MC-4 O-1 CLOSED** before any clamp was
        written (battery `locrow`, `make missing-characterize ONLY=locrow`,
        18 rows, batched + boot-per-case identical): **`LOCATE`'s row clamps to
        the console's own bottom row**, which moves with `KEY` (reference 22 at
        `KEY ON`, 23 at `KEY OFF`; zerobas 23 in both) — **not** a literal 23 and
        **not** `CRTCNT`, which measures 24 on both machines everywhere. Also
        measured for the spec: the argument domain has **two** error stages
        (`Overflow` past int16, `Illegal function call` outside `0..255`), and
        the five tokens are pinned from the reference's own crunch
        (`LOCATE $D8`, `SWAP $A4`, `TRON $A2`, `TROFF $A3`, `MOTOR $CE`).
        📋 **SPEC WRITTEN, awaiting sign-off (S-MC-1..5)**:
        [`docs/spec-basic-missing-class.md`](../../docs/spec-basic-missing-class.md)
        — 300–420 B against 420 B free, proposed **repack-only** so the lean
        cart stays byte-identical, ordered cheapest-first
        (`MOTOR` → `TRON`/`TROFF` → D-MISS-1 → `LOCATE` → `SWAP`).
        ✅ **D-MC-1 SIGNED OFF + D-KW-2 LANDED 2026-07-27**: the `exec_stmt`
        dispatch table replaced the 69-entry `cp`/`jp z` chain, **page-1 free
        311 B → 420 B (+109 B)**, dispatch block 377 B → 268 B, and the
        per-token cost is now 3 B instead of 5 B. Gated by
        [`tests/test_stmt_dispatch.py`](../../tests/test_stmt_dispatch.py) in
        `make unit-test`: **all 121 entries** (52 lean + 69 repack) reach the
        handler the pre-refactor chain sent them to, plus the fallthrough paths.
        ⚠️ It moves the **LEAN** cart too (shared code) — `LEAN_SHA256` updated
        deliberately in the same commit, as `tools/check_reloc.py` requires, and
        lean is gated per-entry exactly like repack. **The first version of that
        gate was green and worthless** — it read its expectations from the table
        under test, and passed with `PRINT` deleted and `CLS` re-pointed; the
        fix was an expectation recovered from the pre-refactor chain in git.
        **The measurement changed the plan: the class does NOT fit.** The
        roadmap costed it as dispatch glue only, on the premise that bodies live
        in `sub.rom`; but four of the five touch interpreter-core state (cursor,
        variable table, line executor) and are real statements. Measured against
        whole-statement spans already in the tree (`ex_color` = **100 B** for the
        same 3-optional-argument parse shape, with no bound check and no clamp),
        the five come to **300–405 B + 25 B glue against 311 B free**. So
        **D-KW-2 is now a prerequisite, not an option** — exactly as this item
        predicted. Its saving is re-measured on the current tree and confirms the
        estimate: 69 entries, 345 B of chain → 223–231 B of table, **−114…−122 B**.
        Surface highlights the spec turns on: `LOCATE`'s bound is
        **`WIDTH`-relative** and all three arguments are byte-domain-then-clamped
        (`0,255` accepted, `0,256` → `Illegal function call`); `SWAP` requires
        **exact type equality** (`%`≠`!`≠`#`), and its **second** operand must
        already exist while the first may be created; `TRON` traces per **LINE**,
        never in direct mode, survives `RUN` but not `NEW`; `MOTOR` is three
        forms and everything else is `Syntax error` — and
        [`tape/tape.asm:175`](../../tape/tape.asm:175) **already implements `STMOTR`
        (`$00F3`)** with the matching convention, so its body is a parse and a
        `call`.
      - **`DEF FN`/`FN`** — ⚠️ **THE FILED PRICE IS PART MEASURED AND PART
        REFUTED, 2026-08-22**, by
        [`docs/deffn-scout-2026-08-22.md`](../../docs/deffn-scout-2026-08-22.md)
        (`scratchpad/deffn_scout.py` + `.out`, four rounds, both references
        agreeing on every row). It read *"an arc, not a slice (200–400 B): a
        definition table, argument binding, re-entrant evaluation"*.
        ❌ **NO DEFINITION TABLE EXISTS IN THE CRUNCH.** `FN` is ONE token,
        **`$DE`** — the byte immediately after `USR`'s `$DD`, whose statement
        (`ex_def`) and function (`ev_f_usr`) paths both already ship — and the
        NAME is stored as plain ASCII after it, arbitrary length, read at run
        time like any identifier. Here the same line crunches `46 4E` ("FN" as
        text), one byte longer per occurrence, which is why `DEF` reaches
        `stmt_error`; `basic/usr.asm`'s own comment already names the hook.
        ✅ **`ERR 18` AND ITS MESSAGE ALREADY SHIP** (`err_msgtab` entry 18,
        `sub/errmsg.asm` `em_undef_fn`).
        ✅ **RE-ENTRANT EVALUATION IS CONFIRMED**: direct recursion is **ERR 7**
        on both references, i.e. it runs the stack out rather than refusing.
        🔴 **AND THE BINDING IS DEARER THAN FILED.** `X=5:DEF FNA(X)=X+1:
        Y=FNA(2)` leaves **X = 5** on both references — the formal is SAVED AND
        RESTORED, not bound through the variable table the way classic MS BASIC
        does. The surface is also wider: **0, 1 and 2 parameters all legal**
        (`DEF FNA=7` → 7; `DEF FNA(X,Y)=X+Y` → 5), string-typed forms work
        (`DEF FNA$(X$)=X$+"!"` → `hi!`), redefinition takes the last, and FN
        calling FN works.
        🔴 **TWO ROWS ARE A SILENT WRONG ANSWER HERE**: `FNZ(1)` undefined, and a
        `DEF` on a later unexecuted line, are **ERR 18** on both references and
        read **`0`** here.
        💰 **NO TOTAL IS CLAIMED** — nothing has been assembled, and a size from
        arithmetic is not a measurement. ⚠️ It is RESIDENT wherever it lands:
        `FN` evaluation must call `eval`, which is main page 1, and no sub-ROM
        tenant can reach main page 1. **Read both walls from `make basic-reloc`
        at the time.**
        ⚠️ **AND THE SCOUT'S OWN HEADLINE IS NOW REFUTED, 2026-08-22**, by
        [`docs/deffn-design-2026-08-22.md`](../../docs/deffn-design-2026-08-22.md)
        (rounds 5–10, `scratchpad/deffn_round5.out` … `deffn_round10.out`,
        **82 rows, both references agreeing on every scored one**).
        ❌ **THERE IS NO SAVE AND NO RESTORE.** The scout read *"the formal is
        SAVED AND RESTORED … that is the fact the design turns on"*; the
        variable is **never written**. `X=5:P=VARPTR(X):DEF FNA(X)=PEEK(P)` →
        **5**, and `DEF FNA(X)=VARPTR(X)-P` → **30327, not 0**: the formal is a
        **SHADOW CELL that only the defining function's own body sees**
        (`DEF FNB(Y)=X` called from inside `FNA(X)`'s body reads the GLOBAL).
        Nothing has to be unwound, which is also why `X` survives a body that
        RAISES. 🔴 The round-8 row built to prove the opposite (`PEEK(VARPTR(X))`
        → 2) **agreed for the wrong reason** — `VARPTR` inside the body resolves
        the name the same way the body does.
        🎯 **THE CEILING IS A DIVISION, NOT A RULE**: 9 formals legal / 10 →
        **ERR 5 at the call**, and the reference's shadow reads `$F6EB`, i.e.
        3 B into a 100-byte block; a slot shaped like a variable entry is 11 B;
        100/11 = 9.
        🎯 **`DEF FN` DOES NOT PARSE ITS BODY** — `DEF FNA(X)=X+*2` and even
        `DEF FNA(X) X+1` (no `=`) are accepted; the ONLY DEF-time check is that
        a letter follows `FN`. The skip to end-of-statement is token-aware
        (`DEF FNA$(X$)=X$+":Q"` → `a:Q`), i.e. `if_skip_to_else`'s shape with
        `COLON`.
        🎯 **`DEF FN` IN DIRECT MODE IS `Illegal direct` (ERR 12)**, pinned by
        two controls (`DEF USR` and a direct `LET` in the same position are
        both fine). ✅ ERR 12's message already ships.
        🎯 **`CLEAR` ERASES A DEFINITION** and `A`/`FNA` coexist — so the
        definition lives in the VARIABLE TABLE under a key no variable can
        make (bit 7 of `name0`), needing **no new table**:
        `var_alloc_or_find(BC,2)` already allocates a typed 2-byte entry and
        2 B is exactly a text pointer.
        📏 **GATED**: `make deffn-acceptance` (`probes/basic/basic_probe_deffn.py`,
        82 rows + 3 claim rows). At `84e080c`: **8 of 8 positive controls PASS,
        67 of 69 subject rows divergent** — red by design until the verb ships;
        `make deffn-strict` is the target that flips.
        🔴 **SIX ROWS ARE A SILENT WRONG ANSWER, NOT TWO** (`b.undef`,
        `b.forward`, `o.undefarg`, `o.ifnot`, `d.def`, `d.defrun`): an undefined
        `FN<name>(…)` parses as a subscripted array reference and reads **`0`**.
        🔴 **AND THE TWO GREEN SUBJECT ROWS ARE VACUOUS** — `o.twofault` /
        `o.badname` want `ERR 2 AT 20` and so do 44 of the 69, because this tree
        answers `Syntax error` to EVERY `DEF FN` line. The probe detects the
        blanket and prints `GREEN BUT VACUOUS` beside them.
        💰 **STILL NOT LANDED, AND NOW FOR A MEASURED REASON.** Walls at
        `84e080c`, clean, 2026-08-22: **main page 1 = 4 B, main page-0 low =
        46 B** (sub p0 3075 B, sub p1 1624 B). The draft was assembled far
        enough to hit a second obstacle and then REVERTED (the tree is
        byte-identical): 🔴 **the RAM window the 100-byte parameter area needed
        IS NOT FREE, AND `basic/sysvars.inc` SAID IT WAS** — *"376 B spare"*
        below `$E560`, while `GFX_PSTK`/`GFX_DBUF` have sat at `$E3F2` (256 B)
        since G5. **10 bytes are actually free there.** That comment is FIXED
        (conclusion inverted, 0 ROM bytes), as is `basic/vars.asm`'s header
        filing `var_find`/`var_get_key`/`var_set_key` as an available carve —
        R1 took them three weeks ago.
        💰 **THE FUNDING SURVEY IS MEASURED**:
        `scratchpad/dupspan_sweep.py` (calibrated with a planted pair, prints
        its 1467-span denominator) finds ~150–190 B of byte-identical spans on
        the D-PAINTBORD `gfx_absent equ gfx_err5` precedent — the biggest being
        **8 copies of `ld a,5 / jp raise_error` (35 B)** and **6 of `ld a,2 /
        jp raise_error` (25 B)**. 🔴 Every row is a CANDIDATE, not a verdict:
        some sites are FALLTHROUGH targets (`sw_illegal` recovers 2 B, not 5)
        and seven are reached by `jr` (1 B each to widen). **DEF FN is an arc
        with a funding slice in front of it — but for a different and now
        measured reason than the filed one.**
      - **The `CLEAR` string-pool partition** — ✅ **LANDED 2026-07-29, 51/51
        gated, falsified.** Opened by the `BIN$`/`FRE` slice (D-BF-A(c)):
        zerobas had ONE free gap where the reference has TWO pools, and
        `CLEAR`'s string-space argument was evaluated and discarded. The six
        recorded-not-gated `FRE` rows are back in a gate.
        [`docs/spec-basic-clearpool.md`](../../docs/spec-basic-clearpool.md),
        [`docs/clearpool-vg8020-characterization.md`](../../docs/clearpool-vg8020-characterization.md),
        [`docs/decision-clearpool-funding.md`](../../docs/decision-clearpool-funding.md),
        `make clearpool-acceptance` (57 rows, twelve batteries). Baseline 6/51.
        FUNDED by promoting `fld_lookup` to a page-0 sub-ROM tenant
        (`sub/fldlook.asm`, index 12 — **the last page-0 index that fits before
        the fixed `$0038` vector**): page 1 3 B → 41 B free.
        ⚠️ **THREE THINGS THE SPEC DID NOT ANTICIPATE, all found by measuring.**
        (1) `FRE(n)` needed its own handler — both forms shared op 15 because
        there was one gap, and left alone `FRE(0)` reads 200 at boot (the
        probe's `ctl-fre0` CONTROL catches it). (2) **A sized pool measures the
        PEAK, and zerobas's peak was 3×**: `A$=STRING$(100,"A")` charged 300
        (the `STRING$` temp, `str_set_key`'s H1 snapshot *of that temp*, and the
        variable's body) where the reference charges 100 — and **`FRE("")` HID
        it**, because FRE GCs first, so the resting number looked right while
        `CLEAR 100 : A$=STRING$(100,"A")` raised ERR 14. Fixed by skipping the
        redundant snapshot for a source that is already a temp, and by having
        `sh_var_store` **adopt** a temp's body instead of copying it.
        (3) ERR 14 cost **one byte** — a different FPERR code, not a different
        code path. Also: **`oos-vs-oom` was measuring two claims at once** and
        was SPLIT rather than silenced; the six ungated rows are ungated for
        three different reasons and the battery names (`rep`/`share`/`arr`)
        carry which.
        The model is a **single moving boundary, not a second
        allocator** — `CLEAR 200`→`FRE(0)`=28815 and `CLEAR 4000`→25015, a
        difference of **exactly 3800**, so the pool is carved from the same RAM.
        The pools are independent: the equal-depth `FRE(0)` delta across
        `A$=STRING$(100,"A")` is **6 on the reference at both 100 and 200
        chars** (the entry only) against zerobas's 106 and 206.
        `CLEAR n` sizes the pool to exactly n; the default is 200 but a **bare
        `CLEAR` KEEPS the current size** (`CLEAR 500:CLEAR` → 500, and so do
        `NEW`/`RUN`/`CLEAR ,himem`); **`B$=A$` COPIES** the body; a dead body is
        reclaimed and a pure temp fully given back; **`Out of string space`
        (ERR 14) is real and the failed allocation is ROLLED BACK**; and
        `CLEAR -1`/`32768`/`"200"` raise IFC/Overflow/Type mismatch where
        zerobas raises **nothing**. ERR 14 is currently a **hole** in
        `err_msgtab` pointing at `err_unprintable`, exactly as ERR 24 was.
        ✅ **S-CLP-1 the carve, S-CLP-2 derive-don't-store, S-CLP-3 the 200-byte
        default, S-CLP-4 the stored literal and S-CLP-5 body sharing are all
        answered — see the spec's §7.** S-CLP-4 is the one whose ANSWER moved
        it: a stored-program literal costs the pool **nothing** (measured, and a
        25-char literal still costs nothing, so it is zero and not slack),
        because the reference points the descriptor at the program text — but
        matching that needs storing by REFERENCE, which is S-CLP-5's scope, not
        a `heap_alloc` change as the question assumed.
        ⚠️ **S-CLP-3 was the user-visible one**: the 200-byte default means
        programs that used to have ~15 KB of string space now get 200 unless
        they say otherwise. The full acceptance corpus was re-run, not just this
        slice's gate.
      🔴 **THE ⛔ IS DEAD, AND THE FIXTURE IT NAMED HAD EXISTED ALL ALONG
      (2026-09-12, D-KWDISK).** This item was held closed by *"needs a fixture"*;
      the fixture is `disk/test720.dsk`, generated by `tools/make_test_dsk.py`,
      mounted through `probe_sides.diska()` and used by `ramfree-acceptance` for
      months. `basic_probe_kwsweep.py` simply never named it. Mounting a WRITABLE
      PRIVATE COPY on both sides took one slice and moved twenty keywords.
      ⚠️ **ELEVEN OF THIRTEEN BLOCKERS RE-CHECKED IN THAT SESSION WERE STALE** —
      re-verifying is cheaper than the work a blocker hides, every time so far.
      ➡️ **SO THE EXIT CRITERION IS NOW RUNNABLE, WHICH IS THE POINT.** The three
      classes this item was opened for are EMPTY and stay empty:
      **SILENT-GAP**, **MISSING** and — since 2026-09-12 — **DIVERGENT**, the
      whole sweep's first clean run. What is left is not a defect but an ABSENCE
      OF EVIDENCE: the keywords `tier_table --keywords` lists under **"no known
      gap"**, each with no open item and no kwsweep row.
      📏 **DONE = that list is EMPTY.** Run the command; do not read a number here.
      🟢 **THE LIST IS EMPTY — 2026-09-13, D-KWINKEY. `tier_table --keywords` now
      reports `no known gap ... 0`, which is this item's own stated exit criterion.**
      Joost's 2026-09-12 ruling is satisfied: 114 → 0, with every keyword carrying
      either an open item or a kwsweep row that observes it.
      🔴 **AND THE LAST WORD'S BLOCKER WAS WRONG, like eleven before it.** `INKEY$`
      was filed as needing a HARNESS change — a key had to arrive after the machine
      consumed `RUN` and before the statement read it, a moment computed inside
      `run_cases` from `boot` + per-line `step` that a row cannot see, with
      D-LATCH/D-LATCH2 as the races such a change must not reopen. All true, and
      all beside the point: **a key does not have to be TYPED to be waiting.** The
      BIOS type-ahead buffer is ordinary MSX work area — `KEYBUF` $FBF0 with the
      `GETPNT`/`PUTPNT` cursors, empty when equal — so the program stuffs one
      character, sets the cursors one apart, and `INKEY$` returns a REAL keystroke
      with no injector timing anywhere. Measured `[A 1 ]` on both machines
      ([`scratchpad/kwdrain_inkeypoke.py`](../../scratchpad/kwdrain_inkeypoke.py)),
      against the `[ 0 ]` an unstuffed buffer and a stub both give.
      ⚠️ **STORED, AND THAT IS LOAD-BEARING**: in direct mode the harness delivers
      the next line through that very buffer and would overwrite the stuffed
      character. Nothing competes for it during `RUN` — which is why the blocker
      looked real from the direct-mode side it was filed from.
      🎯 **TWELVE BLOCKERS RE-VERIFIED ACROSS THIS DRAIN, TWELVE STALE.** Not one
      survived contact with a measurement. The pattern is worth more than the
      drain: a blocker is written down at the moment of most confusion about a
      problem, and then it is never re-read against what was learned afterwards.
      🎯 **RULED (Joost, 2026-09-13): "keep it TIER 1 — step (c) is worth
      building."** Both halves answered. The tier STAYS despite nothing under it
      being measured broken, which is the conservative reading and the one the
      drain's own record supports: re-tiering on "nothing is measured broken" is the
      reasoning that would have hidden `NEW`, `FILES`, `LFILES` and `MERGE`.
      ➡️ **AND THE EXIT CRITERION MOVES ON, it does not disappear.** "The list is
      empty" is DONE and stays done; what this item is now open for is **step (c)**,
      which upgrades the evidence from *a row exists for this keyword* to *a row
      whose verdict MOVES when this keyword breaks*.
      📏 **DONE = every keyword's attribution is MUTATION-PROVEN, and the BLIND ones
      are filed.** Run the instrument; do not read a number here.
      🎯 **RE-AIMED THE SAME HOUR (Joost, 2026-09-13): *"instead of trying to match
      existing tests on keywords, it would make more sense to just add more tests
      for each keyword proving the tier"* — and he is right, on evidence this
      session produced.**
      | | writes a row per keyword | matches existing suites (the filed step (c)) |
      |---|---|---|
      | finds defects | **five TIER 1 this session** — `NEW` `FILES` `LFILES` `MERGE`, and `LOAD`, which only the `MERGE` row could have found | **none, by construction** — it certifies coverage that already exists |
      | what it proves | the keyword's BEHAVIOUR against the reference, at its tier | only that *a total failure of the handler is noticed* — the spec says so itself |
      | apparatus needed | none: four rigs already exist | a keyword→dispatch map, a ROM patcher, per-keyword suite selection |
      | BLIND keywords | n/a | still need a row written afterwards — **you pay twice** |
      🔴 **AND THE "THIS KEYWORD CANNOT TAKE A ROW" OBJECTION IS EMPIRICALLY DEAD**:
      twelve blockers re-verified across the drain, twelve stale, including *the
      display verbs cannot take a kwsweep row* and *the multi-line words cannot be
      expressed in one row*. Both got rows.
      ➡️ **SO THE `subject:` TAG IS NOT BUILT — THE ROW IS THE ATTRIBUTION.** Step
      (c) as filed is retired in favour of rows, and what survives of it is the
      KNIFE, demoted from a per-keyword mechanism to a **sampling spot-check**
      answering *"is this row load-bearing?"* — which is the question the five
      silent-failure modes actually raise. Rows can go green while seeing nothing:
      five did this session and `CSAVE` nearly made it six, scoring SUPPORTED on an
      EMPTY capture.
      📏 **DONE = every keyword has a row that OBSERVES it, and a sample of rows is
      knife-proven load-bearing.** Run the instruments; do not read a number here.
      ~~ **THE MECHANISM IS ALREADY SPECIFIED AND NEEDS NO DESIGN** (D-KWCOVER
      spec §2): `make kwcover` says which suites TYPE each keyword — 159/159 typed,
      27 THIN — so the candidate set per keyword is 1–4 suites, not 82. A handler is
      then disabled by patching the **BUILT ROM** (seconds, no rebuild) and only
      those suites re-run; keywords with disjoint suite sets can be knifed in the
      same ROM. **A keyword whose handler can be disabled with its suites still
      GREEN is BLIND**, and that is the row list.~~ — RETIRED as the primary
      mechanism by the re-aim above; kept as the sampling spot-check.
      ⚠️ **EXERCISED IS NOT VERIFIED, and the drain just proved why at row level**:
      five silent-failure modes shipped green rows this session, and a sixth nearly
      did (`CSAVE` scored SUPPORTED on an EMPTY capture — two machines agreeing that
      nothing happened). Mutation is the general cure for exactly that class, which
      is what makes step (c) worth its price rather than bookkeeping.
      💰 **PRICED BEFORE IT WAS APPROVED**: ~15 minutes per keyword as a mutation +
      rebuild + full battery — but the spec's ROM-patch route removes the rebuild
      and the disjoint-set batching removes most of the battery, which is where the
      real saving is. Measure the per-keyword cost on the first one before assuming
      either figure.
      ~~ **SO THE TIER IS NOW THE QUESTION, EXACTLY AS THIS ITEM SAID IT WOULD BE.**~~ — ANSWERED, see above.
      
      The three defect classes are empty (SILENT-GAP, MISSING, DIVERGENT), the
      unattributed list is empty, and the item asked for the tier to be re-asked
      WITH JOOST at this point rather than re-tiered autonomously. Two things need
      his call: whether this stays TIER 1 now that nothing under it is measured
      broken, and whether the remaining apparatus gap — **step (c)**, a `subject:`
      tag meaning "a row whose verdict MOVES when this keyword breaks" — is worth
      its measured price of a mutation + rebuild + full battery per keyword.
      🎚️ TIER 1 — happy path: the measured keyword-completeness remainder, now an
      ABSENCE OF EVIDENCE rather than a measured defect — the three defect classes
      are empty and what is left is the unattributed list (this line names no
      keyword on purpose: the tier table reads a backticked word here as an open gap)
      ⚠️ **THE TIER IS KEPT DELIBERATELY, and the reason is the only thing that
      justifies it**: Joost's 2026-09-12 ruling is that an unattributed keyword can
      HIDE a happy-path defect, and four did — `NEW`, `FILES`, `LFILES` and `MERGE`
      all came out of the "no known gap" list, and `LOAD` came out of the sweep one
      of them earned. Re-tiering on "nothing is measured broken" would be the same
      reasoning the drain has refuted four times. When the list empties, THAT is
      when the tier is the question to re-ask — with Joost.
      ✅ **THE KNIFE HALF IS DONE (D-KWSUFCUT, 2026-09-16): NO KEYWORD IS HELD
      BACK BY ATTRIBUTION ANY MORE.** `docs/tier-status.md` carried exactly one
      *"not knife-proven CONNECTED"* — `INPUT$`, with BOTH its forms agreeing —
      and that count is now **0**. STATEMENT 149 → **150**.
      🔴 **AND IT WAS NOT MERELY UNCUT, IT WAS UNREACHABLE BY THE INSTRUMENT.**
      `enumerate_fn_targets` walks `kwtable.inc`, and **`INPUT$` HAS NO TOKEN** —
      MSX tokenises `INPUT` and `$` separately, which `tools/kwforms.py` says in
      its own words — so there was no entry to enumerate and no token byte for any
      of the six token-keyed shapes to compare against. It is dispatched by a
      SUFFIX instead: `str_eval_maybe_inputd`'s `ld a,(hl) / cp '$' / jr z,…`.
      🔪 **THE SEVENTH CUT SHAPE** (`plant_suffix`) patches that compared
      CHARACTER, and the row is found by its own `SUBJECT:` tag — the attribution
      `kwforms.py` and `tier_table` already use for it — because `kw2row` is keyed
      on the kwtable set too. Verified: `INPUT$ row inputdol_b knifed -> MISSING
      LOAD-BEARING`.
      ⚠️ **IT IS A DECLARED TABLE, NOT A HEURISTIC.** Matching "a `cp <printable>`
      inside a routine whose name contains the stem" would also sweep up
      `ex_input`, `input_common`, `str_inputd` and `str_inputd_read` — the same
      substring trap `plant_cp_named` records for `LEN`, where a length EQUATE
      nearly outranked the real site. And a token-free subject now SKIPS every
      token-keyed shape explicitly rather than relying on each one happening to
      miss on `None`.
      ⚠️ **THE BLIND LIST IS UNCHANGED AND EACH ENTRY IS EXPLAINED**: `MAX`/`CALL`
      score reservedness and have no happy path here; `VDP`/`BASE` are cut on the
      STATEMENT path while their rows use the FUNCTION form (the knife's own
      docstring records that); `ELSE` is a particle; `PAD` is the joystick-rig
      limit. This slice added none.
      🤖 AUTONOMOUS — Joost ruled both halves on 2026-09-13: the tier STAYS and
      step (c) IS worth building; he RE-AIMED it the same hour to *"add more tests
      for each keyword"*, so the `subject:` tag is retired and the ROW is the
      attribution, with the knife kept as the sampling spot-check. **That
      spot-check now has no keyword it cannot reach.**
      🟢 **D-CONTROW (2026-09-24): `CONT` HAD NO ROW AT ALL, AND NOW IS LEVEL 1.**
      It was the ONLY keyword in `docs/tier-status.md`'s ⚪ UNPROVEN bucket —
      no form list, no knife — and the only level-0 keyword that was neither a
      particle, composite-only, the parked rig (`PAD`/`STICK`/`STRIG`) nor
      waiting on Joost (`PLAY` ×2, `VARPTR`'s file form). New row `contkw`
      (a `RESPOND:CONT` row: the program STOPs after `[C1]`, `CONT` is typed at
      the prompt, `[C2]` must follow) + form `resume` in `tools/kwforms.py`.
      🔴 **THE FIRST CUT AGREED FOR THE WRONG REASON:** anchored on the `RUN`
      echo, the window ENDS at the prompt the STOP returns to, so both sides
      read `[C1]|Break in 10` — SUPPORTED and blind to `CONT`. Now a `NOECHO:`
      marker row on `[C2]`, spelled `"[C"+"2]"` so the typed source never
      carries it. Both read `[C2]`; the knife (`CONT:contkw`) moves it to
      UNREADABLE — LOAD-BEARING. ⚪ UNPROVEN is now **empty**.

      📏 **RE-RUN 2026-11-13 (after the day's BIOS / disk ROM changes):** `make kwsweep` --
      SUMMARY SUPPORTED 987, DIVERGENT 1, WEAK (excluded) 3 ([`kwsweep_1113.out`](../../scratchpad/kwsweep_1113.out)); the one
      DIVERGENT row, `chanfor`, had the REFERENCE's screen garbled (a column of `|`, the key
      row) where zerobas printed `1 2 3 10 20 30`, and alone reads SUPPORTED
      ([`kwsweep_chanfor1.out`](../../scratchpad/kwsweep_chanfor1.out)) -- a capture fault of the long run, not a keyword gap. No MISSING.
