<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Keyword pages

← [zerobas](../../README.md)

One page per BASIC keyword, written for a person: what the keyword does, how
zerobas behaves, an example, where it differs from the reference machine, and
what we found out about it along the way. The rest of `docs/` is mostly the
working record those findings came from; these pages are the distilled result.

The reference is the Philips VG-8020 for BASIC and the National CF-3300 for
Disk BASIC; each page says which it was compared with.

## The rules for these pages

- **A keyword gets a page once it reaches level 3**: the happy path, a
  reasonable time and the common errors are all proven. Below that its
  behaviour is still moving. When a page's own checking finds a happy-path
  difference, the keyword drops below level 3 and its page stays, saying so
  in its status line: `READ`, `DATA` and `FILES` on 2026-10-09.
- **A page changes only when an error at a lower tier is found and fixed**, or
  when a ruling changes what the keyword should do. It is not a log.
- **No speed figures** until on-par speed is established for every keyword.
- **Every example is run on zerobas and on the reference**, and the page shows
  what both printed: [`scratchpad/kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)
  reads each page's `<!-- example: … -->` line and its `## Example` block, types
  the program on both machines and compares the screens. Six examples need
  hardware the check cannot drive (a cassette, a printer, `AUTO`'s line entry);
  those pages say so and name the gate that covers them instead.
- **Each page has the same sections:** status, summary, syntax, details,
  example, differences from the reference, what we found and how, where it
  lives, and the tests that cover it.

## The pages

### Words that start other statements

`ON`, `DEF`, `GET` and `PUT` never stand alone; each is the first word of
one or more statements. Their pages list those statements and link to where
each is described.

| word | starts | page |
|---|---|---|
| [`ON`](ON.md) | `ON n GOTO`, `ON n GOSUB`, `ON ERROR GOTO`, `ON KEY` / `STRIG` / `SPRITE` / `STOP` / `INTERVAL GOSUB` | the list, and `ON INTERVAL GOSUB` in full |
| [`DEF`](DEF.md) | `DEF FN`, `DEF USR` | the list |
| [`GET`](GET.md) | `GET #` | `GET #` in full |
| [`PUT`](PUT.md) | `PUT #`, `PUT SPRITE` | `PUT #` in full |

### Strings

| keyword | what it does |
|---|---|
| [`ASC`](ASC.md) | the character code of a string's first character |
| [`BIN$`](BIN$.md) | a number written in binary |
| [`CHR$`](CHR$.md) | the character with a given code |
| [`HEX$`](HEX$.md) | a number written in hexadecimal |
| [`INSTR`](INSTR.md) | find one string inside another |
| [`LEFT$`](LEFT$.md) | the first characters of a string |
| [`LEN`](LEN.md) | the length of a string |
| [`MID$`](MID$.md) | characters from the middle of a string, or overwrite them |
| [`OCT$`](OCT$.md) | a number written in octal |
| [`RIGHT$`](RIGHT$.md) | the last characters of a string |
| [`SPACE$`](SPACE$.md) | a string of spaces |
| [`STR$`](STR$.md) | a number as text |
| [`STRING$`](STRING$.md) | a character repeated a number of times |
| [`VAL`](VAL.md) | the number at the start of a string |

### Numbers and maths

| keyword | what it does |
|---|---|
| [`ABS`](ABS.md) | the absolute value of a number |
| [`ATN`](ATN.md) | the arctangent of a number |
| [`COS`](COS.md) | the cosine of an angle |
| [`EXP`](EXP.md) | e raised to a power |
| [`FIX`](FIX.md) | drop the fraction of a number |
| [`INT`](INT.md) | round a number down to a whole number |
| [`LOG`](LOG.md) | the natural logarithm of a number |
| [`RND`](RND.md) | a pseudo-random number |
| [`SGN`](SGN.md) | the sign of a number |
| [`SIN`](SIN.md) | the sine of an angle |
| [`SQR`](SQR.md) | the square root of a number |
| [`TAN`](TAN.md) | the tangent of an angle |

### Type conversion

| keyword | what it does |
|---|---|
| [`CDBL`](CDBL.md) | convert a number to double precision |
| [`CINT`](CINT.md) | convert a number to an integer |
| [`CSNG`](CSNG.md) | convert a number to single precision |
| [`CVD`](CVD.md) | read a double-precision number back from an 8-byte string |
| [`CVI`](CVI.md) | read an integer back from a 2-byte string |
| [`CVS`](CVS.md) | read a single-precision number back from a 4-byte string |
| [`MKD$`](MKD$.md) | pack a double-precision number into an 8-byte string |
| [`MKI$`](MKI$.md) | pack an integer into a 2-byte string |
| [`MKS$`](MKS$.md) | pack a single-precision number into a 4-byte string |

### Operators and assignment

| keyword | what it does |
|---|---|
| [`AND`](AND.md) | bitwise and logical "and" |
| [`EQV`](EQV.md) | bitwise equivalence |
| [`IMP`](IMP.md) | bitwise implication |
| [`MOD`](MOD.md) | the remainder of an integer division |
| [`NOT`](NOT.md) | bitwise and logical "not" |
| [`OR`](OR.md) | bitwise and logical "or" |
| [`XOR`](XOR.md) | bitwise exclusive "or" |
| [`LET`](LET.md) | give a variable a value |
| [`SWAP`](SWAP.md) | exchange the values of two variables |

### Program flow

| keyword | what it does |
|---|---|
| [`CONT`](CONT.md) | continue a stopped program |
| [`END`](END.md) | stop the program |
| [`FOR`](FOR.md) | start a counted loop |
| [`GOSUB`](GOSUB.md) | call a subroutine |
| [`GOTO`](GOTO.md) | jump to a line |
| [`IF`](IF.md) | run part of a line only when a condition holds |
| [`NEXT`](NEXT.md) | end of a `FOR` loop: step, test, go round |
| [`RETURN`](RETURN.md) | come back from a subroutine |
| [`RUN`](RUN.md) | start the program |
| [`STOP`](STOP.md) | pause the program with a `Break` message |

### Errors, tracing and types

| keyword | what it does |
|---|---|
| [`ERL`](ERL.md) | the line of the last error |
| [`ERR`](ERR.md) | the code of the last error |
| [`ERROR`](ERROR.md) | raise an error on purpose |
| [`RESUME`](RESUME.md) | leave an error handler and carry on |
| [`TROFF`](TROFF.md) | stop tracing |
| [`TRON`](TRON.md) | trace a running program, line by line |
| [`REM`](REM.md) | a comment |
| [`DEFDBL`](DEFDBL.md) | make variables double precision by their first letter |
| [`DEFINT`](DEFINT.md) | make variables integers by their first letter |
| [`DEFSNG`](DEFSNG.md) | make variables single precision by their first letter |
| [`DEFSTR`](DEFSTR.md) | make variables strings by their first letter |

### Editing, data and arrays

| keyword | what it does |
|---|---|
| [`AUTO`](AUTO.md) | number the lines for you while you type |
| [`DELETE`](DELETE.md) | remove program lines |
| [`LIST`](LIST.md) | show the program on the screen |
| [`LLIST`](LLIST.md) | print the program on the printer |
| [`NEW`](NEW.md) | erase the program and its variables |
| [`RENUM`](RENUM.md) | renumber the program |
| [`DATA`](DATA.md) | values stored in the program for `READ` |
| [`READ`](READ.md) | take the next values from `DATA` |
| [`RESTORE`](RESTORE.md) | choose where `READ` starts |
| [`CLEAR`](CLEAR.md) | reset the variables, and size the string space |
| [`DIM`](DIM.md) | declare an array |
| [`ERASE`](ERASE.md) | remove an array |

### Memory, ports and time

| keyword | what it does |
|---|---|
| [`BASE`](BASE.md) | where each screen mode keeps its tables in video memory |
| [`FN`](FN.md) | one-line functions of your own (`DEF FN`) |
| [`FRE`](FRE.md) | how much memory is free |
| [`INP`](INP.md) | read a byte from an I/O port |
| [`OUT`](OUT.md) | write a byte to an I/O port |
| [`PEEK`](PEEK.md) | read one byte of memory |
| [`POKE`](POKE.md) | write one byte to memory |
| [`TIME`](TIME.md) | the frame counter, readable and settable |
| [`USR`](USR.md) | call a machine-code routine (`DEF USR`) |
| [`VARPTR`](VARPTR.md) | the memory address of a variable or a file channel |
| [`WAIT`](WAIT.md) | pause until an I/O port shows a bit pattern |

### Text screen and printer

| keyword | what it does |
|---|---|
| [`CLS`](CLS.md) | clear the screen |
| [`COLOR`](COLOR.md) | set the foreground, background and border colours |
| [`CSRLIN`](CSRLIN.md) | the row the cursor is on |
| [`KEY`](KEY.md) | function-key texts and the function-key line |
| [`LOCATE`](LOCATE.md) | move the text cursor |
| [`LPOS`](LPOS.md) | the printer head's column |
| [`LPRINT`](LPRINT.md) | print to the printer |
| [`POS`](POS.md) | the column the cursor is in |
| [`PRINT`](PRINT.md) | write text and numbers to the screen |
| [`SCREEN`](SCREEN.md) | choose the display mode |
| [`WIDTH`](WIDTH.md) | set the number of text columns |

### Graphics and video

| keyword | what it does |
|---|---|
| [`CIRCLE`](CIRCLE.md) | draw a circle, an ellipse or an arc |
| [`DRAW`](DRAW.md) | draw with a string of pen commands |
| [`LINE`](LINE.md) | draw a line, a box or a filled box |
| [`PAINT`](PAINT.md) | fill an area with a colour |
| [`POINT`](POINT.md) | the colour of one pixel |
| [`PRESET`](PRESET.md) | erase one pixel on the graphics screen |
| [`PSET`](PSET.md) | set one pixel on the graphics screen |
| [`SPRITE`](SPRITE.md) | sprite shapes, and the collision switch |
| [`VDP`](VDP.md) | read or write a video chip register |
| [`VPEEK`](VPEEK.md) | read one byte of video memory |
| [`VPOKE`](VPOKE.md) | write one byte of video memory |

### Sound and input devices

| keyword | what it does |
|---|---|
| [`BEEP`](BEEP.md) | sound one short beep |
| [`PLAY`](PLAY.md) | play music in the background |
| [`SOUND`](SOUND.md) | write one register of the sound chip |
| [`INKEY$`](INKEY$.md) | the key waiting in the keyboard buffer, if any |
| [`INPUT`](INPUT.md) | read a typed line into variables |
| [`PAD`](PAD.md) | read a touch pad |
| [`PDL`](PDL.md) | the position of a paddle |
| [`STICK`](STICK.md) | the direction of the cursor keys or a joystick |
| [`STRIG`](STRIG.md) | is the space bar or a fire button pressed? |
| [`MOTOR`](MOTOR.md) | switch the cassette motor on or off |

### Programs and files

| keyword | what it does |
|---|---|
| [`BLOAD`](BLOAD.md) | load a binary file into memory |
| [`BSAVE`](BSAVE.md) | save a block of memory to a file |
| [`CLOAD`](CLOAD.md) | load a BASIC program from cassette |
| [`CSAVE`](CSAVE.md) | save the program to cassette |
| [`LOAD`](LOAD.md) | replace the program with one from a file |
| [`SAVE`](SAVE.md) | write the program to a file |
| [`MERGE`](MERGE.md) | add the lines of a text file to the program |
| [`OPEN`](OPEN.md) | open a file or device on a numbered channel |
| [`CLOSE`](CLOSE.md) | close one channel, several, or all |
| [`EOF`](EOF.md) | has a file been read to its end? |

### Disk

| keyword | what it does |
|---|---|
| [`COPY`](COPY.md) | copy a file on the disk |
| [`DSKF`](DSKF.md) | free space on the disk |
| [`DSKI$`](DSKI$.md) | read a raw disk sector |
| [`DSKO$`](DSKO$.md) | write a raw disk sector |
| [`FILES`](FILES.md) | list the files on the disk |
| [`LFILES`](LFILES.md) | list the files on the disk to the printer |
| [`KILL`](KILL.md) | delete a file from the disk |
| [`NAME`](NAME.md) | rename a file on the disk |
| [`LOC`](LOC.md) | where a file channel is |
| [`LOF`](LOF.md) | the length of an open file |
| [`FIELD`](FIELD.md) | name the parts of a random-file record |
| [`LSET`](LSET.md) | fill a string in place, left-justified |
| [`RSET`](RSET.md) | fill a string in place, right-justified |
| [`IPL`](IPL.md) | a reserved word that is always refused |
| [`CMD`](CMD.md) | a reserved word that is always refused |
| [`SET`](SET.md) | a reserved word that is always refused |

### Joining words

These words only appear inside other statements; they are described on the
page of the statement they belong to.

| word | belongs to |
|---|---|
| `THEN`, `ELSE` | [`IF`](IF.md) |
| `TO`, `STEP` | [`FOR`](FOR.md) |
| `USING`, `SPC(`, `TAB(` | [`PRINT`](PRINT.md) |
| `AS` | [`OPEN`](OPEN.md), [`FIELD`](FIELD.md), [`NAME`](NAME.md) |
| `INTERVAL` | [`ON`](ON.md) |
| `OFF` | [`KEY`](KEY.md), [`STRIG`](STRIG.md), [`SPRITE`](SPRITE.md), [`STOP`](STOP.md), [`ON`](ON.md) (`INTERVAL OFF`) |
| `MAXFILES` | [`OPEN`](OPEN.md) |
| `LINE INPUT`, `INPUT$` | [`INPUT`](INPUT.md); `LINE INPUT #` on [`OPEN`](OPEN.md) |
| `SPRITE$` | [`SPRITE`](SPRITE.md) |
