"""텔레그램 알림 / 미리보기 전송. 토큰은 절대 로그에 남기지 않는다."""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from .common import get_logger, mask

log = get_logger("notify")


def _api(method: str) -> str | None:
    tok = os.getenv("TELEGRAM_BOT_TOKEN")
    return f"https://api.telegram.org/bot{tok}/{method}" if tok else None


def _chat() -> str | None:
    return os.getenv("TELEGRAM_CHAT_ID")


def send(text: str) -> bool:
    url, chat = _api("sendMessage"), _chat()
    if not url or not chat:
        log.warning("텔레그램 설정이 없어 알림을 건너뜁니다: %s", text[:80])
        return False
    for _ in range(3):
        try:
            r = requests.post(url, data={"chat_id": chat, "text": text[:4096], "disable_web_page_preview": "true"}, timeout=20)
            if r.ok:
                return True
            log.warning("텔레그램 응답 오류 %s", r.status_code)
        except requests.RequestException as e:
            log.warning("텔레그램 전송 실패: %s", mask(e))
    return False


def send_media_group(files: list[str], caption: str = "") -> bool:
    url, chat = _api("sendMediaGroup"), _chat()
    if not url or not chat:
        return False
    media, handles = [], {}
    for i, f in enumerate(files[:10]):
        key = f"photo{i}"
        handles[key] = open(f, "rb")
        item = {"type": "photo", "media": f"attach://{key}"}
        if i == 0 and caption:
            item["caption"] = caption[:1024]
        media.append(item)
    try:
        r = requests.post(url, data={"chat_id": chat, "media": json.dumps(media)}, files=handles, timeout=120)
        if not r.ok:
            log.warning("미디어 그룹 전송 오류 %s", r.status_code)
        return r.ok
    except requests.RequestException as e:
        log.warning("미디어 그룹 전송 실패: %s", mask(e))
        return False
    finally:
        for h in handles.values():
            h.close()


def success(slot_label: str, topic: str, link: str) -> None:
    send(f"✅ 게시 완료\n슬롯: {slot_label}\n주제: {topic}\n링크: {link}")


def failure(slot_label: str, step: str, message: str) -> None:
    send(f"❌ 게시 실패 (슬롯 건너뜀)\n슬롯: {slot_label}\n실패 단계: {step}\n에러: {mask(message)[:1500]}")


def preview(slot_label: str, doc: dict, files: list[str]) -> None:
    send_media_group(files, f"[검수 미리보기] {slot_label} · {doc['topic']}")
    src = "\n".join(f"- {s['source']}: {s['url']}" for s in doc.get("sources", []))
    send(f"📝 REVIEW_MODE 미리보기 — 자동 게시하지 않았습니다.\n슬롯: {slot_label}\n주제: {doc['topic']}\n\n"
         f"[캡션]\n{doc['caption']}\n\n[선정 근거] {doc.get('reason','')}\n[출처]\n{src}\n\n"
         f"게시하려면 GitHub Actions에서 'Post card news'를 slot={doc['slot']}, publish_preview=true 로 수동 실행하세요.")


if __name__ == "__main__":
    import sys
    print(send(" ".join(sys.argv[1:]) or "테스트 메시지"))
