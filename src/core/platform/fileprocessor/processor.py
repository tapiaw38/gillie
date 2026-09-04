import base64
import io
import requests
import logging
from typing import List, Dict, Optional, Any, Tuple
from PIL import Image, ImageEnhance, ImageFilter
from src.core.platform.config.service import ConfigurationService
from openai import AsyncOpenAI
import asyncio
from dataclasses import dataclass
from collections import Counter
import re

try:
    import cv2
except ImportError:
    cv2 = None
import numpy as np
from io import BytesIO


logger = logging.getLogger(__name__)


@dataclass
class ImageSearchResult:
    page_number: int
    sheet_name: Optional[str]  # For Excel sheets
    image_base64: str
    description: str
    confidence: float
    bbox: Optional[Dict[str, float]] = None


@dataclass
class ProcessingResult:
    success: bool
    data: Any = None
    error: Optional[str] = None


class BaseFileProcessor:
    """Base class with common functionality for file processing"""

    _MULTILINGUAL_STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
        "with", "by", "from", "up", "about", "into", "through", "during", "before",
        "after", "above", "below", "between", "among", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "should", "could", "can", "may", "might", "must", "shall", "this",
        "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me",
        "him", "her", "us", "them", "my", "your", "his", "its", "our", "their", "if",
        "so", "as", "el", "la", "los", "las", "un", "una", "de", "del", "al", "en",
        "y", "que", "es", "se", "no", "te", "lo", "le", "da", "su", "por", "son",
        "con", "para", "sin", "pero", "sus", "como", "si", "ya", "mi", "tu", "todo",
        "todos", "toda", "todas", "mas", "más", "esta", "este", "estos", "estas",
    }

    def __init__(self, config_service: ConfigurationService):
        config = config_service.openai_config
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        vision_cfg = getattr(config_service, "vision_config", None)
        if vision_cfg and vision_cfg.api_key:
            self._vision_client = AsyncOpenAI(api_key=vision_cfg.api_key, base_url=vision_cfg.base_url)
            self._vision_model = vision_cfg.model
            self._vision_base_url = vision_cfg.base_url
            logger.info(
                "Vision configured: model=%s base_url=%s",
                self._vision_model,
                self._vision_base_url,
            )
        else:
            self._vision_client = None
            self._vision_model = None
            self._vision_base_url = ""
            logger.info("Vision not configured: using technical-only image analysis")

    def _extract_keywords_from_phrase_common(self, phrase: str) -> List[str]:
        """Extract unique keywords from a short search phrase."""
        try:
            cleaned_phrase = phrase.lower().strip()
            words = re.findall(
                r"\b[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ0-9]{2,}\b",
                cleaned_phrase,
                re.IGNORECASE,
            )

            keywords = []
            seen = set()
            for word in words:
                word_lower = word.lower()
                if (
                    word_lower not in self._MULTILINGUAL_STOPWORDS
                    and word_lower not in seen
                ):
                    keywords.append(word)
                    seen.add(word_lower)

            return keywords or [phrase.strip()]
        except Exception:
            return [phrase.strip()]

    def _extract_keywords_from_text_common(
        self, text: str, min_word_length: int = 4, max_keywords: int = 10
    ) -> List[str]:
        """Extract the most frequent keywords from longer text."""
        try:
            words = re.findall(
                r"\b[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{3,}\b",
                text.lower(),
            )
            keywords = [
                word
                for word in words
                if word not in self._MULTILINGUAL_STOPWORDS
                and len(word) >= min_word_length
            ]
            word_counts = Counter(keywords)
            return [word for word, _ in word_counts.most_common(max_keywords)]
        except Exception:
            return []

    def _analyze_image_with_python_tools(self, image_base64: str) -> Dict[str, Any]:
        """Analyze image using Python tools (common for all processors)"""
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))

            img_array = np.array(image)

            analysis = {
                "dimensions": image.size,
                "mode": image.mode,
                "has_transparency": image.mode in ("RGBA", "LA")
                or "transparency" in image.info,
                "dominant_colors": self._get_dominant_colors(img_array),
                "color_names": self._get_color_names(img_array),
                "brightness": self._calculate_brightness(img_array),
                "contrast": self._calculate_contrast(img_array),
                "sharpness": self._calculate_sharpness(img_array),
                "text_detected": self._detect_text_regions(img_array),
                "ocr_text": self._extract_text_ocr(image),
                "faces_detected": self._detect_faces(img_array),
                "image_type": self._classify_image_type(img_array, image.size),
                "objects_detected": self._detect_objects(img_array),
                "quality_score": self._calculate_quality_score(img_array),
            }

            return analysis

        except Exception as e:
            return {"error": f"Error analyzing image: {str(e)}"}

    def _extract_text_ocr(self, image: "Image.Image") -> str:
        """Extract text from image using Tesseract OCR"""
        try:
            import pytesseract
            text = pytesseract.image_to_string(image, config="--psm 3").strip()
            # Clean up excessive whitespace
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            normalized = "\n".join(lines)
            return self._sanitize_ocr_text(normalized)
        except Exception:
            return ""

    def _sanitize_ocr_text(self, text: str, max_chars: int = 600) -> str:
        """Keep OCR text bounded and printable to prevent prompt/context blowups."""
        if not text:
            return ""

        cleaned = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\u024F]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) > max_chars:
            cleaned = f"{cleaned[:max_chars]} ...[truncated]"
        return cleaned

    def _truncate_text(self, text: str, max_chars: int = 800) -> str:
        """Bound free-form text to avoid oversized prompt/report payloads."""
        if not text:
            return ""
        compact = re.sub(r"\s+", " ", str(text)).strip()
        if len(compact) > max_chars:
            return f"{compact[:max_chars]} ...[truncated]"
        return compact

    def _detect_faces(self, img_array: np.ndarray) -> int:
        """Detect faces using OpenCV Haar cascades"""
        try:
            if cv2 is None:
                return 0
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if len(img_array.shape) == 3 else img_array
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            return len(faces) if len(faces) > 0 else 0
        except Exception:
            return 0

    def _get_color_names(self, img_array: np.ndarray) -> List[str]:
        """Convert dominant RGB colors to human-readable names"""
        _COLOR_MAP = [
            ((255, 0, 0), "red"), ((0, 255, 0), "green"), ((0, 0, 255), "blue"),
            ((255, 255, 0), "yellow"), ((0, 255, 255), "cyan"), ((255, 0, 255), "magenta"),
            ((255, 165, 0), "orange"), ((128, 0, 128), "purple"), ((255, 192, 203), "pink"),
            ((165, 42, 42), "brown"), ((0, 0, 0), "black"), ((255, 255, 255), "white"),
            ((128, 128, 128), "gray"), ((0, 128, 128), "teal"), ((0, 0, 128), "navy"),
            ((255, 215, 0), "gold"), ((192, 192, 192), "silver"), ((245, 245, 220), "beige"),
        ]
        try:
            colors = self._get_dominant_colors(img_array)
            names = []
            for rgb in colors[:3]:
                if len(rgb) < 3:
                    continue
                best_name, best_dist = "unknown", float("inf")
                for ref_rgb, name in _COLOR_MAP:
                    dist = sum((a - b) ** 2 for a, b in zip(rgb[:3], ref_rgb)) ** 0.5
                    if dist < best_dist:
                        best_dist, best_name = dist, name
                if best_name not in names:
                    names.append(best_name)
            return names
        except Exception:
            return []

    def _classify_image_type(self, img_array: np.ndarray, size: tuple) -> str:
        """Heuristically classify the type of image"""
        try:
            w, h = size
            aspect = w / h if h > 0 else 1.0

            # Edge density as proxy for screenshot vs photo
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if cv2 and len(img_array.shape) == 3 else None
            edge_density = 0.0
            if gray is not None and cv2:
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size

            # Unique color count
            if len(img_array.shape) == 3:
                flat = img_array[:, :, :3].reshape(-1, 3)
                sample = flat[::max(1, len(flat) // 5000)]
                unique_colors = len(np.unique(sample, axis=0))
            else:
                unique_colors = len(np.unique(img_array))

            if edge_density > 0.12 and unique_colors < 500:
                return "diagram or chart"
            if edge_density > 0.08 and aspect > 1.2:
                return "screenshot or document"
            if unique_colors > 5000 and edge_density < 0.08:
                return "photograph"
            if aspect < 0.6:
                return "portrait photo"
            if aspect > 2.0:
                return "banner or panoramic image"
            return "image"
        except Exception:
            return "image"

    def _get_dominant_colors(self, img_array: np.ndarray) -> List[List[int]]:
        """Get dominant colors from image"""
        try:
            pixels = (
                img_array.reshape(-1, 3)
                if len(img_array.shape) == 3
                else img_array.reshape(-1, 1)
            )

            try:
                from sklearn.cluster import KMeans

                sample_size = min(1000, len(pixels))
                sample_pixels = pixels[:: len(pixels) // sample_size]
                kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
                kmeans.fit(sample_pixels)
                colors = kmeans.cluster_centers_.astype(int)
                return colors.tolist()
            except ImportError:
                return self._get_dominant_colors_fallback(img_array)
        except Exception:
            return []

    def _get_dominant_colors_fallback(self, img_array: np.ndarray) -> List[List[int]]:
        """Alternative method to get dominant colors without sklearn"""
        try:
            if isinstance(img_array, np.ndarray):
                if len(img_array.shape) == 3:
                    image = Image.fromarray(img_array)
                else:
                    image = Image.fromarray(img_array, mode="L")
            else:
                image = img_array

            image_reduced = image.quantize(colors=5)
            palette = image_reduced.getpalette()

            colors = []
            for i in range(5):
                color = palette[i * 3 : (i + 1) * 3]
                colors.append(color)

            return colors
        except Exception:
            return []

    def _calculate_brightness(self, img_array: np.ndarray) -> float:
        """Calculate average brightness of an image"""
        try:
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            return float(np.mean(gray))
        except Exception:
            if len(img_array.shape) == 3:
                gray = np.dot(img_array[..., :3], [0.2989, 0.5870, 0.1140])
            else:
                gray = img_array
            return float(np.mean(gray))

    def _calculate_contrast(self, img_array: np.ndarray) -> float:
        """Calculate contrast of an image"""
        try:
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            return float(np.std(gray))
        except Exception:
            if len(img_array.shape) == 3:
                gray = np.dot(img_array[..., :3], [0.2989, 0.5870, 0.1140])
            else:
                gray = img_array
            return float(np.std(gray))

    def _calculate_sharpness(self, img_array: np.ndarray) -> float:
        """Calculate sharpness of an image using Laplacian operator"""
        try:
            if len(img_array.shape) == 3:
                gray = (
                    cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    if cv2 is not None
                    else np.dot(img_array[..., :3], [0.2989, 0.5870, 0.1140])
                )
            else:
                gray = img_array

            if cv2 is not None:
                return float(cv2.Laplacian(gray, cv2.CV_64F).var())

            gradient_y, gradient_x = np.gradient(gray.astype(float))
            return float(np.var(gradient_x) + np.var(gradient_y))
        except Exception:
            return 0.0

    def _detect_text_regions(self, img_array: np.ndarray) -> bool:
        """Detect if there are text regions in the image"""
        try:
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            text_contours = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if 100 < area < 10000:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h
                    if 0.5 < aspect_ratio < 5:
                        text_contours += 1

            return text_contours > 5
        except Exception:
            return False

    def _detect_objects(self, img_array: np.ndarray) -> int:
        """Detect approximate number of objects in the image"""
        try:
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            significant_contours = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:
                    significant_contours += 1

            return significant_contours
        except Exception:
            return 0

    def _calculate_quality_score(self, img_array: np.ndarray) -> float:
        """Calculate image quality score based on various factors"""
        try:
            brightness = self._calculate_brightness(img_array)
            contrast = self._calculate_contrast(img_array)
            sharpness = self._calculate_sharpness(img_array)

            brightness_score = 1.0 - abs(brightness - 127.5) / 127.5
            contrast_score = min(contrast / 50.0, 1.0)
            sharpness_score = min(sharpness / 1000.0, 1.0)

            quality_score = (brightness_score + contrast_score + sharpness_score) / 3.0
            return float(quality_score)
        except Exception:
            return 0.5

    def _calculate_relevance_score(
        self, analysis: Dict[str, Any], search_term: str
    ) -> float:
        """Calculate relevance score based on technical characteristics"""
        try:
            base_score = 0.0

            quality_score = analysis.get("quality_score", 0.0)
            if quality_score > 0.8:
                base_score += 0.35  # High quality images are more relevant
            elif quality_score > 0.6:
                base_score += 0.25
            elif quality_score > 0.4:
                base_score += 0.15
            elif quality_score > 0.2:
                base_score += 0.05

            objects_detected = analysis.get("objects_detected", 0)
            if objects_detected > 5:
                base_score += 0.40  # Many objects = complex, detailed content
            elif objects_detected > 3:
                base_score += 0.30
            elif objects_detected > 1:
                base_score += 0.20
            elif objects_detected > 0:
                base_score += 0.10

            if analysis.get("text_detected", False):
                base_score += 0.15

            dominant_colors = analysis.get("dominant_colors", [])
            if len(dominant_colors) > 4:
                base_score += 0.20
            elif len(dominant_colors) > 2:
                base_score += 0.15
            elif len(dominant_colors) > 1:
                base_score += 0.10

            search_term_lower = search_term.lower()

            if search_term_lower in ["product", "item", "article", "object"]:
                if objects_detected > 0:
                    base_score += 0.30

            elif search_term_lower in [
                "chart",
                "graph",
                "table",
                "diagram",
                "visualization",
            ]:
                if objects_detected > 0:
                    base_score += 0.25
                if analysis.get("text_detected", False):
                    base_score += 0.15

            elif search_term_lower in ["image", "photo", "picture", "illustration"]:
                base_score += 0.20
                if quality_score > 0.6:
                    base_score += 0.15

            dimensions = analysis.get("dimensions", (0, 0))
            if dimensions[0] > 0 and dimensions[1] > 0:
                pixel_count = dimensions[0] * dimensions[1]
                if pixel_count > 500000:  # High resolution
                    base_score += 0.10
                elif pixel_count > 100000:  # Medium resolution
                    base_score += 0.05

            if quality_score < 0.1:
                base_score *= 0.3
            elif quality_score < 0.2:
                base_score *= 0.6

            return min(max(base_score, 0.0), 1.0)

        except Exception as e:
            print(f"Error calculating relevance: {e}")
            return 0.0

    def _calculate_relevance_score_optimized(
        self,
        analysis: Dict[str, Any],
        search_term: str,
        img_data: Dict[str, Any] = None,
    ) -> float:
        """
        Optimized relevance calculation that avoids API calls and uses only local analysis
        """
        try:
            search_term_lower = search_term.lower()
            base_score = 0.0

            if analysis.get("text_detected", False):
                base_score += 0.2

            quality_score = analysis.get("quality_score", 0)
            if quality_score > 0.7:
                base_score += 0.15
            elif quality_score > 0.5:
                base_score += 0.1

            objects_detected = analysis.get("objects_detected", 0)
            if objects_detected > 0:
                base_score += min(objects_detected * 0.1, 0.2)

            dimensions = analysis.get("dimensions", (0, 0))
            if dimensions[0] > 300 and dimensions[1] > 300:  # Reasonable size
                base_score += 0.1

            brightness = analysis.get("brightness", 0)
            contrast = analysis.get("contrast", 0)
            if 0.3 < brightness < 0.8 and contrast > 30:
                base_score += 0.1

            image_keywords = [
                "chart",
                "graph",
                "image",
                "picture",
                "photo",
                "diagram",
                "illustration",
                "logo",
                "product",
                "item",
                "data",
                "analysis",
            ]

            for keyword in image_keywords:
                if keyword in search_term_lower:
                    base_score += 0.15
                    break

            if img_data:
                sheet_name = img_data.get("sheet_name", "").lower()
                page_info = img_data.get("page_number", 1)

                if page_info == 1:
                    base_score += 0.1

                if search_term_lower in sheet_name:
                    base_score += 0.2

            base_score += 0.3

            final_score = min(base_score, 1.0)

            return final_score

        except Exception as e:
            return 0.5

    def _describe_colors(self, colors: List[List[int]]) -> str:
        """Describe colors in a user-friendly way"""
        try:
            color_names = []
            for color in colors[:3]:
                r, g, b = color[:3]

                if r > 200 and g > 200 and b > 200:
                    color_names.append("white")
                elif r < 50 and g < 50 and b < 50:
                    color_names.append("black")
                elif r > 200 and g < 100 and b < 100:
                    color_names.append("red")
                elif r < 100 and g > 200 and b < 100:
                    color_names.append("green")
                elif r < 100 and g < 100 and b > 200:
                    color_names.append("blue")
                elif r > 200 and g > 200 and b < 100:
                    color_names.append("yellow")
                else:
                    color_names.append("mixed color")

            return ", ".join(color_names)
        except Exception:
            return "varied colors"

    def _create_description_from_analysis(
        self, analysis: Dict[str, Any], search_term: str, context: str = ""
    ) -> str:
        """Create description based on technical analysis"""
        try:
            description_parts = []

            dimensions = analysis.get("dimensions", (0, 0))
            description_parts.append(f"Image of {dimensions[0]}x{dimensions[1]} pixels")

            quality_score = analysis.get("quality_score", 0.0)
            if quality_score > 0.8:
                description_parts.append("of high quality")
            elif quality_score > 0.6:
                description_parts.append("of good quality")
            elif quality_score > 0.4:
                description_parts.append("of medium quality")
            else:
                description_parts.append("of low quality")

            objects_detected = analysis.get("objects_detected", 0)
            if objects_detected > 3:
                description_parts.append(
                    f"with multiple detected objects ({objects_detected})"
                )
            elif objects_detected > 1:
                description_parts.append(f"with {objects_detected} detected objects")
            elif objects_detected == 1:
                description_parts.append("with one main object")

            dominant_colors = analysis.get("dominant_colors", [])
            if len(dominant_colors) > 0:
                color_description = self._describe_colors(dominant_colors)
                description_parts.append(
                    f"with predominant colors: {color_description}"
                )

            if analysis.get("text_detected", False):
                description_parts.append("containing text")

            if context:
                description_parts.append(f"from {context}")

            if objects_detected > 0:
                description_parts.append(
                    f"Content potentially related to {search_term}"
                )

            return ". ".join(description_parts).capitalize() + "."
        except Exception as e:
            return f"Technically analyzed image. Possible relation to {search_term}."

    async def describe_image(self, image_base64: str, prompt: str = None) -> str:
        python_analysis = self._analyze_image_with_python_tools(image_base64)

        if self._vision_client:
            try:
                logger.info(
                    "Vision describe_image call: model=%s base_url=%s prompt_provided=%s",
                    self._vision_model,
                    self._vision_base_url,
                    bool(prompt),
                )
                user_prompt = prompt or "Analyze this image."
                response = await self._vision_client.chat.completions.create(
                    model=self._vision_model,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                            },
                            {
                                "type": "text",
                                "text": (
                                    "Return grounded analysis only.\n"
                                    "Format:\n"
                                    "- observed_text: literal text visible in image (or 'none')\n"
                                    "- observed_objects: bullets with directly visible items\n"
                                    "- uncertainties: what is unclear/ambiguous\n"
                                    "- final_summary: concise summary without guessing identities, brands, songs, events, or people unless text in image confirms it\n\n"
                                    f"User focus: {user_prompt}"
                                )
                            }
                        ]
                    }],
                    max_tokens=300,
                )
                vision_text = self._truncate_text(response.choices[0].message.content, max_chars=700)
                return self._build_grounded_report(python_analysis, vision_text, vision_enabled=True)
            except Exception as e:
                logger.warning(
                    "Vision describe_image failed: model=%s base_url=%s error=%s",
                    self._vision_model,
                    self._vision_base_url,
                    e,
                )
                return self._build_grounded_report(
                    python_analysis,
                    self._truncate_text(f"Vision model error: {e}", max_chars=220),
                    vision_enabled=False,
                )

        logger.info("Vision describe_image fallback: technical-only mode")
        return self._build_grounded_report(python_analysis, None, vision_enabled=False)

    def _build_grounded_report(self, analysis: Dict[str, Any], vision_text: str = None, vision_enabled: bool = False) -> str:
        """Create strict, evidence-first image report."""
        dimensions = analysis.get("dimensions", (0, 0))
        ocr_text = self._sanitize_ocr_text((analysis.get("ocr_text") or "").strip())
        objects_detected = analysis.get("objects_detected", 0)
        faces_detected = analysis.get("faces_detected", 0)
        color_names = analysis.get("color_names", [])

        observed_text = ocr_text if ocr_text else "none"
        observed_objects = [
            f"estimated objects detected: {objects_detected}",
            f"faces detected: {faces_detected}",
            f"image dimensions: {dimensions[0]}x{dimensions[1]}",
        ]
        if color_names:
            observed_objects.append(f"main colors: {', '.join(color_names[:6])}")

        uncertainties = [
            "object detector and OCR are approximate",
            "semantic identity (brand/person/event) may be wrong without clear visible text",
        ]

        lines = [
            "Observed evidence:",
            f"- observed_text: {observed_text}",
            "- observed_objects:",
        ]
        lines.extend([f"  - {item}" for item in observed_objects])
        lines.append("- uncertainties:")
        lines.extend([f"  - {item}" for item in uncertainties])

        if vision_enabled and vision_text:
            lines.append("- final_summary:")
            lines.append(f"  {self._truncate_text(vision_text, max_chars=700)}")
        else:
            lines.append("- final_summary:")
            lines.append(
                "  Technical-only analysis provided. No strong semantic claims about brand/person/event are made."
            )

        return "\n".join(lines)

    def _create_detailed_description(self, analysis: Dict[str, Any]) -> str:
        """Create detailed description based on technical analysis"""
        try:
            parts = []

            dimensions = analysis.get("dimensions", (0, 0))
            parts.append(
                f"This is an image of {dimensions[0]} x {dimensions[1]} pixels"
            )

            quality_score = analysis.get("quality_score", 0.0)
            if quality_score > 0.8:
                parts.append("of excellent visual quality")
            elif quality_score > 0.6:
                parts.append("of good quality")
            elif quality_score > 0.4:
                parts.append("of medium quality")
            else:
                parts.append("of basic quality")

            objects_detected = analysis.get("objects_detected", 0)
            if objects_detected > 5:
                parts.append(
                    f"Multiple objects detected ({objects_detected}), suggesting a complex composition"
                )
            elif objects_detected > 2:
                parts.append(f"{objects_detected} main objects detected")
            elif objects_detected > 0:
                parts.append(f"{objects_detected} main object detected")
            else:
                parts.append("No clearly defined objects detected")

            if analysis.get("text_detected", False):
                parts.append("The image contains text or textual elements")

            dominant_colors = analysis.get("dominant_colors", [])
            if len(dominant_colors) > 0:
                color_description = self._describe_colors(dominant_colors)
                parts.append(f"The predominant colors are: {color_description}")

            return ". ".join(parts) + "."
        except Exception as e:
            return f"Technical image analysis available. Error in detailed description: {str(e)}"

    async def _enhance_description_with_ai(
        self, technical_description: str, analysis: Dict[str, Any], user_prompt: str = None
    ) -> str:
        """Enhance technical description using AI"""
        try:
            ocr_text = self._sanitize_ocr_text(analysis.get("ocr_text", ""))
            faces = analysis.get("faces_detected", 0)
            image_type = analysis.get("image_type", "image")
            color_names = analysis.get("color_names", [])

            ocr_section = f"\n- Extracted text (OCR): \"{ocr_text}\"" if ocr_text else ""
            faces_section = f"\n- Faces detected: {faces}" if faces > 0 else ""
            colors_section = f"\n- Main colors: {', '.join(color_names)}" if color_names else ""
            focus = f"\n\nQUESTION TO ANSWER: {user_prompt}" if user_prompt else ""

            prompt = f"""You are analyzing an image using technical data only. Describe only what data supports.

IMAGE TYPE: {image_type}
DIMENSIONS: {analysis.get('dimensions', 'N/A')}
QUALITY: {analysis.get('quality_score', 0):.0%}{ocr_section}{faces_section}{colors_section}
{focus}

Rules:
- If OCR text is present, it is the most important clue — use it to infer the image content
- If faces are detected, mention people are present
- Be direct and specific, not generic
- Do not guess identities (people, songs, brands, places) unless OCR explicitly shows them
- If evidence is insufficient, say uncertainty explicitly
- Max 150 words
"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"{technical_description}\n\n[Error enhancing description with AI: {str(e)}]"

    def enhance_image_quality(self, image_base64: str) -> str:
        """Enhance image quality using Python tools"""
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))

            enhanced = image

            enhancer = ImageEnhance.Brightness(enhanced)
            enhanced = enhancer.enhance(1.1)

            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(1.2)

            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(1.3)

            enhanced = enhanced.filter(ImageFilter.SMOOTH_MORE)

            buffered = io.BytesIO()
            enhanced.save(buffered, format="PNG")
            enhanced_base64 = base64.b64encode(buffered.getvalue()).decode()

            return enhanced_base64
        except Exception as e:
            print(f"Error enhancing image: {e}")
            return image_base64
