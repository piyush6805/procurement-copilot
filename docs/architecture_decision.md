# Architecture decision: ship the single-agent baseline

**Decision:** ship Architecture A for this local procurement copilot; retain Architecture B as an evaluated alternative.

The customer needs a review-ready request with inspectable evidence, required approvals and an actionable next step. Agent count is useful only if it improves that outcome.

We compared both implementations on the same ten supplied requests, including six public cases, using `openai/gpt-4.1-mini` and identical tools, policy checks and output validation. Both passed 10/10 final cases with grounded evidence and human review preserved. Single averaged 5.76 seconds, two LLM calls and INR 1.9607 across the suite. Staged averaged 8.66 seconds, 3.1 calls and INR 3.4039. Both executed four tools per request. One staged case needed a schema/evidence repair, which is included rather than hidden.

The staged reviewer added latency and cost without an observed improvement in final correctness. Single also has fewer prompts and model boundaries to operate and diagnose. Therefore the extra reviewer is not justified by this evidence.

Safety comes from the shared code boundary: deterministic approval thresholds and budget checks, snapshot-based expiry, mandatory specialist routing, explicit unavailable/conflicting evidence, supported references and human-only final approval. Model output cannot remove required reviews, buy software or alter budgets. Request and vendor text remain untrusted data.

This is a small synthetic evaluation with one observation per architecture per case. It does not establish production reliability or statistical superiority. Shared guardrails intentionally reduce the architectures' differences, and source records themselves are not independently verified.

Reconsider staged if a broader customer evaluation shows that it catches material semantic mistakes or improves review completeness enough to justify its overhead. Before production, add authenticated reviewers, live source refresh, immutable audit storage and customer-owned approval integrations. See the CSV and traces for reproducible supporting evidence.
