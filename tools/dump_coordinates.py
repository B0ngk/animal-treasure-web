#!/usr/bin/env python3
"""모든 슬라이드의 도형 좌표를 docs/slide-coordinates.json 으로 내보낸다.

원본 .pptm 은 저장소에 포함하지 않으므로(상용 배포물), 포팅에 필요한
좌표·색상·폰트 정보만 텍스트로 추출해 커밋한다. 이렇게 하면 .pptm 이
없는 PC에서도 남은 화면을 이어서 작업할 수 있다.

사용법:
    python3 tools/dump_coordinates.py
"""
import json
import re
from pathlib import Path

from extract_slide import PPTM, WORK, shapes, unpack

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'slide-coordinates.json'


def slide_numbers():
    nums = []
    for p in (WORK / 'ppt' / 'slides').glob('slide*.xml'):
        m = re.match(r'slide(\d+)\.xml$', p.name)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def layout_of(num):
    rels = WORK / 'ppt' / 'slides' / '_rels' / f'slide{num}.xml.rels'
    if not rels.exists():
        return None
    m = re.search(r'slideLayout(\d+)\.xml', rels.read_text())
    return int(m.group(1)) if m else None


def main():
    unpack('ppt/slides/*', 'ppt/slideLayouts/*', 'ppt/presentation.xml')

    data = {
        'source': PPTM.name,
        'note': '좌표 단위는 px (1280x720 무대 기준). 원본 EMU / 9525.',
        'slides': {},
        'layouts': {},
    }

    for num in slide_numbers():
        path = WORK / 'ppt' / 'slides' / f'slide{num}.xml'
        lay = layout_of(num)
        data['slides'][str(num)] = {'layout': lay, 'shapes': shapes(path)}
        if lay is not None and str(lay) not in data['layouts']:
            lp = WORK / 'ppt' / 'slideLayouts' / f'slideLayout{lay}.xml'
            if lp.exists():
                data['layouts'][str(lay)] = {'shapes': shapes(lp)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))

    size = OUT.stat().st_size
    print(f'{OUT.relative_to(ROOT)} 생성: 슬라이드 {len(data["slides"])}개, '
          f'레이아웃 {len(data["layouts"])}개, {size/1024:.0f}KB')


if __name__ == '__main__':
    main()
