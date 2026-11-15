
"""Collect Google News RSS titles, using stdlib only. Run daily via GitHub Actions."""
import json, re, html, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
now = datetime.now(timezone.utc)

config = json.loads((ROOT / 'keywords.json').read_text(encoding='utf-8'))
path = ROOT / 'news.json'
existing = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []

by_url = {x['url']: x for x in existing}

for record in by_url.values():
    record.setdefault('first_seen', record.get('published', now.isoformat()))

# Search both spaced and unspaced versions of selected terms.
SPACING_GROUPS = [
    ('시니어테크', '시니어 테크'),
    ('실버테크', '실버 테크'),
    ('에이지테크', '에이지 테크'),
    ('키즈테크', '키즈 테크'),
    ('에듀테크', '에듀 테크'),
    ('돌봄로봇', '돌봄 로봇'),
    ('반려로봇', '반려 로봇'),
    ('교육로봇', '교육 로봇'),
    ('서비스로봇', '서비스 로봇'),
    ('AI교육로봇', 'AI 교육로봇', 'AI 교육 로봇'),
]

def search_variants(keyword):
    """Return original keyword plus known spacing variants."""
    variants = [keyword]
    normalized = re.sub(r'\s+', '', keyword).casefold()

    for group in SPACING_GROUPS:
        if any(re.sub(r'\s+', '', term).casefold() == normalized for term in group):
            variants.extend(group)

    return list(dict.fromkeys(variants))


for category, keywords in config.items():
    for keyword in keywords:
        for search_term in search_variants(keyword):
            query = f'"{search_term}" when:7d'
            params = urllib.parse.urlencode({
                'q': query,
                'hl': 'ko',
                'gl': 'KR',
                'ceid': 'KR:ko'
            })
            url = 'https://news.google.com/rss/search?' + params

            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; LemmyNewsMonitor/1.0)'
                    }
                )

                with urllib.request.urlopen(req, timeout=20) as response:
                    root = ET.fromstring(response.read())

                for item in root.findall('./channel/item'):
                    link = (item.findtext('link') or '').strip()
                    title = html.unescape((item.findtext('title') or '').strip())

                    if not link or not title:
                        continue

                    try:
                        published = parsedate_to_datetime(
                            item.findtext('pubDate')
                        ).astimezone(timezone.utc)
                    except Exception:
                        continue

                    if (
                        published < now - timedelta(days=31)
                        or published > now + timedelta(hours=2)
                    ):
                        continue

                    source = item.find('source')
                    publisher = source.text if source is not None else ''

                    if link not in by_url:
                        by_url[link] = {
                            'title': title,
                            'url': link,
                            'published': published.isoformat(),
                            'first_seen': now.isoformat(),
                            'source': publisher or '',
                            'categories': [category],
                            'keywords': [keyword]
                        }
                    else:
                        record = by_url[link]

                        if category not in record['categories']:
                            record['categories'].append(category)

                        if keyword not in record['keywords']:
                            record['keywords'].append(keyword)

            except Exception as exc:
                print(f'WARN {keyword} ({search_term}): {exc}')

            time.sleep(0.15)

# Keep all collected articles; do not delete older records.
result = sorted(
    by_url.values(),
    key=lambda x: x['published'],
    reverse=True
)

path.write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding='utf-8'
)

print(
    f'Updated {len(result)} records at {datetime.now(KST).isoformat()}'
)
