<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CLRTXT` (sub-ROM $0119) — clear the text screen (interface unpublished)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

An entry at sub-ROM $0119 named CLRTXT by other open implementations. The MSX2 Technical Handbook's
sub-ROM listing does not list it: its existence on the references, its inputs and its behaviour are
all unknown until measured. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- Not published: the handbook's sub-ROM listing goes from CLSSUB ($0115) to DSPFNK ($011D)
  [P App. 1, SUB-ROM].
- In / out / registers / interrupts: [A].

**Behaviour.**
- Clears the text screen [A] (from the name only). Whether it differs from [CLS](CLS.md) in a text
  mode, and what it does in a graphic mode, [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

First establish that $0119 is an entry on each reference (a `JP` / `RET` pattern is not readable —
clean room — so call it from a safe state and observe). Recorded per case: as [CLS](CLS.md#open-not-measured).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| CT-EX | — | SCREEN 0, all three machines | an entry at all (behaves vs crashes / returns at once) | ? | ? | ? |
| CT-Z | Z set / clear | SCREEN 0, 1 | a Z gate like main-ROM CLS | ? | ? | ? |
| CT-0 | — | SCREEN 0 (40, 80), key line on / off, cursor mid-screen | = CLS vs clear without home / without key line / without LINTTB | ? | ? | ? |
| CT-1 | — | SCREEN 1, colour table garbage | colour table touched | ? | ? | ? |
| CT-GR | — | SCREEN 2, 5, 8 | does nothing vs clears vs switches to text | ? | ? | ? |
| CT-REG | registers distinct | SCREEN 0 | registers kept | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CLS](CLS.md); [DSPFNK](DSPFNK.md).

## Tests that cover it

none yet
