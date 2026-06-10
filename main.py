#!/usr/bin/env python3
# main.py - 인스타그램 카드뉴스 자동화 파이프라인

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# .env 파일 로드 (있으면)
load_dotenv()

from config import UPLOAD_DELAY_SECONDS, OUTPUT_DIR
from trend_collector import collect_trends, TrendItem
from content_generator import generate_card_content, CardContent
from image_generator import generate_image

# ── 로깅 설정 ─────────────────────────────────────────────

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(OUTPUT_DIR / "pipeline.log", encoding="utf-8"),
        ],
    )

logger = logging.getLogger(__name__)


# ── CLI 인수 ──────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="인스타그램 카드뉴스 자동화 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py                        # 기본 실행 (3개, 업로드 포함)
  python main.py --count 5 --dry-run    # 5개 생성, 업로드 건너뜀
  python main.py --category 뷰티        # 뷰티 카테고리만
  python main.py --count 1 --verbose    # 상세 로그 출력
        """,
    )
    parser.add_argument(
        "--count", "-n", type=int, default=3,
        help="생성할 카드뉴스 수 (기본: 3)",
    )
    parser.add_argument(
        "--category", "-c", type=str, default=None,
        help="특정 카테고리만 처리 (예: 뷰티, 패션, 음식, 여행, 라이프스타일, 기술)",
    )
    parser.add_argument(
        "--dry-run", "-d", action="store_true",
        help="이미지 생성만, Instagram 업로드 건너뜀",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="상세 로그 출력",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="이미지 저장 폴더 (기본: ./output)",
    )
    return parser.parse_args()


# ── 업로드 로직 ───────────────────────────────────────────

def upload_to_instagram(image_path: Path, content: CardContent) -> str | None:
    """이미지를 ImgBB에 호스팅 후 Instagram에 업로드"""
    try:
        from instagram_uploader import InstagramUploader, upload_image_to_imgbb
    except ImportError as e:
        logger.error(f"업로더 모듈 로드 실패: {e}")
        return None

    imgbb_key = os.getenv("IMGBB_API_KEY", "")
    if not imgbb_key:
        logger.warning(
            "IMGBB_API_KEY 미설정 → 업로드 건너뜀\n"
            "  .env 파일에 IMGBB_API_KEY=<키> 를 추가하세요."
        )
        return None

    try:
        # 로컬 이미지 → 공개 URL
        image_url = upload_image_to_imgbb(image_path, imgbb_key)

        # 캡션 구성 (본문 + 해시태그)
        caption_body = (
            f"{content.emoji_accent} {content.title}\n\n"
            f"{content.subtitle}\n\n"
            + "\n".join(f"✅ {b}" for b in content.bullets)
            + f"\n\n💬 {content.cta}\n\n"
            + " ".join(content.hashtags)
        )

        uploader = InstagramUploader()
        post_id = uploader.upload(image_url, caption_body)
        return post_id

    except Exception as e:
        logger.error(f"Instagram 업로드 실패: {e}")
        return None


# ── 단계별 진행 출력 ──────────────────────────────────────

def print_banner() -> None:
    print("\n" + "=" * 58)
    print("  📱 Instagram 카드뉴스 자동화 파이프라인")
    print("=" * 58 + "\n")


def print_step(step: int, total: int, keyword: str, category: str) -> None:
    print(f"\n[{step}/{total}] 키워드: {keyword}  ({category})")
    print("-" * 40)


# ── 메인 파이프라인 ───────────────────────────────────────

def run_pipeline(
    count: int = 3,
    category_filter: str | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    전체 파이프라인 실행.
    반환: 처리 결과 목록 (keyword, image_path, post_id)
    """
    results = []

    # ── Step 1: 트렌드 수집 ───────────────────────────────
    logger.info("📡 트렌드 키워드 수집 중...")
    trends = collect_trends(count=max(count * 3, 15))  # 필터링 여유분

    if category_filter:
        trends = [t for t in trends if t.category == category_filter]
        logger.info(f"카테고리 필터 적용: {category_filter} → {len(trends)}개")

    if not trends:
        logger.error("수집된 트렌드가 없습니다. 종료합니다.")
        return []

    trends = trends[:count]
    logger.info(f"처리할 트렌드: {len(trends)}개\n")

    for trend in trends:
        logger.info(f"  • [{trend.category}] {trend.keyword} (score={trend.score}, source={trend.source})")

    print()

    # ── Step 2~4: 각 트렌드 처리 ─────────────────────────
    for i, trend in enumerate(trends, start=1):
        print_step(i, len(trends), trend.keyword, trend.category)

        # Step 2: 콘텐츠 생성
        logger.info("  ✍️  콘텐츠 생성 중...")
        content = generate_card_content(trend)
        logger.info(f"  제목: {content.title}")
        logger.info(f"  불릿: {len(content.bullets)}개")
        logger.info(f"  해시태그: {len(content.hashtags)}개")

        # Step 3: 이미지 생성
        logger.info("  🎨 이미지 생성 중...")
        try:
            image_path = generate_image(content)
            logger.info(f"  ✅ 저장: {image_path.name}")
        except Exception as e:
            logger.error(f"  ❌ 이미지 생성 실패: {e}")
            continue

        # Step 4: Instagram 업로드
        post_id = None
        if dry_run:
            logger.info("  ⏭️  드라이런 모드 — 업로드 건너뜀")
        else:
            logger.info("  📤 Instagram 업로드 중...")
            post_id = upload_to_instagram(image_path, content)
            if post_id:
                logger.info(f"  ✅ 게시 완료! ID: {post_id}")
            else:
                logger.warning("  ⚠️  업로드 실패 (이미지는 로컬에 저장됨)")

        results.append({
            "keyword": trend.keyword,
            "category": trend.category,
            "image_path": str(image_path),
            "post_id": post_id,
        })

        # 업로드 딜레이 (마지막은 생략)
        if not dry_run and post_id and i < len(trends):
            logger.info(f"  ⏳ {UPLOAD_DELAY_SECONDS}초 대기 (Instagram 속도 제한 방지)...")
            time.sleep(UPLOAD_DELAY_SECONDS)

    return results


# ── 결과 요약 출력 ────────────────────────────────────────

def print_summary(results: list[dict], dry_run: bool) -> None:
    print("\n" + "=" * 58)
    print("  📊 처리 결과 요약")
    print("=" * 58)

    success_img = sum(1 for r in results if r["image_path"])
    success_upload = sum(1 for r in results if r["post_id"])

    print(f"  이미지 생성: {success_img}/{len(results)}개 성공")
    if not dry_run:
        print(f"  Instagram 업로드: {success_upload}/{len(results)}개 성공")
    else:
        print("  Instagram 업로드: 드라이런 모드 (건너뜀)")

    print(f"\n  저장 폴더: {OUTPUT_DIR.absolute()}")
    print()

    for r in results:
        status = "✅" if r["image_path"] else "❌"
        upload_status = f"(post: {r['post_id']})" if r["post_id"] else ""
        img_name = Path(r["image_path"]).name if r["image_path"] else "생성 실패"
        print(f"  {status} [{r['category']}] {r['keyword']}")
        print(f"       {img_name} {upload_status}")

    print()


# ── 진입점 ────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # 출력 디렉토리 재설정 (CLI 옵션)
    if args.output_dir:
        import config as cfg
        cfg.OUTPUT_DIR = Path(args.output_dir)
        cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    setup_logging(args.verbose)
    print_banner()

    if args.dry_run:
        logger.info("🔍 드라이런 모드 — Instagram 업로드를 건너뜁니다.\n")

    try:
        results = run_pipeline(
            count=args.count,
            category_filter=args.category,
            dry_run=args.dry_run,
        )
        print_summary(results, args.dry_run)

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"파이프라인 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
