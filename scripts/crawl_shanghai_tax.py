"""Fetch the latest Shanghai tax documents with the project's Scrapy parser.

Run from the project root: .luck3mc/bin/python scripts/crawl_shanghai_tax.py
Only the first latest-files page is visited; the strict publication window applies.
No notifications or database writes.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scrapy import Request
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from crawler.spiders.policy_root_base import PolicyRootBaseSpider
from crawler.utils.compliance import is_compliance_blocked
from scrapy.exceptions import CloseSpider

ROOT = "https://shanghai.chinatax.gov.cn/zcfw/"


class ShanghaiTaxLatestSpider(PolicyRootBaseSpider):
    name = "shanghai_tax_latest"
    category = "caishui"

    def __init__(self, **kwargs):
        super().__init__(roots=ROOT, **kwargs)

    async def start(self):
        yield Request(ROOT + "zxwj/", callback=self.parse_latest)

    def parse_latest(self, response):
        if is_compliance_blocked(response.text):
            raise CloseSpider("waf_blocked_compliance")
        links = response.css("a.info[href]")
        self.crawler.stats.set_value("latest/list_entries", len(links))
        for link in links:
            url = response.urljoin(link.attrib["href"])
            if url.startswith(ROOT + "zcfgk/") and url.endswith(".html"):
                yield Request(url, callback=self.parse_document,
                              cb_kwargs={"list_title": link.attrib.get("title", "")})

    def parse_document(self, response, list_title):
        for item in self.parse_page(response):
            if list_title:
                item["title"] = list_title.strip()
            # This site labels the full document number separately from body text.
            for text in response.xpath("//div/text()").getall():
                if text.strip().startswith("文号："):
                    item["doc_number"] = text.strip().removeprefix("文号：").strip()
                    break
            yield item


def main():
    settings = get_project_settings()
    settings.setdict({
        "ITEM_PIPELINES": {
            "crawler.pipelines.validation.ValidationPipeline": 100,
            "crawler.pipelines.date_filter.DateFilterPipeline": 150,
        },
        "NOTIFY_ENABLED": False,
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "logs/shanghai_tax_latest.log",
        "CLOSESPIDER_TIMEOUT": 180,
        "FEEDS": {"data/shanghai_tax_latest.jsonl": {
            "format": "jsonlines", "encoding": "utf-8", "overwrite": True,
        }},
    }, priority="cmdline")
    process = CrawlerProcess(settings)
    crawler = process.create_crawler(ShanghaiTaxLatestSpider)
    process.crawl(crawler)
    process.start()
    stats = crawler.stats.get_stats()
    count = stats.get("item_scraped_count", 0)
    expected = stats.get("latest/list_entries", 0)
    dropped = sum(value for key, value in stats.items()
                  if key.startswith("date_filter/dropped/"))
    print(f"Kept {count}, time-filtered {dropped}, listed {expected}; "
          f"reason={stats.get('finish_reason')}")
    if (not expected or count + dropped != expected
            or stats.get("finish_reason") != "finished"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
