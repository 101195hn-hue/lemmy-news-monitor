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
for category, keywords in config.items():
    for keyword in keywords:
        query = f'"{keyword}" when:7d'
        params = urllib.parse.urlencode({'q': query, 'hl':'ko', 'gl':'KR', 'ceid':'KR:ko'})
        url = 'https://news.google.com/rss/search?' + params
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; LemmyNewsMonitor/1.0)'})
            with urllib.request.urlopen(req, timeout=20) as response:
                root = ET.fromstring(response.read())
            for item in root.findall('./channel/item'):
                link = (item.findtext('link') or '').strip()
                title = html.unescape((item.findtext('title') or '').strip())
                if not link or not title: continue
                try: published = parsedate_to_datetime(item.findtext('pubDate')).astimezone(timezone.utc)
                except Exception: continue
                if published < now - timedelta(days=31) or published > now + timedelta(hours=2): continue
                source = item.find('source')
                publisher = source.text if source is not None else ''
                if link not in by_url:
                    by_url[link] = {'title': title, 'url': link, 'published': published.isoformat(), 'source': publisher or '', 'categories': [category], 'keywords': [keyword]}
                else:
                    record = by_url[link]
                    if category not in record['categories']: record['categories'].append(category)
                    if keyword not in record['keywords']: record['keywords'].append(keyword)
        except Exception as exc:
            print(f'WARN {keyword}: {exc}')
        time.sleep(0.15)
cutoff = now - timedelta(days=90)
result = sorted((x for x in by_url.values() if datetime.fromisoformat(x['published']) >= cutoff), key=lambda x: x['published'], reverse=True)
path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Updated {len(result)} records at {datetime.now(KST).isoformat()}')
