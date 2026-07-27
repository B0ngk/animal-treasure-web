#!/usr/bin/env python3
"""문제은행을 webapp/questions.json 으로 추출한다.

원본 문제은행은 슬라이드 70부터 시작하며 한 문항이 3슬라이드를 차지한다.
  +0 표지("문제 N")  +1 문제  +2 정답 및 해설
VBA 의 QuizCount = ((마지막슬라이드 + 1) - 70) / 3 과 같은 규칙이다.

문항은 네 가지 유형이 섞여 있고, 유형마다 슬라이드 구성이 다르다.

  short   단답형. 문제 44pt + 정답 115pt + 해설 24pt
  ox      O/X. 문제 슬라이드에 O·X 도형, 정답 슬라이드의 'o'/'x' 도형 중
          숨겨지지 않은 쪽이 정답
  blank   빈칸. 문제 문장에 정답 단어가 그대로 들어있고 '?' 도형이 그 위를
          덮어 가린다. 그대로 뽑으면 정답이 노출되므로 마스킹해야 한다
  choice  4지선다. 번호 배지(24pt)와 보기 텍스트(36pt) 4쌍 + 정답 번호 96pt

사용법:
    python3 tools/dump_questions.py
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COORDS = ROOT / 'docs' / 'slide-coordinates.json'
ORIGINAL = ROOT / 'assets' / 'original'
OUT = ROOT / 'webapp' / 'questions.json'
IMG_DIR = ROOT / 'webapp' / 'assets' / 'q'

BANK_START = 70
SLIDES_PER_Q = 3
BLANK_MARK = '◯'          # 가려진 정답 자리에 넣을 표시


def visible(shapes):
    return [s for s in shapes if not s.get('hidden')]


def texts(shapes):
    return [s for s in visible(shapes) if s['text'].strip()]


def by_size(shapes):
    """글자 크기 내림차순. 크기가 없는 것은 0 으로 본다."""
    return sorted(texts(shapes), key=lambda s: -(s['size'] or 0))


def stem_of(shapes):
    """문제 본문: 보기·번호를 뺀 가장 긴 텍스트."""
    cand = [s for s in texts(shapes) if len(s['text'].strip()) > 6]
    return max(cand, key=lambda s: len(s['text']))['text'].strip() if cand else ''


def explanation_of(a_shapes):
    """해설: 24~28pt 텍스트."""
    for s in texts(a_shapes):
        if s['size'] and 20 <= s['size'] <= 30:
            return s['text'].strip()
    return ''


def detect_type(q_shapes, a_shapes):
    names = {s['name'] for s in a_shapes}
    if 'o' in names and 'x' in names:
        return 'ox'
    badges = [s['text'].strip() for s in texts(q_shapes)
              if s['text'].strip() in ('1', '2', '3', '4')]
    if len(set(badges)) >= 4:
        return 'choice'
    if any(s['text'].strip() == '?' for s in texts(q_shapes)):
        return 'blank'
    return 'short'


def ox_answer(a_shapes):
    """숨겨지지 않은 쪽이 정답."""
    for s in a_shapes:
        if s['name'] in ('o', 'x') and not s.get('hidden'):
            return s['name'].upper()
    return ''


def choice_list(q_shapes):
    """번호 배지와 보기 텍스트를 짝지어 1~4 순서로 돌려준다."""
    t = texts(q_shapes)
    badges = [s for s in t if s['text'].strip() in ('1', '2', '3', '4')]
    options = [s for s in t if s['size'] and abs(s['size'] - 36) < 1]
    out = {}
    for b in badges:
        # 같은 줄(y 가 가까움)에서 배지 오른쪽에 있는 보기를 찾는다
        same_row = [o for o in options
                    if abs(o['y'] - b['y']) < 20 and o['x'] > b['x']]
        if same_row:
            near = min(same_row, key=lambda o: o['x'] - b['x'])
            out[b['text'].strip()] = near['text'].strip()
    return [out.get(str(i), '') for i in (1, 2, 3, 4)]


def mask_answer(question, answer):
    """빈칸 문항에서 문장에 노출된 정답을 가린다."""
    parts = [p.strip() for p in re.split(r'[,·]', answer) if p.strip()]
    masked = question
    for p in parts:
        if p and p in masked:
            masked = masked.replace(p, BLANK_MARK, 1)
    return masked


def first_image(shapes):
    for s in visible(shapes):
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
    stats = {}

    for i in range(count):
        base = BANK_START + i * SLIDES_PER_Q
        q = slides.get(str(base + 1))
        a = slides.get(str(base + 2))
        if not q or not a:
            continue
        qs, as_ = q['shapes'], a['shapes']

        kind = detect_type(qs, as_)
        stats[kind] = stats.get(kind, 0) + 1

        item = {'id': i + 1, 'type': kind,
                'question': stem_of(qs),
                'explanation': explanation_of(as_)}

        if kind == 'ox':
            item['answer'] = ox_answer(as_)
        elif kind == 'choice':
            item['choices'] = choice_list(qs)
            big = [s for s in by_size(as_) if s['text'].strip().isdigit()]
            item['answer'] = big[0]['text'].strip() if big else ''
        else:
            big = by_size(as_)
            item['answer'] = big[0]['text'].strip() if big else ''
            if kind == 'blank':
                item['question'] = mask_answer(item['question'], item['answer'])

        img = first_image(qs)
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

    print(f'{OUT.relative_to(ROOT)} 생성: {len(questions)}문항 '
          f'({", ".join(f"{k} {v}" for k, v in sorted(stats.items()))})')

    # 뽑은 결과가 문항 수만큼 되는지, 정답이 빈 곳이 없는지 확인
    bad = [q['id'] for q in questions if not q['answer'] or not q['question']]
    if bad:
        print(f'  ⚠️ 정답/문제가 비어 있는 문항: {bad}')
    spoiled = [q['id'] for q in questions
               if q['type'] == 'blank' and q['answer'] in q['question']]
    if spoiled:
        print(f'  ⚠️ 정답이 문제에 노출된 문항: {spoiled}')


if __name__ == '__main__':
    main()
