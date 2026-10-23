# Adversarial scenarios and evidence

The versioned `make fixture` data is entirely fictional. It checks a short journey, not the quality of an AP or session. New scenarios should start from the seven success scenarios in `VISION.md` and ask how each claim could be false.

| Risk to falsify | Pre-integration test case | Required evidence |
| --- | --- | --- |
| Long memory / provenance | old promise, two conflicting sources, broken locators | answer with source and uncertainty; tested correction |
| AP / canon / proposal | source chapter contradicts the table; rejected idea | distinct states on screen and in queries |
| Late correction | attribution changed after preparation and publication | dependencies corrected; already-viewed publication flagged |
| Privacy | GM secret in several linked objects | negative tests for every player read/publication path |
| Branching / preparation | simulated players follow and then leave the AP | playable prep and durable consequences; editorial review |
| Foundry | scene edited between synchronizations | test on real v14 instance, conflict preview, no overwrite or duplicate |
| Transcription | two voices on one track and out-of-game chatter | uncertain speaker, no improper promotion to canon |
| Outage / spending cap | unavailable provider and cost at cap | access to preparations, rejected expense, idempotent resume |

For each milestone, record automated tests, integrated trial, visual inspection where relevant, real external environment, review of perceived quality, and limitations separately. Independent QA receives the vision, scenario, and product, then seeks counterexamples without adopting implementation assumptions. If no separate agent is available, run a second QA pass from this matrix after implementation.

Licensed PDFs, long excerpts, real transcripts, and raw audio remain in the private test environment. Public fixtures and reports contain only invented material or permitted references.
