# trend_collector.py - 트렌드 키워드 수집

import logging
import time
import random
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    logger.warning("pytrends 미설치 → 폴백 데이터 사용")

from config import TRENDS_GEO, TRENDS_LANGUAGE, TRENDS_COUNT, CATEGORY_KEYWORDS


@dataclass
class TrendItem:
    keyword: str
    category: str
    score: int           # 0~100 상대 인기 점수
    related: list[str] = field(default_factory=list)
    source: str = "unknown"


def _detect_category(keyword: str) -> str:
    """키워드를 카테고리에 매핑"""
    kw_lower = keyword.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(k in kw_lower for k in keywords):
            return cat
    return "기본"


# ── Google Trends (pytrends) ──────────────────────────────

def fetch_google_trends(count: int = TRENDS_COUNT) -> list[TrendItem]:
    """pytrends로 실시간 인기 급상승 검색어 수집"""
    if not PYTRENDS_AVAILABLE:
        return []

    try:
        pytrends = TrendReq(hl=TRENDS_LANGUAGE, tz=540, timeout=(10, 25))
        # 실시간 트렌드 (일간 검색 트렌드)
        trending_df = pytrends.trending_searches(pn="south_korea")
        keywords = trending_df[0].tolist()[:count]

        results = []
        for i, kw in enumerate(keywords):
            score = max(10, 100 - i * 8)
            item = TrendItem(
                keyword=kw,
                category=_detect_category(kw),
                score=score,
                source="google_trends",
            )
            results.append(item)
            time.sleep(0.3)  # 요청 간 짧은 딜레이

        logger.info(f"Google Trends에서 {len(results)}개 키워드 수집 완료")
        return results

    except Exception as e:
        logger.warning(f"Google Trends 수집 실패: {e}")
        return []


# ── 네이버 실시간 검색어 스크래핑 ────────────────────────

def fetch_naver_trends(count: int = TRENDS_COUNT) -> list[TrendItem]:
    """네이버 데이터랩 급상승 검색어 스크래핑"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    try:
        # 네이버 DataLab 급상승 검색어
        url = "https://datalab.naver.com/keyword/realtimeList.naver"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".item_title")[:count]

        results = []
        for i, el in enumerate(items):
            kw = el.get_text(strip=True)
            if kw:
                score = max(10, 100 - i * 7)
                results.append(TrendItem(
                    keyword=kw,
                    category=_detect_category(kw),
                    score=score,
                    source="naver",
                ))

        logger.info(f"네이버에서 {len(results)}개 키워드 수집 완료")
        return results

    except Exception as e:
        logger.warning(f"네이버 스크래핑 실패: {e}")
        return []


# ── 멜론 차트 (음악 트렌드 보조) ─────────────────────────

def fetch_melon_chart(count: int = 5) -> list[TrendItem]:
    """멜론 TOP 100에서 음악 트렌드 키워드 수집"""
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        "Referer": "https://www.melon.com/",
    }
    try:
        url = "https://www.melon.com/chart/index.htm"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        song_items = soup.select(".rank01 .ellipsis")[:count]

        results = []
        for i, el in enumerate(song_items):
            kw = el.get_text(strip=True)
            if kw:
                results.append(TrendItem(
                    keyword=kw,
                    category="라이프스타일",
                    score=max(20, 80 - i * 10),
                    source="melon",
                ))

        return results

    except Exception as e:
        logger.debug(f"멜론 차트 수집 실패(선택 사항): {e}")
        return []


# ── 폴백: 샘플 트렌드 데이터 ─────────────────────────────

FALLBACK_TRENDS = [
    ("봄 메이크업 트렌드", "뷰티", 95),
    ("오늘 뭐먹지 집밥 레시피", "음식", 90),
    ("2024 봄 패션 코디", "패션", 85),
    ("제주도 여행 코스 추천", "여행", 82),
    ("홈카페 인테리어 아이디어", "라이프스타일", 78),
    ("AI 활용법 일상 꿀팁", "기술", 75),
    ("다이어트 운동 루틴", "라이프스타일", 70),
    ("카페 신메뉴 디저트", "음식", 65),
    ("스킨케어 루틴 추천", "뷰티", 60),
    ("국내 숨은 여행지", "여행", 55),
]


def get_fallback_trends(count: int = TRENDS_COUNT) -> list[TrendItem]:
    shuffled = random.sample(FALLBACK_TRENDS, min(count, len(FALLBACK_TRENDS)))
    return [
        TrendItem(keyword=kw, category=cat, score=sc, source="fallback")
        for kw, cat, sc in shuffled
    ]


# ── 공개 인터페이스 ───────────────────────────────────────

def collect_trends(count: int = TRENDS_COUNT) -> list[TrendItem]:
    """
    여러 소스에서 트렌드 수집 후 중복 제거하여 반환.
    모든 소스 실패 시 폴백 데이터 반환.
    """
    all_trends: list[TrendItem] = []

    # 1순위: Google Trends
    all_trends.extend(fetch_google_trends(count))

    # 2순위: 네이버 (Google 실패 또는 보충)
    if len(all_trends) < count:
        all_trends.extend(fetch_naver_trends(count))

    # 3순위: 멜론 (보충)
    if len(all_trends) < count:
        all_trends.extend(fetch_melon_chart(5))

    # 폴백
    if not all_trends:
        logger.warning("모든 수집 소스 실패 → 폴백 트렌드 데이터 사용")
        all_trends = get_fallback_trends(count)

    # 중복 키워드 제거 (첫 번째 우선)
    seen = set()
    unique = []
    for item in all_trends:
        key = item.keyword.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 점수 내림차순 정렬
    unique.sort(key=lambda x: x.score, reverse=True)
    return unique[:count]
