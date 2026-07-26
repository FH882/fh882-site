# -*- coding: utf-8 -*-
"""Dump each exam's 60 parsed question texts into one readable .txt file
for manual one-line summary writing (Phase 3)."""
import json, os

SCRATCH = r"C:\Users\haya1\AppData\Local\Temp\claude\C--Users-haya1-brain\c38bab3f-803e-4c5b-b5ed-c48ef1a3b8a0\scratchpad"
PARSED_DIR = os.path.join(SCRATCH, "parsed")
OUT_DIR = os.path.join(SCRATCH, "dump")
os.makedirs(OUT_DIR, exist_ok=True)

files = sorted(f for f in os.listdir(PARSED_DIR) if f.endswith(".json"))
for fn in files:
    examkey = fn[:-5]
    with open(os.path.join(PARSED_DIR, fn), encoding="utf-8") as f:
        d = json.load(f)
    lines = []
    for q in d["questions"]:
        lines.append(f"==Q{q['num']}[{q['subject']}]==")
        txt = q["text"][:420] if q["text"] else "(OCR抽出失敗)"
        lines.append(txt)
    with open(os.path.join(OUT_DIR, f"{examkey}.txt"), "w", encoding="utf-8") as out:
        out.write("\n".join(lines))
print(f"Dumped {len(files)} exams to {OUT_DIR}")
