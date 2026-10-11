# Evaluation report

Final paired live evaluation, 11 October 2026. Model: `openai/gpt-4.1-mini`. All six public cases and four additional supplied requests were run through both architectures. One observation per case/architecture; architecture order alternated by case. Evaluation requested provider cache bypass.

| Metric | Single | Staged |
|---|---:|---:|
| Cases passing all checks | 10/10 | 10/10 |
| Completed live agent workflows | 10/10 | 10/10 |
| Correct recommendation label | 10/10 | 10/10 |
| Grounded evidence and supported references | 10/10 | 10/10 |
| Mean latency | 5.76s | 8.66s |
| Median latency | 5.66s | 8.49s |
| Mean LLM calls | 2.0 | 3.1 |
| Mean tool executions | 4.0 | 4.0 |
| Total final-suite cost | INR 1.9607 | INR 3.4039 |

All outputs preserved human review and met the provided public-case minimum checks. This does not mean every approval was completed; the app only identifies required reviews.

The staged REQ-1006 workflow needed one bounded JSON/evidence-validation repair; its four model calls are included in latency, token and cost metrics. Failures are not discarded or counted as live successes. The final suite followed two development passes, whose aggregate results are retained in `evals/development/`.

## How grading works

The comparator applies the original public minimum checks, an independently declared action oracle for supplied cases, supported model-reference validation, exact equality of displayed evidence with recorded tool-generated evidence, expected agent-stage completion and human-authority checks. Deterministic policy behavior is also covered by 59 automated tests. Recommendations are not hardcoded in the product; the oracle exists only in evaluation code.

REQ-1001 permits either Manager routing or existing-capacity review because utilization is not provided. A same-vendor training request is not a functional duplicate of a software license. These policy interpretations are documented before the final comparison.

Raw decisions and agent/tool traces are in `evals/results/traces/`. Machine-readable results are in `comparison.csv` and `summary.json`. Token and call metrics come from actual provider responses, not assumed architecture counts.

## FDE interpretation

Both architectures made the same acceptable routing choices on this small set. Single used fewer calls, took 33.4% less mean elapsed time and cost 42.4% less than staged. The reviewer did not demonstrate additional customer value here. Ship single with the shared deterministic controls and retain staged as a reproducible experiment.

No LLM-as-judge was used. Semantic quality is measured against these declared workflow labels, not a universal procurement oracle. One repeat, ten synthetic requests, provider timing variability and shared deterministic controls limit generalization. Grounding checks validate references and tool-generated facts; they do not independently establish that the source business records are true. Provider billing is estimated from reported token usage and catalog rates.

Development, probes, UI checks and all evaluation passes shared the INR 20 ledger. At final-suite completion the cumulative ledger was INR 15.4760; later UI demo calls may add to this local total.
