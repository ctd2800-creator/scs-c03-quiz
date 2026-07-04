"""Translate ALL_QUESTIONS explanations to Korean."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import translators as ts

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
CACHE = ROOT / "explanation_ko.json"

CHUNK = 1500
TRANSLATORS = ("bing", "google", "yandex")


def _translate_chunk(chunk: str) -> str:
    last_err: Exception | None = None
    for name in TRANSLATORS:
        try:
            return ts.translate_text(
                chunk,
                translator=name,
                from_language="en",
                to_language="ko",
            )
        except Exception as e:
            last_err = e
            time.sleep(1)
    if last_err:
        raise last_err
    raise RuntimeError("translate failed")


def load_questions() -> list[dict]:
    html = INDEX.read_text(encoding="utf-8")
    m = re.search(r"var ALL_QUESTIONS = \[(.*?)\n\];", html, re.S)
    body = m.group(1).rstrip().rstrip(",")
    return json.loads("[" + body + "]")


def save_questions(questions: list[dict]) -> None:
    html = INDEX.read_text(encoding="utf-8")
    lines = ["var ALL_QUESTIONS = ["]
    for q in questions:
        lines.append("  " + json.dumps(q, ensure_ascii=False) + ",")
    lines.append("];")
    new_arr = "\n".join(lines)
    html = re.sub(r"var ALL_QUESTIONS = \[.*?\n\];", new_arr, html, count=1, flags=re.S)
    INDEX.write_text(html, encoding="utf-8")


def needs_translation(text: str) -> bool:
    if not text.strip():
        return False
    kor = len(re.findall(r"[가-힣]", text))
    eng = len(re.findall(r"[A-Za-z]{3,}", text))
    return eng > 15 and kor < max(30, eng // 4)


def load_cache() -> dict[int, str]:
    if CACHE.exists():
        raw = json.loads(CACHE.read_text(encoding="utf-8"))
        return {int(k): v for k, v in raw.items()}
    return {}


def save_cache(cache: dict[int, str]) -> None:
    CACHE.write_text(
        json.dumps({str(k): v for k, v in sorted(cache.items())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _split_chunks(text: str) -> list[str]:
    if len(text) <= CHUNK:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK, len(text))
        if end < len(text):
            for sep in (". ", ".\n", "\n"):
                pos = text.rfind(sep, start, end)
                if pos > start + 200:
                    end = pos + len(sep)
                    break
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


def translate_text(text: str) -> str:
    text = text.strip()
    chunks = _split_chunks(text)
    out: list[str] = []
    for chunk in chunks:
        out.append(_translate_chunk(chunk))
        time.sleep(0.8)
    return " ".join(out)


def main():
    questions = load_questions()
    cache = load_cache()
    todo = [q for q in questions if needs_translation(q.get("explanation", "")) and q["id"] not in cache]
    print(f"translate targets: {len(todo)} (cached {len(cache)})", flush=True)

    failed: list[int] = []
    for n, q in enumerate(todo, 1):
        qid = q["id"]
        try:
            ko = translate_text(q["explanation"])
            cache[qid] = ko
            save_cache(cache)
            print(f"[{n}/{len(todo)}] id={qid} ok ({len(ko)} chars)", flush=True)
        except Exception as e:
            print(f"[{n}/{len(todo)}] id={qid} FAIL: {type(e).__name__}", flush=True)
            failed.append(qid)
        time.sleep(1.2)

    if failed:
        print(f"failed ids ({len(failed)}): {failed}", flush=True)

    applied = 0
    for q in questions:
        if q["id"] in cache and cache[q["id"]]:
            q["explanation"] = cache[q["id"]]
            applied += 1
    save_questions(questions)
    print(f"done: applied {applied} -> {INDEX}", flush=True)


if __name__ == "__main__":
    main()
