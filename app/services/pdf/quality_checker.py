"""
Quality Checker - PDF 처리 품질 평가
"""

import logging
from typing import List

from app.services.pdf.schemas import (
    ExtractedText,
    Section,
    TableData,
    Reference,
    QualityMetrics,
    SectionType,
)

logger = logging.getLogger(__name__)


class QualityChecker:
    """PDF 처리 품질 평가"""

    def evaluate(
        self,
        extracted_text: ExtractedText,
        sections: List[Section],
        tables: List[TableData],
        references: List[Reference],
    ) -> QualityMetrics:
        """
        Evaluate overall processing quality

        Args:
            extracted_text: Extracted text data
            sections: List of sections
            tables: List of tables
            references: List of references

        Returns:
            QualityMetrics
        """
        logger.info("📊 Evaluating PDF processing quality...")

        # 1. Text completeness score
        text_score = self._evaluate_text_completeness(extracted_text)

        # 2. Section coverage score
        section_score = self._evaluate_section_coverage(sections)

        # 3. Table extraction score
        table_score = self._evaluate_table_extraction(tables)

        # 4. Reference validity score
        reference_score = self._evaluate_references(references)

        # Overall score (weighted average)
        overall_score = (
            text_score * 0.4 +
            section_score * 0.3 +
            table_score * 0.15 +
            reference_score * 0.15
        )

        metrics = QualityMetrics(
            text_completeness_score=text_score,
            section_coverage_score=section_score,
            table_extraction_score=table_score,
            reference_validity_score=reference_score,
            overall_quality_score=overall_score,
        )

        logger.info(f"✅ Quality Score: {overall_score:.3f}")
        return metrics

    def _evaluate_text_completeness(self, extracted_text: ExtractedText) -> float:
        """
        Evaluate text extraction completeness

        Criteria:
        - Word count (expect 3000+ for typical papers)
        - Character count
        - Page count

        Args:
            extracted_text: Extracted text data

        Returns:
            Score between 0 and 1
        """
        score = 0.0

        # Word count check (typical paper: 3000-8000 words)
        if extracted_text.word_count >= 3000:
            score += 0.5
        elif extracted_text.word_count >= 1500:
            score += 0.3
        elif extracted_text.word_count >= 500:
            score += 0.1

        # Page count check (typical paper: 6-15 pages)
        if 6 <= extracted_text.page_count <= 20:
            score += 0.3
        elif 3 <= extracted_text.page_count <= 30:
            score += 0.2
        elif extracted_text.page_count > 0:
            score += 0.1

        # Words per page ratio check (expect 200-500 words/page)
        if extracted_text.page_count > 0:
            words_per_page = extracted_text.word_count / extracted_text.page_count
            if 200 <= words_per_page <= 800:
                score += 0.2
            elif 100 <= words_per_page <= 1000:
                score += 0.1

        return min(score, 1.0)

    def _evaluate_section_coverage(self, sections: List[Section]) -> float:
        """
        Evaluate section coverage

        Criteria:
        - Presence of key sections (abstract, intro, method, conclusion)
        - Number of sections found

        Args:
            sections: List of sections

        Returns:
            Score between 0 and 1
        """
        if not sections:
            return 0.0

        score = 0.0
        section_types = {s.section_type for s in sections}

        # Check for key sections
        key_sections = {
            SectionType.ABSTRACT: 0.25,
            SectionType.INTRODUCTION: 0.20,
            SectionType.METHODOLOGY: 0.20,
            SectionType.CONCLUSION: 0.15,
            SectionType.REFERENCES: 0.10,
        }

        for sec_type, weight in key_sections.items():
            if sec_type in section_types:
                score += weight

        # Bonus for having multiple sections
        if len(sections) >= 5:
            score += 0.1

        return min(score, 1.0)

    def _evaluate_table_extraction(self, tables: List[TableData]) -> float:
        """
        Evaluate table extraction quality

        Criteria:
        - Tables extracted
        - Valid structure (rows/columns)

        Args:
            tables: List of tables

        Returns:
            Score between 0 and 1
        """
        if not tables:
            return 0.5  # Neutral score (not all papers have tables)

        score = 0.5  # Base score for finding tables

        # Check table validity
        valid_tables = 0
        for table in tables:
            if table.row_count >= 2 and table.column_count >= 2:
                valid_tables += 1

        if valid_tables > 0:
            validity_ratio = valid_tables / len(tables)
            score += 0.5 * validity_ratio

        return min(score, 1.0)

    def _evaluate_references(self, references: List[Reference]) -> float:
        """
        Evaluate reference extraction quality

        Criteria:
        - Number of references (expect 10-50)
        - Parsed references with metadata

        Args:
            references: List of references

        Returns:
            Score between 0 and 1
        """
        if not references:
            return 0.3  # Low score but not zero (some papers might not have refs extracted)

        score = 0.0

        # Number of references
        ref_count = len(references)
        if 10 <= ref_count <= 100:
            score += 0.5
        elif 5 <= ref_count <= 150:
            score += 0.3
        elif ref_count > 0:
            score += 0.1

        # Check for parsed metadata
        parsed_refs = sum(
            1 for ref in references
            if ref.title or ref.year or ref.doi
        )

        if parsed_refs > 0:
            parse_ratio = parsed_refs / len(references)
            score += 0.5 * parse_ratio

        return min(score, 1.0)

    def check_minimum_quality(self, metrics: QualityMetrics, threshold: float = 0.5) -> bool:
        """
        Check if processing meets minimum quality threshold

        Args:
            metrics: Quality metrics
            threshold: Minimum acceptable score

        Returns:
            True if meets threshold, False otherwise
        """
        meets_threshold = metrics.overall_quality_score >= threshold

        if not meets_threshold:
            logger.warning(
                f"⚠️ Quality below threshold: {metrics.overall_quality_score:.3f} < {threshold}"
            )

        return meets_threshold

    def get_quality_report(self, metrics: QualityMetrics) -> str:
        """
        Generate human-readable quality report

        Args:
            metrics: Quality metrics

        Returns:
            Quality report string
        """
        report = f"""
Quality Assessment Report
========================
Text Completeness:    {metrics.text_completeness_score:.3f} {'✅' if metrics.text_completeness_score >= 0.7 else '⚠️'}
Section Coverage:     {metrics.section_coverage_score:.3f} {'✅' if metrics.section_coverage_score >= 0.6 else '⚠️'}
Table Extraction:     {metrics.table_extraction_score:.3f} {'✅' if metrics.table_extraction_score >= 0.5 else '⚠️'}
Reference Validity:   {metrics.reference_validity_score:.3f} {'✅' if metrics.reference_validity_score >= 0.5 else '⚠️'}
------------------------
Overall Quality:      {metrics.overall_quality_score:.3f} {'✅' if metrics.overall_quality_score >= 0.7 else '⚠️' if metrics.overall_quality_score >= 0.5 else '❌'}
        """.strip()

        return report


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Sample data
    from app.services.pdf.schemas import ExtractedText, Section, SectionType

    text = ExtractedText(
        full_text="Sample text" * 500,
        page_count=10,
        word_count=5000,
        char_count=30000,
    )

    sections = [
        Section(
            section_type=SectionType.ABSTRACT,
            content="Abstract content",
            word_count=150,
            section_order=0,
        ),
        Section(
            section_type=SectionType.INTRODUCTION,
            content="Intro content",
            word_count=800,
            section_order=1,
        ),
        Section(
            section_type=SectionType.METHODOLOGY,
            content="Method content",
            word_count=1500,
            section_order=2,
        ),
    ]

    tables = []
    references = []

    checker = QualityChecker()
    metrics = checker.evaluate(text, sections, tables, references)

    print(checker.get_quality_report(metrics))
