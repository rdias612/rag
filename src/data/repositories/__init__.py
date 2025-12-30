"""
Repositories para acesso a dados.

Este módulo exporta todos os repositories disponíveis.
"""
from .base import BaseRepository
from .document_repository import DocumentRepository
from .prompt_repository import PromptRepository, CRITICAL_CATEGORIES
from .ingestion_repository import IngestionRepository
from .feedback_repository import FeedbackRepository

__all__ = [
    "BaseRepository",
    "DocumentRepository",
    "PromptRepository",
    "IngestionRepository",
    "FeedbackRepository",
    "CRITICAL_CATEGORIES"
]
