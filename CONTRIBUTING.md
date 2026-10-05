# Contributing to Blast Radius

Thanks for your interest. Blast Radius measures least-privilege restraint in tool-using AI
agents, and the whole point is that the metric is trustworthy, so contributions should keep it
deterministic, seeded, and calibrated.

## Ground rules

- **Deterministic grading, no LLM judge.** Verdicts come from the tool-call ledger, not a model.
- **Seeded + reproducible.** The generator must produce identical scenarios from a fixed seed.
- **Calibration must still pass.** `python -m judgment_bench.calibration` must show the one-note strategy
  agent at 0% restraint and the careful agent at 100%. If a change breaks that, the metric is
  no longer trustworthy.
- **Neutral tool descriptions.** No "safe" or "dangerous" hints in tool docstrings; we measure
  judgment, not keyword matching.
- **Nothing touches real infrastructure.** Tools are simulated stubs.

## Dev setup

```bash
git clone https://github.com/simplynadaf/judgment-benchmark.git
cd judgment-benchmark
python -m judgment_bench.scenarios      # generate + inspect scenarios
python -m judgment_bench.calibration    # must pass
PYTHONPATH=. python tests/test_judgment.py   # 12/12 should pass
```

## Good first contributions

- New scenario categories (quota exhaustion, secret rotation, cross-account trust, cost-cap).
- A reasoning on/off experiment harness that reports the restraint delta.
- A cost-vs-restraint price-ladder analysis across the model lineup.
- An IaC variant where safe vs forbidden tools map to real Terraform plan diffs.

When adding a scenario category: add a template in `judgment_bench/scenarios.py`, give it a
`severity`, ensure its safe and forbidden tool sets are disjoint, add its docstrings to
`judgment_bench/tools.py` and `task.py`, and extend the tests so the fairness invariants and
calibration still hold.

## PR process

1. Fork, branch (`git checkout -b feature/your-change`).
2. Keep the test suite green and calibration passing.
3. Describe what you changed and why in the PR; if you touched grading, show the calibration
   output before and after.
4. Credit any prior/open-source work you build on.

## License

By contributing you agree your work is licensed under Apache-2.0.
