"""Validate items before they reach storage.

Drops items missing required fields and coerces types. This keeps bad records
out of the data lake and gives spiders a single, consistent contract.
"""

from itemadapter import ItemAdapter

from crawler.utils.log_config import get_logger

# Minimum fields an item must have to be worth storing.
REQUIRED_FIELDS = {
    "title": True,
    "source_url": True,
    "pub_date": False,  # warn but don't drop if missing
}


class ValidationPipeline:
    """Enforce required fields and log (not raise) on soft failures."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.dropped = 0

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        missing = [f for f in REQUIRED_FIELDS if REQUIRED_FIELDS[f] and not adapter.get(f)]
        if missing:
            self.dropped += 1
            spider.logger.warning(
                "Dropping %s item (missing required: %s)",
                item.__class__.__name__,
                ", ".join(missing),
            )
            return None  # signal drop

        # Soft warning for recommended-but-optional fields.
        for f, required in REQUIRED_FIELDS.items():
            if not required and not adapter.get(f):
                spider.logger.debug(
                    "%s item missing optional field '%s'",
                    item.__class__.__name__,
                    f,
                )
        return item

    def close_spider(self, spider):
        if self.dropped:
            self.logger.info("ValidationPipeline dropped %d invalid items.", self.dropped)
