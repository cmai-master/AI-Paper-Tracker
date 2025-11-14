# PDF Processing Module - 설계 문서

**모듈명:** PDF Processing
**버전:** 1.0
**작성일:** 2025-11-14
**담당:** Document Processing Team

---

## 1. 모듈 개요

### 1.1 목적
학술 논문 PDF에서 텍스트, 테이블, 이미지, 참고문헌 등을 정확하게 추출하고 구조화하여 다운스트림 분석을 지원

### 1.2 핵심 책임
- 다양한 형식의 PDF 파싱 (텍스트 기반, 이미지 기반, 하이브리드)
- 섹션별 텍스트 분리 (Abstract, Introduction, Methodology 등)
- 테이블 및 이미지 추출
- 참고문헌 파싱
- 수식 및 특수 기호 처리
- 품질 검증 및 메트릭 수집

### 1.3 주요 기능
1. **Multi-Parser Architecture**: PyMuPDF, pdfplumber, Tesseract OCR 조합
2. **Section Segmentation**: 논문 표준 섹션 자동 분리
3. **Table Extraction**: 테이블 구조 보존 및 CSV 변환
4. **Reference Parsing**: 참고문헌 정보 추출 및 링크 생성
5. **Quality Assessment**: 추출 품질 자동 평가
6. **Caching**: 처리 결과 캐싱으로 중복 처리 방지

---

## 2. 아키텍처

### 2.1 처리 파이프라인

```
┌─────────────────────────────────────────────────────────┐
│                PDF Processing Pipeline                   │
│                                                          │
│  ┌──────────┐                                           │
│  │ PDF URL  │                                           │
│  └────┬─────┘                                           │
│       │                                                  │
│       ▼                                                  │
│  ┌──────────┐     Cache Hit?                            │
│  │ Downloader├─────────────┐                           │
│  └────┬─────┘              │                           │
│       │ No                 │ Yes                        │
│       ▼                    ▼                            │
│  ┌──────────┐         ┌────────┐                       │
│  │ Format   │         │ Cache  │──► Return             │
│  │ Detector │         └────────┘                       │
│  └────┬─────┘                                           │
│       │                                                  │
│  ┌────┴──────┬───────────┬──────────┐                  │
│  ▼           ▼           ▼          ▼                   │
│┌────┐   ┌────────┐  ┌──────┐  ┌────────┐              │
││Text│   │Scanned │  │Hybrid│  │Legacy  │              │
││PDF │   │  PDF   │  │ PDF  │  │ Format │              │
│└─┬──┘   └───┬────┘  └──┬───┘  └───┬────┘              │
│  │          │           │          │                    │
│  ▼          ▼           ▼          ▼                    │
│┌──────────────────────────────────────┐                │
││      Text Extraction Layer           │                │
││  ┌────────┐ ┌─────────┐ ┌─────────┐ │                │
││  │PyMuPDF │ │pdfplumber│ │Tesseract│ │                │
││  └────────┘ └─────────┘ └─────────┘ │                │
│└──────────────────┬───────────────────┘                │
│                   │                                     │
│                   ▼                                     │
│         ┌──────────────────┐                            │
│         │ Section Segmenter│                            │
│         └──────────┬───────┘                            │
│                    │                                     │
│      ┌─────────────┼─────────────┐                      │
│      ▼             ▼             ▼                      │
│ ┌────────┐   ┌─────────┐   ┌──────────┐               │
│ │ Table  │   │  Image  │   │Reference │               │
│ │Extractor   │Extractor│   │  Parser  │               │
│ └────┬───┘   └────┬────┘   └────┬─────┘               │
│      │            │             │                       │
│      └────────────┼─────────────┘                       │
│                   │                                     │
│                   ▼                                     │
│            ┌──────────────┐                             │
│            │   Validator  │                             │
│            │  & Quality   │                             │
│            │   Checker    │                             │
│            └──────┬───────┘                             │
│                   │                                     │
│                   ▼                                     │
│            ┌──────────────┐                             │
│            │   Storage    │                             │
│            │  (Postgres + │                             │
│            │    S3/Minio) │                             │
│            └──────────────┘                             │
└─────────────────────────────────────────────────────────┘
```

### 2.2 컴포넌트 구조

```python
from abc import ABC, abstractmethod
from typing import Protocol

class PDFParser(Protocol):
    """PDF 파서 인터페이스"""

    def extract_text(self, pdf_path: str) -> str:
        """전체 텍스트 추출"""
        ...

    def extract_page(self, pdf_path: str, page_num: int) -> str:
        """특정 페이지 텍스트 추출"""
        ...

    def get_metadata(self, pdf_path: str) -> dict:
        """PDF 메타데이터"""
        ...

class PDFProcessorOrchestrator:
    """PDF 처리 오케스트레이터"""

    def __init__(self):
        self.parsers = {
            "pymupdf": PyMuPDFParser(),
            "pdfplumber": PDFPlumberParser(),
            "tesseract": TesseractParser()
        }
        self.segmenter = SectionSegmenter()
        self.table_extractor = TableExtractor()
        self.image_extractor = ImageExtractor()
        self.reference_parser = ReferenceParser()
        self.quality_checker = QualityChecker()
        self.cache = RedisCache()

    def process(self, paper_id: str, pdf_url: str) -> ProcessedDocument:
        """PDF 처리 메인 엔트리포인트"""
        ...
```

---

## 3. 데이터 모델

### 3.1 데이터베이스 스키마

```sql
-- 처리된 문서 메타데이터
CREATE TABLE processed_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,

    -- Processing Info
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    processing_duration_ms INT,
    processor_version VARCHAR(20),

    -- Quality Metrics
    text_completeness_score FLOAT,  -- 0.0 - 1.0
    section_coverage_score FLOAT,
    table_extraction_score FLOAT,
    reference_validity_score FLOAT,
    overall_quality_score FLOAT,

    -- Extraction Stats
    page_count INT,
    word_count INT,
    table_count INT,
    image_count INT,
    reference_count INT,
    equation_count INT,

    -- Format Info
    pdf_format VARCHAR(20),  -- text, scanned, hybrid
    ocr_used BOOLEAN DEFAULT false,

    -- Storage
    full_text_path TEXT,  -- S3/Minio path
    sections_path TEXT,
    tables_path TEXT,
    images_path TEXT,

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_paper_processing UNIQUE (paper_id),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- 섹션별 텍스트
CREATE TABLE document_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES processed_documents(id) ON DELETE CASCADE,

    section_type VARCHAR(50) NOT NULL,  -- abstract, introduction, methodology, etc.
    section_title TEXT,
    section_number VARCHAR(20),  -- "2.1", "3.2.1", etc.

    content TEXT NOT NULL,
    word_count INT,
    char_count INT,

    start_page INT,
    end_page INT,

    -- Hierarchy
    parent_section_id UUID REFERENCES document_sections(id),
    section_order INT,

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_doc_section UNIQUE (document_id, section_type, section_number)
);

-- 추출된 테이블
CREATE TABLE extracted_tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES processed_documents(id) ON DELETE CASCADE,

    table_index INT NOT NULL,
    page_number INT,

    -- Table Data
    data JSONB NOT NULL,  -- 2D array
    headers JSONB,  -- First row as headers
    row_count INT,
    column_count INT,

    -- Table Caption
    caption TEXT,
    caption_position VARCHAR(10),  -- above, below

    -- Storage
    csv_path TEXT,  -- S3 path to CSV file
    image_path TEXT,  -- Screenshot of table

    created_at TIMESTAMP DEFAULT NOW()
);

-- 추출된 이미지
CREATE TABLE extracted_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES processed_documents(id) ON DELETE CASCADE,

    image_index INT NOT NULL,
    page_number INT,

    -- Image Info
    image_type VARCHAR(20),  -- figure, diagram, photo, chart
    format VARCHAR(10),  -- png, jpg, svg
    width INT,
    height INT,
    size_bytes INT,

    -- Caption & Context
    caption TEXT,
    context TEXT,  -- Surrounding text

    -- Storage
    storage_path TEXT,  -- S3/Minio path

    created_at TIMESTAMP DEFAULT NOW()
);

-- 참고문헌
CREATE TABLE extracted_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES processed_documents(id) ON DELETE CASCADE,

    reference_index INT NOT NULL,
    raw_text TEXT NOT NULL,

    -- Parsed Fields
    title TEXT,
    authors JSONB,  -- [{"name": "..."}]
    year INT,
    venue TEXT,  -- Journal/Conference name

    -- External IDs
    arxiv_id VARCHAR(20),
    doi VARCHAR(100),
    url TEXT,

    -- Link to our database
    linked_paper_id UUID REFERENCES papers(id),

    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_processed_docs_paper_id ON processed_documents(paper_id);
CREATE INDEX idx_processed_docs_status ON processed_documents(status);
CREATE INDEX idx_sections_document_id ON document_sections(document_id);
CREATE INDEX idx_sections_type ON document_sections(section_type);
CREATE INDEX idx_tables_document_id ON extracted_tables(document_id);
CREATE INDEX idx_images_document_id ON extracted_images(document_id);
CREATE INDEX idx_references_document_id ON extracted_references(document_id);
CREATE INDEX idx_references_linked_paper ON extracted_references(linked_paper_id);
```

### 3.2 내부 데이터 모델

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime
from enum import Enum

class PDFFormat(str, Enum):
    TEXT = "text"
    SCANNED = "scanned"
    HYBRID = "hybrid"
    LEGACY = "legacy"

class SectionType(str, Enum):
    TITLE = "title"
    ABSTRACT = "abstract"
    KEYWORDS = "keywords"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    BACKGROUND = "background"
    METHODOLOGY = "methodology"
    EXPERIMENTS = "experiments"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    ACKNOWLEDGMENTS = "acknowledgments"
    REFERENCES = "references"
    APPENDIX = "appendix"

class DocumentSection(BaseModel):
    section_type: SectionType
    section_title: Optional[str]
    section_number: Optional[str]
    content: str
    word_count: int
    start_page: int
    end_page: int
    subsections: List['DocumentSection'] = []

    def to_dict(self) -> dict:
        return {
            "type": self.section_type,
            "title": self.section_title,
            "number": self.section_number,
            "content": self.content,
            "words": self.word_count,
            "pages": f"{self.start_page}-{self.end_page}",
            "subsections": [s.to_dict() for s in self.subsections]
        }

class ExtractedTable(BaseModel):
    table_index: int
    page_number: int
    data: List[List[str]]  # 2D array
    headers: Optional[List[str]]
    caption: Optional[str]
    caption_position: Optional[Literal["above", "below"]]

    @property
    def row_count(self) -> int:
        return len(self.data)

    @property
    def column_count(self) -> int:
        return len(self.data[0]) if self.data else 0

    def to_csv(self) -> str:
        """CSV 형식으로 변환"""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        if self.headers:
            writer.writerow(self.headers)

        writer.writerows(self.data)
        return output.getvalue()

class ExtractedImage(BaseModel):
    image_index: int
    page_number: int
    image_type: Literal["figure", "diagram", "photo", "chart"]
    format: str
    width: int
    height: int
    data: bytes
    caption: Optional[str]
    context: Optional[str]  # Surrounding text

class ParsedReference(BaseModel):
    reference_index: int
    raw_text: str
    title: Optional[str]
    authors: List[str] = []
    year: Optional[int]
    venue: Optional[str]
    arxiv_id: Optional[str]
    doi: Optional[str]
    url: Optional[str]

class QualityMetrics(BaseModel):
    text_completeness: float  # 0.0 - 1.0
    section_coverage: float
    table_accuracy: float
    reference_validity: float
    overall_score: float

    def is_acceptable(self, threshold: float = 0.7) -> bool:
        return self.overall_score >= threshold

class ProcessedDocument(BaseModel):
    paper_id: str
    processing_started_at: datetime
    processing_completed_at: Optional[datetime]

    # Extracted Content
    full_text: str
    sections: List[DocumentSection]
    tables: List[ExtractedTable]
    images: List[ExtractedImage]
    references: List[ParsedReference]

    # Metadata
    page_count: int
    word_count: int
    pdf_format: PDFFormat
    ocr_used: bool

    # Quality
    quality_metrics: QualityMetrics

    # Status
    status: Literal["pending", "processing", "completed", "failed"]
    error_message: Optional[str]
```

---

## 4. PDF 파싱 구현

### 4.1 PyMuPDF Parser

```python
import fitz  # PyMuPDF
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PyMuPDFParser:
    """PyMuPDF 기반 파서 - 빠르고 정확한 텍스트 추출"""

    def extract_text(self, pdf_path: str) -> str:
        """전체 텍스트 추출"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""

            for page_num, page in enumerate(doc):
                page_text = page.get_text("text")
                full_text += f"\n--- PAGE {page_num + 1} ---\n{page_text}"

            doc.close()
            return full_text

        except Exception as e:
            logger.error(f"PyMuPDF text extraction failed: {e}")
            raise

    def extract_with_layout(self, pdf_path: str) -> str:
        """레이아웃 보존하여 텍스트 추출"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""

            for page_num, page in enumerate(doc):
                # "blocks" 모드는 텍스트 블록 정보 포함
                blocks = page.get_text("blocks")

                page_text = f"\n--- PAGE {page_num + 1} ---\n"

                # 블록을 y좌표 기준 정렬 (상->하)
                blocks.sort(key=lambda b: b[1])  # b[1] is y0

                for block in blocks:
                    if block[6] == 0:  # block type 0 = text
                        text = block[4]
                        page_text += text + "\n"

                full_text += page_text

            doc.close()
            return full_text

        except Exception as e:
            logger.error(f"PyMuPDF layout extraction failed: {e}")
            raise

    def extract_images(self, pdf_path: str) -> List[ExtractedImage]:
        """이미지 추출"""
        images = []

        try:
            doc = fitz.open(pdf_path)

            for page_num, page in enumerate(doc):
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)

                    extracted = ExtractedImage(
                        image_index=img_index,
                        page_number=page_num + 1,
                        image_type="figure",  # Will be classified later
                        format=base_image["ext"],
                        width=base_image.get("width", 0),
                        height=base_image.get("height", 0),
                        data=base_image["image"],
                        caption=None,  # Will be extracted from surrounding text
                        context=None
                    )

                    images.append(extracted)

            doc.close()
            return images

        except Exception as e:
            logger.error(f"PyMuPDF image extraction failed: {e}")
            return []

    def get_metadata(self, pdf_path: str) -> dict:
        """PDF 메타데이터"""
        try:
            doc = fitz.open(pdf_path)
            metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "format": doc.metadata.get("format", ""),
            }
            doc.close()
            return metadata

        except Exception as e:
            logger.error(f"PyMuPDF metadata extraction failed: {e}")
            return {}

    def detect_text_density(self, pdf_path: str) -> float:
        """텍스트 밀도 계산 (OCR 필요 여부 판단)"""
        try:
            doc = fitz.open(pdf_path)
            total_chars = 0
            total_pages = len(doc)

            for page in doc:
                text = page.get_text("text")
                total_chars += len(text.strip())

            doc.close()

            avg_chars_per_page = total_chars / total_pages if total_pages > 0 else 0

            # 페이지당 평균 100자 이하면 스캔 PDF로 판단
            return avg_chars_per_page

        except Exception as e:
            logger.error(f"Text density detection failed: {e}")
            return 0
```

### 4.2 PDFPlumber Parser (테이블 전용)

```python
import pdfplumber
from typing import List

class PDFPlumberParser:
    """pdfplumber - 테이블 추출 특화"""

    def extract_tables(self, pdf_path: str) -> List[ExtractedTable]:
        """테이블 추출"""
        tables = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # 테이블 추출
                    page_tables = page.extract_tables()

                    for table_index, table_data in enumerate(page_tables):
                        if not table_data or len(table_data) == 0:
                            continue

                        # 첫 행을 헤더로 간주
                        headers = table_data[0] if table_data else None
                        data_rows = table_data[1:] if len(table_data) > 1 else []

                        # Caption 추출 (테이블 위/아래 텍스트에서)
                        caption = self._extract_table_caption(page, table_data)

                        extracted = ExtractedTable(
                            table_index=table_index,
                            page_number=page_num + 1,
                            data=data_rows,
                            headers=headers,
                            caption=caption,
                            caption_position="above" if caption else None
                        )

                        tables.append(extracted)

            return tables

        except Exception as e:
            logger.error(f"PDFPlumber table extraction failed: {e}")
            return []

    def _extract_table_caption(self, page, table_data) -> Optional[str]:
        """테이블 캡션 추출"""
        # 테이블 위/아래 텍스트에서 "Table X:" 패턴 찾기
        import re

        text = page.extract_text()
        if not text:
            return None

        # "Table 1:", "Table 2:" 등의 패턴
        caption_pattern = r'Table\s+\d+[:\.]?\s*(.+?)(?:\n|$)'
        match = re.search(caption_pattern, text, re.IGNORECASE)

        if match:
            return match.group(0).strip()

        return None
```

### 4.3 Tesseract OCR Parser

```python
import pytesseract
from PIL import Image
import fitz  # PyMuPDF for PDF -> Image conversion
from typing import List

class TesseractParser:
    """Tesseract OCR - 스캔 PDF 처리"""

    def __init__(self, lang: str = "eng"):
        self.lang = lang
        self.was_used = False

    def extract_text_from_scanned_pdf(self, pdf_path: str) -> str:
        """스캔 PDF에서 OCR로 텍스트 추출"""
        self.was_used = True
        full_text = ""

        try:
            doc = fitz.open(pdf_path)

            for page_num, page in enumerate(doc):
                # PDF 페이지를 이미지로 변환
                pix = page.get_pixmap(dpi=300)  # 고해상도
                img_data = pix.tobytes("png")

                # PIL Image로 변환
                image = Image.open(io.BytesIO(img_data))

                # OCR 수행
                page_text = pytesseract.image_to_string(
                    image,
                    lang=self.lang,
                    config='--psm 1'  # Automatic page segmentation with OSD
                )

                full_text += f"\n--- PAGE {page_num + 1} (OCR) ---\n{page_text}"

            doc.close()
            return full_text

        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            raise

    def extract_from_image_region(self, pdf_path: str, page_num: int,
                                  bbox: tuple) -> str:
        """특정 영역에서 OCR"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]

            # 특정 영역 추출
            rect = fitz.Rect(bbox)
            pix = page.get_pixmap(clip=rect, dpi=300)
            img_data = pix.tobytes("png")

            image = Image.open(io.BytesIO(img_data))
            text = pytesseract.image_to_string(image, lang=self.lang)

            doc.close()
            return text

        except Exception as e:
            logger.error(f"Region OCR failed: {e}")
            return ""
```

---

## 5. 섹션 분할 (Section Segmentation)

### 5.1 Rule-Based Segmenter

```python
import re
from typing import Dict, List

class SectionSegmenter:
    """논문 섹션 자동 분할"""

    # 섹션 패턴 정의
    SECTION_PATTERNS = {
        SectionType.ABSTRACT: [
            r'(?i)^abstract\s*\n',
            r'(?i)^summary\s*\n'
        ],
        SectionType.INTRODUCTION: [
            r'(?i)^1\.?\s*introduction\s*\n',
            r'(?i)^introduction\s*\n'
        ],
        SectionType.RELATED_WORK: [
            r'(?i)^2\.?\s*related\s+work\s*\n',
            r'(?i)^related\s+work\s*\n',
            r'(?i)^2\.?\s*background\s*\n'
        ],
        SectionType.METHODOLOGY: [
            r'(?i)^3\.?\s*method(?:ology)?\s*\n',
            r'(?i)^3\.?\s*approach\s*\n',
            r'(?i)^method(?:ology)?\s*\n'
        ],
        SectionType.EXPERIMENTS: [
            r'(?i)^4\.?\s*experiment(?:s|al\s+results)?\s*\n',
            r'(?i)^4\.?\s*evaluation\s*\n',
            r'(?i)^experiment(?:s)?\s*\n'
        ],
        SectionType.CONCLUSION: [
            r'(?i)^(?:5|6)\.?\s*conclusion(?:s)?\s*\n',
            r'(?i)^conclusion(?:s)?\s*\n'
        ],
        SectionType.REFERENCES: [
            r'(?i)^references?\s*\n',
            r'(?i)^bibliography\s*\n'
        ]
    }

    def segment(self, full_text: str) -> List[DocumentSection]:
        """텍스트를 섹션으로 분할"""
        sections = []

        # 섹션 경계 찾기
        boundaries = self._find_section_boundaries(full_text)

        # 섹션별로 텍스트 추출
        for i, (section_type, start_pos) in enumerate(boundaries):
            # 다음 섹션 시작 위치 (없으면 끝까지)
            end_pos = boundaries[i + 1][1] if i + 1 < len(boundaries) else len(full_text)

            content = full_text[start_pos:end_pos].strip()

            # 섹션 제목 추출
            title_match = re.match(r'^([\d\.]+\s+)?(.+?)(?:\n|$)', content)
            section_title = title_match.group(2).strip() if title_match else None
            section_number = title_match.group(1).strip() if title_match and title_match.group(1) else None

            # 제목 제거한 본문
            if title_match:
                content = content[title_match.end():].strip()

            # 페이지 번호 추정 (PAGE 마커 기반)
            start_page = self._estimate_page_number(full_text[:start_pos])
            end_page = self._estimate_page_number(full_text[:end_pos])

            section = DocumentSection(
                section_type=section_type,
                section_title=section_title,
                section_number=section_number,
                content=content,
                word_count=len(content.split()),
                start_page=start_page,
                end_page=end_page
            )

            sections.append(section)

        return sections

    def _find_section_boundaries(self, text: str) -> List[tuple]:
        """섹션 경계 찾기"""
        boundaries = []

        for section_type, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    boundaries.append((section_type, match.start()))
                    break  # 첫 번째 매칭 패턴 사용

        # 위치 순으로 정렬
        boundaries.sort(key=lambda x: x[1])

        return boundaries

    def _estimate_page_number(self, text_before: str) -> int:
        """PAGE 마커 개수로 페이지 번호 추정"""
        page_markers = re.findall(r'--- PAGE (\d+) ---', text_before)
        return int(page_markers[-1]) if page_markers else 1

    def extract_abstract(self, text: str) -> Optional[str]:
        """초록만 빠르게 추출"""
        for pattern in self.SECTION_PATTERNS[SectionType.ABSTRACT]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 초록 시작 위치
                start = match.end()

                # 다음 섹션 찾기 (Introduction 또는 Keywords)
                next_section = re.search(
                    r'(?i)(introduction|keywords|1\.)',
                    text[start:]
                )

                if next_section:
                    end = start + next_section.start()
                else:
                    # 찾지 못하면 500자까지
                    end = start + 500

                abstract = text[start:end].strip()
                return abstract

        return None
```

### 5.2 ML-Based Segmenter (Advanced)

```python
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

class MLSectionSegmenter:
    """ML 기반 섹션 분할 (SciBERT 등 사용)"""

    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            num_labels=len(SectionType)
        )
        # TODO: Fine-tune on paper section dataset

    def segment(self, text: str) -> List[DocumentSection]:
        """ML 모델로 섹션 분할"""
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )

        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=-1)

        # Convert predictions to sections
        # TODO: Implement label decoding

        return []
```

---

## 6. 참고문헌 파싱

### 6.1 Reference Parser

```python
import re
from typing import List, Optional

class ReferenceParser:
    """참고문헌 파싱"""

    def parse_references(self, references_text: str) -> List[ParsedReference]:
        """참고문헌 섹션에서 개별 참고문헌 파싱"""
        references = []

        # 참고문헌을 개별 항목으로 분리
        # 패턴: [1] 또는 1. 로 시작하는 라인
        items = re.split(r'\n\s*[\[\(]?\d+[\]\)]?\s+', references_text)

        for idx, item_text in enumerate(items[1:], start=1):  # 첫 항목은 헤더
            if not item_text.strip():
                continue

            parsed = self._parse_single_reference(idx, item_text.strip())
            if parsed:
                references.append(parsed)

        return references

    def _parse_single_reference(self, index: int, text: str) -> Optional[ParsedReference]:
        """개별 참고문헌 파싱"""

        # arXiv ID 추출
        arxiv_match = re.search(r'arXiv:(\d+\.\d+)', text, re.IGNORECASE)
        arxiv_id = arxiv_match.group(1) if arxiv_match else None

        # DOI 추출
        doi_match = re.search(r'doi:?\s*(10\.\d+/[^\s]+)', text, re.IGNORECASE)
        doi = doi_match.group(1) if doi_match else None

        # URL 추출
        url_match = re.search(r'https?://[^\s]+', text)
        url = url_match.group(0) if url_match else None

        # 제목 추출 (따옴표 안의 텍스트 또는 첫 번째 긴 문자열)
        title_match = re.search(r'["\'](.+?)["\']', text)
        title = title_match.group(1) if title_match else None

        if not title:
            # 따옴표가 없으면 첫 번째 긴 구문을 제목으로 간주
            words = text.split()
            if len(words) > 3:
                title = ' '.join(words[:min(15, len(words))])

        # 저자 추출 (간단한 휴리스틱)
        authors = self._extract_authors(text)

        # 연도 추출
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        year = int(year_match.group(0)) if year_match else None

        # Venue 추출 (컨퍼런스/저널 이름)
        venue = self._extract_venue(text)

        return ParsedReference(
            reference_index=index,
            raw_text=text,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            arxiv_id=arxiv_id,
            doi=doi,
            url=url
        )

    def _extract_authors(self, text: str) -> List[str]:
        """저자 이름 추출"""
        # 간단한 패턴: "LastName, FirstInitial." 형식
        author_pattern = r'([A-Z][a-z]+(?:\s+[A-Z]\.)+)'
        matches = re.findall(author_pattern, text)
        return matches[:10]  # 최대 10명

    def _extract_venue(self, text: str) -> Optional[str]:
        """컨퍼런스/저널 이름 추출"""
        # 잘 알려진 컨퍼런스/저널 약어
        venues = [
            "NeurIPS", "ICML", "ICLR", "ACL", "EMNLP", "CVPR", "ICCV",
            "ECCV", "AAAI", "IJCAI", "KDD", "WWW", "SIGIR",
            "Nature", "Science", "PNAS", "JMLR"
        ]

        for venue in venues:
            if re.search(rf'\b{venue}\b', text, re.IGNORECASE):
                return venue

        return None
```

---

## 7. 품질 평가

### 7.1 Quality Checker

```python
class QualityChecker:
    """처리 품질 평가"""

    def evaluate(self, processed_doc: ProcessedDocument) -> QualityMetrics:
        """전반적인 품질 평가"""

        text_completeness = self._check_text_completeness(processed_doc)
        section_coverage = self._check_section_coverage(processed_doc)
        table_accuracy = self._check_table_quality(processed_doc)
        reference_validity = self._check_reference_validity(processed_doc)

        overall = (
            text_completeness * 0.4 +
            section_coverage * 0.3 +
            table_accuracy * 0.15 +
            reference_validity * 0.15
        )

        return QualityMetrics(
            text_completeness=text_completeness,
            section_coverage=section_coverage,
            table_accuracy=table_accuracy,
            reference_validity=reference_validity,
            overall_score=overall
        )

    def _check_text_completeness(self, doc: ProcessedDocument) -> float:
        """텍스트 완성도 체크"""
        # 기대 단어 수 대비 실제 단어 수
        expected_words_per_page = 500
        expected_total = doc.page_count * expected_words_per_page

        if doc.word_count >= expected_total * 0.8:
            return 1.0
        elif doc.word_count >= expected_total * 0.5:
            return 0.7
        elif doc.word_count >= expected_total * 0.3:
            return 0.4
        else:
            return 0.2

    def _check_section_coverage(self, doc: ProcessedDocument) -> float:
        """필수 섹션 포함 여부"""
        required_sections = {
            SectionType.ABSTRACT,
            SectionType.INTRODUCTION,
            SectionType.METHODOLOGY,
            SectionType.CONCLUSION,
            SectionType.REFERENCES
        }

        found_sections = {s.section_type for s in doc.sections}
        coverage = len(required_sections & found_sections) / len(required_sections)

        return coverage

    def _check_table_quality(self, doc: ProcessedDocument) -> float:
        """테이블 추출 품질"""
        if not doc.tables:
            return 0.5  # 테이블 없음은 중립

        valid_tables = sum(
            1 for t in doc.tables
            if t.row_count >= 2 and t.column_count >= 2
        )

        return valid_tables / len(doc.tables)

    def _check_reference_validity(self, doc: ProcessedDocument) -> float:
        """참고문헌 유효성"""
        if not doc.references:
            return 0.3

        valid_refs = sum(
            1 for r in doc.references
            if r.title or r.arxiv_id or r.doi
        )

        return valid_refs / len(doc.references)
```

---

## 8. API 및 태스크

### 8.1 Celery Task

```python
@app.task(bind=True, max_retries=3)
def process_pdf(self, paper_id: str, pdf_url: str):
    """PDF 처리 태스크"""
    try:
        orchestrator = PDFProcessorOrchestrator()
        result = orchestrator.process(paper_id, pdf_url)

        return {
            "status": "success",
            "paper_id": paper_id,
            "word_count": result.word_count,
            "quality_score": result.quality_metrics.overall_score
        }

    except Exception as exc:
        logger.error(f"PDF processing failed for {paper_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### 8.2 REST API

```python
@router.post("/process")
async def trigger_pdf_processing(
    paper_id: str,
    pdf_url: str,
    background_tasks: BackgroundTasks
):
    """PDF 처리 시작"""
    background_tasks.add_task(process_pdf, paper_id, pdf_url)
    return {"status": "processing", "paper_id": paper_id}

@router.get("/status/{paper_id}")
async def get_processing_status(paper_id: str, db: Session = Depends(get_db)):
    """처리 상태 조회"""
    doc = db.query(ProcessedDocument).filter(
        ProcessedDocument.paper_id == paper_id
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "status": doc.status,
        "quality_score": doc.overall_quality_score,
        "sections_count": len(doc.sections),
        "completed_at": doc.processing_completed_at
    }
```

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-11-14
