# D-DEFCORNER — a DEFtype item's tail ran as a statement, hidden by a row that agreed for the wrong reason

*2026-08-31. `sub/deftype.asm` (item-end check). Probe
`scratchpad/defcorner_probe.py`, 9 rows × 3 machines: **1 DIFF → 0**.
Sub-ROM only. Fourth verb group off
[review-tier-worklist.md](review-tier-worklist.md).*

## 1. The review flagged the shape; the obvious row could not see it

Reading `deftype_tenant`'s range-list parser: after an item, **any** non-comma
byte ended the list and handed the cursor back — so `DEFINT AB` filled A and
left the cursor on `B`, and `exec_stmt` re-dispatched the item's tail as a
statement. The obvious row agreed anyway:

| row | VG-8020 | CF-3300 | zerobas | |
|---|---|---|---|---|
| `d.two` `DEFINT AB` | ERR 2 | ERR 2 | ERR 2 | SAME — **for the wrong reason** |
| `d.tail` `DEFINT AC=7` | ERR 2 | ERR 2 | **7** | 🔴 the same mechanism, visible |

The references reject the malformed *item*; zerobas re-dispatched `B` alone,
which is *also* ERR 2 at the same line — two mechanisms agreeing by accident
([[a-case-that-agrees-can-agree-for-the-wrong-reason]]). The separating row
makes the tail **harmless and observable**: `C=7` runs (7, no error) under the
cursor-hand-back mechanism and cannot run under an item reject. It ran.

## 2. The rule, measured

An item may end only at `,`, `:` or EOL — anything glued to it rejects the
**statement**. All other corners agree outright: reversed range (`Z-A`), bare
`DEFINT`, `A-1`, `DEFINT 1` are ERR 2 on all three; `A-C` fills and `DEFSTR`
re-types (controls).

## 3. The fix

The item-end check accepts `,` / `:` / EOL and routes anything else to
`edt_fail` (ERR 2). `d.two`'s SAME is now produced by the right mechanism —
the item reject — rather than by the coincidence.

## 4. Worth keeping

**Write the wrong-reason hazard into the probe before running it.** This
probe's docstring named the coincidence and the separating row's design in
advance; the first run's 0/8 would otherwise have closed the review as a
no-finding with the defect alive under it.
