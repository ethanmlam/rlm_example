Use the recursive-decomposition skill to answer the 20 Oolong questions.

Allowed inputs:
- data/pi_eval_20/questions.json
- data/pi_eval_20/contexts/*.txt

Do not read:
- .env
- data/pi_eval_20/gold/*
- data/*.db
- Hugging Face cache files
- files outside data/pi_eval_20 unless needed to inspect the skill itself

The contexts are too large to load wholesale. First map file sizes and line counts, then inspect only small header/tail samples. Use explicit decomposition: split or stream fixed line ranges, compute per-chunk aggregates independently, write per-chunk summaries to data/pi_eval_20/chunk_summaries.jsonl, then reduce those summaries into data/pi_eval_20/pi_results.json.

Required decomposition evidence:
- Do not solve the task with one whole-file Python pass that directly writes final answers.
- Process the context as fixed chunks, such as 5,000 data lines per chunk.
- Write one JSON object per chunk to data/pi_eval_20/chunk_summaries.jsonl before producing final answers.
- Final answers must be derived from data/pi_eval_20/chunk_summaries.jsonl, not by re-reading the whole context.
- Include the number of chunks, chunk size, and reduction method in the "notes" field of data/pi_eval_20/pi_results.json.

Write data/pi_eval_20/pi_results.json with this schema:
{"answers":[{"id":"...","answer":"...","method":"...","confidence":"high|medium|low"}],"notes":"..."}

Do not modify files outside data/pi_eval_20.
