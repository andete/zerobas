"""D-KWT6 S2 — ENUMERATE the reference's error set per keyword form (T6's denominator).

Joost's T6 ruling (2026-09-27): a keyword proves T6 when, for each documented
form, it has one row per DISTINCT error the reference raises for that form. This
probe measures that set on the VG-8020 by applying a FIXED FAULT BATTERY to each
form's argument and trapping what comes back:

    10 ON ERROR GOTO 90
    20 <the case>
    30 PRINT"[OK]":END
    90 PRINT"[";ERR;ERL;"]":END

`ERR`/`ERL` are the reference's own BASIC variables -- the code AND the line,
read directly, no message table to go stale. A case that raises nothing prints
`[OK]` and adds nothing to the set.

THE BATTERY IS THE BOUND, and it is stated here rather than implied: per argument
of a numeric function -- wrong type (a string), missing, one extra argument, and
the range edges below; per string argument -- wrong type (a number), missing,
extra, empty. A code no case elicits is not in the set; widening the battery is
how the set grows, and the output says which case produced each code so the T6
rows can be written from it.

Clean room: typed BASIC and the screen. Fresh boot per case (one error must not
leave state for the next).  `--zb` runs the same cases on zerobas for comparison.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"

NUM = ['"A"', "", "1,2"]            # type, missing, extra -- every numeric arg
STR = ["5", "", '"A","B"', '""']    # type, missing, extra, empty -- every string arg

# keyword -> (form, printable expression template with {a}, extra argument cases)
BATCH = {
    "ABS":  ("magnitude",    "ABS({a})",  NUM + ["-1E38"]),
    "SGN":  ("sign",         "SGN({a})",  NUM + ["-1E38"]),
    "INT":  ("floor",        "INT({a})",  NUM + ["-1E38"]),
    "SQR":  ("square-root",  "SQR({a})",  NUM + ["-1", "0"]),
    "LOG":  ("logarithm",    "LOG({a})",  NUM + ["0", "-1"]),
    # 🔴 EXP(99) was the first cut and read OK on both: e^99 is ~1E43, inside
    # MSX's ~1E63 range -- my arithmetic, not the machine. 150 is past it.
    "EXP":  ("exponential",  "EXP({a})",  NUM + ["99", "-99", "150"]),
    "ASC":  ("code-of",      "ASC({a})",  STR),
    "CHR$": ("code-to-char", "CHR$({a})", NUM + ["256", "-1", "70000"]),
    "LEN":  ("length",       "LEN({a})",  STR),
    "PEEK": ("address-read", "PEEK({a})", NUM + ["65536", "-32769", "70000"]),
}


# --- BATCH 2 (2026-09-27): MULTI-ARGUMENT functions and STATEMENTS -------------
# Each ARGUMENT gets its own faults: wrong type (N gets "A", S gets 5) and the
# range edges listed for it; then the call MISSING its last argument, with NO
# arguments, and with one EXTRA argument. A statement (stmt=True) is typed bare.
# keyword -> (form, stmt?, [(kind, valid, [edges])])
N, S = "N", "S"
BATCH2 = {
    "LEFT$":   ("prefix",          False, [(S, '"AB"', []), (N, "1", ["-1", "256", "70000"])]),
    "RIGHT$":  ("suffix",          False, [(S, '"AB"', []), (N, "1", ["-1", "256", "70000"])]),
    "STRING$": ("repeat",          False, [(N, "2", ["-1", "256"]),
                                           ("X", '"A"', ['""', "256", "-1"])]),
    "HEX$":    ("to-hex",          False, [(N, "1", ["70000", "-70000"])]),
    "OCT$":    ("to-octal",        False, [(N, "1", ["70000", "-70000"])]),
    "BIN$":    ("to-binary",       False, [(N, "1", ["70000", "-70000"])]),
    "SPACE$":  ("pad",             False, [(N, "1", ["-1", "256"])]),
    "MKI$":    ("int-to-string",   False, [(N, "1", ["32768", "-32769"])]),
    "CVI":     ("string-to-int",   False, [(S, '"AB"', ['""', '"A"'])]),
    "STR$":    ("number-to-string", False, [(N, "1", [])]),
    "CINT":    ("to-integer",      False, [(N, "1", ["32768", "-32769"])]),
    "FIX":     ("truncate",        False, [(N, "1", ["-1E38"])]),
    "CSNG":    ("to-single",       False, [(N, "1", ["1E38"])]),
    "CDBL":    ("to-double",       False, [(N, "1", ["1E38"])]),
    "SIN":     ("sine",            False, [(N, "1", ["1E38"])]),
    "COS":     ("cosine",          False, [(N, "1", ["1E38"])]),
    "TAN":     ("tangent",         False, [(N, "1", ["1E38"])]),
    "ATN":     ("arctangent",      False, [(N, "1", ["1E38"])]),
    "VPEEK":   ("address-read",    False, [(N, "1", ["16384", "-1", "70000"])]),
    # &H9000, not a work-area address: the `extra` case pokes BEFORE its Syntax
    # error, and $E800 is zerobas's private workspace. $9000 is free program/
    # variable space on both machines at this program size.
    "POKE":    ("address-value",   True,  [(N, "&H9000", ["65536", "-32769"]),
                                           (N, "1", ["256", "-1"])]),
    "VPOKE":   ("address-value",   True,  [(N, "1", ["16384", "-1", "70000"]),
                                           (N, "1", ["256", "-1"])]),
    "SOUND":   ("register-value",  True,  [(N, "8", ["14", "-1", "256"]),
                                           (N, "0", ["256", "-1"])]),
}


# --- BATCH 3 (2026-09-27): DISK BASIC functions -- `--disk` runs the CF-3300
# against zerobas's DISK build, the pairing kwsweep's NEEDS-DISK: rows use. Batch
# 2 showed the diskless VG-8020 is the wrong oracle here (MKI$("A") read 5).
BATCH3 = {
    "MKI$": ("int-to-string",    False, [(N, "1", ["32768", "-32769"])]),
    "CVI":  ("string-to-int",    False, [(S, '"AB"', ['""', '"A"'])]),
    "MKS$": ("single-to-string", False, [(N, "1", [])]),
    "CVS":  ("string-to-single", False, [(S, '"ABCD"', ['""', '"ABC"'])]),
    "MKD$": ("double-to-string", False, [(N, "1", [])]),
    "CVD":  ("string-to-double", False, [(S, '"ABCDEFGH"', ['""', '"ABCDEFG"'])]),
    "DSKF": ("free-space",       False, [(N, "0", ["9", "-1", "256"])]),
}


# --- BATCH 4 (2026-09-27): STATEMENTS and MULTI-FORM keywords ------------------
# Their errors are SCENARIOS (NEXT without FOR, RETURN without GOSUB, Out of DATA),
# not argument faults, so each (keyword, form) lists hand-written ONE-LINE cases:
# set-up goes on the same line with colons so ERL stays the line under test.
# RETURN's line form needs a live GOSUB to reach its own error (8), and gets one
# by recursing into its own line: `IF X=0 THEN X=1:GOSUB 20 ELSE RETURN 99`.
# VAL and FRE are NOT here: their "forms" are argument CONTENT/type, which no
# syntax fault can tell apart.
BATCH4 = {
    "INSTR": [
        ("search", ['PRINT INSTR("AB",5)', 'PRINT INSTR("AB")', "PRINT INSTR()",
                    'PRINT INSTR("AB","B","C")']),
        ("search-from", ['PRINT INSTR(0,"AB","B")', 'PRINT INSTR(256,"AB","B")',
                         'PRINT INSTR(70000,"AB","B")', 'PRINT INSTR(1,5,"B")',
                         'PRINT INSTR(1,"AB",5)', 'PRINT INSTR(1,"AB","B","C")',
                         'PRINT INSTR(1,"AB")'])],
    "MID$": [
        ("substring-3arg", ["PRINT MID$(5,1,1)", 'PRINT MID$("AB",0,1)',
                            'PRINT MID$("AB",256,1)', 'PRINT MID$("AB",1,-1)',
                            'PRINT MID$("AB",1,256)', 'PRINT MID$("AB","A",1)',
                            'PRINT MID$("AB",1,"A")', 'PRINT MID$("AB",1,1,1)',
                            'PRINT MID$("AB",70000,1)']),
        ("substring-to-end", ["PRINT MID$(5,1)", 'PRINT MID$("AB",0)',
                              'PRINT MID$("AB")', 'PRINT MID$("AB","A")', "PRINT MID$()"]),
        ("assign", ['A$="AB":MID$(A$,0)="X"', 'A$="AB":MID$(A$,1)=5',
                    'A$="AB":MID$(A$,3)="X"', 'A$="AB":MID$(A$,1,-1)="X"',
                    'A$="AB":MID$(A$,1,1)', 'MID$(5,1)="X"', 'A$="AB":MID$(A$)="X"',
                    'A$="AB":MID$(A$,256)="X"'])],
    "NEXT": [
        ("bare", ["NEXT", "FOR I=1 TO 2:NEXT:NEXT"]),
        ("named", ["NEXT I", "FOR I=1 TO 2:NEXT J", "FOR I=1 TO 2:NEXT A$",
                   "FOR I=1 TO 2:NEXT 5"]),
        ("comma-list", ["FOR I=1 TO 2:FOR J=1 TO 2:NEXT J,K", "NEXT I,J",
                        "FOR I=1 TO 2:FOR J=1 TO 2:NEXT J,"])],
    "RETURN": [
        ("bare", ["RETURN"]),
        ("line", ["RETURN 99", "IF X=0 THEN X=1:GOSUB 20 ELSE RETURN 99",
                  'IF X=0 THEN X=1:GOSUB 20 ELSE RETURN "A"'])],
    "RESTORE": [
        ("bare", ["RESTORE,", "RESTORE 1,2"]),
        ("line", ["RESTORE 99", 'RESTORE "A"', "RESTORE -1", "RESTORE 70000"])],
    "GOTO": [("jump", ["GOTO 99", "GOTO", 'GOTO "A"', "GOTO -1", "GOTO 70000"])],
    "READ": [("read-data", ["READ A", "READ A:DATA X", "READ 5", "READ",
                            "READ A:DATA 1E99"])],
    "SWAP": [("exchange", ["SWAP A,B$", "SWAP A", "SWAP", "SWAP A,5"])],
    "ERASE": [("free-array", ["ERASE A", "ERASE", "ERASE 5", "DIM A(2):ERASE A,A"])],
    "DIM": [
        ("one-dimensional", ["DIM A(2):DIM A(2)", "DIM A(-1)", 'DIM A("X")',
                             "DIM A(70000)", "DIM A(10000)", "DIM 5"]),
        ("multi-dimensional", ["DIM B(2,2):DIM B(2,2)", "DIM B(-1,2)", 'DIM B(2,"X")',
                               "DIM B(200,200)"])],
}


# --- BATCH 5 (2026-09-27): one-form OPERATORS, bare statements and readers ------
# OUT's `extra` case writes its port BEFORE the Syntax error, so it uses &H2F, an
# unused port. ERROR's valid form raises its own argument, so only MALFORMED
# forms are faulted. REM is absent: a comment has no errors, and a zero
# denominator proves nothing.
def _op(kw):
    return [f'PRINT 1 {kw} "A"', f"PRINT 1 {kw}", f"PRINT 70000 {kw} 1",
            f"PRINT 1 {kw} 70000"]


BATCH5 = {
    "AND": [("bitwise-and", _op("AND"))],
    "OR": [("bitwise-or", _op("OR"))],
    "XOR": [("bitwise-xor", _op("XOR"))],
    "EQV": [("equivalence", _op("EQV"))],
    "IMP": [("implication", _op("IMP"))],
    "NOT": [("bitwise-not", ['PRINT NOT "A"', "PRINT NOT", "PRINT NOT 70000"])],
    "MOD": [("modulo", ["PRINT 5 MOD 0", 'PRINT 5 MOD "A"', "PRINT 5 MOD",
                        "PRINT 70000 MOD 2"])],
    "BEEP": [("no-argument", ["BEEP 1", "BEEP,"])],
    "CLS": [("no-argument", ["CLS 1", "CLS,"])],
    "TRON": [("toggle", ["TRON 1", "TRON,"])],
    "TROFF": [("toggle", ["TROFF 1", "TROFF,"])],
    "END": [("terminate", ["END 1", "END,"])],
    "CSRLIN": [("row-read", ["PRINT CSRLIN(1)", "A=CSRLIN 1"])],
    "ERL": [("error-line", ["PRINT ERL(1)", "A=ERL 1"])],
    "ERR": [("error-code", ["PRINT ERR(1)", "A=ERR 1"])],
    "ERROR": [("raise", ["ERROR 0", "ERROR 256", 'ERROR "A"', "ERROR", "ERROR -1",
                         "ERROR 70000", "ERROR 1,1"])],
    "GOSUB": [("call", ["GOSUB 99", "GOSUB", 'GOSUB "A"', "GOSUB -1", "GOSUB 70000"])],
    "INKEY$": [("poll-key", ["PRINT INKEY$(1)", "A=INKEY$"])],
    "INP": [("port-read", ['PRINT INP("A")', "PRINT INP()", "PRINT INP(256)",
                           "PRINT INP(-1)", "PRINT INP(1,2)"])],
    "LET": [("assign", ['LET A="X"', "LET A$=5", "LET 5=1", "LET", "LET A"])],
    "OUT": [("port-value", ['OUT "A",1', 'OUT &H2F,"A"', "OUT 256,1", "OUT &H2F,256",
                            "OUT &H2F", "OUT", "OUT &H2F,1,1"])],
    "POINT": [("pixel-read", ['PRINT POINT("A",1)', "PRINT POINT(1)", "PRINT POINT()",
                              "PRINT POINT(1,1,1)"])],
    "POS": [("column-read", ['PRINT POS("A")', "PRINT POS()", "PRINT POS(1,2)"])],
    "LPOS": [("column-read", ['PRINT LPOS("A")', "PRINT LPOS()", "PRINT LPOS(1,2)"])],
    "RND": [("reseeded-draw", ['PRINT RND("A")', "PRINT RND()", "PRINT RND(1,2)"])],
}


# --- BATCH 6 (2026-09-27): multi-form STATEMENTS -------------------------------
# Only FAULTS are typed: a valid SCREEN would switch mode under the capture, a
# valid CLEAR resets the handler, a valid WAIT blocks forever (WAIT is not here;
# nor WIDTH, whose mode1 form needs a SCREEN 1 reading). RESUME's forms all read
# "RESUME without error" (22) outside a handler -- plus their syntax faults.
def _deft(k):
    return [("single-letter", [f"{k} 5", f"{k}", f"{k} A,", f'{k} "A"']),
            ("letter-range", [f"{k} A-", f"{k} A-5", f"{k} Z-A", f"{k} A-B-C"])]


BATCH6 = {
    "FOR": [
        ("ascending", ['FOR I="A" TO 2:NEXT', 'FOR I=1 TO "A":NEXT', "FOR I=1:NEXT",
                       "FOR 5=1 TO 2:NEXT", "FOR I=1 TO:NEXT", "FOR A$=1 TO 2:NEXT"]),
        ("step", ['FOR I=1 TO 2 STEP "A":NEXT', "FOR I=1 TO 2 STEP:NEXT",
                  "FOR I=1 TO 2 STEP 1,2:NEXT"]),
        ("negative-step", ['FOR I=2 TO 1 STEP -"A":NEXT', "FOR I=2 TO 1 STEP -:NEXT",
                           "FOR I=2 TO 1 STEP -1 -:NEXT"])],
    "IF": [
        ("then", ['IF "A" THEN 30', "IF THEN 30", "IF 1 THEN 99", "IF 1 THEN"]),
        ("else", ["IF 0 THEN 30 ELSE 99", 'IF "A" THEN 30 ELSE 30', "IF 0 THEN 30 ELSE"]),
        ("goto", ["IF 1 GOTO 99", "IF 1 GOTO", 'IF 1 GOTO "A"', 'IF "A" GOTO 30'])],
    "CLEAR": [
        ("bare", ["CLEAR 1,2,3", "CLEAR,"]),
        ("string-space", ["CLEAR -1", "CLEAR 70000", 'CLEAR "A"', "CLEAR 30000"]),
        ("himem", ['CLEAR 200,"A"', "CLEAR 200,&H7000", "CLEAR 200,-1", "CLEAR 200,"])],
    "COLOR": [
        ("foreground", ["COLOR 16", 'COLOR "A"', "COLOR -1"]),
        ("background", ["COLOR ,16", 'COLOR ,"A"', "COLOR ,-1"]),
        ("border", ["COLOR ,,16", 'COLOR ,,"A"', "COLOR 1,1,1,1"])],
    "SCREEN": [
        ("mode", ["SCREEN 4", 'SCREEN "A"', "SCREEN -1"]),
        ("sprite-size", ["SCREEN ,4", 'SCREEN ,"A"', "SCREEN ,-1"]),
        ("key-click", ['SCREEN ,,"A"', "SCREEN ,,256", "SCREEN ,,,,,,"])],
    "LOCATE": [
        ("column", ["LOCATE 40", 'LOCATE "A"', "LOCATE -1"]),
        ("row", ["LOCATE 1,24", 'LOCATE 1,"A"', "LOCATE 1,-1"]),
        ("omitted-column", ["LOCATE ,24", 'LOCATE ,"A"']),
        ("cursor-switch", ["LOCATE 1,1,2", 'LOCATE 1,1,"A"', "LOCATE 1,1,1,1"])],
    "TIME": [
        ("read", ["A$=TIME", "PRINT TIME(1)"]),
        ("write", ['TIME="A"', "TIME=70000", "TIME=", "TIME=-1"])],
    "DEFINT": _deft("DEFINT"), "DEFSNG": _deft("DEFSNG"),
    "DEFDBL": _deft("DEFDBL"), "DEFSTR": _deft("DEFSTR"),
    "RESUME": [
        ("next", ["RESUME NEXT", "RESUME NEXT,1"]),
        ("bare", ["RESUME", "RESUME,"]),
        ("line", ["RESUME 30", 'RESUME "A"', "RESUME 30,1"])],
}


def _call(kw, stmt, args):
    a = ",".join(args)
    return f"{kw} {a}".rstrip() if stmt else f"PRINT {kw}({a})"


# --- BATCH 7 (2026-09-27): graphics statements, device functions, ON/KEY/FN ---
# A graphics case sets SCREEN 2 (or 3) ON ITS OWN LINE; program() then puts
# `SCREEN 0:` in front of the handler's PRINTs, because the reading is text and
# a PRINT in a bitmap mode draws nowhere the reader looks. Only cases whose
# statement names SCREEN get that shape, so batches 1-6 are unchanged.
G = "SCREEN 2:"
BATCH7 = {
    "PSET": [
        ("colour-explicit", [G + "PSET(10,10),16", G + 'PSET(10,10),"A"', G + "PSET(10,10),-1",
                             G + 'PSET("A",10)', "PSET(10,10),1", G + "PSET(10)", G + "PSET 10,10"]),
        ("colour-default", [G + "PSET(10,10", G + "PSET(10,10),", G + "PSET(,10)"]),
        ("step-relative", [G + 'PSET STEP("A",1)', G + "PSET STEP 1,1", G + "PSET STEP(1,1),16"]),
        ("mode-screen3", ["SCREEN 3:PSET(10,10),16", 'SCREEN 3:PSET(10,10),"A"',
                          "SCREEN 3:PSET(99999,1)"])],
    "PRESET": [
        ("colour-default", [G + "PRESET(10,10", G + "PRESET(10)", G + 'PRESET("A",10)',
                            "PRESET(10,10)", G + "PRESET 10,10"]),
        ("colour-explicit", [G + "PRESET(10,10),16", G + 'PRESET(10,10),"A"', G + "PRESET(10,10),-1"]),
        ("step-relative", [G + 'PRESET STEP("A",1)', G + "PRESET STEP 1,1"]),
        ("mode-screen3", ["SCREEN 3:PRESET(10,10),16", 'SCREEN 3:PRESET(10,10),"A"'])],
    "LINE": [
        ("segment", [G + 'LINE(0,0)-("A",1)', G + "LINE(0,0)-", G + "LINE(0,0)(1,1)",
                     G + "LINE(0,0)-(1,1),16", "LINE(0,0)-(1,1)", G + "LINE(0,0)-(1)"]),
        ("box", [G + "LINE(0,0)-(9,9),1,C", G + "LINE(0,0)-(9,9),16,B", G + "LINE(0,0)-(9,9),1,B,1"]),
        ("filled-box", [G + "LINE(0,0)-(9,9),1,BX", G + "LINE(0,0)-(9,9),16,BF"]),
        ("step-relative", [G + 'LINE STEP("A",1)-(9,9)', G + "LINE STEP(1,1)-STEP",
                           G + "LINE STEP 1,1-(9,9)"]),
        ("omitted-start", [G + 'LINE -("A",1)', G + "LINE -(9)", G + "LINE -"]),
        ("colour-default", [G + "LINE(0,0)-(9,9),", G + "LINE(0,0)-(9,9),,", G + 'LINE(0,0)-(9,9),"A"'])],
    "CIRCLE": [
        ("centre-radius", [G + "CIRCLE(99,99)", G + 'CIRCLE(99,99),"A"', G + "CIRCLE(99,99),-5",
                           G + "CIRCLE(99,99),5,16", "CIRCLE(99,99),5", G + "CIRCLE(99),5"]),
        ("arc", [G + "CIRCLE(99,99),5,1,7", G + 'CIRCLE(99,99),5,1,"A"', G + "CIRCLE(99,99),5,1,1,7"]),
        ("step-relative", [G + 'CIRCLE STEP("A",1),5', G + "CIRCLE STEP 1,1,5"]),
        ("aspect", [G + 'CIRCLE(99,99),5,1,,,"A"', G + "CIRCLE(99,99),5,1,,,-1",
                    G + "CIRCLE(99,99),5,1,,,1,1"]),
        ("colour-default", [G + "CIRCLE(99,99),5,", G + "CIRCLE(99,99),5,,"])],
    "PAINT": [
        ("flood", [G + 'PAINT("A",1)', G + "PAINT(1)", "PAINT(1,1)", G + "PAINT 1,1"]),
        ("fill-colour", [G + "PAINT(1,1),16", G + 'PAINT(1,1),"A"', G + "PAINT(1,1),-1"]),
        ("border-colour", [G + "PAINT(1,1),1,16", G + 'PAINT(1,1),1,"A"', G + "PAINT(1,1),1,1,1"])],
    "DRAW": [
        ("movement", [G + 'DRAW"Q"', G + "DRAW 5", 'DRAW"U5"', G + 'DRAW"U-"', G + 'DRAW"U99999"']),
        ("move-absolute", [G + 'DRAW"M"', G + 'DRAW"M5"', G + 'DRAW"M5,"']),
        ("move-relative", [G + 'DRAW"M+5"', G + 'DRAW"M+5,"', G + 'DRAW"M+99999,1"']),
        ("blank-prefix", [G + 'DRAW"B"', G + 'DRAW"BQ"']),
        ("no-update-prefix", [G + 'DRAW"N"', G + 'DRAW"NQ"']),
        ("colour", [G + 'DRAW"C16"', G + 'DRAW"C"', G + 'DRAW"C-1"']),
        ("scale", [G + 'DRAW"S256"', G + 'DRAW"S"', G + 'DRAW"S-1"']),
        ("angle", [G + 'DRAW"A4"', G + 'DRAW"A"', G + 'DRAW"A-1"']),
        ("substring-exec", [G + 'DRAW"XZ$;"', G + 'DRAW"X"', G + 'DRAW"XA;"']),
        ("variable-substitution", [G + 'DRAW"U=Q;"', G + 'DRAW"U=A$;"', G + 'DRAW"U="'])],
    "BASE": [
        ("read", ["A=BASE(20)", 'A=BASE("A")', "A=BASE(-1)", "A=BASE"]),
        ("write", ["BASE(20)=0", 'BASE(5)="A"', "BASE(5)=-1", "BASE(5)=70000", "BASE(5)="])],
    "VDP": [
        ("read", ["A=VDP(8)", 'A=VDP("A")', "A=VDP(-1)", "A=VDP"]),
        ("write", ["VDP(8)=0", 'VDP(7)="A"', "VDP(7)=256", "VDP(7)=-1", "VDP(7)="])],
    "SPRITE": [
        ("pattern-write", ['SPRITE$(32)="A"', 'SPRITE$("A")="A"', "SPRITE$(1)=5", 'SPRITE$(-1)="A"']),
        ("enable", ["SPRITE ON 1", "SPRITE ON,"]),
        ("disable", ["SPRITE OFF 1", "SPRITE STOP 1"])],
    "ON GOTO": [
        ("index-goto", ['ON "A" GOTO 30', "ON -1 GOTO 30", "ON 256 GOTO 30", "ON 1 GOTO 99",
                        "ON 1 GOTO", "ON 1 GOTO 30,"])],
    "ON GOSUB": [
        ("index-gosub", ['ON "A" GOSUB 30', "ON -1 GOSUB 30", "ON 256 GOSUB 30", "ON 1 GOSUB 99",
                         "ON 1 GOSUB"])],
    "KEY": [
        ("assign", ['KEY 11,"A"', "KEY 1,5", 'KEY 0,"A"', 'KEY "A","B"', "KEY 1"]),
        ("list", ["KEY LIST 1"]),
        ("display-on", ["KEY ON 1"]),
        ("display-off", ["KEY OFF 1"])],
    "STICK": [
        ("cursor-keys", ["A=STICK(3)", 'A=STICK("A")', "A=STICK(-1)", "A=STICK"]),
        ("joystick-port", ["A=STICK(1,1)", "A=STICK(2.5)+STICK(3)"])],
    "STRIG": [
        ("space-bar", ["A=STRIG(5)", 'A=STRIG("A")', "A=STRIG(-1)", "A=STRIG"]),
        ("joystick-trigger", ["A=STRIG(1,1)", "A=STRIG(4)+STRIG(5)"])],
    "PDL": [
        ("read", ["A=PDL(13)", "A=PDL(0)", 'A=PDL("A")', "A=PDL"])],
    "PAD": [
        ("touch-status", ["A=PAD(8)", 'A=PAD("A")', "A=PAD(-1)", "A=PAD"]),
        ("coordinate", ["A=PAD(1,1)", "A=PAD(2)+PAD(9)"]),
        ("switch", ["A=PAD(3,1)", "A=PAD(7)+PAD(20)"])],
    "DEF USR": [
        ("default", ['DEF USR="A"', "DEF USR=70000", "DEF USR", "DEF USR=-1", "DEF USR=1,2"]),
        ("numbered", ['DEF USR9="A"', "DEF USR9", "DEF USR9=70000"])],
    "DEF FN": [
        ("numeric", ["DEF FNA(X)=", "DEF FNA(5)=1", "DEF FN(X)=1", "DEF FNA(X", "DEF FNA(X,)=1"]),
        ("string-valued", ["DEF FNA$(X)=", "DEF FNA$(5)=1", "DEF FNA$(X$"])],
    "FN": [
        ("numeric", ["DEF FNA(X)=X:A=FNA(1,2)", 'DEF FNA(X)=X:A=FNA("A")', "A=FNB(1)",
                     "DEF FNA(X)=X:A=FNA"]),
        ("string-valued", ['DEF FNA$(X)=STR$(X):A$=FNA$("A")', "A$=FNB$(1)",
                           "DEF FNA$(X)=STR$(X):A=FNA$(1)"])],
    "STOP": [
        ("break", ["STOP 1", "STOP ON 1", "STOP,"])],
    "PLAY": [
        ("notes", ['PLAY"H"', "PLAY 5", 'PLAY"C99"']),
        ("note-number", ['PLAY"N97"', 'PLAY"N"', 'PLAY"N-1"']),
        ("rest", ['PLAY"R0"', 'PLAY"R65"']),
        ("octave", ['PLAY"O9"', 'PLAY"O0"']),
        ("default-length", ['PLAY"L0"', 'PLAY"L65"']),
        ("tempo", ['PLAY"T31"', 'PLAY"T256"']),
        ("volume", ['PLAY"V16"', 'PLAY"V-1"']),
        ("envelope", ['PLAY"S16"', 'PLAY"M0"', 'PLAY"M65536"']),
        ("multi-voice", ['PLAY"C","D","E","F"', 'PLAY"C",5']),
        ("substring-exec", ['PLAY"XZ$;"', 'PLAY"X"', 'PLAY"XA;"'])],
    "SET": [
        ("refuse", ["SET 1", "SET", 'SET "A"'])],
}


def batch2_cases(kw, form, stmt, spec):
    valid = [v for _k, v, _e in spec]
    for i, (kind, _v, edges) in enumerate(spec):
        bad = ['"A"'] if kind == N else (["5"] if kind == S else [])
        for x in bad + edges:
            yield kw, form, x, _call(kw, stmt, valid[:i] + [x] + valid[i + 1:])
    if len(valid) > 1:
        yield kw, form, "missing-last", _call(kw, stmt, valid[:-1])
    yield kw, form, "no-args", _call(kw, stmt, [])
    yield kw, form, "extra", _call(kw, stmt, valid + [valid[-1]])


def cases():
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")), None)
    if any(f"--batch={n}" in sys.argv for n in (4, 5, 6, 7)):
        b = (BATCH7 if "--batch=7" in sys.argv else
             BATCH6 if "--batch=6" in sys.argv else
             BATCH5 if "--batch=5" in sys.argv else BATCH4)
        for kw, formlist in b.items():
            if only and kw not in only.split(","):
                continue
            for form, stmts in formlist:
                for st in stmts:
                    yield kw, form, st, st
        return
    if "--batch=2" in sys.argv or "--batch=3" in sys.argv:
        b = BATCH3 if "--batch=3" in sys.argv else BATCH2
        for kw, (form, stmt, spec) in b.items():
            if only and kw not in only.split(","):
                continue
            yield from batch2_cases(kw, form, stmt, spec)
        return
    for kw, (form, tpl, args) in BATCH.items():
        if only and kw not in only.split(","):
            continue
        for a in args:
            yield kw, form, a, f"PRINT {tpl.format(a=a)}"


def program(stmt):
    # batch 7: a case that switches to a bitmap SCREEN reports back in SCREEN 0
    # (a PRINT in SCREEN 2 draws where no reader looks); every other case is the
    # batches-1..6 program, unchanged.
    back = "SCREEN 0:" if "SCREEN" in stmt else ""
    return ["NEW", "10 ON ERROR GOTO 90", f"20 {stmt}", f'30 {back}PRINT"[OK]":END',
            f'90 {back}PRINT"[";ERR;ERL;"]":END', "RUN"]


def reading(raw):
    rows = [(raw or "")[i * omsx_repl.COLS:(i + 1) * omsx_repl.COLS]
            for i in range(omsx_repl.ROWS)]
    runi = [i for i, r in enumerate(rows) if r.strip() == "RUN"]
    # a batch-7 case's `SCREEN 0` clears the echoed RUN away: then the screen
    # holds ONLY the handler's output, so all of it is the reading
    out = "".join(rows[runi[-1] + 1:]) if runi else "".join(rows)
    m = re.findall(r"\[\s*(\d+)\s+(\d+)\s*\]|\[OK\]", out)
    if not m:
        return None
    last = m[-1]
    return "OK" if last == ("", "") else (int(last[0]), int(last[1]))


def _disk_image():
    import shutil, tempfile
    fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
    fh.close()
    shutil.copy(os.path.join(REPO, "disk", "test720.dsk"), fh.name)
    return fh.name


def main():
    disk = "--batch=3" in sys.argv
    ref, zb = (("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK") if disk else (REF, ZB))
    machines = [ref] + ([zb] if "--zb" in sys.argv else [])
    cs = list(cases())
    res = {}
    for m in machines:
        kw = {}
        if disk:
            # a PRIVATE writable copy per machine; the CF-3300 boots SCREEN 1 and
            # needs kwsweep's MACH_RESET_PRE / MACH_BOOT (an Enter, SCREEN 0; 14 s)
            kw = dict(diska=_disk_image(), step=8.0, cap_gap=20.0)
        cf = m.startswith("National")
        res[m] = omsx_repl.run_cases(m, [("direct", program(st)) for *_, st in cs],
                                     batch=False,
                                     reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                     boot=14.0 if cf else 8.0, capture="screen", **kw)
    sets = {}
    print(f"{'keyword':7} {'case':44} " + " ".join(f"{m[:12]:>14}" for m in machines))
    for i, (kw, form, a, st) in enumerate(cs):
        vals = [reading(res[m][i]) for m in machines]
        print(f"{kw:7} {st:44} " + " ".join(f"{str(v):>14}" for v in vals))
        v = vals[0]
        if isinstance(v, tuple):
            sets.setdefault(kw, {}).setdefault(form, {}).setdefault(v[0], st)
        elif v is None:
            print(f"   ⚠️ {kw} {st!r}: NO READING on the reference -- not scored")
    print("\n# the reference's error set per keyword form (code: first case)")
    for kw, forms in sets.items():
        for form, codes in forms.items():
            print(f"{kw:6} {form:14} " + "  ".join(f"{c}: {s}" for c, s in sorted(codes.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
