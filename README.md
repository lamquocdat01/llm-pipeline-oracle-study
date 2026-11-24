# Where to Put the Oracle — data and scripts for studies 2, 3, the follow-up V2-09 and the re-analysis addendum

Release for the manuscript "Where to Put the Oracle: Decision-Level Assertions and the Limits of Pinning in Regression
Testing of LLM Pipeline Stages". The data of study 1 are available from the
author on request.

* `study/pipeline2/prereg/PREREG_V2.md` — analysis plan with every amendment (Vietnamese);
  `PREREG_SUMMARY_EN.md` — English summary.
* `study/pipeline2/results/` — raw records of study 2 (`P2_*`, `P2O_*`, `P3_*`, `P3H_*`, `MD3*`), study 3 (`S3_*`) and
  V2-09 (`S3B_*`); `results/oracle/obs_lan*.json` — oracle observations.
* `study/pipeline2/p2`, `scripts`, `tests` — the measurement code; `desktop/mrunner` — the shared runner.
* `study/pipeline2/tests_p2_decision/`, `tests_p2_artefact/` — the two pytest oracle suites of study 2 (committed in
  `203c724`, before the first call). `study/pipeline2/p2/oracle.py` runs them on each oracle run against the golden run.
* `study/analysis_v2` (registered, study 2), `analysis_v3` (registered, study 3), `analysis_v3b` (registered, V2-09),
  `analysis_v2_posthoc`, `analysis_v3_posthoc` (post hoc) — analysis scripts and their outputs in `out/`.
* Re-analysis addendum and repeated measurement (P6, added in tag `jss-v2.2-submission`):
  `prereg/p6/PREREG_ADDENDUM_MD_20261121.md` (plan, committed before the analyses and the first call),
  `PREREG_ADDENDUM_MD_AMEND1_20261122.md` and `PREREG_ADDENDUM_MD_AMEND2_20261124.md` (two amendments after failures of
  the host, each committed before the runs it governs), `INCIDENT_S3C_20261122.md` (what failed and why),
  `RESULTS_ADDENDUM_MD.md` (results; all in Vietnamese). Records: `study/pipeline2/results/S3C_20261121_v1.jsonl` and its
  manifest (22 runs; five runs voided by a full disk are kept and excluded by the analysis), `S3C_LUOT_20261124.json`
  (the final session), `S3C_SMOKE_*.jsonl` (smoke tests, not part of the sample), `S3C_local_*.log` (runner logs,
  UTF-16). Runner: `study/pipeline2/p2/s3c.py`, `scripts/run_s3c.py`; analyses: `study/analysis_p6/run_b1.py`,
  `run_b2.py`, `run_s3c.py`, outputs in `study/analysis_p6/out/`.
  Post hoc analyses after the second review of the manuscript (server state, the two standards, units):
  `study/analysis_p6/run_posthoc_r2b.py`, described in `prereg/p6/POSTHOC_R2B_MD_20261124.md` (added in tag `jss-v2.3-submission`).
* `datasets/pipeline2_corpus/dev-v2.0.json` — SQuAD 2.0 dev (CC BY-SA 4.0).
* `prereg/COMMIT_TIMELINE.md` — when each analysis plan was committed, against its first call. The plans were committed
  in the author's own repository, whose full history also holds unrelated private work and is not released.
  `prereg/commit_proofs/` holds, for every plan commit cited in the paper, the raw commit object, the tree objects on the
  path to each released file and the file contents; `python prereg/verify_commit_proofs.py` re-hashes them.

Re-run the two oracle suites offline on the stored observations, without any model call (example: run 3 against
the golden run 1; the suites skip when the two variables are unset):

    cd study/pipeline2
    P2_ORACLE_RUN=results/oracle/obs_lan03.json P2_ORACLE_GOLDEN=results/oracle/obs_lan01.json python -m pytest -q tests_p2_decision
    P2_ORACLE_RUN=results/oracle/obs_lan03.json P2_ORACLE_GOLDEN=results/oracle/obs_lan01.json python -m pytest -q tests_p2_artefact

(on Windows, set the two variables with `set` first). For run 3 this gives 16 of 280 decision tests and 72 of 280
artefact tests failed, as recorded.

Reproduce every number file: `python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt`, then
`THS_DATASETS=datasets .venv/Scripts/python repro_ist.py`. The script reruns all analyses into a temporary folder and
compares each JSON key by key with the shipped outputs. On Linux or macOS use `.venv/bin/python` and
`THS_DATASETS=datasets .venv/bin/python repro_ist.py`.

The addendum needs a second environment, because its embedding oracle pins a newer numpy:
`python -m venv .venv_p6 && .venv_p6/Scripts/python -m pip install -r requirements_p6.txt`, then
`THS_DATASETS=datasets .venv_p6/Scripts/python repro_p6.py` (downloads `intfloat/multilingual-e5-small` at the pinned
revision on first use; reruns the four analyses and compares key by key, restoring the shipped outputs).

Notes:

* Code is under the MIT licence (`LICENSE`). The records and analysis outputs produced by the studies may be reused
  under CC BY 4.0 with attribution to the paper; the SQuAD 2.0 corpus keeps its own licence, CC BY-SA 4.0.
* Many JSON keys, docstrings and comments are in Vietnamese (for example `ca_sot` = misses, `dung_sang_sai` = correct
  to wrong, `sai_sang_dung` = wrong to correct); the paper and its supplement give the English meaning of every
  reported quantity.
* The measurement code calls model services and needs packages not pinned here (for example `google-genai`, `psutil`);
  a logged-only language label in `p2/stages.py` uses a fastText model from study 1, and the study-1 task types in
  `desktop/mrunner/thuc.py` import modules of the voice assistant. None of these is released or needed to re-run the
  oracle suites or to reproduce the number files.
