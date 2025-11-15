"""
PDF Downloader - arXiv 및 기타 소스에서 PDF 다운로드
"""

import logging
import hashlib
from pathlib import Path
from typing import Optional
import aiohttp
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFDownloader:
    """PDF 다운로더"""

    def __init__(self, download_dir: str = "./data/pdfs"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting
        self.semaphore = asyncio.Semaphore(5)  # Max 5 concurrent downloads
        self.min_delay = 1.0  # Minimum delay between requests (seconds)

    async def download_arxiv_pdf(
        self, arxiv_id: str, force_redownload: bool = False
    ) -> Optional[Path]:
        """
        Download PDF from arXiv

        Args:
            arxiv_id: arXiv paper ID (e.g., "2311.12345")
            force_redownload: Force redownload even if file exists

        Returns:
            Path to downloaded PDF or None if failed
        """
        # Construct URL
        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # Generate filename
        filename = f"{arxiv_id}.pdf"
        filepath = self.download_dir / filename

        # Check if already exists
        if filepath.exists() and not force_redownload:
            logger.info(f"✓ PDF already exists: {filename}")
            return filepath

        logger.info(f"📥 Downloading PDF: {arxiv_id} from {url}")

        async with self.semaphore:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                        if response.status == 200:
                            content = await response.read()

                            # Verify it's actually a PDF
                            if not content.startswith(b"%PDF"):
                                logger.error(f"❌ Downloaded file is not a valid PDF: {arxiv_id}")
                                return None

                            # Save to disk
                            with open(filepath, "wb") as f:
                                f.write(content)

                            # Verify file size
                            file_size = filepath.stat().st_size
                            logger.info(
                                f"✅ Downloaded PDF: {filename} ({file_size / 1024:.1f} KB)"
                            )

                            # Rate limiting
                            await asyncio.sleep(self.min_delay)

                            return filepath

                        elif response.status == 404:
                            logger.error(f"❌ PDF not found: {arxiv_id}")
                            return None
                        else:
                            logger.error(
                                f"❌ Failed to download PDF {arxiv_id}: HTTP {response.status}"
                            )
                            return None

            except asyncio.TimeoutError:
                logger.error(f"❌ Download timeout for {arxiv_id}")
                return None
            except Exception as e:
                logger.error(f"❌ Error downloading {arxiv_id}: {e}", exc_info=True)
                return None

    async def download_from_url(
        self, url: str, filename: Optional[str] = None
    ) -> Optional[Path]:
        """
        Download PDF from arbitrary URL

        Args:
            url: PDF URL
            filename: Optional filename (will hash URL if not provided)

        Returns:
            Path to downloaded PDF or None if failed
        """
        # Generate filename from URL hash if not provided
        if not filename:
            url_hash = hashlib.md5(url.encode()).hexdigest()
            filename = f"{url_hash}.pdf"

        filepath = self.download_dir / filename

        logger.info(f"📥 Downloading PDF from: {url}")

        async with self.semaphore:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=300),
                        headers={"User-Agent": "PaperPulse/1.0"}
                    ) as response:
                        if response.status == 200:
                            content = await response.read()

                            # Verify it's a PDF
                            if not content.startswith(b"%PDF"):
                                logger.error(f"❌ Downloaded file is not a valid PDF: {url}")
                                return None

                            # Save to disk
                            with open(filepath, "wb") as f:
                                f.write(content)

                            file_size = filepath.stat().st_size
                            logger.info(
                                f"✅ Downloaded PDF: {filename} ({file_size / 1024:.1f} KB)"
                            )

                            await asyncio.sleep(self.min_delay)
                            return filepath

                        else:
                            logger.error(f"❌ Failed to download PDF: HTTP {response.status}")
                            return None

            except Exception as e:
                logger.error(f"❌ Error downloading PDF from {url}: {e}", exc_info=True)
                return None

    def get_pdf_path(self, arxiv_id: str) -> Optional[Path]:
        """
        Get path to local PDF file if it exists

        Args:
            arxiv_id: arXiv paper ID

        Returns:
            Path if file exists, None otherwise
        """
        filepath = self.download_dir / f"{arxiv_id}.pdf"
        return filepath if filepath.exists() else None

    def delete_pdf(self, arxiv_id: str) -> bool:
        """
        Delete local PDF file

        Args:
            arxiv_id: arXiv paper ID

        Returns:
            True if deleted, False if file didn't exist
        """
        filepath = self.download_dir / f"{arxiv_id}.pdf"
        if filepath.exists():
            filepath.unlink()
            logger.info(f"🗑️ Deleted PDF: {arxiv_id}")
            return True
        return False


# Example usage
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def main():
        downloader = PDFDownloader()

        # Download a specific paper
        arxiv_id = "2311.12345"  # Replace with actual arXiv ID
        pdf_path = await downloader.download_arxiv_pdf(arxiv_id)

        if pdf_path:
            print(f"\n✅ PDF downloaded to: {pdf_path}")
        else:
            print(f"\n❌ Failed to download PDF")

    asyncio.run(main())
