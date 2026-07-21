# skill-judger

LLM-based skills taxonomy classifier for UK retail bank job families. Reads a CSV of skills, judges each one against 10 job families using an LLM, and writes the results back out with a `yes`/`no` column per family.

## Requirements

- Python 3.9+
- [`uv`](https://docs.astral.sh/uv/) installed

## Setup

- Clone the repo and `cd` into it
- Install dependencies:
  ```bash
  uv sync
  ```
- Copy the env template and fill in your real credentials:
  ```bash
  cp .env.example .env
  ```
  - `CYBERARK_SERVICE_ACCOUNT` / `CYBERARK_PASSWORD` — your CyberArk credentials, used to fetch a JWT for the prod gateway
  - `GENAI_GATEWAY_JWT` — optional. If set, this overrides the yaml-based JWT URL lookup, useful for fast local testing
  - `OPENAI_API_KEY` — needed only for **testing mode** (see below)
- Copy the model config template and fill in your real gateway/model values:
  ```bash
  cp config/model_config.local.yaml.example config/model_config.local.yaml
  ```
  - This file is gitignored. It's merged on top of `config/model_config.yaml` (which stays a safe, placeholder-only template in git) — real values never need to be shared or committed.
  - Fill in `auth.jwt_url` and your real `models` list (id, name, url, etc.)

## Running it

- Run the tool:
  ```bash
  uv run python src/skill_judger/orchestrator.py
  ```
- You'll be prompted: `Environment (testing/prod):`
  - **`testing`** — bypasses your internal gateway entirely and calls OpenAI's `gpt-4o` directly. Useful for fast iteration without needing real gateway credentials. Output: `data/skills_graded.csv`
  - **`prod`** — authenticates via CyberArk → JWT, then calls your real GenAI Gateway with per-model rate limiting and rotation across the configured endpoints. Output: `data/skills_graded_prod.csv`

## CSV validation

- `orchestrator.py` automatically checks `data/skills.csv` against `config/prompts/grade_rating_prompt.yaml`'s `user_template` **before every run** (both `testing` and `prod`) — if it fails, the run aborts before wasting any authentication or API calls
- The check reports:
  - The exact column names in your CSV (hidden characters like a UTF-8 BOM are shown, not silently swallowed)
  - Whether a BOM is present — this can silently turn a column named `skill_name` into `﻿skill_name`, which breaks the prompt template with a `KeyError` mid-run
  - Whether the file looks like it's using the wrong delimiter (e.g. tab-separated but named `.csv`)
  - Whether every field the prompt template needs (`{skill_name}`, `{description}`, etc.) actually exists as a column in your CSV
- On failure it tells you exactly what's missing and where to fix it — either rename your CSV's columns, or update `user_template` in the prompt YAML to match your CSV's real column names
- You can also run it standalone, any time, without starting a full run:
  ```bash
  uv run python src/skill_judger/validate_csv.py
  ```

## Input / output

- Input: `data/skills.csv`, with at minimum `skill_name` and `description` columns (this is gitignored — supply your own)
- Output: same rows, plus one `yes`/`no` column per job family defined in `config/prompts/grade_rating_prompt.yaml`

## If it stops partway through

- Every row is written to the output file as soon as it's graded — nothing is held in memory until the end
- If the run is interrupted (crash, killed, daily token budget reached), just run it again with the same command
- Already-graded rows are automatically skipped, so you only lose the one row that was in progress when it stopped — not the whole run

## Project structure

- `src/skill_judger/orchestrator.py` — entry point, prompts for environment, wires everything together
- `src/skill_judger/auth.py` — CyberArk → JWT auth flow for the prod gateway
- `src/skill_judger/config.py` — loads `model_config.yaml` merged with your local override
- `src/skill_judger/grader.py` — the generic grading loop (checkpointing, retry, response validation). Doesn't know anything about skills or job families specifically — reusable for other projects with a different prompt/CSV
- `src/skill_judger/rate_limiter.py` — per-model rate limiting and rotation for the prod gateway
- `src/skill_judger/prod_provider.py` — the real GenAI Gateway call
- `src/skill_judger/testing_provider.py` — the OpenAI call used only in testing mode. **Delete this file (and its hook in `orchestrator.py`) before a true production deployment** — it has no role there
- `src/skill_judger/validate_csv.py` — pre-flight check for column-name/BOM/delimiter mismatches between your CSV and the prompt template. Runs automatically before every `orchestrator.py` run; can also be run standalone
- `config/prompts/grade_rating_prompt.yaml` — the classifier prompt, plus `expected_keys` (the schema every response is validated against)
- `config/model_config.yaml` — tracked template (rate limits, HTTP settings, model list — all placeholders)
- `config/model_config.local.yaml` — your real values, gitignored, never shared

## Adapting this for a different project

- Write a new prompt YAML with your own `system_prompt`, `user_template`, and `expected_keys`
- Point `orchestrator.py`'s `PROMPT_PATH` / `INPUT_CSV` / `OUTPUT_CSV_*` at your new files
- `grader.py` and the rate limiter need no changes — they're generic
