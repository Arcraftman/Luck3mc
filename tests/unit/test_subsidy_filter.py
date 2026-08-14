"""Unit tests for :func:`crawler.pipelines.subsidy_filter.matches_subsidy`.

Covers the three requested behaviours: title hit, body hit (via a *program*
keyword), and trade-remedy (反补贴) exclusion. No network involved.
"""

from __future__ import annotations

from crawler.pipelines.subsidy_filter import matches_subsidy


def test_title_hit_with_generic_keyword():
    # A subsidy keyword in the title is a strong signal -> kept.
    assert matches_subsidy(title="新能源汽车购置补贴通知") is True


def test_body_hit_with_program_keyword():
    # No title/summary hit, but a concrete program keyword in the body fires.
    assert matches_subsidy(title="", content="消费者可享以旧换新补贴政策，最高补贴万元") is True


def test_antidumping_subsidy_excluded():
    # "反补贴" contains "补贴" but must NOT be treated as a fiscal subsidy.
    assert matches_subsidy(title="某国对华反补贴调查正式启动") is False


def test_generic_body_only_does_not_false_positive():
    # Bare "补贴" only in the body (not a body-safe program keyword) is ignored
    # to avoid noise from passing news mentions.
    assert matches_subsidy(title="", content="本网站提供各类补贴政策查询服务") is False


def test_empty_text_is_not_a_subsidy():
    assert matches_subsidy(title="", summary="", content="") is False


def test_subsidy_keyword_in_summary_counts_as_head():
    # Summary shares the "head" rule with the title.
    assert matches_subsidy(title="", summary="关于留抵退税政策的解答") is True
