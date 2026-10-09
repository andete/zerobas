# `COPY "src" TO "dst"` — the last of the eight (D-COPY)

> ⚠️ **Historical (2026-09-11).** For how `COPY` behaves today, read
> [keywords/COPY.md](keywords/COPY.md). Since this page was written, wildcards
> gained their single-match and no-match behaviour (D-COPYWILD), open files
> are refused with 64, and the body moved from sub.rom's `tnt_copy` into
> `disk.rom` (D-COPYLOCAL).

Characterised 2026-09-07 (D-COPYVERB, `scratchpad/copyverb_probe.py`: works;
`ERR 53` missing source; `ERR 5` self-copy; `ERR 5` no `TO`) and completed
2026-09-11 on the CF-3300:

| row | program | face |
|---|---|---|
| `c.plain` | `COPY"PROG.BAS"TO"NEW.BAS"`, then `LOF` of NEW.BAS | 16 (= PROG.BAS) |
| `c.exist` | copy PROG.BAS to NEW.BAS, then HI.TXT to NEW.BAS | 26 (= HI.TXT: **overwritten**) |
| `c.big` | `COPY"TEST.BIN"TO"T2.BIN"` | 2048 |
| `c.wild` | `COPY"*.BAS"TO"Z.BAS"` | `ERR 5` |
| `c.spc` | `COPY "PROG.BAS" TO "N2.BAS"` (blanks) | 16 |
| `c.var` | `COPY A$ TO B$` | 16 |

Crunch (VG-8020's own program text): `COPY` = **$D6**, and `TO` inside the
line is **TO_TOKEN $D9** — `COPY"A.B"TO"C.D"` is `D6 22 41 2E 42 22 D9 22 43
2E 44 22`. Diskless: the class of the eight — refused on sight (`ERR 5`); the
nodisk gate's `h.copy` row measures it against the VG-8020.

## Design

* `kwtable` row `COPY` (4 B + 3), `stmt_table` entry, hook `H_COPY` = $FE08
  claimed by `hk_present`; `ex_copy` in the low region beside `DSKO$`.
* Parse: gate → `fname_fcb` (= `fname_expr` + `pdfcb_resume`, now a helper
  shared with `KILL`/`NAME`) → dirverb op 6 stashes the 8.3 name into
  `COPY_SRC` (`DISK_FCB_NAME` is the only 8.3 buffer) → `TO_TOKEN` or `ERR 5`
  (the measured face for a missing clause) → `fname_fcb` for the destination
  → dirverb op 7.
* Body (`tnt_copy`, sub page 1): mount; self-copy / wildcard (`?` after
  `pdfcb`'s `*` expansion) → STATUS 3 (`ERR 5`); `fat_find` the source FIRST —
  it records the entry's location in `FWR_DIRSEC`/`FWR_DIROFF`, which the
  destination's create must own afterwards — stash first cluster + size
  (`COPY_CLUS`, `COPY_LEFT`; the destination's delete/create go through
  `fat_find` too and clobber `FAT_FIRSTCLUS`/`FAT_FILESIZE`); `fat_delete`
  an old destination (the reference overwrites); `fat_dir_create` + the
  write-cursor reset `fat_io_create` does; restore the first cluster and
  `fat_open`; per sector `fat_read_file_sector` → `FSECTOR_BUF`, `n =
  min(512, left)`, `FWR_BUFLEN = n`, `FWR_BYTES += n`, `fat_flush_data_sector`;
  then `fat_dir_update`. The read iterator (`FAT_CURCLUS`/`FAT_CLUSSEC`) and
  the write cursor (`FWR_*`) are disjoint cells; the one shared buffer is the
  point.
* RAM: 17 B at `$E080..$E090` from the band D-FORVAR freed (claim rewritten).
* Gate: `make copy-acceptance` — every row on a private image, and the copied
  file's BYTES read back by a host-side FAT12 reader and compared with the
  source's (a verb that made the entry and wrote nothing cannot pass).
