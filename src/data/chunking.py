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

# Tentar carregar spaCy e modelo português
try:
    import spacy
    
    try:
        # Carregar modelo mínimo para segmentação de sentenças
        nlp = spacy.blank("pt")  # Modelo em branco (mais leve)
        nlp.add_pipe("sentencizer")  # Adicionar apenas sentencizer
        SPACY_AVAILABLE = True
        logger.info("spaCy carregado com sucesso (sentencizer pt)")
    except Exception as e:
        SPACY_AVAILABLE = False
        nlp = None
        logger.warning(f"Erro ao carregar spaCy: {e}. Usando fallback regex.")
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
        """Divide sentenças usando spaCy."""
        doc = nlp(text)
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
        "model_name": "pt_core_news_sm" if nlp else None,
        "fallback_mode": not SPACY_AVAILABLE
    }


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
