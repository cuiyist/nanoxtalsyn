# CHECK V6 and paired reading comparison, November 19

V6 is adopted on the original fixed sets, with zero new readings. Accuracy
uses the established paper-field matching, plus the local model for
nonmatches; unresolved claims are wrong. This is not a scientific audit.
Paper text, quotes, model inputs, and classification receipts stay local.

| Held-out metric | V5 | V6 |
|---|---:|---:|
| Accuracy (historical seven fields) | 896/901 (99.45%) | 971/976 (99.49%) |
| Added values correct vs. V5 | — | 75/75 |
| Completeness across the five required fields | 1,765/5,208 (33.89%) | 1,880/5,208 (36.10%) |

| Field | V5 accuracy | V6 accuracy | V5 completeness | V6 completeness |
|---|---:|---:|---:|---:|
| Composition | 68/68 | 68/68 | — | — |
| Chemical name | 311/314 | 311/314 | 765/2,511 | 765/2,511 |
| Chemical amount | 153/153 | 183/183 | 355/1,268 | 425/1,268 |
| Temperature | 126/126 | 141/141 | 289/569 | 324/569 |
| Time | 153/153 | 175/175 | 310/608 | 317/608 |
| Size | 52/52 | 55/55 | 46/252 | 49/252 |
| Emission peak | 14/14 | 19/19 | — | — |
| Absorption peak | 19/21 | 19/21 | — | — |
| Quantum yield | 9/9 | 9/9 | — | — |

Development (15 papers): V5 230/231 accuracy and 558/2,666 completeness;
V6 244/246 and 600/2,666. Only the 50 held-out papers determined adoption.
Single-pass amounts, temperatures, times, sizes and emission peaks are
enabled. No additional quantum-yield value was tested on the held-out
set, so its two-pass rule stays. Absorption remains held back from
conversion. Seven local classification jobs ran for new unmatched claims.

## T8: paired valid results

This comparison uses the saved T1 scores with V5 and includes only papers
valid for both R0 and the stated reading. The T4 speed floor remains
14.52 valid papers per hour.

| Reading | Common papers | R0 accuracy | Reading accuracy | R0 completeness | Reading completeness | Change | Valid papers/h |
|---|---:|---:|---:|---:|---:|---:|---:|
| R1 | 41 | 732/736 | 824/829 | 1,310/3,930 | 1,436/3,930 | +3.21 pts | 38.03 |
| R2 | 38 | 709/713 | 1,033/1,065 | 1,252/3,537 | 1,251/3,537 | −0.03 pts | 16.44 |
| R3 | 38 | 709/713 | 1,147/1,184 | 1,252/3,537 | 1,304/3,537 | +1.47 pts | 11.75 |
| R4 | 37 | 663/666 | 1,258/1,272 | 1,166/3,428 | 1,408/3,428 | +7.06 pts | 5.01 |

| Reading | Context | Malformed/invalid output | Timeout | Other/unspecified |
|---|---:|---:|---:|---:|
| R1 | 7 | 2 | 0 | 0 |
| R2 | 0 | 3 | 0 | 9 |
| R3 | 0 | 3 | 0 | 9 |
| R4 | 0 | 5 | 0 | 8 |

One cause per failed paper. Unresolved errors in the older archive are not
reclassified without evidence. Only R1 qualified for the fixed-set T9
retest. At this checkpoint, that retest is in progress. The previously
completed T5 run remains stopped: 200 papers, 191 attempts, 186 valid and
0 of 330 recipes qualified for replacement.
