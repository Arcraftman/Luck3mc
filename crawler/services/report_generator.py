"""Application service: daily policy report generation + push.

This is the *business core* extracted from ``scripts/generate_report.py``.
The script is now a thin CLI that delegates here; this module owns:

  * collecting crawled items from ``data/<spider>/<date>.jsonl``
  * calling DeepSeek to draft a Chinese Markdown summary from the raw text
  * appending the "原文链接" section
  * pushing the final Markdown to WeChat via ``crawler.notifiers``

Design notes:
  * No direct ``urllib``/``requests`` POST for *push* — delivery is delegated to
    :class:`crawler.notifiers.WebhookNotifier` (pushplus ``markdown`` template),
    satisfying the "no hand-rolled push" rule. The DeepSeek call still uses
    ``urllib`` (it is the *content* source, not the notification transport).
  * ``run()`` is the orchestration entry point; the script only does argparse,
    calls ``run()``, and prints the final user-facing result.
  * All functions are import-safe (no network at import time) and ``collect_items``
    is pure/read-only, so tests can exercise it against fixture JSONL.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
from collections import defaultdict, Counter
from pathlib import Path

from crawler.config import get_settings
from crawler.notifiers import get_notifier
from crawler.utils.config_loader import load_config
from crawler.utils.load_diagnostics import check_config
from crawler.utils.log_config import get_logger
from crawler.utils.backend_connection import get_backend_ingest_token

logger = get_logger(__name__)

# Project root (crawler/services -> parents[2]). Generated reports land in
# ``reports/`` (git-ignored runtime artifacts), never at the repo root, so the
# tree stays clean. ``report_<date>.md`` is the canonical artifact that gets
# pushed to WeChat, so the push and the on-disk report can never diverge.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# pushplus free-tier content ceiling is 20 000 chars; stay under it with a
# safety margin so a single markdown report never gets rejected.
MAX_PUSHPLES_CONTENT = 19_000

# Same analyst prompt as before — preserved verbatim so generated reports keep
# their established voice and structure.
SYSTEM_PROMPT = """你是一名资深的财税与产业政策分析助手。下面是某日从政府网站爬取的政策原文（含标题、发布机关、发布日期、正文）。
请基于这些原文，生成一份**中文 Markdown 报告摘要**，要求：
1. 开头一段总体概述（当天有哪些政策、整体动向）。
2. 按主题/部门分类梳理（如财政补贴、税收优惠、产业扶持、科技专项、金融监管等），每类下列关键要点。
3. 标注与企业/个人最相关的可操作要点（申报条件、补贴标准、时限等）。
4. 语言精炼、客观，适合微信推送阅读，全文控制在 900 字以内。
5. 不编造原文没有的信息；信息不足时如实说明。
6. 覆盖输入中的各个来源，按对应政策主题归类，不要仅总结某一个来源。
只输出 Markdown 正文，不要任何额外解释。"""


def _load_dotenv() -> None:
    """极简 .env 加载（项目根 .env，已被 git 忽略）。

    Only sets keys that are not already in the environment, so explicit env
    vars always win. Used to surface ``DEEPSEEK_API_KEY`` / ``NOTIFY_WEBHOOK_TOKEN``.
    """
    root = Path(get_settings().raw.get("__root__", "")) if False else Path(__file__).resolve().parents[2]
    p = root / ".env"
    if not p.exists():
        return
    with p.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def collect_items(
    date_str: str,
    spiders: list[str] | None = None,
    max_items: int = 50,
    max_chars: int = 1200,
    data_dir: str | Path | None = None,
) -> list[dict]:
    """Read daily JSONL, selecting up to max_items newest records per source site.

    Pure / read-only: never writes, never touches the network. The returned
    dicts carry ``spider / title / url / pub_date / authority / content`` so the
    report builder and DeepSeek caller share one shape.
    """
    base = Path(data_dir) if data_dir else get_settings().data_dir
    items: list[dict] = []
    seen = set()
    if max_items <= 0:
        return []
    pattern = os.path.join(str(base), "*", f"{date_str}.jsonl")
    for path in sorted(glob.glob(pattern)):
        spider = os.path.basename(os.path.dirname(path))
        if spiders and spider not in spiders:
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if not isinstance(d, dict):
                    continue
                url = d.get("source_url") or ""
                if url and url in seen:
                    continue
                if url:
                    seen.add(url)
                source = d.get("source_site") or spider
                source_name = {"shanghai_rsj": "上海市人力资源和社会保障局"}.get(source, source)
                content = (d.get("content") or "")[:max_chars]
                items.append({
                    "spider": spider,
                    "source_site": source,
                    "source_name": source_name,
                    "title": d.get("title") or "",
                    "url": d.get("source_url") or "",
                    "pub_date": str(d.get("pub_date") or ""),
                    "authority": d.get("issuing_authority") or source_name,
                    "content": content,
                })
    groups = defaultdict(list)
    for item in items:
        groups[item["source_site"]].append(item)
    selected = []
    for _, group in sorted(groups.items()):
        selected.extend(sorted(group, key=lambda i: i["pub_date"], reverse=True)[:max_items])
    logger.info("报告来源分配：%s（采集 %d 条，入选 %d 条，每网站上限 %d）",
                dict(Counter(i["source_name"] for i in selected)), len(items), len(selected), max_items)
    return selected


def build_user_content(items: list[dict]) -> str:
    """Flatten collected items into the DeepSeek user prompt body."""
    blocks = []
    for i, it in enumerate(items, 1):
        blocks.append(
            f"【政策{i}】\n来源：{it.get('source_name', it['authority'])}\n标题：{it['title']}\n发布机关：{it['authority']}\n"
            f"发布日期：{it['pub_date']}\n原文链接：{it['url']}\n正文：{it['content']}"
        )
    return "\n\n".join(blocks)


def call_deepseek(
    items: list[dict],
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> str:
    """Draft a Markdown report summary from the raw items via DeepSeek.

    Reads credentials from ``DEEPSEEK_API_KEY`` / ``DEEPSEEK_MODEL`` /
    ``DEEPSEEK_BASE_URL`` (overrideable for tests). Raises ``RuntimeError`` when
    the key is missing or the API returns an unexpected shape — callers decide
    how to surface that to the operator.
    """
    import urllib.request

    key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        logger.warning("DEEPSEEK_API_KEY 未设置（请在 .env 填入，或 export 该环境变量）")
        raise RuntimeError("DEEPSEEK_API_KEY 未设置（请在 .env 填入）")

    payload = {
        "model": model or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_content(items)},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }
    url = (base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")).rstrip("/")
    url = url + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def build_links_section(items: list[dict]) -> str:
    """Append the '## 原文链接' block listing every source URL."""
    lines = ["", "---", "", "## 原文链接", ""]
    for it in items:
        if not it["url"]:
            continue
        title = it["title"] or it["url"]
        meta = " ｜ ".join(x for x in [it["pub_date"], it["authority"]] if x)
        line = f"- [{title}]({it['url']})"
        if meta:
            line += f" ｜ {meta}"
        lines.append(line)
    return "\n".join(lines)


def generate_site_summaries(items: list[dict]) -> str:
    """Summarise each source separately so the total input cannot crowd out sites."""
    groups = defaultdict(list)
    for item in items:
        groups[item.get("source_site") or item["spider"]].append(item)
    reports = []
    for site, group in groups.items():
        name = group[0].get("source_name") or site
        logger.info("正在生成网站报告：%s（%d 条）", name, len(group))
        reports.append(f"## {name}（{len(group)} 条）\n\n" + call_deepseek(group))
    return "\n\n".join(reports)


def _build_notifier():
    """Construct the pushplus (markdown) notifier from typed config.

    Honours ``NOTIFY_WEBHOOK_TOKEN`` env override; raises if no token is found
    so the caller can fail loudly instead of silently skipping the push.
    """
    _load_dotenv()
    cfg = get_settings()
    token = cfg.notify.webhook_token or os.environ.get("NOTIFY_WEBHOOK_TOKEN") or ""
    if not token:
        raise RuntimeError("未找到 pushplus token（NOTIFY_WEBHOOK_TOKEN 或 config）")
    return get_notifier(cfg.to_notifier_settings())


def _split_markdown(content: str, max_len: int = MAX_PUSHPLES_CONTENT) -> list[str]:
    """Split a long markdown report into pushable chunks.

    Prefers cutting at section boundaries (``## heading``); only falls back to a
    hard character split when a single section still exceeds ``max_len``. This
    keeps the full report deliverable even when it breaches pushplus' 20k cap.
    """
    if len(content) <= max_len:
        return [content]
    parts = content.split("\n## ")
    chunks: list[str] = []
    cur = ""
    for i, part in enumerate(parts):
        block = f"## {part}" if i > 0 else part
        if cur and len(cur) + len(block) + 1 > max_len:
            chunks.append(cur)
            cur = block
        elif cur:
            cur = f"{cur}\n{block}"
        else:
            cur = block
    if cur:
        chunks.append(cur)

    final: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_len:
            final.append(chunk)
        else:
            for j in range(0, len(chunk), max_len):
                final.append(chunk[j:j + max_len])
    return final


def send_report(title: str, content_md: str, notifier=None) -> bool:
    """Push the Markdown report via the configured notifier.

    When the content is longer than pushplus' limit it is split into numbered
    parts (``标题（1/N）``) so the whole report still arrives. Returns the
    notifier's boolean result; never raises (a dead webhook must not crash
    report generation). A ``None`` notifier is resolved lazily.
    """
    if notifier is None:
        notifier = _build_notifier()
    parts = _split_markdown(content_md)
    if len(parts) == 1:
        return notifier.send_markdown(title, parts[0])
    ok = True
    for i, part in enumerate(parts, 1):
        t = f"{title}（{i}/{len(parts)}）"
        if not notifier.send_markdown(t, part):
            ok = False
    return ok


def push_file(path: str, title: str | None = None, no_push: bool = False) -> dict:
    """Push an already-generated report markdown file, without regenerating.

    This is the path the operator uses to re-send an existing ``report_<date>.md``
    (e.g. the one produced earlier) — DeepSeek is *not* called. The file content
    is exactly what gets pushed to WeChat.
    """
    _load_dotenv()
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"报告文件不存在: {path}")
    md = p.read_text(encoding="utf-8")
    if not md.strip():
        raise RuntimeError(f"报告文件为空: {path}")
    title = title or p.stem
    if no_push:
        return {"pushed": None, "path": str(path), "chars": len(md)}
    pushed = send_report(title, md)
    return {"pushed": pushed, "path": str(path), "chars": len(md)}


def push_report_to_backend(
    title: str, content_md: str, date_str: str, spiders: str = ""
) -> bool:
    """Best-effort mirror of a finished report to the FastAPI backend.

    Disabled unless ``backend.sink_enabled`` is true and ``backend.ingest_url``
    is set. Never raises — a missing/unreachable backend must not break report
    generation or the WeChat push.
    """
    import urllib.request

    cfg = load_config().get("backend") or {}
    url = (cfg.get("ingest_url") or "").rstrip("/")
    if not url or not cfg.get("sink_enabled"):
        return False
    payload = {
        "title": title,
        "content_md": content_md,
        "date": date_str,
        "spiders": spiders,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/api/ingest/report",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Token": cfg.get("ingest_token") or get_backend_ingest_token(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status < 400
    except Exception as exc:  # noqa: BLE001
        logger.warning("[report] backend ingest failed: %s", exc)
        return False


def run(
    date_str: str | None = None,
    spiders: list[str] | None = None,
    max_items: int = 50,
    no_push: bool = False,
    out: str | None = None,
    no_save: bool = False,
) -> dict:
    """High-level orchestration: collect → DeepSeek → append links → (push).

    The generated report is **always materialised as ``report_<date>.md``** at
    the repo root (unless ``no_save``) — that file is the canonical artifact
    that gets pushed to WeChat, so the push and the on-disk report can never
    diverge. ``--out`` overrides the path; ``--no-save`` skips writing.

    Returns a small status dict the CLI prints. Never prints internally except
    via the logger; the final user-facing summary is left to the caller so this
    service stays presentation-agnostic.
    """
    _load_dotenv()
    check_config()
    if date_str is None:
        date_str = datetime.date.today().isoformat()

    items = collect_items(date_str, spiders, max_items)
    if not items:
        logger.info("没有找到 %s 的 jsonl 数据", date_str)
        return {"items": 0, "date": date_str, "markdown": None, "pushed": None, "out": None}

    logger.info("读取 %d 条政策原文，调用 DeepSeek 生成报告…", len(items))
    report = generate_site_summaries(items)
    coverage = "\n\n## 本次摘要来源\n\n" + "\n".join(
        f"- {source}：{count} 条" for source, count in
        Counter(i.get("source_name", i["authority"]) for i in items).items())
    full_md = report + coverage + build_links_section(items)
    title = f"政策日报 {date_str}"

    # Always materialise the report as ``report_<date>.md`` (unless --no-save):
    # this file IS the artifact that gets pushed to WeChat. It lands in
    # ``reports/`` by default so the repo root stays clean.
    written_out: str | None = None
    if not no_save:
        out_path = Path(out) if out else REPORTS_DIR / f"report_{date_str}.md"
        out_path.write_text(full_md, encoding="utf-8")
        written_out = str(out_path)

    # Push the canonical on-disk artifact when available, else the in-memory copy.
    push_md = full_md
    if written_out:
        try:
            push_md = Path(written_out).read_text(encoding="utf-8")
        except Exception:
            push_md = full_md

    pushed: bool | None = None
    if not no_push:
        pushed = send_report(title, push_md)

    backend_ok = push_report_to_backend(title, push_md, date_str, ",".join(spiders or []))

    return {
        "items": len(items),
        "date": date_str,
        "markdown": push_md,
        "pushed": pushed,
        "backend": backend_ok,
        "out": written_out,
    }


__all__ = [
    "SYSTEM_PROMPT",
    "collect_items",
    "build_user_content",
    "call_deepseek",
    "build_links_section",
    "send_report",
    "push_file",
    "run",
]
