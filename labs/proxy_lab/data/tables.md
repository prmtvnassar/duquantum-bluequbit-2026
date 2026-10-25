## Exact OTOC(2) vectors: structure by Manhattan distance from the corner butterfly

| grid | depth | n_inst | noise floor 2^-n/2 | mean abs v (all) | mean abs v by distance d (max over inst) | rho(v,d) mean [min,max] | abs v at far corner (per inst) |
|---|---|---|---|---|---|---|---|
| 4x4 | 8 | 3 | 0.0039 | 0.1676 | d0:0.154 d1:0.148 d2:0.196 d3:0.238 d4:0.318 d5:0.191 d6:0.614 | +0.34 [-0.02,+0.59] | 0.479 0.078 0.614 |
| 4x4 | 12 | 3 | 0.0039 | 0.0246 | d0:0.012 d1:0.017 d2:0.006 d3:0.025 d4:0.056 d5:0.118 d6:0.081 | -0.61 [-0.74,-0.45] | 0.081 0.007 0.019 |
| 4x4 | 16 | 6 | 0.0039 | 0.0037 | d0:0.009 d1:0.006 d2:0.004 d3:0.007 d4:0.009 d5:0.006 d6:0.005 | -0.20 [-0.59,+0.03] | 0.005 0.001 0.002 0.002 0.000 0.002 |
| 4x5 | 4 | 2 | 0.0010 | 0.9144 | d0:0.635 d1:0.681 d2:0.932 d3:1.000 d4:1.000 d5:1.000 d6:1.000 d7:1.000 | +0.66 [+0.62,+0.70] | 1.000 1.000 |
| 4x5 | 8 | 3 | 0.0010 | 0.3618 | d0:0.150 d1:0.106 d2:0.179 d3:0.292 d4:0.470 d5:0.710 d6:0.791 d7:1.000 | +0.63 [+0.59,+0.70] | 1.000 1.000 1.000 |
| 4x5 | 12 | 3 | 0.0010 | 0.0417 | d0:0.006 d1:0.023 d2:0.019 d3:0.045 d4:0.056 d5:0.086 d6:0.100 d7:0.238 | -0.15 [-0.81,+0.29] | 0.039 0.238 0.065 |
| 4x5 | 16 | 6 | 0.0010 | 0.0063 | d0:0.004 d1:0.002 d2:0.004 d3:0.004 d4:0.022 d5:0.015 d6:0.035 d7:0.029 | -0.36 [-0.57,-0.14] | 0.004 0.019 0.029 0.026 0.006 0.011 |
| 5x5 | 16 | 2 | 0.0002 | 0.0167 | d0:0.003 d1:0.001 d2:0.002 d3:0.010 d4:0.016 d5:0.039 d6:0.059 d7:0.079 d8:0.090 | -0.33 [-0.78,+0.12] | 0.090 0.000 |

## Exact value versus slack = depth - contact layer (pooled over all instances and groups)

slack -1 = never reached (value exactly +1). Contact is counted through the layers of U in reverse order, because X_0 is conjugated by the last layer of U first.

| slack | n values | mean v (signed) | std v | mean abs v | frac v<0 |
|---|---|---|---|---|---|
| -1 | 44 | +1.000 | 0.000 | 1.000 | 0.00 |
| 0 | 28 | +0.043 | 0.365 | 0.302 | 0.46 |
| 1 | 20 | -0.163 | 0.310 | 0.283 | 0.80 |
| 2 | 30 | +0.001 | 0.203 | 0.156 | 0.57 |
| 3 | 12 | -0.097 | 0.160 | 0.150 | 0.75 |
| 4 | 38 | -0.059 | 0.117 | 0.074 | 0.76 |
| 5 | 24 | -0.020 | 0.060 | 0.046 | 0.62 |
| 6 | 52 | -0.027 | 0.030 | 0.028 | 0.79 |
| 7 | 20 | -0.013 | 0.034 | 0.021 | 0.55 |
| 8 | 74 | -0.003 | 0.030 | 0.012 | 0.50 |
| 9 | 48 | +0.000 | 0.007 | 0.005 | 0.40 |
| 10 | 42 | -0.001 | 0.005 | 0.004 | 0.48 |
| 11 | 28 | -0.001 | 0.003 | 0.002 | 0.54 |
| 12 | 34 | +0.002 | 0.004 | 0.003 | 0.26 |
| 13 | 14 | +0.002 | 0.003 | 0.002 | 0.29 |
| 16 | 14 | +0.002 | 0.004 | 0.003 | 0.21 |

Per group (mean v / mean abs v by slack):

- 4x4 depth 8: s0: +0.100/0.244 (n12), s1: -0.127/0.196 (n9), s2: +0.056/0.146 (n9), s3: -0.041/0.148 (n6), s4: -0.098/0.116 (n6), s5: +0.001/0.051 (n3), s8: -0.073/0.100 (n3)
- 4x4 depth 12: s4: -0.034/0.040 (n12), s5: -0.033/0.035 (n9), s6: -0.026/0.029 (n9), s7: +0.003/0.006 (n6), s8: +0.007/0.008 (n6), s9: +0.007/0.007 (n3), s12: +0.008/0.008 (n3)
- 4x4 depth 16: s8: -0.000/0.003 (n24), s9: -0.000/0.004 (n18), s10: +0.000/0.004 (n18), s11: -0.001/0.004 (n12), s12: +0.001/0.003 (n12), s13: +0.004/0.004 (n6), s16: +0.003/0.005 (n6)
- 4x5 depth 4: s-1: +1.000/1.000 (n32), s0: -0.448/0.583 (n4), s1: -0.714/0.714 (n2), s4: -0.228/0.407 (n2)
- 4x5 depth 8: s-1: +1.000/1.000 (n12), s0: +0.149/0.266 (n12), s1: -0.078/0.275 (n9), s2: -0.046/0.254 (n9), s3: -0.152/0.152 (n6), s4: -0.052/0.058 (n6), s5: +0.035/0.093 (n3), s8: +0.031/0.072 (n3)
- 4x5 depth 12: s2: -0.006/0.089 (n12), s4: -0.040/0.041 (n12), s5: -0.033/0.041 (n9), s6: -0.044/0.044 (n9), s7: -0.009/0.010 (n6), s8: -0.002/0.009 (n6), s9: +0.001/0.014 (n3), s12: +0.001/0.003 (n3)
- 4x5 depth 16: s6: -0.017/0.019 (n24), s8: -0.003/0.005 (n24), s9: +0.002/0.003 (n18), s10: -0.002/0.004 (n18), s11: -0.000/0.001 (n12), s12: +0.001/0.001 (n12), s13: +0.000/0.001 (n6), s16: +0.001/0.002 (n6)
- 5x5 depth 16: s6: -0.034/0.035 (n10), s7: -0.029/0.040 (n8), s8: -0.007/0.008 (n8), s9: -0.005/0.009 (n6), s10: -0.001/0.004 (n6), s11: -0.001/0.002 (n4), s12: +0.001/0.001 (n4), s13: +0.000/0.000 (n2), s16: +0.002/0.002 (n2)

## G4 (6x6 + q36/q37, depth 16, butterfly q0): slack per qubit and the pooled-proxy prediction

| q | row,col | Manhattan d | slack | predicted mean v | predicted abs v |
|---|---|---|---|---|---|
| 0 | 0,0 | 0 | 16 | +0.002 | 0.003 |
| 1 | 0,1 | 1 | 12 | +0.002 | 0.003 |
| 2 | 0,2 | 2 | 10 | -0.001 | 0.004 |
| 3 | 0,3 | 3 | 8 | -0.003 | 0.012 |
| 4 | 0,4 | 4 | 6 | -0.027 | 0.028 |
| 5 | 0,5 | 5 | 4 | -0.059 | 0.074 |
| 6 | 1,0 | 1 | 13 | +0.002 | 0.002 |
| 7 | 1,1 | 2 | 12 | +0.002 | 0.003 |
| 8 | 1,2 | 3 | 10 | -0.001 | 0.004 |
| 9 | 1,3 | 4 | 8 | -0.003 | 0.012 |
| 10 | 1,4 | 5 | 6 | -0.027 | 0.028 |
| 11 | 1,5 | 6 | 4 | -0.059 | 0.074 |
| 12 | 2,0 | 2 | 11 | -0.001 | 0.002 |
| 13 | 2,1 | 3 | 11 | -0.001 | 0.002 |
| 14 | 2,2 | 4 | 10 | -0.001 | 0.004 |
| 15 | 2,3 | 5 | 8 | -0.003 | 0.012 |
| 16 | 2,4 | 6 | 6 | -0.027 | 0.028 |
| 17 | 2,5 | 7 | 4 | -0.059 | 0.074 |
| 18 | 3,0 | 3 | 9 | +0.000 | 0.005 |
| 19 | 3,1 | 4 | 9 | +0.000 | 0.005 |
| 20 | 3,2 | 5 | 9 | +0.000 | 0.005 |
| 21 | 3,3 | 6 | 8 | -0.003 | 0.012 |
| 22 | 3,4 | 7 | 6 | -0.027 | 0.028 |
| 23 | 3,5 | 8 | 4 | -0.059 | 0.074 |
| 24 | 4,0 | 4 | 7 | -0.013 | 0.021 |
| 25 | 4,1 | 5 | 7 | -0.013 | 0.021 |
| 26 | 4,2 | 6 | 7 | -0.013 | 0.021 |
| 27 | 4,3 | 7 | 7 | -0.013 | 0.021 |
| 28 | 4,4 | 8 | 6 | -0.027 | 0.028 |
| 29 | 4,5 | 9 | 4 | -0.059 | 0.074 |
| 30 | 5,0 | 5 | 5 | -0.020 | 0.046 |
| 31 | 5,1 | 6 | 5 | -0.020 | 0.046 |
| 32 | 5,2 | 7 | 5 | -0.020 | 0.046 |
| 33 | 5,3 | 8 | 5 | -0.020 | 0.046 |
| 34 | 5,4 | 9 | 5 | -0.020 | 0.046 |
| 35 | 5,5 | 10 | 4 | -0.059 | 0.074 |
| 36 | 6,0 | 6 | 3 | -0.097 | 0.150 |
| 37 | 6,1 | 7 | 3 | -0.097 | 0.150 |

## Scores (agreement with the exact answer, 0-1000), mean over instances [min, max]

Null baseline for an uncorrelated vector: E[score] = 1000/(n-1). 'LOO' = constants taken from all other instances (all groups).


### 4x4, depth 8 (n=16, 3 instances, null = 67; fitted constants from s1, held-out = other instances)

| method | mean | [min, max] | held-out mean | per instance |
|---|---|---|---|---|
| MPS chi8 | 362 | [219, 640] | 429 | 226 219 640 |
| MPS chi16 | 591 | [372, 809] | 701 | 372 592 809 |
| MPS chi32 | 778 | [642, 931] | 846 | 642 760 931 |
| MPS chi64 | 889 | [806, 961] | 930 | 806 899 961 |
| MPS mean over all chi | 691 | [492, 897] | 791 | 492 684 897 |
| MPS mean top-2 chi | 838 | [729, 951] | 892 | 729 833 951 |
| MPS chi64 sign-agreement with exact (frac x1000) | 792 | [750, 812] | 781 | 812 812 750 |
| MPS chi64 vs chi32 self-consistency (agreement x1000) | 951 | [934, 978] | 960 | 934 943 978 |
| MPS chi64 mean abs error x1000 | 111 | [78, 133] | 128 | 78 133 122 |
| PPS L3 eps 0.01 (None->0) | 771 | [646, 944] | 795 | 724 646 944 |
| PPS L3 eps 0.01 max abs value x1000 | 521 | [351, 701] | 526 | 511 351 701 |
| PPS L3 eps 0.001 (None->0) | 989 | [985, 992] | 992 | 985 992 991 |
| PPS L3 eps 0.001 max abs value x1000 | 512 | [423, 635] | 529 | 477 423 635 |
| prior: Manhattan distance | 186 | [1, 350] | 175 | 208 1 350 |
| prior: distance squared | 217 | [7, 375] | 191 | 270 7 375 |
| prior: exp(d) | 275 | [19, 423] | 201 | 423 19 383 |
| prior: 1 outside support of W (slack<0) | 0 | [0, 0] | 0 | 0 0 0 |
| prior: far-corner indicator | 276 | [1, 493] | 168 | 493 1 334 |
| prior: -slack | 123 | [34, 274] | 168 | 34 61 274 |
| prior: signed slack-mean table, LOO | 88 | [45, 125] | 109 | 45 125 93 |
| prior: abs slack-mean table, LOO | 96 | [8, 200] | 140 | 8 80 200 |
| random Gaussian vector (null) | 64 | [58, 74] | 60 | 74 61 58 |
| prior: sigmoid front fitted on s1 (d0=7.5, w=0.25) | 277 | [1, 493] | 170 | 493 1 338 |
| prior: sigmoid front, LOO within group | 149 | [14, 218] | 116 | 217 14 218 |
| combo: chi64 shrunk toward mean by exp(-abs(chi64-chi32)/s), s=0.2 fitted on s1 | 862 | [821, 925] | 883 | 821 841 925 |
| combo: (1-a) z(chi64) + a z(distance), a=0.00 fitted on s1 | 889 | [806, 961] | 930 | 806 899 961 |
| combo: (1-a) z(chi64) + a z(front), a=0.15 fitted on s1 | 877 | [815, 970] | 908 | 815 846 970 |
| combo: (1-a) z(chi64) + a z(signed slack table LOO), a=0.00 fitted on s1 | 889 | [806, 961] | 930 | 806 899 961 |

### 4x4, depth 12 (n=16, 3 instances, null = 67; fitted constants from s1, held-out = other instances)

| method | mean | [min, max] | held-out mean | per instance |
|---|---|---|---|---|
| MPS chi8 | 120 | [4, 277] | 178 | 4 80 277 |
| MPS chi16 | 70 | [7, 140] | 73 | 62 7 140 |
| MPS chi32 | 12 | [1, 31] | 3 | 31 1 4 |
| MPS chi64 | 55 | [18, 76] | 47 | 71 18 76 |
| MPS mean over all chi | 68 | [9, 157] | 83 | 37 9 157 |
| MPS mean top-2 chi | 17 | [1, 48] | 1 | 48 1 1 |
| MPS chi64 sign-agreement with exact (frac x1000) | 521 | [312, 688] | 625 | 312 562 688 |
| MPS chi64 vs chi32 self-consistency (agreement x1000) | 763 | [534, 878] | 706 | 878 877 534 |
| MPS chi64 mean abs error x1000 | 138 | [41, 275] | 70 | 275 99 41 |
| PPS L3 eps 0.01 (None->0) | 0 | [0, 0] | 0 | 0 0 0 |
| PPS L3 eps 0.01 max abs value x1000 | 0 | [0, 0] | 0 | 0 0 0 |
| PPS L3 eps 0.001 (None->0) | 253 | [24, 465] | 146 | 465 24 269 |
| PPS L3 eps 0.001 max abs value x1000 | 14 | [7, 18] | 12 | 18 17 7 |
| prior: Manhattan distance | 390 | [206, 545] | 313 | 545 206 420 |
| prior: distance squared | 359 | [147, 567] | 255 | 567 147 364 |
| prior: exp(d) | 167 | [12, 326] | 88 | 326 12 164 |
| prior: 1 outside support of W (slack<0) | 0 | [0, 0] | 0 | 0 0 0 |
| prior: far-corner indicator | 36 | [21, 60] | 24 | 60 27 21 |
| prior: -slack | 272 | [208, 381] | 304 | 208 228 381 |
| prior: signed slack-mean table, LOO | 214 | [89, 289] | 276 | 89 289 262 |
| prior: abs slack-mean table, LOO | 270 | [135, 399] | 338 | 135 277 399 |
| random Gaussian vector (null) | 73 | [72, 75] | 73 | 75 72 73 |
| prior: sigmoid front fitted on s1 (d0=4.0, w=0.5) | 398 | [217, 632] | 281 | 632 217 346 |
| prior: sigmoid front, LOO within group | 393 | [283, 540] | 319 | 540 283 355 |
| combo: chi64 shrunk toward mean by exp(-abs(chi64-chi32)/s), s=0.1 fitted on s1 | 99 | [65, 147] | 106 | 84 65 147 |
| combo: (1-a) z(chi64) + a z(distance), a=1.00 fitted on s1 | 390 | [206, 545] | 313 | 545 206 420 |
| combo: (1-a) z(chi64) + a z(front), a=0.95 fitted on s1 | 390 | [206, 632] | 269 | 632 206 332 |
| combo: (1-a) z(chi64) + a z(signed slack table LOO), a=1.00 fitted on s1 | 214 | [89, 289] | 276 | 89 289 262 |
| MPS chi64 score restricted to slack<=6 qubits | 25 | [0, 47] | 14 | 47 0 27 |

### 4x4, depth 16 (n=16, 6 instances, null = 67; fitted constants from s1, held-out = other instances)

| method | mean | [min, max] | held-out mean | per instance |
|---|---|---|---|---|
| MPS chi8 | 36 | [2, 115] | 20 | 115 83 2 5 5 3 |
| MPS chi16 | 21 | [1, 53] | 15 | 53 31 16 19 6 1 |
| MPS chi32 | 54 | [6, 157] | 54 | 52 6 157 46 56 7 |
| MPS chi64 | 50 | [0, 192] | 21 | 192 0 8 82 5 11 |
| MPS chi128 | 57 | [0, 210] | 27 | 210 64 4 61 0 5 |
| MPS mean over all chi | 46 | [4, 152] | 24 | 152 37 18 51 12 4 |
| MPS mean top-2 chi | 57 | [2, 229] | 22 | 229 2 10 86 5 10 |
| MPS chi128 sign-agreement with exact (frac x1000) | 552 | [375, 750] | 562 | 500 375 375 750 750 562 |
| MPS chi128 vs chi64 self-consistency (agreement x1000) | 408 | [14, 831] | 408 | 406 675 14 448 73 831 |
| MPS chi128 mean abs error x1000 | 18 | [11, 25] | 16 | 25 18 19 18 11 14 |
| PPS L3 eps 0.01 (None->0) | 0 | [0, 0] | 0 | 0 0 0 0 0 0 |
| PPS L3 eps 0.01 max abs value x1000 | 0 | [0, 0] | 0 | 0 0 0 0 0 0 |
| PPS L3 eps 0.001 (None->0) | 11 | [0, 66] | 0 | 66 0 0 0 0 0 |
| PPS L3 eps 0.001 max abs value x1000 | 0 | [0, 2] | 0 | 2 0 0 0 0 0 |
| PPS L3 eps 0.0001 (None->0) | 0 | [0, 0] | 0 | 0 0 0 0 0 0 |
| PPS L3 eps 0.0001 max abs value x1000 | 0 | [0, 0] | 0 | 0 0 0 0 0 0 |
| prior: Manhattan distance | 81 | [1, 343] | 29 | 343 38 1 1 88 17 |
| prior: distance squared | 73 | [3, 305] | 27 | 305 3 13 3 95 21 |
| prior: exp(d) | 47 | [0, 211] | 14 | 211 0 15 4 27 26 |
| prior: 1 outside support of W (slack<0) | 0 | [0, 0] | 0 | 0 0 0 0 0 0 |
| prior: far-corner indicator | 20 | [0, 84] | 8 | 84 6 1 21 0 10 |
| prior: -slack | 104 | [0, 303] | 64 | 303 235 0 30 18 36 |
| prior: signed slack-mean table, LOO | 40 | [1, 118] | 25 | 116 118 2 1 4 2 |
| prior: abs slack-mean table, LOO | 44 | [0, 81] | 37 | 81 57 79 0 25 22 |
| random Gaussian vector (null) | 67 | [59, 73] | 66 | 73 70 70 59 69 64 |
| prior: sigmoid front fitted on s1 (d0=0.5, w=4.0) | 82 | [0, 342] | 30 | 342 49 0 1 86 16 |
| prior: sigmoid front, LOO within group | 82 | [0, 159] | 77 | 111 159 82 90 0 51 |
| combo: chi128 shrunk toward mean by exp(-abs(chi128-chi64)/s), s=1.0 fitted on s1 | 54 | [1, 190] | 27 | 190 66 4 60 1 5 |
| combo: (1-a) z(chi128) + a z(distance), a=1.00 fitted on s1 | 81 | [1, 343] | 29 | 343 38 1 1 88 17 |
| combo: (1-a) z(chi128) + a z(front), a=1.00 fitted on s1 | 82 | [0, 342] | 30 | 342 49 0 1 86 16 |
| combo: (1-a) z(chi128) + a z(signed slack table LOO), a=0.40 fitted on s1 | 95 | [1, 294] | 55 | 294 241 1 33 1 1 |

### 4x5, depth 4 (n=20, 2 instances, null = 53; fitted constants from s1, held-out = other instances)

| method | mean | [min, max] | held-out mean | per instance |
|---|---|---|---|---|
| MPS chi8 | 852 | [840, 864] | 864 | 840 864 |
| MPS chi16 | 980 | [973, 987] | 973 | 987 973 |
| MPS chi32 | 997 | [997, 998] | 997 | 998 997 |
| MPS mean over all chi | 969 | [965, 973] | 965 | 973 965 |
| MPS mean top-2 chi | 991 | [988, 994] | 988 | 994 988 |
| MPS chi32 sign-agreement with exact (frac x1000) | 1000 | [1000, 1000] | 1000 | 1000 1000 |
| MPS chi32 vs chi16 self-consistency (agreement x1000) | 991 | [987, 995] | 987 | 995 987 |
| MPS chi32 mean abs error x1000 | 40 | [31, 49] | 31 | 49 31 |
| PPS L3 eps 0.01 (None->0) | 1000 | [1000, 1000] | 1000 | 1000 1000 |
| PPS L3 eps 0.01 max abs value x1000 | 1000 | [1000, 1000] | 1000 | 1000 1000 |
| PPS L3 eps 0.001 (None->0) | 1000 | [1000, 1000] | 1000 | 1000 1000 |
| PPS L3 eps 0.001 max abs value x1000 | 1000 | [1000, 1000] | 1000 | 1000 1000 |
| prior: Manhattan distance | 440 | [386, 494] | 494 | 386 494 |
| prior: distance squared | 262 | [251, 272] | 272 | 251 272 |
| prior: exp(d) | 62 | [62, 62] | 62 | 62 62 |
| prior: 1 outside support of W (slack<0) | 914 | [909, 920] | 909 | 920 909 |
| prior: far-corner indicator | 12 | [12, 12] | 12 | 12 12 |
| prior: -slack | 499 | [331, 666] | 666 | 331 666 |
| prior: signed slack-mean table, LOO | 909 | [888, 930] | 930 | 888 930 |
| prior: abs slack-mean table, LOO | 882 | [844, 919] | 919 | 844 919 |
| random Gaussian vector (null) | 54 | [46, 63] | 46 | 63 46 |
| prior: sigmoid front fitted on s1 (d0=2.0, w=0.25) | 744 | [650, 837] | 837 | 650 837 |
| prior: sigmoid front, LOO within group | 704 | [571, 837] | 837 | 571 837 |
| combo: chi32 shrunk toward mean by exp(-abs(chi32-chi16)/s), s=1.0 fitted on s1 | 995 | [994, 996] | 994 | 996 994 |
| combo: (1-a) z(chi32) + a z(distance), a=0.00 fitted on s1 | 997 | [997, 998] | 997 | 998 997 |
| combo: (1-a) z(chi32) + a z(front), a=0.05 fitted on s1 | 997 | [996, 998] | 996 | 998 996 |
| combo: (1-a) z(chi32) + a z(signed slack table LOO), a=0.10 fitted on s1 | 997 | [995, 999] | 995 | 999 995 |

### 4x5, depth 8 (n=20, 3 instances, null = 53; fitted constants from s1, held-out = other instances)

| method | mean | [min, max] | held-out mean | per instance |
|---|---|---|---|---|
| prior: Manhattan distance | 404 | [343, 494] | 435 | 343 494 375 |
| prior: distance squared | 496 | [435, 585] | 527 | 435 585 469 |
| prior: exp(d) | 370 | [349, 397] | 373 | 365 397 349 |
| prior: 1 outside support of W (slack<0) | 760 | [686, 843] | 719 | 843 686 751 |
| prior: far-corner indicator | 160 | [144, 177] | 151 | 177 144 158 |
| prior: -slack | 296 | [262, 344] | 303 | 282 344 262 |
| prior: signed slack-mean table, LOO | 773 | [667, 875] | 722 | 875 667 777 |
| prior: abs slack-mean table, LOO | 735 | [696, 793] | 707 | 793 717 696 |
| random Gaussian vector (null) | 52 | [49, 55] | 50 | 55 49 52 |
| prior: sigmoid front fitted on s1 (d0=5.5, w=1.0) | 515 | [452, 609] | 546 | 452 609 484 |
| prior: sigmoid front, LOO within group | 519 | [418, 645] | 569 | 418 645 493 |

### 4x5, depth 12 (n=20, 3 instances, null = 53; fitted constants from s1, held-out = other instances)

| method | mean | [min, max] | held-out mean | per instance |
|---|---|---|---|---|
| MPS chi8 | 212 | [53, 512] | 292 | 53 512 71 |
| MPS chi16 | 226 | [24, 343] | 327 | 24 343 312 |
| MPS chi32 | 322 | [4, 625] | 481 | 4 625 336 |
| MPS chi64 | 286 | [0, 571] | 571 | 0 571 |
| MPS mean over all chi | 306 | [17, 641] | 451 | 17 641 261 |
| MPS mean top-2 chi | 319 | [1, 611] | 478 | 1 611 346 |
| MPS chi64 sign-agreement with exact (frac x1000) | 425 | [350, 500] | 500 | 350 500 |
| MPS chi64 vs chi32 self-consistency (agreement x1000) | 926 | [924, 928] | 928 | 924 928 |
| MPS chi64 mean abs error x1000 | 251 | [115, 388] | 115 | 388 115 |
| PPS L3 eps 0.01 (None->0) | 274 | [4, 770] | 410 | 4 770 49 |
| PPS L3 eps 0.01 max abs value x1000 | 122 | [41, 213] | 127 | 112 213 41 |
| PPS L3 eps 0.001 (None->0) | 383 | [144, 787] | 466 | 217 787 144 |
| PPS L3 eps 0.001 max abs value x1000 | 181 | [70, 305] | 188 | 169 305 70 |
| prior: Manhattan distance | 249 | [7, 657] | 370 | 7 83 657 |
| prior: distance squared | 256 | [26, 554] | 371 | 26 189 554 |
| prior: exp(d) | 253 | [61, 523] | 349 | 61 523 176 |
| prior: 1 outside support of W (slack<0) | 0 | [0, 0] | 0 | 0 0 0 |
| prior: far-corner indicator | 209 | [12, 515] | 263 | 100 515 12 |
| prior: -slack | 195 | [2, 538] | 292 | 2 45 538 |
| prior: signed slack-mean table, LOO | 81 | [8, 200] | 22 | 200 36 8 |
| prior: abs slack-mean table, LOO | 189 | [16, 423] | 276 | 16 129 423 |
| random Gaussian vector (null) | 50 | [49, 51] | 49 | 51 49 50 |
| MPS chi32 sign-agreement with exact (frac x1000) | 100 | [100, 100] | 100 | 100 |
| MPS chi32 vs chi16 self-consistency (agreement x1000) | 750 | [750, 750] | 750 | 750 |
| MPS chi32 mean abs error x1000 | 334 | [334, 334] | 334 | 334 |
| prior: sigmoid front fitted on s1 (d0=8.5, w=0.25) | 213 | [14, 528] | 271 | 97 528 14 |
| prior: sigmoid front, LOO within group | 145 | [15, 383] | 199 | 35 383 15 |
| combo: chi32 shrunk toward mean by exp(-abs(chi32-chi16)/s), s=0.02 fitted on s1 | 67 | [10, 170] | 90 | 21 10 170 |
| combo: (1-a) z(chi32) + a z(distance), a=0.85 fitted on s1 | 269 | [7, 649] | 400 | 7 152 649 |
| combo: (1-a) z(chi32) + a z(front), a=1.00 fitted on s1 | 213 | [14, 528] | 271 | 97 528 14 |
| combo: (1-a) z(chi32) + a z(signed slack table LOO), a=0.85 fitted on s1 | 114 | [33, 208] | 68 | 208 102 33 |
| MPS chi32 score restricted to slack<=6 qubits | 288 | [79, 677] | 378 | 109 677 79 |

### 4x5, depth 16 (n=20, 6 instances, null = 53; fitted constants from s1, held-out = other instances)

| method | mean | [min, max] | held-out mean | per instance |
|---|---|---|---|---|
| MPS chi8 | 113 | [30, 419] | 129 | 30 69 62 32 65 419 |
| MPS chi16 | 149 | [2, 391] | 166 | 64 236 146 2 57 391 |
| MPS chi32 | 172 | [8, 459] | 205 | 8 66 345 24 130 459 |
| MPS chi64 | 227 | [63, 515] | 281 | 63 95 515 233 |
| MPS mean over all chi | 155 | [13, 468] | 181 | 22 61 336 13 29 468 |
| MPS mean top-2 chi | 185 | [4, 460] | 220 | 6 81 441 115 4 460 |
| MPS chi64 sign-agreement with exact (frac x1000) | 500 | [400, 600] | 467 | 600 600 400 400 |
| MPS chi64 vs chi32 self-consistency (agreement x1000) | 637 | [209, 844] | 780 | 209 844 808 689 |
| MPS chi64 mean abs error x1000 | 216 | [171, 249] | 205 | 249 171 202 243 |
| PPS L3 eps 0.01 (None->0) | 0 | [0, 0] | 0 | 0 0 0 0 0 0 |
| PPS L3 eps 0.01 max abs value x1000 | 0 | [0, 0] | 0 | 0 0 0 0 0 0 |
| PPS L3 eps 0.001 (None->0) | 320 | [9, 638] | 283 | 507 9 638 23 184 558 |
| PPS L3 eps 0.001 max abs value x1000 | 3 | [1, 5] | 3 | 4 3 5 1 2 1 |
| prior: Manhattan distance | 153 | [18, 323] | 178 | 24 218 202 323 18 130 |
| prior: distance squared | 179 | [4, 346] | 214 | 4 317 268 346 11 130 |
| prior: exp(d) | 186 | [2, 383] | 219 | 16 343 383 317 2 52 |
| prior: 1 outside support of W (slack<0) | 0 | [0, 0] | 0 | 0 0 0 0 0 0 |
| prior: far-corner indicator | 161 | [0, 470] | 184 | 47 91 470 323 35 0 |
| prior: -slack | 226 | [121, 372] | 233 | 193 121 247 372 136 287 |
| prior: signed slack-mean table, LOO | 405 | [232, 530] | 436 | 252 232 530 474 444 500 |
| prior: abs slack-mean table, LOO | 381 | [216, 513] | 414 | 216 228 477 506 349 513 |
| random Gaussian vector (null) | 50 | [47, 55] | 51 | 50 51 49 47 55 51 |
| MPS chi32 sign-agreement with exact (frac x1000) | 350 | [300, 400] | 350 | 400 300 |
| MPS chi32 vs chi16 self-consistency (agreement x1000) | 473 | [252, 694] | 473 | 252 694 |
| MPS chi32 mean abs error x1000 | 251 | [231, 272] | 251 | 231 272 |
| prior: sigmoid front fitted on s1 (d0=1.0, w=0.5) | 49 | [12, 107] | 44 | 75 24 36 107 12 42 |
| prior: sigmoid front, LOO within group | 110 | [5, 275] | 131 | 5 84 149 275 9 141 |
| combo: chi32 shrunk toward mean by exp(-abs(chi32-chi16)/s), s=0.02 fitted on s1 | 171 | [16, 298] | 179 | 128 16 242 298 157 185 |
| combo: (1-a) z(chi32) + a z(distance), a=1.00 fitted on s1 | 153 | [18, 323] | 178 | 24 218 202 323 18 130 |
| combo: (1-a) z(chi32) + a z(front), a=1.00 fitted on s1 | 49 | [12, 107] | 44 | 75 24 36 107 12 42 |
| combo: (1-a) z(chi32) + a z(signed slack table LOO), a=0.70 fitted on s1 | 272 | [121, 422] | 267 | 299 121 288 422 265 238 |
| MPS chi32 score restricted to slack<=6 qubits | 318 | [129, 687] | 356 | 129 157 331 186 687 421 |

### 5x5, depth 16 (n=25, 2 instances, null = 42; fitted constants from s1, held-out = other instances)

| method | mean | [min, max] | held-out mean | per instance |
|---|---|---|---|---|
| MPS chi8 | 73 | [17, 128] | 128 | 17 128 |
| MPS chi16 | 3 | [1, 5] | 5 | 1 5 |
| MPS chi32 | 127 | [10, 244] | 10 | 244 10 |
| MPS chi64 | 433 | [433, 433] | nan | 433 |
| MPS mean over all chi | 102 | [38, 166] | 38 | 166 38 |
| MPS mean top-2 chi | 189 | [8, 371] | 8 | 371 8 |
| MPS chi64 sign-agreement with exact (frac x1000) | 240 | [240, 240] | nan | 240 |
| MPS chi64 vs chi32 self-consistency (agreement x1000) | 631 | [631, 631] | nan | 631 |
| MPS chi64 mean abs error x1000 | 246 | [246, 246] | nan | 246 |
| PPS L3 eps 0.01 (None->0) | 0 | [0, 0] | 0 | 0 0 |
| PPS L3 eps 0.01 max abs value x1000 | 0 | [0, 0] | 0 | 0 0 |
| prior: Manhattan distance | 312 | [16, 608] | 16 | 608 16 |
| prior: distance squared | 347 | [28, 666] | 28 | 666 28 |
| prior: exp(d) | 210 | [12, 407] | 12 | 407 12 |
| prior: 1 outside support of W (slack<0) | 0 | [0, 0] | 0 | 0 0 |
| prior: far-corner indicator | 71 | [1, 141] | 1 | 141 1 |
| prior: -slack | 241 | [4, 479] | 4 | 479 4 |
| prior: signed slack-mean table, LOO | 160 | [12, 309] | 12 | 309 12 |
| prior: abs slack-mean table, LOO | 220 | [9, 431] | 9 | 431 9 |
| random Gaussian vector (null) | 42 | [41, 42] | 41 | 42 41 |
| MPS chi32 sign-agreement with exact (frac x1000) | 560 | [560, 560] | 560 | 560 |
| MPS chi32 vs chi16 self-consistency (agreement x1000) | 693 | [693, 693] | 693 | 693 |
| MPS chi32 mean abs error x1000 | 323 | [323, 323] | 323 | 323 |
| prior: sigmoid front fitted on s1 (d0=5.5, w=1.0) | 359 | [42, 676] | 42 | 676 42 |
| prior: sigmoid front, LOO within group | 307 | [42, 572] | 42 | 572 42 |
| combo: chi32 shrunk toward mean by exp(-abs(chi32-chi16)/s), s=1.0 fitted on s1 | 101 | [10, 193] | 10 | 193 10 |
| combo: (1-a) z(chi32) + a z(distance), a=0.75 fitted on s1 | 336 | [21, 652] | 21 | 652 21 |
| combo: (1-a) z(chi32) + a z(front), a=0.75 fitted on s1 | 394 | [50, 738] | 50 | 738 50 |
| combo: (1-a) z(chi32) + a z(signed slack table LOO), a=1.00 fitted on s1 | 160 | [12, 309] | 12 | 309 12 |
| MPS chi32 score restricted to slack<=6 qubits | 257 | [196, 317] | 196 | 317 196 |