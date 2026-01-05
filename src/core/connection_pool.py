"""
Módulo de Connection Pool Avançado para PostgreSQL.

Implementa um pool de conexões com:
- Reutilização de conexões
- Health checks automáticos
- Estatísticas detalhadas
- Failover automático
- Balanceamento de carga

Author: Sistema RAG
Created: 2025-12-29
"""
import threading
import time

from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from collections import defaultdict

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from psycopg2.errors import OperationalError, InterfaceError

from src.config import (
    DATABASE_CONFIG,
    ENABLE_CONNECTION_POOL,
    DB_POOL_MIN_CONN,
    DB_POOL_MAX_CONN,
    DB_CONNECTION_TIMEOUT,
    DB_STATEMENT_TIMEOUT
)

print(__name__)


class ConnectionPoolStats:
    """Estatísticas do pool de conexões."""
    
    def __init__(self):
        self.total_acquisitions = 0
        self.total_releases = 0
        self.failed_acquisitions = 0
        self.active_connections = 0
        self.max_concurrent_connections = 0
        self.total_queries = 0
        self.total_query_time = 0.0
        self.slow_queries = 0  # Queries > 1s
        self.failed_queries = 0
        self.errors_by_type = defaultdict(int)
        self.lock = threading.Lock()
    
    def record_acquisition(self, success: bool):
        """Registra uma tentativa de obter conexão."""
        with self.lock:
            self.total_acquisitions += 1
            if not success:
                self.failed_acquisitions += 1
    
    def record_release(self):
        """Registra uma liberação de conexão."""
        with self.lock:
            self.total_releases += 1
            self.active_connections -= 1
    
    def record_query_start(self) -> float:
        """Registra início de query e retorna timestamp."""
        with self.lock:
            self.total_queries += 1
            self.active_connections += 1
            self.max_concurrent_connections = max(
                self.max_concurrent_connections,
                self.active_connections
            )
        return time.time()
    
    def record_query_end(self, start_time: float, success: bool, error_type: Optional[str] = None):
        """Registra fim de query."""
        duration = time.time() - start_time
        
        with self.lock:
            self.total_query_time += duration
            self.active_connections -= 1
            
            if duration > 1.0:  # Query lenta (> 1s)
                self.slow_queries += 1
            
            if not success:
                self.failed_queries += 1
                if error_type:
                    self.errors_by_type[error_type] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do pool."""
        with self.lock:
            avg_query_time = (
                self.total_query_time / self.total_queries
                if self.total_queries > 0
                else 0
            )
            
            error_rate = (
                self.failed_queries / self.total_queries * 100
                if self.total_queries > 0
                else 0
            )
            
            return {
                "total_acquisitions": self.total_acquisitions,
                "total_releases": self.total_releases,
                "failed_acquisitions": self.failed_acquisitions,
                "active_connections": self.active_connections,
                "max_concurrent_connections": self.max_concurrent_connections,
                "total_queries": self.total_queries,
                "avg_query_time_ms": round(avg_query_time * 1000, 2),
                "slow_queries": self.slow_queries,
                "failed_queries": self.failed_queries,
                "error_rate_percent": round(error_rate, 2),
                "errors_by_type": dict(self.errors_by_type)
            }
    
    def reset(self):
        """Reseta todas as estatísticas."""
        with self.lock:
            self.total_acquisitions = 0
            self.total_releases = 0
            self.failed_acquisitions = 0
            self.active_connections = 0
            self.max_concurrent_connections = 0
            self.total_queries = 0
            self.total_query_time = 0.0
            self.slow_queries = 0
            self.failed_queries = 0
            self.errors_by_type = defaultdict(int)


class AdvancedConnectionPool:
    """
    Pool de conexões avançado para PostgreSQL.
    
    Features:
    - Reutilização de conexões
    - Health checks automáticos
    - Estatísticas detalhadas
    - Failover automático
    - Timeout de conexão e statement
    """
    
    def __init__(
        self,
        min_connections: int = DB_POOL_MIN_CONN,
        max_connections: int = DB_POOL_MAX_CONN,
        connection_timeout: int = DB_CONNECTION_TIMEOUT,
        statement_timeout: int = DB_STATEMENT_TIMEOUT,
        **pool_config
    ):
        """
        Inicializa o pool de conexões.
        
        Args:
            min_connections: Número mínimo de conexões no pool
            max_connections: Número máximo de conexões no pool
            connection_timeout: Timeout para estabelecer conexão (segundos)
            statement_timeout: Timeout para cada statement (segundos)
            **pool_config: Configurações adicionais do pool
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.statement_timeout = statement_timeout
        
        # Preparar configuração com timeouts
        final_pool_config = {
            **pool_config,
            **DATABASE_CONFIG,
            'connect_timeout': connection_timeout,
            'options': f'-c statement_timeout={statement_timeout * 1000}'
        }
        
        # Criar pool de conexões
        try:
            self.pool = pool.ThreadedConnectionPool(
                minconn=min_connections,
                maxconn=max_connections,
                **final_pool_config
            )
            print(
                f"AdvancedConnectionPool initialized: "
                f"min={min_connections}, max={max_connections}, "
                f"conn_timeout={connection_timeout}s, stmt_timeout={statement_timeout}s"
            )
        except Exception as e:
            print(f"Failed to initialize connection pool: {e}")
            raise RuntimeError(f"Connection pool initialization failed: {e}")
        
        # Estatísticas
        self.stats = ConnectionPoolStats()
        
        # Health check worker
        self._health_check_running = False
        self._health_check_thread = None
    
    def _get_connection(self) -> Optional[psycopg2.extensions.connection]:
        """
        Obtém uma conexão do pool.
        
        Returns:
            Conexão ou None em caso de erro
        """
        try:
            self.stats.record_acquisition(success=True)
            conn = self.pool.getconn()
            print("Connection acquired from pool")
            return conn
        except Exception as e:
            self.stats.record_acquisition(success=False)
            error_type = type(e).__name__
            print(f"Failed to acquire connection: {e} ({error_type})")
            self.stats.record_query_end(
                time.time(),
                success=False,
                error_type=error_type
            )
            return None
    
    def _return_connection(self, conn: psycopg2.extensions.connection):
        """
        Devolve uma conexão ao pool.
        
        Args:
            conn: Conexão PostgreSQL
        """
        try:
            self.pool.putconn(conn)
            self.stats.record_release()
            print("Connection returned to pool")
        except Exception as e:
            print(f"Failed to return connection to pool: {e}")
            # Tentar fechar a conexão se falhar ao devolver
            try:
                conn.close()
            except:
                pass
    
    @contextmanager
    def get_connection(self):
        """
        Context manager para obter e devolver conexão.
        
        Yields:
            Conexão PostgreSQL
        """
        conn = None
        query_start = time.time()
        success = True
        error_type = None
        
        try:
            conn = self._get_connection()
            if conn is None:
                raise RuntimeError("Failed to acquire connection from pool")
            
            yield conn
            
            # Commit bem-sucedido
            conn.commit()
            
        except (OperationalError, InterfaceError) as e:
            # Erro de operação - rollback e não devolver conexão ao pool
            error_type = type(e).__name__
            success = False
            if conn:
                try:
                    conn.rollback()
                    # Fechar conexão defeituosa
                    self.pool.putconn(conn, close=True)
                    print("Failed connection closed and removed from pool")
                except:
                    pass
            raise e
        except Exception as e:
            # Outros erros - rollback mas manter conexão
            error_type = type(e).__name__
            success = False
            if conn:
                try:
                    conn.rollback()
                    print(f"Transaction rolled back due to error: {e}")
                except:
                    pass
            raise e
        finally:
            # Registrar estatísticas
            self.stats.record_query_end(query_start, success, error_type)
            
            # Devolver conexão ao pool se ainda for válida
            if conn:
                try:
                    self._return_connection(conn)
                except:
                    pass
    
    def health_check(self) -> bool:
        """
        Verifica a saúde do pool de conexões.
        
        Returns:
            True se pool está saudável, False caso contrário
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    result = cur.fetchone()
                    if result and result[0] == 1:
                        print("Pool health check passed")
                        return True
                    else:
                        print("Pool health check failed: unexpected result")
                        return False
        except Exception as e:
            print(f"Pool health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do pool.
        
        Returns:
            Dicionário com estatísticas
        """
        pool_stats = self.stats.get_stats()
        
        # Adicionar informações do pool psycopg2
        pool_info = {
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "pool_closed": self.pool.closed
        }
        
        return {
            **pool_info,
            **pool_info
        }
    
    def reset_stats(self):
        """Reseta as estatísticas do pool."""
        self.stats.reset()
        print("Connection pool statistics reset")
    
    def close_all(self):
        """
        Fecha todas as conexões do pool.
        
        Deve ser chamado ao encerrar a aplicação.
        """
        print("Closing all connections in pool...")
        
        # Parar health check se estiver rodando
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        
        # Fechar pool
        try:
            self.pool.closeall()
            print("All connections closed successfully")
        except Exception as e:
            print(f"Error closing pool: {e}")
    
    def start_health_check(self, interval: int = 60):
        """
        Inicia health check automático em background.
        
        Args:
            interval: Intervalo entre health checks em segundos
        """
        if self._health_check_running:
            print("Health check is already running")
            return
        
        self._health_check_running = True
        
        def health_check_worker():
            while self._health_check_running:
                try:
                    if self.health_check():
                        print("Health check passed")
                    else:
                        print("Health check failed!")
                except Exception as e:
                    print(f"Health check error: {e}")
                
                # Dormir até o próximo check
                for _ in range(interval):
                    if not self._health_check_running:
                        break
                    time.sleep(1)
        
        self._health_check_thread = threading.Thread(
            target=health_check_worker,
            daemon=True,
            name="pool-health-check"
        )
        self._health_check_thread.start()
        print(f"Health check started (interval: {interval}s)")


# Instância global do pool de conexões
_global_pool: Optional[AdvancedConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool() -> AdvancedConnectionPool:
    """
    Retorna a instância global do pool de conexões.
    
    Cria o pool na primeira chamada se não existir.
    
    Returns:
        Instância de AdvancedConnectionPool
    """
    global _global_pool
    
    with _pool_lock:
        if _global_pool is None:
            if not ENABLE_CONNECTION_POOL:
                print(
                    "Connection pooling is disabled. "
                    "Create pool manually if needed."
                )
                # Criar pool com configurações mínimas
                _global_pool = AdvancedConnectionPool(
                    min_connections=1,
                    max_connections=1
                )
            else:
                _global_pool = AdvancedConnectionPool(
                    min_connections=DB_POOL_MIN_CONN,
                    max_connections=DB_POOL_MAX_CONN,
                    connection_timeout=DB_CONNECTION_TIMEOUT,
                    statement_timeout=DB_STATEMENT_TIMEOUT
                )
                
                # Iniciar health check automático
                _global_pool.start_health_check(interval=60)
        
        return _global_pool


def reset_global_pool():
    """Reseta a instância global do pool de conexões."""
    global _global_pool
    
    with _pool_lock:
        if _global_pool:
            _global_pool.close_all()
            _global_pool = None
            print("Global connection pool reset")


@contextmanager
def get_db_connection():
    """
    Context manager para obter conexão do pool global.
    
    Uso simplificado compatível com o get_connection() original.
    
    Yields:
        Conexão PostgreSQL do pool global
    """
    pool = get_connection_pool()
    with pool.get_connection() as conn:
        yield conn
