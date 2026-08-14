"""Generic broad sweep across operator-provided roots (incl. local-government).

This spider is now a thin subclass of :class:`PolicyRootBaseSpider`: it declares
``category = "gov_general"`` and the actual roots live in
``gov_categories.yaml`` (the ``gov_general`` block). All crawling machinery —
rules, compliance guard, policy classification, item extraction and politeness
settings — is inherited, so there is no per-site hard-coding here.

Why this spider still exists
----------------------------
The 5 category spiders (``caishui`` / ``gaoqi`` / ``gongxin`` / ``yanfa`` /
``kexiao``) cover the national fiscal / tech / industry sites. This one is the
catch-all for *everything else* the operator wants swept — currently
``www.gov.cn/zhengce/`` plus a placeholder for the Shanghai municipal
government (fill in the real root in ``gov_categories.yaml``). It also accepts
``-a roots=url1,url2`` for a one-off sweep without touching the YAML.

Run
---
    scrapy crawl gov_policy_root
    scrapy crawl gov_policy_root -a roots=https://www.gov.cn/zhengce/
"""

from crawler.spiders.policy_root_base import PolicyRootBaseSpider


class GovPolicyRootSpider(PolicyRootBaseSpider):
    name = "gov_policy_root"
    category = "gov_general"
    # Fallback tag; per-root names (from gov_categories.yaml) win via meta.
    source_site = "gov_policy_root"
