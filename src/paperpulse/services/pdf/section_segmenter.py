"""Section segmentation for academic papers."""

import re
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()


class SectionSegmenter:
    """Segment academic paper into logical sections."""

    # Common section headers in academic papers
    SECTION_PATTERNS = [
        # Abstract
        (r"^abstract\s*$", "abstract"),
        # Introduction
        (r"^1\.?\s+introduction\s*$", "introduction"),
        (r"^introduction\s*$", "introduction"),
        # Related Work
        (r"^2\.?\s+related\s+work\s*$", "related_work"),
        (r"^related\s+work\s*$", "related_work"),
        (r"^background\s*$", "related_work"),
        # Methodology / Methods
        (r"^3\.?\s+method(ology)?\s*$", "methodology"),
        (r"^method(ology|s)?\s*$", "methodology"),
        (r"^approach\s*$", "methodology"),
        # Experiments / Results
        (r"^4\.?\s+experiments?\s*$", "experiments"),
        (r"^experiments?\s*$", "experiments"),
        (r"^results?\s*$", "results"),
        (r"^evaluation\s*$", "results"),
        # Discussion
        (r"^5\.?\s+discussion\s*$", "discussion"),
        (r"^discussion\s*$", "discussion"),
        # Conclusion
        (r"^6\.?\s+conclusion\s*$", "conclusion"),
        (r"^conclusion(s)?\s*$", "conclusion"),
        # References
        (r"^references\s*$", "references"),
        (r"^bibliography\s*$", "references"),
        # Appendix
        (r"^appendi(x|ces)\s*$", "appendix"),
        (r"^supplementary\s+materials?\s*$", "appendix"),
    ]

    def segment(self, text: str) -> Dict[str, str]:
        """
        Segment paper text into sections.

        Args:
            text: Full paper text

        Returns:
            Dictionary mapping section names to section content
        """
        if not text:
            return {}

        sections = {}

        # Split into lines
        lines = text.split("\n")

        # Find section boundaries
        section_boundaries = self._find_section_boundaries(lines)

        # Extract sections
        for i, (start_idx, section_name) in enumerate(section_boundaries):
            # Find end of section (start of next section or end of document)
            if i < len(section_boundaries) - 1:
                end_idx = section_boundaries[i + 1][0]
            else:
                end_idx = len(lines)

            # Extract section content
            section_lines = lines[start_idx + 1 : end_idx]
            section_text = "\n".join(section_lines).strip()

            # Only add non-empty sections
            if section_text:
                sections[section_name] = section_text

        logger.info(
            "segmentation_completed",
            sections_found=list(sections.keys()),
            total_sections=len(sections),
        )

        # If no sections found, try basic extraction
        if not sections:
            sections = self._basic_segmentation(text)

        return sections

    def _find_section_boundaries(self, lines: List[str]) -> List[tuple]:
        """
        Find section boundaries in text.

        Args:
            lines: List of text lines

        Returns:
            List of (line_index, section_name) tuples
        """
        boundaries = []

        for i, line in enumerate(lines):
            # Clean line for matching
            clean_line = line.strip().lower()

            # Skip empty lines
            if not clean_line:
                continue

            # Try to match section patterns
            for pattern, section_name in self.SECTION_PATTERNS:
                if re.match(pattern, clean_line, re.IGNORECASE):
                    boundaries.append((i, section_name))
                    break

        return boundaries

    def _basic_segmentation(self, text: str) -> Dict[str, str]:
        """
        Basic segmentation when structured sections are not found.

        Tries to extract at least abstract and main body.

        Args:
            text: Full paper text

        Returns:
            Basic sections dictionary
        """
        sections = {}

        # Try to extract abstract
        abstract_match = re.search(
            r"abstract[\s\n]+(.*?)(?=\n1\.|introduction|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if abstract_match:
            sections["abstract"] = abstract_match.group(1).strip()

            # Everything after abstract is main body
            remaining_text = text[abstract_match.end() :]
            sections["body"] = remaining_text.strip()
        else:
            # No clear structure, put everything in body
            sections["body"] = text

        logger.info(
            "basic_segmentation_applied",
            sections_found=list(sections.keys()),
        )

        return sections

    def extract_key_phrases(self, text: str, max_phrases: int = 20) -> List[str]:
        """
        Extract key phrases from text.

        Simple extraction based on capitalized phrases and technical terms.

        Args:
            text: Text to extract phrases from
            max_phrases: Maximum number of phrases to return

        Returns:
            List of key phrases
        """
        phrases = []

        # Extract capitalized phrases (likely proper nouns, method names)
        capitalized_pattern = r"\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b"
        matches = re.findall(capitalized_pattern, text)

        # Filter out common words and very short phrases
        common_words = {
            "The",
            "We",
            "Our",
            "This",
            "These",
            "In",
            "For",
            "However",
            "Moreover",
            "Figure",
            "Table",
        }

        for phrase in matches:
            if phrase not in common_words and len(phrase) > 3:
                phrases.append(phrase)

        # Get unique phrases and limit count
        unique_phrases = list(set(phrases))
        return unique_phrases[:max_phrases]

    def get_section_statistics(self, sections: Dict[str, str]) -> Dict:
        """
        Calculate statistics for each section.

        Args:
            sections: Dictionary of sections

        Returns:
            Statistics dictionary
        """
        stats = {}

        for section_name, content in sections.items():
            words = content.split()
            stats[section_name] = {
                "word_count": len(words),
                "char_count": len(content),
                "line_count": len(content.split("\n")),
            }

        return stats
