1 REM @ANSWERS ABCDEFGH
10 REM D-PRSTR2X: a string item followed by a relational operator is read ONCE
20 PRINT "GO"
30 K$=INKEY$:IF K$="" THEN 30
40 LPRINT "A [";K$;"]"
50 LPRINT "B";INKEY$="";INKEY$="C";INKEY$<>""
60 IF INKEY$="E" THEN LPRINT "C YES" ELSE LPRINT "C NO"
70 LPRINT "D";INPUT$(1)="F";INPUT$(1)>"F"
80 A$="X":LPRINT "E";A$="X";A$<"A" OR -1;MID$("AB",2)>"A";LEFT$("AB",1)+"C"="AC";"A"<"B" AND 3
90 LPRINT "F [";INKEY$;"]"
100 T=5:LPRINT "G";T;"H"T
