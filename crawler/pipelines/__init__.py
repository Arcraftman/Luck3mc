"""Item pipelines.

Order (set in settings) matters: validate -> deduplicate -> store.
Each pipeline is independently importable and unit-testable.
"""

from .deduplication import DeduplicatePipeline
from .storage import JsonLinesExportPipeline
from .validation import ValidationPipeline

__all__ = [
    "ValidationPipeline",
    "DeduplicatePipeline",
    "JsonLinesExportPipeline",
]
