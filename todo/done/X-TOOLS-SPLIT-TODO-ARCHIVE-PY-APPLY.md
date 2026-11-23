- [x] 🔴 **`tools/split_todo_archive.py --apply` IS A ONE-SHOT TOOL THAT DOES NOT
      SAY SO, AND THE SECOND RUN DAMAGED TWO TRACKED FILES.** Found 2026-08-30
      while doing the routine second split; both were caught by hand, and
      **neither was caught by the tool's own checks**.
      🔴 **(1) IT CLOBBERS THE ARCHIVE.** It regenerates
      `docs/TODO-done.md` from `TODO.md` ALONE, so a second run rebuilds the
      archive out of only what is still in the pickup list: it **deleted 8857 of
      the 8903 lines** already there. Its `lossless` check passed while doing it,
      because that check reconstructs the **SOURCE** (`TODO.md`), not the
      destination. Recovered with `git checkout` + appending the new blocks by
      hand, insertions only, verified line-for-line against the pre-split file.
      ➡️ **Needs an APPEND mode**, and a losslessness check that includes the
      DESTINATION's prior content.
      🔴 **(2) THE CITATION REPOINTER CORRUPTS OVERLAPPING REWRITES — 19
      citations in 12 files.** It produced
      `TODO.md:10745 (T-6FE392)8 (T-529ABE)` from `TODO.md:15182 (T-529ABE)`: a  NOT-A-CITATION
      rewrite for one citation landed INSIDE another's line number, because the
      old-line → new-line map is applied as plain text substitution and
      `TODO.md:461` is a prefix of `TODO.md:4618`. Every damaged file was  NOT-A-CITATION
      reverted and repointed with `check_todo_citations.py --fix`, which resolves
      by **block id** and got 18 of 19 right; the 19th named a block that had
      moved to the archive, which `--fix` cannot do because it rewrites the LINE
      and not the FILE.
      ➡️ **Repoint by ID, or match the whole `file:line (T-xxxxxx)` token** —
      never by line-number substring. And **teach `--fix` to change the FILE**
      when a block's id resolves in the other document.
      ⚠️ **`todo-citation-check` DID catch (2) once the corruption existed** —
      it is the gate that found all 19 — but nothing catches (1), because no gate
      reads the archive's line count against its own history.
      🤖 AUTONOMOUS — both defects are reproducible from this commit's parent and
      settled by the tool's own `--verify` once it is extended.
