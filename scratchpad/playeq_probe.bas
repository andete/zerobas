10 REM playeq-acceptance: PLAY's =name; (D-PLAYEQ) -- the error code of each row
20 FOR K=1 TO 300:NEXT:ON ERROR GOTO 900
30 I%=4:A!=8.4:B!=8.6:C#=8.5:N=-1:S$="X":E%=255:F!=65535:X9=9:X8=8:Y1=31:Y2=32:Z#=-.5
40 DATA "V=I%;","N=I%;","O=I%;","L=I%;","S=I%;","M=I%;","R=I%;","C=I%;","C#=I%;","O=A!;"
50 DATA "O=B!;","O=C#;","V=N;","V=S$;","V=I%","V=ZZ;","V=I% ;","V= I%;","M=E%;","M=F!;"
60 DATA "T=1E2;","O=A;","V=(I%);","O=X9;","O=X8;","T=Y1;","T=Y2;","V=Z#;","O4V=I%;C","L=I%;R=I%;"
70 FOR R=1 TO 30:READ P$:E=0:PLAY P$:LPRINT R;P$;E:NEXT
80 FOR I=1 TO 2000:NEXT:LPRINT "Z END":END
900 E=ERR:RESUME NEXT
