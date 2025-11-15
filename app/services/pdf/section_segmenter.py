"""
Section Segmentation - 논문을 섹션별로 분할
"""

import re
import logging
from typing import List, Dict, Optional, Tuple

from app.services.pdf.schemas import Section, SectionType

logger = logging.getLogger(__name__)


class SectionSegmenter:
    """논문 섹션 자동 분할기"""

    # Section headers patterns (case-insensitive)
    SECTION_PATTERNS = {
        SectionType.ABSTRACT: [
            r"^abstract\b",
            r"^summary\b",
        ],
        SectionType.INTRODUCTION: [
            r"^1\.?\s*introduction\b",
            r"^introduction\b",
            r"^1\.?\s*background\b",
        ],
        SectionType.RELATED_WORK: [
            r"^2\.?\s*related\s+work\b",
            r"^related\s+work\b",
            r"^background\b",
            r"^literature\s+review\b",
            r"^prior\s+work\b",
        ],
        SectionType.METHODOLOGY: [
            r"^3\.?\s*method",
            r"^method",
            r"^approach\b",
            r"^proposed\s+(method|approach)",
            r"^model\b",
            r"^architecture\b",
        ],
        SectionType.EXPERIMENTS: [
            r"^4\.?\s*experiment",
            r"^experiment",
            r"^evaluation\b",
            r"^empirical\s+(study|analysis)",
        ],
        SectionType.RESULTS: [
            r"^5\.?\s*result",
            r"^result",
            r"^findings\b",
        ],
        SectionType.DISCUSSION: [
            r"^6\.?\s*discussion\b",
            r"^discussion\b",
            r"^analysis\b",
        ],
        SectionType.CONCLUSION: [
            r"^7\.?\s*conclusion",
            r"^conclusion",
            r"^summary\b",
            r"^future\s+work\b",
        ],
        SectionType.REFERENCES: [
            r"^references\b",
            r"^bibliography\b",
        ],
        SectionType.APPENDIX: [
            r"^appendix\b",
            r"^supplementary",
        ],
        SectionType.ACKNOWLEDGMENTS: [
            r"^acknowledgments?\b",
            r"^acknowledgements?\b",
        ],
    }

    def segment(self, full_text: str) -> List[Section]:
        """
        Segment text into sections

        Args:
            full_text: Full paper text

        Returns:
            List of Section objects
        """
        logger.info("🔪 Segmenting document into sections...")

        # Split into lines
        lines = full_text.split("\n")

        # Find section boundaries
        section_boundaries = self._find_section_boundaries(lines)

        # Extract sections
        sections = []
        for i, (start_idx, section_type, title) in enumerate(section_boundaries):
            # Find end of this section (start of next section or end of document)
            if i + 1 < len(section_boundaries):
                end_idx = section_boundaries[i + 1][0]
            else:
                end_idx = len(lines)

            # Extract content
            content_lines = lines[start_idx + 1 : end_idx]  # Skip the header line
            content = "\n".join(content_lines).strip()

            if content:  # Only add non-empty sections
                section = Section(
                    section_type=section_type,
                    section_title=title,
                    content=content,
                    word_count=len(content.split()),
                    section_order=i,
                )
                sections.append(section)

        logger.info(f"✅ Found {len(sections)} sections")
        return sections

    def _find_section_boundaries(self, lines: List[str]) -> List[Tuple[int, SectionType, str]]:
        """
        Find section boundaries in text

        Args:
            lines: List of text lines

        Returns:
            List of (line_index, section_type, title) tuples
        """
        boundaries = []

        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Check if this line matches any section pattern
            section_type = self._match_section_type(line_stripped)
            if section_type:
                boundaries.append((idx, section_type, line_stripped))

        return boundaries

    def _match_section_type(self, line: str) -> Optional[SectionType]:
        """
        Match a line to a section type

        Args:
            line: Text line to match

        Returns:
            SectionType or None if no match
        """
        line_lower = line.lower()

        for section_type, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    return section_type

        return None

    def extract_abstract(self, full_text: str) -> Optional[str]:
        """
        Extract just the abstract section

        Args:
            full_text: Full paper text

        Returns:
            Abstract text or None
        """
        sections = self.segment(full_text)
        for section in sections:
            if section.section_type == SectionType.ABSTRACT:
                return section.content
        return None

    def extract_introduction(self, full_text: str) -> Optional[str]:
        """
        Extract just the introduction section

        Args:
            full_text: Full paper text

        Returns:
            Introduction text or None
        """
        sections = self.segment(full_text)
        for section in sections:
            if section.section_type == SectionType.INTRODUCTION:
                return section.content
        return None

    def get_section_coverage(self, sections: List[Section]) -> Dict[str, bool]:
        """
        Check which standard sections are present

        Args:
            sections: List of sections

        Returns:
            Dictionary of section_type -> present
        """
        present_types = {s.section_type for s in sections}

        coverage = {
            "abstract": SectionType.ABSTRACT in present_types,
            "introduction": SectionType.INTRODUCTION in present_types,
            "methodology": SectionType.METHODOLOGY in present_types,
            "experiments": SectionType.EXPERIMENTS in present_types,
            "conclusion": SectionType.CONCLUSION in present_types,
            "references": SectionType.REFERENCES in present_types,
        }

        return coverage

    def compute_coverage_score(self, sections: List[Section]) -> float:
        """
        Compute section coverage score (0-1)

        Args:
            sections: List of sections

        Returns:
            Coverage score
        """
        coverage = self.get_section_coverage(sections)

        # Weight different sections
        weights = {
            "abstract": 0.2,
            "introduction": 0.2,
            "methodology": 0.2,
            "experiments": 0.15,
            "conclusion": 0.15,
            "references": 0.1,
        }

        score = sum(weights[key] for key, present in coverage.items() if present)
        return score


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Sample paper text
    sample_text = """
    Abstract
    This paper presents a novel approach to deep learning.

    1. Introduction
    Deep learning has revolutionized many fields...

    2. Related Work
    Previous work in this area includes...

    3. Methodology
    Our proposed method consists of three main components...

    4. Experiments
    We evaluated our approach on several benchmarks...

    5. Results
    Our method achieves state-of-the-art performance...

    6. Conclusion
    In this work, we have demonstrated...

    References
    [1] Author et al. (2020)...
    """

    segmenter = SectionSegmenter()
    sections = segmenter.segment(sample_text)

    print(f"\n📋 Segmentation Results:")
    print(f"Found {len(sections)} sections:\n")

    for section in sections:
        print(f"{section.section_type.value:15} | {section.word_count:4} words | {section.section_title}")

    # Coverage score
    coverage_score = segmenter.compute_coverage_score(sections)
    print(f"\n📊 Coverage Score: {coverage_score:.2f}")
