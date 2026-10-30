1 REM @ANSWERS ABCDEFGH
10 REM INKEY$ used directly inside a comparison, with keys waiting
20 PRINT "GO"
30 K$=INKEY$:IF K$="" THEN 30
40 LPRINT "A [";K$;"]"
50 LPRINT "B";INKEY$="";INKEY$="C";INKEY$<>""
60 IF INKEY$="E" THEN LPRINT "C YES" ELSE LPRINT "C NO"
70 X=(INKEY$>"");Y$=INKEY$:LPRINT "D";X;"[";Y$;"]";LEN(INKEY$)
