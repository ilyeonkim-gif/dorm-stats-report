# -*- coding: utf-8 -*-
"""생활관 일일 인원 HWP(한글 5.0) 파일 분석기"""
import olefile, zlib, struct, re, os
from datetime import date

def _records(data):
    i = 0
    while i + 4 <= len(data):
        h = struct.unpack('<I', data[i:i+4])[0]; i += 4
        tag, lvl, size = h & 0x3ff, (h >> 10) & 0x3ff, h >> 20
        if size == 0xfff:
            size = struct.unpack('<I', data[i:i+4])[0]; i += 4
        yield tag, lvl, data[i:i+size]
        i += size

def _para_text(b):
    out, i = [], 0
    while i + 1 < len(b):
        c = struct.unpack('<H', b[i:i+2])[0]
        if c < 32:
            if c in (1,2,3,4,5,6,7,8,9,11,12,14,15,16,17,18,19,20,21,22,23):
                if c == 9: out.append('\t')
                i += 16; continue
            if c == 10: out.append('\n')
            i += 2; continue
        out.append(chr(c)); i += 2
    return ''.join(out)

def read_blocks(path):
    """문서를 ('para', 텍스트) / ('table', [(행, 열, 텍스트)]) 목록으로 변환"""
    f = olefile.OleFileIO(path)
    compressed = f.openstream('FileHeader').read()[36] & 1
    sections = sorted([s for s in f.listdir() if s[0] == 'BodyText'], key=lambda s: int(s[1][7:]))
    blocks, table, tbl_lvl, cell = [], None, None, None
    for s in sections:
        d = f.openstream(s).read()
        if compressed:
            d = zlib.decompress(d, -15)
        for tag, lvl, b in _records(d):
            if table is not None and tag == 66 and lvl < tbl_lvl:      # 표 밖 문단 → 표 종료
                blocks.append(('table', table)); table = None; cell = None
            if tag == 71 and b[:4][::-1] == b'tbl ' and table is None:
                table, tbl_lvl, cell = [], lvl, None
            elif tag == 72 and table is not None and len(b) >= 12:
                col, row = struct.unpack('<HH', b[8:12])
                cell = [row, col, '']; table.append(cell)
            elif tag == 67:
                t = _para_text(b).strip()
                if not t: continue
                if table is not None and cell is not None:
                    cell[2] = (cell[2] + '\n' + t).strip()
                elif table is None:
                    blocks.append(('para', t))
    if table is not None:
        blocks.append(('table', table))
    f.close()
    return blocks

NUM = lambda pat, s: int(m.group(1)) if (m := re.search(pat, s)) else None
REASON_RE = re.compile(r'([가-힣A-Za-z]+)\s*(\d+)\s*명?')

def _reasons(text):
    return [(r, int(n)) for r, n in REASON_RE.findall(text)
            if r not in ('현인원', '총인원', '귀가', '외박', '남', '여')]

def _parse_status_table(cells):
    """현인원/귀가/외박 표 → {학년: {...}}"""
    res, grade, mode = {}, '전체', None
    for row, col, text in sorted(cells, key=lambda c: (c[0], c[1])):
        g = re.search(r'([1-3])\s*학년', text)
        if g:
            grade = f'{g.group(1)}학년'; mode = None; continue
        d = res.setdefault(grade, {'current': None, 'total': None, 'home': 0, 'out': 0, 'reasons': []})
        if '현인원' in text:
            d['current'] = NUM(r'현인원\s*(\d+)', text); d['total'] = NUM(r'총인원\s*(\d+)', text)
        elif re.match(r'^\s*귀가', text):
            d['home'] = NUM(r'귀가\s*(\d+)', text) or 0; mode = '귀가'
        elif re.match(r'^\s*외박', text):
            d['out'] = NUM(r'외박\s*(\d+)', text) or 0; mode = '외박'
        elif mode:
            d['reasons'] += [(mode, r, n) for r, n in _reasons(text)]
    return res

def _parse_night_table(cells):
    rows = {}
    for row, col, text in cells:
        rows.setdefault(row, {})[col] = text
    out = []
    for r in sorted(rows):
        line = rows[r]
        label = line.get(0, '')
        g = re.search(r'([1-3])\s*학년', label)
        if not g: continue
        rest = ' '.join(v for k, v in sorted(line.items()) if k > 0)
        out.append({'grade': f'{g.group(1)}학년',
                    'total': NUM(r'(\d+)\s*명', line.get(1, '')) or 0,
                    'male': NUM(r'남\s*(\d+)', rest) or 0,
                    'female': NUM(r'여\s*(\d+)', rest) or 0})
    return out

def parse_daily(path, filename=None):
    filename = filename or os.path.basename(path)
    blocks = read_blocks(path)
    paras = [t for k, t in blocks if k == 'para']

    # 날짜: 파일명 YYMMDD 우선, 없으면 제목의 M/D
    day = None
    m = re.search(r'(\d{2})(\d{2})(\d{2})(?!\d)', filename)
    if m:
        try: day = date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError: day = None
    if day is None:
        for t in paras[:3]:
            m = re.search(r'(\d{1,2})\s*/\s*(\d{1,2})', t)
            if m:
                day = date(date.today().year, int(m.group(1)), int(m.group(2))); break

    overall, grades, night = None, {}, []
    for kind, cells in blocks:
        if kind != 'table': continue
        alltext = ' '.join(c[2] for c in cells)
        if '현인원' in alltext:
            parsed = _parse_status_table(cells)
            if any(k != '전체' for k in parsed):
                grades = {k: v for k, v in parsed.items() if k != '전체'}
            elif '전체' in parsed:
                overall = parsed['전체']
        elif '남' in alltext and '여' in alltext and '학년' in alltext:
            night = _parse_night_table(cells)

    # 특이사항
    notes = {'학생': [], '민원': []}
    current = None
    for k, t in blocks:
        if k != 'para': continue
        for line in t.split('\n'):
            line = line.strip()
            if not line: continue
            if '특이사항' in line and '학생' in line: current = '학생'; continue
            if '특이사항' in line and '민원' in line: current = '민원'; continue
            if re.match(r'^\d+\s*[.)]\s*\S', line): current = None; continue
            if current:
                txt = line.lstrip('＊*•·- ').strip()
                if txt and txt not in ('없음', '해당없음', '해당 없음'):
                    notes[current].append(txt)

    if overall is None and grades:
        overall = {'current': sum(g['current'] or 0 for g in grades.values()),
                   'total': sum(g['total'] or 0 for g in grades.values()),
                   'home': sum(g['home'] for g in grades.values()),
                   'out': sum(g['out'] for g in grades.values()), 'reasons': []}

    warnings = []
    if day is None: warnings.append('날짜를 찾지 못했습니다 (파일명에 YYMMDD 형식 필요)')
    if overall is None: warnings.append('인원 현황 표를 찾지 못했습니다')
    if overall and grades:
        sc = sum(g['current'] or 0 for g in grades.values())
        if overall['current'] is not None and sc != overall['current']:
            warnings.append(f'학년별 현인원 합({sc})과 전체 현인원({overall["current"]})이 다릅니다')
    for g, v in grades.items():
        if v['total'] is not None and v['current'] is not None and v['total'] - v['home'] - v['out'] != v['current']:
            warnings.append(f'{g}: 총원-귀가-외박이 현인원과 다릅니다')
        if sum(n for m_, r, n in v['reasons'] if m_ == '귀가') not in (0, v['home']):
            warnings.append(f'{g}: 귀가 사유 합계가 귀가 인원과 다릅니다')

    return {'date': day, 'filename': filename, 'overall': overall, 'grades': grades,
            'night': night, 'notes': notes, 'warnings': warnings}

if __name__ == '__main__':
    import sys, pprint
    pprint.pprint(parse_daily(sys.argv[1]))
