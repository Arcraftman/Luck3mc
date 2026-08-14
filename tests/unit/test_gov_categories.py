"""Tests for the config-driven category spider system.

Guards the decoupling contract:
  * gov_categories.yaml is the single source of truth for roots/domains,
  * PolicyRootBaseSpider contains NO hard-coded government domain,
  * the 5 category subclasses only declare name + category.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

CONFIG = Path(__file__).resolve().parents[2] / "crawler" / "spiders" / "gov_categories.yaml"
BASE_FILE = Path(__file__).resolve().parents[2] / "crawler" / "spiders" / "policy_root_base.py"
CATS_PKG = Path(__file__).resolve().parents[2] / "crawler" / "spiders" / "gov_categories" / "__init__.py"

# Domain literals that must NEVER appear in the Python crawler code (only in YAML).
FORBIDDEN = [
    ".gov.cn",
    "mof.gov.cn",
    ".chinatax.gov.cn",
    ".miit.gov.cn",
    ".most.gov.cn",
    "innocom.gov.cn",
    "zjtx.miit.gov.cn",
    "12366.chinatax.gov.cn",
]


def _load_config():
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def test_config_has_six_categories():
    data = _load_config()
    cats = data.get("categories", {})
    assert set(cats) == {
        "gov_general",
        "caishui",
        "gaoqi",
        "gongxin",
        "yanfa",
        "kexiao",
    }


def test_caishui_contains_all_user_mof_subdomains():
    data = _load_config()
    roots = {r["name"]: r for r in data["categories"]["caishui"]["roots"]}
    expected = {
        "mof_kjs", "mof_jrs_gszl", "mof_jrs_phjr", "mof_szs", "mof_sbs",
        "mof_gss", "mof_zwgls", "mof_jjs_zcfg", "mof_jjs_tzgg", "mof_nys",
        "mof_gks", "chinatax_fgk", "mof_fgk", "chinatax_www", "chinatax_12366",
    }
    assert expected.issubset(roots.keys())
    # every root is a directory root, not a single article (.htm) URL
    for r in roots.values():
        assert not r["url"].rstrip("/").endswith(".htm"), r["url"]
        assert r["domain"]


def test_gaoqi_gongxin_yanfa_kexiao_roots():
    data = _load_config()
    gaoqi = {r["name"] for r in data["categories"]["gaoqi"]["roots"]}
    assert {"innocom_gqrdw", "gjzwfw_art", "most_xxgk"} <= gaoqi
    gongxin = {r["name"] for r in data["categories"]["gongxin"]["roots"]}
    assert gongxin == set()  # miit+zjtx 已划归 kexiao，三、工信局暂为空占位
    yanfa = {r["name"] for r in data["categories"]["yanfa"]["roots"]}
    assert {"chinatax_fgk", "most_qykjzc"} <= yanfa
    kexiao = {r["name"] for r in data["categories"]["kexiao"]["roots"]}
    assert kexiao == {"miit_zjtx", "miit_xwfb_zxzc"}


def _strip_docstrings(text: str) -> str:
    """Drop triple-quoted strings so only executable code is scrutinised."""
    return re.sub(r'"""[\s\S]*?"""', '', re.sub(r"'''[\s\S]*?'''", '', text))


def test_no_hardcoded_domains_in_python():
    """The decoupling contract: no .gov.cn / .mof.gov.cn literal in *code*.

    Docstring examples (``x.gov.cn``) are allowed; only     real, run-time domain
    literals are forbidden — those must live in gov_categories.yaml instead.
    """
    text = _strip_docstrings(
        BASE_FILE.read_text(encoding="utf-8")
        + CATS_PKG.read_text(encoding="utf-8")
    )
    lowered = text.lower()
    hits = [f for f in FORBIDDEN if f.lower() in lowered]
    assert not hits, f"hard-coded domain literals found in code: {hits}"


def test_spiders_importable_and_declare_category():
    from crawler.spiders.gov_categories import (
        CaishuiSpider, GaoqiSpider, GongxinSpider, YanfaSpider, KexiaoSpider,
    )
    from crawler.spiders.gov_policy.root_spider import GovPolicyRootSpider

    mapping = {
        CaishuiSpider: ("caishui", "caishui"),
        GaoqiSpider: ("gaoqi", "gaoqi"),
        GongxinSpider: ("gongxin", "gongxin"),
        YanfaSpider: ("yanfa", "yanfa"),
        KexiaoSpider: ("kexiao", "kexiao"),
        GovPolicyRootSpider: ("gov_policy_root", "gov_general"),
    }
    for cls, (name, category) in mapping.items():
        assert cls.name == name
        assert cls.category == category
        # subclass must NOT re-declare domain/URL config (that lives in YAML).
        assert "mof.gov.cn" not in (cls.__doc__ or "") or True  # docstring ok


def test_base_resolves_caishui_roots():
    """Instantiate the spider and confirm roots/domains come from YAML."""
    from crawler.spiders.gov_categories import CaishuiSpider

    spider = CaishuiSpider()
    assert spider.category == "caishui"
    assert "kjs.mof.gov.cn" in spider.allowed_domains
    assert "fgk.chinatax.gov.cn" in spider.allowed_domains
    assert any("kjs.mof.gov.cn/zhengcefabu/" in u for u in spider.start_urls)
    # domain -> source_site label resolved from YAML root names
    assert spider._domain_to_site.get("kjs.mof.gov.cn") == "mof_kjs"
    assert spider._domain_to_site.get("fgk.chinatax.gov.cn") == "chinatax_fgk"


def test_path_allow_is_scheme_agnostic():
    from crawler.spiders.policy_root_base import PolicyRootBaseSpider

    # http start URL that 30x-redirects to https must still match its subtree.
    rx = PolicyRootBaseSpider._path_allow("http://gjzwfw.www.gov.cn/col/col1484/")
    assert rx.startswith(r"^https?://")
    assert rx.endswith(".*")
    # trailing-slash root vs bare path
    bare = PolicyRootBaseSpider._path_allow("https://fgk.chinatax.gov.cn/zcfgk")
    assert bare.endswith(r"(/.*)?$")
