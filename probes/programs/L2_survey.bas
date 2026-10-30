1 REM @ANSWERS ABC|42|7,X|7,8|3,4,5|"SMITH, J",33|JONES|28|"Q",9||12|ALL OF IT, REALLY|1E2|-0|&H1F|  15  |N
10 REM ** A SURVEY - INPUT THE WAY PEOPLE TYPE INTO IT **
20 KEY OFF:CLS:N=0:T=0
30 REM 1: a number, typed wrong first (letters: ?Redo from start)
40 INPUT "AGE";A:LPRINT "CP 1";A
50 REM 2: two numbers: one bad, one right
60 INPUT "SHOE SIZE, HEIGHT";B,C:LPRINT "CP 2";B;C
70 REM 3: too many values (?Extra ignored)
80 INPUT "X,Y";X,Y:LPRINT "CP 3";X;Y
90 REM 4: a quoted name with a comma in it, then a plain one with a missing value
100 FOR K=1 TO 2:INPUT "NAME, AGE";N$,G:LPRINT "CP 4 [";N$;"]";G:N=N+1:T=T+G:NEXT
110 REM 5: a quoted single letter, then an empty answer to a number
120 INPUT "CODE, SCORE";Q$,S:LPRINT "CP 5 [";Q$;"]";S
130 INPUT "BONUS";U:LPRINT "CP 6";U
140 INPUT "LEVEL";V:LPRINT "CP 7";V
150 REM 6: LINE INPUT keeps the comma and everything else
160 LINE INPUT "COMMENT? ";M$:LPRINT "CP 8 [";M$;"]";LEN(M$)
170 REM 7: how numbers are read: exponent, signed zero, hex, spaces around
180 INPUT "A";E1:INPUT "B";E2:INPUT "C";E3:INPUT "D";E4:LPRINT "CP 9";E1;E2;E3;E4
190 INPUT "AGAIN (Y/N)";R$:LPRINT "CP 10 [";R$;"]";N;T;T/N
200 END
