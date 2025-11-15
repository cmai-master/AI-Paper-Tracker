"""PDF text extraction parsers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
import structlog

logger = structlog.get_logger()


class PDFParser(ABC):
    """Abstract base class for PDF parsers."""

    @abstractmethod
    def extract_text(self, pdf_path: str) -> str:
        """Extract full text from PDF."""
        pass

    @abstractmethod
    def extract_page(self, pdf_path: str, page_num: int) -> str:
        """Extract text from specific page."""
        pass

    @abstractmethod
    def get_metadata(self, pdf_path: str) -> Dict:
        """Get PDF metadata."""
        pass


class PyMuPDFParser(PDFParser):
    """PDF parser using PyMuPDF (fitz)."""

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract full text from PDF using PyMuPDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page in doc:
                text = page.get_text()
                text_parts.append(text)

            doc.close()

            full_text = "\n\n".join(text_parts)

            logger.info(
                "pymupdf_extraction_completed",
                pdf_path=pdf_path,
                pages=len(text_parts),
                chars=len(full_text),
            )

            return full_text

        except Exception as e:
            logger.error(
                "pymupdf_extraction_failed",
                pdf_path=pdf_path,
                error=str(e),
                exc_info=True,
            )
            raise

    def extract_page(self, pdf_path: str, page_num: int) -> str:
        """Extract text from specific page."""
        try:
            doc = fitz.open(pdf_path)

            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} out of range")

            page = doc[page_num]
            text = page.get_text()

            doc.close()

            return text

        except Exception as e:
            logger.error(
                "pymupdf_page_extraction_failed",
                pdf_path=pdf_path,
                page_num=page_num,
                error=str(e),
            )
            raise

    def get_metadata(self, pdf_path: str) -> Dict:
        """Get PDF metadata."""
        try:
            doc = fitz.open(pdf_path)

            metadata = {
                "page_count": len(doc),
                "format": doc.metadata.get("format", ""),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
            }

            doc.close()

            return metadata

        except Exception as e:
            logger.error(
                "pymupdf_metadata_extraction_failed",
                pdf_path=pdf_path,
                error=str(e),
            )
            return {}

    def extract_images(self, pdf_path: str) -> List[Dict]:
        """
        Extract images from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of image metadata dictionaries
        """
        images = []

        try:
            doc = fitz.open(pdf_path)

            for page_num, page in enumerate(doc):
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)

                    images.append(
                        {
                            "page": page_num,
                            "index": img_index,
                            "xref": xref,
                            "width": base_image.get("width"),
                            "height": base_image.get("height"),
                            "colorspace": base_image.get("colorspace"),
                            "ext": base_image.get("ext"),
                            "image_data": base_image.get("image"),
                        }
                    )

            doc.close()

            logger.info(
                "image_extraction_completed",
                pdf_path=pdf_path,
                image_count=len(images),
            )

        except Exception as e:
            logger.error(
                "image_extraction_failed",
                pdf_path=pdf_path,
                error=str(e),
            )

        return images


class PDFPlumberParser(PDFParser):
    """PDF parser using pdfplumber (better for tables)."""

    def extract_text(self, pdf_path: str) -> str:
        """Extract full text from PDF using pdfplumber."""
        try:
            text_parts = []

            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            full_text = "\n\n".join(text_parts)

            logger.info(
                "pdfplumber_extraction_completed",
                pdf_path=pdf_path,
                pages=len(text_parts),
                chars=len(full_text),
            )

            return full_text

        except Exception as e:
            logger.error(
                "pdfplumber_extraction_failed",
                pdf_path=pdf_path,
                error=str(e),
                exc_info=True,
            )
            raise

    def extract_page(self, pdf_path: str, page_num: int) -> str:
        """Extract text from specific page."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num >= len(pdf.pages):
                    raise ValueError(f"Page {page_num} out of range")

                page = pdf.pages[page_num]
                text = page.extract_text() or ""

            return text

        except Exception as e:
            logger.error(
                "pdfplumber_page_extraction_failed",
                pdf_path=pdf_path,
                page_num=page_num,
                error=str(e),
            )
            raise

    def get_metadata(self, pdf_path: str) -> Dict:
        """Get PDF metadata."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                metadata = {
                    "page_count": len(pdf.pages),
                    "metadata": pdf.metadata or {},
                }

            return metadata

        except Exception as e:
            logger.error(
                "pdfplumber_metadata_extraction_failed",
                pdf_path=pdf_path,
                error=str(e),
            )
            return {}

    def extract_tables(self, pdf_path: str) -> List[Dict]:
        """
        Extract tables from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of table data dictionaries
        """
        tables = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()

                    for table_index, table in enumerate(page_tables):
                        if table:
                            tables.append(
                                {
                                    "page": page_num,
                                    "index": table_index,
                                    "data": table,
                                    "rows": len(table),
                                    "cols": len(table[0]) if table else 0,
                                }
                            )

            logger.info(
                "table_extraction_completed",
                pdf_path=pdf_path,
                table_count=len(tables),
            )

        except Exception as e:
            logger.error(
                "table_extraction_failed",
                pdf_path=pdf_path,
                error=str(e),
            )

        return tables


class HybridPDFParser:
    """
    Hybrid parser that uses multiple parsers for best results.

    Uses PyMuPDF for text and images, pdfplumber for tables.
    """

    def __init__(self):
        self.pymupdf_parser = PyMuPDFParser()
        self.pdfplumber_parser = PDFPlumberParser()

    def extract_text(self, pdf_path: str, prefer_parser: str = "pymupdf") -> str:
        """
        Extract text using preferred parser with fallback.

        Args:
            pdf_path: Path to PDF file
            prefer_parser: Preferred parser ("pymupdf" or "pdfplumber")

        Returns:
            Extracted text
        """
        try:
            if prefer_parser == "pymupdf":
                return self.pymupdf_parser.extract_text(pdf_path)
            else:
                return self.pdfplumber_parser.extract_text(pdf_path)

        except Exception as e:
            logger.warning(
                f"{prefer_parser}_failed_trying_fallback",
                pdf_path=pdf_path,
                error=str(e),
            )

            # Try fallback parser
            try:
                if prefer_parser == "pymupdf":
                    return self.pdfplumber_parser.extract_text(pdf_path)
                else:
                    return self.pymupdf_parser.extract_text(pdf_path)
            except Exception as fallback_error:
                logger.error(
                    "all_parsers_failed",
                    pdf_path=pdf_path,
                    error=str(fallback_error),
                )
                raise

    def extract_all(self, pdf_path: str) -> Dict:
        """
        Extract all content from PDF (text, tables, images).

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with all extracted content
        """
        result = {
            "text": "",
            "tables": [],
            "images": [],
            "metadata": {},
            "page_count": 0,
        }

        try:
            # Extract text (prefer PyMuPDF)
            result["text"] = self.pymupdf_parser.extract_text(pdf_path)

            # Extract tables (use pdfplumber)
            result["tables"] = self.pdfplumber_parser.extract_tables(pdf_path)

            # Extract images (use PyMuPDF)
            result["images"] = self.pymupdf_parser.extract_images(pdf_path)

            # Get metadata
            result["metadata"] = self.pymupdf_parser.get_metadata(pdf_path)
            result["page_count"] = result["metadata"].get("page_count", 0)

            logger.info(
                "hybrid_extraction_completed",
                pdf_path=pdf_path,
                text_length=len(result["text"]),
                tables=len(result["tables"]),
                images=len(result["images"]),
            )

        except Exception as e:
            logger.error(
                "hybrid_extraction_failed",
                pdf_path=pdf_path,
                error=str(e),
                exc_info=True,
            )
            raise

        return result
