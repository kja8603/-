# image_generator.py - 멀티슬라이드 카드뉴스 이미지 생성

import io
import logging
import re
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import (
    IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_FORMAT,
    OUTPUT_DIR, KOREAN_FONT_PATHS, COLOR_PALETTES,
)
from content_generator import CardContent, CardSlide

logger = logging.getLogger(__name__)

W, H = IMAGE_WIDTH, IMAGE_HEIGHT
MARGIN = 60
INNER_W = W - MARGIN * 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


# ── 폰트 로딩 ─────────────────────────────────────────────

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in KOREAN_FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ── 배경 이미지 다운로드 ──────────────────────────────────

def _download_bg_image(url: str) -> Optional[Image.Image]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        return img
    except Exception as e:
        logger.debug(f"배경 이미지 다운로드 실패: {e}")
    return None


def _make_bg_with_image(bg_img: Image.Image, palette: dict) -> Image.Image:
    """기사 이미지를 배경으로 사용 (블러 + 다크 오버레이)"""
    # 정사각형으로 크롭
    w, h = bg_img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    bg_img = bg_img.crop((left, top, left + side, top + side))

    bg = bg_img.resize((W, H), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=4))

    # 다크 오버레이
    overlay = Image.new("RGBA", (W, H), (*palette["bg"], palette["overlay_opacity"]))
    bg = bg.convert("RGBA")
    bg = Image.alpha_composite(bg, overlay)
    return bg.convert("RGB")


def _make_plain_bg(palette: dict) -> Image.Image:
    """단색 + 그라디언트 배경 (이미지 없을 때)"""
    bg_color = palette["bg"]
    accent = palette["accent"]
    img = Image.new("RGB", (W, H), bg_color)

    # 대각선 그라디언트 효과
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 상단 좌측 원형 glow
    for r in range(400, 0, -20):
        alpha = int((400 - r) / 400 * 60)
        draw.ellipse([-r // 2, -r // 2, r, r], fill=(*accent, alpha))

    # 하단 우측 원형 glow
    for r in range(300, 0, -20):
        alpha = int((300 - r) / 300 * 40)
        draw.ellipse([W - r // 2, H - r, W + r // 2, H + r // 2], fill=(*accent, alpha))

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    return img.convert("RGB")


# ── 텍스트 렌더링 헬퍼 ────────────────────────────────────

def _draw_text_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    x: int, y: int,
    color: tuple,
    max_width: int,
    line_gap: int = 8,
) -> int:
    """줄바꿈 텍스트 그리기, 다음 y 반환"""
    try:
        char_w = draw.textlength("가", font=font)
    except Exception:
        char_w = font.size * 0.9 if hasattr(font, "size") else 20
    chars = max(1, int(max_width / char_w))
    lines = textwrap.wrap(text, width=chars) or [text]

    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        try:
            bb = draw.textbbox((x, y), line, font=font)
            y += (bb[3] - bb[1]) + line_gap
        except Exception:
            y += (font.size if hasattr(font, "size") else 30) + line_gap
    return y


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, xy: tuple, radius: int, fill: tuple) -> None:
    draw.rounded_rectangle(list(xy), radius=radius, fill=fill)


# ── 슬라이드 렌더링 ───────────────────────────────────────

def _render_cover(bg: Image.Image, slide: CardSlide, palette: dict, slide_idx: int, total: int) -> Image.Image:
    """커버 카드 (배경 이미지 + 하단 텍스트 오버레이)"""
    img = bg.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)

    accent = palette["accent"]
    white = (255, 255, 255, 255)

    f_label = _load_font(28)
    f_headline = _load_font(64)
    f_sub = _load_font(34)
    f_page = _load_font(26)

    # 하단 텍스트 영역 그라디언트
    text_band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    band_draw = ImageDraw.Draw(text_band)
    for i in range(400):
        alpha = int((i / 400) * 200)
        band_draw.line([(0, H - 400 + i), (W, H - 400 + i)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, text_band)
    draw = ImageDraw.Draw(img)

    # 상단 레이블 배지
    if slide.label:
        label_bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lb_draw = ImageDraw.Draw(label_bg)
        try:
            tw = draw.textlength(slide.label, font=f_label)
        except Exception:
            tw = len(slide.label) * 16
        pad_x, pad_y = 20, 10
        bx = MARGIN
        by = MARGIN
        lb_draw.rounded_rectangle(
            [bx, by, bx + tw + pad_x * 2, by + 40 + pad_y],
            radius=8,
            fill=(*accent, 220),
        )
        img = Image.alpha_composite(img, label_bg)
        draw = ImageDraw.Draw(img)
        draw.text((bx + pad_x, by + pad_y // 2), slide.label, font=f_label, fill=white)

    # 헤드라인
    y = H - 320
    y = _draw_text_wrapped(draw, slide.headline, f_headline, MARGIN, y, white, INNER_W, line_gap=12)

    # 서브헤드라인
    if slide.subheadline:
        y += 10
        _draw_text_wrapped(draw, slide.subheadline, f_sub, MARGIN, y, (200, 200, 200, 220), INNER_W)

    # 페이지 표시
    if total > 1:
        page_text = f"{slide_idx + 1} / {total}"
        draw.text((W - MARGIN - 60, MARGIN + 5), page_text, font=f_page, fill=(180, 180, 180, 200))

    # 하단 액센트 라인
    draw.line([(MARGIN, H - 60), (W - MARGIN, H - 60)], fill=(*accent, 120), width=2)

    return img.convert("RGB")


def _render_bullets(bg: Image.Image, slide: CardSlide, palette: dict, slide_idx: int, total: int) -> Image.Image:
    """불릿 카드 (어두운 배경 + 번호 배지 불릿)"""
    # 어두운 반투명 패널 오버레이
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 200))
    img = Image.alpha_composite(bg.convert("RGBA"), dark)

    # 패널 카드
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(panel)
    p_draw.rounded_rectangle(
        [MARGIN, 120, W - MARGIN, H - 100],
        radius=24,
        fill=(*palette["bg"], 220),
    )
    img = Image.alpha_composite(img, panel)
    draw = ImageDraw.Draw(img)

    accent = palette["accent"]
    white = (255, 255, 255, 255)
    text_c = (*palette["text_color"], 235)

    f_label = _load_font(26)
    f_headline = _load_font(52)
    f_bullet = _load_font(34)
    f_page = _load_font(26)

    # 레이블
    y = 160
    if slide.label:
        draw.text((MARGIN + 30, y), slide.label, font=f_label, fill=(*accent, 220))
        y += 44

    # 액센트 라인
    draw.line([(MARGIN + 30, y), (MARGIN + 30 + 60, y)], fill=(*accent, 200), width=4)
    y += 20

    # 헤드라인
    y = _draw_text_wrapped(draw, slide.headline, f_headline, MARGIN + 30, y, white, INNER_W - 30, line_gap=10)
    y += 30

    # 불릿 포인트
    for i, bullet in enumerate(slide.bullets[:4], start=1):
        badge_r = 22
        bx, by = MARGIN + 30, y
        draw.ellipse([bx, by, bx + badge_r * 2, by + badge_r * 2], fill=(*accent, 230))
        draw.text((bx + badge_r, by + badge_r), str(i), font=_load_font(22), fill=white, anchor="mm")
        next_y = _draw_text_wrapped(
            draw, bullet, f_bullet,
            bx + badge_r * 2 + 16, by + 4,
            text_c, INNER_W - badge_r * 2 - 20,
            line_gap=6,
        )
        y = max(next_y, by + badge_r * 2) + 20

    # 서브헤드라인 (있으면)
    if slide.subheadline:
        draw.text((MARGIN + 30, y + 10), slide.subheadline, font=f_label, fill=(*accent, 180))

    # 페이지 표시
    if total > 1:
        draw.text((W - MARGIN - 70, H - 70), f"{slide_idx + 1} / {total}", font=f_page, fill=(160, 160, 160, 200))

    return img.convert("RGB")


def _render_cta(bg: Image.Image, slide: CardSlide, palette: dict, slide_idx: int, total: int) -> Image.Image:
    """CTA 카드 (중앙 정렬 메시지)"""
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 180))
    img = Image.alpha_composite(bg.convert("RGBA"), dark)

    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(panel)
    p_draw.rounded_rectangle(
        [MARGIN, H // 3, W - MARGIN, H * 2 // 3 + 60],
        radius=24,
        fill=(*palette["bg"], 230),
    )
    img = Image.alpha_composite(img, panel)
    draw = ImageDraw.Draw(img)

    accent = palette["accent"]
    white = (255, 255, 255, 255)

    f_label = _load_font(28)
    f_headline = _load_font(54)
    f_sub = _load_font(32)

    # 레이블
    if slide.label:
        try:
            tw = draw.textlength(slide.label, font=f_label)
        except Exception:
            tw = len(slide.label) * 15
        lx = (W - tw) // 2
        draw.text((lx, H // 3 + 40), slide.label, font=f_label, fill=(*accent, 220))

    # 헤드라인 (중앙)
    hy = H // 3 + 100
    for line in textwrap.wrap(slide.headline, width=14):
        try:
            tw = draw.textlength(line, font=f_headline)
        except Exception:
            tw = len(line) * 30
        draw.text(((W - tw) // 2, hy), line, font=f_headline, fill=white)
        try:
            bb = draw.textbbox(((W - tw) // 2, hy), line, font=f_headline)
            hy += (bb[3] - bb[1]) + 12
        except Exception:
            hy += 60

    # 서브헤드라인
    if slide.subheadline:
        try:
            tw = draw.textlength(slide.subheadline, font=f_sub)
        except Exception:
            tw = len(slide.subheadline) * 17
        draw.text(((W - tw) // 2, hy + 20), slide.subheadline, font=f_sub, fill=(200, 200, 200, 200))

    # 하단 계정명
    f_acct = _load_font(26)
    acct = "@space.go__"
    try:
        tw = draw.textlength(acct, font=f_acct)
    except Exception:
        tw = 180
    draw.text(((W - tw) // 2, H - 80), acct, font=f_acct, fill=(*accent, 180))

    if total > 1:
        draw.text((W - MARGIN - 70, H - 80), f"{slide_idx + 1} / {total}", font=f_label, fill=(160, 160, 160, 200))

    return img.convert("RGB")


def _render_slide(bg: Image.Image, slide: CardSlide, palette: dict, idx: int, total: int) -> Image.Image:
    if slide.slide_type == "cover":
        return _render_cover(bg, slide, palette, idx, total)
    elif slide.slide_type == "cta":
        return _render_cta(bg, slide, palette, idx, total)
    else:  # bullets / detail
        return _render_bullets(bg, slide, palette, idx, total)


# ── 공개 인터페이스 ───────────────────────────────────────

def generate_card_images(content: CardContent) -> list[Path]:
    """
    CardContent → 슬라이드 이미지 파일 목록 반환 (1~4장)
    """
    palette = COLOR_PALETTES.get(content.category, COLOR_PALETTES["기본"])

    # 배경 이미지 준비
    bg: Optional[Image.Image] = None
    if content.image_url:
        bg = _download_bg_image(content.image_url)
        if bg:
            bg = _make_bg_with_image(bg, palette)
    if bg is None:
        bg = _make_plain_bg(palette)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = re.sub(r"[^\w가-힣]", "", content.article_title)[:20]
    total = len(content.slides)

    paths: list[Path] = []
    for i, slide in enumerate(content.slides):
        rendered = _render_slide(bg, slide, palette, i, total)
        filename = f"card_{safe_title}_{timestamp}_{i + 1}of{total}.png"
        out_path = OUTPUT_DIR / filename
        rendered.save(out_path, "PNG", optimize=True)
        logger.info(f"슬라이드 저장: {out_path.name}")
        paths.append(out_path)

    return paths
