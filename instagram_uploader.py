# instagram_uploader.py - Instagram Graph API 업로드

import logging
import time
from pathlib import Path

import requests

from config import (
    INSTAGRAM_API_BASE,
    INSTAGRAM_ACCOUNT_ID,
    INSTAGRAM_ACCESS_TOKEN,
    UPLOAD_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)


class InstagramUploader:
    """Instagram Graph API를 통한 이미지 업로드 클래스"""

    def __init__(
        self,
        account_id: str = INSTAGRAM_ACCOUNT_ID,
        access_token: str = INSTAGRAM_ACCESS_TOKEN,
    ):
        if not account_id or not access_token:
            raise ValueError(
                "INSTAGRAM_ACCOUNT_ID와 INSTAGRAM_ACCESS_TOKEN 환경변수를 설정하세요.\n"
                ".env.example 파일을 참고하여 .env 파일을 만들어주세요."
            )
        self.account_id = account_id
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _api_url(self, path: str) -> str:
        return f"{INSTAGRAM_API_BASE}/{path}"

    def _handle_error(self, resp: requests.Response) -> None:
        """API 에러 응답 파싱 및 예외 발생"""
        try:
            data = resp.json()
            err = data.get("error", {})
            msg = err.get("message", resp.text)
            code = err.get("code", resp.status_code)
            raise RuntimeError(f"Instagram API 오류 [{code}]: {msg}")
        except ValueError:
            raise RuntimeError(f"Instagram API HTTP {resp.status_code}: {resp.text[:200]}")

    # ── 1단계: 미디어 컨테이너 생성 ──────────────────────

    def create_media_container(self, image_url: str, caption: str) -> str:
        """
        Instagram 미디어 컨테이너 생성.
        image_url은 공개 접근 가능한 HTTPS URL이어야 함.
        반환값: container_id
        """
        url = self._api_url(f"{self.account_id}/media")
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }

        resp = self.session.post(url, data=payload, timeout=30)
        if not resp.ok:
            self._handle_error(resp)

        container_id = resp.json().get("id")
        if not container_id:
            raise RuntimeError("미디어 컨테이너 ID를 받지 못했습니다.")

        logger.info(f"미디어 컨테이너 생성됨: {container_id}")
        return container_id

    # ── 2단계: 컨테이너 상태 확인 ────────────────────────

    def wait_for_container(self, container_id: str, max_wait: int = 60) -> None:
        """컨테이너 처리 완료까지 대기 (최대 max_wait초)"""
        url = self._api_url(container_id)
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token,
        }

        elapsed = 0
        while elapsed < max_wait:
            resp = self.session.get(url, params=params, timeout=15)
            if not resp.ok:
                self._handle_error(resp)

            data = resp.json()
            status = data.get("status_code", "")

            if status == "FINISHED":
                logger.info("미디어 컨테이너 처리 완료")
                return
            elif status == "ERROR":
                raise RuntimeError(f"미디어 처리 실패: {data.get('status', '')}")
            elif status in ("IN_PROGRESS", "PUBLISHED"):
                logger.debug(f"컨테이너 처리 중... ({elapsed}s)")
                time.sleep(5)
                elapsed += 5
            else:
                time.sleep(3)
                elapsed += 3

        raise TimeoutError(f"미디어 컨테이너 처리 타임아웃 ({max_wait}s)")

    # ── 3단계: 게시물 발행 ────────────────────────────────

    def publish_media(self, container_id: str) -> str:
        """
        생성된 컨테이너를 Instagram에 발행.
        반환값: 게시물 ID
        """
        url = self._api_url(f"{self.account_id}/media_publish")
        payload = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }

        resp = self.session.post(url, data=payload, timeout=30)
        if not resp.ok:
            self._handle_error(resp)

        post_id = resp.json().get("id")
        if not post_id:
            raise RuntimeError("게시물 ID를 받지 못했습니다.")

        logger.info(f"Instagram 게시물 발행 완료! 게시물 ID: {post_id}")
        return post_id

    # ── 공개 메서드: 업로드 전체 파이프라인 ──────────────

    def upload(
        self,
        image_url: str,
        caption: str,
        retry: int = 2,
    ) -> str:
        """
        이미지 URL과 캡션으로 Instagram에 업로드.

        Parameters
        ----------
        image_url : 공개 HTTPS URL (로컬 파일 직접 업로드 불가)
        caption   : 해시태그 포함 캡션
        retry     : 실패 시 재시도 횟수

        Returns
        -------
        str : 발행된 게시물 ID
        """
        last_err = None
        for attempt in range(1, retry + 2):
            try:
                container_id = self.create_media_container(image_url, caption)
                self.wait_for_container(container_id)
                post_id = self.publish_media(container_id)
                return post_id
            except Exception as e:
                last_err = e
                if attempt <= retry:
                    wait = 2 ** attempt
                    logger.warning(f"업로드 실패 (시도 {attempt}/{retry+1}): {e} — {wait}초 후 재시도")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"업로드 최종 실패: {last_err}") from last_err

    def get_account_info(self) -> dict:
        """계정 정보 조회 (연결 테스트용)"""
        url = self._api_url(self.account_id)
        params = {
            "fields": "id,name,username,followers_count,media_count",
            "access_token": self.access_token,
        }
        resp = self.session.get(url, params=params, timeout=10)
        if not resp.ok:
            self._handle_error(resp)
        return resp.json()


# ── 이미지 호스팅 헬퍼 (로컬 파일 → URL 변환) ────────────

def upload_image_to_imgbb(image_path: Path, api_key: str) -> str:
    """
    ImgBB 무료 이미지 호스팅 서비스에 이미지를 업로드하고 공개 URL 반환.
    IMGBB_API_KEY 환경변수 필요. (https://api.imgbb.com/ 에서 무료 발급)
    """
    import base64, os

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={
            "key": api_key,
            "image": image_data,
            "name": image_path.stem,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"ImgBB 업로드 실패: {data}")

    url = data["data"]["url"]
    logger.info(f"이미지 호스팅 완료: {url}")
    return url
