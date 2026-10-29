10 REM PRINT USING: an E-form value in a field wider than its text
20 FOR K=1 TO 300:NEXT
30 LPRINT USING "A ################ B";1D+15
40 LPRINT USING "C **##############.## D";-1D+15
50 LPRINT USING "E ####################";1.2345678901234D+15
