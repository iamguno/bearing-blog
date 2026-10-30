"""블로그 원고(md)로 블로그 사이트를 만든다. 표준 라이브러리만 쓴다.

사용법: python3 build_site.py <원고 md 폴더> <사이트 폴더>

- 글 끝의 '올릴 때 쓸 정보'(작업용 메모)는 공개 페이지에 넣지 않는다.
- 비어 있는 현장 이야기 자리는 '현장 이야기' 소제목째 공개 페이지에서 뺀다. 이야기를 채우면 그대로 보인다.
- 견적 문의 버튼은 메일 쓰기 창을 연다. 메일 주소는 스팸을 줄이려고 페이지 글자로 드러내지 않고, 누를 때 만든다.
- 소개·문의·개인정보 처리방침은 원고 폴더의 '고정 페이지'에 md로 쓴다 (PAGES).
- 영어판은 원고 폴더의 '영어판'에 쓰고 /en/ 아래에 만든다. 한국어 글과 '주소'가 같으면 짝이 되어
  서로 오가는 링크와 검색엔진용 짝 표시(hreflang)가 붙는다 (EN_POSTS, EN_PAGES).
- 영어 페이지는 방문자가 동의할 때만 방문 통계를 켠다 (유럽 쿠키 규정).
- 한국어 페이지는 브라우저 언어에 한국어가 없는 방문자에게만 맨 위에 영어 안내 띠를 띄운다. 자동으로 넘기지는 않는다
  (구글이 언어에 따라 강제로 넘기지 말라고 안내하고, 넘기면 한국어 페이지가 검색에 덜 잡힐 수 있다).
- 아직 정하지 않은 책 제목과 일정은 공개용 문구로 바꾼다 (PUBLIC_EDITS).
- SITE_OPEN이 True면 robots.txt와 사이트맵을 만들고, False면 모든 페이지에 검색 제외(noindex)와 미리보기 표시를 넣는다.
"""
import datetime
import html
import os
import re
import shutil
import sys

SITE_NAME = '로비아테크 블로그'
# 블로그 주소. 넣으면 CNAME 파일이 생기고 페이지 안 주소도 바뀐다.
# GitHub 설정에도 같은 주소를 등록했다(2026-10-29). 비우고 올리면 주소 등록이 풀려 다른 사람이 주소를 가로챌 수 있으니 비우지 않는다.
CUSTOM_DOMAIN = 'blog.roviatech.co.kr'
BASE_URL = f'https://{CUSTOM_DOMAIN}/' if CUSTOM_DOMAIN else 'https://iamguno.github.io/bearing-blog/'
SITE_INTRO = ('30년 베어링 현장 경험과 공학 지식으로, 베어링 번호 읽는 법부터 '
              '고장 원인과 베어링의 역사까지 쉽게 풀어 씁니다.')

# 정식으로 열었는지 (2026-10-30 사장님 OK). False로 바꾸면 다시 미리보기(검색 제외)가 된다.
SITE_OPEN = True
# 견적 문의를 받을 메일 (2026-10-30: 일단 운영자 메일만. 사장님 메일은 블로그 운영을 지켜본 뒤)
CONTACT_EMAIL = 'iamguno@naver.com'
# 방문 통계: 구글 애널리틱스 측정 ID (예: 'G-XXXXXXXXXX'). 비우면 넣지 않는다.
ANALYTICS_ID = 'G-C03R1C6F9V'   # 2026-10-30, 계정 '로비아테크' > 속성 '로비아테크 블로그'
# 검색 등록 확인 코드: 구글 서치 콘솔, 네이버 서치어드바이저의 'HTML 태그' 방식 content 값. 비우면 넣지 않는다.
SITE_VERIFICATION = {'google-site-verification': 'FnGy8vwjUJnrvPE3zHXfZ7db4EVpizQZHd8lW3kn4e0',
                     'naver-site-verification': 'fee8d032d96fe8d049fef2ab432df04f8d8b290f'}

# 고정 페이지: (원고 폴더의 '고정 페이지' 안 파일, 주소, 검색 결과에 보일 설명)
PAGES_DIR = '고정 페이지'
PAGES = [
    ('소개.md', 'about', '30년 베어링 현장 경험으로 베어링을 쉽게 풀어 쓰는 로비아테크 블로그를 소개해요.'),
    ('문의.md', 'contact', '베어링 견적, 호환품·단종품 찾기, 고장 상담을 메일로 받아요.'),
    ('개인정보 처리방침.md', 'privacy', '로비아테크 블로그가 문의로 받은 개인정보를 어떻게 쓰고 관리하는지 알려 드려요.'),
]

# 첫 화면에 보이는 순서
POSTS = ['17_풍력발전기의 거대한 날개를 받치는 베어링.md', '11_베어링 번호 읽는 법.md', '16_통나무에서 볼 베어링까지.md']

# 영어판 (2026-10-30부터 ★ 글을 한국어 글과 함께 올림). 원고 폴더의 '영어판' 안, 고정 페이지는 '영어판/고정 페이지' 안.
EN_DIR = '영어판'
EN_POSTS = ['17_Wind Turbine Bearings.md', '11_How to Read Bearing Numbers.md']
EN_PAGES = [
    ('About.md', 'about', 'Roviatech is a bearing company in Seoul, Korea. Our blog explains bearings from 30 years in the field.'),
    ('Contact.md', 'contact', 'Ask us for a bearing quote, a cross-reference between brands, or help finding a discontinued bearing.'),
    ('Privacy.md', 'privacy', 'How the Roviatech Blog uses the information you send us.'),
]

# 공개 페이지에서만 바꿀 문구: (원고 문구, 공개용 문구). 원고에서 못 찾으면 멈춘다. 한국어 글에만 쓴다.
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
FORBIDDEN = ['올릴 때 쓸 정보', '현장 이야기 자리', '큰아빠', '사장님', '사실 확인', '수수료', '목표액', '『', '』']

CTA_TEXT = '이 베어링 찾으세요? 번호나 사진만 보내 주세요.'
CTA_TEXT_PREVIEW = '견적 문의는 사이트를 정식으로 열 때 함께 열어요.'

# 언어별 화면 문구
LANG = {
    'ko': dict(site=SITE_NAME, brand='로비아테크 <span>블로그</span>', intro=SITE_INTRO, locale='ko_KR',
               about='소개', contact='문의', privacy='개인정보 처리방침', switch='English', back='← 글 목록',
               more='곧 더 많은 글이 올라와요.', cta=CTA_TEXT,
               home_cta='베어링을 찾거나 고장으로 고민이면 번호나 사진만 보내 주세요.',
               button='견적 문의하기', subject='[블로그 문의] ', general='견적·상담',
               email='메일 주소', email_fallback='버튼을 눌러 주세요', owner='로비아테크',
               preview='미리보기 사이트예요 · 정식으로 열기 전이라 검색에는 나오지 않아요', preview_foot=' · 미리보기'),
    'en': dict(site='Roviatech Blog', brand='Roviatech <span>Blog</span>', locale='en_US',
               intro=('Bearing know-how from 30 years in the bearing trade in Korea: '
                      'how to read bearing numbers, why bearings fail, and where bearings work.'),
               about='About', contact='Contact', privacy='Privacy Policy', switch='한국어', back='← All articles',
               more='More articles are on the way.', cta='Looking for this bearing? Just send us the number or a photo.',
               home_cta='Need a bearing or help with a failed one? Send us the bearing number or a photo.',
               button='Request a Quote', subject='[Blog inquiry] ', general='Quote request',
               email='Email', email_fallback='Click the button', owner='Roviatech',
               preview='Preview site · not yet open to search engines', preview_foot=' · Preview'),
}

# 문의 버튼을 누를 때 메일 주소와 메일 틀을 만든다 (페이지 글자에는 주소가 없다)
MAIL_SCRIPT = r'''<script>
(function () {
  var bodies = {
    ko: '베어링 번호(호칭):\n제조사:\n수량:\n희망 납기:\n쓰는 곳(장비):\n회사명:\n연락처:\n\n사진이 있으면 첨부해 주세요.',
    en: 'Bearing number:\nBrand:\nQuantity:\nRequired delivery date:\nApplication (machine):\nCompany:\nCountry:\nPhone:\n\nPlease attach photos if you have them.'
  };
  function addr(el) { return el.getAttribute('data-u') + '@' + el.getAttribute('data-d'); }
  document.querySelectorAll('[data-mailtext]').forEach(function (el) { el.textContent = addr(el); });
  document.querySelectorAll('a[data-mail]').forEach(function (a) {
    a.addEventListener('click', function () {
      a.href = 'mailto:' + addr(a) + '?subject=' + encodeURIComponent(a.getAttribute('data-s') || '') +
               '&body=' + encodeURIComponent(bodies[a.getAttribute('data-lang')] || bodies.ko);
    });
  });
})();
</script>'''

# 영어 페이지: 방문자가 동의할 때만 방문 통계를 켠다. 선택은 이 브라우저에만 남는다.
CONSENT_HTML = '''<div class="consent" id="consent" hidden><p>We use Google Analytics cookies to count visits and see which articles are read.
<button type="button" data-consent="yes">Accept</button><button type="button" data-consent="no">Decline</button></p></div>
<script>
(function () {
  var KEY = 'roviatech-analytics', ID = '@@ID@@', box = document.getElementById('consent'), v = null;
  function load() {
    var s = document.createElement('script'); s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + ID; document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date()); window.gtag('config', ID);
  }
  try { v = localStorage.getItem(KEY); } catch (e) {}
  if (v === 'yes') { load(); return; }
  if (v === 'no') { return; }
  box.hidden = false;
  box.addEventListener('click', function (e) {
    var c = e.target.getAttribute('data-consent');
    if (!c) { return; }
    try { localStorage.setItem(KEY, c); } catch (err) {}
    box.hidden = true;
    if (c === 'yes') { load(); }
  });
})();
</script>'''


# 한국어 페이지: 브라우저 언어에 한국어가 없으면 영어판을 알려 주는 띠. 닫으면 이 브라우저에서는 다시 안 뜬다.
LANG_HINT_HTML = '''<div class="lang-hint" id="lang-hint" hidden data-nosnippet lang="en"><div class="inner"><span>@@TEXT@@ <a href="@@HREF@@" hreflang="en">@@LINK@@</a></span><button type="button" aria-label="Close">×</button></div></div>
<script>
(function () {
  var KEY = 'roviatech-lang-hint', box = document.getElementById('lang-hint'), closed = null;
  var langs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ''];
  var korean = langs.some(function (l) { return /^ko\\b/i.test(l || ''); });
  try { closed = localStorage.getItem(KEY); } catch (e) {}
  if (korean || closed) { return; }
  box.hidden = false;
  box.querySelector('button').addEventListener('click', function () {
    box.hidden = true;
    try { localStorage.setItem(KEY, '1'); } catch (e) {}
  });
})();
</script>
'''


def esc(s):
    return html.escape(s, quote=True)


def mail_button(subject, fallback, lang='ko'):
    user, domain = CONTACT_EMAIL.split('@')
    return (f'<a class="btn" href="{esc(fallback)}" data-mail data-lang="{lang}" data-u="{esc(user)}" data-d="{esc(domain)}" '
            f'data-s="{esc(subject)}">{LANG[lang]["button"]}</a>')


def mail_text(lang='ko'):
    user, domain = CONTACT_EMAIL.split('@')
    return (f'<span class="mail-addr" data-mailtext data-u="{esc(user)}" data-d="{esc(domain)}">'
            f'{LANG[lang]["email_fallback"]}</span>')


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


def publicize(post, published, lang='ko'):
    body = post['body']
    for old, new in (PUBLIC_EDITS.get(post['num'], []) if lang == 'ko' else []):
        if old not in body:
            sys.exit(f"#{post['num']}: 바꿀 문구를 원고에서 못 찾음 → {old[:40]}…")
        body = body.replace(old, new)
    # 비어 있는 현장 이야기는 소제목째 빼고(채우면 그대로 보인다), 견적 문의 줄은 표시로 바꾼다
    body = re.sub(r'(?m)^## 현장 이야기[^\n]*\n+(?=> 〔[^\n]*현장 이야기 자리)', '', body)
    body = re.sub(r'(?m)^> 〔[^\n]*현장 이야기 자리[^\n]*\n(?:>[^\n]*\n)*\n*', '', body)
    body = re.sub(r'(?m)^\*\*\[(?:견적 문의하기|Request a Quote)\]\*\*.*$', '@@CTA@@', body)
    # 더 알아보기: 같은 언어로 이미 있는 글은 링크로, 나머지 공개 일정은 '준비 중'으로
    for other in published:
        if other is post:
            continue
        link = f"[{other['title']}](../{other['slug']}/)"
        body = re.sub(rf'(?m)^- {re.escape(other["title"])}\s*\*\([^)]*\)\*\s*$', f'- {link}', body)
    body = re.sub(r'\*\(\d+월 공개(?: 예정)?\)\*', '*(준비 중)*', body)
    post['body'] = body


def page(title, desc, body_html, depth, og_image, path, og_type='article', lang='ko', alt=None):
    """path: 사이트 뿌리에서 본 이 페이지의 주소 (예: 'posts/x/', 'en/about/'). alt: 언어별 짝 페이지 주소."""
    L = LANG[lang]
    up = '../' * depth
    home = up + ('en/' if lang == 'en' else '')
    url = BASE_URL + path
    alt = alt or {}
    head_extra = '' if SITE_OPEN else '<meta name="robots" content="noindex, nofollow">\n'
    for name, code in SITE_VERIFICATION.items():
        if code:
            head_extra += f'<meta name="{name}" content="{esc(code)}">\n'
    if len(alt) > 1:
        for l, p in alt.items():
            head_extra += f'<link rel="alternate" hreflang="{l}" href="{esc(BASE_URL + p)}">\n'
        head_extra += f'<link rel="alternate" hreflang="x-default" href="{esc(BASE_URL + alt.get("ko", path))}">\n'
    consent = ''
    if ANALYTICS_ID and lang == 'ko':
        head_extra += (f'<script async src="https://www.googletagmanager.com/gtag/js?id={ANALYTICS_ID}"></script>\n'
                       '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}'
                       f"gtag('js',new Date());gtag('config','{ANALYTICS_ID}');</script>\n")
    elif ANALYTICS_ID:
        consent = CONSENT_HTML.replace('@@ID@@', ANALYTICS_ID) + '\n'
    other = 'en' if lang == 'ko' else 'ko'
    switch = up + alt.get(other, 'en/' if other == 'en' else '')
    bar = '' if SITE_OPEN else f'<div class="preview-bar">{L["preview"]}</div>\n'
    foot = '' if SITE_OPEN else L['preview_foot']
    hint = ''
    if lang == 'ko':
        text, link = (('This page is also available in English.', 'Read in English →') if 'en' in alt
                      else ('Some of our articles are also in English.', 'See English articles →'))
        hint = (LANG_HINT_HTML.replace('@@TEXT@@', text).replace('@@LINK@@', link)
                .replace('@@HREF@@', esc(switch or './')))
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head_extra}<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="{L["locale"]}">
<meta property="og:site_name" content="{esc(L["site"])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{esc(og_image)}">
<meta property="og:url" content="{esc(url)}">
<link rel="stylesheet" href="{up}assets/style.css">
</head>
<body>
{bar}{hint}<header class="site-header"><div class="inner"><a class="brand" href="{home or './'}">{L["brand"]}</a><nav><a href="{home}about/">{L["about"]}</a><a href="{home}contact/">{L["contact"]}</a><a class="lang" href="{switch or './'}" hreflang="{other}">{L["switch"]}</a></nav></div></header>
<main>
{body_html}
</main>
<footer><div class="inner">© 2026 {L["owner"]}{foot} · <a href="{home}privacy/">{L["privacy"]}</a></div></footer>
{consent}{MAIL_SCRIPT}
</body>
</html>
'''


def check(doc, what):
    bad = [w for w in FORBIDDEN if w in doc]
    if bad:
        sys.exit(f'{what}: 공개하면 안 되는 말이 남음 → {bad}')


def render_posts(lang, src_dir, files, out, pairs):
    """글 페이지를 만들고, 첫 화면에 쓸 카드와 사이트 뿌리에서 본 주소 목록을 돌려준다."""
    L = LANG[lang]
    prefix = 'en/' if lang == 'en' else ''
    depth = 3 if lang == 'en' else 2
    up = '../' * depth
    posts = [load_post(os.path.join(src_dir, f)) for f in files]
    for p in posts:
        publicize(p, posts, lang)
    cards, paths = [], []
    for p in posts:
        images = []

        def copy_image(m):
            name = m.group(2).strip('<>')
            new = f"{p['slug']}{'-en' if lang == 'en' else ''}-{len(images) + 1}{os.path.splitext(name)[1].lower()}"
            shutil.copyfile(os.path.join(src_dir, name), os.path.join(out, 'images', new))
            images.append(new)
            return f'![{m.group(1)}]({up}images/{new})'

        body = re.sub(r'!\[([^\]]*)\]\((<[^>]+>|\S+)\)', copy_image, p['body'])
        if SITE_OPEN:
            cta = (f'<div class="cta"><p>{esc(L["cta"])}</p>'
                   f'{mail_button(L["subject"] + p["title"], "../../contact/", lang)}</div>')
        else:
            cta = (f'<div class="cta"><p>{esc(CTA_TEXT_PREVIEW)}</p>'
                   '<span class="btn disabled">견적 문의하기 (준비 중)</span></div>')
        content = (f'<p class="crumbs"><a href="../../">{L["back"]}</a> · <span class="tag">{esc(p["category"])}</span></p>\n'
                   f'<h1>{esc(p["title"])}</h1>\n' + md_to_html(body, cta))
        if '@@' in content:
            sys.exit(f"#{p['num']} ({lang}): 바꾸지 못한 표시가 남음")
        path = f"{prefix}posts/{p['slug']}/"
        alt = {l: f"{'en/' if l == 'en' else ''}posts/{p['slug']}/" for l in ('ko', 'en') if p['slug'] in pairs[l]}
        og = BASE_URL + 'images/' + images[0] if images else ''
        doc = page(f"{p['title']} | {L['site']}", p['desc'], content, depth, og, path, lang=lang, alt=alt)
        check(doc, f"#{p['num']} ({lang})")
        os.makedirs(os.path.join(out, path))
        open(os.path.join(out, path, 'index.html'), 'w', encoding='utf-8').write(doc)
        thumb = f'<img src="{"../" if lang == "en" else ""}images/{images[0]}" alt="">' if images else ''
        cards.append(f'<a class="card" href="posts/{p["slug"]}/">{thumb}<div class="body">'
                     f'<span class="tag">{esc(p["category"])}</span><h2>{esc(p["title"])}</h2>'
                     f'<p>{esc(p["desc"])}</p></div></a>')
        paths.append(path)
        print(f"#{p['num']} → {path} (그림 {len(images)}장)")
    first_image = BASE_URL + 'images/' + f"{posts[0]['slug']}{'-en' if lang == 'en' else ''}-1.png"
    return cards, paths, first_image


def render_pages(lang, page_dir, pages, out, first_image, pair_slugs):
    L = LANG[lang]
    prefix = 'en/' if lang == 'en' else ''
    depth = 2 if lang == 'en' else 1
    paths = []
    for name, slug, desc in pages:
        raw = open(os.path.join(page_dir, name), encoding='utf-8').read()
        title = re.match(r'^# (.+)$', raw, re.M).group(1).strip()
        body = re.sub(r'^# .+\n', '', raw, count=1)
        if slug == 'privacy' and not ANALYTICS_ID:      # 통계 도구를 아직 안 붙였으면 그 설명은 뺀다
            body = re.sub(r'(?ms)^## (?:방문 통계|Analytics)\n.*?(?=^## )', '', body)
        cta = ''
        if slug == 'contact':
            cta = (f'<div class="cta"><p>{L["email"]}: {mail_text(lang)}</p>'
                   f'{mail_button(L["subject"] + L["general"], "#", lang)}</div>')
        content = f'<h1>{esc(title)}</h1>\n' + md_to_html(body, cta)
        if '@@' in content:
            sys.exit(f'{name}: 바꾸지 못한 표시가 남음')
        path = f'{prefix}{slug}/'
        alt = {'ko': f'{slug}/', 'en': f'en/{slug}/'} if slug in pair_slugs else {}
        doc = page(f'{title} | {L["site"]}', desc, content, depth, first_image, path, og_type='website', lang=lang, alt=alt)
        check(doc, name)
        os.makedirs(os.path.join(out, path))
        open(os.path.join(out, path, 'index.html'), 'w', encoding='utf-8').write(doc)
        paths.append(path)
        print(f'{name} → {path}')
    return paths


def render_home(lang, cards, out, first_image):
    L = LANG[lang]
    contact = 'contact/'
    home_cta = (f'<div class="cta"><p>{esc(L["home_cta"])}</p>'
                f'{mail_button(L["subject"] + L["general"], contact, lang)}</div>' if SITE_OPEN else '')
    body = (f'<section class="hero"><h1>{esc(L["site"])}</h1><p>{esc(L["intro"])}</p></section>\n'
            '<section class="cards">' + ''.join(cards) + '</section>\n'
            f'<p class="more">{esc(L["more"])}</p>\n' + home_cta)
    path = 'en/' if lang == 'en' else ''
    doc = page(L['site'], L['intro'], body, 1 if lang == 'en' else 0, first_image, path,
               og_type='website', lang=lang, alt={'ko': '', 'en': 'en/'})
    check(doc, f'첫 화면 ({lang})')
    open(os.path.join(out, path, 'index.html'), 'w', encoding='utf-8').write(doc)
    print(f'{path}index.html 완료')
    return path


def build(src, out):
    en_src = os.path.join(src, EN_DIR)
    slugs = {'ko': {load_post(os.path.join(src, f))['slug'] for f in POSTS},
             'en': {load_post(os.path.join(en_src, f))['slug'] for f in EN_POSTS}}
    page_pairs = {slug for _, slug, _ in PAGES} & {slug for _, slug, _ in EN_PAGES}
    for d in ('posts', 'images', 'en') + tuple(slug for _, slug, _ in PAGES):
        shutil.rmtree(os.path.join(out, d), ignore_errors=True)
    for d in ('posts', 'images', 'en/posts'):
        os.makedirs(os.path.join(out, d))
    open(os.path.join(out, '.nojekyll'), 'w').close()
    cname = os.path.join(out, 'CNAME')
    if CUSTOM_DOMAIN:
        open(cname, 'w').write(CUSTOM_DOMAIN + '\n')
    elif os.path.exists(cname):
        os.remove(cname)

    paths = []
    for lang, src_dir, files, page_dir, pages in (('ko', src, POSTS, os.path.join(src, PAGES_DIR), PAGES),
                                                  ('en', en_src, EN_POSTS, os.path.join(en_src, PAGES_DIR), EN_PAGES)):
        if not files:
            continue
        cards, post_paths, first_image = render_posts(lang, src_dir, files, out, slugs)
        paths.append(render_home(lang, cards, out, first_image))
        paths += post_paths
        paths += render_pages(lang, page_dir, pages, out, first_image, page_pairs)

    robots, sitemap = os.path.join(out, 'robots.txt'), os.path.join(out, 'sitemap.xml')
    if SITE_OPEN:
        open(robots, 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}sitemap.xml\n')
        today = datetime.date.today().isoformat()
        open(sitemap, 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n'
                                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                 + ''.join(f'<url><loc>{esc(BASE_URL + p)}</loc><lastmod>{today}</lastmod></url>\n'
                                           for p in paths)
                                 + '</urlset>\n')
        print('robots.txt, sitemap.xml 완료')
    else:
        for f in (robots, sitemap):
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
