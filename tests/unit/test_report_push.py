"""Tests for the report push changes (Task 2): split + push existing .md file."""

import importlib

import crawler.services.report_generator as rg
from crawler.services.report_generator import _split_markdown, push_file


def test_split_markdown_short_stays_single():
    text = "# 标题\n正文" * 10
    assert _split_markdown(text) == [text]


def test_split_markdown_splits_long_content():
    chunk = "正文内容" * 300  # ~1200 chars
    long = "\n## ".join([f"第{i}节\n{chunk}" for i in range(30)])  # ~36k chars
    parts = _split_markdown(long)
    assert len(parts) >= 2
    assert all(len(p) <= rg.MAX_PUSHPLES_CONTENT for p in parts)
    # First part should contain the leading (non-##) heading context.
    assert parts[0].startswith("第0节") or "第0节" in parts[0]


def test_push_file_reads_disk_and_calls_send(monkeypatch, tmp_path):
    md = "# 政策日报 2026-08-12\n\n这是一份示例报告。" + "要点。" * 50
    f = tmp_path / "report_2026-08-12.md"
    f.write_text(md, encoding="utf-8")

    captured = {}

    def fake_send(title, content_md, notifier=None):
        captured["title"] = title
        captured["content"] = content_md
        return True

    monkeypatch.setattr(rg, "send_report", fake_send)
    res = push_file(str(f))
    assert res["pushed"] is True
    assert captured["content"] == md
    assert captured["title"] == "report_2026-08-12"


def test_push_file_missing_raises(tmp_path):
    import pytest

    with pytest.raises(RuntimeError):
        push_file(str(tmp_path / "nope.md"))


def test_push_file_no_push_does_not_send(monkeypatch, tmp_path):
    f = tmp_path / "report_x.md"
    f.write_text("# x\n正文", encoding="utf-8")
    called = {"n": 0}
    monkeypatch.setattr(rg, "send_report", lambda *a, **k: called.__setitem__("n", 1))
    res = push_file(str(f), no_push=True)
    assert res["pushed"] is None
    assert called["n"] == 0
