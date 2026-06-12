# content_generator.py - 뉴스 기사 기반 카드뉴스 콘텐츠 생성

import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from typing import Optional

from news_collector import NewsArticle
from config import (
    COLOR_PALETTES, CATEGORY_HASHTAGS, BASE_HASHTAGS,
    CARDS_RANGE, ANTHROPIC_API_KEY,
)

logger = logging.getLogger(__name__)


@dataclass
class CardSlide:
    slide_type: str          # "cover" | "bullets" | "detail" | "cta"
    headline: str            # 메인 텍스트
    subheadline: str = ""    # 서브 텍스트
    bullets: list[str] = field(default_factory=list)
    label: str = ""          # 상단 레이블 (예: "스포츠 | 오늘의 이슈")


@dataclass
class CardContent:
    category: str
    article_title: str
    slides: list[CardSlide]    # 1~4장
    caption: str               # Instagram 캡션 (요약 + 해시태그)
    hashtags: list[str]
    image_url: Optional[str]   # 배경 이미지 URL


# ── Claude API 기반 콘텐츠 생성 ───────────────────────────

def _generate_with_claude(article: NewsArticle, num_cards: int) -> Optional[dict]:
    """Claude API로 카드뉴스 JSON 생성"""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        text_input = article.body or article.summary
        prompt = f"""당신은 한국 인스타그램 카드뉴스 작성 전문가입니다.
아래 뉴스 기사를 바탕으로 {num_cards}장짜리 카드뉴스 콘텐츠를 JSON으로 생성하세요.

카테고리: {article.category}
제목: {article.title}
내용: {text_input[:800]}

규칙:
- 모든 텍스트는 반드시 한국어
- 헤드라인은 임팩트 있게 20자 이내
- 불릿은 핵심만, 한 줄 30자 이내
- 캡션은 2~3문장 자연스러운 요약

반드시 아래 JSON 형식만 반환하세요:
{{
  "slides": [
    {{
      "slide_type": "cover",
      "headline": "강렬한 헤드라인",
      "subheadline": "부제목 (15자 이내)",
      "label": "{article.category} | 오늘의 이슈"
    }}{"," if num_cards > 1 else ""}
    {', '.join(['''{{
      "slide_type": "bullets",
      "headline": "핵심 포인트",
      "bullets": ["포인트 1", "포인트 2", "포인트 3"],
      "label": "주요 내용"
    }}''' for _ in range(min(num_cards - 1, 2))])}{"," if num_cards >= 4 else ""}
    {'''{{
      "slide_type": "cta",
      "headline": "한 줄 핵심 메시지",
      "subheadline": "여러분의 생각은?",
      "label": "오늘의 한마디"
    }}''' if num_cards >= 4 else ""}
  ],
  "caption": "인스타그램 캡션 요약 2~3문장",
  "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3", "#해시태그4", "#해시태그5"]
}}"""

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # JSON 블록 추출
        match = re.search(r"\{[\s\S]+\}", raw)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.warning(f"Claude API 콘텐츠 생성 실패: {e}")
    return None


# ── 템플릿 기반 폴백 콘텐츠 생성 ─────────────────────────

COVER_TEMPLATES = {
    "연예": [
        "{title}",
        "지금 연예계 핫이슈",
        "오늘 터진 연예 뉴스",
    ],
    "한국 사회": [
        "오늘 한국 사회 이슈",
        "지금 한국에서 일어난 일",
        "놓치면 안 될 사회 이슈",
    ],
    "스포츠": [
        "오늘의 스포츠 소식",
        "핫한 스포츠 이슈",
        "스포츠 오늘의 하이라이트",
    ],
    "주요 세계 이슈": [
        "세계가 주목하는 지금",
        "오늘의 세계 이슈",
        "글로벌 핫 이슈",
    ],
    "기본": [
        "오늘의 주요 이슈",
        "지금 뜨는 뉴스",
        "놓치면 아쉬운 오늘의 소식",
    ],
}


def _split_into_bullets(text: str, count: int = 3) -> list[str]:
    """텍스트를 문장 단위로 분리하여 불릿 생성"""
    sentences = re.split(r"[.。!?]\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    if not sentences:
        return [text[:60]]

    result = []
    for s in sentences[:count]:
        line = s[:50] + ("…" if len(s) > 50 else "")
        result.append(line)
    while len(result) < count and result:
        result.append(result[-1])
    return result[:count]


def _generate_template_content(article: NewsArticle, num_cards: int) -> dict:
    """템플릿 기반 콘텐츠 생성 (API 폴백)"""
    cat = article.category
    tmpl_covers = COVER_TEMPLATES.get(cat, COVER_TEMPLATES["기본"])

    slides = []

    # 카드 1: 커버
    slides.append({
        "slide_type": "cover",
        "headline": article.title[:40] + ("…" if len(article.title) > 40 else ""),
        "subheadline": random.choice(tmpl_covers),
        "label": f"{cat} | 오늘의 이슈",
        "bullets": [],
    })

    # 카드 2: 불릿 요약
    if num_cards >= 2:
        text = article.body or article.summary
        bullets = _split_into_bullets(text, 3)
        slides.append({
            "slide_type": "bullets",
            "headline": "핵심 내용",
            "subheadline": "",
            "label": "주요 내용",
            "bullets": bullets,
        })

    # 카드 3: 추가 내용
    if num_cards >= 3 and len(article.summary) > 150:
        more_text = (article.body or article.summary)[200:]
        bullets2 = _split_into_bullets(more_text, 3)
        slides.append({
            "slide_type": "detail",
            "headline": "더 알아보기",
            "subheadline": "",
            "label": "상세 내용",
            "bullets": bullets2,
        })

    # 카드 4: CTA
    if num_cards >= 4:
        slides.append({
            "slide_type": "cta",
            "headline": "여러분의 생각은?",
            "subheadline": "댓글로 의견을 남겨주세요",
            "label": "오늘의 한마디",
            "bullets": [],
        })

    caption = f"{article.title}\n\n{article.summary[:200]}" if article.summary else article.title
    hashtags = ["#뉴스", "#이슈", f"#{cat}"]

    return {
        "slides": slides[:num_cards],
        "caption": caption,
        "hashtags": hashtags,
    }


# ── 공개 인터페이스 ───────────────────────────────────────

def _determine_num_cards(article: NewsArticle, category: str) -> int:
    """기사 길이와 카테고리 기반으로 카드 수 결정"""
    min_c, max_c = CARDS_RANGE.get(category, (1, 4))
    text_len = len(article.body or article.summary or "")

    if text_len < 100:
        return min_c
    elif text_len < 300:
        return min(min_c + 1, max_c)
    elif text_len < 600:
        return min(min_c + 2, max_c)
    else:
        return max_c


def _build_hashtags(category: str, extra_tags: list[str]) -> list[str]:
    tags = set(BASE_HASHTAGS)
    tags.update(CATEGORY_HASHTAGS.get(category, []))
    tags.update(extra_tags)
    return list(tags)[:20]


def generate_card_content(article: NewsArticle) -> CardContent:
    """NewsArticle → CardContent 생성 (Claude API 우선, 템플릿 폴백)"""
    cat = article.category
    num_cards = _determine_num_cards(article, cat)

    # Claude API 시도
    raw = _generate_with_claude(article, num_cards)

    # 폴백
    if not raw:
        raw = _generate_template_content(article, num_cards)

    # 슬라이드 파싱
    slides = []
    for s in raw.get("slides", [])[:num_cards]:
        slides.append(CardSlide(
            slide_type=s.get("slide_type", "bullets"),
            headline=s.get("headline", article.title[:40]),
            subheadline=s.get("subheadline", ""),
            bullets=[b for b in s.get("bullets", []) if b],
            label=s.get("label", cat),
        ))

    if not slides:
        slides = [CardSlide(
            slide_type="cover",
            headline=article.title[:40],
            subheadline="",
            label=cat,
        )]

    # 캡션 구성
    caption_body = raw.get("caption", article.summary[:200] or article.title)
    extra_tags = raw.get("hashtags", [])
    hashtags = _build_hashtags(cat, extra_tags)

    caption = f"{caption_body}\n\n" + " ".join(hashtags[:15])

    return CardContent(
        category=cat,
        article_title=article.title,
        slides=slides,
        caption=caption,
        hashtags=hashtags,
        image_url=article.image_url,
    )
