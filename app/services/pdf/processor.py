"""
PDF Processor - Complete PDF processing pipeline
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pdf.downloader import PDFDownloader
from app.services.pdf.parsers import MultiPDFParser
from app.services.pdf.section_segmenter import SectionSegmenter
from app.services.pdf.quality_checker import QualityChecker
from app.services.pdf.schemas import (
    ProcessedPDF,
    ProcessingStatus,
    PDFProcessingResult,
)
from app.models.document import (
    ProcessedDocument,
    DocumentSection,
    ExtractedTable,
    ExtractedImage,
)
from app.models.paper import Paper

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Complete PDF processing pipeline"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.downloader = PDFDownloader()
        self.parser = MultiPDFParser()
        self.segmenter = SectionSegmenter()
        self.quality_checker = QualityChecker()

    async def process_paper(
        self,
        paper_id: UUID,
        arxiv_id: str,
        force_reprocess: bool = False,
    ) -> PDFProcessingResult:
        """
        Process a paper's PDF completely

        Args:
            paper_id: UUID of paper in database
            arxiv_id: arXiv ID for PDF download
            force_reprocess: Force reprocessing even if already done

        Returns:
            PDFProcessingResult
        """
        start_time = datetime.utcnow()
        logger.info(f"🚀 Processing PDF for paper: {paper_id} (arXiv: {arxiv_id})")

        try:
            # 1. Check if already processed
            if not force_reprocess:
                existing = await self._get_processed_document(paper_id)
                if existing and existing.status == "completed":
                    logger.info(f"✓ Paper already processed: {paper_id}")
                    duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    return PDFProcessingResult(
                        success=True,
                        paper_id=str(paper_id),
                        document_id=str(existing.id),
                        processing_time_ms=duration,
                        message="Already processed",
                        quality_score=existing.overall_quality_score,
                    )

            # 2. Download PDF
            pdf_path = await self.downloader.download_arxiv_pdf(arxiv_id)
            if not pdf_path:
                return PDFProcessingResult(
                    success=False,
                    paper_id=str(paper_id),
                    processing_time_ms=0,
                    message="PDF download failed",
                    error="Could not download PDF from arXiv",
                )

            # 3. Parse PDF
            extracted_text, tables, images, pdf_format = self.parser.parse(pdf_path)

            if not extracted_text:
                return PDFProcessingResult(
                    success=False,
                    paper_id=str(paper_id),
                    processing_time_ms=0,
                    message="PDF parsing failed",
                    error="Could not extract text from PDF",
                )

            # 4. Segment into sections
            sections = self.segmenter.segment(extracted_text.full_text)

            # 5. Evaluate quality
            quality_metrics = self.quality_checker.evaluate(
                extracted_text,
                sections,
                tables,
                [],  # References will be added later
            )

            # 6. Save to database
            document_id = await self._save_processed_document(
                paper_id=paper_id,
                extracted_text=extracted_text,
                sections=sections,
                tables=tables,
                images=images,
                pdf_format=pdf_format,
                quality_metrics=quality_metrics,
                start_time=start_time,
            )

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # 7. Log quality report
            report = self.quality_checker.get_quality_report(quality_metrics)
            logger.info(f"\n{report}")

            logger.info(
                f"✅ PDF processing completed in {duration}ms | "
                f"Quality: {quality_metrics.overall_quality_score:.3f}"
            )

            return PDFProcessingResult(
                success=True,
                paper_id=str(paper_id),
                document_id=str(document_id),
                processing_time_ms=duration,
                message="Processing completed successfully",
                quality_score=quality_metrics.overall_quality_score,
            )

        except Exception as e:
            logger.error(f"❌ PDF processing failed: {e}", exc_info=True)
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return PDFProcessingResult(
                success=False,
                paper_id=str(paper_id),
                processing_time_ms=duration,
                message="Processing failed",
                error=str(e),
            )

    async def _get_processed_document(self, paper_id: UUID) -> Optional[ProcessedDocument]:
        """Get existing processed document"""
        from sqlalchemy import select

        stmt = select(ProcessedDocument).where(ProcessedDocument.paper_id == paper_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _save_processed_document(
        self,
        paper_id: UUID,
        extracted_text,
        sections,
        tables,
        images,
        pdf_format,
        quality_metrics,
        start_time: datetime,
    ) -> UUID:
        """Save processed document to database"""
        from sqlalchemy import select

        # Check if document already exists
        stmt = select(ProcessedDocument).where(ProcessedDocument.paper_id == paper_id)
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()

        if doc:
            # Update existing
            doc.processing_started_at = start_time
            doc.processing_completed_at = datetime.utcnow()
            doc.processing_duration_ms = int(
                (doc.processing_completed_at - start_time).total_seconds() * 1000
            )
            doc.status = "completed"
        else:
            # Create new
            doc = ProcessedDocument(
                paper_id=paper_id,
                processing_started_at=start_time,
                processing_completed_at=datetime.utcnow(),
                processing_duration_ms=int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
                status="completed",
            )
            self.db.add(doc)

        # Update stats
        doc.page_count = extracted_text.page_count
        doc.word_count = extracted_text.word_count
        doc.table_count = len(tables)
        doc.image_count = len(images)
        doc.pdf_format = pdf_format.value

        # Update quality metrics
        doc.text_completeness_score = quality_metrics.text_completeness_score
        doc.section_coverage_score = quality_metrics.section_coverage_score
        doc.table_extraction_score = quality_metrics.table_extraction_score
        doc.reference_validity_score = quality_metrics.reference_validity_score
        doc.overall_quality_score = quality_metrics.overall_quality_score

        await self.db.commit()
        await self.db.refresh(doc)

        # Save sections
        await self._save_sections(doc.id, sections)

        # Save tables
        await self._save_tables(doc.id, tables)

        # Save images
        await self._save_images(doc.id, images)

        await self.db.commit()

        return doc.id

    async def _save_sections(self, document_id: UUID, sections):
        """Save document sections"""
        for section in sections:
            db_section = DocumentSection(
                document_id=document_id,
                section_type=section.section_type.value,
                section_title=section.section_title,
                content=section.content,
                word_count=section.word_count,
                char_count=len(section.content),
                section_order=section.section_order,
            )
            self.db.add(db_section)

    async def _save_tables(self, document_id: UUID, tables):
        """Save extracted tables"""
        for table in tables:
            db_table = ExtractedTable(
                document_id=document_id,
                table_index=table.table_index,
                page_number=table.page_number,
                data=table.data,
                headers=table.headers,
                row_count=table.row_count,
                column_count=table.column_count,
                caption=table.caption,
            )
            self.db.add(db_table)

    async def _save_images(self, document_id: UUID, images):
        """Save extracted images"""
        for image in images:
            db_image = ExtractedImage(
                document_id=document_id,
                image_index=image.image_index,
                page_number=image.page_number,
                image_type=image.image_type,
                format=image.format,
                width=image.width,
                height=image.height,
                size_bytes=image.size_bytes,
                storage_path=image.storage_path,
            )
            self.db.add(db_image)


# Example usage
if __name__ == "__main__":
    import asyncio
    from app.core.database import AsyncSessionLocal

    logging.basicConfig(level=logging.INFO)

    async def main():
        async with AsyncSessionLocal() as db:
            processor = PDFProcessor(db)

            # Example paper (replace with actual UUID and arXiv ID)
            from uuid import uuid4
            paper_id = uuid4()
            arxiv_id = "2311.12345"

            result = await processor.process_paper(paper_id, arxiv_id)

            print(f"\n{'='*60}")
            print(f"Processing Result:")
            print(f"  Success: {result.success}")
            print(f"  Time: {result.processing_time_ms}ms")
            print(f"  Quality: {result.quality_score:.3f}")
            print(f"  Message: {result.message}")
            if result.error:
                print(f"  Error: {result.error}")
            print(f"{'='*60}")

    asyncio.run(main())
