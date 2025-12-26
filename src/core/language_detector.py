"""
Módulo de detecção de idioma e gerenciamento de modelos spaCy por idioma.

Detecta automaticamente o idioma do texto e carrega o modelo spaCy apropriado
para chunking mais preciso de documentos multilíngues.
"""
import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Flag de disponibilidade do langdetect
LANGDETECT_AVAILABLE = False

try:
    from langdetect import detect, DetectorFactory
    # Seed para resultados consistentes
    DetectorFactory.seed = 42
    LANGDETECT_AVAILABLE = True
    logger.info("langdetect disponível para detecção automática de idioma")
except ImportError:
    logger.warning(
        "langdetect não instalado. "
        "Usando português como fallback. "
        "Instale com: pip install langdetect"
    )


# Mapeamento de códigos de idioma para modelos spaCy
LANGUAGE_MODELS = {
    'pt': 'pt',  # Português
    'en': 'en',  # Inglês
    'es': 'es',  # Espanhol
    'de': 'de',  # Alemão
    'fr': 'fr',  # Francês
    'it': 'it',  # Italiano
}

# Idioma padrão
DEFAULT_LANGUAGE = 'pt'

# Cache de modelos spaCy carregados
_nlp_models = {}


def detect_language(text: str, sample_size: int = 1000) -> str:
    """
    Detecta o idioma do texto.
    
    Args:
        text: Texto para detectar idioma
        sample_size: Número de caracteres a usar para detecção (para textos longos)
        
    Returns:
        Código do idioma (ex: 'pt', 'en', 'es')
    """
    if not LANGDETECT_AVAILABLE:
        return DEFAULT_LANGUAGE
    
    if not text or len(text.strip()) < 20:
        # Texto muito curto para detecção confiável
        return DEFAULT_LANGUAGE
    
    try:
        # Usar amostra do texto para detecção (mais rápido)
        sample = text[:sample_size] if len(text) > sample_size else text
        detected = detect(sample)
        
        # Verificar se temos suporte para este idioma
        if detected in LANGUAGE_MODELS:
            logger.debug(f"Idioma detectado: {detected}")
            return detected
        else:
            logger.debug(f"Idioma detectado ({detected}) não suportado, usando {DEFAULT_LANGUAGE}")
            return DEFAULT_LANGUAGE
            
    except Exception as e:
        logger.warning(f"Erro na detecção de idioma: {e}. Usando {DEFAULT_LANGUAGE}")
        return DEFAULT_LANGUAGE


@lru_cache(maxsize=10)
def _load_spacy_model(language: str):
    """
    Carrega modelo spaCy para um idioma (com cache).
    
    Args:
        language: Código do idioma
        
    Returns:
        Modelo spaCy carregado com sentencizer
    """
    try:
        import spacy
        
        # Usar modelo em branco (mais leve) com sentencizer
        nlp = spacy.blank(language)
        nlp.add_pipe("sentencizer")
        
        logger.info(f"spaCy modelo '{language}' carregado com sucesso")
        return nlp
        
    except Exception as e:
        logger.warning(f"Erro ao carregar spaCy para '{language}': {e}")
        
        # Fallback para português se falhar
        if language != DEFAULT_LANGUAGE:
            logger.info(f"Usando fallback para {DEFAULT_LANGUAGE}")
            return _load_spacy_model(DEFAULT_LANGUAGE)
        
        return None


def get_nlp_for_text(text: str) -> tuple:
    """
    Detecta idioma do texto e retorna modelo spaCy apropriado.
    
    Args:
        text: Texto para processar
        
    Returns:
        Tupla (modelo_nlp, idioma_detectado)
    """
    language = detect_language(text)
    nlp = _load_spacy_model(language)
    return nlp, language


def get_nlp_for_language(language: str):
    """
    Retorna modelo spaCy para um idioma específico.
    
    Args:
        language: Código do idioma (ex: 'pt', 'en', 'es')
        
    Returns:
        Modelo spaCy carregado
    """
    if language not in LANGUAGE_MODELS:
        language = DEFAULT_LANGUAGE
    
    return _load_spacy_model(language)


def get_supported_languages() -> dict:
    """
    Retorna idiomas suportados.
    
    Returns:
        Dict com códigos de idioma e descrições
    """
    return {
        'pt': 'Português',
        'en': 'English',
        'es': 'Español',
        'de': 'Deutsch',
        'fr': 'Français',
        'it': 'Italiano',
    }


def check_language_detection_status() -> dict:
    """
    Verifica status do módulo de detecção de idioma.
    
    Returns:
        Dict com status das funcionalidades
    """
    return {
        "langdetect_available": LANGDETECT_AVAILABLE,
        "default_language": DEFAULT_LANGUAGE,
        "supported_languages": list(LANGUAGE_MODELS.keys()),
        "cached_models": list(_load_spacy_model.cache_info()._asdict().items())
    }
