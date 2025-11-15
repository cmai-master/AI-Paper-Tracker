"""
PDF Parsers - Multi-parser architecture
"""

import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from abc import ABC, abstractmethod

import fitz  # PyMuPDF
import pdfplumber

from app.services.pdf.schemas import (
    ExtractedText,
    TableData,
    ImageData,
    PDFFormat,
)

logger = logging.getLogger(__name__)


class BasePDFParser(ABC):
    """Base PDF parser interface"""

    @abstractmethod
    def extract_text(self, pdf_path: Path) -> Optional[ExtractedText]:
        """Extract text from PDF"""
        pass

    @abstractmethod
    def extract_tables(self, pdf_path: Path) -> List[TableData]:
        """Extract tables from PDF"""
        pass

    @abstractmethod
    def detect_format(self, pdf_path: Path) -> PDFFormat:
        """Detect PDF format (text, scanned, hybrid)"""
        pass


class PyMuPDFParser(BasePDFParser):
    """PyMuPDF (fitz) parser - Fast and reliable for text extraction"""

    def extract_text(self, pdf_path: Path) -> Optional[ExtractedText]:
        """
        Extract text using PyMuPDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            ExtractedText or None if failed
        """
        try:
            doc = fitz.open(pdf_path)
            full_text_parts = []
            page_count = len(doc)

            for page_num in range(page_count):
                page = doc[page_num]
                text = page.get_text()
                full_text_parts.append(text)

            doc.close()

            full_text = "\n\n".join(full_text_parts)
            word_count = len(full_text.split())
            char_count = len(full_text)

            logger.debug(
                f"Extracted {word_count} words, {char_count} chars from {page_count} pages"
            )

            return ExtractedText(
                full_text=full_text,
                page_count=page_count,
                word_count=word_count,
                char_count=char_count,
            )

        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}", exc_info=True)
            return None

    def extract_tables(self, pdf_path: Path) -> List[TableData]:
        """
        PyMuPDF doesn't have table extraction - use pdfplumber instead

        Args:
            pdf_path: Path to PDF file

        Returns:
            Empty list (defer to pdfplumber)
        """
        return []

    def extract_images(self, pdf_path: Path, output_dir: Optional[Path] = None) -> List[ImageData]:
        """
        Extract images from PDF

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save extracted images

        Returns:
            List of ImageData
        """
        images = []

        try:
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)

                    image_data = ImageData(
                        image_index=len(images),
                        page_number=page_num + 1,
                        format=base_image["ext"],
                        width=base_image["width"],
                        height=base_image["height"],
                        size_bytes=len(base_image["image"]),
                    )

                    # Save image if output_dir provided
                    if output_dir:
                        output_dir.mkdir(parents=True, exist_ok=True)
                        image_path = (
                            output_dir / f"image_{len(images)}_p{page_num + 1}.{base_image['ext']}"
                        )
                        with open(image_path, "wb") as img_file:
                            img_file.write(base_image["image"])
                        image_data.storage_path = str(image_path)

                    images.append(image_data)

            doc.close()
            logger.info(f"✅ Extracted {len(images)} images from PDF")

        except Exception as e:
            logger.error(f"Image extraction failed: {e}", exc_info=True)

        return images

    def detect_format(self, pdf_path: Path) -> PDFFormat:
        """
        Detect PDF format by analyzing text content

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFFormat (text, scanned, or hybrid)
        """
        try:
            doc = fitz.open(pdf_path)
            text_pages = 0
            total_pages = len(doc)

            for page in doc:
                text = page.get_text().strip()
                if len(text) > 100:  # Threshold for "has text"
                    text_pages += 1

            doc.close()

            text_ratio = text_pages / total_pages if total_pages > 0 else 0

            if text_ratio >= 0.9:
                return PDFFormat.TEXT
            elif text_ratio <= 0.1:
                return PDFFormat.SCANNED
            else:
                return PDFFormat.HYBRID

        except Exception as e:
            logger.error(f"Format detection failed: {e}", exc_info=True)
            return PDFFormat.TEXT  # Default


class PDFPlumberParser(BasePDFParser):
    """pdfplumber parser - Excellent for table extraction"""

    def extract_text(self, pdf_path: Path) -> Optional[ExtractedText]:
        """
        Extract text using pdfplumber

        Args:
            pdf_path: Path to PDF file

        Returns:
            ExtractedText or None if failed
        """
        try:
            full_text_parts = []

            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)

                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text_parts.append(text)

            full_text = "\n\n".join(full_text_parts)
            word_count = len(full_text.split())
            char_count = len(full_text)

            logger.debug(
                f"pdfplumber: Extracted {word_count} words, {char_count} chars from {page_count} pages"
            )

            return ExtractedText(
                full_text=full_text,
                page_count=page_count,
                word_count=word_count,
                char_count=char_count,
            )

        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}", exc_info=True)
            return None

    def extract_tables(self, pdf_path: Path) -> List[TableData]:
        """
        Extract tables using pdfplumber

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of TableData
        """
        tables = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_tables = page.extract_tables()

                    for table_idx, table in enumerate(page_tables):
                        if not table or len(table) == 0:
                            continue

                        # Clean table data
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [
                                str(cell).strip() if cell is not None else ""
                                for cell in row
                            ]
                            cleaned_table.append(cleaned_row)

                        # Extract headers (first row)
                        headers = cleaned_table[0] if cleaned_table else []
                        data_rows = cleaned_table[1:] if len(cleaned_table) > 1 else cleaned_table

                        table_data = TableData(
                            table_index=len(tables),
                            page_number=page_num,
                            data=cleaned_table,
                            headers=headers if headers else None,
                            row_count=len(cleaned_table),
                            column_count=len(cleaned_table[0]) if cleaned_table else 0,
                        )

                        tables.append(table_data)

            logger.info(f"✅ Extracted {len(tables)} tables from PDF")

        except Exception as e:
            logger.error(f"Table extraction failed: {e}", exc_info=True)

        return tables

    def detect_format(self, pdf_path: Path) -> PDFFormat:
        """
        Detect PDF format using pdfplumber

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFFormat
        """
        try:
            text_pages = 0
            total_pages = 0

            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

                for page in pdf.pages:
                    text = page.extract_text()
                    if text and len(text.strip()) > 100:
                        text_pages += 1

            text_ratio = text_pages / total_pages if total_pages > 0 else 0

            if text_ratio >= 0.9:
                return PDFFormat.TEXT
            elif text_ratio <= 0.1:
                return PDFFormat.SCANNED
            else:
                return PDFFormat.HYBRID

        except Exception as e:
            logger.error(f"Format detection failed: {e}", exc_info=True)
            return PDFFormat.TEXT


class MultiPDFParser:
    """
    Multi-parser strategy with fallback

    Uses PyMuPDF as primary (fast), pdfplumber for tables
    """

    def __init__(self):
        self.pymupdf = PyMuPDFParser()
        self.pdfplumber = PDFPlumberParser()

    def parse(self, pdf_path: Path) -> Tuple[
        Optional[ExtractedText],
        List[TableData],
        List[ImageData],
        PDFFormat
    ]:
        """
        Parse PDF using multi-parser strategy

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (text, tables, images, format)
        """
        logger.info(f"📄 Parsing PDF: {pdf_path.name}")

        # 1. Detect format
        pdf_format = self.pymupdf.detect_format(pdf_path)
        logger.info(f"PDF format detected: {pdf_format.value}")

        # 2. Extract text (try PyMuPDF first, fallback to pdfplumber)
        extracted_text = self.pymupdf.extract_text(pdf_path)
        if not extracted_text or extracted_text.word_count < 100:
            logger.warning("PyMuPDF extraction poor, trying pdfplumber...")
            extracted_text = self.pdfplumber.extract_text(pdf_path)

        # 3. Extract tables (use pdfplumber)
        tables = self.pdfplumber.extract_tables(pdf_path)

        # 4. Extract images (use PyMuPDF)
        images = self.pymupdf.extract_images(pdf_path)

        logger.info(
            f"✅ Parsed: {extracted_text.word_count if extracted_text else 0} words, "
            f"{len(tables)} tables, {len(images)} images"
        )

        return extracted_text, tables, images, pdf_format


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python parsers.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])

    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    parser = MultiPDFParser()
    text, tables, images, pdf_format = parser.parse(pdf_path)

    print(f"\n📊 Results:")
    print(f"Format: {pdf_format.value}")
    if text:
        print(f"Text: {text.word_count} words, {text.page_count} pages")
    print(f"Tables: {len(tables)}")
    print(f"Images: {len(images)}")

    if text:
        print(f"\nFirst 500 characters:\n{text.full_text[:500]}...")
