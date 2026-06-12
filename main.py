#!/usr/bin/env python3
# main.py - 뉴스 카드뉴스 자동화 파이프라인

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from config import (
    OUTPUT_DIR, UPLOAD_DELAY_SECONDS,
    INSTAGRAM_ACCOUNT_ID, INSTAGRAM_ACCESS_TOKEN,
)
from news_collector import collect_news_by_category, NewsArticle
from content_generator import generate_card_content, CardContent
from image_generator import generate_card_images

CATEGORIES = ["연예", "한국 사회", "스포츠", "주요 세계 이슈"]


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="뉴스 카드뉴스 자동화")
    parser.add_argument("--category", "-c", type=str, default=None,
                        help="특정 카테고리 (연예 / 한국 사회 / 스포츠 / 주요 세계 이슈)")
    parser.add_argument("--dry-run", "-d", action="store_true",
                        help="이미지 생성만, Instagram 업로드 건너뜀")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="상세 로그")
    parser.add_argument("--all-categories", "-a", action="store_true",
                        help="4개 카테고리 모두 처리")
    return parser.parse_args()


def upload_to_instagram(image_paths: list[Path], content: CardContent) -> str | None:
    """ImgBB 호스팅 후 Instagram 캐러셀 업로드"""
    try:
        from instagram_uploader import InstagramUploader, upload_image_to_imgbb
    except ImportError as e:
        logger.error(f"업로더 모듈 로드 실패: {e}")
        return None

    imgbb_key = os.getenv("IMGBB_API_KEY", "")
    if not imgbb_key:
        logger.warning("IMGBB_API_KEY 미설정 → 업로드 건너뜀")
        return None

    try:
        # 각 슬라이드 이미지 → 공개 URL
        image_urls = []
        for path in image_paths:
            url = upload_image_to_imgbb(path, imgbb_key)
            image_urls.append(url)
            time.sleep(0.5)

        uploader = InstagramUploader()
        post_id = uploader.upload_carousel(image_urls, content.caption)
        return post_id
    except Exception as e:
        logger.error(f"Instagram 업로드 실패: {e}")
        return None


def run_pipeline(
    categories: list[str] | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """전체 파이프라인 실행"""
    if categories is None:
        categories = CATEGORIES  # 4개 카테고리 모두

    results = []

    # Step 1: 뉴스 수집
    logger.info(f"뉴스 수집 중: {categories}")
    news_by_cat = collect_news_by_category(categories, per_category=3)

    for cat in categories:
        articles = news_by_cat.get(cat, [])
        if not articles:
            logger.warning(f"[{cat}] 수집된 기사 없음, 건너뜀")
            continue

        article = articles[0]  # 상위 1개 기사 처리
        logger.info(f"\n[{cat}] 기사: {article.title[:60]}")

        # Step 2: 콘텐츠 생성
        logger.info("  콘텐츠 생성 중...")
        content = generate_card_content(article)
        logger.info(f"  슬라이드 수: {len(content.slides)}장")

        # Step 3: 이미지 생성
        logger.info("  이미지 생성 중...")
        try:
            image_paths = generate_card_images(content)
            logger.info(f"  이미지 {len(image_paths)}장 생성 완료")
        except Exception as e:
            logger.error(f"  이미지 생성 실패: {e}")
            continue

        # Step 4: Instagram 업로드
        post_id = None
        if dry_run:
            logger.info("  드라이런 — 업로드 건너뜀")
        else:
            logger.info(f"  Instagram 업로드 중 ({len(image_paths)}장)...")
            post_id = upload_to_instagram(image_paths, content)
            if post_id:
                logger.info(f"  게시 완료! ID: {post_id}")
            else:
                logger.warning("  업로드 실패 (이미지는 로컬에 저장됨)")

        results.append({
            "category": cat,
            "title": article.title,
            "slides": len(image_paths),
            "image_paths": [str(p) for p in image_paths],
            "post_id": post_id,
        })

        # 업로드 딜레이
        if not dry_run and post_id and cat != categories[-1]:
            logger.info(f"  {UPLOAD_DELAY_SECONDS}초 대기...")
            time.sleep(UPLOAD_DELAY_SECONDS)

    return results


def print_summary(results: list[dict], dry_run: bool) -> None:
    print("\n" + "=" * 60)
    print("  결과 요약")
    print("=" * 60)
    success_img = sum(1 for r in results if r.get("image_paths"))
    success_upload = sum(1 for r in results if r.get("post_id"))
    print(f"  처리된 카테고리: {len(results)}개")
    print(f"  이미지 생성: {success_img}개 성공")
    if not dry_run:
        print(f"  Instagram 게시: {success_upload}개 성공")
    print(f"\n  저장 폴더: {OUTPUT_DIR.absolute()}\n")
    for r in results:
        status = "✅" if r.get("image_paths") else "❌"
        upload = f"→ post: {r['post_id']}" if r.get("post_id") else ""
        print(f"  {status} [{r['category']}] {r['title'][:50]} ({r.get('slides', 0)}장) {upload}")
    print()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    print("\n" + "=" * 60)
    print("  뉴스 카드뉴스 자동화 파이프라인")
    print("=" * 60 + "\n")

    if args.dry_run:
        logger.info("드라이런 모드 — Instagram 업로드를 건너뜁니다.\n")

    if args.category:
        categories = [args.category]
    elif args.all_categories:
        categories = CATEGORIES
    else:
        categories = CATEGORIES  # 기본: 전체

    try:
        results = run_pipeline(categories=categories, dry_run=args.dry_run)
        print_summary(results, args.dry_run)
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"파이프라인 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
