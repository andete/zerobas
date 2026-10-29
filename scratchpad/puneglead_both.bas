10 REM PRINT USING: a leading and a trailing sign on one field
20 FOR K=1 TO 300:NEXT
30 LPRINT USING "A +.##+ B +.##- C +#.##+ D +#.##-";-.25;-.25;-.25;-.25
40 LPRINT USING "E +.##+ F +#.##+ G +#.##-";.25;.25;.25
