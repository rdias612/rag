"""
Módulo de detecção de idioma e integração com NLPManager.

Detecta automaticamente o idioma do texto e delega para o NLPManager
o fornecimento de pipelines spaCy apropriados para documentos multilíngues.
"""
from typing import Optional, Tuple
from src.core.logger import get_logger
from src.core.nlp import nlp_manager

logger = get_logger("core.language_detector")

# Flag de disponibilidade do langdetect
LANGDETECT_AVAILABLE = False

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 42
    LANGDETECT_AVAILABLE = True
    logger.debug("langdetect disponível para detecção automática de idioma")
except ImportError:
    logger.warning("langdetect não instalado. Usando português como fallback padrão.")

# Mapeamento de códigos de idioma suportados
LANGUAGE_MODELS = {
    'pt': 'Português',
    'en': 'English',
    'es': 'Español',
    'de': 'Deutsch',
    'fr': 'Français',
    'it': 'Italiano',
}

DEFAULT_LANGUAGE = 'pt'


def detect_language(text: str, sample_size: int = 1000) -> str:
    """
    Detecta o idioma do texto.
    
    Args:
        text: Texto para detectar idioma
        sample_size: Número de caracteres a usar para detecção
        
    Returns:
        Código do idioma (ex: 'pt', 'en', 'es')
    """
    if not LANGDETECT_AVAILABLE:
        return DEFAULT_LANGUAGE
    
    if not text or len(text.strip()) < 20:
        return DEFAULT_LANGUAGE
    
    try:
        sample = text[:sample_size] if len(text) > sample_size else text
        detected = detect(sample)
        
        if detected in LANGUAGE_MODELS:
            logger.debug("Idioma detectado: %s", detected)
            return detected
        else:
            logger.debug("Idioma detectado (%s) não suportado, usando %s", detected, DEFAULT_LANGUAGE)
            return DEFAULT_LANGUAGE
            
    except Exception as e:
        logger.debug("Erro na detecção de idioma: %s. Usando %s", e, DEFAULT_LANGUAGE)
        return DEFAULT_LANGUAGE


def get_nlp_for_language(language: str):
    """
    Retorna modelo spaCy para um idioma específico via NLPManager.
    """
    lang = language if language in LANGUAGE_MODELS else DEFAULT_LANGUAGE
    return nlp_manager.get_pipeline(lang)


def get_nlp_for_text(text: str) -> Tuple[any, str]:
    """
    Detecta idioma do texto e retorna modelo spaCy apropriado.
    """
    language = detect_language(text)
    nlp = get_nlp_for_language(language)
    return nlp, language


def get_supported_languages() -> dict:
    """Retorna idiomas suportados."""
    return LANGUAGE_MODELS.copy()


def check_language_detection_status() -> dict:
    """Verifica status do módulo de detecção de idioma."""
    return {
        "langdetect_available": LANGDETECT_AVAILABLE,
        "default_language": DEFAULT_LANGUAGE,
        "supported_languages": list(LANGUAGE_MODELS.keys())
    }
