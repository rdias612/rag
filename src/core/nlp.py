"""
Módulo centralizado de processamento de linguagem natural (NLP).
Gerencia instâncias spaCy, tokenização e segmentação de sentenças de forma unificada e eficiente.
"""
import re
from functools import lru_cache
from typing import List, Optional, Tuple

from src.core.logger import get_logger

logger = get_logger("core.nlp")

# Tentativa de carregar spaCy
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy não instalado. Fallback para regex ativado.")


class NLPManager:
    """
    Gerenciador singleton de pipelines NLP para o sistema RAG.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NLPManager, cls).__new__(cls)
            cls._instance._models = {}
        return cls._instance

    def get_pipeline(self, language: str = "pt", full_model: bool = False):
        """
        Retorna o pipeline spaCy para o idioma solicitado.
        
        Args:
            language: Código do idioma ('pt', 'en', 'es', etc.)
            full_model: Se True, tenta carregar o modelo completo; se False, usa blank com sentencizer (muito mais rápido)
        """
        if not SPACY_AVAILABLE:
            return None

        cache_key = f"{language}_{'full' if full_model else 'blank'}"
        if cache_key in self._models:
            return self._models[cache_key]

        nlp = None
        if full_model:
            model_names = {
                'pt': ['pt_core_news_sm', 'pt_core_news_md'],
                'en': ['en_core_web_sm'],
                'es': ['es_core_news_sm']
            }
            for model_name in model_names.get(language, []):
                try:
                    nlp = spacy.load(model_name)
                    logger.info("spaCy full model '%s' carregado com sucesso.", model_name)
                    break
                except Exception:
                    continue

        if nlp is None:
            try:
                nlp = spacy.blank(language)
                nlp.add_pipe("sentencizer")
                nlp.max_length = 50000000
                logger.debug("spaCy blank model com sentencizer carregado para '%s'.", language)
            except Exception as e:
                logger.warning("Falha ao carregar spaCy para idioma '%s': %s", language, e)
                return None

        self._models[cache_key] = nlp
        return nlp

    def split_into_sentences(self, text: str, language: str = "pt") -> List[str]:
        """
        Divide um texto em sentenças respeitando regras linguísticas.
        """
        if not text or not text.strip():
            return []

        nlp = self.get_pipeline(language=language)
        if nlp is not None:
            try:
                doc = nlp(text)
                sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
                if sentences:
                    return sentences
            except Exception as e:
                logger.debug("Erro na segmentação com spaCy, usando regex: %s", e)

        return self._split_into_sentences_regex(text)

    @staticmethod
    def _split_into_sentences_regex(text: str) -> List[str]:
        """Fallback via expressão regular para segmentação de sentenças."""
        sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z\u00C0-\u00DC])')
        sentences = sentence_endings.split(text)
        cleaned = [s.strip() for s in sentences if s.strip()]
        
        if len(cleaned) <= 1 and len(text) > 200:
            cleaned = [s.strip() + '.' for s in text.split('.') if s.strip()]
            
        return cleaned


# Instância global
nlp_manager = NLPManager()


def split_sentences(text: str, language: str = "pt") -> List[str]:
    """Helper global para segmentação de sentenças."""
    return nlp_manager.split_into_sentences(text, language)
