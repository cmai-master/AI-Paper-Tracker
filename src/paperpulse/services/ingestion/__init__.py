"""Data ingestion services."""

from paperpulse.services.ingestion.arxiv_collector import ArxivCollector
from paperpulse.services.ingestion.semantic_scholar_collector import SemanticScholarCollector
from paperpulse.services.ingestion.normalizer import PaperNormalizer, PaperMerger
from paperpulse.services.ingestion.deduplicator import PaperDeduplicator
from paperpulse.services.ingestion.ingestion_service import IngestionService

__all__ = [
    "ArxivCollector",
    "SemanticScholarCollector",
    "PaperNormalizer",
    "PaperMerger",
    "PaperDeduplicator",
    "IngestionService",
]
