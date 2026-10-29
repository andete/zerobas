10 REM ** ENGINEER'S TABLES - NUMBERS THE WAY A HOBBYIST PRINTED THEM **
20 KEY OFF:CLS:DEFINT I-N:DEFDBL D:DEFSNG S
30 REM 1: integer arithmetic, \ and MOD, the bitwise operators
40 A%=1000:B%=7:LPRINT "CP 1";A%\B%;A% MOD B%;-A%\B%;-A% MOD B%;A% AND 255;A% OR 7;A% XOR -1;NOT B%
50 REM 2: number bases, both ways
60 FOR I=0 TO 3:N=I*85+1:LPRINT "CP 2";N;HEX$(N);" ";OCT$(N);" ";BIN$(N);VAL("&H"+HEX$(N));VAL("&O"+OCT$(N)):NEXT
70 REM 3: rounding: INT, FIX, CINT on both sides of zero
80 FOR X=-2.5 TO 2.6 STEP 1.25:LPRINT "CP 3";X;INT(X);FIX(X);CINT(X);SGN(X);ABS(X):NEXT
90 REM 4: single against double precision
100 S=1/3:D=1/3#:LPRINT "CP 4";S;D;S*3;D*3;CSNG(D);CDBL(S)
110 D=0:FOR I=1 TO 10:D=D+.1#:NEXT:S=0:FOR I=1 TO 10:S=S+.1:NEXT:LPRINT "CP 5";D;S;D=1;S=1
120 REM 6: a table of square roots, logs and powers
130 FOR I=1 TO 5:LPRINT USING "CP 6 ## ##.#### ##.#### ####.### #.####^^^^";I;SQR(I);LOG(I);EXP(I);I^-3:NEXT
140 REM 7: trigonometry in degrees, through a DEF FN
150 PI#=4*ATN(1#):DEF FNR(G)=G*PI#/180
160 FOR G=0 TO 90 STEP 30:LPRINT USING "CP 7 ### +#.##### +#.##### ";G;SIN(FNR(G));COS(FNR(G));:IF G<90 THEN LPRINT USING "+##.####";TAN(FNR(G)) ELSE LPRINT "  INF"
170 NEXT
180 REM 8: compound interest, the hobbyist's favourite
190 DEF FNC#(P#,R,N)=P#*(1+R/100)^N
200 FOR N=5 TO 20 STEP 5:LPRINT USING "CP 8 ## ######.##";N;FNC#(1000,6.5,N):NEXT
210 REM 9: a bubble sort with SWAP, then the median and the mean
220 DIM V(9):RESTORE 900:FOR I=0 TO 9:READ V(I):NEXT
230 FOR I=0 TO 8:FOR J=0 TO 8-I:IF V(J)>V(J+1) THEN SWAP V(J),V(J+1)
240 NEXT J,I
250 T=0:FOR I=0 TO 9:T=T+V(I):LPRINT V(I);:NEXT:LPRINT
260 LPRINT "CP 9 MEDIAN";(V(4)+V(5))/2;"MEAN";T/10
270 REM 10: the largest numbers, and what STR$ makes of them
280 D=1.234567890123D+62:S=9.99999E+62:LPRINT "CP 10";D;S;STR$(-0.000001);STR$(1E+15);LEN(STR$(D))
290 REM 11: integer edge: 32767 + 1 is trapped
300 ON ERROR GOTO 800:I=32767:I=I+1:LPRINT "CP 11 NOT REACHED"
310 LPRINT "CP 12 END";FRE(0)>1000
320 END
800 LPRINT "CP 11 ERR";ERR;"IN";ERL;I:RESUME 310
900 DATA 31,-4,17,8.5,0,99,23,-11.25,42,6
