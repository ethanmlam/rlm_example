# Handoff: Pi + Recursive Decomposition Skill + Oolong-Pairs

This workspace sets up a Pi coding-agent run against the largest Oolong synthetic benchmark examples using the local recursive-decomposition skill.

## Current Layout

Root:

- `recursive-decomposition/` - local skill/plugin source.
- `oolong-pairs/` - cloned from `https://github.com/zircote/oolong-pairs.git`.
- `oolong-pairs/data/pi_eval/` - clean task inputs and Pi output from this experiment.
- `artifacts/pi_eval_20/` - committed lightweight artifacts from the later 20-task Pi/Oolong run.
- `.env` - local secret file. Do not read, copy, commit, or share.

The original `oolong/` and `rlm/` submodules are not needed for this Pi-only test. The only submodule kept in `.gitmodules` is `oolong-pairs`.

## Prerequisites

- `pi` CLI installed.
- `OPENROUTER_API_KEY` configured for Pi or available in the shell.
- Python `>=3.11`.
- Network access for PyPI and Hugging Face on first setup.

The successful local setup used:

```bash
/opt/homebrew/bin/python3.13 --version
# Python 3.13.11
```

## Fresh Setup Commands

From the workspace root:

```bash
git clone https://github.com/zircote/oolong-pairs.git oolong-pairs
cd oolong-pairs
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/oolong-pairs stats --dataset trec_coarse
```

If `/opt/homebrew/bin/python3.13` does not exist, use any Python `>=3.11`.

The stats command downloads/caches `oolongbench/oolong-synth` from Hugging Face. It may warn about unauthenticated HF requests.

## Materialize Largest 5 Tasks

Run from `oolong-pairs/`:

```bash
PYTHONPATH=src .venv/bin/python -u - <<'PY'
import json
from pathlib import Path
from datasets import load_dataset

out = Path('data/largest5_tasks')
out.mkdir(parents=True, exist_ok=True)
ds = load_dataset('oolongbench/oolong-synth', split='validation')
rows = []
for idx, row in enumerate(ds):
    if row.get('dataset') != 'trec_coarse':
        continue
    rows.append((len(row.get('context_window_text', '')), idx, row))

selected = sorted(rows, key=lambda x: (x[0], x[1]), reverse=True)[:5]
summary = []
for rank, (length, idx, row) in enumerate(selected, 1):
    task_id = str(row.get('id', idx))
    context_path = out / f'{rank:02d}_{task_id}_context.txt'
    meta_path = out / f'{rank:02d}_{task_id}_meta.json'
    context_path.write_text(row.get('context_window_text', ''), encoding='utf-8')
    meta = {
        'rank': rank,
        'dataset_index': idx,
        'id': task_id,
        'dataset': row.get('dataset'),
        'context_window_id': row.get('context_window_id'),
        'context_length': length,
        'question': row.get('question'),
        'answer': str(row.get('answer', '')).strip('[]'),
        'answer_type': row.get('answer_type'),
        'task': row.get('task'),
        'task_group': row.get('task_group'),
        'context_file': str(context_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    summary.append(meta)

(out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
PY
```

Important: `data/largest5_tasks/summary.json` contains gold answers. Do not let Pi read it during evaluation.

## Build Clean Pi Input

The five largest examples all share the same context window. Create a clean input directory without gold answers:

```bash
mkdir -p data/pi_eval
ln -f data/largest5_tasks/01_22000270_context.txt data/pi_eval/context.txt
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path

summary = json.loads(Path('data/largest5_tasks/summary.json').read_text())
questions = [
    {
        'rank': item['rank'],
        'id': item['id'],
        'question': item['question'],
        'answer_type': item['answer_type'],
        'task': item['task'],
    }
    for item in summary
]
Path('data/pi_eval/questions.json').write_text(json.dumps(questions, indent=2), encoding='utf-8')
PY
```

Create `data/pi_eval/instructions.md`:

```markdown
Use the recursive-decomposition skill to answer the five Oolong questions.

Allowed inputs:
- data/pi_eval/context.txt
- data/pi_eval/questions.json

Do not read:
- .env
- data/largest5_tasks/*
- data/*.db
- Hugging Face cache files
- any file outside data/pi_eval unless needed to inspect the skill itself

The context is too large to load wholesale. First map its size and line count, then inspect only small header/tail samples. Use explicit decomposition: split or stream fixed line ranges, compute per-chunk aggregates independently, write per-chunk summaries to data/pi_eval/chunk_summaries.jsonl, then reduce those summaries into data/pi_eval/pi_results.json.

Write results to data/pi_eval/pi_results.json:

{
  "answers": [
    {
      "id": "...",
      "answer": "...",
      "method": "...",
      "confidence": "high|medium|low"
    }
  ],
  "notes": "..."
}

Do not modify files outside data/pi_eval.
```

The explicit `chunk_summaries.jsonl` requirement matters. In the first run, Pi used Python over the whole file directly, which was external-data processing but not true decomposition.

## Run Pi RPC

From `oolong-pairs/`:

```bash
pi --mode rpc \
  --provider openrouter \
  --model qwen/qwen3.6-35b-a3b \
  --thinking off \
  --skill ../recursive-decomposition/skills/recursive-decomposition \
  --tools read,bash,grep,find,ls,write \
  --approve \
  --name "pi-oolong-largest5"
```

Verify via RPC:

```json
{"id":"state-1","type":"get_state"}
{"id":"commands-1","type":"get_commands"}
```

Send prompt:

```json
{"id":"run-largest5","type":"prompt","message":"/skill:recursive-decomposition Follow data/pi_eval/instructions.md. Run the five tasks and write data/pi_eval/pi_results.json."}
```

If using a PTY, keep JSON-RPC lines short. Long JSON prompt lines can be truncated or ignored.

## Prior Run Results

Pi run:

- Provider/model: `openrouter/qwen/qwen3.6-35b-a3b`
- Thinking: `off`
- Skill registered: `skill:recursive-decomposition`
- Output file: `oolong-pairs/data/pi_eval/pi_results.json`

Predictions vs gold:

```text
22000270  pred: Label: abbreviation  gold: location   wrong
22000269  pred: Label: entity        gold: entity     correct
22000268  pred: User: 89348          gold: 89348      correct
22000267  pred: User: 78832          gold: 78832      correct
22000266  pred: Answer: 45941        gold: 23477      wrong
```

Observed behavior:

- Pi did not load the whole 9.5 MB file into the model prompt.
- Pi used shell/Python over `data/pi_eval/context.txt`.
- Pi did not perform true recursive decomposition; it made a direct whole-file Python pass with a heuristic classifier.
- The user/frequency tasks worked.
- The label tasks failed because labels are not explicit in the context and the heuristic classifier was inaccurate.

## Recommended Next Experiment

Force a visible map/reduce run:

1. Split `context.txt` into chunks, e.g. 5,000 data lines each.
2. For each chunk, produce a JSON object with:
   - line range
   - user frequency counts
   - user `94127` instances and inferred labels
   - global inferred label counts
   - confidence/ambiguous examples
3. Save one JSON object per line to `data/pi_eval/chunk_summaries.jsonl`.
4. Reduce `chunk_summaries.jsonl` into `pi_results.json`.
5. Compare against `data/largest5_tasks/summary.json` only after Pi finishes.

Expected gold for the five tasks:

```text
22000270 location
22000269 entity
22000268 89348
22000267 78832
22000266 23477
```

## Largest 20 Task Run

The later 20-task run used the same `trec_coarse` context window and wrote lightweight, committed artifacts under `artifacts/pi_eval_20/`:

- `questions.json` - the 20 selected tasks without gold answers.
- `instructions.md` - the prompt/instructions used for the decomposition run.
- `chunk_summaries_isolated.jsonl` - isolated chunk summaries from Pi-generated reduction.
- `pi_generated_reducer.py` - reducer script generated during the Pi run.
- `pi_results.json` - final reduced answers.
- `pi_results_score.json` - local score against gold after the candidate was written.

Score with answer-type-aware normalization: `12/20`.

Important caveat: Pi decomposed the context into chunks and generated the reducer, but it did not autonomously finish by writing `pi_results.json`. The final result file was reduced locally from the Pi-generated chunk summary. User-frequency answers were exact from parsed `User:` fields; label-count answers were heuristic because the context includes question text, not explicit TREC labels.

## Safety Notes

- Do not let agents read `.env`.
- Do not send `.env` or Pi session logs to anyone. A prior smoke test accidentally ran `cat .env` and exposed the OpenRouter key in a Pi session log.
- Do not include `data/largest5_tasks/*_meta.json` or `summary.json` in model-visible prompts before evaluation; they contain gold answers.
- Close Pi RPC with Ctrl-C after the run if pending messages remain queued.
