# Spec — audio Slice 2a: `IDX_PLAY_PARSE` (linear MML → RAM queues)

**Status: LANDED (2026-07-21).** D1-A / D2-A / D3 / D4-B / D5 all implemented and
gated. The VG-8020 differential (`make play-acceptance`) **corrected two grammar
facts** the pre-impl spec drew from a broader (non-MSX1) MML reference — see the
**Empirical corrections** box below. Slice-design addendum to the
signed-off arc spec [`spec-basic-audio-play.md`](spec-basic-audio-play.md). Slice 1
(`SOUND`) is landed. This slice adds the `PLAY` statement's **parser half**: a
page-1 sub-ROM tenant (`IDX_PLAY_PARSE`, index **14**) that parses each MML voice
string into an own-design RAM packet queue and sets `MUSICF` last. **No live drain
yet** — the interrupt-driven servicer + `H.TIMI` seam is Slice 3. Slice 2a is
validated **statically**: our own host decoder reads the queue bytes back and
asserts they match the MML; `PLAY` returns without hanging; the program-visible
work-area cells land at their reference addresses (§2.4 of the arc spec).

> **Empirical corrections (VG-8020 differential, 2026-07-21) — the load-bearing
> pass, [memory: error-handling-arc].** The green host test + green build hid TWO
> real integration bugs AND the differential overturned two spec assumptions:
> 1. **`PLAY` was never added to the keyword table** — the tokeniser never emitted
>    `$C1`, so `ex_play` never ran. Host test missed it (it pokes tokens directly).
> 2. **`ex_play` clobbered `HL` across the `subrom_call` CALSLT** — the statement
>    cursor was garbage, so the next statement (`:`/next line) Syntax-errored. Host
>    test missed it (no CALSLT, no statement chaining). Fixed: `push`/`pop hl`.
> 3. **`&` (tie) is NOT MSX1 PLAY MML** — the VG-8020 raises Illegal function call
>    (ERR 5) for `C&C`/`C&D`/`C&`. Removed the tie machinery; `&` now → ERR 5. (The
>    spec §2.2 list drew `&` from a broader MML reference; D5 "all linear incl. &"
>    is corrected to "all linear, `&` is out — MSX1 rejects it".)
> 4. **A voice is a required string expression; a bare comma is a Syntax error.**
>    `PLAY,"E"` → ERR 2, `PLAY 5` → ERR 13, but `PLAY"","E"` → ok (empty string is
>    the faithful "skip a voice"). The pre-impl "bare comma = skip voice" guess was
>    wrong. Syntax error is raised via `raise_error` (trappable by `ON ERROR`, like
>    the reference), not the un-trappable `stmt_error`.
>
> All four are locked by `probes/basic/basic_probe_play.py` (15 differential cases).

Provenance boundary is inherited from the arc spec §0: MML syntax + work-area
addresses + BIOS/PSG contracts are published clean-provenance; the **packet
encoding and duration accounting are own-design, host-validated** — never lifted
from stock ROM ([memory: no-reference-rom-disasm]).

---

## 1. What lands in 2a vs. what defers

| Piece | Slice | Notes |
|---|---|---|
| `PLAY_TOKEN` ($C1) statement dispatch | 2a | already captured, [`sysvars.inc:311`](../basic/sysvars.inc) |
| Resident `ex_play` stub: parse `PLAY <str>[,<str>[,<str>]]`, eval each string arg, marshal (body-ptr, len)×3 to RAM | 2a | uses `str_eval` (§4) |
| `IDX_PLAY_PARSE` tenant: MML → per-voice packet queue; set `MUSICF` last | 2a | the big code chunk; page-1 leaf |
| GICINI-equiv init (zero queues, clear `MUSICF`, silence 3 tone channels) | 2a | first `PLAY` needs it (arc spec §3.E) |
| Linear MML grammar: `A`–`G` `#/+/-` len, `N`, `R`, `O`, `>`, `<`, `L`, `.`, `T`, `V`, `S`, `M`, `&` | 2a | full linear set |
| `X<var>;` substring exec (recursion + var lookup) | **2b** | arc spec Q6 |
| Live queue drain in the ISR (`play_service` + `H.TIMI` seam) | **3** | the async half |
| Byte-exact match of the *reference's* queue bytes | **3-stretch** | arc spec §3.1; ours is own-design |
| Unbounded strings via incremental ring-buffer refill | **3** | see §3, the queue-model decision |

---

## 2. The queue model — the one real architectural fork (DECISION D1)

**The reference is a producer/consumer ring.** On a real MSX the interpreter is a
*producer* filling a small fixed per-voice ring queue; the timer ISR is the
*consumer* draining it. A long string does not need a huge buffer because the
player drains as the interpreter fills (and the interpreter blocks/waits when the
ring is momentarily full). That model **requires the live consumer**, which does
not exist until Slice 3.

**Consequence for 2a:** with no consumer, the parser cannot drain, so it can only
buffer what fits a fixed per-voice buffer. Two ways to stage this:

- **D1-A (recommended): fixed per-voice buffer, whole-string parse up front, error
  on overflow.** Allocate a fixed queue buffer per voice (proposed **256 B/voice**,
  §5). Parse the entire string into it; if it overflows, raise the reference's
  long-string error (`String too long`, ERR 15 — confirm the exact error black-box
  in impl). Representative 2a MML fits comfortably. Slice 3 replaces the "parse it
  all now" front-end with the incremental producer/consumer refill for unbounded
  strings, reusing the *same packet format*. Clean risk-staging: the format and the
  static decoder are proven in 2a; only the refill scheduling is new in 3.
- **D1-B: build the full ring machinery now** (head/tail wrap, "producer blocks
  when full"), but with the consumer stubbed. More code up front, and the blocking
  path can't actually be exercised without the consumer — so it would ship untested,
  the exact trap the arc keeps hitting ([memory: error-handling-arc]). Not
  recommended.

**Recommendation: D1-A.** It keeps 2a a pure synchronous leaf (matches
`IDX_FORMAT`/`IDX_FATPRIM`), and the fixed buffer doubles as the Slice-3 ring
storage.

---

## 3. Duration accounting — DECISION D2

Each note's on-time must be expressed in a unit the Slice-3 servicer decrements
once per interrupt. Two encodings:

- **D2-A (recommended): bake integer *frames* at parse time.** The parser converts
  `(tempo T, note length L, dots, ties)` → an integer frame count stored in the
  packet. The servicer just decrements it per interrupt — trivial, register-cheap.
  Proposed own-design formula (documented deviation, [memory: bug-for-bug-compat-over-accuracy]):

  ```
  frames_per_whole_note = round( FRAMES_PER_MIN * 4 / T )     ; T = tempo, def 120
  note_frames           = round( frames_per_whole_note / L )  ; then × dot/tie factors
  ```

  with `FRAMES_PER_MIN` a fixed own constant. The exact constant that matches the
  VG-8020's music speed is a **Slice-3 differential** target (PSG-write frame trace
  vs. the real machine); 2a's host decoder checks *our* formula, not the reference's
  tick count. This defers the PAL/NTSC-frequency question to Slice 3 where it can be
  measured, and keeps the parser frequency-agnostic in behavior (it emits frames
  from a fixed constant; if S3 finds the reference scales by VDP frequency, the
  constant/scaling moves into the servicer then).
- **D2-B: store tempo-independent ticks + let the servicer scale by a tempo
  accumulator.** More faithful to the reference's internal model, but pushes tempo
  math into the ISR (Slice 3) and complicates 2a's static decoder. Defer.

**Recommendation: D2-A** (bake frames), revisit the constant in Slice 3's frame
differential.

---

## 4. Resident `ex_play` stub (main ROM, repack-only)

Mirrors `ex_sound` + the PRINT string-item loop. Dispatched from
[`interp.asm:262`](../basic/interp.asm) as `cp PLAY_TOKEN / jp z,ex_play`, inside
the existing `IF ROM_BASE < $4000` block.

```
ex_play:
        inc  hl                      ; past PLAY token
        ; --- init audio work area on first use (GICINI-equiv) ---
        call play_init_if_needed     ; zero queues + MUSICF, silence tone channels
        ; --- parse up to 3 comma-separated string args ---
        ld   b,0                     ; B = voice index 0..2
pl_arg: call skip_spaces
        ld   a,(hl)
        cp   ','                     ; empty voice (leading ',') -> channel unchanged
        jr   z,pl_skip
        or   a
        jr   z,pl_go                 ; EOL -> done collecting
        cp   COLON
        jr   z,pl_go
        push bc
        call str_eval                ; HL->STRPTR desc, VALTYP=1, CF=1 ok; advances HL
        pop  bc
        jp   nc,stmt_error           ; not a string operand -> Syntax error
        ; deref body ptr + len from the descriptor, stash in AUDIO_VOICE[B]
        ...marshal (body_ptr:2, len:1) into AUDIO_* RAM for voice B...
pl_next:
        inc  b
        ld   a,b
        cp   3
        jr   nc,pl_go                ; max 3 voices
        call skip_spaces
        ld   a,(hl)
        cp   ','
        jr   z,pl_comma
        jr   pl_go                   ; no comma -> end of list
pl_comma:
        inc  hl
        jr   pl_arg
pl_go:  call check_expr_errors       ; FPERR at stmt boundary (str_eval defers errors)
        ; one CALSLT into the tenant (all voices marshalled)
        ld   ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_PLAY_PARSE
        call subrom_call
        jp   c,<subrom-absent error> ; defensive; merged ROM always ships it
        ld   a,(AUDIO_STATUS)        ; tenant result via RAM (CF is the absence signal)
        or   a
        jp   nz,play_parse_error     ; e.g. Illegal function call / String too long
        jp   exec_stmt               ; PLAY returns immediately; chain next stmt
```

Key ABI facts (from the tenant survey):
- **Marshal everything through page-3 RAM** — CALSLT clobbers all registers. The
  stub derefs each string's **body pointer** (not the descriptor) + length and
  writes them to a fresh `AUDIO_*` block in the `$E9xx` scratch region (the
  `DISKOP_*` idiom, [`sysvars.inc:1183`](../basic/sysvars.inc)). String bodies live
  in RAM (program text ≥ `TXTTAB`, or the string heap) — always visible to a page-1
  tenant, which keeps RAM pages 2–3 mapped.
- **`subrom_call` ABI:** `IX = $4010 + 3*14`; CF=1 means *sub-ROM absent, no call
  made*; the tenant's real success/error rides back in `AUDIO_STATUS`
  ([`subromcall.asm:55`](../basic/subromcall.asm), [`format.asm:131`](../basic/format.asm)).
- **`str_eval`** ([`strvar.asm:22`](../basic/strvar.asm)): `HL` at operand → sets
  `STRPTR`→`[len][ptr]` descriptor (repack build), `VALTYP=1`, `CF=1` on success,
  advances `HL`; deref the body with `pu_deref_body`
  ([`str-engine.asm:124`](../basic/str-engine.asm)). Errors are deferred → check
  `FPERR`/`check_expr_errors` at the statement boundary.

---

## 5. RAM layout — the FULL standard MSX music work area (Q2 faithfulness = yes)

**Measured 2026-07-21 (drove the placement).** Page-3 RAM below the C-BIOS
sysvar/stack ceiling (`~$F380`) is *full* — the disk file-channel contexts
(`FCH_CTX $EA00..$EE63`), FIELD/GET-PUT scratch, `FLD_DESC`, and the float/
trampoline/disk cells (`$F000..$F37F`) leave no room for dedicated queue buffers.
But the **standard MSX music work area at `$F959..$FBAF` is reserved by C-BIOS and
otherwise unused** (zerobas touches only `EXBRSA $FAF8` in that span; C-BIOS's
`PLAY` is a boot-reserved `TODO` stub — it inits `QUETAB` but never drains). So we
place **everything at its documented MSX2-TH reference address** — the placement
*is* the faithfulness. This is a published-contract layout (MSX2 Technical Handbook
work-area appendix), confirmed reserved by our open target C-BIOS; no stock-ROM
disassembly, no C-BIOS bytes copied ([memory: no-reference-rom-disasm]).

| Addr | Name | Struct | 2a use |
|---|---|---|---|
| `F959H` | `QUETAB` | 4 × 6-byte ring descriptors `[put:1][get:1][putback:1][size:1][addr:2]` (3 voice + 1 RS232) | per-voice ring cursor into its buffer; parser advances `put`, `get`=0 (no drain yet), `size`+`addr` from init |
| `F975H` | `VOICAQ` | 128 B | voice-0 packet buffer |
| `F9F5H` | `VOICBQ` | 128 B | voice-1 packet buffer |
| `FA75H` | `VOICCQ` | 128 B | voice-2 packet buffer |
| `FB38H` | `VOICEN` | 1 B | voice currently being parsed (0–2) |
| `FB3EH` | `QUEUEN` | 1 B | active queue # scratch |
| `FB3FH` | `MUSICF` | 1 B | bitmask, bit *v* = voice *v* active. **Set LAST** (arc spec §4.3) |
| `FB40H` | `PLYCNT` | 1 B | PLAY statements parsed-not-executed |
| `FB41H` | `VCBA` | 37 B (`VCBB $FB66`, `VCBC $FB8B`) | per-voice control block, incl. the persisted parse state — see below |

**VCB fields used in 2a** (offsets from `VCBA/VCBB/VCBC`, MSX2-TH layout): `TONPRX`
+10 pitch, `AMPLTX` +12 amplitude, `OCTAVX` +15 octave, `NOTELX` +16 default
length, `TEMPOX` +17 tempo, `VOLUMX` +18 volume, `ENVLPX` +19 envelope shape,
`METREX` +0 interrupt counter (the per-note frame countdown the Slice-3 servicer
decrements — its existence **confirms D2-A**: the reference *does* store a frame
count per note). `VCXSTP` +5 is the `X`-nesting stack pointer reserved for Slice 2b.

**Queue buffers are 128 B/voice (D1-A) at the faithful `VOICxQ` addresses** — this
*is* the real MSX buffer size, so even the overflow point (long-string error) is
faithful, not an arbitrary own cap. Marshalling cells (`AUDIO_VOICE_PTR/LEN`×3,
`AUDIO_STATUS`) go in the `$E9xx`-style page-3 scratch like `DISKOP_*` (input to
the tenant; the queues/`MUSICF` are the output, read directly).

**DECISION D4-B (persist) — now faithful for free.** The VCB *is* the reference's
per-voice persisted state; `OCTAVX/NOTELX/TEMPOX/VOLUMX/ENVLPX` survive between
`PLAY` statements exactly as on real MSX. Cold-boot `play_init` seeds the defaults
(`O4 L4 T120 V8`, envelope off).

---

## 6. Packet format (own-design — DECISION D3)

Opcode-prefixed byte stream written into that voice's `VOICxQ` buffer via its
`QUETAB` ring descriptor (`get`=0, `put` advances as packets append; `MUSICF` bit
set last). The *packet bytes* are own-design — byte-exact match to the reference's
queue content is the arc-spec §3.1 stretch, deferred to Slice 3. Opcodes (clarity
+ extensibility over bit-packing; the 128 B buffer is the pressure point, watched
by the overflow check):

| Opcode | Bytes | Payload | Servicer action (Slice 3) |
|---|---|---|---|
| `OP_NOTE` `$00` | 6 | `amp:1, tone_lo:1, tone_hi:1, dur:2` | program tone period (regs 2v,2v+1) + amplitude (reg 8+v); count down `dur` frames |
| `OP_ENV` `$01` | 4 | `shape:1, per_lo:1, per_hi:1` | write env period (regs 11/12) + shape (reg 13); amp-reg env bit handled via `OP_NOTE.amp` bit4 |
| `OP_END` `$FF` | 1 | — | clear this voice's `MUSICF` bit; stop draining |

- **Rest** = `OP_NOTE` with `amp=0` (channel silent for `dur` frames) — no separate
  rest opcode needed.
- **`amp`** byte: bits 0–3 = volume 0–15; **bit4 = envelope mode** (PSG amplitude
  register value `$10`, channel follows the envelope generator). Set by an `S`
  command taking effect for subsequent notes.
- **tone period** = 12-bit PSG value from note+octave+accidental via an own note→
  period table (equal-tempered, A4 tuning documented in impl). `tone_hi` uses the
  low nibble (regs are 12-bit).
- **`N n`** emits an `OP_NOTE` by absolute note number; **`M`/`S`** emit `OP_ENV`;
  `T`/`V`/`L`/`O`/`>`/`<`/`.` mutate parse state, not packets.

The Slice-2a host decoder (`tests/test_play_parse.py`) walks this exact stream and
reconstructs (pitch, amp, frames) per note to compare against the MML — so the
format is locked by an executable oracle, not prose.

---

## 7. Error surface (raised by the resident stub, tenant returns status)

Like `dirverb`, the tenant funnels a disposition into `AUDIO_STATUS`; the resident
stub raises. ERR numbers **VG-8020-confirmed** (`basic_probe_play.py`):

- Bad MML (unknown command incl. `&`, out-of-range `O`/`T`/`V`/`L`, malformed) →
  `Illegal function call` (**ERR 5**) — matches the reference on all tested cases.
- Missing/bare-comma voice operand (`PLAY,"E"`, a 4th voice) → `Syntax error`
  (**ERR 2**), raised via `raise_error` so `ON ERROR` traps it (the reference does).
- Numeric argument (`PLAY 5`) → `Type mismatch` (**ERR 13**) via `str_eval` CF=0.
- Queue overflow (D1-A, string longer than the 128 B `VOICxQ`) → `String too long`
  (**ERR 15**). (Not yet differential-checked against the reference's exact code for
  an over-long string; the 128 B cap is the faithful buffer size regardless.)

---

## 8. Gates (Definition of Done, 2a)

1. **`tests/test_play_parse.py`** (fast host layer, emulator-free, `unit-test`):
   build `main-reloc` + the sub image; call `ex_play`/the tenant on representative
   MML strings; **decode the resulting queue bytes with the §6 walker and assert
   pitch/amp/frames match the MML**. Cover: notes+accidentals, octave `O`/`>`/`<`,
   `L`/explicit length/`.`dots, `R` rest, `T` tempo→frames, `V` volume, `N`, `S`/`M`
   envelope, `&` tie, multi-voice `PLAY a$,b$,c$`, empty voice (`,,`), overflow error.
2. **`MUSICF`/`QUETAB` land at the §5 addresses** (RAM-faithfulness variable-level
   check): after a `PLAY`, `MUSICF` bits reflect the non-empty voices; `QUETAB`
   descriptors point into the buffers. Asserted in the host test.
3. **`PLAY` returns without hanging** (no live drain to wait on) — the host test
   returns; add an openMSX smoke case that `PLAY "cde"` then the REPL prompt returns.
4. **`MUSICF` set LAST** (ordering, arc spec §4.3): assert in the tenant test that
   the queues are fully written before `MUSICF` is nonzero (structural check on the
   parse routine, so Slice 3's ISR can never drain a half-built queue).
5. **PLAY token crunch byte-identity** ($C1) added to `basic_probe_crunch.py`
   (mirrors the Slice-1 SOUND $C4 case).
6. **Lean ROM byte-identical** (`PLAY` is repack-only, whole body under
   `IF ROM_BASE < $4000`); report page-1 tenant bytes + resident stub/init bytes;
   name the funder if page-1 pressure appears (disk/file eviction left ~1.1 KB —
   [memory: basic-rom-space-and-growth]).

Slice 3 owns the **PSG-write frame-trace differential vs. VG-8020** (the
load-bearing empirical pass): our own duration constant (D2), the exact error ERR
numbers, and byte-exact reference-queue matching are all *confirmed or tuned there*.
2a's job is the parser + a self-consistent own-format decoder.

---

## 9. Decisions (SIGNED OFF 2026-07-21)

- **D1** — queue model: **D1-A** ✅ fixed 256 B/voice buffer, whole-string parse,
  error on overflow (ring refill → Slice 3).
- **D2** — duration unit: **D2-A** ✅ bake integer frames at parse time from an
  own-design tempo constant (exact value tuned in Slice 3's frame differential).
- **D3** — packet format: **✅** the §6 opcode stream (`OP_NOTE`/`OP_ENV`/`OP_END`),
  locked by the host decoder.
- **D4** — per-voice state persistence across `PLAY` statements: **D4-B** ✅ persist
  octave/length/tempo/volume in `VCBA` (faithful, cheap); cold-boot defaults are
  the `play_init` values.
- **D5** — grammar coverage: **✅ (corrected)** all linear commands in 2a EXCEPT
  `&` — the VG-8020 differential proved `&` is not MSX1 PLAY MML (→ ERR 5). `X` → 2b.

---

## Appendix — sources (inherited from arc spec §A)

MSX Wiki PLAY/MML; map.grauw.nl BIOS list (`GICINI $0090`, `WRTPSG $0093`,
`RDPSG $0096`, `STRTMS $0099`, `GETVCP $0150`, `GETVC2 $0153`; PSG ports `$A0/$A1/
$A2`); MSX2 Technical Handbook work-area appendix (`MUSICF FB3FH`, `PLYCNT FB40H`,
`VOICEN FB38H`, `QUETAB F959H`, `VCBA FB41H`, `H.TIMI FD9FH`). Packet encoding +
duration accounting are own-design, host-validated ([memory: no-reference-rom-disasm]).
