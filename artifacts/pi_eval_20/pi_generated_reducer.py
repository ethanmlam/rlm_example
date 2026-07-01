#!/usr/bin/env python3
"""
Process context_window_22.txt in fixed 5000-line chunks with improved heuristic labeling.
"""
import json
import re
import sys
from collections import defaultdict

CONTEXT_FILE = "/private/tmp/pi_oolong_eval_20/contexts/context_window_22.txt"
CHUNK_SIZE = 5000
OUTPUT_FILE = "/private/tmp/pi_oolong_eval_20/chunk_summaries.jsonl"
LABELS = ["entity", "description and abstract concept", "human being", "location", "abbreviation", "numeric value"]

def parse_line(line):
    """Parse a line into (user_id, question) or None."""
    # Match pattern: Date: ... || User: XXXX || Instance: ...
    # User ID is between "User: " and " || Instance:"
    m = re.search(r'\|\|\s*User:\s*(\d+)\s*\|\|\s*Instance:\s*(.+)', line)
    if not m:
        return None
    return m.group(1), m.group(2).strip()

def classify(question):
    """Heuristic classification of a TREC question into one of 6 coarse labels."""
    q = question.strip()
    q_lower = q.lower()
    
    # Strip leading "What is", "What are", "Who was", etc. for pattern matching
    # but keep the original for keyword matching

    # === ABBREVIATION (first priority - very distinctive patterns) ===
    if any(kw in q_lower for kw in [
        "what does", "what do", "stand for", "abbreviat", "acronym"
    ]):
        # But not "what does it mean" which is description
        if "mean" not in q_lower and "definition" not in q_lower:
            return "abbreviation"
    
    # === NUMERIC VALUE ===
    if any(kw in q_lower for kw in [
        "how much", "how many", "how old", "how long", "how far",
        "what year", "what date", "what time", "what amount",
        "what percent", "what percentage", "how often",
        "how wide", "how tall", "how deep",
        "count of", "cost of", "price of", "population of",
        "distance", "weight", "speed", "rate", "budget",
        "how many states", "how many people", "how many",
    ]):
        return "numeric value"

    # === LOCATION ===
    if any(kw in q_lower for kw in [
        "where", "which country", "which city", "which state",
        "which place", "located in", "capital of", "city in",
        "state in", "country in", "region in", "continent",
        "born in", "from which", "native country",
        "world's leading", "worlds leading", "world leading",
        "leading supplier", "top producer", "top exporter",
        "which country is", "what country is the world",
        "what country is the worlds",
    ]):
        return "location"

    # === HUMAN BEING ===
    if any(kw in q_lower for kw in [
        "who was", "who is", "who wrote", "who directed",
        "who played", "who starred", "who created",
        "who developed", "who discovered", "who painted",
        "who composed", "who designed", "who built",
        "who founded", "who invented", "who led",
        "first president", "last king", "first queen",
        "who does", "who sings", "who performed",
        "who recorded", "who records",
    ]):
        return "human being"

    # === LABEL COUNT QUERIES ===
    # Questions asking "how many data points should be classified as label X"
    if "how many data points" in q_lower:
        if "entity" in q_lower:
            return "entity"
        elif "description" in q_lower or "abstract" in q_lower:
            return "description and abstract concept"
        elif "human being" in q_lower:
            return "human being"
        elif "location" in q_lower:
            return "location"
        elif "numeric" in q_lower:
            return "numeric value"
        elif "abbreviation" in q_lower:
            return "abbreviation"

    # === COMPARISON QUERIES ===
    # Questions asking which label is more/less common
    # These need label counts, not classification of the question itself
    # We'll handle these separately - they're about label frequencies

    # === DESCRIPTION AND ABSTRACT CONCEPT ===
    if any(kw in q_lower for kw in [
        "what is", "what is a", "what is the", "what kind of",
        "what type of", "what term", "what concept",
        "what is meant by", "describe", "definition of",
        "what causes", "what lead", "what makes",
        "what effect", "what reason", "what purpose",
        "what feature", "what was", "what are",
        "what film", "what book", "what song", "what movie",
        "what show", "what program", "what disease",
        "what condition", "what drug", "what remedy",
        "what treatment", "what method", "what approach",
        "what theory", "what hypothesis", "what phenomenon",
        "what's the best", "what's the most", "what's the largest",
        "what's the smallest", "what's the oldest",
        "what's the newest", "what's the fastest",
        "what's the slowest", "what's the highest",
        "what's the lowest", "what's the hottest",
        "what's the coldest", "what's the deepest",
        "what's the shallowest", "what's the tallest",
        "what's the shortest",
        "what requires", "what are the requirements",
        "what is the world's", "what is the worlds",
        "what does the", "what does it mean",
        "what is a common", "what is the most common",
        "what is the best selling", "what is the biggest",
        "what is the smallest", "what is the oldest",
        "what is the newest", "what is the fastest",
        "what is the slowest", "what is the highest",
        "what is the lowest", "what is the deepest",
        "what is the shallowest", "what is the most famous",
        "what is the most popular", "what is the top",
        "what is the number one", "what is the number two",
        "what is the worlds", "what is the world",
        "what does the letters", "what do the letters",
        "what is the abbreviation of the company name",
    ]):
        # But we need to exclude ones already caught by other categories
        # The question itself is asking for a description/definition
        return "description and abstract concept"

    # === ENTITY (catch-all for orgs, products, events, etc.) ===
    return "entity"


def process_chunk(lines):
    """Process a chunk of lines and return statistics."""
    user_counts = defaultdict(int)
    user_94127_labels = defaultdict(int)
    label_counts = defaultdict(int)
    total_instances = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        parsed = parse_line(line)
        if not parsed:
            continue
        user_id, question = parsed
        total_instances += 1
        user_counts[user_id] += 1

        label = classify(question)
        label_counts[label] += 1

        if user_id == "94127":
            user_94127_labels[label] += 1

    sorted_users = sorted(user_counts.items(), key=lambda x: -x[1])
    most_freq_user = sorted_users[0] if sorted_users else (None, 0)
    second_most_freq_user = sorted_users[1] if len(sorted_users) > 1 else (None, 0)

    return {
        "total_instances": total_instances,
        "user_counts": dict(user_counts),
        "label_counts": dict(label_counts),
        "user_94127_labels": dict(user_94127_labels),
        "most_freq_user": most_freq_user,
        "second_most_freq_user": second_most_freq_user,
        "sorted_user_counts": [(uid, cnt) for uid, cnt in sorted_users[:5]]
    }


def main():
    with open(CONTEXT_FILE, "r") as f:
        all_lines = f.readlines()

    total_lines = len(all_lines)
    num_chunks = (total_lines + CHUNK_SIZE - 1) // CHUNK_SIZE

    chunk_summaries = []
    global_user_counts = defaultdict(int)
    global_label_counts = defaultdict(int)
    global_94127_labels = defaultdict(int)
    grand_total = 0
    most_freq_user = (None, 0)
    second_most_freq_user = (None, 0)

    for i in range(num_chunks):
        start = i * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, total_lines)
        chunk_lines = all_lines[start:end]

        result = process_chunk(chunk_lines)
        summary = {
            "chunk_index": i,
            "start_line": start,
            "end_line": end,
            "chunk_size": len(chunk_lines),
            "total_instances": result["total_instances"],
            "label_counts": result["label_counts"],
            "user_94127_labels": result["user_94127_labels"],
            "most_freq_user": result["most_freq_user"],
            "second_most_freq_user": result["second_most_freq_user"],
            "sorted_top5": result["sorted_user_counts"],
            "user_counts_sample": dict(list(result["user_counts"].items())[:20])
        }

        for uid, cnt in result["user_counts"].items():
            global_user_counts[uid] += cnt
        for label, cnt in result["label_counts"].items():
            global_label_counts[label] += cnt
        for label, cnt in result["user_94127_labels"].items():
            global_94127_labels[label] += cnt
        grand_total += result["total_instances"]

        chunk_summaries.append(summary)
        print(f"Chunk {i}: {result['total_instances']} instances, labels={dict(result['label_counts'])}")

    sorted_global_users = sorted(global_user_counts.items(), key=lambda x: -x[1])
    final_most = sorted_global_users[0] if sorted_global_users else (None, 0)
    final_second = sorted_global_users[1] if len(sorted_global_users) > 1 else (None, 0)

    summary = {
        "chunk_count": num_chunks,
        "chunk_size": CHUNK_SIZE,
        "total_lines": total_lines,
        "grand_total_instances": grand_total,
        "global_label_counts": dict(global_label_counts),
        "global_user_94127_labels": dict(global_94127_labels),
        "most_freq_user": final_most,
        "second_most_freq_user": final_second,
        "top_5_users": [(uid, cnt) for uid, cnt in sorted_global_users[:5]],
        "top_20_users": [(uid, cnt) for uid, cnt in sorted_global_users[:20]]
    }

    with open(OUTPUT_FILE, "w") as f:
        for cs in chunk_summaries:
            f.write(json.dumps(cs) + "\n")
        f.write(json.dumps(summary) + "\n")

    print(f"\nTotal lines: {total_lines}")
    print(f"Total chunks: {num_chunks}")
    print(f"Grand total instances: {grand_total}")
    print(f"Global label counts: {dict(global_label_counts)}")
    print(f"User 94127 label counts: {dict(global_94127_labels)}")
    print(f"Most freq user: {final_most}")
    print(f"Second most freq user: {final_second}")
    print(f"Top 5 users: {sorted_global_users[:5]}")
    print(f"Wrote {num_chunks + 1} summaries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
