"""
Repositories para acesso a dados.

Este módulo exporta todos os repositories disponíveis.
"""
from .base import BaseRepository
from .document_repository import DocumentRepository
from .prompt_repository import PromptRepository, CRITICAL_CATEGORIES
from .ingestion_repository import IngestionRepository
from .feedback_repository import FeedbackRepository
from .question_type_instruction_repository import QuestionTypeInstructionRepository, _question_type_instruction_repo

__all__ = [
    "BaseRepository",
    "DocumentRepository",
    "PromptRepository",
    "IngestionRepository",
    "FeedbackRepository",
    "CRITICAL_CATEGORIES",
    "QuestionTypeInstructionRepository",
    "_question_type_instruction_repo"
]
