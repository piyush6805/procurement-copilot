# Demo runbook

Start with `python run_local.py` and open http://127.0.0.1:8501.

1. **Routine request:** REQ-1010, SignFlow Training Pack. Show $950, available Finance budget, current vendor assessment and Manager approval. Explain that training is a distinct service scope.
2. **Sensitive request:** REQ-1005, ProspectPilot. Show the $4,000 Sales budget shortfall, customer PII, new vendor, outside-region storage and Finance/Security/Privacy/Legal routing. An existing approved vendor would not remove use-case review requirements.
3. **Evidence failure:** REQ-1009, NimbusAI Contract Reviewer. The mock API intentionally returns 503. Show unavailable evidence, Security/Legal/Finance reviews, and the human next step; do not infer vendor safety.
4. **Prompt injection:** REQ-1006. Show missing cost/users/data access, the embedded CFO-approval instruction, and clarification rather than approval.
5. Open **Human handoff**, download the full evidence packet, and record a reviewer note. Explain that the local event does not constitute approval.
6. Open **Run details** and compare normal two-call single against three-call staged behavior. Use `evals/results/summary.json` for measured aggregate results, not a guessed latency claim.

Do not rerun paid cases unnecessarily. The tracked budget applies across development, evaluation and UI.
