"""Main PDF processing service."""

from typing import Dict, Optional
from pathlib import Path
import httpx
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
import structlog

from paperpulse.models.paper import Paper, ProcessedDocument
from paperpulse.services.pdf.pdf_parser import HybridPDFParser
from paperpulse.services.pdf.section_segmenter import SectionSegmenter
from paperpulse.config.settings import settings

logger = structlog.get_logger()


class PDFProcessingService:
    """Main service for processing paper PDFs."""

    def __init__(self, db: Session):
        self.db = db
        self.parser = HybridPDFParser()
        self.segmenter = SectionSegmenter()
        self.download_dir = Path("./data/pdfs")
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def process_paper(self, paper_id: str) -> Optional[ProcessedDocument]:
        """
        Process PDF for a paper.

        Args:
            paper_id: Paper UUID

        Returns:
            ProcessedDocument or None if processing failed
        """
        # Get paper from database
        paper = self.db.query(Paper).filter(Paper.id == paper_id).first()

        if not paper:
            logger.error("paper_not_found", paper_id=paper_id)
            return None

        if not paper.pdf_url:
            logger.error("no_pdf_url", paper_id=paper_id)
            return None

        # Check if already processed
        existing_doc = (
            self.db.query(ProcessedDocument)
            .filter(ProcessedDocument.paper_id == paper_id)
            .first()
        )

        if existing_doc and existing_doc.full_text:
            logger.info("paper_already_processed", paper_id=paper_id)
            return existing_doc

        logger.info(
            "processing_started",
            paper_id=paper_id,
            pdf_url=paper.pdf_url,
        )

        start_time = datetime.utcnow()

        try:
            # Update paper status
            paper.processing_status = "processing"
            self.db.commit()

            # Download PDF
            pdf_path = await self._download_pdf(paper.pdf_url, paper.arxiv_id or str(paper.id))

            # Extract content
            extracted = self.parser.extract_all(str(pdf_path))

            # Segment text into sections
            sections = self.segmenter.segment(extracted["text"])

            # Extract key phrases
            key_phrases = []
            if "abstract" in sections:
                key_phrases = self.segmenter.extract_key_phrases(sections["abstract"])

            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(extracted, sections)

            # Calculate PDF hash for deduplication
            pdf_hash = self._calculate_file_hash(pdf_path)

            # Create or update ProcessedDocument
            if existing_doc:
                doc = existing_doc
            else:
                doc = ProcessedDocument(paper_id=paper_id)
                self.db.add(doc)

            # Update document
            doc.full_text = extracted["text"]
            doc.sections = sections
            doc.tables = extracted["tables"]
            doc.figures = [
                {"page": img["page"], "index": img["index"]}
                for img in extracted["images"]
            ]
            doc.key_phrases = key_phrases
            doc.pdf_hash = pdf_hash
            doc.parser_used = "hybrid"
            doc.word_count = len(extracted["text"].split())
            doc.page_count = extracted["page_count"]
            doc.processed_at = datetime.utcnow()

            # Update paper status
            paper.processing_status = "completed"

            self.db.commit()

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                "processing_completed",
                paper_id=paper_id,
                duration_seconds=duration,
                word_count=doc.word_count,
                page_count=doc.page_count,
                sections=len(sections),
                tables=len(extracted["tables"]),
                images=len(extracted["images"]),
            )

            return doc

        except Exception as e:
            logger.error(
                "processing_failed",
                paper_id=paper_id,
                error=str(e),
                exc_info=True,
            )

            # Update paper status
            paper.processing_status = "failed"
            paper.error_message = str(e)
            self.db.commit()

            return None

    async def _download_pdf(self, url: str, filename: str) -> Path:
        """
        Download PDF from URL.

        Args:
            url: PDF URL
            filename: Filename to save as

        Returns:
            Path to downloaded PDF
        """
        # Clean filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        pdf_path = self.download_dir / f"{safe_filename}.pdf"

        # Check if already downloaded
        if pdf_path.exists():
            logger.info("pdf_already_downloaded", path=str(pdf_path))
            return pdf_path

        logger.info("downloading_pdf", url=url, path=str(pdf_path))

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                # Save PDF
                pdf_path.write_bytes(response.content)

                logger.info(
                    "pdf_downloaded",
                    path=str(pdf_path),
                    size_bytes=len(response.content),
                )

        except Exception as e:
            logger.error(
                "pdf_download_failed",
                url=url,
                error=str(e),
                exc_info=True,
            )
            raise

        return pdf_path

    def _calculate_quality_metrics(
        self, extracted: Dict, sections: Dict[str, str]
    ) -> Dict:
        """
        Calculate quality metrics for extracted content.

        Args:
            extracted: Extracted content dictionary
            sections: Segmented sections

        Returns:
            Quality metrics dictionary
        """
        metrics = {
            "text_completeness": 0.0,
            "section_coverage": 0.0,
            "table_extraction": 0.0,
        }

        # Text completeness (based on word count relative to page count)
        word_count = len(extracted["text"].split())
        page_count = extracted["page_count"]

        if page_count > 0:
            # Assume ~300 words per page as reasonable
            expected_words = page_count * 300
            metrics["text_completeness"] = min(1.0, word_count / expected_words)

        # Section coverage (how many standard sections found)
        standard_sections = {
            "abstract",
            "introduction",
            "methodology",
            "results",
            "conclusion",
            "references",
        }
        found_sections = set(sections.keys())
        common_sections = standard_sections & found_sections

        if standard_sections:
            metrics["section_coverage"] = len(common_sections) / len(
                standard_sections
            )

        # Table extraction quality (basic: just count)
        metrics["table_extraction"] = 1.0 if extracted["tables"] else 0.5

        return metrics

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def get_processing_status(self, paper_id: str) -> Optional[Dict]:
        """
        Get processing status for a paper.

        Args:
            paper_id: Paper UUID

        Returns:
            Status dictionary or None
        """
        paper = self.db.query(Paper).filter(Paper.id == paper_id).first()

        if not paper:
            return None

        doc = (
            self.db.query(ProcessedDocument)
            .filter(ProcessedDocument.paper_id == paper_id)
            .first()
        )

        return {
            "paper_id": str(paper.id),
            "status": paper.processing_status,
            "error_message": paper.error_message,
            "processed": doc is not None,
            "word_count": doc.word_count if doc else None,
            "page_count": doc.page_count if doc else None,
            "processed_at": doc.processed_at if doc else None,
        }

    async def reprocess_paper(self, paper_id: str) -> Optional[ProcessedDocument]:
        """
        Reprocess a paper (delete existing and process again).

        Args:
            paper_id: Paper UUID

        Returns:
            ProcessedDocument or None
        """
        # Delete existing processed document
        existing = (
            self.db.query(ProcessedDocument)
            .filter(ProcessedDocument.paper_id == paper_id)
            .first()
        )

        if existing:
            self.db.delete(existing)
            self.db.commit()

        # Process again
        return await self.process_paper(paper_id)
