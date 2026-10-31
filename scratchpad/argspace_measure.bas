10 REM D-ARGSPACE: a space after ( or , before a string function's string argument
15 FOR I=1 TO 500:NEXT: REM long enough for the harness to see the run start
20 A$="AB"
30 LPRINT "1";STRING$(2, "AB")
40 LPRINT "2";STRING$(2, A$)
50 LPRINT "3";LEFT$( "ABCDE",2)
60 LPRINT "4";MID$( "ABCDE",2,2)
70 LPRINT "5";RIGHT$( "ABCDE",2)
80 SCREEN 1:SPRITE$(0)= "AB":B$=LEFT$(SPRITE$(0),2):SCREEN 0
90 LPRINT "6";B$
100 LPRINT "7";LEFT$( A$,1)
110 LPRINT "END"
