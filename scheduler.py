#!/usr/bin/env python3
# scheduler.py - 오전 7시 / 오후 4시 / 오후 11시 자동 실행 (KST)

import logging
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    import pytz
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

from config import SCHEDULE_TIMES_KST, TIMEZONE
from main import run_pipeline, print_summary, CATEGORIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("output/scheduler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def scheduled_job() -> None:
    now = datetime.now()
    logger.info(f"\n{'='*60}")
    logger.info(f"  스케줄 실행 시작: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")

    try:
        results = run_pipeline(categories=CATEGORIES, dry_run=False)
        print_summary(results, dry_run=False)
    except Exception as e:
        logger.exception(f"스케줄 실행 오류: {e}")


def run_with_apscheduler() -> None:
    """APScheduler로 실행 (타임존 정확)"""
    tz = pytz.timezone(TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    for time_str in SCHEDULE_TIMES_KST:
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            scheduled_job,
            CronTrigger(hour=hour, minute=minute, timezone=tz),
            id=f"news_card_{time_str.replace(':', '')}",
            name=f"뉴스 카드뉴스 {time_str} KST",
            max_instances=1,
            misfire_grace_time=300,  # 5분 이내 지연 허용
        )
        logger.info(f"  등록: 매일 {time_str} KST")

    logger.info("\n스케줄러 시작 — Ctrl+C로 종료\n")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러 종료")


def run_with_schedule_lib() -> None:
    """schedule 라이브러리로 실행 (KST 환경 필요)"""
    import schedule

    for time_str in SCHEDULE_TIMES_KST:
        schedule.every().day.at(time_str).do(scheduled_job)
        logger.info(f"  등록: 매일 {time_str} (시스템 시간 기준)")

    logger.info("\n스케줄러 시작 — Ctrl+C로 종료\n")
    logger.warning("주의: schedule 라이브러리는 시스템 시간 기준입니다.")
    logger.warning("서버 시간이 UTC라면 APScheduler 사용을 권장합니다.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("스케줄러 종료")


def main() -> None:
    logger.info("뉴스 카드뉴스 스케줄러")
    logger.info(f"실행 시간: {', '.join(SCHEDULE_TIMES_KST)} KST")
    logger.info(f"카테고리: 연예 | 한국 사회 | 스포츠 | 주요 세계 이슈\n")

    if APSCHEDULER_AVAILABLE:
        logger.info("APScheduler 사용 (정확한 KST 타임존)")
        run_with_apscheduler()
    else:
        try:
            import schedule
            logger.info("schedule 라이브러리 사용")
            run_with_schedule_lib()
        except ImportError:
            logger.error("스케줄러 라이브러리가 없습니다. 다음 중 하나를 설치하세요:")
            logger.error("  pip install apscheduler pytz  (권장)")
            logger.error("  pip install schedule")
            sys.exit(1)


if __name__ == "__main__":
    main()
