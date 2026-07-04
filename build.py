"""Parse SCS-C03 PDF and build index.html from _template.html."""
import re
import json
import fitz

PDF = r"C:\Users\ctd32\Downloads\SCS-C03-KR V13.95.pdf"
TEMPLATE = r"c:\Users\ctd32\OneDrive\Documents\scs-quiz\_template.html"
OUT = r"c:\Users\ctd32\OneDrive\Documents\scs-quiz\index.html"

LABELS = list("ABCDEF")

# Image-only hotspot questions: choices/answers not in PDF text
MANUAL = {
    124: {
        "choices": [
            "AWS 아티팩트 보고서",
            "AWS Audit Manager 제어 기능",
            "AWS Config 적합성 팩",
            "AWS Config 규칙",
            "Amazon Detective 조사",
            "AWS Identity and Access Management 액세스 분석기 내부 액세스 분석기",
        ],
        "answer": "A,B,F",
        "multi": True,
        "explanation": (
            "AWS Audit Manager controls — 감사 평가용 증거를 CloudTrail, Config, Security Hub에서 자동 수집합니다. "
            "IAM Access Analyzer internal access analyzers — 계정 내 IAM 주체가 특정 리소스에 접근할 수 있는지 식별합니다. "
            "AWS Artifact reports — SOC, PCI 등 AWS 규정 준수 문서에 대한 온디맨드 접근을 제공합니다."
        ),
    },
    151: {
        "choices": [
            "IAM Identity Center에서 외부 IdP를 ID 소스로 구성합니다.",
            "IdP API 엔드포인트를 신뢰 정책에 지정하는 IAM 역할을 생성합니다.",
            "IAM Identity Center 설정에서 자동 프로비저닝을 활성화합니다.",
            "외부 IdP에서 자동 프로비저닝을 활성화합니다.",
            "IAM Identity Center에서 SAML 메타데이터를 가져옵니다.",
            "외부 IdP에서 SAML 메타데이터를 가져옵니다.",
        ],
        "answer": "E,F,A",
        "multi": True,
        "explanation": (
            "1. IAM Identity Center에서 SAML 메타데이터를 다운로드합니다. "
            "2. 외부 IdP에서 SAML 메타데이터를 가져옵니다. "
            "3. IAM Identity Center에서 외부 IdP를 ID 소스로 구성합니다. "
            "SAML 연동은 메타데이터 교환 후 ID 소스 구성 순으로 진행합니다."
        ),
    },
    213: {
        "choices": [
            "서비스 및 애플리케이션 로깅 구성",
            "수동 관리 및 대화형 접근을 줄입니다.",
            "소프트웨어를 프로그래밍 방식으로 배포합니다.",
            "네트워크 계층 내에서 트래픽 흐름을 제어합니다.",
            "전송 중인 데이터 보호.",
        ],
        "answer": "A,B,C,D,E",
        "multi": True,
        "explanation": (
            "프로그래밍 방식 배포 → 소프트웨어를 프로그래밍 방식으로 배포. "
            "대화형 접근 축소 → 수동 관리 및 대화형 접근을 줄입니다. "
            "트래픽 흐름 제어 → 네트워크 계층 내에서 트래픽 흐름을 제어. "
            "전송 중 데이터 보호 → 전송 중인 데이터 보호. "
            "로깅 구성 → 서비스 및 애플리케이션 로깅 구성."
        ),
    },
}


def extract_text(path):
    doc = fitz.open(path)
    parts = [p.get_text("text") for p in doc]
    doc.close()
    return "\n".join(parts)


def clean_lines(raw):
    out = []
    for ln in raw.split("\n"):
        s = ln.rstrip()
        st = s.strip()
        if st == "":
            out.append("")
            continue
        if st.startswith("IT Certification Guaranteed"):
            continue
        if re.fullmatch(r"-{2}\s*\d+\s+of\s+\d+\s*-{2}", st):
            continue
        if re.fullmatch(r"\d+", st):
            continue
        out.append(s)
    return out


CHOICE_RE = re.compile(r"^([A-F])\.\s?(.*)$")
BULLET_RE = re.compile(r"^-\s+(.*)$")


def is_hotspot(text):
    return "핫스팟" in text


def norm(s):
    return re.sub(r"\s+", " ", s.lower().strip())


def match_choice_line(line, choices):
    nl = norm(line)
    for i, ch in enumerate(choices):
        nc = norm(ch)
        if nl in nc or nc in nl:
            return LABELS[i]
        # keyword overlap for EN/KR mixed explanations
        words = [w for w in re.split(r"[^a-z0-9가-힣]+", nl) if len(w) > 3]
        cw = [w for w in re.split(r"[^a-z0-9가-힣]+", nc) if len(w) > 3]
        if words and sum(1 for w in words if w in nc) >= min(2, len(words)):
            return LABELS[i]
        if cw and sum(1 for w in cw if w in nl) >= min(2, len(cw)):
            return LABELS[i]
    return None


def answer_from_explanation(explanation, choices, ordered=False):
    if not explanation or not choices:
        return ""
    lines = [l.strip() for l in explanation.split("\n") if l.strip()]
    answer_lines = []
    for line in lines:
        m = re.match(r"^\d+\.\s*(.+)$", line)
        if m:
            answer_lines.append(m.group(1).strip())
            continue
        # Title-like lines before long English paragraph
        if len(line) < 100 and not line.endswith("."):
            if re.search(r"(according to|can automatically|provides|is designed|when )", line, re.I):
                break
            if len(line.split()) <= 12:
                answer_lines.append(line)
                continue
        if len(line) > 120:
            break

    letters = []
    for al in answer_lines[: len(choices)]:
        letter = match_choice_line(al, choices)
        if letter and letter not in letters:
            letters.append(letter)
    if not letters and len(answer_lines) == len(choices):
        # positional fallback for matching-style hotspots
        letters = LABELS[: len(answer_lines)]
    if ordered:
        return ",".join(letters)
    return ",".join(sorted(letters))


def strip_inline_answer(s):
    if "Answer:" in s:
        s = s.split("Answer:")[0]
    if "Explanation:" in s:
        s = s.split("Explanation:")[0]
    return s.strip()


def parse_block(num, block):
    if num in MANUAL:
        m = MANUAL[num]
        stem_m = re.match(r"(.*?)(?:\n|$)", block.strip())
        stem = ""
        for ln in block.split("\n"):
            st = ln.strip()
            if not st or st == "핫스팟 질문":
                continue
            if st.startswith("다음 목록") or st.startswith("Answer"):
                break
            if st.startswith("-"):
                break
            stem += (" " if stem else "") + st
        return {
            "id": num,
            "text": stem.strip(),
            "choices": m["choices"],
            "answer": m["answer"],
            "multi": m["multi"],
            "explanation": m["explanation"],
        }

    block_lines = block.split("\n")
    answer = None
    stem_choice_lines = []
    explanation_lines = []
    past_answer = False

    for ln in block_lines:
        st = ln.strip()
        m = re.match(r"^Answer:\s*(.*)$", st)
        if m and answer is None:
            ans = m.group(1).strip()
            answer = ans if ans else ""
            past_answer = True
            continue
        if st == "Explanation:" or st.startswith("Explanation:"):
            past_answer = True
            rest = st.replace("Explanation:", "", 1).strip()
            if rest:
                explanation_lines.append(rest)
            continue
        if not past_answer:
            stem_choice_lines.append(ln)
        else:
            explanation_lines.append(ln)

    choices = []
    stem_parts = []
    cur_choice = None
    hotspot = is_hotspot(block)

    for ln in stem_choice_lines:
        st = ln.strip()
        if "Answer:" in st:
            st = strip_inline_answer(st)
            if not st:
                break
        if st == "핫스팟 질문":
            continue
        cm = CHOICE_RE.match(st)
        bm = BULLET_RE.match(st) if hotspot else None
        if cm:
            if cur_choice is not None:
                choices.append(cur_choice.strip())
            cur_choice = cm.group(2)
        elif bm and hotspot:
            if cur_choice is not None:
                choices.append(cur_choice.strip())
            cur_choice = bm.group(1)
        else:
            if cur_choice is None:
                if st:
                    stem_parts.append(st)
            else:
                if st:
                    st = strip_inline_answer(st)
                    if st:
                        cur_choice += " " + st
                    else:
                        if cur_choice is not None:
                            choices.append(cur_choice.strip())
                            cur_choice = None
                        break
    if cur_choice is not None:
        choices.append(cur_choice.strip())

    stem = " ".join(stem_parts).strip()
    explanation = "\n".join(l.strip() for l in explanation_lines if l.strip()).strip()
    # flatten multi-line explanation for display
    explanation_flat = re.sub(r"\s+", " ", explanation)

    if answer is None and not hotspot:
        return None

    ordered = "순서" in stem or "순서대로" in stem
    if not answer and hotspot and choices:
        answer = answer_from_explanation(explanation, choices, ordered=ordered)

    if not answer and hotspot and explanation:
        # Q207-style: numbered English steps
        nums = re.findall(r"^\d+\.\s*(.+)$", explanation, re.M)
        if nums:
            letters = []
            for step in nums:
                letter = match_choice_line(step, choices)
                if letter:
                    letters.append(letter)
            if letters:
                answer = ",".join(letters) if ordered else ",".join(sorted(set(letters)))

    if not answer:
        return None

    answer = answer.replace(" ", "").upper()
    answer = re.sub(r"[^A-F,]", "", answer)
    if "," not in answer and len(answer) > 1:
        answer = ",".join(list(answer))
    multi = "," in answer

    if not stem or len(choices) < 2:
        return None

    return {
        "id": num,
        "text": stem,
        "choices": choices,
        "answer": answer,
        "multi": multi,
        "explanation": explanation_flat,
    }


def parse_questions(text):
    lines = clean_lines(text)
    full = "\n".join(lines)
    blocks = re.split(r"QUESTION NO:\s*\d+", full)
    nums = re.findall(r"QUESTION NO:\s*(\d+)", full)
    questions = []
    for num, block in zip(nums, blocks[1:]):
        q = parse_block(int(num), block)
        if q:
            questions.append(q)
    return questions


def js_array(questions):
    lines = ["var ALL_QUESTIONS = ["]
    for q in questions:
        lines.append("  " + json.dumps(q, ensure_ascii=False) + ",")
    lines.append("];")
    return "\n".join(lines)


def patch_html(html, questions):
    total = len(questions)
    new_arr = js_array(questions)
    html = re.sub(r"var ALL_QUESTIONS = \[.*?\n\];", new_arr, html, count=1, flags=re.S)

    if "var TOTAL = ALL_QUESTIONS.length;" not in html:
        html = html.replace(
            "];\n\n/* ── 상태 ── */",
            "];\nvar TOTAL = ALL_QUESTIONS.length;\n\n/* ── 상태 ── */",
            1,
        )

    html = html.replace("var rangeFrom = 1, rangeTo = 97;", "var rangeFrom = 1, rangeTo = TOTAL;")
    html = re.sub(r"' / 97'", "' / ' + TOTAL", html)
    html = html.replace("!(v >= 1 && v <= 97)", "!(v >= 1 && v <= TOTAL)")
    html = html.replace("if (v >= 1 && v <= 97) {", "if (v >= 1 && v <= TOTAL) {")
    html = html.replace(
        "if (f < 1 || f > 97 || t < 1 || t > 97 || f > t) {",
        "if (f < 1 || f > TOTAL || t < 1 || t > TOTAL || f > t) {",
    )
    html = html.replace(
        "if (!customCount || customCount < 1 || customCount > 97) return;",
        "if (!customCount || customCount < 1 || customCount > TOTAL) return;",
    )

    html = html.replace("<title>AIP-C01 모의고사</title>", "<title>SCS-C03 모의고사</title>")
    html = html.replace(
        '<span class="logo-text">AIP-C01 모의고사</span>',
        '<span class="logo-text">SCS-C03 모의고사</span>',
    )
    html = html.replace(
        '<div class="start-title">AWS GenAI Developer 모의고사</div>',
        '<div class="start-title">AWS Security Specialty 모의고사</div>',
    )
    html = re.sub(
        r'<div class="start-sub">.*?</div>',
        f'<div class="start-sub">SCS-C03-KR · {total}문제 기출 덤프 · 랜덤 출제 · 즉시 해설</div>',
        html,
        count=1,
    )
    html = re.sub(
        r'(<div class="stat"><div class="stat-val">)\d+(</div><div class="stat-lbl">총 문제</div></div>)',
        rf"\g<1>{total}\2",
        html,
        count=1,
    )
    html = re.sub(
        r'onclick="selectPreset\(\d+,\'card97\'\)"',
        f"onclick=\"selectPreset({total},'card97')\"",
        html,
        count=1,
    )
    html = re.sub(
        r'(<button class="opt-card" id="card97"[^>]*>\s*<div class="opt-num">)\d+(</div><div class="opt-label">전체</div>)',
        rf"\g<1>{total}\2",
        html,
        count=1,
    )
    html = re.sub(
        r'(<input class="num-input-inline" id="customCountInput"[^>]*min="1" max=")\d+(" placeholder=")1~\d+(")',
        rf'\g<1>{total}\g<2>1~{total}\g<3>',
        html,
        count=1,
    )
    html = re.sub(
        r'(<input class="num-input" id="rangeFrom"[^>]*min="1" max=")\d+(" placeholder=")\d+(")',
        rf'\g<1>{total}\g<2>1\g<3>',
        html,
        count=1,
    )
    html = re.sub(
        r'(<input class="num-input" id="rangeTo"[^>]*min="1" max=")\d+(" placeholder=")\d+(")',
        rf'\g<1>{total}\g<2>{total}\g<3>',
        html,
        count=1,
    )
    html = re.sub(
        r'(<span class="qselect-count" id="qselectCount">)선택: \d+ / \d+(</span>)',
        rf"\g<1>선택: {total} / {total}\2",
        html,
        count=1,
    )

    if 'id="explainBox"' not in html:
        html = html.replace(
            '<div class="feedback-box" id="feedbackBox"></div>',
            '<div class="feedback-box" id="feedbackBox"></div>\n  <div class="explain-box" id="explainBox"></div>',
            1,
        )
    if ".explain-box" not in html:
        expl_css = (
            "  .explain-box { margin-top:10px; padding:13px 15px; border-radius:10px;"
            " font-size:13px; line-height:1.7; display:none; background:var(--surface2);"
            " border:1px solid var(--border); color:var(--text2); }\n"
            "  .explain-box.show { display:block; }\n"
            "  .explain-box .explain-title { font-size:11px; font-weight:700; letter-spacing:0.5px;"
            " text-transform:uppercase; color:var(--accent); margin-bottom:6px; }\n"
        )
        html = html.replace("  .feedback-box.wrong-fb {", expl_css + "  .feedback-box.wrong-fb {", 1)

    if "escapeHtml" not in html:
        html = html.replace(
            "function gel(id) { return document.getElementById(id); }",
            "function gel(id) { return document.getElementById(id); }\n"
            "function escapeHtml(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}",
            1,
        )

    if "explainBox" not in html or "/* 해설 */" not in html:
        old = """  } else {
    fb.className = 'feedback-box';
    fb.textContent = '';
  }

  /* 버튼 상태 */"""
        new = """  } else {
    fb.className = 'feedback-box';
    fb.textContent = '';
  }

  /* 해설 */
  var eb = gel('explainBox');
  if (answered && q.explanation) {
    eb.className = 'explain-box show';
    eb.innerHTML = '<div class="explain-title">해설</div>' + escapeHtml(q.explanation);
  } else {
    eb.className = 'explain-box';
    eb.innerHTML = '';
  }

  /* 버튼 상태 */"""
        if old in html:
            html = html.replace(old, new, 1)

    return html


def build():
    # Use existing index.html as template base (already SCS-branded) or _template if exists
    import os
    base = TEMPLATE if os.path.exists(TEMPLATE) else OUT
    text = extract_text(PDF)
    questions = parse_questions(text)
    questions.sort(key=lambda q: q["id"])
    total = len(questions)
    ids = [q["id"] for q in questions]
    print(f"Parsed {total} questions (ids {min(ids)}-{max(ids)})")
    missing = [i for i in range(1, 216) if i not in set(ids)]
    if missing:
        print(f"  WARNING missing ids: {missing}")

    with open(base, encoding="utf-8") as f:
        html = f.read()
    html = patch_html(html, questions)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
