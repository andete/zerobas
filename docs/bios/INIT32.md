<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `INIT32` ($006F) — set up the 32-column text screen (SCREEN 1)

> **Spec:** DRAFT 1 (2026-11-17), not yet reviewed. Stated on [INITXT's page](INITXT.md), together
> with INITXT: the two calls differ only in values.

## Summary

`INIT32` switches the screen to 32-column text (SCREEN 1): the VDP from T32NAM .. T32PAT, the width
from LINL32, the colour table filled from FORCLR / BAKCLR, the border from BDRCLR, the screen cleared,
the cursor home, and the function-key line when it is on. The rules are on
[INITXT's page](INITXT.md), sections "2. INIT32" and "3. Both".

## Differences from the reference

As INITXT's (its page's Differences): **D-KEYLINESHIFT**, **D-LINTTBVAL**, and the ruled font.
