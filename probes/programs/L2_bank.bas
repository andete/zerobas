10 REM ** SAVINGS LEDGER - monthly interest, deposits, a yearly summary **
20 REM single precision (!) balances, integer (%) months, cents rounded with INT
30 CLS:DEFSNG A-Z:DEFINT M,Y
40 B=1250:R=.035:D=75
50 FOR Y%=1 TO 3:TI=0:TD=0
60 FOR M%=1 TO 12
70 I=INT(B*R/12*100+.5)/100:B=B+I:TI=TI+I
80 IF M% MOD 3=0 THEN B=B+D:TD=TD+D
90 IF M%=6 AND Y%=2 THEN B=B-400:LPRINT "CP W";Y%;M%;B
100 NEXT M%
110 LPRINT "CP";Y%;:LPRINT USING "##,###.## ##,###.## ##,###.##";B;TI;TD
120 PRINT USING "YEAR # BALANCE ##,###.##";Y%;B
130 NEXT Y%
140 C!=B:C%=B:LPRINT "CP C";C%;CINT(B);FIX(B);INT(-B);STR$(INT(B*100)/100)
150 A$="":FOR K=1 TO 4:A$=A$+RIGHT$(STR$(INT(B)),3)+",":NEXT:LPRINT "CP S ";A$;LEN(A$)
160 X=1/3:LPRINT "CP X";X;CSNG(2/3);1E6*X;10^5+.5;1234567;12345678
170 END
