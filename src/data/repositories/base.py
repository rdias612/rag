"""
Base Repository com métodos comuns a todos os repositories.
"""
from abc import ABC, abstractmethod
from contextlib import contextmanager, ExitStack
from typing import Optional, TypeVar, Generic, Any

from src.data.database import get_connection
from psycopg2.extras import RealDictCursor

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Classe base para todos os repositories."""
    
    def __init__(self, connection=None):
        self._external_connection = connection
    
    @contextmanager
    def _get_cursor(self, dict_cursor: bool = False):
        """
        Obtém cursor garantindo que diferentes tipos de conexão funcionem
        (instância direta, conexão externa ou context manager).

        Args:
            dict_cursor: Se True, usa RealDictCursor para retornar dicts
        """
        cursor_factory = RealDictCursor if dict_cursor else None

        # Permitir receber tanto uma conexão já aberta quanto um context manager.
        connection_source = self._external_connection or get_connection()

        with ExitStack() as stack:
            # Se for um context manager (ex.: GeneratorContextManager), entrar nele.
            if hasattr(connection_source, "__enter__"):
                conn = stack.enter_context(connection_source)
                manage_commit = False  # commit/rollback é responsabilidade do context manager
            else:
                conn = connection_source
                manage_commit = False if self._external_connection else True

            cur = stack.enter_context(conn.cursor(cursor_factory=cursor_factory))
            try:
                yield cur
            finally:
                if manage_commit:
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
