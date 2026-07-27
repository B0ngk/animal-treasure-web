#!/usr/bin/env python3
"""원본 PPT 슬라이드의 도형 좌표·색상·폰트를 추출한다.

슬라이드가 12192000x6858000 EMU(=1280x720px)이므로 EMU/9525 로 나누면
웹 무대(1280x720)의 px 좌표와 1:1로 대응한다. 그룹 안에 중첩된 도형은
그룹의 오프셋·스케일을 누적해 절대 좌표로 환산한다.

사용법:
    python3 tools/extract_slide.py 9              # 슬라이드 9
    python3 tools/extract_slide.py 9 --layout     # 해당 슬라이드의 레이아웃까지
"""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
}
EMBED = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'
EMU = 9525.0  # 1 px

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / '_slides'

# 원본 .pptm 은 상용 배포물이라 저장소에 포함하지 않는다.
# .pptm 이 없는 PC에서는 docs/slide-coordinates.json 에 이미 추출해 둔
# 좌표를 사용한다.
# '~$' 로 시작하는 파일은 Office 가 만드는 임시 잠금 파일이라 제외한다.
_found = sorted(p for p in ROOT.glob('*.pptm') if not p.name.startswith('~$'))
PPTM = _found[0] if _found else None


def require_pptm():
    if PPTM is None:
        sys.exit(
            '원본 .pptm 을 찾을 수 없습니다 (저장소에 포함되지 않음).\n'
            '이미 추출해 둔 좌표를 쓰려면: docs/slide-coordinates.json\n'
            f'원본으로 다시 추출하려면 .pptm 을 {ROOT} 에 두고 실행하세요.'
        )


def unpack(*members):
    require_pptm()
    WORK.mkdir(exist_ok=True)
    subprocess.run(['unzip', '-o', '-q', str(PPTM), *members, '-d', str(WORK)],
                   check=False)


def rels_for(xml_path):
    """해당 xml의 rId -> 이미지 파일명 매핑."""
    rels = xml_path.parent / '_rels' / (xml_path.name + '.rels')
    if not rels.exists():
        return {}
    text = rels.read_text()
    return dict(re.findall(r'Id="(rId\d+)"[^>]*Target="[^"]*media/([^"]+)"', text))


def shapes(xml_path):
    """(kind, name, img, x, y, w, h, rot, text, size_pt, color, font) 목록."""
    rels = rels_for(xml_path)
    tree = ET.parse(xml_path).getroot()
    out = []

    def walk(node, ox, oy, sx, sy):
        for el in node:
            kind = el.tag.split('}')[1]
            if kind not in ('sp', 'pic', 'grpSp'):
                continue
            xfrm = (el.find('./p:grpSpPr/a:xfrm', NS)
                    or el.find('./p:spPr/a:xfrm', NS))
            if xfrm is None:
                continue
            off, ext = xfrm.find('a:off', NS), xfrm.find('a:ext', NS)
            if off is None or ext is None:
                continue
            x, y = int(off.get('x')), int(off.get('y'))
            w, h = int(ext.get('cx')), int(ext.get('cy'))
            ax, ay = ox + x * sx, oy + y * sy

            if kind == 'grpSp':
                ch, ce = xfrm.find('a:chOff', NS), xfrm.find('a:chExt', NS)
                nsx = sx * (w / int(ce.get('cx'))) if ce is not None and int(ce.get('cx')) else sx
                nsy = sy * (h / int(ce.get('cy'))) if ce is not None and int(ce.get('cy')) else sy
                cox = ax - (int(ch.get('x')) * nsx if ch is not None else 0)
                coy = ay - (int(ch.get('y')) * nsy if ch is not None else 0)
                walk(el, cox, coy, nsx, nsy)
                continue

            nv = (el.find('./p:nvPicPr/p:cNvPr', NS)
                  or el.find('./p:nvSpPr/p:cNvPr', NS))
            name = nv.get('name') if nv is not None else '?'

            blip = el.find('.//a:blip', NS)
            img = rels.get(blip.get(EMBED), '') if blip is not None else ''

            rot = xfrm.get('rot')
            rot = round(int(rot) / 60000) if rot else 0

            text = ''.join(t.text or '' for t in el.findall('.//a:t', NS)).strip()
            rPr = el.find('.//a:rPr', NS)
            size = int(rPr.get('sz')) / 100 if rPr is not None and rPr.get('sz') else None
            clr = el.find('.//a:rPr//a:srgbClr', NS)
            fill = el.find('./p:spPr//a:solidFill/a:srgbClr', NS)
            latin = el.find('.//a:latin', NS)

            # 숨겨진 도형은 화면에 나오지 않는다. OX 문제의 정답 표시처럼
            # 정답 정보를 담고 있는 경우가 있어 함께 기록한다.
            hidden = nv.get('hidden') == '1' if nv is not None else False

            out.append(dict(
                kind=kind, name=name, img=img, hidden=hidden,
                x=round(ax / EMU), y=round(ay / EMU),
                w=round(w * sx / EMU), h=round(h * sy / EMU),
                rot=rot, text=text, size=size,
                color=clr.get('val') if clr is not None else '',
                fill=fill.get('val') if fill is not None else '',
                font=latin.get('typeface') if latin is not None else '',
            ))

    walk(tree.find('.//p:cSld/p:spTree', NS), 0, 0, 1.0, 1.0)
    return out


def report(xml_path, only_named=False):
    print(f'\n===== {xml_path.name} =====')
    print(f'{"NAME":<30}{"IMG":<13}{"x":>5}{"y":>5}{"w":>5}{"h":>5}{"rot":>5}'
          f'{"pt":>6} {"color":<8}{"fill":<8} TEXT')
    for s in shapes(xml_path):
        if only_named and not s['text'] and not s['img']:
            continue
        pt = f'{s["size"]:.0f}' if s['size'] else ''
        print(f'{s["name"][:29]:<30}{s["img"]:<13}{s["x"]:5}{s["y"]:5}{s["w"]:5}{s["h"]:5}'
              f'{s["rot"]:5}{pt:>6} {s["color"]:<8}{s["fill"]:<8} {s["text"][:34]}')


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    num = sys.argv[1]
    unpack(f'ppt/slides/slide{num}.xml', f'ppt/slides/_rels/slide{num}.xml.rels',
           'ppt/slideLayouts/*', 'ppt/presentation.xml')
    slide = WORK / 'ppt' / 'slides' / f'slide{num}.xml'
    report(slide, only_named='--all' not in sys.argv)

    if '--layout' in sys.argv:
        target = re.search(r'slideLayout(\d+)\.xml',
                           (slide.parent / '_rels' / f'{slide.name}.rels').read_text())
        if target:
            report(WORK / 'ppt' / 'slideLayouts' / f'slideLayout{target.group(1)}.xml',
                   only_named='--all' not in sys.argv)


if __name__ == '__main__':
    main()
