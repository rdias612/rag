"""
Esquemas Pydantic para validação de requisições da API.
Melhoria #12 - Validação de Schema com Pydantic
"""
from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Modelo para requisições ao endpoint /api/query."""
    question: str = Field(..., min_length=1, description="Pergunta a ser respondida")
    top_k: int = Field(default=5, ge=1, le=50, description="Número de chunks a recuperar")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Criatividade do LLM")
    include_sources: bool = Field(default=True, description="Incluir fontes na resposta")
    collection: Optional[str] = Field(default=None, description="Filtrar por coleção")
    debug: bool = Field(default=False, description="Ativar modo debug/explain")

    class Config:
        extra = "ignore"


class SearchRequest(BaseModel):
    """Modelo para requisições ao endpoint /api/search."""
    question: str = Field(..., min_length=1, description="Query de busca")
    top_k: int = Field(default=5, ge=1, le=100, description="Número de resultados")

    class Config:
        extra = "ignore"


class ChatRequest(BaseModel):
    """Modelo para requisições ao endpoint /api/chat."""
    question: str = Field(..., min_length=1, description="Pergunta a ser respondida")
    session_id: Optional[str] = Field(default=None, description="ID da sessão (omitir para nova)")
    top_k: int = Field(default=5, ge=1, le=50, description="Número de chunks a recuperar")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Criatividade do LLM")
    include_sources: bool = Field(default=True, description="Incluir fontes na resposta")
    collection: Optional[str] = Field(default=None, description="Filtrar por coleção")
    debug: bool = Field(default=False, description="Ativar modo debug/explain")

    class Config:
        extra = "ignore"


class StreamQueryRequest(BaseModel):
    """Modelo para requisições ao endpoint /api/query/stream."""
    question: str = Field(..., min_length=1, description="Pergunta a ser respondida")
    top_k: int = Field(default=5, ge=1, le=50, description="Número de chunks")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Criatividade do LLM")

    class Config:
        extra = "ignore"
