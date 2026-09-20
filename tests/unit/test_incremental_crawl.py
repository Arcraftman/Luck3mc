from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scrapy.exceptions import DropItem
from scrapy.http import HtmlResponse, Request
from scrapy.settings import Settings

from crawler.db.models import CrawledUrl
from crawler.db.session import get_engine, get_sessionmaker, init_db
from crawler.pipelines.deduplication import DeduplicatePipeline
from crawler.spiders.gov_policy.root_spider import GovPolicyRootSpider


def test_persisted_details_skip_download_but_lists_and_new_urls_continue(tmp_path):
    database = f"sqlite:///{tmp_path / 'crawl.db'}"
    engine = get_engine(database)
    init_db(engine)
    detail = "https://rsj.sh.gov.cn/tshbx_17729/20260812/t0035_1443067.html"
    listing = "https://rsj.sh.gov.cn/tgwgfx_17726/index_2.html"
    with get_sessionmaker(engine)() as session:
        session.add_all([CrawledUrl(url=url, source_site="shanghai_rsj")
                         for url in (detail, listing)])
        session.commit()
    engine.dispose()
    spider = GovPolicyRootSpider()
    spider.crawler = SimpleNamespace(settings=Settings({"DATABASE_URL": database}), stats=Mock())
    spider._load_known_documents()
    response = HtmlResponse(url="https://rsj.sh.gov.cn/tgwgfx_17726/index.html")
    assert spider.process_request(Request(detail), response) is None
    assert spider.process_request(Request(listing), response) is not None
    assert spider.process_request(Request(detail.replace("1443067", "9999999")), response) is not None
    spider.crawler.stats.inc_value.assert_called_with("incremental/skipped_known_detail")

    # The post-download guard must still work, for races and disabled prefiltering.
    pipeline = DeduplicatePipeline(database)
    pipeline.open_spider(spider)
    with pytest.raises(DropItem):
        pipeline.process_item({"source_url": detail, "source_site": "shanghai_rsj"}, spider)
    pipeline.engine.dispose()

    spider.crawler.settings.set("INCREMENTAL_CRAWL_ENABLED", False)
    spider._load_known_documents()
    assert spider.process_request(Request(detail), response) is not None


def test_unavailable_database_falls_back_without_blocking_discovery(tmp_path):
    spider = GovPolicyRootSpider()
    spider.crawler = SimpleNamespace(settings=Settings({
        "DATABASE_URL": f"sqlite:///{tmp_path / 'missing' / 'crawl.db'}"
    }), stats=Mock())
    spider._load_known_documents()
    assert not spider._known_documents
    spider.crawler.stats.inc_value.assert_called_with("incremental/ledger_unavailable")
