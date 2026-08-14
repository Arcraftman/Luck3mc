"""Spider package.

All production spiders are **config-driven** and live under ``gov_categories/``
(each a ~4-line subclass of
:class:`crawler.spiders.policy_root_base.PolicyRootBaseSpider`), with their
root URLs / domains declared in ``gov_categories.yaml``. ``gov_policy/`` holds
the generic / local-government fallback spider. No spider contains a hard-coded
``.gov.cn`` domain — that is the project's decoupling contract.
"""
