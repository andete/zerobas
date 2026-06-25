# openMSX probing toolbox

A practical catalogue of the openMSX (this build) debug/probe surface, with the
exact Tcl that was **validated against a live boot** on
`National_CF-3300_ZEROBASDISK`. The point is to stop rediscovering capabilities
mid-hunt: before reaching for a new ad-hoc probe, check whether one of these
already answers the question.

This documents the **emulator tool**, not any oracle ROM — clean-room safe.

Run pattern used throughout (headless, fast, self-exiting):

```tcl
set throttle off          ;# run as fast as the host allows
set renderer none         ;# no video output
proc log {m} { set f [open /tmp/x.out a]; puts $f $m; close $f }
# ... set traps ...
after time 30 { log DONE; exit }   ;# 'after time N' = N EMULATED seconds
```

`openmsx -machine <m> -diska <dsk> -script <tcl>`. A full DOS boot + derail fits
in ~30 emulated seconds and runs in a few real seconds with `throttle off`.

> **Command structure note.** This build uses the *newer* nested form:
> `debug breakpoint create|list|configure|remove`, `debug watchpoint …`,
> `debug condition …`, `debug probe …`. The old flat `debug set_bp` /
> `debug set_condition` may not exist here — prefer the nested form.

---

## 1. Breakpoints, watchpoints, conditions

All three are created with `-property value` pairs and share `-condition`,
`-command`, `-enabled`, `-once`. The default `-command` is `debug break`.

### Breakpoint — single address
```tcl
debug breakpoint create -address 0xD88A -once -command { ... }
```

### Watchpoint — ADDRESS RANGE + memory access (the workhorse)
`-address` accepts a **begin/end pair**; the range is checked natively in C++,
so it is cheap while execution is *outside* the range. Types: `read_mem`,
`write_mem`, `read_io`, `write_io`.

**Validated fact: `read_mem` fires on the Z80 OPCODE FETCH** (and on every
operand/data byte read in range). At the moment it fires, `[reg PC]` is the
address of the executing instruction, so `[debug read memory [reg PC]]` reads
that instruction's **opcode**.

```tcl
# "execute an opcode X anywhere in a band" trap, with no per-byte breakpoint list:
debug watchpoint create -type read_mem -address {0x4000 0x7fff} -once \
  -condition {[reg PC] >= 0x4000 && [reg PC] <= 0x7fff && [debug read memory [reg PC]] == 0x00} \
  -command { ... }
```
Because the condition tests the byte at **PC** (the opcode), in-range *data*
reads of that byte value do **not** false-trip — only execution does.

> Cost note: while execution is heavily *inside* the band, the Tcl `-condition`
> is evaluated on every in-range read, which slows emulation. Keep bands tight,
> or gate with `reverse` (§4) to bound the window.

### Condition — evaluated every instruction (use sparingly)
```tcl
debug condition create -command { lappend ::ring [format %04X [reg PC]] }
```
No address gating → per-instruction Tcl → slow over a whole boot. Best created
*inside* a breakpoint/probe command so it only runs over a short window.

### Listing / removing
`debug breakpoint list` / `watchpoint list` / `condition list` return a Tcl dict
keyed by id; `... remove <id>`, `... configure <id> -prop val`.

---

## 2. Hardware probes — `debug probe` (the big find)

Named hardware signals you can break on **without** any per-instruction
condition. `debug probe list` on this machine:

```
VDP.IRQvertical  VDP.IRQhorizontal  VDP.commandExecuting
z80.pendingIRQ   z80.acceptIRQ
```

- `debug probe read <name>` — current value.
- `debug probe set_bp <name> [-once] [<cond>] [<cmd>]` — break when it changes/fires.

**`z80.acceptIRQ` is the interrupt-storm catcher.** It fires at the exact moment
the Z80 *accepts* a maskable interrupt; `[reg PC]` is the interrupted code's PC.
Validated — logs the PC of each acceptance:

```tcl
debug probe set_bp z80.acceptIRQ {} {
  log "ACCEPT PC=[format %04X [reg PC]] SP=[format %04X [reg SP]] emt=[format %.3f [machine_info time]]"
}
```
Pair with a `-cond` (e.g. `[reg PC] == 0x4251` or an SP threshold) to catch the
*first storm acceptance* directly, then jump to §4 to find what derailed there.

`VDP.IRQvertical` / `VDP.IRQhorizontal` expose the VDP interrupt sources (the
H.TIMI / vertical-retrace lines) — useful when reasoning about VDP-ack timing.

---

## 3. Reading state: registers, IFF, memory by slot

### CPU registers debuggable — `{CPU regs}` (byte-addressable)
```
0 A  1 F  2 B  3 C  4 D  5 E  6 H  7 L      (8..15 = shadow set)
16 IXH 17 IXL 18 IYH 19 IYL  20 PCH 21 PCL  22 SPH 23 SPL
24 I  25 R  26 IM  27 IFF
```
**Byte 27 carries IFF** — bit0 = IFF1, bit1 = IFF2, **bit2 = "could accept an IRQ
at the start of the current instruction"** (IFF1 AND last-insn-was-not-EI).
(`reg IFF1` as a register name does NOT exist — read byte 27 instead.)
```tcl
set b [debug read {CPU regs} 27]
# IFF1=[expr {$b&1}]  IFF2=[expr {($b>>1)&1}]  canAccept=[expr {($b>>2)&1}]
```
Byte 25 = R (7-bit refresh) — a cheap coarse "did the CPU advance" tick, but it
wraps every 128; use `machine_info time` for real progress.

`reg PC` / `reg SP` / `reg AF` … remain the convenient per-register accessors.

### Memory
- `debug read memory <addr>` / `debug write memory <addr> <v>` — current paging.
- `debug read_block memory <addr> <len>` — bulk read.
- `{slotted memory}` debuggable — read/write a specific **slot/segment**
  regardless of what is currently paged in (read ROM that isn't mapped, etc.).
- `{Main RAM}`, `{physical VRAM}`, `VRAM`, `{VDP regs}`, `{PSG regs}`,
  `ioports`, `keymatrix`, … (see `debug list` for the full set).

### Disassembly
- `debug disasm <addr>` → `{mnemonic hexbytes}`; instruction length =
  `[string length [lindex $d 1]] / 2`.
- `debug disasm_blob <binary> <addr> [<symfn>]` → disassemble a Tcl byte string,
  with an optional symbol-substitution callback.

---

## 4. Reverse / replay — `reverse` (rewind to the cause)

Full time-travel. Snapshots are taken ~every emulated second.

```tcl
reverse start                 ;# begin collecting
reverse status                ;# -> dict: begin/end/current/snapshots/last_event
reverse goback <n>            ;# go back n seconds (enters 'replaying' mode)
reverse goto <time>           ;# jump to an absolute emulated time
reverse truncatereplay        ;# drop 'future' data, resume live from here
reverse savereplay [name] / loadreplay [-goto …] name
```
Validated: from t=3 (PC 435E), `goback 1` → t=2 (PC 7D0D); `goto 1.0` → t=1
(PC 7D63).

**Derail-locator workflow** (the reason this matters): pick a **predicate** that is
false during healthy execution and true at the failure (e.g. `[reg SP]` in the ROM
page, or `[debug read memory 0x4251] != 0xC3` for "disk ROM left page 1"). Run to a
settle time T with `reverse` collecting, then **binary-search emulated time** for the
first instant the predicate flips (`reverse goto mid`, evaluate, narrow). Each probe
is O(1) — no trace. The `LAST-GOOD` instruction at the flip is the cause; a forward
trace across it shows the consequence. Choosing the predicate is the judgment; the
bisect is mechanical. (A symptom predicate finds the symptom — SP-in-ROM-page lands
on the storm; the paging predicate lands on the root. Same tool, different question.)

> **Stepping gotcha:** `debug step` does **NOT** advance inside an `after time`
> callback (nor over `-control stdio`) — the reactor isn't ticking. To trace forward
> from a `reverse goto` point, install a per-instruction `debug condition` and
> **return** from the callback (let the reactor free-run); the condition logs and
> `exit`s after N. Single-stepping only works in interactive break mode.

---

## 5. Symbols — make traces readable

`debug symbols load <file> [<type>]`; types: `asMSX generic htc NoICE vasm
wlalink linkmap`. Lookup: `debug symbols lookup -name <n>` or `$sym(<n>)`.

**Our pasmo `--sym` output autodetects as `htc` and fails to parse.** Convert to
the `generic` format (`NAME: equ 0xVALUE`) first:

```sh
pasmo -I disk --bin disk/disk.asm build/disk.rom build/disk.sym
python3 tools/sym_to_openmsx.py build/disk.sym build/disk.omsx.sym
```
```tcl
debug symbols load build/disk.omsx.sym generic   ;# validated: 352 symbols
```

---

## 6. Context / timing

- `machine_info time` — emulated seconds (the progress/timestamp of record).
- `machine_info z80_freq`, `VDP_line_in_frame`, `VDP_frame_count`,
  `input_port`/`output_port`, `issubslotted`, `slot`, … (`machine_info` lists
  all topics).
- `openmsx_info` — `version`, `machines`, `extensions`, `romtype`, `setting`, …

---

## 7. Automation harness — `omsx_session.py` + `disk_derail_locate.py`

The mechanical loop (write Tcl → launch → poll → parse → decide → repeat) is the
token sink, and it is fully encodable. Two Python modules fold it away:

- **`probes/disk/omsx_session.py` — `OmsxRun` job-runner.** Composes a Tcl job from
  validated primitives, runs it in ONE openMSX boot, returns parsed records.
  Primitives: `bisect_locate(predicate, lo, settle, trace_n)` (the full boot →
  time-bisect → LAST-GOOD/FIRST-BAD → forward-trace composite), `forward_from`,
  `time_sweep`. Every record is one `ctx` line (regs + IFF + t + `m4251` + disasm).
  > **Architecture note:** `-control stdio` (interactive REPL) was tried and rejected
  > — that openMSX does **not** free-run its emulation between commands (`debug cont`,
  > `set pause false`, even `debug step` leave the CPU frozen at reset). The
  > `-script` + `after time` mechanism free-runs reliably, so each high-level op is
  > one generated script / one boot. Faithful data collection only — no conclusions.

- **`probes/disk/disk_derail_locate.py` — thin locator CLI.** Runs `bisect_locate`,
  recognises only KNOWN mechanical patterns (slot/subslot write, 2-PC storm
  oscillation), and ends in one verdict: `RESOLVED` / `DECISION-NEEDED` / `STUCK`.
  It escalates the semantic "is this correct?" call and *suggests* the next
  mechanical predicate but does not auto-recurse. Presets: `sp-rompage`, `paging-p1`,
  `sp-lost`.

**Trust rule (validated):** the harness is only trustworthy because it reproduces a
hand-verified result. `disk_derail_locate.py --preset paging-p1` independently
re-derives the 2026-06-25 root cause (`$E7AA: ld ($ffff),a` unmaps page 1 →
COMMAND.COM storm). Re-run that after touching the harness; if it stops naming
`$E7AA`, the harness — not the ROM — changed.

```sh
python3 probes/disk/disk_derail_locate.py --preset paging-p1   # → DECISION-NEEDED @ $E7AA
python3 probes/disk/disk_derail_locate.py --preset sp-rompage  # → storm, redirects to root
```

---

## Quick chooser

| Question | Reach for |
|---|---|
| "Did execution ever reach opcode/region X?" | `read_mem` watchpoint, range + opcode `-condition` (§1) |
| "When/where is an interrupt accepted?" | `z80.acceptIRQ` probe (§2) |
| "Were interrupts enabled at this point?" | `{CPU regs}` byte 27 (§3) |
| "What jumped control to here?" | `reverse goto` before it, forward-trace via condition (§4) |
| "Where does failure-state X first arise?" | `disk_derail_locate.py` / `bisect_locate` (§7) |
| "Read ROM/RAM that isn't paged in" | `{slotted memory}` (§3) |
| "Make a PC trace legible" | convert + `debug symbols load … generic` (§5) |

Origin: 2026-06-25 toolbox sweep, after the dead-zone NOP tripwire's premise was
falsified (no `$00` opcode executes anywhere in $0000–$FFFF during the boot) —
which prompted mapping the full instrument set before continuing the derail hunt.
See `probes/disk/disk_probe_dosboot_tripwire.py` and the review queue.
