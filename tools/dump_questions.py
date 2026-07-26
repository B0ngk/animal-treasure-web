#!/usr/bin/env python3
"""문제은행을 webapp/questions.json 으로 추출한다.

원본 문제은행은 슬라이드 70부터 시작하며 한 문항이 3슬라이드를 차지한다.
  +0 표지("문제 N")  +1 문제  +2 정답 및 해설
VBA 의 QuizCount = ((마지막슬라이드 + 1) - 70) / 3 과 같은 규칙이다.

문항에 그림이 있으면 webapp/assets/q/ 로 복사하고 파일명을 함께 기록한다.

사용법:
    python3 tools/dump_questions.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COORDS = ROOT / 'docs' / 'slide-coordinates.json'
ORIGINAL = ROOT / 'assets' / 'original'
OUT = ROOT / 'webapp' / 'questions.json'
IMG_DIR = ROOT / 'webapp' / 'assets' / 'q'

BANK_START = 70      # 문제은행 시작 슬라이드
SLIDES_PER_Q = 3     # 한 문항이 차지하는 슬라이드 수


def longest_text(shapes):
    """도형 중 가장 긴 텍스트를 고른다 (본문 텍스트 상자)."""
    texts = [s['text'].strip() for s in shapes if s['text'].strip()]
    return max(texts, key=len) if texts else ''


def texts_by_size(shapes):
    """글자 크기 내림차순으로 (크기, 텍스트) 목록을 만든다."""
    out = [(s['size'] or 0, s['text'].strip()) for s in shapes if s['text'].strip()]
    return sorted(out, key=lambda t: -t[0])


def first_image(shapes):
    for s in shapes:
        if s['img']:
            return s['img']
    return ''


def main():
    data = json.loads(COORDS.read_text())
    slides = data['slides']
    total = max(int(n) for n in slides)
    count = (total + 1 - BANK_START) // SLIDES_PER_Q

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    questions = []

    for i in range(count):
        base = BANK_START + i * SLIDES_PER_Q
        q_slide = slides.get(str(base + 1))
        a_slide = slides.get(str(base + 2))
        if not q_slide or not a_slide:
            continue

        question = longest_text(q_slide['shapes'])

        # 정답 슬라이드: 가장 큰 글자가 정답, 그다음이 해설
        sized = texts_by_size(a_slide['shapes'])
        answer = sized[0][1] if sized else ''
        explanation = sized[1][1] if len(sized) > 1 else ''

        item = {
            'id': i + 1,
            'question': question,
            'answer': answer,
            'explanation': explanation,
        }

        img = first_image(q_slide['shapes'])
        if img:
            src = ORIGINAL / img
            if src.exists():
                shutil.copy(src, IMG_DIR / img)
                item['image'] = 'assets/q/' + img

        questions.append(item)

    payload = {
        'meta': {
            'subject': '과학',
            'grade': '5학년 2학기',
            'unit': '3. 열과 우리 생활',
            'pages': '교과서 80-83쪽',
            'version': '2026-2학기',
        },
        'settings': {'cardCount': 15, 'pointsPerCorrect': 1},
        'questions': questions,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1))

    with_img = sum(1 for q in questions if 'image' in q)
    print(f'{OUT.relative_to(ROOT)} 생성: {len(questions)}문항 '
          f'(그림 포함 {with_img}문항), {OUT.stat().st_size/1024:.0f}KB')


if __name__ == '__main__':
    main()
