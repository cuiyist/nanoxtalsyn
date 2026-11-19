# Two-pass recipe completeness: F and T

Checkpoint: 2026-11-17, F4 decided / F5 implemented / F6 candidate checks. This is an
in-progress experiment, not an independent scientific audit. All paper text, quotations, passes and
local-model scoring inputs remain on the curation computer. Reviewed records
are immutable; machine-extracted records remain `source_extracted`.

## Current results and pending decisions

- **F1:** saved inputs located for all **3,075** live machine-extracted primary
  papers at the frozen Source snapshot. The unchanged native CHECK was attempted
  on one primary archived reading per paper and 359 distinct alternate readings.
  Among **3,049 current-CLI-shape-valid primary readings**, CHECK retained
  **68,081 / 100,056 native-counted values (68.04%)** and 4,869 pairs. This is
  retention, not measured accuracy or recipe completeness.
- **F2–F4:** original 15-paper development set pinned; **50** other audited live
  papers drawn without replacement from 229 eligible primary DOIs using seed
  **20261116**. The unchanged baseline completed with **50/50** valid two-pass
  outputs, 100 calls and no retries. **F4 selects V5**, the last cumulative
  variant satisfying all three held-out criteria. The decision is recorded;
  the public implementation passed fixed-set equivalence; publication is pending.
- **F5 optics:** emission peaks (14/14 correct) and quantum yields (9/9)
  qualify for conversion. Absorption peaks remain held back (19/21, 90.48%).
- **F6 replacements:** [PR 178](https://github.com/cuiyist/nanoxtalsyn/pull/178)
  shipped 66 revised recipes in 40 existing papers, verified against Site commit
  `ed43e988a8e27d3e0a52c4f82d0c4a7db3a1d5fe`. The next candidate covers 300
  existing papers and 476 revisions. It includes next revisions for all 66
  PR 178 records with the owner-directed W corrections. This batch shipped
  and was verified in [PR 179](https://github.com/cuiyist/nanoxtalsyn/pull/179),
  Site `9bcb9f0f329742a816b7e237330b9d88ea05f822`.
  W actions in that batch: 83 starting-particle role changes, six shell
  omissions, four duplicate merges, and one determinate missing Greek letter
  restored (PR 178 subset: 15, six, three and one; counts can overlap).
  The next candidate is 457 revisions across 300 other existing papers.
  After the W transforms it adds a net 741 checked chemical entries, 514
  steps and 61 amounts. Five proposals with no checked gain after W were
  held out. W actions in this candidate: 71 role changes, 12 shell omissions
  and two duplicate merges. No new papers or training admissions. The next
  candidate counts are not published counts.
- **T3 / T4:** keeps R0 with CHECK V5. R4 increased completeness to 35.52%
  but its 5.01 valid papers/hour missed the 14.52/hour floor. R1–R3 did not
  increase held-out completeness. The full tables are below.
- **T5:** not started; 0 candidate papers reread or improved in this experiment.
- New-paper intake remains paused until F5 and T4 are decided. The audit lane,
  Worker A/B queue and five older owner holds remain paused.

### F2–F4 held-out comparison and decision

All 50 fixed held-out papers are included. Overall accuracy is over the seven
historical scored field kinds, not every prose statement. Completeness is the
preregistered audited-field presence metric described below.

| Variant | Overall accuracy | Accuracy of additions over V0 | Completeness | F4 result |
|---|---:|---:|---:|---|
| V0 | 763/773 (98.71%) | — | 1489/5208 (28.59%) | Baseline |
| V1 | 775/781 (99.23%) | 38/38 (100%) | 1523/5208 (29.24%) | Pass |
| V2 | 819/826 (99.15%) | 77/78 (98.72%) | 1626/5208 (31.22%) | Pass |
| V3 | 855/860 (99.42%) | 111/112 (99.11%) | 1709/5208 (32.81%) | Pass |
| V4 | 874/879 (99.43%) | 130/131 (99.24%) | 1734/5208 (33.29%) | Pass |
| V5 | 896/901 (99.45%) | 149/151 (98.68%) | 1765/5208 (33.89%) | **Selected** |

V0 exceeded 95%, so the accuracy gate remained 95%; the fallback threshold was
not used. V5 adds 5.30 percentage points of measured completeness. Across the
same 77 checked product pairs, chemicals increase from 224 to 314 and steps
from 272 to 339. This is CHECK retention, not 77 newly published recipes.
No development result determined adoption. Local held-out classification
completed 34/34 jobs: 118 unique nonmatches, 106 class A, zero error jobs or
retries. All non-A and unsettled outcomes count as wrong.

### Implementation and F6 preparation

The public CHECK port matched the frozen implementation in 378 comparisons
across the 65 fixed papers and six variants; two historical development inputs
retain shape holds. A subsequent wrapper correction restored Python's native
universal-newline handling of saved Windows text files. Without it, CRLF page
markers lost their locators. All 378 fixed-set comparisons and all 3,364 valid
saved readings were identical after removing page metadata. No scientific field,
score, model classification, adoption threshold or decision changed. Both old
and corrected receipts remain local; no model or PDF rereading was performed.

F6 examined 4,498 extracted records. The current protected private proposal pool
contains **2,881 revisions across 2,019 papers**, not live replacements. Another
1,030 records have no qualifying gain after preservation; 587 retain technical,
identity, alignment, conflict or historical-correction holds. Exact archived
whole-object omissions are reapplied after CHECK, rather than restoring prior
errors or discarding unrelated new details. Ambiguous omissions remain holds.
This curation overlay does not modify CHECK or its accuracy results.

Every proposal preserves the same record ID, next revision, extracted status,
figures, existing checked values and training eligibility. Product binding uses
the explicit sample label, any reported composition, and exact reproduction of
the native record ID, navigation formula and source group. Navigation never fills
an unreported scientific composition. Release checks and anonymous verification
remain required; the published replacement count above is still zero.

## F1: unchanged CHECK diagnosis

The primary denominator uses the archived reading tied to the public pair
export where an exact projected-pair hash is available. Otherwise it uses the
original saved reading and records that weaker binding. Distinct alternate
readings, including prior D rereads, have separate receipts and are not added
to the paper denominator. Public pair archives may predate canonical revisions
or deletion-only source corrections; this diagnostic does not reconstruct every
current canonical value or authorize restoring previously removed wrong facts.

### Shape-valid primary readings: drops by kind and reason

| Kind | Reported | Kept | Quote absent | Pass disagreement | Number absent from quote | No quote | Unit/range | Not numeric | Near-wording subset of quote-absent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chemical name | 19,013 | 14,470 | 2,421 | 2,122 | 0 | 0 | 0 | 0 | 433 |
| Chemical amount, assessed parent | 11,536* | 7,157 | 0 | 1,056 | 855 | 0 | 0 | 0 | 0 |
| Step | 22,832 | 14,457 | 2,399 | 5,976 | 0 | 0 | 0 | 0 | 627 |
| Structure field | 37,432 | 25,016 | 6,616 | 3,551 | 1,745 | 267 | 235 | 2 | 1,825 |
| Recipe field | 20,779 | 14,138 | 2,794 | 2,005 | 1,056 | 764 | 20 | 2 | 711 |

\* The amount denominator includes 2,468 amounts not assessed because their
parent chemical was dropped. Those are separate from the 1,911 assessed amount
failures. Native CHECK counts chemicals and steps as values but does not add
their child amounts, temperatures or times to its native value/kept totals.
Its amount failures do enter native drop counters. These historical mixed
units are preserved, not silently reconciled into an accuracy statistic.

Of 14,230 quote-absent rejections, **3,596** nearly match the paper (the native
rejection diagnostic uses an 85% contiguous normalized run to label near wording;
this is not an acceptance threshold), 9,757 are partly found and
877 are not found. These are subsets, not additional failures. F's proposed V4
threshold is 90%; it is included in the adopted cumulative V5.

**2,290 dropped chemical occurrences are named in a retained step's action,
description or uses list for the same product.** Of these separate mention
axes, 2,247 appear in uses and 826 in action/description; their intersection is
not counted twice. Separately, 978 dropped occurrences appear in retained step
quotes. This F1 measurement uses normalized whole-word literal names, not yet
V1 chemical-identity matching, and counts occurrences rather than distinct
compounds or papers.

Supplemental child-field accounting:

| Child field | Reported in pass A | Kept | Parent dropped, not assessed | Other rejection |
|---|---:|---:|---:|---:|
| Chemical amount | 11,536 | 7,157 | 2,468 | 1,911 |
| Step temperature | 11,197 | 4,851 | 4,235 | 2,111 |
| Step time | 8,245 | 4,155 | 3,329 | 761 |

Temperature rejections comprise 2,106 number-absent and five unit/range failures;
time rejections comprise 760 number-absent and one nonnumeric failure.

Native product pairing also omitted 320 pass-A products before assessing their
2,411 structure fields, 1,364 recipe fields, 1,194 chemicals, 827 amounts and
1,460 steps. Pass B contributed 341 unpaired products; within paired products,
2,403 pass-B-only chemical nominations (including 1,280 amounts) were never
considered by the asymmetric native checker. These are not folded into its
native 100,056-value denominator.

### Legacy shapes and failures

Twenty-six primary archived readings fail today's strict CLI shape admission.
They remain unchanged. Native diagnostic calls completed for 25 of them,
retaining 575 / 953 native-counted values and 39 pairs; 45 dropped chemical
occurrences still appear in retained step text/uses. These are explicitly
**diagnostic-only, not CLI-admitted results**. The remaining paper,
DOI `10.1021/es049194z`, raised `AttributeError` on its original malformed saved
input. It remains a technical failure, not a no-synthesis finding.

Across the separate 359 alternate saved readings, 357 native diagnostics
completed and two malformed-input calls failed. Their results are retained
separately and provide no extra unique-paper credit. No original pass, current
CHECK predicate, converter, canonical record or review status was changed for F1.

## F2–F4 preregistration

Development is exactly the 15 papers in the October 11 Qwen3-32B test, using
their saved two-pass inputs. Held-out selection is Python
`random.Random(20261116).shuffle(sorted(primary_DOIs))`, followed by the first
50, excluding development DOIs. The population is every other live primary
paper having an audited record (`review_status != source_extracted`). Selection
preceded PDF availability checks and any new extraction, scoring or variant
outcomes; there is no material-family or baseline-quality filter.

R0 completed at 2026-11-17T15:50:34Z in 4,131.453 seconds (68.86 minutes):
**43.5682 papers/hour**, measured after local model readiness, with two
concurrent papers and each paper's A/B passes sequential. Startup and subsequent
scoring are outside this reading-rate denominator. No other GPU model workload
ran during the baseline. This is the T4 speed reference, not end-to-end
publication throughput.

Accuracy, additions-over-V0 accuracy and audited-record completeness are
reported separately by field. Nonmatches were classified only by the local
model; unsettled classifications count as wrong. The cumulative variants and
adoption thresholds are those in the owner's November 16 instruction. No
held-out result is used to tune a variant after its specification is frozen.

The historical accuracy denominator has seven field kinds: composition,
chemical name, chemical amount, temperature, time, size and optical peak.
Quantum yield has a separate F5 gate. Other structure/recipe prose and
nonnumeric step descriptions are outside that historical accuracy denominator;
their retention is not a claim of measured 95% accuracy. Automatic matches use
October 11's per-paper, per-field rules, not independent product/step validation.
The local classifier checks product/step assignment for nonmatching values;
wrong-scope, wrong, missing, malformed and unsettled answers all count as wrong.

Completeness is micro-averaged presence recall over audited chemical-name,
amount, operation-temperature, operation-time and size occurrences, using the
specified score matching rules and identity-based chemical names. Name/formula
aliases count once per audited material. Maximum one-to-one occurrence recall
is also reported to show when one prediction matches repeated audited values;
it is not silently substituted for the preregistered decision metric. Failed
outputs stay in the fixed-set completeness denominator.

Before held-out scoring, two synthetic Unicode regression tests found and
corrected an offset mismatch in V4's supported-number span. The second frozen
specification preserves the first and the reason for the correction. All 90
development paper/variant outputs remained byte-identical. No held-out variant
outputs or scores were inspected for that correction, and no threshold, set,
prompt or scoring rule changed.

V1 uses chemical identity and considers pass B; V2 adds names supported by kept
step quotes; V3 permits overlapping-quote step pairing; V4 permits a 90%
contiguous quote run with numbers inside that run; V5 permits quoted single-pass
names/steps but not single-pass numeric fields. The variants are cumulative;
product pairing and strict whole-pass shape admission remain unchanged.

For F5, emission and quantum yield meet the separate 95% field gate, while
absorption does not. The small optical denominators are shown explicitly and
are not population-level certainty estimates. Every F6 replacement must retain all live checked values and figures,
increase checked chemicals, steps or amounts, retain the record ID/status and
advance the revision. Older source-backed deletions remain protected.

### Development: accuracy by field

| Field | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---:|---:|---:|---:|---:|---:|
| Composition | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 |
| Chemical name | 64/65 | 65/65 | 67/67 | 68/68 | 68/68 | 88/89 |
| Chemical amount | 36/36 | 38/40 | 38/40 | 38/40 | 38/40 | 40/40 |
| Temperature | 38/38 | 38/38 | 38/38 | 38/38 | 38/38 | 38/38 |
| Time | 23/23 | 23/23 | 23/23 | 29/29 | 29/29 | 29/29 |
| Size | 6/6 | 6/6 | 6/6 | 6/6 | 9/9 | 9/9 |
| Optical peak | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 | 13/13 |
| Quantum yield (separate F5 metric) | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |

Entries are correct/kept. Development V0 accuracy is 193/194 (99.48%); V5 is
230/231 (99.57%) with additions 38/39 (97.44%). Two original development passes
fail current strict shape admission: `10.1021/acs.chemmater.5b03943` and
`10.1021/acsanm.5c03294`. They were not repaired or reread; their audited fields
remain in the completeness denominator. Local scoring completed 10/10 jobs,
37 unique nonmatches, 33 class A, zero error jobs or retries.

### Development: completeness by field

| Field | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---:|---:|---:|---:|---:|---:|
| Chemical name | 184/1246 | 210/1246 | 211/1246 | 213/1246 | 213/1246 | 249/1246 |
| Chemical amount | 103/861 | 116/861 | 116/861 | 116/861 | 116/861 | 116/861 |
| Temperature | 112/232 | 112/232 | 112/232 | 112/232 | 112/232 | 112/232 |
| Time | 48/241 | 48/241 | 48/241 | 69/241 | 69/241 | 69/241 |
| Size | 9/86 | 9/86 | 9/86 | 9/86 | 12/86 | 12/86 |

Entries are matched audited occurrences/all audited occurrences. Overall
development completeness is V0 456/2666 (17.10%) and V5 558/2666 (20.93%).
One-to-one occurrence recall, a sensitivity rather than the decision metric:
V0 135/2666 (5.06%), V1 146/2666 (5.48%), V2 147/2666 (5.51%),
V3 154/2666 (5.78%), V4 157/2666 (5.89%), V5 169/2666 (6.34%).

### Held-out: accuracy by field

| Field | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---:|---:|---:|---:|---:|---:|
| Composition | 66/66 | 66/66 | 66/66 | 66/66 | 68/68 | 68/68 |
| Chemical name | 223/224 | 229/230 | 275/277 | 282/284 | 290/292 | 311/314 |
| Chemical amount | 149/153 | 155/155 | 153/153 | 153/153 | 153/153 | 153/153 |
| Temperature | 113/114 | 113/114 | 113/114 | 126/126 | 126/126 | 126/126 |
| Time | 131/133 | 131/133 | 131/133 | 147/148 | 152/153 | 153/153 |
| Size | 50/50 | 50/50 | 50/50 | 50/50 | 52/52 | 52/52 |
| Optical peak | 31/33 | 31/33 | 31/33 | 31/33 | 33/35 | 33/35 |
| Quantum yield (separate F5 metric) | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 |

Entries are correct/kept. All 50 held-out two-pass outputs pass strict shape
admission. V5 absorption is 19/21 (90.48%); emission is 14/14 (100%); quantum
yield is 9/9 (100%). Absorption and emission are combined only in the historical
accuracy field above, not in their separate F5 conversion decisions.

### Held-out: completeness by field

| Field | V0 | V1 | V2 | V3 | V4 | V5 |
|---|---:|---:|---:|---:|---:|---:|
| Chemical name | 577/2511 | 602/2511 | 709/2511 | 717/2511 | 734/2511 | 765/2511 |
| Chemical amount | 350/1268 | 359/1268 | 355/1268 | 355/1268 | 355/1268 | 355/1268 |
| Temperature | 243/569 | 243/569 | 243/569 | 289/569 | 289/569 | 289/569 |
| Time | 273/608 | 273/608 | 273/608 | 302/608 | 310/608 | 310/608 |
| Size | 46/252 | 46/252 | 46/252 | 46/252 | 46/252 | 46/252 |

Entries are matched audited occurrences/all audited occurrences. One-to-one
occurrence recall (sensitivity, not decision metric): V0 535/5208 (10.27%),
V1 557/5208 (10.70%), V2 592/5208 (11.37%), V3 616/5208 (11.83%),
V4 628/5208 (12.06%), V5 643/5208 (12.35%). The large difference from presence
recall shows why repeated-value matches must not be mistaken for complete,
sample-specific recipes or training readiness.

### Fixed paper sets

Development: `10.1006/jssc.1999.8299`, `10.1006/jssc.2000.8772`, `10.1021/ac0701233`, `10.1021/ac203261x`, `10.1021/ac400041t`, `10.1021/acs.cgd.3c01472`, `10.1021/acs.chemmater.3c01309`, `10.1021/acs.chemmater.5b03943`, `10.1021/acs.chemmater.7b02861`, `10.1021/acs.jpcc.5b07318`, `10.1021/acs.nanolett.5c06337`, `10.1021/acsami.1c13723`, `10.1021/acsami.5b08595`, `10.1021/acsanm.5c03294`, `10.1038/nmat1826`.

Held out, in fixed sampled order: `10.1021/ac2033968`, `10.1021/la0347051`, `10.1021/ja9805425`, `10.1063/1.2752021`, `10.1063/1.1887823`, `10.1021/jp905720g`, `10.1021/acs.inorgchem.8b02945`, `10.1021/acs.chemmater.7b00354`, `10.1021/acsami.8b04556`, `10.1021/acs.chemmater.5c02845`, `10.1023/a:1011445009443`, `10.1021/nl801817d`, `10.1021/ja0489184`, `10.1007/bf02708509`, `10.1021/acssuschemeng.8b00398`, `10.1021/cm990228p`, `10.1021/cm201400w`, `10.1021/am4029735`, `10.1021/jp991389j`, `10.1021/jp1050047`, `10.1021/acsnano.4c06961`, `10.1021/ja103607q`, `10.1021/nl025785g`, `10.1021/cm502687p`, `10.1006/jssc.1999.8366`, `10.1021/la035405m`, `10.1021/acsami.7b12046`, `10.1021/acs.chemmater.9b03529`, `10.1021/acs.chemmater.4c02553`, `10.1039/b406060a`, `10.1021/acs.jpcc.5c05144`, `10.1021/nl100571m`, `10.1021/cm0102436`, `10.1021/nl4044289`, `10.1021/acs.chemmater.5b03731`, `10.1021/cm970557m`, `10.1021/la051196p`, `10.1021/jp951903v`, `10.1039/a806166a`, `10.1021/ac200383z`, `10.1021/acsami.1c18038`, `10.1021/acsami.4c00615`, `10.1021/acs.inorgchem.3c03156`, `10.1007/s11671-010-9592-3`, `10.1021/cm970189m`, `10.1021/jp912103t`, `10.1103/physrevlett.100.235503`, `10.1016/j.ica.2011.10.038`, `10.1021/ja048427j`, `10.1021/cm0115416`.

## Publication baseline, not F/T publication credit

The already-read intake was closed before F1. Its final 37-paper batch added
49 records and 182 source crops through [PR 177](https://github.com/cuiyist/mattersyn/pull/177).
Frozen [Source commit](https://github.com/cuiyist/mattersyn/commit/0a5c3aebfcd27e7d82a6a9bfd7c338ad821310c8)
and verified [Site commit](https://github.com/cuiyist/mattersyn-site/commit/9e2dbbc77e4f70e24233ee24c75cca529dc10755)
are the F1/F2 record baseline. Publisher run 44079884776 succeeded; anonymous
verification, payload checks and the full 73,083-file boundary scan passed.
That release is not an F6 replacement release. The first 40-paper / 66-revision
F6 batch is live through [PR 178](https://github.com/cuiyist/nanoxtalsyn/pull/178).
Publisher run 44156606277 and Pages run 44163181313 passed; anonymous verification
matched all revised record bytes and the accompanying public assets.

### Preserved engineering failures and corrections

The first Source preparation stopped because the new authored policy JSON had
no path classification. One exact Source-only configuration classification was
added through the existing mechanism; the guard was unchanged and the complete
boundary scan then passed. No private-content exception was introduced.

The first PR178 Linux candidate build failed in its isolated test package:
the new policy module/configuration were not among the snapshot-bound test
dependencies, and file-based test loaders did not resolve sibling modules.
The correction adds those two exact dependencies and the normal sibling import
path in two test loaders. All missing/changed/duplicate dependency rejection
checks remain. The 26 focused dependency, Reader-compaction and actual-consumer
regressions pass; a fresh complete GitHub run is still required. No canonical
record, frozen CHECK, converter logic, scoring result or publication gate changed.

## T3–T4: held-out results and decision

T4 adopts **R0**. The cutoff is 95% accuracy and 14.52 valid papers/hour. The set is the same 50 audited papers; no paper text left the machine.

| Reading | Accuracy | Completeness | Valid / attempted | Valid papers/h | Attempted papers/h | Chemicals / recipe | Steps / recipe |
|---|---:|---:|---:|---:|---:|---:|---:|
| R0 | 896/901 (99.45%) | 1,765/5,208 (33.89%) | 50/50 | 43.57 | 43.57 | 4.08 | 4.40 |
| R1 | 824/829 (99.40%) | 1,436/5,208 (27.57%) | 41/50 | 38.03 | 46.37 | 5.00 | 4.97 |
| R2 | 1,354/1,389 (97.48%) | 1,498/5,208 (28.76%) | 38/50 | 16.44 | 21.63 | 5.04 | 5.30 |
| R3 | 1,490/1,532 (97.26%) | 1,559/5,208 (29.93%) | 38/50 | 11.75 | 15.46 | 5.44 | 5.39 |
| R4 | 1,771/1,787 (99.10%) | 1,850/5,208 (35.52%) | 37/50 | 5.01 | 6.76 | 4.90 | 4.04 |

Full-set completeness includes the missing values from failed readings. Valid-paper throughput counts successful two-pass reads, not merely attempts.

### Accuracy by field

| Field | R0 | R1 | R2 | R3 | R4 |
|---|---:|---:|---:|---:|---:|
| composition | 68/68 (100.00%) | 50/50 (100.00%) | 81/81 (100.00%) | 81/81 (100.00%) | 119/123 (96.75%) |
| chemical name | 311/314 (99.04%) | 307/310 (99.03%) | 477/489 (97.55%) | 511/528 (96.78%) | 704/710 (99.15%) |
| chemical amount | 153/153 (100.00%) | 152/152 (100.00%) | 262/266 (98.50%) | 327/338 (96.75%) | 387/388 (99.74%) |
| temperature | 126/126 (100.00%) | 132/132 (100.00%) | 227/228 (99.56%) | 239/239 (100.00%) | 205/207 (99.03%) |
| time | 153/153 (100.00%) | 119/119 (100.00%) | 200/208 (96.15%) | 222/227 (97.80%) | 253/253 (100.00%) |
| size | 52/52 (100.00%) | 39/39 (100.00%) | 65/66 (98.48%) | 65/66 (98.48%) | 62/62 (100.00%) |
| optical peak | 33/35 (94.29%) | 25/27 (92.59%) | 42/51 (82.35%) | 45/53 (84.91%) | 41/44 (93.18%) |
| quantum yield | 9/9 (100.00%) | 10/10 (100.00%) | 14/16 (87.50%) | 17/18 (94.44%) | 13/14 (92.86%) |

### Completeness by field

| Field | R0 | R1 | R2 | R3 | R4 |
|---|---:|---:|---:|---:|---:|
| chemical name | 765/2,511 (30.47%) | 618/2,511 (24.61%) | 620/2,511 (24.69%) | 621/2,511 (24.73%) | 796/2,511 (31.70%) |
| chemical amount | 355/1,268 (28.00%) | 287/1,268 (22.63%) | 306/1,268 (24.13%) | 352/1,268 (27.76%) | 362/1,268 (28.55%) |
| temperature | 289/569 (50.79%) | 239/569 (42.00%) | 288/569 (50.62%) | 291/569 (51.14%) | 305/569 (53.60%) |
| time | 310/608 (50.99%) | 255/608 (41.94%) | 249/608 (40.95%) | 260/608 (42.76%) | 339/608 (55.76%) |
| size | 46/252 (18.25%) | 37/252 (14.68%) | 35/252 (13.89%) | 35/252 (13.89%) | 48/252 (19.05%) |

T7: 1,599 live DOI papers had a filename-matched SI PDF beside the main PDF. Of 3,319 live primary DOIs, 3,318 had a DOI-named main PDF in the local corpora. This metadata count does not rule out supplements with ambiguous filenames.
