"""오케스트레이터: 수집 → 원고 → 렌더 → 커밋/푸시 → URL 검증 → (검수 미리보기 | 게시) → 기록·알림.

실행: python -m src.main [--slot morning|lunch|evening|night] [--force] [--publish-preview] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from .common import (OUTPUT, ROOT, SLOTS, StepError, detect_slot, get_logger, mask, now_kst,
                     retry, slot_locked, slot_target, upsert_history)
from . import collect as collect_mod
from . import notify
from . import publish as publish_mod
from . import render as render_mod
from . import token as ig_token
from . import write as write_mod

log = get_logger("main")


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} 실패: {mask(r.stderr.strip()[:300])}")
    return r.stdout.strip()


@retry("git-push", attempts=3, base_delay=5)
def commit_push(paths: list[str], message: str) -> str:
    git("add", *paths)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0:
        git("commit", "-m", message)
    git("pull", "--rebase", "--autostash")
    git("push")
    return git("rev-parse", "HEAD")


def raw_urls(sha: str, files: list[str]) -> list[str]:
    repo = os.environ["GITHUB_REPOSITORY"]
    return [f"https://raw.githubusercontent.com/{repo}/{sha}/{os.path.relpath(f, ROOT)}" for f in files]


@retry("collect", attempts=3, base_delay=10)
def step_collect(slot):
    return collect_mod.collect(slot)


@retry("write", attempts=3, base_delay=10)
def step_write(collected):
    return write_mod.write(collected)


@retry("render", attempts=3, base_delay=5)
def step_render(doc, out_dir):
    return render_mod.render(doc, out_dir)


def build(slot: str, date: str) -> tuple[dict, list[str]]:
    out_dir = OUTPUT / date / slot
    collected = step_collect(slot)
    log.info("선정: %s (%s)", collected["selected"]["title"], collected["reason"])
    doc = step_write(collected)
    doc["date"] = date
    res = step_render(doc, out_dir)
    for _ in range(2):  # 폰트 축소로도 넘치면 원고 재요약 후 재렌더
        if not res["overflow"]:
            break
        log.info("넘침 카드 %s → 재요약", [i + 1 for i in res["overflow"]])
        doc = write_mod.shorten(doc, res["overflow"])
        res = step_render(doc, out_dir)
    if res["overflow"]:
        raise StepError("render", f"재요약 후에도 글자 넘침: 카드 {[i + 1 for i in res['overflow']]}")
    (out_dir / "post.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "collected.json").write_text(json.dumps(
        {k: collected[k] for k in ("selected", "reason", "candidates")} |
        {"sources": [{k: s[k] for k in ("source", "title", "url")} for s in collected["sources"]]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return doc, res["files"]


def run(slot: str, force: bool, publish_preview: bool, dry_run: bool) -> int:
    t = now_kst()
    date = t.date().isoformat()
    label = f"{SLOTS[slot]['label']}({SLOTS[slot]['time']})"
    review = os.getenv("REVIEW_MODE", "true").lower() == "true" and not publish_preview
    log.info("슬롯=%s 날짜=%s REVIEW_MODE=%s", slot, date, review)

    lock = slot_locked(date, slot, include_preview=not publish_preview)
    if lock and not force:
        log.info("이미 처리된 슬롯입니다 (%s) → 종료", lock.get("status"))
        return 0

    step = "init"
    entry = {"date": date, "slot": slot, "started_at": t.isoformat()}
    try:
        if not review and not dry_run:
            step = "token"
            ig_token.ensure_token()

        out_dir = OUTPUT / date / slot
        if publish_preview:
            step = "load-preview"
            doc = json.loads((out_dir / "post.json").read_text(encoding="utf-8"))
            files = sorted(str(p) for p in out_dir.glob("card_*.jpg"))
        else:
            step = "build"
            doc, files = build(slot, date)
        entry |= {"topic": doc["topic"], "source_title": doc["sources"][0]["title"] if doc["sources"] else "",
                  "sources": [s["url"] for s in doc["sources"]]}
        if dry_run:
            log.info("dry-run: 렌더링까지만 수행 → %s", files)
            return 0

        step = "commit-images"
        sha = commit_push([str(out_dir.relative_to(ROOT))], f"cardnews: {date} {slot} images")
        urls = raw_urls(sha, files)
        step = "verify-url"
        publish_mod.verify_urls(urls)

        if review:
            step = "preview"
            notify.preview(label, doc, files)
            entry |= {"status": "preview", "image_urls": urls}
        else:
            step = "publish"
            res = publish_mod.publish(urls, doc["caption"], publish_at=slot_target(slot, t.date()))
            entry |= {"status": "published", "media_id": res["media_id"], "permalink": res["permalink"],
                      "published_at": now_kst().isoformat(), "image_urls": urls}
            notify.success(label, doc["topic"], res["permalink"])
        upsert_history(entry)
        commit_push(["data/history.json"], f"history: {date} {slot} {entry['status']}")
        return 0
    except StepError as e:
        return _fail(entry, label, e.step or step, e.message)
    except Exception as e:  # noqa: BLE001
        return _fail(entry, label, step, str(e))


def _fail(entry: dict, label: str, step: str, message: str) -> int:
    log.error("실패 [%s] %s", step, mask(message))
    notify.failure(label, step, message)
    entry |= {"status": "failed", "failed_step": step, "error": mask(message)[:500]}
    try:
        upsert_history(entry)
        commit_push(["data/history.json"], f"history: {entry['date']} {entry['slot']} failed")
    except Exception as e:  # noqa: BLE001
        log.error("실패 기록 커밋도 실패: %s", mask(e))
    return 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", default="auto", choices=["auto", *SLOTS])
    ap.add_argument("--force", action="store_true", help="잠금 무시 (주의: 중복 게시 가능)")
    ap.add_argument("--publish-preview", action="store_true", help="REVIEW_MODE 미리보기 결과를 그대로 게시")
    ap.add_argument("--dry-run", action="store_true", help="수집·원고·렌더까지만")
    a = ap.parse_args()
    slot = detect_slot() if a.slot == "auto" else a.slot
    sys.exit(run(slot, a.force, a.publish_preview, a.dry_run))


if __name__ == "__main__":
    main()
