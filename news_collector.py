# news_collector.py - 실시간 뉴스 기사 수집

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FEEDPARSER_AVAILABLE = False  # Python 3.11+에서 sgmllib 제거로 비활성화

import os
from config import NEWS_FEEDS

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Cache-Control": "no-cache",
}

# ── 폴백 뉴스 데이터 ──────────────────────────────────────
# RSS 수집 실패 시 사용 (예: 네트워크 제한 환경)
FALLBACK_NEWS = {
    "연예": [
        {
            "title": "인기 드라마 OST 음원 차트 1위 등극, 팬들 열광",
            "summary": "최근 방영 중인 인기 드라마의 OST가 주요 음원 차트 1위를 차지했다. "
                      "해당 곡은 공개 하루 만에 멜론, 지니, 벅스 등 주요 스트리밍 플랫폼을 석권하며 "
                      "폭발적인 반응을 얻고 있다. 팬들은 SNS를 통해 뜨거운 관심을 보이고 있으며 "
                      "드라마 시청률도 덩달아 상승 중이다.",
            "url": "https://example.com/entertainment1",
            "image_url": None,
        },
        {
            "title": "글로벌 K팝 그룹, 월드투어 한국 콘서트 전석 매진",
            "summary": "세계적으로 인기를 끌고 있는 K팝 그룹이 월드투어 한국 공연 티켓이 "
                      "오픈 15분 만에 전석 매진됐다. 팬들의 뜨거운 관심 속에 추가 공연 개최 여부에도 "
                      "관심이 집중되고 있다.",
            "url": "https://example.com/entertainment2",
            "image_url": None,
        },
    ],
    "한국 사회": [
        {
            "title": "서울 수도권 폭우 예보, 기상청 '강한 집중호우 대비' 당부",
            "summary": "기상청은 이번 주말 서울 및 수도권 지역에 강한 집중호우가 예상된다고 발표했다. "
                      "시간당 최대 80mm 이상의 비가 내릴 수 있으며, 저지대 침수와 하천 범람에 대한 "
                      "각별한 주의가 요구된다. 서울시는 재난 대응 비상 체계를 가동했다.",
            "url": "https://example.com/society1",
            "image_url": None,
        },
        {
            "title": "정부, 내년 최저임금 결정 앞두고 노사 막판 협상 진행",
            "summary": "내년도 최저임금을 결정하기 위한 노사 간 막판 협상이 진행 중이다. "
                      "노동계는 대폭 인상을 요구하는 반면, 경영계는 동결 혹은 소폭 인상을 주장하며 "
                      "입장 차를 좁히지 못하고 있다. 최저임금위원회는 이번 주 안에 최종 결론을 낼 예정이다.",
            "url": "https://example.com/society2",
            "image_url": None,
        },
    ],
    "스포츠": [
        {
            "title": "한국 축구대표팀, 월드컵 예선 홈경기서 2-0 완승",
            "summary": "한국 축구대표팀이 월드컵 아시아 예선 홈경기에서 상대팀을 2-0으로 꺾고 "
                      "조 1위 자리를 굳혔다. 전반 선제골에 이어 후반 추가골로 완벽한 승리를 거둔 "
                      "대표팀은 다음 원정경기에서도 좋은 결과를 기대하고 있다.",
            "url": "https://example.com/sports1",
            "image_url": None,
        },
        {
            "title": "KBO 리그, 선두 다툼 치열... 오늘의 주요 경기 결과",
            "summary": "KBO 프로야구 페넌트레이스에서 선두 다툼이 더욱 치열해지고 있다. "
                      "어제 경기에서 상위권 팀들이 모두 승리를 거두며 순위 변동은 없었지만 "
                      "게임 차는 더욱 좁혀졌다. 올스타 브레이크 이후 후반기 레이스가 더욱 흥미로워질 전망이다.",
            "url": "https://example.com/sports2",
            "image_url": None,
        },
    ],
    "주요 세계 이슈": [
        {
            "title": "중동 정세 긴장 고조... 국제사회 외교적 해결 촉구",
            "summary": "중동 지역의 군사적 긴장이 다시 고조되면서 국제사회의 우려가 커지고 있다. "
                      "미국, 유럽연합, 유엔 등 주요 국제기구는 모든 당사자들에게 자제를 촉구하며 "
                      "외교적 대화를 통한 해결을 요청했다. 유가와 금융시장도 불안한 움직임을 보이고 있다.",
            "url": "https://example.com/world1",
            "image_url": None,
        },
        {
            "title": "G7 정상회담, AI 규제·기후변화·경제협력 공동선언 채택",
            "summary": "주요 7개국(G7) 정상회담이 마무리되며 인공지능 규제 강화, 기후변화 대응, "
                      "글로벌 공급망 안정화 등을 담은 공동선언을 채택했다. 특히 AI 거버넌스 부문에서 "
                      "구체적인 국제 협력 프레임워크가 합의되어 주목받고 있다.",
            "url": "https://example.com/world2",
            "image_url": None,
        },
    ],
}


@dataclass
class NewsArticle:
    title: str
    summary: str        # RSS에서 온 요약
    body: str           # 기사 본문 (스크래핑)
    url: str
    image_url: Optional[str]
    category: str
    source: str
    published: str = ""


def _clean_text(text: str) -> str:
    """HTML 태그 및 여분 공백 제거"""
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fetch_og_image(url: str) -> Optional[str]:
    """기사 URL에서 og:image 메타 태그 추출"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        if not resp.ok:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # og:image 우선
        for prop in ("og:image", "twitter:image", "twitter:image:src"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content", "").startswith("http"):
                return tag["content"]

        # article 내 첫 번째 img
        article = soup.find("article") or soup.find(class_=re.compile(r"article|content|body", re.I))
        if article:
            img = article.find("img")
            if img:
                src = img.get("src") or img.get("data-src", "")
                if src.startswith("http"):
                    return src
    except Exception as e:
        logger.debug(f"og:image 추출 실패 ({url[:60]}): {e}")
    return None


def _fetch_article_body(url: str, max_chars: int = 1500) -> str:
    """기사 본문 텍스트 스크래핑"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        if not resp.ok:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()

        # article 태그 우선
        article = (
            soup.find("article")
            or soup.find(class_=re.compile(r"article.?body|article.?content|newsview|news.?content", re.I))
            or soup.find("main")
        )
        if article:
            text = article.get_text(separator=" ", strip=True)
        else:
            text = soup.get_text(separator=" ", strip=True)

        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as e:
        logger.debug(f"본문 스크래핑 실패 ({url[:60]}): {e}")
    return ""


def _parse_rss_with_feedparser(feed_url: str, count: int, category: str) -> list[NewsArticle]:
    """feedparser로 RSS 파싱"""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:count * 2]:  # 필터링 여유분
            title = _clean_text(entry.get("title", "")).strip()
            if not title or len(title) < 5:
                continue

            summary = _clean_text(entry.get("summary", "") or entry.get("description", ""))
            url = entry.get("link", "")
            published = entry.get("published", "")

            # Google News는 실제 기사 URL로 리다이렉트됨
            article = NewsArticle(
                title=title,
                summary=summary[:600],
                body="",
                url=url,
                image_url=None,
                category=category,
                source=feed.feed.get("title", "rss"),
                published=published,
            )
            articles.append(article)
            if len(articles) >= count:
                break
        return articles
    except Exception as e:
        logger.warning(f"feedparser RSS 파싱 실패 ({feed_url[:60]}): {e}")
        return []


def _parse_rss_with_requests(feed_url: str, count: int, category: str) -> list[NewsArticle]:
    """feedparser 없을 때 requests로 XML 파싱"""
    try:
        import xml.etree.ElementTree as ET
        resp = requests.get(feed_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = {"media": "http://search.yahoo.com/mrss/"}

        articles = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            summary = _clean_text(item.findtext("description") or "")
            url = item.findtext("link") or ""
            published = item.findtext("pubDate") or ""

            article = NewsArticle(
                title=title,
                summary=summary[:600],
                body="",
                url=url,
                image_url=None,
                category=category,
                source="rss",
                published=published,
            )
            articles.append(article)
            if len(articles) >= count:
                break
        return articles
    except Exception as e:
        logger.warning(f"RSS XML 파싱 실패 ({feed_url[:60]}): {e}")
        return []


def fetch_category_news(category: str, count: int = 5) -> list[NewsArticle]:
    """특정 카테고리의 뉴스 기사 수집"""
    feed_urls = NEWS_FEEDS.get(category, [])
    articles: list[NewsArticle] = []

    for feed_url in feed_urls:
        if len(articles) >= count:
            break
        if FEEDPARSER_AVAILABLE:
            new_items = _parse_rss_with_feedparser(feed_url, count, category)
        else:
            new_items = _parse_rss_with_requests(feed_url, count, category)
        articles.extend(new_items)

    # 중복 제목 제거
    seen = set()
    unique = []
    for a in articles:
        key = a.title[:30].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    logger.info(f"[{category}] {len(unique)}개 기사 수집")
    return unique[:count]


def enrich_article(article: NewsArticle) -> NewsArticle:
    """기사 URL에서 이미지와 본문을 추가 수집"""
    if not article.url:
        return article

    # 이미지 수집
    if not article.image_url:
        article.image_url = _fetch_og_image(article.url)
        if article.image_url:
            logger.debug(f"이미지 획득: {article.image_url[:60]}")

    # 본문이 짧으면 스크래핑 시도
    if len(article.summary) < 100:
        body = _fetch_article_body(article.url)
        if body:
            article.body = body
            if not article.summary:
                article.summary = body[:300]

    time.sleep(0.5)  # 서버 부하 방지
    return article


def _get_fallback_articles(category: str, count: int) -> list[NewsArticle]:
    """폴백 샘플 뉴스 반환 (RSS 수집 실패 시)"""
    items = FALLBACK_NEWS.get(category, FALLBACK_NEWS.get("한국 사회", []))
    articles = []
    for d in items[:count]:
        articles.append(NewsArticle(
            title=d["title"],
            summary=d["summary"],
            body=d["summary"],
            url=d["url"],
            image_url=d.get("image_url"),
            category=category,
            source="fallback",
        ))
    return articles


def fetch_naver_news(category: str, count: int = 5) -> list[NewsArticle]:
    """네이버 뉴스 검색 API (NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 필요)"""
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return []

    NAVER_QUERY = {
        "연예": "연예 연예인",
        "한국 사회": "한국 사회 정치",
        "스포츠": "스포츠 축구 야구",
        "주요 세계 이슈": "세계 국제 이슈",
    }
    query = NAVER_QUERY.get(category, category)

    try:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            params={"query": query, "display": count, "sort": "date"},
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        articles = []
        for item in items:
            title = _clean_text(item.get("title", ""))
            summary = _clean_text(item.get("description", ""))
            articles.append(NewsArticle(
                title=title,
                summary=summary[:600],
                body="",
                url=item.get("link", ""),
                image_url=None,
                category=category,
                source="naver_api",
                published=item.get("pubDate", ""),
            ))
        logger.info(f"[{category}] 네이버 API {len(articles)}개 수집")
        return articles
    except Exception as e:
        logger.debug(f"네이버 API 실패: {e}")
        return []


def collect_news_by_category(categories: list[str], per_category: int = 3) -> dict[str, list[NewsArticle]]:
    """여러 카테고리 뉴스 수집 후 반환"""
    result = {}
    for cat in categories:
        # 1순위: 네이버 API
        articles = fetch_naver_news(cat, count=per_category)

        # 2순위: RSS
        if not articles:
            articles = fetch_category_news(cat, count=per_category)

        # 3순위: 폴백 샘플 데이터
        if not articles:
            logger.warning(f"[{cat}] RSS 수집 실패 → 폴백 데이터 사용")
            articles = _get_fallback_articles(cat, per_category)

        # 상위 기사 1개에 대해 이미지/본문 보강
        if articles and articles[0].source not in ("fallback",):
            articles[0] = enrich_article(articles[0])

        result[cat] = articles
    return result
