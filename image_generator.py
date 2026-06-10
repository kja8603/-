# image_generator.py - Pillow 기반 카드뉴스 이미지 생성

import logging
import textwrap
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import (
    IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_QUALITY,
    OUTPUT_DIR, KOREAN_FONT_PATHS, COLOR_PALETTES,
)
from content_generator import CardContent

logger = logging.getLogger(__name__)


# ── 폰트 로딩 ─────────────────────────────────────────────

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """한글 폰트 로드 (없으면 기본 폰트 폴백)"""
    paths = KOREAN_FONT_PATHS if not bold else KOREAN_FONT_PATHS  # 동일 목록 (Bold 우선 포함)
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    # 최후 폴백: Pillow 내장 폰트 (한글 미지원)
    logger.debug(f"한글 폰트 없음 → 기본 폰트 사용 (size={size})")
    return ImageFont.load_default()


# ── 그라디언트 배경 ───────────────────────────────────────

def _make_gradient(width: int, height: int, top_color: tuple, bottom_color: tuple) -> Image.Image:
    """세로 선형 그라디언트 이미지 생성"""
    base = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return base


# ── 장식 요소 ─────────────────────────────────────────────

def _draw_decorations(draw: ImageDraw.ImageDraw, palette: dict, width: int, height: int) -> None:
    """배경 장식 도형 그리기"""
    accent = palette["accent"]

    # 우상단 큰 원
    draw.ellipse(
        [width - 280, -120, width + 80, 240],
        fill=(*accent, 40),
        outline=(*accent, 60),
        width=3,
    )
    # 좌하단 원
    draw.ellipse(
        [-100, height - 320, 220, height + 60],
        fill=(*accent, 30),
        outline=(*accent, 50),
        width=2,
    )
    # 중앙 우측 작은 원
    draw.ellipse(
        [width - 120, height // 2 - 60, width - 20, height // 2 + 40],
        fill=(*accent, 50),
    )
    # 상단 수평 구분선
    draw.line(
        [(60, 200), (width - 60, 200)],
        fill=(*accent, 80),
        width=2,
    )


# ── 둥근 사각형 ───────────────────────────────────────────

def _rounded_rect(draw: ImageDraw.ImageDraw, xy: tuple, radius: int, fill: tuple) -> None:
    """모서리가 둥근 사각형 그리기"""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill)


# ── 텍스트 렌더링 헬퍼 ────────────────────────────────────

def _draw_multiline(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    x: int,
    y: int,
    color: tuple,
    max_width: int,
    line_spacing: int = 8,
) -> int:
    """최대 너비에 맞게 줄바꿈 후 텍스트 그리기. 다음 y 좌표 반환."""
    # 한 줄 너비 추정 (한글 1글자 ≈ font_size px)
    try:
        char_w = draw.textlength("가", font=font)
    except Exception:
        char_w = 20
    chars_per_line = max(1, int(max_width / char_w))
    lines = textwrap.wrap(text, width=chars_per_line) or [text]

    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        try:
            bbox = draw.textbbox((x, y), line, font=font)
            line_h = bbox[3] - bbox[1]
        except Exception:
            line_h = 30
        y += line_h + line_spacing
    return y


# ── 메인 이미지 생성 ──────────────────────────────────────

def generate_image(content: CardContent) -> Path:
    """
    CardContent로부터 9:16 카드뉴스 이미지를 생성하고 파일 경로를 반환.
    """
    palette = COLOR_PALETTES.get(content.category, COLOR_PALETTES["기본"])
    W, H = IMAGE_WIDTH, IMAGE_HEIGHT

    # ── 1. 그라디언트 배경 ────────────────────────────────
    img = _make_gradient(W, H, palette["gradient_top"], palette["gradient_bottom"])

    # RGBA 변환 (투명도 처리용)
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # ── 2. 장식 요소 ──────────────────────────────────────
    _draw_decorations(draw_overlay, palette, W, H)

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # ── 3. 폰트 세트 ──────────────────────────────────────
    font_emoji    = _load_font(90)
    font_title    = _load_font(62, bold=True)
    font_subtitle = _load_font(36)
    font_bullet   = _load_font(34)
    font_cta      = _load_font(32)
    font_hashtag  = _load_font(26)
    font_number   = _load_font(28, bold=True)

    MARGIN = 70
    CARD_X1, CARD_X2 = MARGIN, W - MARGIN
    card_text_w = CARD_X2 - CARD_X1 - 60  # 카드 내부 여백 제외

    # ── 4. 상단 이모지 & 카테고리 태그 ───────────────────
    y = 90
    draw.text((MARGIN, y), content.emoji_accent, font=font_emoji,
              fill=(*palette["card_bg"][:3], 230))

    cat_tag = f"  {content.category}  "
    cat_bg = (*palette["accent"], 200)
    try:
        tag_bbox = draw.textbbox((0, 0), cat_tag, font=font_subtitle)
        tag_w = tag_bbox[2] - tag_bbox[0] + 20
        tag_h = tag_bbox[3] - tag_bbox[1] + 14
    except Exception:
        tag_w, tag_h = 120, 40
    _rounded_rect(draw, (W - MARGIN - tag_w, y + 10, W - MARGIN, y + 10 + tag_h),
                  radius=12, fill=cat_bg)
    draw.text((W - MARGIN - tag_w + 10, y + 17), cat_tag,
              font=font_subtitle, fill=(255, 255, 255, 240))

    y = 220

    # ── 5. 메인 카드 (흰색 반투명 패널) ──────────────────
    card_top = y
    card_bottom = H - 220
    card_fill = palette["card_bg"]  # (R, G, B, A)
    card_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_img)
    card_draw.rounded_rectangle(
        [CARD_X1, card_top, CARD_X2, card_bottom],
        radius=30, fill=card_fill,
    )
    img = Image.alpha_composite(img, card_img)
    draw = ImageDraw.Draw(img)

    # ── 6. 제목 ───────────────────────────────────────────
    y = card_top + 50
    y = _draw_multiline(
        draw, content.title, font_title,
        CARD_X1 + 40, y,
        color=(*palette["title_color"], 255),
        max_width=card_text_w,
        line_spacing=10,
    )
    y += 10

    # 제목 하단 강조선
    draw.line([(CARD_X1 + 40, y), (CARD_X1 + 40 + 80, y)],
              fill=(*palette["accent"], 200), width=4)
    y += 20

    # ── 7. 부제목 ─────────────────────────────────────────
    y = _draw_multiline(
        draw, content.subtitle, font_subtitle,
        CARD_X1 + 40, y,
        color=(*palette["text_color"], 180),
        max_width=card_text_w,
        line_spacing=6,
    )
    y += 30

    # ── 8. 불릿 포인트 ────────────────────────────────────
    for i, bullet in enumerate(content.bullets, start=1):
        # 번호 배지
        badge_size = 34
        badge_x = CARD_X1 + 35
        draw.ellipse(
            [badge_x, y, badge_x + badge_size, y + badge_size],
            fill=(*palette["accent"], 220),
        )
        draw.text(
            (badge_x + badge_size // 2, y + badge_size // 2),
            str(i), font=font_number,
            fill=(255, 255, 255, 255),
            anchor="mm",
        )
        # 불릿 텍스트
        y = _draw_multiline(
            draw, bullet, font_bullet,
            badge_x + badge_size + 14, y + 2,
            color=(*palette["text_color"], 230),
            max_width=card_text_w - badge_size - 20,
            line_spacing=5,
        )
        y += 16

    # ── 9. CTA ────────────────────────────────────────────
    y = max(y + 20, card_bottom - 160)
    cta_bg_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cta_draw = ImageDraw.Draw(cta_bg_img)
    cta_draw.rounded_rectangle(
        [CARD_X1 + 30, y, CARD_X2 - 30, y + 60],
        radius=14, fill=(*palette["accent"], 50),
    )
    img = Image.alpha_composite(img, cta_bg_img)
    draw = ImageDraw.Draw(img)
    draw.text(
        ((CARD_X1 + CARD_X2) // 2, y + 30),
        content.cta, font=font_cta,
        fill=(*palette["title_color"], 240),
        anchor="mm",
    )

    # ── 10. 하단 해시태그 영역 ────────────────────────────
    hashtag_y = card_bottom + 30
    hashtag_text = "  ".join(content.hashtags[:8])
    _draw_multiline(
        draw, hashtag_text, font_hashtag,
        MARGIN, hashtag_y,
        color=(255, 255, 255, 180),
        max_width=W - MARGIN * 2,
        line_spacing=6,
    )

    # ── 11. 저장 ──────────────────────────────────────────
    img_rgb = img.convert("RGB")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw = "".join(c for c in content.keyword if c.isalnum() or c in "가-힣")[:20]
    filename = f"card_{safe_kw}_{timestamp}.jpg"
    output_path = OUTPUT_DIR / filename
    img_rgb.save(output_path, "JPEG", quality=IMAGE_QUALITY, optimize=True)

    logger.info(f"이미지 생성 완료: {output_path}")
    return output_path
