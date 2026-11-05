10 REM D-TRAPCOST round 5b: string names at an operand's start, keyed once
20 A$="AB":B$="ABC":DEFSTR S:S="Q":C$(1)="X":DIM D$(3):D$(2)="YY"
30 LPRINT -(A$="AB");-(A$<B$);-(A$+"C"=B$);-(S="Q");-(C$(1)="X");-(D$(2)+A$="YYAB")
40 LPRINT -(A$ = "AB");-(NOT A$="X");LEN(A$+B$);-(A$>"A" AND B$<"B");-(S+S="QQ")
50 X=1:LPRINT -(X=1);-(A$<>"");ASC(A$);-("AB"=A$);A$+B$
60 ON ERROR GOTO 90:LPRINT -(A$=5):LPRINT "after":END
90 LPRINT "ERR";ERR:RESUME NEXT
