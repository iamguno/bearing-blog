"""블로그 원고(md)로 미리보기 사이트를 만든다. 표준 라이브러리만 쓴다.

사용법: python3 build_site.py <원고 md 폴더> <사이트 폴더>

- 글 끝의 '올릴 때 쓸 정보'(작업용 메모)는 공개 페이지에 넣지 않는다.
- 비어 있는 현장 이야기 자리와 견적 문의 버튼은 '준비 중'으로 보여 준다.
- 아직 정하지 않은 책 제목과 일정은 공개용 문구로 바꾼다 (PUBLIC_EDITS).
- 모든 페이지에 검색 제외(noindex)를 넣는다.
"""
import html
import os
import re
import shutil
import sys

SITE_NAME = '로비아테크 블로그'
BASE_URL = 'https://iamguno.github.io/bearing-blog/'
SITE_INTRO = ('30년 베어링 현장 경험과 공학 지식으로, 베어링 번호 읽는 법부터 '
              '고장 원인과 베어링의 역사까지 쉽게 풀어 씁니다.')

# 첫 화면에 보이는 순서
POSTS = ['11_베어링 번호 읽는 법.md', '16_통나무에서 볼 베어링까지.md']

# 공개 페이지에서만 바꿀 문구: (원고 문구, 공개용 문구). 원고에서 못 찾으면 멈춘다.
PUBLIC_EDITS = {
    '11': [
        ("- 『베어링 공학』의 '주요 치수와 호칭 기호' — 치수 계열과 정밀도 등급, 인치 베어링까지 더 자세히 *(2027년 1월 출간 예정)*",
         "- 준비 중인 베어링 공학책의 '주요 치수와 호칭 기호' — 치수 계열과 정밀도 등급, 인치 베어링까지 더 자세히 *(출간 준비 중)*"),
    ],
    '16': [
        ("- 이 글은 준비 중인 교양책 『세상을 움직이는 기술, 베어링 이야기』 1장의 두 꼭지를 줄인 것이에요. 책이 나오면 이곳에서 알려 드릴게요.",
         "- 이 글은 준비 중인 교양책 1장의 두 꼭지를 줄인 것이에요. 책이 나오면 이곳에서 알려 드릴게요."),
    ],
}

# 공개 페이지에 남으면 안 되는 말 (작업용 메모, 사업 계획, 책 제목)
FORBIDDEN = ['올릴 때 쓸 정보', '현장 이야기 자리', '큰아빠', '사실 확인', '수수료', '목표액', '『', '』']

FIELD_STORY = ('<div class="field-story">현장 이야기는 준비 중이에요. '
               '30년 동안 베어링 현장에서 겪은 이야기로 곧 채울게요.</div>')
CTA_TEXT = '견적 문의는 사이트를 정식으로 열 때 함께 열어요.'


def esc(s):
    return html.escape(s, quote=True)


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![*\w])\*(?![\s*])(.+?)(?<![\s*])\*(?![*\w])', r'<em>\1</em>', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', s)
    return s


def table(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    head, body = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r':?-{3,}:?', c) for c in r)]
    out = ['<div class="table-wrap"><table><thead><tr>']
    out += [f'<th>{inline(c)}</th>' for c in head]
    out.append('</tr></thead><tbody>')
    for r in body:
        out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


BLOCK_START = re.compile(r'^(#{1,6}\s|!\[|\||>|- |\d+\.\s|@@|---\s*$)')


def md_to_html(md, cta_html):
    lines, out, i = md.split('\n'), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('@@FIELD_STORY@@'):
            out.append(FIELD_STORY)
            i += 1
            continue
        if line.startswith('@@CTA@@'):
            out.append(cta_html)
            i += 1
            continue
        m = re.match(r'^(#{2,3})\s+(.*)$', line)
        if m:
            n = len(m.group(1))
            out.append(f'<h{n}>{inline(m.group(2))}</h{n}>')
            i += 1
            continue
        m = re.match(r'^!\[([^\]]*)\]\((\S+)\)\s*$', line)
        if m:
            out.append(f'<figure><img src="{esc(m.group(2))}" alt="{esc(m.group(1))}"></figure>')
            i += 1
            continue
        if line.startswith('|'):
            block = []
            while i < len(lines) and lines[i].startswith('|'):
                block.append(lines[i])
                i += 1
            out.append(table(block))
            continue
        if line.startswith('>'):
            block = []
            while i < len(lines) and lines[i].startswith('>'):
                block.append(lines[i][1:].strip())
                i += 1
            paras = [p for p in '\n'.join(block).split('\n\n') if p.strip()]
            out.append('<blockquote>' + ''.join(f'<p>{inline(" ".join(p.split()))}</p>' for p in paras) + '</blockquote>')
            continue
        if re.match(r'^\d+\.\s', line):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s', lines[i]):
                items.append(re.sub(r'^\d+\.\s+', '', lines[i]))
                i += 1
            out.append('<ol>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ol>')
            continue
        if line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].startswith('- '):
                items.append(lines[i][2:])
                i += 1
            out.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ul>')
            continue
        if re.match(r'^---\s*$', line):
            out.append('<hr>')
            i += 1
            continue
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not BLOCK_START.match(lines[i]):
            para.append(lines[i])
            i += 1
        out.append(f'<p>{inline(" ".join(para))}</p>')
    return '\n'.join(out)


def meta_value(info, key):
    m = re.search(rf'^\| {re.escape(key)} \| (.+?) \|\s*$', info, re.M)
    if not m:
        sys.exit(f'올릴 때 쓸 정보에서 "{key}"를 못 찾음')
    return m.group(1).strip()


def load_post(path):
    raw = open(path, encoding='utf-8').read()
    body, sep, info = raw.partition('\n---\n\n## 올릴 때 쓸 정보')
    if not sep:
        sys.exit(f'{os.path.basename(path)}: 올릴 때 쓸 정보 구분선을 못 찾음')
    num = os.path.basename(path).split('_', 1)[0]
    title = re.match(r'^# (.+)$', body, re.M).group(1).strip()
    body = re.sub(r'^# .+\n', '', body, count=1)
    category = re.split(r'\s[—(]', meta_value(info, '분류'))[0].strip()
    slug = meta_value(info, '주소')
    desc = meta_value(info, '검색 결과에 보일 설명')
    return dict(num=num, title=title, body=body, category=category, slug=slug, desc=desc)


def publicize(post, published):
    body = post['body']
    for old, new in PUBLIC_EDITS.get(post['num'], []):
        if old not in body:
            sys.exit(f"#{post['num']}: 바꿀 문구를 원고에서 못 찾음 → {old[:40]}…")
        body = body.replace(old, new)
    # 현장 이야기 자리(인용문)와 견적 문의 줄을 표시로 바꾼다
    body = re.sub(r'(?m)^> 〔[^\n]*현장 이야기 자리[^\n]*\n(?:>[^\n]*\n)*', '@@FIELD_STORY@@\n', body)
    body = re.sub(r'(?m)^\*\*\[견적 문의하기\]\*\*.*$', '@@CTA@@', body)
    # 더 알아보기: 이미 있는 글은 링크로, 나머지 공개 일정은 '준비 중'으로
    for other in published:
        if other is post:
            continue
        link = f"[{other['title']}](../{other['slug']}/)"
        body = re.sub(rf'(?m)^- {re.escape(other["title"])}\s*\*\([^)]*\)\*\s*$', f'- {link}', body)
    body = re.sub(r'\*\(\d+월 공개(?: 예정)?\)\*', '*(준비 중)*', body)
    post['body'] = body


def page(title, desc, body_html, depth, og_image, url, og_type='article'):
    up = '../' * depth
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(og_image)}">
<meta property="og:url" content="{esc(url)}">
<link rel="stylesheet" href="{up}assets/style.css">
</head>
<body>
<div class="preview-bar">미리보기 사이트예요 · 정식으로 열기 전이라 검색에는 나오지 않아요</div>
<header class="site-header"><div class="inner"><a class="brand" href="{up or './'}">로비아테크 <span>블로그</span></a></div></header>
<main>
{body_html}
</main>
<footer><div class="inner">© 2026 로비아테크 · 미리보기</div></footer>
</body>
</html>
'''


def build(src, out):
    posts = [load_post(os.path.join(src, f)) for f in POSTS]
    for p in posts:
        publicize(p, posts)
    for d in ('posts', 'images'):
        shutil.rmtree(os.path.join(out, d), ignore_errors=True)
        os.makedirs(os.path.join(out, d))
    open(os.path.join(out, '.nojekyll'), 'w').close()

    cards = []
    for p in posts:
        images = []

        def copy_image(m):
            name = m.group(2).strip('<>')
            new = f"{p['slug']}-{len(images) + 1}{os.path.splitext(name)[1].lower()}"
            shutil.copyfile(os.path.join(src, name), os.path.join(out, 'images', new))
            images.append(new)
            return f'![{m.group(1)}](../../images/{new})'

        body = re.sub(r'!\[([^\]]*)\]\((<[^>]+>|\S+)\)', copy_image, p['body'])
        cta = (f'<div class="cta"><p>{esc(CTA_TEXT)}</p>'
               '<span class="btn disabled">견적 문의하기 (준비 중)</span></div>')
        content = (f'<p class="crumbs"><a href="../../">← 글 목록</a> · <span class="tag">{esc(p["category"])}</span></p>\n'
                   f'<h1>{esc(p["title"])}</h1>\n' + md_to_html(body, cta))
        if '@@' in content:
            sys.exit(f"#{p['num']}: 바꾸지 못한 표시가 남음")
        og = BASE_URL + 'images/' + images[0] if images else ''
        url = f"{BASE_URL}posts/{p['slug']}/"
        doc = page(f"{p['title']} | {SITE_NAME}", p['desc'], content, 2, og, url)
        bad = [w for w in FORBIDDEN if w in doc]
        if bad:
            sys.exit(f"#{p['num']}: 공개하면 안 되는 말이 남음 → {bad}")
        os.makedirs(os.path.join(out, 'posts', p['slug']))
        open(os.path.join(out, 'posts', p['slug'], 'index.html'), 'w', encoding='utf-8').write(doc)
        thumb = f'<img src="images/{images[0]}" alt="">' if images else ''
        cards.append(f'<a class="card" href="posts/{p["slug"]}/">{thumb}<div class="body">'
                     f'<span class="tag">{esc(p["category"])}</span><h2>{esc(p["title"])}</h2>'
                     f'<p>{esc(p["desc"])}</p></div></a>')
        print(f"#{p['num']} → posts/{p['slug']}/ (그림 {len(images)}장)")

    home = (f'<section class="hero"><h1>{esc(SITE_NAME)}</h1><p>{esc(SITE_INTRO)}</p></section>\n'
            '<section class="cards">' + ''.join(cards) + '</section>\n'
            '<p class="more">곧 더 많은 글이 올라와요.</p>')
    first_image = BASE_URL + 'images/' + f"{posts[0]['slug']}-1.png"
    doc = page(SITE_NAME, SITE_INTRO, home, 0, first_image, BASE_URL, og_type='website')
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(doc)
    print('index.html 완료')


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
