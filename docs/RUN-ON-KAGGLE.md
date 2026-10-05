# Running The Judgment Benchmark on Kaggle (the ~30-minute hands-on step)

Everything else is built. This is the only part that needs a Kaggle login + Model Proxy
quota. Follow top to bottom. Expect a few models to error or be endpoint-incompatible
(normal); we report that honestly and exclude it from scoring.

## 0. One-time setup
```bash
# A recent Kaggle CLI with the Benchmarks subcommands is required (PyPI `kaggle` does NOT
# have `kaggle b`). Install the official CLI from source into a Python 3.11+ env:
pip install "git+https://github.com/Kaggle/kaggle-cli.git" kaggle-benchmarks pandas

# Auth: create an API token at https://www.kaggle.com/settings (API section),
# then either export KAGGLE_API_TOKEN=KGAT_... or save it to ~/.kaggle/access_token.
# Your account must be phone-verified to mint a Model Proxy token.

git clone https://github.com/simplynadaf/judgment-benchmark.git
cd judgment-benchmark

kaggle b init -y            # fetches Model Proxy creds, writes .env + example
kaggle b t models           # list the available model slugs for the lineup
```

## 1. Validate locally before pushing
```bash
set -a; source .env; set +a
python kaggle/task.py        # should run and produce *.run.json + judgment_verdicts.json
ls -1 *.run.json             # confirm run files exist
```
If `python kaggle/task.py` fails with an auth error, run `kaggle b auth -y` (the key is short-lived).

## 2. Push the task
```bash
kaggle b t push judgment -f kaggle/task.py --wait
```

## 3. Run against the model lineup (3x each for run-to-run stability)
Run each model with `-m`, repeated. Use the slugs from `kaggle b t models`.
```bash
kaggle b t run judgment \
  -m claude-opus-5-default \
  -m claude-haiku-4-5-20251001 \
  -m gemini-3.1-pro-preview \
  -m gemini-3.5-flash \
  -m gemini-3.5-flash-lite \
  -m gpt-5.4-nano-2026-03-17 \
  -m gpt-oss-20b \
  --wait
# repeat the same run 2 more times to measure stability (median move per model)
```
Budget note: the Model Proxy reserves quota against `max_output_tokens`, so the task caps
it (see `MAX_OUTPUT_TOKENS` in `kaggle/task.py`) to avoid false "exceeds your available
quota" errors. Each full lineup is a few dollars; check `kaggle b quota`.

## 4. Check + download results
```bash
kaggle b t status judgment                 # per-model run status
kaggle b t download judgment -o ./results_final -f   # pull run outputs + verdicts
```
Each run writes `judgment_verdicts.json` (the auditable per-scenario record): arm, chosen
tools, solved, quadrant (discerning / cowboy / frozen_operator).

## 5. Build the leaderboard numbers + charts
```bash
# extract per-model balanced accuracy + archetypes from the downloaded verdicts into
# results/results.json + results/categories.json + results/incompatible.json, then:
make charts        # writes docs/charts/{leaderboard,arms,archetypes,category,coverage}.png
```

## 6. Publish the public benchmark (REQUIRED for a valid entry)
```bash
kaggle b t publish judgment     # makes the task + backing notebook public
```
Confirm it is public (HTTP 200 unauthenticated) and copy the URL. That link is MANDATORY
in the Dev.to post.

## 7. Send back / finalize
1. The output of `kaggle b t models` (lineup check).
2. `./results_final` (the real numbers + verdicts).
3. The public Kaggle benchmark URL.

With those, fill the article numbers + charts, drop in the link, and publish before
Oct 11, 11:59 PM PDT.
