# -*- coding: utf-8 -*-
"""Phase 3: merge parsed questions + difficulty + summaries + dictionary-based
term/subtopic matching into the final data/*.json files consumed by index.html.

Term/number frequency counts are script-computed (deterministic) against the
parsed OCR text; only the 1-line summaries are hand-written (may be partial —
missing ones are left null and the UI shows a placeholder).
"""
import json, os, re
from collections import defaultdict

SCRATCH = r"C:\Users\haya1\AppData\Local\Temp\claude\C--Users-haya1-brain\c38bab3f-803e-4c5b-b5ed-c48ef1a3b8a0\scratchpad"
REPO = r"C:\Users\haya1\brain\20_Projects\fh882-site"
TOOLS = os.path.join(REPO, "tools")
DATA_DIR = os.path.join(REPO, "data")
PARSED_DIR = os.path.join(SCRATCH, "parsed")

with open(os.path.join(TOOLS, "dictionaries.json"), encoding="utf-8") as f:
    DICT = json.load(f)
with open(os.path.join(SCRATCH, "difficulty.json"), encoding="utf-8") as f:
    DIFF = json.load(f)
with open(os.path.join(SCRATCH, "summaries.json"), encoding="utf-8") as f:
    SUMM = json.load(f)
with open(os.path.join(SCRATCH, "numbers_raw.json"), encoding="utf-8") as f:
    NUMBERS_RAW = json.load(f)  # curated: [{subject,value,meaning}]

SUBJECTS = DICT["subjects"]
SUBTOPIC_DEFS = DICT["subtopics"]
TERM_DEFS = DICT["terms"]
DIFF_RANK = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}

CALC_RE = re.compile(r"計算|求めよ|いくらか")

def keywords_for(name):
    m = re.search(r"[（(](.*?)[）)]", name)
    base = re.sub(r"[（(].*?[）)]", "", name).strip()
    kws = [base] if base else []
    if m:
        kws += [k for k in re.split(r"[・･、,]", m.group(1)) if k]
    return [k for k in kws if len(k) >= 2]

subtopic_state = {}
for subj, items in SUBTOPIC_DEFS.items():
    subtopic_state[subj] = []
    for t in items:
        subtopic_state[subj].append({
            "id": t["id"], "name": t["name"],
            "keywords": keywords_for(t["name"]),
            "matrix": defaultdict(list),
        })

term_state = {}  # (subj, term) -> {count, exams:[]}

questions_out = []
files = sorted(f for f in os.listdir(PARSED_DIR) if f.endswith(".json"))
for fn in files:
    examkey = fn[:-5]
    year_s, month_s = examkey.split("_")
    year, month = int(year_s), int(month_s)
    with open(os.path.join(PARSED_DIR, fn), encoding="utf-8") as f:
        pdata = json.load(f)
    diff_map = DIFF.get(examkey, {})
    summ_map = SUMM.get(examkey, {})
    for q in pdata["questions"]:
        num = q["num"]; subj = q["subject"]; text = q["text"] or ""
        d = diff_map.get(str(num))
        if d == "-" or d is None:
            d = None
        summary = summ_map.get(str(num))
        calc = bool(CALC_RE.search(text))

        matched_terms = []
        for term in TERM_DEFS.get(subj, []):
            if term and term in text:
                matched_terms.append(term)
                key = (subj, term)
                st = term_state.setdefault(key, {"count": 0, "exams": []})
                st["count"] += 1
                st["exams"].append(f"{examkey}-{num}")

        matched_topics = []
        for t in subtopic_state[subj]:
            if any(kw in text for kw in t["keywords"]):
                matched_topics.append(t["id"])
                t["matrix"][examkey].append(num)

        questions_out.append({
            "exam": examkey, "year": year, "month": month, "num": num,
            "subject": subj, "difficulty": d, "calc": calc,
            "summary": summary, "terms": matched_terms, "topics": matched_topics,
        })

# ---------- terms.json ----------
terms_out = []
for (subj, term), st in term_state.items():
    terms_out.append({
        "subject": subj, "term": term, "count": st["count"],
        "exams": st["exams"], "note": "",
    })
terms_out.sort(key=lambda x: (-x["count"], x["subject"], x["term"]))

# ---------- subtopics.json ----------
subtopics_out = {}
for subj, items in subtopic_state.items():
    subtopics_out[subj] = [
        {"id": t["id"], "name": t["name"], "matrix": dict(t["matrix"])}
        for t in items
    ]

# ---------- numbers.json (curated list, exams filled by matching value string in text) ----------
text_by_qkey = {f"{q['exam']}-{q['num']}": None for q in questions_out}
# build quick lookup of text per question for number matching
text_lookup = {}
for fn in files:
    examkey = fn[:-5]
    with open(os.path.join(PARSED_DIR, fn), encoding="utf-8") as f:
        pdata = json.load(f)
    for q in pdata["questions"]:
        text_lookup[f"{examkey}-{q['num']}"] = q["text"] or ""

numbers_out = []
for n in NUMBERS_RAW:
    exams = [qk for qk, txt in text_lookup.items() if n["value"] in txt and txt]
    numbers_out.append({
        "subject": n["subject"], "value": n["value"], "meaning": n["meaning"],
        "exams": exams,
    })

# ---------- stats.json ----------
all_years = sorted({q["year"] for q in questions_out})
exam_keys = sorted({q["exam"] for q in questions_out})

subj_stats = []
for s in SUBJECTS:
    sid = s["id"]
    qs = [q for q in questions_out if q["subject"] == sid]
    diff_count = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
    for q in qs:
        if q["difficulty"]:
            diff_count[q["difficulty"]] += 1
    calc_count = sum(1 for q in qs if q["calc"])
    top_terms = [t["term"] for t in terms_out if t["subject"] == sid][:5]
    subj_stats.append({
        "id": sid, "name": s["name"], "count": len(qs),
        "difficulty": diff_count, "calcCount": calc_count,
        "calcRatio": round(calc_count / len(qs), 4) if qs else 0,
        "topTerms": top_terms,
    })

by_year = []
for ek in exam_keys:
    qs = [q for q in questions_out if q["exam"] == ek]
    by_year.append({"exam": ek, "year": qs[0]["year"], "month": qs[0]["month"], "count": len(qs)})

# priority scores per subtopic
priority = []
exam_order = {ek: i for i, ek in enumerate(exam_keys)}  # chronological index (files sorted -> not strictly chrono by name)
# build chronological order properly: sort by (year, month)
chron = sorted(exam_keys, key=lambda ek: (int(ek.split("_")[0]), int(ek.split("_")[1])))
chron_index = {ek: i for i, ek in enumerate(chron)}
last_index = len(chron) - 1

for subj, items in subtopics_out.items():
    for t in items:
        tagged_qnums = []
        for ek, nums in t["matrix"].items():
            for n in nums:
                tagged_qnums.append((ek, n))
        freq = len(tagged_qnums)
        if freq == 0:
            continue
        diffs = []
        last_seen = None
        for ek, n in tagged_qnums:
            match = next((q for q in questions_out if q["exam"] == ek and q["num"] == n), None)
            if match and match["difficulty"]:
                diffs.append(DIFF_RANK[match["difficulty"]])
            if last_seen is None or chron_index.get(ek, -1) > chron_index.get(last_seen, -1):
                last_seen = ek
        avg_diff = sum(diffs) / len(diffs) if diffs else None
        gap = last_index - chron_index.get(last_seen, last_index) if last_seen else last_index
        freq_norm = min(freq / 10.0, 1.0)
        diff_norm = ((avg_diff - 1) / 4.0) if avg_diff else 0.5
        gap_norm = min(gap / 10.0, 1.0)
        score = round(freq_norm * 0.4 + diff_norm * 0.3 + gap_norm * 0.3, 3)
        priority.append({
            "subject": subj, "topic": t["id"], "name": t["name"],
            "freq": freq, "avgDifficulty": round(avg_diff, 2) if avg_diff else None,
            "lastSeenExam": last_seen, "gapCount": gap, "score": score,
        })

meta = {
    "examCount": len(exam_keys), "totalQuestions": len(questions_out),
    "years": all_years,
}
stats_out = {"meta": meta, "subjects": subj_stats, "byYear": by_year, "priority": priority}

os.makedirs(DATA_DIR, exist_ok=True)
def dump(name, obj):
    with open(os.path.join(DATA_DIR, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))

dump("questions.json", questions_out)
dump("terms.json", terms_out)
dump("numbers.json", numbers_out)
dump("subtopics.json", subtopics_out)
dump("stats.json", stats_out)

print(f"questions={len(questions_out)} terms={len(terms_out)} numbers={len(numbers_out)} exams={len(exam_keys)}")
print("Wrote data/*.json")
