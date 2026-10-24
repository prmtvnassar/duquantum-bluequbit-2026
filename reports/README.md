# Evidence and dated reviews

The [current workflow](../docs/workflow.md), [decision history](../docs/optimization-decisions.md), and [results audit](../docs/results.md) are the starting points for interpreting results. Reports in this directory were written at different campaign stages. Older narrative reviews can describe then-pending jobs or superseded score attributions; their dated findings remain available for provenance.

## Machine-readable evidence

- [Branch and submission inventory](audit/branch-score-inventory.json): audited refs, historical CSV versions, receipt claims, and row checks.
- [Campaign stop record](audit/campaign-stop.json): terminal status when new quantum work was halted.
- [Sample calibration](calibration_evidence.json) and [benchmarks](sample_benchmarks.json): measured sample costs, errors, and method choices.
- [G4 trend review](g4_partial_trend_review.json), [GPU pilot](gpu_matched_pilot.json), and [extrapolation rejection](extrapolation_rejection.json): numerical evidence behind selected and rejected refinements.
- [Repository cleanup record](repository_cleanup.json) and [audit directory](audit/): source preservation and branch sweep.

[Runs](../runs/README.md) contains the original job and event records; [submissions](../submissions/README.md) contains uploaded vectors, explanations, and feedback. A quote or estimate in a report is not a settled account charge or an observed submission score.
