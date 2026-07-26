# -*- coding: utf-8 -*-
"""Phase 2: split OCR'd page text into per-question chunks, assign subject.

Reads raw_ocr/{examkey}.json (produced by extract_ocr.ps1) and writes
parsed/{examkey}.json with one entry per question 1..60:
  { num, subject, text, ok }
`ok` is False when the question marker could not be reliably located in the
OCR text (subject assignment is still 100% correct either way, since it is
derived purely from the question number, not from OCR).
"""
import json, re, sys, os

SCRATCH = r"C:\Users\haya1\AppData\Local\Temp\claude\C--Users-haya1-brain\c38bab3f-803e-4c5b-b5ed-c48ef1a3b8a0\scratchpad"
RAW_DIR = os.path.join(SCRATCH, "raw_ocr")
OUT_DIR = os.path.join(SCRATCH, "parsed")
os.makedirs(OUT_DIR, exist_ok=True)

MARKER = re.compile(r"問題(\d{1,2})")

def subject_for(num):
    if num <= 10: return "L"
    if num <= 20: return "R"
    if num <= 30: return "F"
    if num <= 40: return "T"
    if num <= 50: return "E"
    return "S"

def parse_exam(examkey, data):
    ans = set(data.get("answerPages", []))
    body_pages = sorted([p for p in data["pages"] if p["page"] not in ans], key=lambda p: p["page"])
    full = "".join(re.sub(r"\s+", "", p["text"]) for p in body_pages)

    matches = list(MARKER.finditer(full))

    # Sequential guard: question numbers must appear as 1,2,3,...,60 in order.
    # A greedy \d{1,2} can over-capture a stray following digit (e.g. "問題6" + "4..."
    # read as "問題64"); when only the first digit matches the expected number,
    # treat the second digit as belonging to the question body instead.
    # A single missed marker must not cascade into "everything after is missing":
    # if a match's number is a bit ahead of `expected`, resync by treating the
    # gap as missing and jumping forward, rather than waiting forever.
    TOLERANCE = 15
    marker_starts = {}
    expected = 1
    for m in matches:
        if expected > 60:
            break
        cap = m.group(1)
        candidates = [int(cap)]
        if len(cap) == 2:
            candidates.append(int(cap[0]))
        # pick the candidate closest to (and >=) expected, within tolerance
        best = None
        for c in candidates:
            if expected <= c <= expected + TOLERANCE:
                if best is None or c < best:
                    best = c
        if best is not None:
            marker_starts[best] = m.start()
            expected = best + 1

    questions = {}
    accepted_nums = sorted(marker_starts.keys())
    for idx, num in enumerate(accepted_nums):
        # body starts right after the marker digits actually consumed
        m_start = marker_starts[num]
        # find this match's end (re-locate corresponding regex match at m_start)
        mm = MARKER.match(full, m_start)
        cap = mm.group(1)
        if int(cap) == num:
            body_start = mm.end()
        else:
            body_start = mm.end() - 1  # only first digit belonged to number
        body_end = marker_starts[accepted_nums[idx + 1]] if idx + 1 < len(accepted_nums) else len(full)
        text = full[body_start:max(body_start, body_end)]
        questions[num] = text

    final = []
    missing = []
    for n in range(1, 61):
        if n in questions:
            final.append({"num": n, "subject": subject_for(n), "text": questions[n], "ok": True})
        else:
            final.append({"num": n, "subject": subject_for(n), "text": "", "ok": False})
            missing.append(n)
    return final, missing

def main():
    files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".json"))
    total_missing = 0
    for fn in files:
        examkey = fn[:-5]
        with open(os.path.join(RAW_DIR, fn), encoding="utf-8") as f:
            data = json.load(f)
        final, missing = parse_exam(examkey, data)
        with open(os.path.join(OUT_DIR, examkey + ".json"), "w", encoding="utf-8") as f:
            json.dump({"examkey": examkey, "questions": final, "missing": missing}, f, ensure_ascii=False)
        total_missing += len(missing)
        print(f"{examkey}: missing={missing}")
    print(f"TOTAL exams={len(files)} total_missing_questions={total_missing}")

if __name__ == "__main__":
    main()
