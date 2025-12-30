"""
Base Repository com métodos comuns a todos os repositories.
"""
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, TypeVar, Generic, Any

from src.data.database import get_connection

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Classe base para todos os repositories."""
    
    def __init__(self, connection=None):
        self._external_connection = connection
    
    @contextmanager
    def _get_cursor(self, dict_cursor: bool = False):
        """
        Obtém cursor com conexão gerenciada.
        
        Args:
            dict_cursor: Se True, usa RealDictCursor para retornar dicts
        """
        from psycopg2.extras import RealDictCursor
        
        cursor_factory = RealDictCursor if dict_cursor else None
        
        if self._external_connection:
            with self._external_connection.cursor(cursor_factory=cursor_factory) as cur:
                yield cur
        else:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
                    conn.commit()
    
    @abstractmethod
    def create(self, entity: T) -> int:
        """Cria uma entidade e retorna seu ID."""
        pass
    
    @abstractmethod
    def find_by_id(self, id: int) -> Optional[T]:
        """Busca entidade por ID."""
        pass
    
    def delete_by_id(self, id: int) -> bool:
        """Remove entidade por ID."""
        raise NotImplementedError
    
    def count(self) -> int:
        """Conta total de entidades."""
        raise NotImplementedError
