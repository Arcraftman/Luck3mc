"""Date parsing helpers (thin wrapper kept for import convenience).

The heavy lifting lives in :mod:`crawler.utils.data_validators`.
"""

from crawler.utils.data_validators import parse_pub_date

__all__ = ["parse_pub_date"]
