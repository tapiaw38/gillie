"""
Image Processing Service

This service handles image search and processing operations,
following the Single Responsibility Principle by focusing
solely on image-related concerns.

Responsibilities:
- Search for relevant images in user files
- Generate image search keywords using AI
- Filter images by confidence threshold
- Format images for chat responses
"""

import logging
from typing import List, Optional
from src.core.platform.fileprocessor.processor import ImageSearchResult
from src.adapters.web.utils.image_formatter import format_images_for_chat_response

logger = logging.getLogger(__name__)

# Module-level constants
IMAGE_CONFIDENCE_THRESHOLD = 0.3
MAX_IMAGES_TO_SHOW = 3
ENABLE_FAST_IMAGE_PROCESSING = True


class ImageProcessingService:
    """
    Service for searching and processing images from user files.

    This service encapsulates all image processing logic, making it
    reusable and testable independently of use cases.
    """

    def __init__(self, openai_integration):
        """
        Initialize the image processing service.

        Args:
            openai_integration: OpenAI integration instance for image search
        """
        self.openai_integration = openai_integration

    async def search_and_format_images(
        self,
        user_message: str,
        profile,
        message_context: Optional[str] = None,
        conversation_history: Optional[str] = None,
        max_images: int = MAX_IMAGES_TO_SHOW,
        confidence_threshold: float = IMAGE_CONFIDENCE_THRESHOLD
    ) -> Optional[str]:
        """
        Searches for relevant images and formats them for chat response.

        This method orchestrates the complete image processing workflow:
        1. Generate optimal search keyword using AI
        2. Search for images in user files
        3. Filter by confidence threshold
        4. Format for chat response

        Args:
            user_message: The user's message content
            profile: User profile with files
            message_context: Optional message context
            conversation_history: Optional conversation history
            max_images: Maximum number of images to show
            confidence_threshold: Minimum confidence score for images

        Returns:
            Formatted images string or None if no images found
        """
        try:
            # Generate optimal search keyword
            search_keyword = await self._generate_image_search_keyword(
                user_message=user_message,
                profile=profile,
                message_context=message_context,
                conversation_history=conversation_history
            )

            logger.info(f"Generated image search keyword: '{search_keyword}'")

            # Search for images
            images = await self._search_images(
                keyword=search_keyword,
                profile=profile,
                max_results=max_images
            )

            if not images:
                logger.info("No images found for the search keyword")
                return None

            # Filter by confidence
            filtered_images = self._filter_by_confidence(
                images=images,
                threshold=confidence_threshold
            )

            if not filtered_images:
                logger.info("No images passed confidence threshold")
                return None

            # Format for chat response
            formatted_images = self._format_images(
                images=filtered_images,
                search_term=search_keyword,
                max_images_to_show=max_images
            )

            return formatted_images

        except Exception as e:
            logger.error(f"Error in image search and format process: {e}")
            return None

    async def _generate_image_search_keyword(
        self,
        user_message: str,
        profile,
        message_context: Optional[str],
        conversation_history: Optional[str]
    ) -> str:
        """
        Generates an optimal keyword for image search using AI.

        Args:
            user_message: The user's message
            profile: User profile
            message_context: Optional message context
            conversation_history: Optional conversation history

        Returns:
            Generated search keyword
        """
        try:
            keyword_prompt = (
                "Given the following user message, what is the best single keyword "
                "or phrase to use to search for relevant images in the user's files? "
                "Respond ONLY with the keyword or phrase, no explanation.\n\n"
                f"User message: {user_message}"
            )

            search_keyword = await self.openai_integration.ask(
                keyword_prompt,
                message_context,
                conversation_history,
                profile
            )

            return search_keyword.strip()

        except Exception as e:
            logger.error(f"Error generating search keyword, using original message: {e}")
            return user_message

    async def _search_images(
        self,
        keyword: str,
        profile,
        max_results: int
    ) -> List[ImageSearchResult]:
        """
        Searches for images in user's files using the keyword.

        Args:
            keyword: Search keyword
            profile: User profile with files
            max_results: Maximum number of results to return

        Returns:
            List of image search results
        """
        try:
            # Optimize for fast processing if enabled
            if ENABLE_FAST_IMAGE_PROCESSING:
                logger.info("Using optimized fast image processing mode")
                max_results = min(max_results, 2)

            images = await self.openai_integration.search_images_in_files(
                keyword,
                profile,
                max_results
            )

            logger.info(f"Found {len(images)} images for keyword: '{keyword}'")
            return images

        except Exception as e:
            logger.error(f"Error searching images: {e}")
            return []

    def _filter_by_confidence(
        self,
        images: List[ImageSearchResult],
        threshold: float
    ) -> List[ImageSearchResult]:
        """
        Filters images by confidence threshold.

        Args:
            images: List of image search results
            threshold: Minimum confidence score

        Returns:
            Filtered list of images
        """
        filtered = [
            img for img in images
            if getattr(img, "confidence", 1.0) >= threshold
        ]

        logger.info(
            f"Filtered {len(images)} images to {len(filtered)} "
            f"using threshold {threshold}"
        )

        return filtered

    def _format_images(
        self,
        images: List[ImageSearchResult],
        search_term: str,
        max_images_to_show: int
    ) -> str:
        """
        Formats images for chat response using the formatter utility.

        Args:
            images: List of image search results
            search_term: Search term used
            max_images_to_show: Maximum number of images to display

        Returns:
            Formatted images string
        """
        return format_images_for_chat_response(
            images=images,
            search_term=search_term,
            max_images_to_show=max_images_to_show,
            max_width=250
        )
