# -*- coding: utf-8 -*-
"""Phase QA: validate data/*.json before deploy.
Checks: 60 questions/exam, difficulty in A-E or null, subject counts,
no duplicate exam-num, all term/number exam references resolve to real
questions, heatmap topic counts don't exceed subject totals.
"""
import json, os

DATA_DIR = r"C:\Users\haya1\brain\20_Projects\fh882-site\data"

def load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)

questions = load("questions.json")
terms = load("terms.json")
numbers = load("numbers.json")
subtopics = load("subtopics.json")
stats = load("stats.json")

errors = []
warnings = []

# 1. exam/question completeness
by_exam = {}
for q in questions:
    by_exam.setdefault(q["exam"], set()).add(q["num"])
for exam, nums in by_exam.items():
    if len(nums) != 60 or nums != set(range(1, 61)):
        errors.append(f"{exam}: has {len(nums)} unique question numbers (expected 60, gap-free)")

if len(by_exam) != 39:
    errors.append(f"exam count = {len(by_exam)} (expected 39)")

# 2. difficulty range
valid_diff = {"A", "B", "C", "D", "E", None}
bad_diff = [q for q in questions if q["difficulty"] not in valid_diff]
if bad_diff:
    errors.append(f"{len(bad_diff)} questions have invalid difficulty values")

# 3. subject distribution (each subject exactly 390 = 39*10)
subj_counts = {}
for q in questions:
    subj_counts[q["subject"]] = subj_counts.get(q["subject"], 0) + 1
for sid, c in subj_counts.items():
    if c != 390:
        errors.append(f"subject {sid}: {c} questions (expected 390)")

# 4. duplicate exam-num
seen = set()
for q in questions:
    key = (q["exam"], q["num"])
    if key in seen:
        errors.append(f"duplicate question: {key}")
    seen.add(key)

# 5. term/number exam references resolve
qkeys = {f"{q['exam']}-{q['num']}" for q in questions}
bad_term_refs = 0
for t in terms:
    for ex in t["exams"]:
        if ex not in qkeys:
            bad_term_refs += 1
if bad_term_refs:
    errors.append(f"{bad_term_refs} term exam-references do not resolve to real questions")

bad_num_refs = 0
for n in numbers:
    for ex in n["exams"]:
        if ex not in qkeys:
            bad_num_refs += 1
if bad_num_refs:
    errors.append(f"{bad_num_refs} number exam-references do not resolve to real questions")

# 6. heatmap topic counts don't exceed subject total questions
for subj, items in subtopics.items():
    subj_total = subj_counts.get(subj, 0)
    for t in items:
        topic_total = sum(len(v) for v in t["matrix"].values())
        if topic_total > subj_total:
            errors.append(f"topic {t['id']} count {topic_total} exceeds subject {subj} total {subj_total}")

# 7. summary coverage (informational, not a hard error)
with_summary = sum(1 for q in questions if q.get("summary"))
warnings.append(f"summary coverage: {with_summary}/{len(questions)} ({with_summary/len(questions)*100:.1f}%), remaining show placeholder in UI")

# 8. stats.meta sanity
if stats["meta"]["totalQuestions"] != len(questions):
    errors.append("stats.meta.totalQuestions mismatch")

print(f"Checked {len(questions)} questions across {len(by_exam)} exams.")
if errors:
    print(f"\n{len(errors)} ERROR(S):")
    for e in errors:
        print(" -", e)
else:
    print("\nAll hard checks PASSED (60/60 per exam, difficulty valid, subject counts=390, no dupes, all references resolve).")
for w in warnings:
    print("[info]", w)
