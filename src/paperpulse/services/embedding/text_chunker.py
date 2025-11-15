"""Text chunking for embedding generation."""

from typing import List, Dict, Optional
import re
import structlog

logger = structlog.get_logger()


class TextChunker:
    """Chunk text for embedding generation."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separator: str = "\n\n",
    ):
        """
        Initialize text chunker.

        Args:
            chunk_size: Target size of each chunk (in tokens, approximate)
            chunk_overlap: Number of tokens to overlap between chunks
            separator: Primary separator to split on
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Chunk text into smaller pieces.

        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or not text.strip():
            return []

        # Split by separator first
        splits = text.split(self.separator)

        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            # Approximate token count (rough: ~4 chars per token)
            split_length = len(split) // 4

            # If split itself is too long, split it further
            if split_length > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunk_text = self.separator.join(current_chunk)
                    chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))
                    current_chunk = []
                    current_length = 0

                # Split long text by sentences
                sub_chunks = self._split_long_text(split)
                for sub_chunk in sub_chunks:
                    chunks.append(
                        self._create_chunk(sub_chunk, len(chunks), metadata)
                    )

            # Add to current chunk if it fits
            elif current_length + split_length <= self.chunk_size:
                current_chunk.append(split)
                current_length += split_length

            # Start new chunk
            else:
                if current_chunk:
                    chunk_text = self.separator.join(current_chunk)
                    chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))

                # Keep overlap from previous chunk
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = [overlap_text, split] if overlap_text else [split]
                current_length = sum(len(c) // 4 for c in current_chunk)

        # Add final chunk
        if current_chunk:
            chunk_text = self.separator.join(current_chunk)
            chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))

        logger.info(
            "text_chunking_completed",
            original_length=len(text),
            chunks_created=len(chunks),
        )

        return chunks

    def chunk_by_sections(
        self, sections: Dict[str, str], metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Chunk text by sections.

        Args:
            sections: Dictionary mapping section names to content
            metadata: Optional metadata

        Returns:
            List of chunk dictionaries
        """
        chunks = []

        for section_name, content in sections.items():
            if not content or not content.strip():
                continue

            # Chunk each section
            section_metadata = {**(metadata or {}), "section": section_name}
            section_chunks = self.chunk(content, section_metadata)

            chunks.extend(section_chunks)

        logger.info(
            "section_chunking_completed",
            sections=len(sections),
            total_chunks=len(chunks),
        )

        return chunks

    def _split_long_text(self, text: str) -> List[str]:
        """
        Split very long text by sentences.

        Args:
            text: Long text to split

        Returns:
            List of smaller chunks
        """
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence) // 4

            if current_length + sentence_length <= self.chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_length
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _get_overlap(self, chunks: List[str]) -> str:
        """
        Get overlap text from previous chunks.

        Args:
            chunks: Previous chunks

        Returns:
            Overlap text
        """
        if not chunks:
            return ""

        # Get last chunk
        last_chunk = chunks[-1]

        # Take last N tokens as overlap (approximate)
        words = last_chunk.split()
        overlap_tokens = min(self.chunk_overlap, len(words))

        if overlap_tokens > 0:
            return " ".join(words[-overlap_tokens:])

        return ""

    def _create_chunk(
        self, text: str, index: int, metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create chunk dictionary.

        Args:
            text: Chunk text
            index: Chunk index
            metadata: Optional metadata

        Returns:
            Chunk dictionary
        """
        chunk = {
            "chunk_index": index,
            "chunk_text": text.strip(),
            "token_count": len(text.split()),
            "char_count": len(text),
        }

        if metadata:
            chunk.update(metadata)

        return chunk


class SemanticChunker:
    """
    Advanced chunker that tries to preserve semantic boundaries.

    Uses heuristics to keep related content together.
    """

    def __init__(self, target_chunk_size: int = 512):
        self.target_chunk_size = target_chunk_size
        self.base_chunker = TextChunker(chunk_size=target_chunk_size)

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Chunk text semantically.

        Args:
            text: Input text
            metadata: Optional metadata

        Returns:
            List of semantic chunks
        """
        # Try to identify natural boundaries
        # 1. Paragraph breaks
        # 2. Section headers
        # 3. List items

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para_length = len(para.split())

            # If paragraph is very long, split it
            if para_length > self.target_chunk_size:
                # Save current chunk
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(
                        self.base_chunker._create_chunk(
                            chunk_text, len(chunks), metadata
                        )
                    )
                    current_chunk = []
                    current_length = 0

                # Split long paragraph
                sub_chunks = self.base_chunker._split_long_text(para)
                for sub in sub_chunks:
                    chunks.append(
                        self.base_chunker._create_chunk(sub, len(chunks), metadata)
                    )

            # Add to current chunk if it fits
            elif current_length + para_length <= self.target_chunk_size:
                current_chunk.append(para)
                current_length += para_length

            # Start new chunk
            else:
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(
                        self.base_chunker._create_chunk(
                            chunk_text, len(chunks), metadata
                        )
                    )
                current_chunk = [para]
                current_length = para_length

        # Final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                self.base_chunker._create_chunk(chunk_text, len(chunks), metadata)
            )

        return chunks
