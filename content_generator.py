# content_generator.py - 트렌드 기반 카드뉴스 콘텐츠 생성

import random
import re
from dataclasses import dataclass, field

from trend_collector import TrendItem
from config import BASE_HASHTAGS, CATEGORY_KEYWORDS


@dataclass
class CardContent:
    keyword: str
    category: str
    title: str
    subtitle: str
    bullets: list[str]          # 본문 포인트 (4~6개)
    cta: str                    # Call to Action
    hashtags: list[str]
    emoji_accent: str           # 카드 상단 이모지


# ── 카테고리별 템플릿 ─────────────────────────────────────

TEMPLATES = {
    "뷰티": {
        "emojis": ["✨", "💄", "🌸", "💅", "🪞"],
        "title_formats": [
            "요즘 난리난 {kw} 완전 정복",
            "{kw} 트렌드, 이것만 알면 돼",
            "올봄 필수템! {kw} 추천",
            "{kw} 제대로 하는 법",
        ],
        "subtitles": [
            "SNS를 뒤흔든 뷰티 트렌드 총정리",
            "뷰티 덕후들이 선택한 꿀템 리스트",
            "지금 당장 따라 해야 할 뷰티 루틴",
        ],
        "bullet_templates": [
            "피부 타입별 맞춤 {kw} 방법",
            "가성비 끝판왕 {kw} 추천 아이템",
            "SNS에서 난리난 {kw} 활용법",
            "전문가가 알려주는 {kw} 꿀팁",
            "계절별 {kw} 루틴 변경 포인트",
            "{kw} 할 때 절대 하지 말아야 할 것",
        ],
        "ctas": [
            "저장하고 나중에 따라 해봐요!",
            "좋아요와 팔로우로 응원해주세요 💕",
            "댓글로 여러분의 {kw} 팁도 공유해요!",
        ],
        "hashtag_extras": ["#뷰티", "#메이크업", "#스킨케어", "#뷰티팁", "#화장법"],
    },
    "패션": {
        "emojis": ["👗", "🛍️", "💜", "✨", "🖤"],
        "title_formats": [
            "{kw} 스타일링 완벽 가이드",
            "지금 당장 도전! {kw} 코디법",
            "{kw}으로 완성하는 데일리룩",
            "패피들의 선택, {kw} 트렌드",
        ],
        "subtitles": [
            "이번 시즌 꼭 알아야 할 패션 키워드",
            "스타일리스트가 픽한 무조건 예쁜 조합",
            "트렌디하게 입고 싶다면 여기 주목",
        ],
        "bullet_templates": [
            "{kw} 아이템 베스트 5 추천",
            "체형별 {kw} 스타일링 꿀팁",
            "예산별 {kw} 쇼핑 리스트",
            "연령대별 {kw} 코디 제안",
            "{kw} 컬러 매칭 가이드",
            "오피스룩부터 캐주얼까지 {kw} 활용",
        ],
        "ctas": [
            "팔로우하고 매일 스타일 업데이트 받아요!",
            "어떤 스타일이 제일 예뻐요? 댓글로!",
            "저장해두고 쇼핑할 때 참고하세요 🛍️",
        ],
        "hashtag_extras": ["#패션", "#오오티디", "#코디", "#스타일", "#패션피플"],
    },
    "음식": {
        "emojis": ["🍽️", "😋", "🔥", "🍜", "☕"],
        "title_formats": [
            "{kw} 맛집 & 레시피 총정리",
            "요즘 핫한 {kw} 완벽 가이드",
            "집에서 만드는 {kw} 레시피",
            "{kw} 먹방 리뷰 & 추천",
        ],
        "subtitles": [
            "지금 SNS에서 가장 많이 먹는 음식",
            "미식가들이 인정한 맛집 & 레시피",
            "한 번만 먹으면 중독되는 그 맛",
        ],
        "bullet_templates": [
            "{kw} 맛집 베스트 추천 리스트",
            "{kw} 레시피 재료 & 만드는 법",
            "{kw} 칼로리 & 영양 정보",
            "{kw} 관련 인스타 핫플 소개",
            "{kw} 배달 꿀팁 & 주문법",
            "{kw}와 어울리는 음료 페어링",
        ],
        "ctas": [
            "드셔보셨나요? 댓글로 후기 남겨요!",
            "저장하고 주말에 도전해보세요 😋",
            "팔로우하면 매일 맛집 정보 드려요!",
        ],
        "hashtag_extras": ["#맛집", "#음식", "#먹스타그램", "#레시피", "#맛스타그램"],
    },
    "여행": {
        "emojis": ["✈️", "🗺️", "🌊", "🏔️", "📸"],
        "title_formats": [
            "{kw} 완벽 여행 가이드",
            "지금 당장 떠나고 싶은 {kw}",
            "{kw} 여행 꿀팁 총정리",
            "{kw}에서 꼭 해야 할 것들",
        ],
        "subtitles": [
            "이번 연휴 여기 어때요?",
            "여행 고수들만 아는 숨은 명소",
            "인생샷 건지는 여행지 추천",
        ],
        "bullet_templates": [
            "{kw} 추천 여행 코스 & 일정",
            "{kw} 숙소 선택 꿀팁",
            "{kw}에서 먹어야 할 현지 음식",
            "{kw} 교통편 & 이동 방법",
            "{kw} 여행 예산 계획 가이드",
            "{kw} 인생샷 포토스팟 리스트",
        ],
        "ctas": [
            "다음 여행지로 저장해두세요 ✈️",
            "가보셨나요? 후기 댓글로 공유해요!",
            "팔로우하고 여행 정보 계속 받아가요!",
        ],
        "hashtag_extras": ["#여행", "#국내여행", "#여행스타그램", "#여행꿀팁", "#여행지추천"],
    },
    "라이프스타일": {
        "emojis": ["🌿", "💚", "🏠", "📚", "🧘"],
        "title_formats": [
            "{kw} 완전 정복 가이드",
            "삶의 질이 올라가는 {kw} 루틴",
            "{kw}으로 바꾸는 일상",
            "요즘 핫한 {kw} 트렌드",
        ],
        "subtitles": [
            "작은 변화가 만드는 큰 차이",
            "삶의 질을 높이는 라이프스타일 팁",
            "지금 당장 실천할 수 있는 꿀팁",
        ],
        "bullet_templates": [
            "{kw} 시작하는 방법 단계별 안내",
            "{kw} 관련 추천 아이템 & 도구",
            "{kw} 효과 극대화 꿀팁",
            "초보자를 위한 {kw} 입문 가이드",
            "{kw} 꾸준히 하는 동기부여 방법",
            "{kw}와 함께하는 하루 루틴 설계",
        ],
        "ctas": [
            "오늘부터 시작해봐요! 응원할게요 💚",
            "저장하고 오늘 바로 실천해보세요!",
            "여러분의 {kw} 팁도 댓글로 공유해요!",
        ],
        "hashtag_extras": ["#라이프스타일", "#일상", "#자기계발", "#힐링", "#루틴"],
    },
    "기술": {
        "emojis": ["🤖", "💡", "📱", "⚡", "🔬"],
        "title_formats": [
            "{kw} 완벽 활용 가이드",
            "몰랐으면 손해! {kw} 꿀팁",
            "{kw} 제대로 쓰는 법",
            "지금 당장 써봐야 할 {kw}",
        ],
        "subtitles": [
            "테크 트렌드 한눈에 정리",
            "일상을 바꾸는 기술 활용법",
            "생산성 10배 높이는 디지털 꿀팁",
        ],
        "bullet_templates": [
            "{kw} 주요 기능 & 장점 소개",
            "{kw} 초보자 시작 가이드",
            "{kw} 활용 실전 꿀팁 모음",
            "{kw} 관련 무료 도구 & 앱 추천",
            "{kw} 보안 & 개인정보 주의사항",
            "{kw} 최신 업데이트 & 변경사항",
        ],
        "ctas": [
            "팔로우하고 최신 기술 트렌드 받아요 🤖",
            "써봤나요? 후기 댓글로 알려주세요!",
            "저장하고 나중에 천천히 읽어보세요!",
        ],
        "hashtag_extras": ["#테크", "#AI", "#디지털", "#앱추천", "#기술트렌드"],
    },
    "기본": {
        "emojis": ["⭐", "💫", "🔥", "✨", "💯"],
        "title_formats": [
            "{kw} 완벽 정리",
            "알면 유용한 {kw} 가이드",
            "{kw} 트렌드 총정리",
            "{kw} 이것만 알면 OK",
        ],
        "subtitles": [
            "지금 가장 핫한 트렌드 정보",
            "알아두면 쓸모있는 꿀팁 모음",
            "SNS에서 가장 많이 본 그것",
        ],
        "bullet_templates": [
            "{kw} 기본 정보 & 개요",
            "{kw} 활용 방법 & 꿀팁",
            "{kw} 추천 & 비교 가이드",
            "{kw} 주의사항 & 알아야 할 것",
            "{kw} 관련 최신 트렌드",
            "{kw} 전문가 추천 포인트",
        ],
        "ctas": [
            "저장하고 나중에 참고하세요!",
            "도움이 됐다면 좋아요 눌러주세요!",
            "팔로우하고 다음 콘텐츠도 받아가요!",
        ],
        "hashtag_extras": ["#꿀팁", "#정보공유", "#트렌드", "#추천"],
    },
}


def _fill(template: str, kw: str) -> str:
    """템플릿의 {kw} 플레이스홀더 치환"""
    return template.replace("{kw}", kw)


def generate_hashtags(keyword: str, category: str, count: int = 15) -> list[str]:
    """키워드 + 카테고리 기반 해시태그 생성"""
    tags = set(BASE_HASHTAGS)

    # 카테고리별 해시태그 추가
    extras = TEMPLATES.get(category, TEMPLATES["기본"])["hashtag_extras"]
    tags.update(extras)

    # 키워드 기반 해시태그
    clean_kw = re.sub(r"[^\w가-힣]", "", keyword)
    if clean_kw:
        tags.add(f"#{clean_kw}")

    # 키워드 단어 분리 해시태그
    words = keyword.split()
    for w in words:
        clean_w = re.sub(r"[^\w가-힣]", "", w)
        if len(clean_w) >= 2:
            tags.add(f"#{clean_w}")

    # 일반 인기 태그 보충
    general_tags = [
        "#오늘의정보", "#인스타그램", "#꿀팁모음", "#유용한정보",
        "#일상공유", "#소통해요", "#팔로우미", "#좋아요반사",
    ]
    tags.update(random.sample(general_tags, min(3, len(general_tags))))

    tag_list = list(tags)[:count]
    random.shuffle(tag_list)
    return tag_list


def generate_card_content(trend: TrendItem) -> CardContent:
    """TrendItem으로부터 카드뉴스 콘텐츠 생성"""
    cat = trend.category if trend.category in TEMPLATES else "기본"
    tmpl = TEMPLATES[cat]
    kw = trend.keyword

    title = _fill(random.choice(tmpl["title_formats"]), kw)
    subtitle = random.choice(tmpl["subtitles"])
    emoji = random.choice(tmpl["emojis"])

    # 불릿 4~5개 무작위 선택
    num_bullets = random.randint(4, 5)
    bullet_pool = tmpl["bullet_templates"]
    selected = random.sample(bullet_pool, min(num_bullets, len(bullet_pool)))
    bullets = [_fill(b, kw) for b in selected]

    cta = _fill(random.choice(tmpl["ctas"]), kw)
    hashtags = generate_hashtags(kw, cat)

    return CardContent(
        keyword=kw,
        category=cat,
        title=title,
        subtitle=subtitle,
        bullets=bullets,
        cta=cta,
        hashtags=hashtags,
        emoji_accent=emoji,
    )
