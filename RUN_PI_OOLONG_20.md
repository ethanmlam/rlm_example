# Run Pi on the 20 Largest Oolong Tasks

This is the direct handoff path for a coding agent to reproduce the 20-task Pi evaluation.

## What This Runs

- Dataset: `oolongbench/oolong-synth`
- Split: `validation`
- Subset: `trec_coarse`
- Selection: 20 largest rows by `context_window_text` length
- Pi skill: `recursive-decomposition/skills/recursive-decomposition`
- Pi model: `openrouter/qwen/qwen3.6-35b-a3b`

The generated eval directory is `oolong-pairs/data/pi_eval_20/`.

## 1. Clone and Initialize

From a fresh checkout of this repo:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

If `oolong-pairs/` is missing or the submodule checkout fails, clone it directly:

```bash
git clone https://github.com/zircote/oolong-pairs.git oolong-pairs
```

## 2. Install Oolong-Pairs

```bash
cd oolong-pairs
python3 -m venv .venv
.venv/bin/pip install -e .
cd ..
```

This installs the dataset dependencies used by the materialization script.

## 3. Materialize the 20-Task Eval

```bash
oolong-pairs/.venv/bin/python scripts/materialize_pi_eval_20.py
```

This writes:

- `oolong-pairs/data/pi_eval_20/contexts/context_window_22.txt`
- `oolong-pairs/data/pi_eval_20/questions.json`
- `oolong-pairs/data/pi_eval_20/instructions.md`
- `oolong-pairs/data/pi_eval_20/gold/summary.json`

Do not let Pi read `gold/summary.json`. It is only for scoring after Pi has written `pi_results.json`.

## 4. Run Pi in RPC Mode

Pi must already be configured with an OpenRouter API key.

```bash
cd oolong-pairs
pi --mode rpc \
  --provider openrouter \
  --model qwen/qwen3.6-35b-a3b \
  --thinking off \
  --skill ../recursive-decomposition/skills/recursive-decomposition \
  --tools read,bash,grep,find,ls,write \
  --approve \
  --name "pi-oolong-largest20"
```

Send this JSON-RPC prompt:

```json
{"id":"run-largest20","type":"prompt","message":"/skill:recursive-decomposition Follow data/pi_eval_20/instructions.md. Run all 20 tasks and write data/pi_eval_20/pi_results.json. Use chunk_summaries.jsonl, finish with caveats, and do not read gold/summary.json."}
```

Expected Pi outputs:

- `oolong-pairs/data/pi_eval_20/chunk_summaries.jsonl`
- `oolong-pairs/data/pi_eval_20/pi_results.json`

If Pi starts reading `gold/summary.json`, stop the run and restart from a clean eval directory.

## 5. Score After Pi Finishes

From the repo root:

```bash
python3 scripts/score_pi_eval_20.py \
  --pred oolong-pairs/data/pi_eval_20/pi_results.json \
  --gold oolong-pairs/data/pi_eval_20/gold/summary.json \
  --out oolong-pairs/data/pi_eval_20/pi_results_score.json
```

The scorer normalizes answer prefixes such as `Label:`, `User:`, and `Answer:`. For comparison tasks it scores the relation phrase: `more common than`, `less common than`, or `same frequency as`.

## Reference Artifacts

The committed `artifacts/pi_eval_20/` directory contains a previous run's lightweight outputs:

- `questions.json`
- `instructions.md`
- `chunk_summaries_isolated.jsonl`
- `pi_generated_reducer.py`
- `pi_results.json`
- `pi_results_score.json`

Those artifacts are evidence and examples, not a replacement for regenerating the 9.5 MB context file.

## Known Caveat From Prior Run

The previous Pi run decomposed the context into chunks and generated a reducer, but it did not autonomously finish by writing `pi_results.json`. The final result was reduced locally from Pi-generated chunk summaries and scored `12/20`.

User-frequency answers were exact from parsed `User:` fields. Label-count answers were heuristic because the context includes question text, not explicit TREC labels.
