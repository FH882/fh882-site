# -*- coding: utf-8 -*-
"""Parse the hand-transcribed difficulty_raw.txt (N+Letter tokens per exam,
verified against the answer-table page images) into difficulty.json.
Validates: exactly 60 tokens per exam, numbers 1..60 each exactly once,
letters in {A,B,C,D,E,-} ('-' = not yet published, e.g. 2026_5).
"""
import json, re, os

SCRATCH = r"C:\Users\haya1\AppData\Local\Temp\claude\C--Users-haya1-brain\c38bab3f-803e-4c5b-b5ed-c48ef1a3b8a0\scratchpad"
SRC = os.path.join(SCRATCH, "difficulty_raw.txt")
OUT = os.path.join(SCRATCH, "difficulty.json")

TOKEN = re.compile(r"(\d{1,2})([A-E-])")

result = {}
errors = []

with open(SRC, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        examkey, rest = line.split(":", 1)
        examkey = examkey.strip()
        tokens = TOKEN.findall(rest)
        seen = {}
        for num_s, letter in tokens:
            num = int(num_s)
            if num in seen:
                errors.append(f"{examkey}: duplicate q{num}")
            seen[num] = letter
        missing = [n for n in range(1, 61) if n not in seen]
        if missing:
            errors.append(f"{examkey}: missing {missing}")
        if len(seen) != 60:
            errors.append(f"{examkey}: total={len(seen)} (expected 60)")
        result[examkey] = {str(n): seen.get(n, None) for n in range(1, 61)}

print(f"Parsed {len(result)} exams")
if errors:
    print("ERRORS:")
    for e in errors:
        print(" -", e)
else:
    print("All exams: 60/60 questions, no duplicates, no gaps. VALIDATION PASSED.")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print(f"Wrote {OUT}")
