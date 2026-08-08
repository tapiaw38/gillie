import base64
import io
import requests
import zipfile
import re
import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from io import BytesIO
from PIL import Image
import xml.etree.ElementTree as ET

from src.core.platform.fileprocessor.processor import (
    BaseFileProcessor,
    ImageSearchResult,
)

logger = logging.getLogger(__name__)

WORD_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}


@dataclass
class DocxTextSearchMatch:
    """Result of a text search match in DOCX"""
    paragraph_number: int
    matched_text: str
    match_context: str
    confidence: float


@dataclass
class DocxSmartSearchResult:
    """Result of smart search in DOCX including text analysis and related images"""
    search_term: str
    processed_keywords: List[str]
    text_matches: List[DocxTextSearchMatch]
    related_images: List[ImageSearchResult]
    total_matches: int
    extraction_method: str


class DocxProcessor(BaseFileProcessor):
    """DOCX file processor that extracts text and embedded images"""

    def __init__(self, config_service):
        super().__init__(config_service)
        self.enable_fast_processing = True

    async def extract_text_from_docx(self, docx_url: str) -> str:
        """Extract all text from a DOCX file"""
        try:
            response = requests.get(docx_url)
            response.raise_for_status()
            docx_data = response.content
            return self._extract_text_from_bytes(docx_data)
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            return ""

    def _extract_text_from_bytes(self, docx_data: bytes) -> str:
        """Extract text from DOCX bytes"""
        try:
            with zipfile.ZipFile(BytesIO(docx_data), "r") as zf:
                if "word/document.xml" not in zf.namelist():
                    return ""
                xml_content = zf.read("word/document.xml")
                root = ET.fromstring(xml_content)
                paragraphs = []
                for para in root.iter(f"{{{WORD_NS['w']}}}p"):
                    texts = []
                    for text_elem in para.iter(f"{{{WORD_NS['w']}}}t"):
                        if text_elem.text:
                            texts.append(text_elem.text)
                    if texts:
                        paragraphs.append("".join(texts))
                return "\n".join(paragraphs)
        except Exception as e:
            logger.error(f"Error parsing DOCX XML: {e}")
            return ""

    def extract_text_for_evaluation(self, docx_data: bytes) -> str:
        """Extract DOCX text from already-downloaded bytes."""
        return self._extract_text_from_bytes(docx_data)

    async def search_images_in_docx(
        self, docx_url: str, search_term: str, max_results: int = 5
    ) -> List[ImageSearchResult]:
        """Search for embedded images in a DOCX file based on a search term"""
        try:
            response = requests.get(docx_url)
            response.raise_for_status()
            docx_data = response.content

            images_data = await self._extract_images_from_docx(docx_data)
            results = await self._search_relevant_images(images_data, search_term, max_results)
            return results
        except Exception as e:
            logger.error(f"Error processing DOCX file: {e}")
            return []

    async def _extract_images_from_docx(self, docx_data: bytes) -> List[Dict[str, Any]]:
        """Extract all embedded images from DOCX file"""
        images_data = []
        try:
            with zipfile.ZipFile(BytesIO(docx_data), "r") as zf:
                media_files = [f for f in zf.namelist() if f.startswith("word/media/")]
                for idx, media_file in enumerate(media_files):
                    try:
                        image_bytes = zf.read(media_file)
                        if self._is_valid_image(image_bytes):
                            image_base64 = base64.b64encode(image_bytes).decode()
                            images_data.append({
                                "page_number": idx + 1,
                                "image_base64": image_base64,
                                "extraction_method": "embedded_image",
                                "media_file": media_file,
                                "image_type": "embedded",
                            })
                    except Exception as e:
                        logger.error(f"Error extracting media file {media_file}: {e}")
                        continue
            return images_data
        except Exception as e:
            logger.error(f"Error extracting images from DOCX: {e}")
            return []

    def _is_valid_image(self, image_data: bytes) -> bool:
        """Check if the data represents a valid image"""
        signatures = [
            b"\xff\xd8\xff",  # JPEG
            b"\x89PNG\r\n\x1a\n",  # PNG
            b"GIF87a",
            b"GIF89a",
            b"BM",  # BMP
            b"RIFF",  # WEBP
        ]
        for sig in signatures:
            if image_data.startswith(sig):
                return True
        try:
            Image.open(BytesIO(image_data))
            return True
        except Exception:
            return False

    async def _search_relevant_images(
        self, images_data: List[Dict[str, Any]], search_term: str, max_results: int
    ) -> List[ImageSearchResult]:
        """Search for relevant images with ranking"""
        if not images_data:
            return []

        semaphore = asyncio.Semaphore(3)
        tasks = [
            self._analyze_image_relevance(semaphore, img, search_term)
            for img in images_data
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                continue
            if r and r.confidence > 0.3:
                valid_results.append(r)

        valid_results.sort(key=lambda x: -x.confidence)
        return valid_results[:max_results]

    async def _analyze_image_relevance(
        self, semaphore: asyncio.Semaphore, img_data: Dict[str, Any], search_term: str
    ) -> Optional[ImageSearchResult]:
        """Analyze image relevance to search term"""
        async with semaphore:
            try:
                analysis = self._analyze_image_with_python_tools(img_data["image_base64"])
                score = self._calculate_relevance_score_optimized(analysis, search_term, img_data)
                if score > 0.3:
                    desc = self._create_description_from_analysis(analysis, search_term, "DOCX document")
                    return ImageSearchResult(
                        page_number=img_data["page_number"],
                        sheet_name=None,
                        image_base64=img_data["image_base64"],
                        description=desc,
                        confidence=score,
                    )
                return None
            except Exception as e:
                logger.error(f"Error analyzing image relevance: {e}")
                return None

    async def smart_search_with_text_analysis(
        self, docx_url: str, search_phrase: str, max_results: int = 10
    ) -> DocxSmartSearchResult:
        """Smart search in DOCX: text + related images"""
        try:
            logger.info(f"Starting smart search in DOCX for: '{search_phrase}'")

            keywords = self._extract_keywords_from_phrase_common(search_phrase)
            logger.info(f"Extracted keywords: {keywords}")

            response = requests.get(docx_url)
            response.raise_for_status()
            docx_data = response.content

            full_text = self._extract_text_from_bytes(docx_data)
            text_matches = self._find_text_matches(full_text, keywords, search_phrase)
            logger.info(f"Found {len(text_matches)} text matches")

            related_images = await self.search_images_in_docx(docx_url, search_phrase, max_results)
            logger.info(f"Found {len(related_images)} related images")

            if text_matches:
                for img in related_images:
                    img.confidence = min(1.0, img.confidence + 0.2)

            return DocxSmartSearchResult(
                search_term=search_phrase,
                processed_keywords=keywords,
                text_matches=text_matches,
                related_images=related_images,
                total_matches=len(text_matches),
                extraction_method="docx_comprehensive",
            )
        except Exception as e:
            logger.error(f"Error in smart DOCX search: {e}")
            return DocxSmartSearchResult(
                search_term=search_phrase,
                processed_keywords=[],
                text_matches=[],
                related_images=[],
                total_matches=0,
                extraction_method="error",
            )

    def _find_text_matches(
        self, text: str, keywords: List[str], original_phrase: str
    ) -> List[DocxTextSearchMatch]:
        """Find text matches using regex"""
        matches = []
        paragraphs = text.split("\n")
        text_lower = text.lower()

        # Exact phrase match
        phrase_pattern = re.escape(original_phrase.lower())
        for match in re.finditer(phrase_pattern, text_lower):
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].strip()
            para_num = text[:match.start()].count("\n") + 1
            matches.append(DocxTextSearchMatch(
                paragraph_number=para_num,
                matched_text=original_phrase,
                match_context=context,
                confidence=1.0,
            ))

        # Keyword matches
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            for match in re.finditer(pattern, text_lower):
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()
                para_num = text[:match.start()].count("\n") + 1
                confidence = min(0.8, 0.4 + len(keyword) * 0.1)
                matches.append(DocxTextSearchMatch(
                    paragraph_number=para_num,
                    matched_text=keyword,
                    match_context=context,
                    confidence=confidence,
                ))

        # Deduplicate
        seen = set()
        unique = []
        for m in sorted(matches, key=lambda x: -x.confidence):
            key = (m.paragraph_number, m.matched_text.lower())
            if key not in seen:
                unique.append(m)
                seen.add(key)

        return unique[:20]

    async def analyze_docx_data(self, docx_url: str) -> Dict[str, Any]:
        """Analyze DOCX file structure and content"""
        try:
            response = requests.get(docx_url)
            response.raise_for_status()
            docx_data = response.content

            text = self._extract_text_from_bytes(docx_data)
            paragraphs = [p for p in text.split("\n") if p.strip()]
            word_count = len(text.split())

            with zipfile.ZipFile(BytesIO(docx_data), "r") as zf:
                media_files = [f for f in zf.namelist() if f.startswith("word/media/")]
                image_count = len(media_files)

            return {
                "paragraph_count": len(paragraphs),
                "word_count": word_count,
                "character_count": len(text),
                "image_count": image_count,
                "has_images": image_count > 0,
                "preview": text[:500] if text else "",
            }
        except Exception as e:
            return {"error": f"Error analyzing DOCX: {e}"}
