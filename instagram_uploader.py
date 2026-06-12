# instagram_uploader.py - Instagram Graph API 업로드 (단일 + 캐러셀)

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


def upload_image_to_imgbb(image_path: Path, api_key: str) -> str:
    """ImgBB에 로컬 이미지를 업로드하고 공개 URL 반환"""
    import base64
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": data, "name": image_path.stem},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise RuntimeError(f"ImgBB 업로드 실패: {result}")
    url = result["data"]["url"]
    logger.info(f"이미지 호스팅: {url}")
    return url


class InstagramUploader:
    def __init__(
        self,
        account_id: str = INSTAGRAM_ACCOUNT_ID,
        access_token: str = INSTAGRAM_ACCESS_TOKEN,
    ):
        if not account_id or not access_token:
            raise ValueError(
                "INSTAGRAM_ACCOUNT_ID와 INSTAGRAM_ACCESS_TOKEN 환경변수를 설정하세요."
            )
        self.account_id = account_id
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _api_url(self, path: str) -> str:
        return f"{INSTAGRAM_API_BASE}/{path}"

    def _handle_error(self, resp: requests.Response) -> None:
        try:
            err = resp.json().get("error", {})
            raise RuntimeError(f"Instagram API [{err.get('code', resp.status_code)}]: {err.get('message', resp.text)}")
        except ValueError:
            raise RuntimeError(f"Instagram API HTTP {resp.status_code}: {resp.text[:200]}")

    def _create_single_container(self, image_url: str, caption: str) -> str:
        """단일 이미지 미디어 컨테이너 생성"""
        resp = self.session.post(
            self._api_url(f"{self.account_id}/media"),
            data={"image_url": image_url, "caption": caption, "access_token": self.access_token},
            timeout=30,
        )
        if not resp.ok:
            self._handle_error(resp)
        container_id = resp.json().get("id")
        if not container_id:
            raise RuntimeError("컨테이너 ID 없음")
        logger.info(f"단일 컨테이너 생성: {container_id}")
        return container_id

    def _create_carousel_item(self, image_url: str) -> str:
        """캐러셀 아이템 컨테이너 생성"""
        resp = self.session.post(
            self._api_url(f"{self.account_id}/media"),
            data={
                "image_url": image_url,
                "is_carousel_item": "true",
                "access_token": self.access_token,
            },
            timeout=30,
        )
        if not resp.ok:
            self._handle_error(resp)
        item_id = resp.json().get("id")
        if not item_id:
            raise RuntimeError("캐러셀 아이템 ID 없음")
        logger.debug(f"캐러셀 아이템 생성: {item_id}")
        return item_id

    def _create_carousel_container(self, item_ids: list[str], caption: str) -> str:
        """캐러셀 컨테이너 생성"""
        resp = self.session.post(
            self._api_url(f"{self.account_id}/media"),
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(item_ids),
                "caption": caption,
                "access_token": self.access_token,
            },
            timeout=30,
        )
        if not resp.ok:
            self._handle_error(resp)
        container_id = resp.json().get("id")
        if not container_id:
            raise RuntimeError("캐러셀 컨테이너 ID 없음")
        logger.info(f"캐러셀 컨테이너 생성: {container_id}")
        return container_id

    def _wait_for_container(self, container_id: str, max_wait: int = 90) -> None:
        """컨테이너 처리 완료까지 대기"""
        url = self._api_url(container_id)
        params = {"fields": "status_code,status", "access_token": self.access_token}
        elapsed = 0
        while elapsed < max_wait:
            resp = self.session.get(url, params=params, timeout=15)
            if not resp.ok:
                self._handle_error(resp)
            status = resp.json().get("status_code", "")
            if status == "FINISHED":
                return
            elif status == "ERROR":
                raise RuntimeError(f"미디어 처리 실패: {resp.json().get('status', '')}")
            time.sleep(5)
            elapsed += 5
        raise TimeoutError(f"컨테이너 처리 타임아웃 ({max_wait}s)")

    def _publish(self, container_id: str) -> str:
        """컨테이너 발행"""
        resp = self.session.post(
            self._api_url(f"{self.account_id}/media_publish"),
            data={"creation_id": container_id, "access_token": self.access_token},
            timeout=30,
        )
        if not resp.ok:
            self._handle_error(resp)
        post_id = resp.json().get("id")
        if not post_id:
            raise RuntimeError("게시물 ID 없음")
        logger.info(f"게시물 발행 완료: {post_id}")
        return post_id

    def upload_single(self, image_url: str, caption: str, retry: int = 2) -> str:
        """단일 이미지 업로드"""
        last_err = None
        for attempt in range(1, retry + 2):
            try:
                container_id = self._create_single_container(image_url, caption)
                self._wait_for_container(container_id)
                return self._publish(container_id)
            except Exception as e:
                last_err = e
                if attempt <= retry:
                    wait = 2 ** attempt
                    logger.warning(f"업로드 재시도 ({attempt}/{retry+1}): {e} — {wait}s 후")
                    time.sleep(wait)
        raise RuntimeError(f"단일 업로드 실패: {last_err}") from last_err

    def upload_carousel(self, image_urls: list[str], caption: str, retry: int = 2) -> str:
        """캐러셀(다중 이미지) 업로드 (2~10장)"""
        if len(image_urls) == 1:
            return self.upload_single(image_urls[0], caption, retry)

        last_err = None
        for attempt in range(1, retry + 2):
            try:
                # 각 슬라이드 아이템 생성
                item_ids = []
                for url in image_urls:
                    item_id = self._create_carousel_item(url)
                    item_ids.append(item_id)
                    time.sleep(1)

                # 캐러셀 컨테이너
                container_id = self._create_carousel_container(item_ids, caption)
                self._wait_for_container(container_id)
                return self._publish(container_id)
            except Exception as e:
                last_err = e
                if attempt <= retry:
                    wait = 2 ** attempt
                    logger.warning(f"캐러셀 재시도 ({attempt}/{retry+1}): {e} — {wait}s 후")
                    time.sleep(wait)
        raise RuntimeError(f"캐러셀 업로드 실패: {last_err}") from last_err

    def get_account_info(self) -> dict:
        """계정 정보 조회 (연결 테스트)"""
        resp = self.session.get(
            self._api_url(self.account_id),
            params={
                "fields": "id,name,username,followers_count,media_count",
                "access_token": self.access_token,
            },
            timeout=10,
        )
        if not resp.ok:
            self._handle_error(resp)
        return resp.json()
