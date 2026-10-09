<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Concept pages

← [zerobas](../../README.md) · [Keyword pages](../keywords/README.md)

How MSX BASIC works beyond single keywords — the editor, numbers, memory,
files, tape, disk and MSX-DOS — and how zerobas compares with a real MSX on
each. Like the [keyword pages](../keywords/README.md), every example that can
run unattended was run on zerobas and on an emulated real machine (a Philips
VG-8020, or a National CF-3300 for disk) and printed the same on both, and each
page lists where zerobas still differs.

([How these pages are made and checked](../keywords/about.md))


## The language

| page | about |
|---|---|
| [Numbers](numbers.md) | integers, single and double precision |
| [Variables](variables.md) | names, types, arrays, and where they live |
| [Strings and string space](strings-and-string-space.md) | where string values live |
| [Program text](program-text.md) | how a typed line becomes a program line |
| [Errors](errors.md) | codes, messages and `ON ERROR` |

## The machine

| page | about |
|---|---|
| [The screen editor](screen-editor.md) | typing, fixing and re-entering lines |
| [Screen modes](screen-modes.md) | the four MSX1 displays |
| [Interrupts and traps](interrupts-and-traps.md) | what runs between statements |
| [The memory map](memory-map.md) | where BASIC keeps things in RAM |

## Storage

| page | about |
|---|---|
| [Files and devices](files-and-devices.md) | numbered channels to the disk, the tape, the screen and the printer |
| [The cassette](cassette.md) | files on tape, and how BASIC finds them |
| [Disk BASIC](disk.md) | files on a 720 KB floppy, one drive |
| [MSX-DOS](msx-dos.md) | booting DOS, the BDOS, and the way back to BASIC |

## Inside zerobas

| page | about |
|---|---|
| [ROM layout](rom-layout.md) | how zerobas is put together |
