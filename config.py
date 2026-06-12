# config.py - 전체 프로젝트 설정

import os
from pathlib import Path

# ── 기본 경로 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
FONT_DIR = BASE_DIR / "fonts"

OUTPUT_DIR.mkdir(exist_ok=True)
FONT_DIR.mkdir(exist_ok=True)

# ── 이미지 설정 (인스타그램 1:1 정사각형) ─────────────────
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1080
IMAGE_QUALITY = 95

# ── 폰트 경로 ─────────────────────────────────────────────
KOREAN_FONT_PATHS = [
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundR.ttf",
    "/usr/share/fonts/truetype/nanum/NanumSquareR.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    str(FONT_DIR / "NanumGothicBold.ttf"),
    str(FONT_DIR / "NanumGothic.ttf"),
]

# ── 카테고리별 컬러 팔레트 ────────────────────────────────
COLOR_PALETTES = {
    "연예": {
        "bg": (15, 10, 25),
        "accent": (255, 60, 120),
        "title_color": (255, 255, 255),
        "text_color": (220, 220, 220),
        "tag_bg": (80, 20, 50),
        "overlay_opacity": 170,
    },
    "한국 사회": {
        "bg": (10, 20, 35),
        "accent": (30, 140, 255),
        "title_color": (255, 255, 255),
        "text_color": (210, 220, 235),
        "tag_bg": (15, 40, 80),
        "overlay_opacity": 175,
    },
    "스포츠": {
        "bg": (10, 25, 10),
        "accent": (50, 220, 80),
        "title_color": (255, 255, 255),
        "text_color": (210, 235, 215),
        "tag_bg": (15, 60, 20),
        "overlay_opacity": 165,
    },
    "주요 세계 이슈": {
        "bg": (25, 15, 10),
        "accent": (255, 165, 30),
        "title_color": (255, 255, 255),
        "text_color": (240, 225, 200),
        "tag_bg": (70, 40, 10),
        "overlay_opacity": 175,
    },
    "기본": {
        "bg": (15, 15, 20),
        "accent": (150, 100, 255),
        "title_color": (255, 255, 255),
        "text_color": (220, 220, 230),
        "tag_bg": (40, 25, 70),
        "overlay_opacity": 170,
    },
}

# ── 뉴스 RSS 피드 ─────────────────────────────────────────
NEWS_FEEDS = {
    "연예": [
        "https://news.google.com/rss/search?q=연예+아이돌+드라마+영화+가수&hl=ko&gl=KR&ceid=KR:ko",
        "https://rss.hankooki.com/entv/entv_list.xml",
    ],
    "한국 사회": [
        "https://news.google.com/rss/search?q=한국+사회+정치+경제+사건사고&hl=ko&gl=KR&ceid=KR:ko",
        "https://rss.hankooki.com/society/society_list.xml",
    ],
    "스포츠": [
        "https://news.google.com/rss/search?q=한국+스포츠+축구+야구+배구+농구&hl=ko&gl=KR&ceid=KR:ko",
        "https://rss.hankooki.com/sports/sports_list.xml",
    ],
    "주요 세계 이슈": [
        "https://news.google.com/rss/search?q=세계+국제+이슈+외교+전쟁+경제위기&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko",
    ],
}

# ── 카테고리별 카드 수 범위 ───────────────────────────────
CARDS_RANGE = {
    "연예": (1, 3),
    "한국 사회": (2, 4),
    "스포츠": (1, 3),
    "주요 세계 이슈": (2, 4),
    "기본": (1, 4),
}

# ── 카테고리별 해시태그 ───────────────────────────────────
CATEGORY_HASHTAGS = {
    "연예": ["#연예", "#연예인", "#드라마", "#아이돌", "#영화", "#가요", "#엔터테인먼트", "#연예뉴스"],
    "한국 사회": ["#한국", "#사회", "#뉴스", "#이슈", "#정치", "#경제", "#한국뉴스", "#사회이슈"],
    "스포츠": ["#스포츠", "#축구", "#야구", "#배구", "#농구", "#스포츠뉴스", "#한국스포츠"],
    "주요 세계 이슈": ["#세계", "#국제", "#글로벌", "#세계뉴스", "#국제뉴스", "#글로벌이슈", "#외교"],
    "기본": ["#뉴스", "#이슈", "#카드뉴스", "#정보"],
}

BASE_HASHTAGS = ["#카드뉴스", "#뉴스", "#이슈", "#오늘의뉴스", "#spacego", "#정보공유"]

# ── Instagram Graph API ────────────────────────────────────
INSTAGRAM_API_BASE = "https://graph.facebook.com/v19.0"
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

# 업로드 간 딜레이 (초)
UPLOAD_DELAY_SECONDS = 30

# ── Claude API ────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 스케줄 시간 (KST, 24시간 형식) ──────────────────────
SCHEDULE_TIMES_KST = ["07:00", "16:00", "23:00"]
TIMEZONE = "Asia/Seoul"

# ── 실행당 처리할 카테고리 수 ─────────────────────────────
ARTICLES_PER_RUN = 2  # 실행당 2개 카테고리 → 2개 게시물
