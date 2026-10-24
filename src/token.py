"""장기 액세스 토큰 만료 점검·갱신 + GitHub Secret(IG_ACCESS_TOKEN) 업데이트.

주의: 표준 라이브러리 token 모듈과 이름이 같으므로 반드시 패키지로 실행/임포트한다.
  python -m src.token   /   from . import token as ig_token
"""
from __future__ import annotations

import base64
import os
import time

import requests

from .common import StepError, env, get_logger, mask
from . import notify

log = get_logger("token")
GRAPH = f"https://graph.facebook.com/{os.getenv('GRAPH_API_VERSION', 'v23.0')}"
REFRESH_DAYS = int(os.getenv("TOKEN_REFRESH_DAYS", "10"))


def days_left(token: str) -> float | None:
    """debug_token으로 남은 일수 확인. 만료 없음(0)이면 None."""
    app_token = f"{env('META_APP_ID')}|{env('META_APP_SECRET')}"
    r = requests.get(f"{GRAPH}/debug_token", params={"input_token": token, "access_token": app_token}, timeout=20)
    d = r.json().get("data", {}) if r.ok else {}
    if not d:
        raise StepError("token-check", f"debug_token 실패 HTTP {r.status_code}: {mask(r.text[:300])}")
    if not d.get("is_valid"):
        raise StepError("token-check", f"토큰이 유효하지 않습니다: {d.get('error', {}).get('message', '')}")
    exp = d.get("data_access_expires_at") if not d.get("expires_at") else d.get("expires_at")
    if not exp:
        return None
    return (exp - time.time()) / 86400


def exchange(token: str) -> str:
    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": env("META_APP_ID"),
        "client_secret": env("META_APP_SECRET"), "fb_exchange_token": token}, timeout=20)
    if not r.ok or "access_token" not in r.json():
        raise StepError("token-refresh", f"토큰 교환 실패 HTTP {r.status_code}: {mask(r.text[:300])}")
    return r.json()["access_token"]


def update_github_secret(name: str, value: str) -> None:
    from nacl import encoding, public

    pat, repo = env("GH_PAT"), env("GITHUB_REPOSITORY")
    h = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    r = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key", headers=h, timeout=20)
    if not r.ok:
        raise StepError("token-secret", f"공개키 조회 실패 HTTP {r.status_code}")
    key = r.json()
    box = public.SealedBox(public.PublicKey(key["key"].encode(), encoding.Base64Encoder()))
    enc = base64.b64encode(box.encrypt(value.encode())).decode()
    r = requests.put(f"https://api.github.com/repos/{repo}/actions/secrets/{name}", headers=h,
                     json={"encrypted_value": enc, "key_id": key["key_id"]}, timeout=20)
    if r.status_code not in (201, 204):
        raise StepError("token-secret", f"Secret 업데이트 실패 HTTP {r.status_code}")


def ensure_token() -> str:
    """유효한 토큰 반환. 남은 기간 10일 이하면 갱신 후 Secret 업데이트. 실패 시 텔레그램 경고."""
    token = env("IG_ACCESS_TOKEN")
    try:
        left = days_left(token)
    except StepError as e:
        notify.send(f"⚠️ 인스타 토큰 점검 실패: {e.message}")
        raise
    if left is None:
        log.info("토큰 만료 없음")
        return token
    log.info("토큰 남은 기간: %.1f일", left)
    if left > REFRESH_DAYS:
        return token
    try:
        new = exchange(token)
        update_github_secret("IG_ACCESS_TOKEN", new)
        os.environ["IG_ACCESS_TOKEN"] = new
        notify.send(f"🔑 인스타 토큰 자동 갱신 완료 (기존 남은 기간 {left:.1f}일)")
        return new
    except StepError as e:
        notify.send(f"⚠️ 인스타 토큰 자동 갱신 실패 (남은 {left:.1f}일): {e.message}\n수동 갱신이 필요합니다.")
        if left > 0:
            return token
        raise


if __name__ == "__main__":
    ensure_token()
    print("token ok")
