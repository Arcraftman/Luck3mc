"""Application services layer.

Thin package that groups the business-core services extracted from the
``scripts/`` CLIs:
  * :mod:`crawler.services.report_generator` — daily DeepSeek report + push
  * :mod:`crawler.services.digest_builder`  — weekly subsidy digest + push

Keeping the orchestration here (instead of in the scripts) implements the
dependency-inversion goal: spiders/scripts are the interface layer, services
are the application layer, and they depend on ``crawler.domain`` (keywords /
subsidy matching) and ``crawler.notifiers`` — never on ad-hoc ``urllib`` POSTs.
"""

from crawler.services import digest_builder, report_generator

__all__ = ["report_generator", "digest_builder"]
