- [ ] 🔧 **D-DEADSEED — `check_dead_code` STAYED GREEN WITH `fat_io_append` UNCALLED (found
      2026-10-06 by S10.B increment 2; NOT TRACED)**
      🎚️ APPARATUS — a gate's blind spot, not a keyword defect.
      📏 After `oo_append` stopped calling it, main's `fat_io_append` (89 B of
      page 1, with `fia_walk`/`fia_walked`/`fia_empty`) had no caller anywhere
      in code -- grep found only its own label -- yet `make basic-reloc`'s
      sweep read `main: … -> 0 dead`. Not prose: `external_names` reads the
      code column only, and the disk-side comment that named it was reworded
      first with no change. It was deleted by hand.
      ➡️ **TRACE IT:** restore the block on a scratch build and ask the sweep
      which seed or edge reaches it (it has no `--why`; add one). A seed that
      keeps one dead routine alive keeps others.
      🤖 **AUTONOMOUS** — the sweep's own data settles it.
