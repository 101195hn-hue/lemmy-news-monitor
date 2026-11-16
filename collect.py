
"""Collect relevant robot news from Google News RSS."""
import json
import re
import html
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
now = datetime.now(timezone.utc)

config = json.loads(
    (ROOT / "keywords.json").read_text(encoding="utf-8")
)

path = ROOT / "news.json"
existing = (
    json.loads(path.read_text(encoding="utf-8"))
    if path.exists() else []
)

# Preserve all previously collected articles.
by_url = {item["url"]: item for item in existing}

for record in by_url.values():
    record.setdefault(
        "first_seen",
        record.get("published", now.isoformat())
    )

# Known spelling/spacing variants.
SPACING_GROUPS = [
    ("시니어테크", "시니어 테크"),
    ("실버테크", "실버 테크"),
    ("에이지테크", "에이지 테크"),
    ("키즈테크", "키즈 테크"),
    ("에듀테크", "에듀 테크"),
    ("돌봄로봇", "돌봄 로봇"),
    ("반려로봇", "반려 로봇"),
    ("교육로봇", "교육 로봇"),
    ("서비스로봇", "서비스 로봇"),
    ("AI교육로봇", "AI 교육로봇", "AI 교육 로봇"),
]

def normalize(value):
    return re.sub(r"\s+", "", value).casefold()

def search_variants(keyword):
    variants = [keyword]
    normalized = normalize(keyword)

    for group in SPACING_GROUPS:
        if any(normalize(term) == normalized for term in group):
            variants.extend(group)

    return list(dict.fromkeys(variants))

# Direct competitors and relevant product names.
COMPETITORS = [
    "효돌",
    "다솜K",
    "케미프렌즈",
    "초롱이",
    "LOVOT",
    "ElliQ",
    "Miko 로봇",
]

# Terms that indicate relevance to LEMMY.
ROBOT_TERMS = [
    "로봇", "robot", "robotics",
    "로보틱스", "휴머노이드",
    "소셜로봇", "반려로봇",
    "돌봄로봇", "교육로봇",
    "서비스로봇", "가정용로봇",
    "스마트토이",
]

CARE_TERMS = [
    "시니어테크", "실버테크", "에이지테크",
    "고령친화", "고령자", "노인",
    "어르신", "시니어", "실버타운",
    "요양", "돌봄", "말벗",
    "독거노인", "노인복지",
]

EDUCATION_TERMS = [
    "키즈테크", "에듀테크",
    "유아교육", "어린이", "유아",
    "영어교육", "영어학습",
    "AI학습", "AI교육",
    "교육용AI", "교육용로봇",
    "학습로봇",
]

BUSINESS_TERMS = [
    "로봇산업", "로봇시장",
    "로봇기업", "로봇사업",
    "로봇정책", "로봇지원사업",
    "로봇실증", "로봇렌탈",
    "로봇출시", "로봇판매",
    "로봇보급", "로봇전시회",
]

def contains_any(title, terms):
    normalized_title = normalize(title)
    return any(
        normalize(term) in normalized_title
        for term in terms
    )

def is_relevant(title, keyword, category):
    """
    Conservative title-based relevance filter.
    Existing articles are never deleted.
    """

    # Keep named competitor/product articles
    # when the title actually mentions that product.
    if contains_any(title, COMPETITORS):
        return True

    has_robot = contains_any(title, ROBOT_TERMS)
    has_care = contains_any(title, CARE_TERMS)
    has_education = contains_any(title, EDUCATION_TERMS)
    has_business = contains_any(title, BUSINESS_TERMS)

    # Robot-related news is relevant to product/industry monitoring.
    if has_robot or has_business:
        return True

    # Care and education technology can matter
    # even when the word "robot" is absent.
    if has_care or has_education:
        return True

    # Keep articles explicitly mentioning a registered
    # multiword keyword when no other signal is available.
    # This reduces accidental losses from niche terms.
    if len(normalize(keyword)) >= 5:
        if normalize(keyword) in normalize(title):
            return True

    return False


new_count = 0
skipped_count = 0
error_count = 0

for category, keywords in config.items():
    for keyword in keywords:
        for search_term in search_variants(keyword):

            query = f'"{search_term}" when:7d'

            params = urllib.parse.urlencode({
                "q": query,
                "hl": "ko",
                "gl": "KR",
                "ceid": "KR:ko"
            })

            url = (
                "https://news.google.com/rss/search?"
                + params
            )

            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent":
                        "Mozilla/5.0 (compatible; LemmyNewsMonitor/1.0)"
                    }
                )

                with urllib.request.urlopen(
                    req, timeout=20
                ) as response:
                    root = ET.fromstring(response.read())

                for item in root.findall("./channel/item"):

                    link = (
                        item.findtext("link") or ""
                    ).strip()

                    title = html.unescape(
                        (item.findtext("title") or "").strip()
                    )

                    if not link or not title:
                        continue

                    try:
                        published = parsedate_to_datetime(
                            item.findtext("pubDate")
                        ).astimezone(timezone.utc)
                    except Exception:
                        continue

                    if (
                        published < now - timedelta(days=31)
                        or published > now + timedelta(hours=2)
                    ):
                        continue

                    # Filter only newly encountered articles.
                    # Existing records remain untouched.
                    if link not in by_url:
                        if not is_relevant(
                            title, keyword, category
                        ):
                            skipped_count += 1
                            continue

                    source = item.find("source")
                    publisher = (
                        source.text
                        if source is not None else ""
                    )

                    if link not in by_url:
                        by_url[link] = {
                            "title": title,
                            "url": link,
                            "published": published.isoformat(),
                            "first_seen": now.isoformat(),
                            "source": publisher or "",
                            "categories": [category],
                            "keywords": [keyword]
                        }
                        new_count += 1
                    else:
                        record = by_url[link]

                        if category not in record["categories"]:
                            record["categories"].append(category)

                        if keyword not in record["keywords"]:
                            record["keywords"].append(keyword)

            except Exception as exc:
                error_count += 1
                print(
                    f"WARN {keyword} ({search_term}): {exc}"
                )

            time.sleep(0.15)

result = sorted(
    by_url.values(),
    key=lambda x: x["published"],
    reverse=True
)

path.write_text(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print(
    f"Updated {len(result)} total records "
    f"at {datetime.now(KST).isoformat()}"
)

print(
    f"New articles: {new_count}, "
    f"Filtered matches: {skipped_count}, "
    f"Request errors: {error_count}"
)
