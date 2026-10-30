10 REM PLAY =name(subscript); : what the subscript may be, and the errors
20 FOR K=1 TO 300:NEXT:ON ERROR GOTO 900:DIM A(5),B%(3,3),S$(2):A(1)=8:A(2)=9:A(3)=4.7:B%(1,2)=7:J=1:S$(1)="V5"
30 DATA "O=A(1);","O=A(2);","O=A(J);","O=A(J+1);","O=A(3);","V=B%(1,2);","V=B%(J,2);","O=A(6);","O=Q(1);","V=S$(1);"
40 DATA "O=A( 1 );","O=A(1) ;","O=A(1);C","O=A(1","O=A();","O=A(1,1);","O=A(-1);","O=A(1.6);","V=A(J*0+1)*2;","O=A(2-1);"
50 FOR R=1 TO 20:READ P$:E=0:PLAY P$:LPRINT R;P$;E:NEXT
60 FOR I=1 TO 2000:NEXT:LPRINT "Z END":END
900 E=ERR:RESUME NEXT
