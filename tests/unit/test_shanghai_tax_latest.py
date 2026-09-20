from scrapy.http import HtmlResponse
from scrapy.crawler import Crawler
from scrapy.settings import Settings
from scrapy.statscollectors import MemoryStatsCollector

from scripts.crawl_shanghai_tax import ROOT, ShanghaiTaxLatestSpider


def test_latest_list_follows_sibling_details_only():
    crawler = Crawler(ShanghaiTaxLatestSpider, Settings())
    crawler.stats = MemoryStatsCollector(crawler)
    spider = ShanghaiTaxLatestSpider.from_crawler(crawler)
    response = HtmlResponse(url=ROOT + "zxwj/", encoding="utf-8", body='''
      <a class="info" href="../zcfgk/zzs/202609/t1.html" title="最新通知">通知</a>
      <a href="index_1.html">下一页</a>
      <a class="info" href="https://example.org/other.html">外站</a>
    '''.encode())
    requests = list(spider.parse_latest(response))
    assert len(requests) == 1
    assert requests[0].url == ROOT + "zcfgk/zzs/202609/t1.html"
    assert requests[0].callback == spider.parse_document


def test_document_keeps_full_title_number_and_clean_body():
    spider = ShanghaiTaxLatestSpider()
    body = "政策正文，支持制造业发展。" * 30
    response = HtmlResponse(url=ROOT + "zcfgk/zzs/202609/t1.html", encoding="utf-8", body=f'''
      <html><body><div id="main"><h1>关于制造业的通知</h1>
      <p>发布时间：2026-09-10 15:12</p><div>文号：工信厅联财函〔2026〕418号</div>
      <div>发文日期：2026-08-20</div><script>function laiyuan(){{}}</script>
      <div class="TRS_Editor"><p>{body}</p></div></div></body></html>
    '''.encode())
    item, = spider.parse_document(response, "三部门关于制造业的通知")
    assert item['title'] == "三部门关于制造业的通知"
    assert item['doc_number'] == "工信厅联财函〔2026〕418号"
    assert str(item['pub_date']) == "2026-09-10"
    assert item['pub_datetime'] == "2026-09-10T15:12:00+08:00"
    assert item['content'] == body
