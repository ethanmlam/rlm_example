#!/usr/bin/env python3
"""Score Pi output for the 20-task Oolong eval."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


COMPARISON_PHRASES = ("more common than", "less common than", "same frequency as")


def strip_answer_prefix(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"^(Label|User|Answer)\s*:\s*", "", text, flags=re.IGNORECASE)
    return text.strip().strip('"').strip("'").strip()


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", strip_answer_prefix(value)).lower()


def normalize_comparison(value: object) -> str:
    text = normalize_text(value)
    for phrase in COMPARISON_PHRASES:
        if phrase in text:
            return phrase
    return text


def load_predictions(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["answers"] if isinstance(payload, dict) and "answers" in payload else payload
    return {str(row["id"]): row for row in rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred", type=Path, default=Path("oolong-pairs/data/pi_eval_20/pi_results.json"))
    parser.add_argument("--gold", type=Path, default=Path("oolong-pairs/data/pi_eval_20/gold/summary.json"))
    parser.add_argument("--out", type=Path, default=Path("oolong-pairs/data/pi_eval_20/pi_results_score.json"))
    args = parser.parse_args()

    predictions = load_predictions(args.pred)
    gold_rows = json.loads(args.gold.read_text(encoding="utf-8"))

    items = []
    correct = 0
    for gold in gold_rows:
        task_id = str(gold["id"])
        if task_id not in predictions:
            predicted = ""
            ok = False
        else:
            predicted_raw = predictions[task_id].get("answer", "")
            if gold.get("answer_type") == "ANSWER_TYPE.COMPARISON":
                predicted = normalize_comparison(predicted_raw)
                expected = normalize_comparison(gold.get("answer", ""))
            else:
                predicted = normalize_text(predicted_raw)
                expected = normalize_text(gold.get("answer", ""))
            ok = predicted == expected

        if task_id not in predictions:
            expected = normalize_comparison(gold.get("answer", "")) if gold.get("answer_type") == "ANSWER_TYPE.COMPARISON" else normalize_text(gold.get("answer", ""))

        correct += int(ok)
        items.append(
            {
                "id": task_id,
                "ok": ok,
                "prediction": predicted,
                "gold": expected,
            }
        )

    score = {
        "correct": correct,
        "total": len(items),
        "accuracy": correct / len(items) if items else 0,
        "items": items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")

    for item in items:
        status = "OK" if item["ok"] else "MISS"
        print(f"{item['id']}\t{status}\tpred={item['prediction']}\tgold={item['gold']}")
    print(f"accuracy\t{correct}/{len(items)}")
    print(f"wrote\t{args.out}")


if __name__ == "__main__":
    main()
