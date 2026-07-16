# SCS-C03 모의고사

AWS Certified Security - Specialty (SCS-C03-KR) 기출 덤프 기반 모의고사 웹앱입니다.

- 총 **267문제** (단일/복수 정답, 핫스팟 포함) · 덤프 V14.35
- 랜덤 출제 · 범위 지정 · 문제 개별 선택
- 문제 풀이 후 **정답 및 해설** 즉시 표시
- 단일 HTML 파일로 동작 (별도 서버 불필요)

## 사용 방법

- 온라인: [GitHub Pages](https://ctd2800-creator.github.io/scs-c03-quiz/)
- 로컬: `index.html` 파일을 브라우저로 열기

## 구조

모든 로직과 문제 데이터(`ALL_QUESTIONS`)가 `index.html` 안에 포함되어 있습니다.

## 업데이트

```powershell
# PDF 경로를 build.py 의 PDF 변수에 맞춘 뒤
python build.py
python translate_explanations.py   # 영문 해설 → 한국어
```
