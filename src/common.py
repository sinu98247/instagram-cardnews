"""공통 유틸: 경로, 슬롯 판별, 이력(잠금), 재시도, 비밀값 마스킹 로깅."""
from __future__ import annotations

import datetime as dt
import functools
import json
import logging
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
TEMPLATES = ROOT / "templates"
CONFIG = ROOT / "config"
HISTORY = DATA / "history.json"

KST = dt.timezone(dt.timedelta(hours=9))
ACCOUNT = os.getenv("IG_ACCOUNT_NAME", "@s_98247")

SLOTS = {
    "morning": {"label": "아침", "time": "08:30", "category": "econ",
                "theme": "경제·시장 모닝 브리핑 (밤사이 미국 증시, 환율, 주요 경제 뉴스)"},
    "lunch": {"label": "점심", "time": "12:30", "category": "tech",
              "theme": "AI·테크 핫이슈"},
    "evening": {"label": "퇴근", "time": "18:00", "category": "econ",
                "theme": "경제·재테크 (금리, 부동산, 절세, 정책 변화 등)"},
    "night": {"label": "저녁", "time": "20:00", "category": "tech",
              "theme": "AI·테크 실용 (새 서비스·툴, 활용법)"},
}

SECRET_ENV = ["IG_ACCESS_TOKEN", "META_APP_SECRET", "LLM_API_KEY", "TELEGRAM_BOT_TOKEN",
              "GH_PAT", "IG_USER_ID", "META_APP_ID", "TELEGRAM_CHAT_ID"]


def now_kst() -> dt.datetime:
    return dt.datetime.now(KST)


def detect_slot(t: dt.datetime | None = None) -> str:
    """실행 시각(KST)으로 슬롯 판별. cron은 목표보다 15~18분 일찍 + 지연 가능."""
    t = t or now_kst()
    m = t.hour * 60 + t.minute
    if m < 10 * 60 + 30:
        return "morning"
    if m < 15 * 60 + 30:
        return "lunch"
    if m < 19 * 60:
        return "evening"
    return "night"


def slot_target(slot: str, day: dt.date) -> dt.datetime:
    hh, mm = map(int, SLOTS[slot]["time"].split(":"))
    return dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=KST)


# ---------- 로깅 (비밀값 마스킹) ----------
class _MaskFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        record.msg = mask(msg)
        record.args = ()
        return True


def mask(text: str) -> str:
    text = str(text)
    for k in SECRET_ENV:
        v = os.getenv(k)
        if v and len(v) >= 4:
            text = text.replace(v, f"***{k}***")
    text = re.sub(r"(access_token=|fb_exchange_token=|client_secret=)[^&\s\"']+", r"\1***", text)
    text = re.sub(r"bot\d+:[A-Za-z0-9_-]+", "bot***", text)
    return text


def get_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s"))
        h.addFilter(_MaskFilter())
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


# ---------- 재시도 ----------
class StepError(Exception):
    def __init__(self, step: str, message: str):
        super().__init__(f"[{step}] {message}")
        self.step = step
        self.message = message


def retry(step: str, attempts: int = 3, base_delay: float = 5.0):
    """최초 1회 + 최대 2회 재시도 (지수 백오프: 5s, 10s)."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            log = get_logger("retry")
            last = None
            for i in range(attempts):
                try:
                    return fn(*a, **kw)
                except Exception as e:  # noqa: BLE001
                    last = e
                    if i < attempts - 1:
                        d = base_delay * (2 ** i)
                        log.warning("%s 실패 (%d/%d): %s → %.0fs 후 재시도", step, i + 1, attempts, mask(e), d)
                        time.sleep(d)
            raise StepError(step, mask(str(last)))
        return wrapper
    return deco


# ---------- 이력 ----------
def load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_history(items: list[dict]) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def slot_locked(date_str: str, slot: str, include_preview: bool = True) -> dict | None:
    """동일 날짜·슬롯이 이미 게시(또는 미리보기)되었으면 그 기록을 반환."""
    blocked = {"published"} | ({"preview"} if include_preview else set())
    for h in load_history():
        if h.get("date") == date_str and h.get("slot") == slot and h.get("status") in blocked:
            return h
    return None


def upsert_history(entry: dict) -> None:
    items = load_history()
    items = [h for h in items if not (h.get("date") == entry["date"] and h.get("slot") == entry["slot"])]
    items.append(entry)
    # 90일 이상 지난 기록은 정리
    cutoff = (now_kst() - dt.timedelta(days=90)).date().isoformat()
    items = [h for h in items if h.get("date", "9999") >= cutoff]
    save_history(items)


def env(name: str, required: bool = True, default: str | None = None) -> str | None:
    v = os.getenv(name, default)
    if required and not v:
        raise StepError("config", f"환경변수 {name} 가 설정되지 않았습니다")
    return v
