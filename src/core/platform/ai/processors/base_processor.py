"""
Base Processor Interface

This module defines the abstract base class for all document processors,
following the Strategy Pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ProcessingMethod(Enum):
    """Available processing methods"""
    TEXT_EXTRACTION = "text_extraction"
    OCR = "ocr"
    LANGCHAIN = "langchain"
    RAG = "rag"
    HYBRID = "hybrid"


@dataclass
class ProcessingResult:
    """Standardized result from document processing"""
    success: bool
    method: ProcessingMethod
    extracted_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    chunks: Optional[List[str]] = None
    error: Optional[str] = None
    document_id: Optional[str] = None


class BaseDocumentProcessor(ABC):
    """
    Abstract base class for document processors.

    All processors (PDF, Excel, Image, etc.) must implement this interface.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the processor with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config

    @abstractmethod
    async def process(
        self,
        file_url: str,
        **kwargs
    ) -> ProcessingResult:
        """
        Process a document from URL.

        Args:
            file_url: URL of the document to process
            **kwargs: Additional processing options

        Returns:
            ProcessingResult with extracted content and metadata
        """
        pass

    @abstractmethod
    def supports_file_type(self, file_path: str) -> bool:
        """
        Check if this processor supports the given file type.

        Args:
            file_path: Path or URL to the file

        Returns:
            True if supported, False otherwise
        """
        pass

    def get_processor_info(self) -> Dict[str, Any]:
        """
        Get information about this processor.

        Returns:
            Dictionary with processor information
        """
        return {
            "name": self.__class__.__name__,
            "config": self.config
        }


class ProcessorError(Exception):
    """Base exception for processor errors"""
    pass
