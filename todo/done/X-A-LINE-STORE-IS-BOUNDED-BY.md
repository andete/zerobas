- [x] 🔴 **A LINE STORE IS BOUNDED BY THE CONSTANT `TXTMAX`, NOT BY HIMEM.**
      Found 2026-08-03 by D-DOTGAPS (§4.2/§6 D4). After
      `CLEAR 300,TXTTAB+1000` both references have **148** free bytes and refuse
      a 32-byte line with `Out of memory`; zerobas has **646**, stores it, and
      prints nothing — `CLEAR`'s HIMEM argument does not reach the store check
      at [`sub/lineedit.asm:139`](sub/lineedit.asm:139), which compares
      `PRGEND + size` against a fixed `$BB00`.
      💰 **SCOUTED 2026-08-20 (not priced, not opened).** The right ceiling
      already exists and is already reachable — the obstacle is neither the
      arithmetic nor the bytes, it is that the two ends are in different
      tenants.
      * The bound wanted is the VARIABLE-region ceiling, `min(HIMEM,TXTMAX) −
        POOLSIZE − MAXF×FCH_CTXSZ`, which is exactly
        [`strheap_varceil`](sub/strheap.asm) — derived, never stored, so it is
        current by construction and `CLEAR ,himem` falls out for free.
      * 🎯 **NO NEW SUB-ROM OP IS NEEDED.** `sh_chan_addr` (op 18) answers
        `strheap_varceil() + (ch−1)×FCH_CTXSZ`, so **channel 1 IS the varceil**;
        `basic/files.asm`'s `fch_ctx_addr` is the existing main-ROM wrapper and
        returns it in HL.
      * 🔴 **THE OBSTACLE IS THE TENANT SPLIT, AND IT IS THE WHOLE COST.**
        `le_store` is in `lineedit_tenant` (sub **page 1**); `strheap_engine` is
        sub **page 0**. A tenant cannot call across, so the ceiling has to be
        fetched by the MAIN-ROM store head (`dl_store`, `basic/program.asm`)
        before it marshals, and published in a RAM cell beside `SL_NUM`/
        `SL_TOK`. Shape: main ROM ≈ a `ld a,1` + `call fch_ctx_addr` + a store;
        sub page 1 **+1 B** (`ld de,TXTMAX` → `ld de,(cell)`).
        💰 **PRICED BY BUILDING IT, 2026-09-05 (D-TXTCEIL): 9 B in main page 1,
        not the ~7 counted here — and it does NOT fit.** Planted, measured,
        reverted byte-identically (ROM hashes unchanged). `ld a,1` (2) +
        `call fch_ctx_addr` (3) + `ld (SL_CEIL),hl` (3) = **8**, and the build
        then refused with *"Relative jump out of range on line 48"* —
        `jr c,dl_new`, which has nothing to do with this edit and goes out of
        reach because **inserting into `dl_store` moves everything after it**.
        Converting it to `jp` is the **9th** byte, and with that the image
        overran the `$8000` ceiling.
        📏 **Main page 1 was 5 B free on 2026-09-05** (`make basic-reloc`, the
        same run — re-read it, never quote this), so this is **4 B short**. Same reach
        mechanism D-UNARYPLUS recorded: a counted price in this page is a LOWER
        BOUND, not a price.
        🎯 **AND THERE IS NO LOW-REGION ESCAPE FOR THE FETCH**: `dl_store`
        (`$7567`) and `fch_ctx_addr` (`$6FB6`) are BOTH in main page 1, read from
        `build/basic-reloc.sym`.
        🔴 **AND THE SHAPE ITSELF IS REFUTED — BUILT, RUN, REVERTED
        (2026-09-05, after D-DGTPUSH's carve funded it).** The 9 B **fit**
        (page 1 15 → 6 B free, sub page 1 918 → 917) and the machine then
        **HANGS ON THE FIRST LINE STORE**: `NEW` / `10 PRINT"HI"` echoes and
        nothing follows — no `RUN`, no prompt. Every `crf-*` row went to
        `<none>` / `<NO ECHO>`, **including `crf-oomctl`, which is an ordinary
        successful store**, and that is the tell: this is not a bound that
        refuses too much, it is a machine that stops.
        🎯 **K-TC1 LOCATES IT AT THE CALL, NOT THE VALUE.** Keeping
        `call fch_ctx_addr` and reverting the sub side to `ld de,TXTMAX` — so the
        published ceiling is fetched and then ignored — **still hangs**. So the
        fault is `call fch_ctx_addr` from `dl_store`, not `strheap_varceil()`
        being wrong or too low.
        🟢 **AND THE CAUSE IS ORDINARY — FOUND ON THE SECOND ATTEMPT, SAME DAY.
        `fch_ctx_addr` RETURNS IN HL, AND HL AT `dl_lnok` IS `tokenise`'S SOURCE
        CURSOR.** Its header lists *"Clobbers A, BC, DE, IX"* and does not mention
        HL **because HL is the result**, so a reader checking the clobber list
        sees nothing wrong. `push hl` / `pop hl` around the call (+2 B) and the
        machine is healthy again: `NEW` / `10 PRINT"HI"` / `RUN` prints `HI`.
        🔴 **SO THE "MECHANISM NOT ESTABLISHED" NOTE ABOVE IS SUPERSEDED, NOT
        VINDICATED.** K-TC1 was right that the CALL was at fault and wrong to
        leave it there: "contextual to line-entry" pointed at slot state and
        re-entrancy when the answer was a clobbered pointer. The knife narrowed
        the site; it did not diagnose it, and stopping at a narrowed site reads
        as a finished diagnosis.
        ⚠️ **THE MECHANISM IS NOT ESTABLISHED AND IS NOT GUESSED AT HERE**
        [[a-mechanism-inferred-from-one-observation]]. What IS known: the same
        routine works from its existing callers (`fch_save_active` /
        `fch_load_ctx`), which the disk battery exercises green on every run — so
        the fault is contextual to calling it at LINE-ENTRY time, not a broken
        `fch_ctx_addr`. The IX contract its header demands of new callers was
        checked and is satisfied (`store_line` reaches the tenant through
        `le_call_op`, which does `ld ix,...` itself), so that is not it either.
        ➡️ **NEXT SHAPE TO TRY, AND IT IS A BETTER ONE ANYWAY: publish `SL_CEIL`
        FROM `CLEAR`, NOT FROM `dl_store`.** `CLEAR` is where HIMEM changes and it
        already touches the pool, so the ceiling would be fetched once per
        `CLEAR` instead of once per typed line — cheaper, and it moves the
        sub-ROM call out of the line-entry path entirely, which is exactly where
        the measured fault is. 🔴 It also needs a boot-time initial value, or a
        program typed before any `CLEAR` reads an unwritten cell.
        🔴 **AND WITH THAT FIXED THE BOUND STILL DOES NOT BIND — the item stays
        OPEN and this is where the next reader starts.** 11 B (the 9 + the
        `push hl`/`pop hl`), which FITS: main page 1 15 → **4 B free**. The
        machine is healthy, and `crf-oomsay` / `crf-oomlst` read EXACTLY as
        before: `Out of memory` on both references, `<nothing listed>` here, and
        the refused line still in the listing.
        📏 **WHAT WAS MEASURED, so nobody re-derives it**: after
        `CLEAR 300,TXTTAB+1000`, `SL_CEIL` reads **30119** (`$75A7`) — a MAIN-ROM
        PAGE-1 ADDRESS, not a RAM ceiling, and far from
        `min(HIMEM,TXTMAX) − POOLSIZE − MAXF×FCH_CTXSZ` (HIMEM read 33769,
        TXTMAX is `$DB00`). And the sub-side arm IS assembled — K-ARM planted a
        bogus token inside the `IF CLEARPOOL` branch of
        [`sub/lineedit.asm`](sub/lineedit.asm) and the assembler saw it on line
        170 — so this is not a branch that was compiled out.
        🟢 **READ THEM — AND THE ANSWER IS THAT `SL_CEIL equ $E038` ALIASES
        `CURLINE`.** Two readings on the **UNMODIFIED** ROM settle it, no build
        required:
        • `PEEK($E038)` already reads **30108** with none of this planted — the
          address was never free, and the 30119 above was `CURLINE`'s value, not
          a ceiling that failed to arrive.
        • `PEEK($E371)` (`SH_PTR`) reads **33419**, which is exactly
          `min(HIMEM,TXTMAX) − POOLSIZE − MAXF×FCH_CTXSZ` for this fixture
          (HIMEM 33769, POOLSIZE 300, MAXF 1, `FCH_CTXSZ` 50 — all PEEKed).
          **So the varceil is already correct and already computed**; neither
          `fch_ctx_addr` nor op 18 was ever in question.
        🔴 **AND IT WOULD HAVE BEEN WORSE THAN NOT WORKING**: publishing the
        ceiling into `CURLINE` on every line store corrupts current-line tracking.
        The bound not binding is the *mild* symptom.
        🎯 **THIS IS THE "RAM HAS NO GATE" CLASS, WALKED INTO WITH THE RULE IN
        MY OWN INDEX.** `$E038` was chosen as the DELTA after `SL_TOK` (2 B at
        `$E036`) and because nothing greps for the literal — neither of which is
        evidence the address is free. `make wall-assertion-check` covers **ROM
        only**; `tools/ram_map.py` says in its own banner that a delta
        is *"the cell at the low address PLUS whatever follows, NEVER free
        space"*, and `$E038` is `CURLINE` in that very map
        [[deffn-ramhunt-slice]].
        🟢 **CELL FOUND AND PROVEN, PLUMBING COMPLETE — AND THE CEILING VALUE
        THIS ENTRY SPECIFIES IS THE THING THAT IS WRONG.** `$E058` (the head of
        the retired `GOSUB_STK` window `sysvars.inc` marks `; FREE-RAM`) was
        **measured** rather than trusted:
        [`scratchpad/ramfree_e058.py`](scratchpad/ramfree_e058.py) fills
        `$E058..$E07F` with `$AA`, works a line store, `GOSUB`/`RETURN` (this IS
        the retired GOSUB stack), `FOR`/`NEXT`, string ops, `DEF FN` and `CLEAR`,
        and reads **0 of 40 bytes changed**. With that cell the 11 B build is
        healthy and `SL_CEIL` publishes **33419**, which is exactly
        `min(HIMEM,TXTMAX) − POOLSIZE − MAXF×FCH_CTXSZ`. End to end, it works.
        🔴 **AND `crf-oomsay` / `crf-oomlst` DO NOT MOVE.** PRGEND reads 32777, so
        the new bound leaves **642 B** of program headroom where **both
        references have 148** — and the filed pre-fix reading was **646**. The
        whole fix moves the headroom by **four bytes**.
        🎯 **AND THE ~500 B IS NOW A FORMULA, NOT A GUESS — AND IT REFRAMES THE
        WHOLE ITEM** (D-HIMEMRES,
        [`scratchpad/himem_reserve.py`](scratchpad/himem_reserve.py)). Sweeping
        `CLEAR <pool>,TXTTAB+<gap>` over three knobs and reading `FRE(0)`:

            reserve R = gap − pool − FRE(0)
            MAXFILES     1      2        model
            vg8020     560    827     R = 293 + 267×MAXFILES
            cf3300     560    827     R = 293 + 267×MAXFILES
            zb          62    112     R =  12 +  50×MAXFILES   (R(4)=212, predicted 212)

        🔴 **THE FIRST SWEEP VARIED POOL AND GAP ONLY AND READ "R CONSTANT 560" ON
        BOTH REFERENCES** — which is exactly what `base + k×MAXFILES` looks like
        when MAXFILES never moves. The `f2` row is what separated them
        [[two-rules-that-coincide-on-every-row-you-have]]. (`f4` is OUT OF DOMAIN
        on the references — 4 channels do not fit a 1500-byte gap, the `CLEAR`
        errors, and `FRE` reports the un-CLEARed machine; the probe now refuses a
        negative reserve instead of printing it beside the real ones.)
        🎯 **267 B PER CHANNEL vs 50 IS D-FCH'S OWN DESIGN, NOT A DEFECT.**
        `basic/files.asm` says it outright: `FCH_CTXSZ equ FCH_STATESZ ; repack:
        block = state ONLY (no buffer)`. The reference reserves a per-channel
        sector buffer; zerobas deliberately does not. **So `crf-oomsay` /
        `crf-oomlst` CANNOT agree unless zerobas reserves RAM it has no use for**,
        and the ~500 B was never a missing term in the ceiling formula.
        🟢 **WHICH LEAVES A REAL DEFECT AND A SEPARATE QUESTION, AND THEY ARE NOT
        THE SAME ONE.** The real defect is the one this entry's headline names:
        the bound is the CONSTANT `TXTMAX` (`$DB00`), so with HIMEM at `$83E9`
        zerobas keeps storing lines **past HIMEM, into the string and variable
        area** — silent corruption, and `strheap_varceil` closes it exactly.
        🙋 **The separate question is whether `FRE(0)` should AGREE with the
        references**, which would mean reserving 267 B per channel for buffers
        that do not exist here. That is a faithfulness call about a measured
        architectural difference, not a bug.
        🟢 **THE ROW EXISTS AND THE FIX SHIPPED (2026-09-05, D-TXTCEIL)**
        ([`scratchpad/prgend_overrun.py`](scratchpad/prgend_overrun.py)). After
        `CLEAR 300,TXTTAB+1000`, 25 typed `REM` lines cross a pool floor 700 B
        above the text base:

            PRGEND   floor = HIMEM−POOLSIZE   headroom
            before   33694        33469         −225   🔴 stored PAST the floor
            after    33398        33469          +71   🟢

        🎯 **`PRGEND <= HIMEM − POOLSIZE` NEEDS NO ORACLE.** It is a claim about
        zerobas's own map and holds whatever a machine reserves per file channel
        — which is exactly what `crf-oom*` cannot say, and why those rows were
        the wrong instrument for this defect all along.
        🔴 **TWO INSTRUMENT FAULTS ON THE WAY, BOTH CAUGHT BY THEIR OWN
        CONTROLS.** Round 1 ran the row on ALL THREE machines and printed the
        references' numbers as readings — `PRGEND` and `POOLSIZE` are zerobas
        sysvars, so on a VG-8020 they are unrelated bytes, and it duly reported
        one reference green and the other *"stored 74119 B past the floor"*. And
        round 1 reported **zerobas green on a fixture that never took**:
        `CLEAR 300,TXTTAB+400` is refused and leaves HIMEM at its default, so the
        verdict was about a machine never set up. `c.clear` now asserts
        `HIMEM == TXTTAB+GAP` and refuses the run otherwise.
        🔧 **`unit-test` WENT RED FOR A GOOD REASON.** Four test files call
        `store_line` DIRECTLY, so `SL_CEIL` was 0 in the harness's zeroed RAM,
        every store was refused as OOM, and the abort funnel's `ld sp,(SAVSTK)`
        ran away (`msxtest.StackLost`). Fixed in the TESTS, as the harness message
        says: each site publishes `TXTMAX` — the constant the code compared
        against before — so those rows go on testing what they tested. ⚠️ Which
        means **the unit rows still do not cover the live ceiling**; the emulator
        row above is what does.
        🟢 **AND IT IS A COLLECTED GATE NOW: `make txtceil-acceptance`**
        ([`probes/basic/basic_probe_txtceil.py`](probes/basic/basic_probe_txtceil.py)),
        in the EMULATOR tier, named by both membership lists. Four rows:

            c.fits   3 lines, room to spare   stored=111  head=589   🟢
            p.n25   25 lines                  stored=629  head= 71   🟢
            p.n40   40 lines                  stored=629  head= 71   🟢
            p.pool2 25 lines, pool 200        stored=740  head= 60   🟢

        🔴 **`c.fits` IS NOT DECORATION.** A one-sided invariant is trivially
        satisfied by a machine that stores NOTHING, so a bound that over-refused
        would read green on the other three
        [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. And `p.pool2`
        shrinks the pool by 100 B: the floor rises 100 B and the store follows
        it, so "bounded" is not one arithmetic coincidence.
        🔧 **The fixture control earned its place on the first run**: `p.tight`
        (pool 500, gap 900) reported `NOT MEASURED` because that `CLEAR` is
        REFUSED and leaves HIMEM at its default — the same trap that made an
        earlier cut of this row report a comfortable green about a machine never
        set up. Replaced with a geometry that takes.
        🔧 **AND THE BESPOKE RAM PROBE WAS UNNECESSARY.** Shrinking the
        `; FREE-RAM` claim to `$E05A..$E080` is enough:
        `make ramfree-acceptance` already fills EVERY declared window and fills
        that one across 11 workload rows on every battery run, so the cell's
        freedom is **gated**, not measured once.
        [`scratchpad/ramfree_e058.py`](scratchpad/ramfree_e058.py) is kept as the
        pre-flight it was — it ran before the claim was shrunk — and is not the
        standing check.
        🙋 **Still his**: whether `FRE(0)` should AGREE with the references, which
        would mean reserving 267 B per channel for buffers that do not exist
        here.
        ➡️ ~~**WHAT IS LEFT IS THE VALUE, NOT THE PLUMBING.** The cell is proven,
        the fetch site is right, the `push hl` and `IF CLEARPOOL` guards are
        settled, and 11 B fits (main page 1 15 → 4 B free on 2026-09-05).
        **Nothing is shipped**: swapping one wrong bound for another that is 4 B
        closer changes behaviour no row pins and leaves `crf-oom*` DIFF either
        way.~~
        🔴 **THE TWO PARAGRAPHS ABOVE AND BELOW ARE STALE, AND THEY SIT AT THE
        END WHERE A READER STOPS (struck 2026-09-07, D-TXTSTALE).** This entry
        says **SHIPPED** in its middle and **"Nothing is shipped"** at its
        bottom; a reader who scrolls to the end concludes the opposite of the
        truth [[two-sections-of-one-doc-disagreed]]. The ROM settles it, not the
        prose: [`sub/lineedit.asm:170`](sub/lineedit.asm:170) reads
        `ld de,(SL_CEIL)`, [`basic/program.asm:163`](basic/program.asm:163)
        publishes it, commit `0731a3e0` is titled *D-TXTCEIL SHIPS*, and
        `make txtceil-acceptance` is collected in the emulator tier and ran green
        in 19 s in today's battery.
        🔴 **AND THE FIX FALSIFIED TWO COMMENTS BESIDE ITS OWN CODE.**
        `sub/lineedit.asm` still told its reader *"NO EMULATOR ROW ON THIS SIDE
        CAN SEE IT ... a green acceptance run is NOT coverage of this rule"* —
        forty lines above the `SL_CEIL` bound that makes it false, and with an
        emulator gate now doing exactly that. Struck in place, plus three inline
        comments that still named `TXTMAX` as the bound. Comments only: the main
        ROM hashes byte-identical across the edit
        [[a-fix-falsifies-the-justification-beside-it]].
        ~~💰 **THE 11 B ARE NOT SPENT** — the attempt was reverted and all four
        ROM digests re-read back to the values `make gates` had recorded for the
        preceding green battery (not quoted here: four 8-hex groups in a row are
        what `audit_citations.py`'s hex-dump check exists to catch, and it caught
        this line). Main page 1 was back to **15 B free on 2026-09-05** — re-read
        it with `make basic-reloc`, never from here.~~
        ✅ **SO THE AUTONOMOUS HALF OF THIS ITEM IS DONE AND THE BOX IS TICKED
        (2026-09-07).** The defect the headline names — a line store bounded by
        the constant `TXTMAX` instead of by HIMEM, so lines grow into the string
        and variable area — is FIXED, and `make txtceil-acceptance` pins it with
        four rows including the `c.fits` control that stops a bound which
        over-refuses from reading green.
        ✅ **DECIDED BY JOOST 2026-09-07: DO NOT RESERVE BUFFERS WE DO NOT USE
        — with the caveat that we must be SURE we do not need them if the
        references do.** That caveat is now measured
        ([`scratchpad/twochan_probe.py`](scratchpad/twochan_probe.py)):
        | row | case | CF-3300 | zerobas |
        |---|---|---|---|
        | `t.solo` | one channel, three reads | `AAA,AAA,AAA` | `AAA,AAA,AAA` |
        | `t.two` | **two channels, interleaved** | `AAA,BBB,AAA` | `AAA,BBB,AAA` |
        🔴 **REFUTED THE NEXT HOUR (2026-09-07, D-FIELDALIAS) — THE HAZARD DOES
        FIRE, AND THE SEQUENTIAL ROW WAS THE WRONG SHAPE TO SEE IT.**
        [`scratchpad/fieldalias_probe.py`](scratchpad/fieldalias_probe.py):
        | field | CF-3300 | zerobas | |
        |---|---|---|---|
        | `P$` = `F$` after its own `GET #1,1` | `AAAAAAAA` | `AAAAAAAA` | SAME |
        | **`Q$` = `F$` after `GET #2,1`** | **`AAAAAAAA`** | **`ZZZZZZZZ`** | 🔴 **DIFF** |
        | `R$` = `G$` after `GET #2,1` (control) | `ZZZZZZZZ` | `ZZZZZZZZ` | SAME |
        **A `FIELD` variable is a WINDOW onto the record buffer, not a copy** —
        `basic/sysvars.inc` says so in as many words — so with ONE shared buffer
        `F$` (on #1) and `G$` (on #2) are the SAME MEMORY. Reading `F$` after a
        `GET` on the other channel returns the other channel's record.
        🎯 **WHY D-TWOCHAN COULD NOT SEE IT**: every observation there followed a
        fresh `GET` on the channel being read, so a correct re-read HID the
        sharing. This row takes its reading with **no `GET` on #1 in between**,
        which is the only geometry that exposes an alias
        [[a-coverage-row-whose-geometry-cannot-reach-the-case]]. Sequential
        reads were the wrong shape; the FIELD row should have gone first.
        ⚠️ **SO THE ANSWER TO THE CAVEAT IS "WE DO NEED SOMETHING", AND IT IS
        SMALLER THAN 267 B.** What is needed is per-channel backing for the
        RECORD buffer (`LEN` ≤ 256), not a per-channel 512-byte SECTOR buffer.
        ⚠️ **That 267 ≈ 256 + overhead is ARITHMETIC, NOT A MEASUREMENT** — the
        reference's block was never dissected, and nothing here establishes what
        its 267 bytes contain [[a-mechanism-inferred-from-one-observation]].
        ➡️ **THIS IS A REAL, USER-VISIBLE DEFECT**: any program with two open
        random files and a `FIELD` on each reads the wrong record. Unpriced, and
        the fix shape is not obvious — per-channel record backing, or refreshing
        the field descriptors at `fch_select`.
        🔴 **AND THE WRITE HALF CORRUPTS THE DISK (2026-09-07, D-FIELDWRITE,
        [`scratchpad/fieldwrite_probe.py`](scratchpad/fieldwrite_probe.py)).**
        | row | | CF-3300 | zerobas | |
        |---|---|---|---|---|
        | `w.two` | two channels open, both FIELDed, both written | `11111111/22222222` | **`22222222/22222222`** | 🔴 DIFF |
        | `w.seq` | CONTROL: one channel at a time | `11111111/22222222` | `11111111/22222222` | SAME |
        `LSET F$="1111…"` then `LSET G$="2222…"` write the SAME BYTES, so
        `PUT #1,1` stores channel 2's record into channel 1's FILE. The row reads
        both files back after `CLOSE`, so this is what is ON THE DISK — it
        survives the program. The read-half defect above is a wrong value in a
        variable; this one is wrong data in a file.
        🎯 **THE CONTROL IS WHAT MAKES IT AN ALIAS RATHER THAN A BROKEN VERB**:
        `w.seq` does the identical two writes with only ONE channel open at a
        time and both machines agree, so `LSET`/`PUT` are correct in general and
        the fault is specifically two channels sharing one record buffer.
        🎯 **ROOT CAUSE LOCATED 2026-09-07 (D-FIELDFIX), AND IT IS A PREMISE THAT
        WAS WITHDRAWN WITHOUT ITS DEPENDANT BEING TOLD.**
        [`basic/field.asm`](basic/field.asm:21)'s header states the design its
        code rests on — *"the record buffer is the channel's `FSECTOR_BUF` … so a
        field's bytes live in the channel's context and **travel with it**"* —
        and the repack then set `FCH_CTXSZ equ FCH_STATESZ` with the comment
        *"block = state ONLY (no buffer)"*, withdrawing exactly that. The premise
        stayed in the source after the mechanism left
        [[a-fix-falsifies-the-justification-beside-it]].
        🔴 **AND THE WRITE-BACK CACHE DOES NOT COVER THE GAP.**
        `fat_restage_channel` ([`basic/fat-prim-body.inc:467`](basic/fat-prim-body.inc:467))
        dispatches on mode — `1 = INPUT`, `2 = OUTPUT`, **everything else returns
        with "device channels own no sector"** — and `fat_detach_channel` flushes
        only mode 2. A RANDOM channel is outside BOTH, so its record is neither
        saved on switch-out nor restored on switch-in. That is the whole defect.
        💰 **A FIX WAS BUILT, PROVEN AND REVERTED.** Letting the record travel
        with the context (`FCH_CTXSZ` 50 → 306, plus a second `ldir` in each of
        `fch_save_active` / `fch_load_ctx`) costs **16 B of main page 1** and
        **closes both defects against the reference**: `Q$` reads `AAAAAAAA` and
        `w.two` writes `11111111/22222222`, with both controls still green.
        🔴 **REVERTED BECAUSE IT REDS TWO ROWS AND I COULD NOT EXPLAIN ONE.**
        `ramfree`'s `ctl.pool` is understood — it pins the control pool at a
        hardcoded `$D980` that the lowered ceiling moves. But `array`'s
        `scalar.input.chain.oom` (a **zb-only** geometry assertion) stops
        reporting `Out of memory` when the machine has **less** RAM, which is
        backwards; the likely cause is `DIM Z(1840)` no longer fitting and so
        freeing ~7 KB, but a direct check of that produced no reading and the
        mechanism is NOT established [[a-mechanism-inferred-from-one-observation]].
        Committing a red battery with an unexplained side effect is the shape
        this tree keeps paying for, so the ROM is back to byte-identical.
        ➡️ **THE BETTER FIX, AND IT IS WHAT JOOST'S INSTINCT POINTED AT: EXTEND
        THE WRITE-BACK CACHE TO RANDOM MODE INSTEAD.** ~0 RAM — no per-channel
        record slot at all. It needs two things the state does not have today: a
        per-channel RECORD NUMBER (`GP_RECNO` is a single global at `$EEC4`,
        outside the `FCH_STATE0..FWR_DIROFF` span) and a DIRTY bit so `LSET`
        without a `PUT` survives a switch. That is a designed change rather than
        a 16-byte patch, and it is the one worth making.
        🟢 **SHIPPED 2026-09-07 (D-FIELDFIX) — OPTION A, ON JOOST'S CALL AFTER
        THE RESERVATION EVIDENCE. BOTH DEFECTS CLOSED, 114/114 GREEN.**
        `FCH_CTXSZ` 50 → 306 (`FCH_STATESZ + FCH_RECMAX`), plus one `ldir` in
        each of `fch_save_active` / `fch_load_ctx` so the record travels with its
        channel — which is what [`basic/field.asm`](basic/field.asm:21)'s header
        always claimed. **16 B of main page 1** (23 → 7 B free, 2026-09-07).
        | probe | before | after |
        |---|---|---|
        | `fieldalias` `Q$` | `ZZZZZZZZ` | **`AAAAAAAA`** = CF-3300 |
        | `fieldwrite` `w.two` | `22222222/22222222` | **`11111111/22222222`** = CF-3300 |
        🎯 **AND THE RAM IS THE REFERENCE'S OWN PRICE, PAID THE REFERENCE'S WAY** —
        D-MAXFRE and D-RESERVE measured it: reserved UP FRONT at `MAXFILES` time,
        −267 B per channel on BOTH references at every step, a FIXED block not
        sized by `LEN=`, and the VG-8020 charges it while DISKLESS.
        🔧 **THE TWO ROWS THAT WENT RED WERE BOTH CALIBRATION, AND BOTH ARE NOW
        IMMUNE RATHER THAN RE-TUNED.**
        • `ramfree` `ctl.pool` pinned the control pool at a hardcoded `$D980`,
        which the lowered ceiling put ABOVE the pool top (`$D906`) — so it
        truthfully reported "the pool did not move" about a window no longer in
        it. It now derives its window from **`CTLTOP` on the machine**, which is
        what the probe's own comment had already said would be better; the row
        reads a stronger result than before (16 of 16 bytes moved).
        • `array`'s two chain-OOM rows are a deliberately room-filling `DIM`
        calibrated against the allocation ceiling. That comment already records
        being bitten this way ONCE — *"raising TXTMAX … handed the row 2128 B it
        did not expect"* — and the fix then was to pin `CLEAR`. The ceiling has
        THREE terms and only two were pinned; `MAXFILES=0` is now pinned too, so
        the squeeze depends solely on numbers the rows set themselves, and the
        `DIM` is re-sized to 1845 (measured: 1840 → 67 B, 1846 → 19 B).
        ~~🔴 **SECOND ATTEMPT ALSO FAILED (2026-09-07, D-WBRAND) — AND IT FAILED
        WORSE THAN THE FIRST.** Joost asked for the low-RAM shape, so: a fixed
        16-entry `FCH_RECNOS` word array (32 B total, **not** per reserved
        channel), noted by the `t_fat_rand_get`/`t_fat_rand_put` tenant wrappers,
        plus a mode-4 arm in `fat_restage_channel` (re-read) and
        `fat_detach_channel` (write back). **Zero main-ROM bytes** — main page 1
        stayed at 23 B, the 75 B all landed in sub page 1.
        **It breaks two-channel operation outright**: every two-channel row went
        to `<empty>` on zerobas while the ONE-channel control `w.seq` stayed
        green, so the switch itself is what the arms break.
        🎯 **THE LIKELY REASON IS WRITTEN IN THE BODY I CALLED.**
        `basic/randio-body.inc:267` (deleted by c577b59c; now [`hk_dget`](disk/kernel.asm)) says the rand
        primitives assume *"the channel is already live (GET/PUT call
        `fch_select` first, setting `FCH_ACTIVE`)"* — and these arms call them
        from INSIDE `fch_select`, when it is not. `fdet_rand` also fires a full
        read-modify-write plus a directory update mid-switch, far heavier than
        the OUTPUT flush that path was built for, and it clobbers `FWBUF` which
        the switch machinery itself uses. ⚠️ **Not established** — the arms were
        reverted rather than instrumented [[a-mechanism-inferred-from-one-observation]].
        ✅ **AND JOOST'S QUESTION IS ANSWERED (2026-09-07, D-RESERVE,
        [`scratchpad/reserve_probe.py`](scratchpad/reserve_probe.py)): THE
        REFERENCE RESERVES UP FRONT FOR `MAXFILES`, NOT AS CHANNELS ARE OPENED,
        AND THE BLOCK IS NOT SIZED BY `LEN=`.**
        | case | base | +open #1 | +open #2 | closed |
        |---|---|---|---|---|
        | CF-3300 `LEN=8` | 22966 | 22955 | 22944 | 22933 |
        | CF-3300 `LEN=256` | 22962 | 22951 | 22940 | 22929 |
        | zerobas `LEN=8` | 22809 | 22798 | 22787 | 22776 |
        `FRE(0)` drops **exactly 11 B per OPEN on both machines**, and the same
        11 whether the record is 8 bytes or 256. So the 267 B/channel of
        D-HIMEMRES is charged at `MAXFILES` time and OPEN adds only a small
        variable-area block that zerobas already pays too.
        🎯 **WHICH MEANS ATTEMPT A IS THE REFERENCE'S OWN ARCHITECTURE, NOT A
        ZEROBAS TAX.** Reserving `256 B × MAXFILES` up front is exactly the shape
        the reference uses (267 × MAXFILES); it is not waste peculiar to us, and
        "allocate only what is opened" is not what the reference does either.
        ✅ **AND IT TRACKS `MAXFILES` EXACTLY (2026-09-07, D-MAXFRE,
        [`scratchpad/maxfiles_probe.py`](scratchpad/maxfiles_probe.py))** — one
        program, stepping `MAXFILES` 0→4 and printing `FRE(0)` after each change
        (it must be PRINTED, not held in a variable: `MAXFILES` clears them):
        | MAXFILES | VG-8020 | CF-3300 | zerobas |
        |---|---|---|---|
        | 0 | 28890 | 23505 | 22899 |
        | 1 | 28623 | 23238 | 22849 |
        | 2 | 28356 | 22971 | 22799 |
        | 3 | 28089 | 22704 | 22749 |
        | 4 | 27822 | 22437 | 22699 |
        **−267 per channel on BOTH references and −50 on zerobas, at every one of
        the four steps.** Five points in one boot, where D-HIMEMRES fitted the
        same rule from two points across separate runs.
        🎯 **AND THE VG-8020 IS DISKLESS.** It has no drive at all and still
        reserves 267 per `MAXFILES`, so this is base MSX BASIC's file-buffer
        reservation and NOT a Disk-BASIC artefact. It also puts a measurement
        behind the arithmetic this entry earlier flagged as unverified: the step
        is exactly 267 and a record is at most 256, so 267 = 256 + 11 of
        per-channel overhead — and 11 is precisely what D-RESERVE measured OPEN
        adding on every machine, zerobas included.
        ➡️ **SO ZEROBAS IS THE OUTLIER BY 217 B PER CHANNEL, BY DESIGN**, and
        attempt A closes exactly that gap in exactly the reference's way.
        🔴 **THE FIRST RUN PRINTED `0` FOR EVERY VG-8020 CELL.** It is diskless,
        so mounting a fixture made openMSX refuse to boot ("No disk drive A
        present") — the harness said so plainly and the probe still tabulated
        zeros, which read as measurements of zero rather than as an apparatus
        failure [[an-unnamed-outcome-reads-as-no-outcome]]. `MAXFILES` needs no
        disk; the mount is now skipped for that side and the row is real.
        ⚠️ **The 4 B gap between the two `base` figures is the PROGRAM TEXT** —
        `LEN=256` is two characters longer on two lines — not a reservation
        effect. Named so it is not read as one.
        ➡️ **WHAT THE NEXT ATTEMPT NEEDS TO KNOW.** Two shapes are now measured
        rather than imagined:
        | attempt | main B | RAM | result |
        |---|---|---|---|
        | record travels in the context (`FCH_CTXSZ` 50→306) | 16 | **256 B per reserved channel** | **both defects FIXED vs the reference**; reds `ramfree ctl.pool` (hardcoded `$D980`) and `array scalar.input.chain.oom` (zb-only, unexplained) |
        | write-back cache for mode 4 (`FCH_RECNOS`) | **0** | 32 B fixed | **breaks two-channel operation entirely** |
        The first WORKS and costs the RAM; the second costs nothing and does not
        work as written. A third shape — restage-only, with the write-back left
        to the existing `PUT` rather than done at switch time — is untried and is
        where I would start: it removes the mid-switch WRITE, which is the half
        that plausibly re-enters.~~ **← SUPERSEDED: option A shipped, above.**
        ⚠️ **THE CONTROL FAILED FIRST, FOR A REASON THAT WAS MINE**: its lines
        were numbered 10/20/50/30/60 to mirror the other row visually, so BASIC
        SORTED them and re-opened `#1` while it was still open — `<NO READING>`
        on both sides. The probe REFUSED to score `w.two` without its control
        rather than publishing a divergence with nothing to rule out the obvious
        rival cause.
        ~~🎯 **THE HAZARD WAS SPECIFIC AND IT DID NOT FIRE.**~~ `FSECTOR_BUF` and
        `FWBUF` are ONE buffer each, global, while the 50 B per-channel state
        carries position and cache markers (`FAT_CURCLUS`, `FAT_CLUSSEC`,
        `FAT_FATSEC` = *"FAT sector currently read"*). So a channel's restored
        state can say "the sector I need is loaded" while the shared buffer holds
        another channel's. Both test files are 12 bytes — ONE sector each — so
        `t.two` puts exactly that case live: #2's read evicts #1's sector, and
        #1's next read still returns `AAA`. zerobas does not trust the stale
        cache. The reference's per-channel buffers buy correctness we already
        have by other means.~~ **← REFUTED, see D-FIELDALIAS above.**
        ⚠️ **ONE PATTERN, NOT A PROOF — and the pattern was the wrong one.** What is NOT covered: RANDOM `GET`/`PUT`
        interleaved on two channels (a different path through `FSECTOR_BUF`),
        multi-sector files where a re-read is forced mid-record, and two-channel
        WRITE interleaving. If the buffers are ever suspected again, those are
        the three rows to add [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
        ~~🙋 **WHAT REMAINS IS JOOST'S AND ONLY HIS**: whether `FRE(0)` should
        AGREE with the references, which would mean reserving **267 B per
        channel** for sector buffers zerobas deliberately does not have
        (`FCH_CTXSZ equ FCH_STATESZ ; repack: block = state ONLY (no buffer)`).
        That is a faithfulness call about a MEASURED architectural difference —
        `R = 293 + 267×MAXFILES` there against `R = 12 + 50×MAXFILES` here — not
        a bug, and `crf-oomsay`/`crf-oomlst` cannot agree until it is made.~~
        ➡️ **SO `crf-oomsay` / `crf-oomlst` STAY DIFF, PERMANENTLY AND ON
        PURPOSE.** They compare `FRE(0)` across an architecture the two machines
        do not share, and the decision above is that zerobas keeps its own. Those
        two rows are now a RECORDED difference rather than an open question.
        Left in place rather than split into its own item: the measurement that
        frames the question is this entry, and a one-line item elsewhere would
        arrive without it.
      * ⚠️ ~~**UNVERIFIED, AND IT IS THE FIRST THING TO CHECK**: `sh_chan_addr` sits
        behind an assembly-time `IF` in `sub/strheap.asm`, so a build without
        D-FCH may not have it. Read the guard before believing the 7-byte shape~~
        [[a-filed-blocker-can-name-the-wrong-obstacle]].
        🟢 **CHECKED 2026-09-05 (D-TXTCEIL scout) — AND THE FILING NAMED THE
        WRONG SWITCH.** The guard is `IF CLEARPOOL`, not a D-FCH one, and
        `basic/sysvars.inc` ships `CLEARPOOL equ 1`, so `sh_chan_addr` **is**
        present. 🔴 **But `make switch-build-check` actively FLIPS CLEARPOOL TO 0**
        and requires that build to assemble — so a new caller of `fch_ctx_addr`
        from `dl_store` must be inside `IF CLEARPOOL` too, or it breaks a build
        the battery checks on every run. The filing did not state that, and it is
        the real constraint the wrong-switch note was gesturing at.
      * ⚠️ And the rule itself is UNMEASURED beyond the three rows below: what
        the references do when the program grows into the variables *while
        variables exist* is a different question from the empty-program case
        these rows drive.
      ✅ **RE-MEASURED 2026-08-20 AT `ef50f4c` — STILL LIVE, BYTE FOR BYTE**, all
      three rows and all three sides unchanged from the 2026-08-09 reading
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.8 and its §7 addendum): ` 148 ` / ` 148 ` / ` 646 ` free, the 32-byte
      line refused by both references and stored here, `99 REM Z` green on all
      three as the control. **Pinned** as `crf-oomsay` /
      `crf-oomlst`.
      🔴 **AND IT IS WHY D-DOTGAPS' OWN RULE HAS NO EMULATOR GATE.** No typed row
      can reach the OOM path on this side, so `crf-oom` agrees at ` 20  0 ` for
      the wrong reason (a *successful* store writing the same number the
      references write on a *refusal*), and R-DOT3a′ is gated by
      [`tests/test_program.py`](tests/test_program.py) alone. Fixing this bound
      would give that rule a real row.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, both numbers exactly as filed**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.8): after `CLEAR 300,TXTTAB+1000`, `FRE(0)` reads ` 148 ` on both
      references and ` 646 ` here, and the 32-byte line the references refuse is
      LISTED here beside the `99 REM Z` that fits.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
