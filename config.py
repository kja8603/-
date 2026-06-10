# config.py - 전체 프로젝트 설정

import os
from pathlib import Path

# ── 기본 경로 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
FONT_DIR = BASE_DIR / "fonts"

OUTPUT_DIR.mkdir(exist_ok=True)
FONT_DIR.mkdir(exist_ok=True)

# ── 이미지 설정 (인스타그램 9:16) ─────────────────────────
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920
IMAGE_QUALITY = 95  # JPEG 품질

# ── 폰트 경로 (시스템 한글 폰트 자동 탐지) ────────────────
KOREAN_FONT_PATHS = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    str(FONT_DIR / "NanumGothicBold.ttf"),
    str(FONT_DIR / "NanumGothic.ttf"),
]

# ── 카테고리별 컬러 팔레트 ────────────────────────────────
COLOR_PALETTES = {
    "뷰티": {
        "gradient_top": (255, 182, 193),    # 핑크
        "gradient_bottom": (199, 21, 133),  # 딥 핑크
        "card_bg": (255, 255, 255, 210),
        "title_color": (199, 21, 133),
        "text_color": (50, 50, 50),
        "accent": (255, 105, 180),
        "tag_bg": (255, 182, 193),
    },
    "패션": {
        "gradient_top": (30, 30, 30),
        "gradient_bottom": (80, 0, 120),
        "card_bg": (255, 255, 255, 220),
        "title_color": (80, 0, 120),
        "text_color": (30, 30, 30),
        "accent": (180, 0, 255),
        "tag_bg": (230, 200, 255),
    },
    "음식": {
        "gradient_top": (255, 140, 0),
        "gradient_bottom": (220, 50, 50),
        "card_bg": (255, 255, 255, 215),
        "title_color": (180, 60, 0),
        "text_color": (50, 30, 0),
        "accent": (255, 165, 0),
        "tag_bg": (255, 220, 150),
    },
    "여행": {
        "gradient_top": (0, 150, 200),
        "gradient_bottom": (0, 80, 160),
        "card_bg": (255, 255, 255, 215),
        "title_color": (0, 80, 160),
        "text_color": (20, 40, 60),
        "accent": (0, 200, 255),
        "tag_bg": (180, 230, 255),
    },
    "라이프스타일": {
        "gradient_top": (80, 200, 120),
        "gradient_bottom": (0, 120, 80),
        "card_bg": (255, 255, 255, 215),
        "title_color": (0, 100, 60),
        "text_color": (20, 50, 30),
        "accent": (50, 220, 100),
        "tag_bg": (180, 255, 200),
    },
    "기술": {
        "gradient_top": (20, 30, 60),
        "gradient_bottom": (0, 100, 200),
        "card_bg": (240, 248, 255, 220),
        "title_color": (0, 80, 200),
        "text_color": (20, 30, 60),
        "accent": (0, 180, 255),
        "tag_bg": (180, 220, 255),
    },
    "기본": {
        "gradient_top": (102, 126, 234),
        "gradient_bottom": (118, 75, 162),
        "card_bg": (255, 255, 255, 210),
        "title_color": (80, 40, 140),
        "text_color": (40, 40, 60),
        "accent": (150, 100, 220),
        "tag_bg": (220, 200, 255),
    },
}

# ── 카테고리 키워드 매핑 ──────────────────────────────────
CATEGORY_KEYWORDS = {
    "뷰티": ["화장", "메이크업", "스킨케어", "립", "아이섀도", "파운데이션", "선크림", "향수", "네일"],
    "패션": ["코디", "패션", "옷", "스타일", "브랜드", "신발", "가방", "트렌드", "오오티디"],
    "음식": ["맛집", "음식", "레시피", "카페", "디저트", "먹방", "요리", "밥", "커피"],
    "여행": ["여행", "국내여행", "해외여행", "관광", "숙소", "호텔", "캠핑", "드라이브"],
    "라이프스타일": ["일상", "홈인테리어", "운동", "건강", "독서", "취미", "힐링", "자기계발"],
    "기술": ["AI", "앱", "스마트폰", "테크", "갤럭시", "아이폰", "유튜브", "틱톡"],
}

# ── Instagram Graph API ────────────────────────────────────
INSTAGRAM_API_BASE = "https://graph.facebook.com/v19.0"
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

# 업로드 간 딜레이 (초) - Instagram 속도 제한 방지
UPLOAD_DELAY_SECONDS = 30

# ── Google Trends 설정 ────────────────────────────────────
TRENDS_GEO = "KR"         # 대한민국
TRENDS_LANGUAGE = "ko"
TRENDS_COUNT = 10          # 수집할 트렌드 수

# ── 해시태그 기본 세트 ────────────────────────────────────
BASE_HASHTAGS = [
    "#카드뉴스", "#인스타그램", "#트렌드", "#정보공유",
    "#일상", "#소통", "#팔로우", "#좋아요",
]
