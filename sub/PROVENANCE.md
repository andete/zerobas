# Provenance log — zerobas-sub

Every constant, address, and design choice in zerobas-sub must appear here with
an independent **allowed** source, or be justified as **own design**. zerobas-sub
is a standalone 32 KB ROM built from `sub/*.asm` and pasmo alone; it never reads,
relocates, or diffs against any stock ROM, so the output firewall (0 C-BIOS-leak
bytes) is trivially clean. Nothing here is derived from any disk-ROM or MSX-BASIC
disassembly.

Allowed sources (same master list as [`../README.md`](../README.md)):
- **MSX2 TH** — MSX2 Technical Handbook (public English translation); documented
  *interfaces* only (entry conventions, work-area layouts) — never ROM code.
- **MSX Assembly Page** — MSX Assembly Page BIOS/sysvar reference (public web).

## Design decisions (see [`../docs/spec-basic-subrom.md`](../docs/spec-basic-subrom.md))

- **`CD` signature at $0000** — sub-ROM identification convention (cartridges use
  `AB`, sub-ROMs use `CD`). *Source:* MSX2 TH sub-ROM section. Our discovery scan
  (`init_ext_roms`, S2b) RDSLT-checks $0000/$0001 for `'C'`/`'D'`.
- **`S1` marker at $4000 (NOT `AB`)** — *own design.* Any non-`AB` value works; the
  point is that `try_init_slot`'s cartridge scan (which checks $4000 for `'A'`/`'B'`
  on every expanded secondary, including 3-2) must **not** pick the passive sub-ROM
  up as a bootable cartridge (spec D-7). `S1` = "sub-ROM page 1", chosen only for
  legibility in a hex dump.
- **Entry-table bases $0010 (page 0) / $4010 (page 1), `IX = base + 3*index`** —
  *own design*, following two allowed shapes: the `$4010` page-1 base mirrors the
  standard disk-ROM DSKIO offset (MSX2 TH disk-interface layout) so a page-1
  CALSLT looks exactly like the disk case; the `IX = target` dispatch matches the
  MSX2 EXTROM register contract (MSX2 TH) so a future real `$015F EXTROM` path is a
  drop-in. Append-only: a tenant's index never moves once assigned.
- **`SUB_PING` = $F105** — *own choice, free RAM.* A page-3 RAM cell in the
  repack-only free window (right after the float pack's last claim `PLF_RA2`
  $F103 and below zerobas-disk's `DRVA_DPB` $F195; see
  [`../basic/sysvars.inc`](../basic/sysvars.inc)). Used only by the S2a skeleton
  pings so the boot-gate probe can observe the round-trip; S2b's dispatch stub
  formalises the marshalling block that begins here.

## Own-design divergences from real MSX (spec §6)

- **(a) An MSX2-style sub-ROM on an MSX1-class machine.** Faithful in *mechanism*
  (Disk/FM/Kanji BASIC all extend the system from ROMs); a documented divergence
  in that a stock MSX1 has no sub-ROM at all.
- **(b) Core numeric/service code will live in the sub-ROM** (from the eviction
  session on) rather than the main ROM. Faithful in *mechanism*; a documented
  divergence in *placement* — real MSX kept e.g. SIN/COS in the main ROM. Accepted
  under the sub-ROM framing (spec §6 / decision §7 Q3).
