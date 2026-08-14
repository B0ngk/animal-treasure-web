#!/usr/bin/env python3
"""O/X 표시를 원본 도형 그대로 PNG 로 만든다.

O·X 는 원본에서 이미지가 아니라 도형이라 추출할 수 없다. 대신 도형 정의를
그대로 옮겨 그린다.
  O : donut, 기본 adj 0.25 → 안쪽 구멍 지름 = 바깥 지름의 50%, 색 #0B76A0
  X : 12점 자유형, 색 #EB3D7B (좌표는 slide83 의 a:gd 값을 비율로 환산)

사용법:
    python3 tools/make_ox.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'webapp' / 'assets'

SCALE = 4                      # 확대해 그린 뒤 축소해 계단 현상을 줄인다
O_COLOR = (11, 118, 160, 255)  # 0B76A0
X_COLOR = (235, 61, 123, 255)  # EB3D7B

# 원본 자유형의 12개 점 (가로·세로 크기 대비 비율)
X_POINTS = [
    (0.1875, 0.0), (0.5, 0.3125), (0.8125, 0.0), (1.0, 0.1875),
    (0.6875, 0.5), (1.0, 0.8125), (0.8125, 1.0), (0.5, 0.6875),
    (0.1875, 1.0), (0.0, 0.8125), (0.3125, 0.5), (0.0, 0.1875),
]


def make_o(size=167):
    s = size * SCALE
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], fill=O_COLOR)
    hole = s * 0.5                                   # adj 0.25 → 구멍 50%
    off = (s - hole) / 2
    d.ellipse([off, off, off + hole - 1, off + hole - 1], fill=(0, 0, 0, 0))
    return im.resize((size, size), Image.LANCZOS)


def make_x(size=161):
    s = size * SCALE
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(x * (s - 1), y * (s - 1)) for x, y in X_POINTS], fill=X_COLOR)
    return im.resize((size, size), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, im in (('ox_o.png', make_o()), ('ox_x.png', make_x())):
        im.save(OUT / name)
        print(f'  {name}  {im.size[0]}x{im.size[1]}')


if __name__ == '__main__':
    main()
