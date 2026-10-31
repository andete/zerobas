10 REM ** C8 - CONTEST STYLE: FLOATING POINT, DIVISION AND POWERS **
20 CLS:CLEAR 500:DEFDBL A-H:DEFINT I-N:DIM A(4,5),X(4):ON ERROR GOTO 900
25 REM the last of 14 digits is a ruled difference (correct rounding): print to 8 places
26 DEF FNR(V#)=INT(V#*1D8+.5)/1D8
30 REM 1: a 4x4 system by Gauss-Jordan elimination with partial pivoting
40 FOR I=1 TO 4:FOR J=1 TO 5:READ A(I,J):NEXT J,I
50 DATA 2,1,-1,3,13, 1,-3,2,1,-1, 3,2,4,-2,16, -1,1,1,1,4
60 D=1:FOR K=1 TO 4:P=K:FOR I=K+1 TO 4:IF ABS(A(I,K))>ABS(A(P,K)) THEN P=I
70 NEXT:IF P<>K THEN D=-D:FOR J=1 TO 5:T=A(K,J):A(K,J)=A(P,J):A(P,J)=T:NEXT
80 D=D*A(K,K):F=A(K,K):FOR J=K TO 5:A(K,J)=A(K,J)/F:NEXT
90 FOR I=1 TO 4:IF I<>K THEN F=A(I,K):FOR J=K TO 5:A(I,J)=A(I,J)-F*A(K,J):NEXT
100 NEXT I,K:FOR I=1 TO 4:X(I)=A(I,5):NEXT
110 LPRINT "CP 1";FNR(X(1));FNR(X(2));FNR(X(3));FNR(X(4));FNR(D)
120 REM 2: the same answers rounded, and the residual of row 1
130 LPRINT "CP 2";CINT(X(1));CINT(X(2));CINT(X(3));CINT(X(4));ABS(2*X(1)+X(2)-X(3)+3*X(4)-13)<1D-10
140 REM 3: powers -- integer, negative and fractional exponents, and negative bases
150 LPRINT "CP 3";2^10;1.5^3;(-2)^3;(-2)^4;2^-3;10^-2;0^0;0^3
160 LPRINT "CP 4";FNR(2^.5);FNR(27^(1/3));FNR(16^.25);FNR(100^1.5);2^30;2^31;-2^2
170 REM 4: division in each precision, and a quotient that rounds up
180 LPRINT "CP 5";1/3;1#/3;2/3!;10/4;-7/2;1E10/3;1/7#;100/3E-5
190 REM 5: SQR, and INT / FIX / CINT around zero and at the halves
200 LPRINT "CP 6";FNR(SQR(2));SQR(1E-10);SQR(144);SQR(0);FNR(SQR(2#))
210 LPRINT "CP 7";INT(-2.5);FIX(-2.5);CINT(-2.5);CINT(2.5);INT(2.999999);FIX(-0.1);CINT(-0.5);CINT(1.5)
220 REM 6: the same numbers through PRINT USING
230 LPRINT USING "CP 8 ##.### +##.## #.##^^^^ ###,###.##";22/7;-1/3;6.02E23;1234567/8
240 LPRINT USING "CP 9 $$###.## **##.# ##.##- &";1/8;2^.5;-1.5;"END"
250 REM 7: the errors -- divide by zero, overflow, a fractional power of a negative
260 E$="":RESTORE 290:FOR I=1 TO 5:READ G$:E=0:Z=0
270 IF G$="Z" THEN Y=1/Z ELSE IF G$="O" THEN Y=1E38*1E38 ELSE IF G$="N" THEN Y=(-8)^(1/3) ELSE IF G$="P" THEN Y=0^-1 ELSE Y=10^99
280 E$=E$+G$+STR$(E)+" ":NEXT:LPRINT "CP 10 ";E$
290 DATA Z,O,N,P,X
300 REM 8: a running sum that drifts in single precision and not in double
310 S!=0:S#=0:FOR I=1 TO 1000:S!=S!+.1:S#=S#+.1#:NEXT:LPRINT "CP 11";S!;S#;S!=100;CSNG(S#)
320 LPRINT "CP 12";CDBL(1/3!);CSNG(1/3#);1/3#=1/3;3*(1/3#)=1
330 LPRINT "END":END
900 E=ERR:RESUME NEXT
