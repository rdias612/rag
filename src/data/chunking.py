"""
Módulo de chunking semântico para textos.

Utiliza spaCy para segmentação precisa de sentenças,
respeitando limites naturais do texto (parágrafos, pontuação).
"""
import re
from typing import List, Optional
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Importar detector de idioma
try:
    from src.core.language_detector import (
        detect_language,
        get_nlp_for_language,
        LANGDETECT_AVAILABLE,
        DEFAULT_LANGUAGE
    )
    LANGUAGE_DETECTION_AVAILABLE = True
except ImportError:
    LANGUAGE_DETECTION_AVAILABLE = False
    LANGDETECT_AVAILABLE = False
    DEFAULT_LANGUAGE = 'pt'
    logger.warning("language_detector não disponível")

# Tentar carregar spaCy
try:
    import spacy
    SPACY_AVAILABLE = True
    
    # Modelo padrão (português) para compatibilidade
    try:
        nlp = spacy.blank("pt")
        nlp.add_pipe("sentencizer")
        nlp.max_length = 50000000  # Aumentar para 50 milhões de caracteres
        logger.info("spaCy carregado com sucesso (sentencizer pt, max_length=50M)")
    except Exception as e:
        nlp = None
        logger.warning(f"Erro ao carregar spaCy padrão: {e}")
        
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None
    logger.warning("spaCy não instalado. Usando fallback com regex.")


class SemanticChunker:
    """
    Classe para chunking semântico de textos.
    
    Divide textos em chunks respeitando:
    - Limites de parágrafos
    - Limites de sentenças
    - Tamanho máximo configurável
    - Overlap por número de sentenças
    """
    
    def __init__(
        self,
        max_chunk_size: int = 800,
        min_chunk_size: int = 200,
        overlap_sentences: int = 1,
        language: str = "portuguese"
    ):
        """
        Inicializa o chunker semântico.
        
        Args:
            max_chunk_size: Tamanho máximo do chunk em caracteres
            min_chunk_size: Tamanho mínimo (evita chunks muito pequenos)
            overlap_sentences: Número de sentenças de overlap entre chunks
            language: Idioma do texto (para futuras expansões)
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_sentences = overlap_sentences
        self.language = language
        self._detected_language = None  # Cache do idioma detectado
        
        if not SPACY_AVAILABLE:
            logger.warning("Usando fallback regex para segmentação de sentenças")
    
    def chunk(self, text: str) -> List[str]:
        """
        Divide texto em chunks semânticos.
        
        Args:
            text: Texto a ser dividido
            
        Returns:
            Lista de chunks semanticamente coesos
        """
        if not text or not text.strip():
            return []
        
        # Normalizar espaços em branco
        text = self._normalize_whitespace(text)
        
        # Se texto é menor que o máximo, retornar como único chunk
        if len(text) <= self.max_chunk_size:
            return [text.strip()]
        
        # Se o texto for extremamente grande, dividir em blocos para não sobrecarregar o spaCy
        # (Embora nlp.max_length tenha aumentado, processar blocos de 1M é mais seguro)
        MAX_SPACY_BLOCK = 1000000
        if len(text) > MAX_SPACY_BLOCK:
            logger.info(f"Texto muito grande ({len(text)} chars). Dividindo em blocos de {MAX_SPACY_BLOCK} para processamento.")
            blocks = [text[i:i + MAX_SPACY_BLOCK] for i in range(0, len(text), MAX_SPACY_BLOCK)]
            all_chunks = []
            for block in blocks:
                all_chunks.extend(self.chunk(block))
            return all_chunks
        
        # Dividir em parágrafos primeiro
        paragraphs = self._split_into_paragraphs(text)
        
        # Processar cada parágrafo
        all_chunks = []
        current_chunk_sentences = []
        current_chunk_size = 0
        
        for paragraph in paragraphs:
            sentences = self._split_into_sentences(paragraph)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_size = len(sentence)
                
                # Se adicionar esta sentença exceder o limite
                if current_chunk_size + sentence_size > self.max_chunk_size and current_chunk_sentences:
                    # Salvar chunk atual
                    chunk_text = " ".join(current_chunk_sentences)
                    all_chunks.append(chunk_text)
                    
                    # Iniciar novo chunk com overlap
                    if self.overlap_sentences > 0 and len(current_chunk_sentences) >= self.overlap_sentences:
                        # Pegar as últimas N sentenças para overlap
                        overlap_sents = current_chunk_sentences[-self.overlap_sentences:]
                        current_chunk_sentences = overlap_sents.copy()
                        current_chunk_size = sum(len(s) for s in current_chunk_sentences) + len(current_chunk_sentences) - 1
                    else:
                        current_chunk_sentences = []
                        current_chunk_size = 0
                
                # Adicionar sentença ao chunk atual
                current_chunk_sentences.append(sentence)
                current_chunk_size += sentence_size + 1  # +1 para espaço
        
        # Adicionar último chunk se houver
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            all_chunks.append(chunk_text)
        
        # Mesclar chunks muito pequenos
        all_chunks = self._merge_small_chunks(all_chunks)
        
        return all_chunks
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normaliza espaços em branco no texto."""
        # Substituir múltiplos espaços por um único
        text = re.sub(r' +', ' ', text)
        # Normalizar quebras de linha
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Divide texto em parágrafos.
        
        Args:
            text: Texto a ser dividido
            
        Returns:
            Lista de parágrafos
        """
        # Dividir por linhas duplas (parágrafo)
        paragraphs = re.split(r'\n\n+', text)
        # Filtrar vazios e limpar
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Divide texto em sentenças usando spaCy ou fallback regex.
        
        Args:
            text: Texto a ser dividido
            
        Returns:
            Lista de sentenças
        """
        if SPACY_AVAILABLE and nlp is not None:
            return self._split_sentences_spacy(text)
        else:
            return self._split_sentences_regex(text)
    
    def _split_sentences_spacy(self, text: str) -> List[str]:
        """Divide sentenças usando spaCy com detecção de idioma."""
        # Detectar idioma se não foi detectado ainda
        if LANGUAGE_DETECTION_AVAILABLE and self._detected_language is None:
            self._detected_language = detect_language(text)
            logger.debug(f"Idioma detectado para chunking: {self._detected_language}")
        
        # Usar modelo do idioma detectado ou default
        if LANGUAGE_DETECTION_AVAILABLE and self._detected_language:
            current_nlp = get_nlp_for_language(self._detected_language)
        else:
            current_nlp = nlp
        
        if current_nlp is None:
            return self._split_sentences_regex(text)
        
        doc = current_nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    
    def _split_sentences_regex(self, text: str) -> List[str]:
        """
        Divide sentenças usando regex (fallback).
        
        Menos preciso que spaCy, mas funciona sem dependências.
        """
        # Padrão para fim de sentença: . ! ? seguido de espaço e maiúscula
        # Evita quebrar em abreviações comuns
        
        # Proteger abreviações comuns
        protected = text
        abbreviations = [
            r'Dr\.', r'Dra\.', r'Sr\.', r'Sra\.', r'Prof\.', 
            r'Fig\.', r'Tab\.', r'etc\.', r'Ex\.', r'vs\.',
            r'p\.', r'pp\.', r'vol\.', r'ed\.',
        ]
        
        for i, abbr in enumerate(abbreviations):
            protected = re.sub(abbr, f'__ABBR{i}__', protected, flags=re.IGNORECASE)
        
        # Dividir por pontuação final
        # Padrão: ponto/interrogação/exclamação seguido de espaço
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ])', protected)
        
        # Restaurar abreviações
        result = []
        for sent in sentences:
            for i, abbr in enumerate(abbreviations):
                original = abbr.replace('\\', '')
                sent = sent.replace(f'__ABBR{i}__', original)
            if sent.strip():
                result.append(sent.strip())
        
        return result
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """
        Mescla chunks muito pequenos com adjacentes.
        
        Args:
            chunks: Lista de chunks
            
        Returns:
            Lista de chunks com pequenos mesclados
        """
        if not chunks:
            return []
        
        merged = []
        current = chunks[0]
        
        for i in range(1, len(chunks)):
            next_chunk = chunks[i]
            
            # Se chunk atual é muito pequeno e cabe no próximo
            if len(current) < self.min_chunk_size:
                combined = current + " " + next_chunk
                if len(combined) <= self.max_chunk_size:
                    current = combined
                    continue
            
            # Salvar atual e passar para próximo
            merged.append(current)
            current = next_chunk
        
        # Adicionar último
        if current:
            # Se o último é muito pequeno, tentar mesclar com anterior
            if len(current) < self.min_chunk_size and merged:
                combined = merged[-1] + " " + current
                if len(combined) <= self.max_chunk_size:
                    merged[-1] = combined
                else:
                    merged.append(current)
            else:
                merged.append(current)
        
        return merged


# =============================================================================
# Função de conveniência para uso direto
# =============================================================================

def chunk_text_semantic(
    text: str,
    max_chunk_size: int = 800,
    min_chunk_size: int = 200,
    overlap_sentences: int = 1
) -> List[str]:
    """
    Função de conveniência para chunking semântico.
    
    Args:
        text: Texto a ser dividido
        max_chunk_size: Tamanho máximo do chunk em caracteres
        min_chunk_size: Tamanho mínimo (evita chunks muito pequenos)
        overlap_sentences: Número de sentenças de overlap
        
    Returns:
        Lista de chunks semanticamente coesos
    """
    chunker = SemanticChunker(
        max_chunk_size=max_chunk_size,
        min_chunk_size=min_chunk_size,
        overlap_sentences=overlap_sentences
    )
    return chunker.chunk(text)


# =============================================================================
# Função de análise de qualidade
# =============================================================================

def analyze_chunk_quality(chunks: List[str]) -> dict:
    """
    Analisa a qualidade dos chunks gerados.
    
    Args:
        chunks: Lista de chunks
        
    Returns:
        Dict com métricas de qualidade
    """
    if not chunks:
        return {
            "total_chunks": 0,
            "incomplete_sentences": 0,
            "incomplete_rate": 0.0,
            "avg_size": 0,
            "min_size": 0,
            "max_size": 0
        }
    
    incomplete = 0
    sizes = []
    
    for chunk in chunks:
        sizes.append(len(chunk))
        # Chunk que não termina com pontuação final
        if chunk and chunk.rstrip()[-1] not in '.!?':
            incomplete += 1
    
    return {
        "total_chunks": len(chunks),
        "incomplete_sentences": incomplete,
        "incomplete_rate": round(incomplete / len(chunks), 4),
        "avg_size": round(sum(sizes) / len(sizes), 2),
        "min_size": min(sizes),
        "max_size": max(sizes)
    }


# =============================================================================
# Verificação do módulo
# =============================================================================

def check_spacy_available() -> dict:
    """
    Verifica se spaCy está disponível e configurado.
    
    Returns:
        Dict com status do spaCy
    """
    return {
        "spacy_installed": SPACY_AVAILABLE,
        "model_loaded": nlp is not None,
        "model_name": "pt (default)" if nlp else None,
        "fallback_mode": not SPACY_AVAILABLE,
        "language_detection_available": LANGUAGE_DETECTION_AVAILABLE,
        "langdetect_available": LANGDETECT_AVAILABLE,
        "default_language": DEFAULT_LANGUAGE
    }


# =============================================================================
# Phase 3 - Contextual Chunking (Metadados Enriquecidos)
# =============================================================================

def extract_section_title(text: str) -> Optional[str]:
    """
    Tenta detectar o título da seção a partir do texto.
    
    Procura por padrões de títulos no início do texto.
    
    Args:
        text: Texto do chunk
        
    Returns:
        Título da seção ou None
    """
    lines = text.strip().split('\n')
    if not lines:
        return None
    
    first_line = lines[0].strip()
    
    # Padrões de títulos
    # 1. Linha curta no início (provavelmente título)
    if len(first_line) < 100 and first_line:
        # Remover numeração de seções
        title = re.sub(r'^[\d.]+\s*', '', first_line)
        title = re.sub(r'^[#*-]+\s*', '', title)
        
        # Verificar se parece um título (sem ponto final, capitalizado)
        if title and not title.endswith('.') and len(title) < 100:
            return title.strip()
    
    # 2. Markdown headers
    match = re.match(r'^#+\s+(.+)$', first_line)
    if match:
        return match.group(1).strip()
    
    return None


def summarize_text(text: str, max_length: int = 100) -> str:
    """
    Cria resumo curto do texto (primeiras N caracteres).
    
    Args:
        text: Texto a resumir
        max_length: Comprimento máximo
        
    Returns:
        Texto resumido
    """
    if not text:
        return ""
    
    text = text.strip()
    
    if len(text) <= max_length:
        return text
    
    # Cortar em limite de palavra
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length // 2:
        truncated = truncated[:last_space]
    
    return truncated.strip() + "..."


def add_contextual_metadata(
    chunks: List[dict],
    add_neighbor_summaries: bool = True,
    add_section_titles: bool = True,
    summary_length: int = 80
) -> List[dict]:
    """
    Enriquece chunks com metadados contextuais.
    
    Adiciona:
    - section_title: título detectado da seção
    - prev_summary: resumo do chunk anterior
    - next_summary: resumo do chunk seguinte
    - chunk_index: posição na lista
    
    Args:
        chunks: Lista de chunks com 'content' e 'metadata'
        add_neighbor_summaries: Se True, adiciona resumos dos vizinhos
        add_section_titles: Se True, detecta títulos de seção
        summary_length: Comprimento máximo dos resumos
        
    Returns:
        Chunks com metadados enriquecidos
    """
    if not chunks:
        return chunks
    
    enriched = []
    
    for i, chunk in enumerate(chunks):
        # Copiar chunk
        new_chunk = chunk.copy()
        if "metadata" not in new_chunk:
            new_chunk["metadata"] = {}
        else:
            new_chunk["metadata"] = chunk["metadata"].copy()
        
        content = chunk.get("content", "")
        
        # Adicionar índice
        new_chunk["metadata"]["chunk_index"] = i
        new_chunk["metadata"]["total_chunks"] = len(chunks)
        
        # Detectar título da seção
        if add_section_titles:
            section_title = extract_section_title(content)
            if section_title:
                new_chunk["metadata"]["section_title"] = section_title
        
        # Adicionar resumos dos vizinhos
        if add_neighbor_summaries:
            # Chunk anterior
            if i > 0:
                prev_content = chunks[i - 1].get("content", "")
                new_chunk["metadata"]["prev_summary"] = summarize_text(prev_content, summary_length)
            
            # Próximo chunk
            if i < len(chunks) - 1:
                next_content = chunks[i + 1].get("content", "")
                new_chunk["metadata"]["next_summary"] = summarize_text(next_content, summary_length)
        
        enriched.append(new_chunk)
    
    logger.info(f"Contextual metadata added to {len(enriched)} chunks")
    
    return enriched


if __name__ == "__main__":
    # Teste rápido do módulo
    print("=== Teste do Chunking Semântico ===\n")
    
    status = check_spacy_available()
    print(f"Status spaCy: {status}\n")
    
    # Texto de exemplo
    sample_text = """
    O GWPRP é um protocolo de roteamento geográfico desenvolvido para FANETs. 
    Ele considera a mobilidade tridimensional dos nós para tomar decisões de encaminhamento.
    
    O protocolo utiliza informações de posição GPS para calcular a distância até o destino.
    Quando um nó precisa encaminhar um pacote, ele avalia seus vizinhos e seleciona o melhor.
    
    Os resultados mostram que o GWPRP supera outros protocolos como GPSR e AODV.
    A taxa de entrega é significativamente maior em cenários de alta mobilidade.
    """
    
    chunks = chunk_text_semantic(sample_text, max_chunk_size=300)
    
    print(f"Texto original: {len(sample_text)} caracteres")
    print(f"Chunks gerados: {len(chunks)}\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ({len(chunk)} chars) ---")
        print(chunk)
        print()
    
    quality = analyze_chunk_quality(chunks)
    print(f"Qualidade: {quality}")

