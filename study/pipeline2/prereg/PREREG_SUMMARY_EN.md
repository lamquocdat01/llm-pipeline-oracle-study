# English summary of the preregistration of study 2 and its amendments (PREREG_V2.md)

This file summarises `PREREG_V2.md`, which is written in Vietnamese. It does not replace it. The registered text is the
version at commit `203c724788d312e0a64f5159e14b9c6cd2b15a47` (2026-11-01, before any measurement of the plan); each amendment
is dated and committed in the same file. Where this summary and the Vietnamese text differ, the Vietnamese text governs.
Summary written 2026-11-14 (P3E).

## Before registration (§0)
Predictions are generated mechanically from the Pin–Observe matrix, not from data. Declared as seen before registering:
a 20-question smoke run (excluded from the sample); a check on two smoke questions in which the artefact suite failed
2 of 14 tests and the decision suite 0; the study-1 results.

## Matrix rule (§1)
Pin axis: a stage is caller-pinnable when the caller fixes every input that determines its output (model hash, seed,
temperature, thread count, prompt hash, index hash); delegated when another party operates a component (hosted Gemini,
web search). Observe axis: decision (discrete label) or artefact (the string that carries it). Prediction: decisions
stable for every stage; artefacts not stable if delegated, stable if pinnable. Depth (classify 1, route 2,
retrieve/live 3, generate 4) adds nothing once pinnability is known (H1).

## Sample (§2)
SQuAD 2.0 dev (11,873 questions). 20 smoke ids excluded; main sample of 200 questions drawn with seed 20261102 (94
unanswerable); 50 live-web questions; 40 oracle questions drawn with seed 20261103 (21 unanswerable). Ids fixed in
`runner/plan_p2.json`.

## Decision and artefact (§3)
classify: answerable/unanswerable vs raw JSON; route: RETRIEVE/ANSWER/REFUSE vs raw text; BM25 retrieve: top-5 ids;
live web: sources or not vs domains and answer text; generate: gold/other/nocite/abstain vs answer text. A parse
failure is a decision value, not missing data.

## Protocol (§4)
Ten runs per question, stage and arm, each at least 6 h after the previous one; temperature 0; hosted thinking budget 0;
local seed 0; at most 400 output tokens. Boundary probes on 20 questions (temperature 0.8; seed 1). A third family
(`llama3.1:8b`) on route and generate, and on two stages of pipeline 1 (MD3). Local pins checked at every call.
Budget cap USD 5, hard stop 4.50.

## Oracle (§5)
40 questions × {classify, route, generate} × {hosted, local} + BM25 = 7 cells, 280 tests per suite. Two pytest suites
(decision equals golden; normalised artefact equals golden). Golden = first valid run; the first 20 valid runs are read.
Failure rate per suite and cell with Wilson 95 % intervals; margin = artefact rate − decision rate with Newcombe hybrid
95 % intervals.

## Units and scoring rule (§6)
Scored pair: run 1 against run 5 (≥ 24 h). A *stable* prediction is correct when k/n ≤ 5 % and the upper Wilson bound
≤ 10 %, wrong when k/n ≥ 20 %; a *not stable* prediction is correct at ≥ 20 % and wrong at ≤ 5 %; in between a unit is
undecided but counts as wrong beyond 12.5 % against the prediction. 17 scored units (13 in pipeline 2, 4 for the third
family). H3 (prediction part): at least two thirds of decided pipeline-2 units correct.

## Hypotheses (§7–§9)
H1: logistic regression of an unchanged pair on depth, pinnability and observable, clustered by question; supported when
the pinnable interval is above 0 and the depth interval contains 0; plus a group comparison of units across depths.
H2: (i) every delegated stage has a margin with lower bound above 0; (ii) every pinned stage has |margin| ≤ 0.05 or an
interval containing 0; (iii) the delegated route margin has the same sign and order (ratio within [0.1, 10]) as in
study 1. H3 (oracle part): lower bound above 0 at delegated oracle cells and interval containing 0 at pinned cells.

## Amendments
- **V2-01** (2026-11-01): runner script renamed; no design change.
- **V2-02** (2026-11-03): oracle milestones from two to four per day.
- **V2-03** (2026-11-03): night-time memory threshold and task selection by hour.
- **V2-04** (2026-11-07): last oracle milestone extended; local server version pinned and checked per call.
- **V2-05** (2026-11-07): analysis plan fixed before analysis (unit counts, frozen scripts, H1 model, depth groups,
  missed milestones, runtime segments, pair spacing, family overlap, small cells, probes).
- **V2-07** (2026-11-07): after the silent update of the local server, corrects V2-04's record; makes the primary pair
  for local cells a same-runtime pair; reads local oracle cells on the original runtime; adds a re-measurement of the
  pipeline-1 units (MD3R); reports pairs across the update as exploratory. Written after those records existed and after
  reading median output-token counts per runtime segment.
- **V2-06** (2026-11-07, written after V2-07): control arm — the same Llama 3.1 8B served by a provider on route and
  generate, with four cells derived by the matrix rule.
- **V2-08** (2026-11-12, commit `b099b11`): study 3 — injected changes (rephrase, drop constraint, larger model,
  temperature 0.8, top-3 retrieval, server version A→B→A) on the 40 oracle questions, three controls, paired bootstrap
  Δ, questions S1–S3 (SQ1–SQ3 in the paper). Written after the study-2 results and an internal review, before any call.
  Addendum `b2a3dd6` drops the delegated larger-model change. Dated correction: the analysis was frozen at `9da8209`,
  after the first call and before the first read.
- **V2-09** (2026-11-13, commit `aea58ad`): follow-up — controls before changes on a restarted pinned server, controls
  after a call to another model, the Synonym change with a manipulation check on 40 questions outside the oracle set,
  three alternations of the pinned server version; fixed run order; analysis frozen in the same commit. Written after
  study 3 and a second internal review, before any call.
