"""Use a real Scrapy pipeline/feed to verify drops never reach output."""
import json
from pathlib import Path
import subprocess
import sys


def test_only_matching_timestamps_reach_feed(tmp_path):
    output = tmp_path / "window.jsonl"
    code = '''
import sys
from scrapy import Spider
from scrapy.crawler import CrawlerProcess
class Probe(Spider):
    name = "window_probe"
    async def start(self):
        for item in [{"pub_datetime": "2025-12-31 23:59:59"},
                     {"pub_datetime": "2026-01-01 00:00:00"},
                     {"pub_datetime": "2026-05-01 08:00:00"},
                     {"pub_datetime": "2026-09-17 12:05:00"},
                     {"pub_datetime": "2026-09-17 12:05:01"},
                     {"pub_date": "2026-09-17"},
                     {"pub_date": "2026-09-18"}]:
            yield item
process = CrawlerProcess({
    "LOG_ENABLED": False,
    "CRAWL_RUN_AT": "2026-09-17 12:05:00",
    "ITEM_PIPELINES": {"crawler.pipelines.date_filter.DateFilterPipeline": 150},
    "FEEDS": {sys.argv[1]: {"format": "jsonlines", "overwrite": True}},
})
process.crawl(Probe)
process.start()
'''
    subprocess.run([sys.executable, "-c", code, str(output)],
                   cwd=Path(__file__).resolve().parents[2], check=True,
                   capture_output=True, text=True, timeout=30)
    items = [json.loads(line) for line in output.read_text().splitlines()]
    assert items == [
        {"pub_datetime": "2026-01-01 00:00:00"},
        {"pub_datetime": "2026-05-01 08:00:00"},
        {"pub_datetime": "2026-09-17 12:05:00"},
        {"pub_date": "2026-09-17"},
    ]
