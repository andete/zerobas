import sys
p = 'TODO.md'
s = open(p).read()
anchor = """      🤖 **AUTONOMOUS** — the audit, then the merge if the audit holds; any
      crossing the audit cannot bracket comes back to Joost.
"""
if s.count(anchor) != 1:
    sys.exit(f'REFUSE: anchor count {s.count(anchor)}')
add = """      🔬 **THE STATIC AUDIT, DONE 2026-09-24 (`scratchpad/bufaudit.py`,
      `scratchpad/bufaudit.out`)** — label-level call closure over every source
      `disk.asm` assembles (10063 lines, 589 labels, over-approximating: any
      `call`/`jp`/`jr`/`djnz`/`ld rr,<label>` is an edge, and an unterminated
      label falls through), roots = the 18 `hook_tab` pairs; then each hook's
      MAIN call site read by hand.
      | crossing | touches a buffer? | main's bracket | verdict |
      |---|---|---|---|
      | `H_DSKF` `H_NAME` `H_KILL` `H_FILE` `H_COPY` | yes — `FAT_DBUF`/`FAT_MBUF` | `chan_gate` (full: save + restage) at every site | ✅ bracketed |
      | `H_FOPEN` → `hk_dpload` (4 sites: `cload`, `files` ×2, `save`) | yes | `chan_gate` at all 4 | ✅ bracketed |
      | `H_LSET`/`H_RSET` → `hk_lrset` | writes `FSECTOR_BUF` **as the record, on purpose** | `chan_gate_bare` | ✅ no sector I/O — the bare gate's own rule |
      | `H_FIELD` · `H_CVI/S/D` · `H_MKI/S/D` · `H_ERRP` | no (closures of 1–9 labels, none name a buffer) | n/a | ✅ clean |
      | `H_DSKI`/`H_DSKO` | presence only; the body is a sub-ROM tenant on `FWBUF` | `dsk_core` → `chan_restore` | ✅ bracketed |
      | `initext` INIT CALSLT · `interp` banner CALSLT · the DOS-boot bridge | yes | none needed | ✅ boot — no channel can be live |
      | sub-ROM FATPRIM → `DSKIO` (`$4010`) | into the caller's page-3 buffer — main's own engine | it IS the engine | ✅ |
      | **`SYSTEM` `$F37D` → `bdos_entry`** | **yes — the `fat_bufinit` pair** | **none: the caller is USER machine code** | 🔴 **cannot be bracketed** |
      | **`HPHYD` `$FFA7` → `DSKIO` with a PAGE-1 destination** | **yes — bounces through `SECTOR_BUF`** (`driver.asm`) | **none: user machine code** | 🔴 **cannot be bracketed** |
      🟢 **EVERY BASIC-VERB CROSSING HOLDS.** The two that do not are the entry
      points a user's `USR`/`BLOAD`ed routine can call while a BASIC channel is
      open; main is not running and cannot restage around them.
      ⚠️ **THEY ALREADY ALIAS MAIN TODAY — THE MERGE MOVES WHAT THEY HIT, IT
      DOES NOT CREATE THE CLASS.** Disk's `SECTOR_BUF` `$E2A0` sits on main's
      `TEMPPOOL` and the `GFX_*` cells, and `WBUF` on 416 B of the staged
      sector. BDOS also keeps a sector in `SECTOR_BUF` ACROSS calls
      (`BDOS_RECIDX`), which any string expression between two calls
      already destroys. And `DBUF_PTR`/`MBUF_PTR` (`$E816`/`$E818`, set once
      at INIT) lie INSIDE main's `FWBUF`: after any BASIC file op a BDOS
      rename (`$17`, `disk/fat.asm`, the only reader) writes from a garbage
      address. All three are the same class: BDOS from BASIC, which nothing
      measures.
      ➡️ **WHAT THE MERGE ITSELF NEEDS, found by the same reading:** disk's
      `SECTOR_BUF`/`WBUF` → `$E5C0`/`$E7C0`, and every disk cell now in
      `$E754..$E779` and `$E7E8..$E819` (the `RDBLK_*`/`WRBLK_*`/`FREAD_*`
      BDOS state, `P1_DEST`, `DBUF_PTR`/`MBUF_PTR`, and the boot-only
      `R30_*`/`BOOT_SV_*`/`CALSLT_HL`) moved OUT, or disk's own fills would
      overwrite its own state. ~45 B; main's map has 1325 B of holes.
      🙋 **BACK TO JOOST, as the ruling said it would come:** the audit holds
      for every BASIC verb and fails for BDOS/PHYDIO called from user machine
      code. Proceed with the merge and declare BDOS-from-BASIC outside the
      contract (as it already silently is), or not?
"""
s = s.replace(anchor, anchor + add)
open(p, 'w').write(s)
print('ok')
