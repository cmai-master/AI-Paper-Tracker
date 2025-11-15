"""
Text Chunker - Split documents into chunks for embedding
"""

import logging
import re
from typing import List, Optional
from dataclasses import dataclass

from app.services.embedding.schemas import TextChunk, ChunkingStrategy

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Text chunking with multiple strategies

    Strategies:
    - fixed: Fixed-size chunks with overlap
    - semantic: Sentence-based semantic chunks
    - sliding: Sliding window with stride
    """

    def __init__(self, strategy: ChunkingStrategy):
        """
        Initialize chunker

        Args:
            strategy: Chunking strategy configuration
        """
        self.strategy = strategy
        logger.info(f"🔪 Initializing TextChunker: {strategy.strategy}")

    def chunk_text(
        self,
        text: str,
        section_type: Optional[str] = None,
        section_title: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> List[TextChunk]:
        """
        Chunk text according to strategy

        Args:
            text: Input text to chunk
            section_type: Section type for metadata
            section_title: Section title for metadata
            page_number: Page number for metadata

        Returns:
            List of TextChunk objects
        """
        if not text or len(text.strip()) < self.strategy.min_chunk_size:
            return []

        # Choose chunking method
        if self.strategy.strategy == "fixed":
            chunks = self._chunk_fixed(text)
        elif self.strategy.strategy == "semantic":
            chunks = self._chunk_semantic(text)
        elif self.strategy.strategy == "sliding":
            chunks = self._chunk_sliding(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {self.strategy.strategy}")

        # Add metadata to chunks
        result = []
        for idx, chunk_text in enumerate(chunks):
            if len(chunk_text.strip()) < self.strategy.min_chunk_size:
                continue

            chunk = TextChunk(
                text=chunk_text.strip(),
                chunk_index=idx,
                chunk_size=len(chunk_text),
                word_count=len(chunk_text.split()),
                section_type=section_type,
                section_title=section_title,
                page_number=page_number,
            )
            result.append(chunk)

        logger.info(f"✂️ Created {len(result)} chunks from {len(text)} characters")
        return result

    def _chunk_fixed(self, text: str) -> List[str]:
        """
        Fixed-size chunking with overlap

        Args:
            text: Input text

        Returns:
            List of chunk texts
        """
        # Approximate characters from tokens (rough: 1 token ≈ 4 chars)
        chunk_size_chars = self.strategy.chunk_size * 4
        overlap_chars = self.strategy.chunk_overlap * 4

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size_chars

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending in next 100 chars
                sentence_end = self._find_sentence_boundary(text, end, end + 100)
                if sentence_end:
                    end = sentence_end

            chunk = text[start:end]
            chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap_chars

            if start >= len(text):
                break

        return chunks

    def _chunk_semantic(self, text: str) -> List[str]:
        """
        Semantic chunking based on sentences

        Groups sentences until target size is reached

        Args:
            text: Input text

        Returns:
            List of chunk texts
        """
        # Split into sentences
        sentences = self._split_sentences(text)

        if not sentences:
            return []

        chunk_size_chars = self.strategy.chunk_size * 4
        overlap_chars = self.strategy.chunk_overlap * 4

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            # If adding this sentence exceeds chunk size, finalize current chunk
            if current_size + sentence_size > chunk_size_chars and current_chunk:
                chunks.append(" ".join(current_chunk))

                # Calculate overlap
                if overlap_chars > 0:
                    # Keep last few sentences for overlap
                    overlap_size = 0
                    overlap_sentences = []

                    for sent in reversed(current_chunk):
                        overlap_size += len(sent)
                        overlap_sentences.insert(0, sent)
                        if overlap_size >= overlap_chars:
                            break

                    current_chunk = overlap_sentences
                    current_size = overlap_size
                else:
                    current_chunk = []
                    current_size = 0

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_size += sentence_size

        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _chunk_sliding(self, text: str) -> List[str]:
        """
        Sliding window chunking

        Args:
            text: Input text

        Returns:
            List of chunk texts
        """
        chunk_size_chars = self.strategy.chunk_size * 4
        stride_chars = chunk_size_chars - (self.strategy.chunk_overlap * 4)

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size_chars

            # Try to break at word boundary
            if end < len(text):
                # Find next space
                space_idx = text.find(" ", end)
                if space_idx != -1 and space_idx - end < 50:
                    end = space_idx

            chunk = text[start:end]
            chunks.append(chunk)

            start += stride_chars

            if start >= len(text):
                break

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences

        Uses regex patterns for sentence boundaries

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Pattern for sentence endings
        # Handles: . ! ? followed by space/newline or end of string
        # Avoids splitting on: Dr. Mr. Mrs. etc.
        sentence_pattern = r"""
            (?<!\w\.\w.)        # Not preceded by abbrev like Dr.
            (?<![A-Z][a-z]\.)   # Not preceded by single letter abbrev
            (?<=\.|\?|\!)       # Preceded by sentence ending
            \s+                 # Followed by whitespace
            (?=[A-Z])           # Followed by capital letter
        """

        # Split on pattern
        sentences = re.split(sentence_pattern, text, flags=re.VERBOSE)

        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        # If no sentences found, split on newlines
        if len(sentences) <= 1:
            sentences = [s.strip() for s in text.split("\n") if s.strip()]

        return sentences

    def _find_sentence_boundary(
        self, text: str, start: int, end: int
    ) -> Optional[int]:
        """
        Find sentence boundary in range

        Args:
            text: Full text
            start: Start position
            end: End position

        Returns:
            Position of sentence ending or None
        """
        search_text = text[start:end]

        # Look for sentence endings
        for char in [". ", "? ", "! ", ".\n", "?\n", "!\n"]:
            idx = search_text.rfind(char)
            if idx != -1:
                return start + idx + 1

        return None

    def chunk_document_sections(
        self, sections: List[dict]
    ) -> List[TextChunk]:
        """
        Chunk multiple document sections

        Args:
            sections: List of section dicts with 'content', 'section_type', 'section_title'

        Returns:
            List of all chunks from all sections
        """
        all_chunks = []

        for section in sections:
            chunks = self.chunk_text(
                text=section.get("content", ""),
                section_type=section.get("section_type"),
                section_title=section.get("section_title"),
                page_number=section.get("page_number"),
            )

            all_chunks.extend(chunks)

        logger.info(
            f"📚 Chunked {len(sections)} sections into {len(all_chunks)} total chunks"
        )
        return all_chunks

    def get_chunk_stats(self, chunks: List[TextChunk]) -> dict:
        """
        Get statistics about chunks

        Args:
            chunks: List of chunks

        Returns:
            Statistics dict
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "avg_word_count": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
            }

        chunk_sizes = [c.chunk_size for c in chunks]
        word_counts = [c.word_count for c in chunks]

        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunks),
            "avg_word_count": sum(word_counts) / len(chunks),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
        }


# Helper function to create chunker
def create_chunker(
    strategy: str = "semantic",
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    min_chunk_size: int = 100,
) -> TextChunker:
    """
    Create a text chunker

    Args:
        strategy: Chunking strategy
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
        min_chunk_size: Minimum chunk size

    Returns:
        TextChunker instance
    """
    config = ChunkingStrategy(
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size,
    )

    return TextChunker(config)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Sample text
    sample_text = """
    Deep learning has revolutionized artificial intelligence in recent years.
    Transformer models, introduced in the seminal paper "Attention is All You Need",
    have become the foundation for modern NLP systems. These models use self-attention
    mechanisms to capture long-range dependencies in text.

    The BERT model, developed by Google, demonstrated the power of pre-training on
    large text corpora. It achieved state-of-the-art results on numerous NLP benchmarks.
    Following BERT, models like GPT-2, GPT-3, and T5 pushed the boundaries of what's
    possible with language models.

    Today, large language models are being applied to diverse tasks including translation,
    summarization, question answering, and code generation. The field continues to evolve
    rapidly with new architectures and training techniques emerging regularly.
    """

    # Test different strategies
    strategies = ["fixed", "semantic", "sliding"]

    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"Strategy: {strategy.upper()}")
        print(f"{'='*60}")

        chunker = create_chunker(
            strategy=strategy, chunk_size=256, chunk_overlap=30, min_chunk_size=50
        )

        chunks = chunker.chunk_text(
            sample_text, section_type="introduction", section_title="Introduction"
        )

        print(f"Total chunks: {len(chunks)}\n")

        for i, chunk in enumerate(chunks):
            print(f"Chunk {i+1}:")
            print(f"  Size: {chunk.chunk_size} chars, {chunk.word_count} words")
            print(f"  Text: {chunk.text[:100]}...")
            print()

        # Stats
        stats = chunker.get_chunk_stats(chunks)
        print(f"Statistics:")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.1f}")
            else:
                print(f"  {key}: {value}")
