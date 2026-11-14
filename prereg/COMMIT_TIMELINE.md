# Commit timeline of the analysis plans (studies 2, 3 and V2-09)

Commits are in the author's own repository; their timestamps are set by the author's machine and are **not** an
independent registry. The full history is not released because the repository also holds unrelated private work.
`commit_proofs/` holds, for each commit below, the raw commit object, the tree objects on the path to each released
file and the file contents; `python prereg/verify_commit_proofs.py` re-hashes them with the git object format and
checks every chain commit → tree → … → blob. A matching SHA-1 shows that the printed hash names exactly that
content; it does not prove when the commit was made.

Where a plan was committed only seconds before its first call, the paper calls it an *analysis plan committed
before the calls*, not a preregistration.

| Commit | Role | What it records | Commit time (+07:00) | First governed call | Commit → call | Files proved |
|---|---|---|---|---|---|---|
| `203c724` | Study 2 plan | Study-2 plan, measurement code and run plan | 2026-11-01 09:20:20 | 2026-11-01 09:21:23 | 64 s | 11 |
| `39b530c` | Study 2 plan | Records hash 203c724 inside the plan | 2026-11-01 09:20:28 | — | — | 1 |
| `a6abb01` | V2-01 | Runner renamed (operational) | 2026-11-01 09:26:06 | — | — | 4 |
| `b8355eb` | V2-02 | Oracle milestones 4 per day | 2026-11-03 10:17:04 | 2026-11-03 12:01:14 | 1.7 h | 5 |
| `bbf4e22` | V2-03 | Night-time memory threshold (operational) | 2026-11-03 11:15:07 | — | — | 1 |
| `04408b5` | V2-04 | Oracle end milestone; server version pinned and checked per call | 2026-11-07 10:57:00 | — | — | 5 |
| `d76d70e` | V2-05 | Study-2 analysis plan | 2026-11-07 14:01:26 | — | — | 1 |
| `2a875a9` | V2-07 | Runtime correction; same-runtime pair; MD3R | 2026-11-07 15:03:29 | 2026-11-07 23:17:29 | 8.2 h | 7 |
| `1a9d2a8` | V2-06 | Control arm (Llama 3.1 8B, provider) | 2026-11-07 15:27:56 | 2026-11-09 09:29:50 | 42.0 h | 8 |
| `4dbaaeb` | V2-05 | Study-2 analysis scripts frozen before the first read | 2026-11-12 13:02:40 | — | — | 13 |
| `b099b11` | V2-08 | Study 3 plan and code | 2026-11-12 16:20:43 | 2026-11-12 16:21:54 | 71 s | 4 |
| `b2a3dd6` | V2-08 | Addendum: delegated Larger model dropped; hash b099b11 recorded | 2026-11-12 16:21:30 | 2026-11-12 16:21:54 | 24 s | 2 |
| `9da8209` | V2-08 | Study-3 analysis frozen (after the first call, before the first read) | 2026-11-12 16:23:12 | 2026-11-12 16:21:54 | -78 s (after) | 4 |
| `aea58ad` | V2-09 | Follow-up plan and code | 2026-11-13 10:10:56 | 2026-11-13 10:11:17 | 21 s | 7 |
| `21db032` | V2-09 | Hash aea58ad recorded; V2-09 analysis frozen | 2026-11-13 10:11:12 | 2026-11-13 10:11:17 | 5 s | 2 |
| `6091f5a` | Post hoc 3 | Plan of post hoc analysis 3 (token-F1 thresholds), before its script ran | 2026-11-14 14:25:19 | — | — | 1 |
| `e287aaf` | Post hoc 4 | Plan of post hoc analysis 4 (naive rule on both pair sets, detection side), before its script ran | 2026-11-14 17:45:30 | — | — | 1 |

Study 1 (plan committed 2026-09-16 16:32:29, first call 2026-09-16 23:10:58) is released under tag `tse-v1.0`,
whose public history starts on 2026-09-23, after its measurements.
