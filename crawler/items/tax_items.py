"""Tax-domain item schemas.

Items use ``scrapy.Item`` plus ``ItemLoader`` input/output processors so that
cleaning happens once, at the boundary, instead of being spread across every
spider. Use ``crawler.utils.data_validators`` processors for reuse.
"""

import scrapy
from itemloaders.processors import Join, MapCompose, TakeFirst

from crawler.utils.data_validators import (
    clean_text,
    normalize_url,
    parse_pub_date,
    to_int_or_none,
)


class TaxPolicyItem(scrapy.Item):
    """Tax laws, regulations and policy documents (政策法规)."""

    title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    doc_number = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    pub_date = scrapy.Field(
        input_processor=MapCompose(parse_pub_date),
        output_processor=TakeFirst(),
    )
    effective_date = scrapy.Field(
        input_processor=MapCompose(parse_pub_date),
        output_processor=TakeFirst(),
    )
    category = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    issuing_authority = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    content = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join("\n"),
    )
    source_url = scrapy.Field(
        input_processor=MapCompose(normalize_url),
        output_processor=TakeFirst(),
    )
    source_site = scrapy.Field(output_processor=TakeFirst())


class TaxAnnouncementItem(scrapy.Item):
    """Public announcements / notices (通知公告)."""

    title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    pub_date = scrapy.Field(
        input_processor=MapCompose(parse_pub_date),
        output_processor=TakeFirst(),
    )
    category = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    summary = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    content = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join("\n"),
    )
    source_url = scrapy.Field(
        input_processor=MapCompose(normalize_url),
        output_processor=TakeFirst(),
    )
    source_site = scrapy.Field(output_processor=TakeFirst())


class TaxNewsItem(scrapy.Item):
    """News / dynamic updates (新闻动态)."""

    title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    pub_date = scrapy.Field(
        input_processor=MapCompose(parse_pub_date),
        output_processor=TakeFirst(),
    )
    author = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    content = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join("\n"),
    )
    source_url = scrapy.Field(
        input_processor=MapCompose(normalize_url),
        output_processor=TakeFirst(),
    )
    source_site = scrapy.Field(output_processor=TakeFirst())


class TaxServiceGuideItem(scrapy.Item):
    """Tax service guides / how-tos (办税指南)."""

    title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    category = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    business_type = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst(),
    )
    processing_time_limit = scrapy.Field(
        input_processor=MapCompose(to_int_or_none),
        output_processor=TakeFirst(),
    )
    content = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join("\n"),
    )
    source_url = scrapy.Field(
        input_processor=MapCompose(normalize_url),
        output_processor=TakeFirst(),
    )
    source_site = scrapy.Field(output_processor=TakeFirst())
