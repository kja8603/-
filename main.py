#!/usr/bin/env python3
# main.py - 뉴스 카드뉴스 PNG 생성 파이프라인

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from config import OUTPUT_DIR
from news_collector import collect_news_by_category
from content_generator import generate_card_content
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
    parser = argparse.ArgumentParser(description="뉴스 카드뉴스 PNG 생성")
    parser.add_argument("--category", "-c", type=str, default=None,
                        help="특정 카테고리 (연예 / 한국 사회 / 스포츠 / 주요 세계 이슈)")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그")
    return parser.parse_args()


def run_pipeline(categories: list[str] | None = None) -> list[dict]:
    """뉴스 수집 → 콘텐츠 생성 → PNG 저장"""
    if categories is None:
        categories = CATEGORIES

    results = []

    logger.info(f"뉴스 수집 중: {categories}")
    news_by_cat = collect_news_by_category(categories, per_category=3)

    for cat in categories:
        articles = news_by_cat.get(cat, [])
        if not articles:
            logger.warning(f"[{cat}] 수집된 기사 없음, 건너뜀")
            continue

        article = articles[0]
        logger.info(f"\n[{cat}] {article.title[:60]}")

        logger.info("  콘텐츠 생성 중...")
        content = generate_card_content(article)
        logger.info(f"  슬라이드: {len(content.slides)}장")

        logger.info("  이미지 생성 중...")
        try:
            image_paths = generate_card_images(content)
            for p in image_paths:
                logger.info(f"  저장: {p.name}")
        except Exception as e:
            logger.error(f"  이미지 생성 실패: {e}")
            continue

        results.append({
            "category": cat,
            "title": article.title,
            "image_paths": [str(p) for p in image_paths],
        })

    return results


def print_summary(results: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("  결과 요약")
    print("=" * 60)
    total_images = sum(len(r["image_paths"]) for r in results)
    print(f"  카테고리: {len(results)}개  |  PNG: {total_images}장")
    print(f"  저장 폴더: {OUTPUT_DIR.absolute()}\n")
    for r in results:
        count = len(r["image_paths"])
        print(f"  ✅ [{r['category']}] {r['title'][:50]} ({count}장)")
        for p in r["image_paths"]:
            print(f"       {Path(p).name}")
    print()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    print("\n" + "=" * 60)
    print("  뉴스 카드뉴스 PNG 생성")
    print("=" * 60 + "\n")

    categories = [args.category] if args.category else CATEGORIES

    try:
        results = run_pipeline(categories=categories)
        print_summary(results)
    except KeyboardInterrupt:
        print("\n중단됨")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
