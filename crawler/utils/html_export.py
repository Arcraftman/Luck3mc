"""Save raw response HTML to disk (the "download as HTML" feature).

Output layout::

    <OUTPUT_DIR>/html/<spider>/<kind>/<safe_name>.html

where ``kind`` is ``list`` or ``detail``. Filenames are derived from the
URL so they stay unique and human-readable. The write is best-effort: a
failure (e.g. permission error) is swallowed so it can never abort a crawl.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from scrapy.http import Response

_MAX_NAME = 160


def _safe_name(url: str) -> str:
    """Filesystem-safe, unique name derived from a URL."""
    name = re.sub(r"^https?://", "", url)
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    if len(name) > _MAX_NAME:
        digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
        name = name[: _MAX_NAME - 12] + "_" + digest
    if not name.endswith(".html"):
        name += ".html"
    return name


def save_response_html(
    response: Response, output_dir, spider_name: str, kind: str
) -> Path | None:
    """Write the response body as an ``.html`` file.

    Returns the written path, or ``None`` if the write failed.
    """
    try:
        base = Path(str(output_dir)) if output_dir else Path("data")
        target = base / "html" / spider_name / kind
        target.mkdir(parents=True, exist_ok=True)
        path = target / _safe_name(response.url)
        # write_bytes preserves the exact payload (encoding already applied).
        path.write_bytes(response.body)
        return path
    except Exception:  # noqa: BLE001 - never let HTML export break a crawl
        return None
