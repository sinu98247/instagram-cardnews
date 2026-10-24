"""카드 렌더링: templates/card.html → Playwright(Chromium) 스크린샷 → 1080×1350 JPEG(q90, 8MB 이하)."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from .common import ACCOUNT, OUTPUT, SLOTS, TEMPLATES, StepError, get_logger, now_kst

log = get_logger("render")
W, H = 1080, 1350
MAX_BYTES = 8 * 1024 * 1024

# 단계적 폰트 축소 (명세: 표지 72~88px, 본문 40~44px)
COVER_STEPS = [(88, 46), (84, 44), (80, 42), (76, 40), (72, 40)]
BODY_STEPS = [(60, 44), (58, 43), (56, 42), (54, 41), (52, 40)]
END_STEPS = [(58, 42), (56, 41), (54, 40)]

CHECK_JS = """
() => {
  const c = document.getElementById('content');
  const cr = c.getBoundingClientRect();
  const over = c.scrollHeight > c.clientHeight + 1 || c.scrollWidth > c.clientWidth + 1;
  const clipped = [];
  c.querySelectorAll('h1,h2,p,li,.sub,.cta,.disclaimer').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.bottom > cr.bottom + 1 || r.right > cr.right + 1 || r.left < cr.left - 1) clipped.push(el.textContent.slice(0, 20));
  });
  return {over, clipped, fontOk: document.fonts.check('800 80px Pretendard') && document.fonts.check('400 40px Pretendard')};
}
"""


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))


def _cover_title_html(title: str) -> Markup:
    # **강조** 구문을 <em>으로 (없으면 그대로)
    esc = html.escape(title)
    parts = esc.split("**")
    out = "".join(f"<em>{p}</em>" if i % 2 else p for i, p in enumerate(parts))
    return Markup(out.replace("\n", "<br>"))


def card_context(doc: dict, i: int, steps: tuple[int, int]) -> dict:
    c = doc["cards"][i]
    total = len(doc["cards"])
    kind = "cover" if i == 0 else ("end" if i == total - 1 else "body")
    if kind == "cover":
        size_vars = f"--title-size:{steps[0]}px; --sub-size:{steps[1]}px;"
    else:
        size_vars = f"--h2-size:{steps[0]}px; --body-size:{steps[1]}px;"
    slot = doc.get("slot", "morning")
    date = doc.get("date") or now_kst().date().isoformat()
    d = dt.date.fromisoformat(date)
    return {
        "base_href": TEMPLATES.resolve().as_uri() + "/",
        "size_vars": Markup(size_vars),
        "category": doc.get("category", SLOTS[slot]["category"]),
        "kind": kind,
        "index": i,
        "tag": f"{SLOTS[slot]['label']} 브리핑 · {'경제' if SLOTS[slot]['category']=='econ' else 'AI·테크'}",
        "title": c.get("title", "").replace("**", ""),
        "title_html": _cover_title_html(c.get("title", "")),
        "body": c.get("body", ""),
        "lines": [x.strip() for x in c.get("body", "").split("\n") if x.strip()],
        "cta": c.get("cta") or "저장해두고 다시 보세요 · 팔로우하면 매일 받아봐요",
        "disclaimer": doc.get("disclaimer", "") if kind == "end" else "",
        "account": ACCOUNT,
        "date_label": f"{d.month}.{d.day} {SLOTS[slot]['label']}",
        "page": i + 1,
        "total": total,
    }


def render(doc: dict, out_dir: Path) -> dict:
    """반환: {"files": [...], "overflow": [카드 인덱스...]}"""
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    tpl = _env().get_template("card.html")
    files, overflow = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--allow-file-access-from-files"])
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        total = len(doc["cards"])
        for i in range(total):
            steps_list = COVER_STEPS if i == 0 else (END_STEPS if i == total - 1 else BODY_STEPS)
            result = None
            html_path = out_dir / f"_card_{i+1}.html"
            for steps in steps_list:
                html_path.write_text(tpl.render(**card_context(doc, i, steps)), encoding="utf-8")
                page.goto(html_path.resolve().as_uri(), wait_until="load")
                page.evaluate("document.fonts.ready")
                result = page.evaluate(CHECK_JS)
                if not result["fontOk"]:
                    raise StepError("render", "Pretendard 폰트 로딩 실패 (templates/fonts 확인)")
                if not result["over"] and not result["clipped"]:
                    break
                log.info("카드 %d 넘침 → 폰트 축소 %s", i + 1, steps)
            if result["over"] or result["clipped"]:
                overflow.append(i)
            jpg = out_dir / f"card_{i+1:02d}.jpg"
            page.screenshot(path=str(jpg), type="jpeg", quality=90, clip={"x": 0, "y": 0, "width": W, "height": H})
            html_path.unlink(missing_ok=True)
            files.append(jpg)
        browser.close()
    verify_images(files)
    return {"files": [str(f) for f in files], "overflow": overflow}


def verify_images(files: list[Path]) -> None:
    from PIL import Image
    for f in files:
        size = f.stat().st_size
        if size > MAX_BYTES:
            raise StepError("render", f"{f.name} 가 8MB를 초과합니다 ({size} bytes)")
        with Image.open(f) as im:
            if im.format != "JPEG" or im.size != (W, H):
                raise StepError("render", f"{f.name} 형식 오류: {im.format} {im.size}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("doc_json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    doc = json.loads(Path(a.doc_json).read_text(encoding="utf-8"))
    out = Path(a.out) if a.out else OUTPUT / (doc.get("date") or now_kst().date().isoformat()) / doc["slot"]
    print(json.dumps(render(doc, out), ensure_ascii=False, indent=2))
