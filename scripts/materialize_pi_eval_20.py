#!/usr/bin/env python3
"""Materialize the 20 largest Oolong trec_coarse tasks for the Pi eval."""

from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset


ROOT = Path(__file__).resolve().parents[1]
OOLONG_DIR = ROOT / "oolong-pairs"
OUT_DIR = OOLONG_DIR / "data" / "pi_eval_20"
CONTEXT_DIR = OUT_DIR / "contexts"
GOLD_DIR = OUT_DIR / "gold"
DATASET_NAME = "oolongbench/oolong-synth"
SPLIT = "validation"
DATASET_FILTER = "trec_coarse"
TASK_COUNT = 20


def clean_answer(value: object) -> str:
    text = str(value)
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return text.strip().strip("'").strip('"')


def write_instructions() -> None:
    instructions = """Use the recursive-decomposition skill to answer the 20 Oolong questions.

Allowed inputs:
- data/pi_eval_20/contexts/context_window_22.txt
- data/pi_eval_20/questions.json

Do not read:
- data/pi_eval_20/gold/*
- .env
- Hugging Face cache files
- any previous pi_eval directory
- any file outside data/pi_eval_20 unless needed to inspect the skill itself

The context is too large to load wholesale. Use explicit decomposition:
1. Map size and line count.
2. Split or stream fixed chunks, for example 5,000 data lines per chunk.
3. For each chunk, compute independent aggregates.
4. Write one JSON object per chunk to data/pi_eval_20/chunk_summaries.jsonl.
5. Reduce chunk_summaries.jsonl into data/pi_eval_20/pi_results.json.

Do not make a single whole-file answer pass without writing chunk summaries first.

Write results to data/pi_eval_20/pi_results.json:

{
  "answers": [
    {
      "id": "...",
      "answer": "...",
      "method": "...",
      "confidence": "high|medium|low"
    }
  ],
  "notes": "Include chunk count, chunk size, reduction method, and caveats."
}

Finish with caveats rather than reading gold or calibration data.
"""
    (OUT_DIR / "instructions.md").write_text(instructions, encoding="utf-8")


def main() -> None:
    if not OOLONG_DIR.exists():
        raise SystemExit("Missing oolong-pairs/. Run git submodule update --init --recursive first.")

    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(DATASET_NAME, split=SPLIT)
    rows = []
    for dataset_index, row in enumerate(dataset):
        if row.get("dataset") != DATASET_FILTER:
            continue
        context = row.get("context_window_text", "")
        rows.append((len(context), dataset_index, row))

    selected = sorted(rows, key=lambda item: (item[0], item[1]), reverse=True)[:TASK_COUNT]
    if len(selected) != TASK_COUNT:
        raise SystemExit(f"Expected {TASK_COUNT} rows, found {len(selected)}")

    questions = []
    gold = []
    written_contexts = set()

    for rank, (context_length, dataset_index, row) in enumerate(selected, 1):
        task_id = str(row.get("id", dataset_index))
        context_window_id = row.get("context_window_id")
        context_name = f"context_window_{context_window_id}.txt"
        context_path = CONTEXT_DIR / context_name

        if context_name not in written_contexts:
            context_path.write_text(row.get("context_window_text", ""), encoding="utf-8")
            written_contexts.add(context_name)

        base = {
            "rank": rank,
            "id": task_id,
            "dataset_index": dataset_index,
            "dataset": row.get("dataset"),
            "context_window_id": context_window_id,
            "context_file": f"data/pi_eval_20/contexts/{context_name}",
            "context_length": context_length,
            "question": row.get("question"),
            "answer_type": row.get("answer_type"),
            "task": row.get("task"),
            "task_group": row.get("task_group"),
        }
        questions.append(base)
        gold.append({**base, "answer": clean_answer(row.get("answer", ""))})

    (OUT_DIR / "questions.json").write_text(json.dumps(questions, indent=2) + "\n", encoding="utf-8")
    (GOLD_DIR / "summary.json").write_text(json.dumps(gold, indent=2) + "\n", encoding="utf-8")
    write_instructions()

    print(f"Wrote {len(questions)} questions to {OUT_DIR / 'questions.json'}")
    print(f"Wrote {len(written_contexts)} context file(s) to {CONTEXT_DIR}")
    print(f"Wrote held-back gold to {GOLD_DIR / 'summary.json'}")
    print(f"Wrote instructions to {OUT_DIR / 'instructions.md'}")


if __name__ == "__main__":
    main()
