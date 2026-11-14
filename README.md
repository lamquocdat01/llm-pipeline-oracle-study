# Where to Put the Oracle — data and scripts for studies 2, 3 and the follow-up V2-09

Release for the manuscript "Where to Put the Oracle: Decision-Level Assertions and the Limits of Pinning in Regression
Testing of LLM Pipeline Stages" (submitted to Information and Software Technology). Study 1 is released under tag
`tse-v1.0` of this repository.

* `study/pipeline2/prereg/PREREG_V2.md` — preregistration with every amendment (Vietnamese);
  `PREREG_SUMMARY_EN.md` — English summary.
* `study/pipeline2/results/` — raw records of study 2 (`P2_*`, `P2O_*`, `P3_*`, `P3H_*`, `MD3*`), study 3 (`S3_*`) and
  V2-09 (`S3B_*`); `results/oracle/obs_lan*.json` — oracle observations.
* `study/pipeline2/p2`, `scripts`, `tests` — the measurement code; `desktop/mrunner` — the shared runner.
* `study/analysis_v2` (registered, study 2), `analysis_v3` (registered, study 3), `analysis_v3b` (registered, V2-09),
  `analysis_v2_posthoc`, `analysis_v3_posthoc` (post hoc) — analysis scripts and their outputs in `out/`.
* `datasets/pipeline2_corpus/dev-v2.0.json` — SQuAD 2.0 dev (CC BY-SA 4.0).

Reproduce every number file: `python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt`, then
`THS_DATASETS=datasets .venv/Scripts/python repro_ist.py`. The script reruns all analyses into a temporary folder and
compares each JSON key by key with the shipped outputs.
