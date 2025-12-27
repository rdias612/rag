"""
Módulo de gerenciamento de histórico de conversas.

Permite manter contexto entre perguntas de follow-up.
"""
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

from src.core.logger import rag_logger


@dataclass
class Message:
    """Representa uma mensagem na conversa."""
    role: str  # "user" ou "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Conversation:
    """Representa uma conversa com histórico de mensagens."""
    session_id: str
    messages: list[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    def add_message(self, role: str, content: str) -> None:
        """Adiciona uma mensagem à conversa."""
        self.messages.append(Message(role=role, content=content))
        self.last_activity = time.time()
    
    def get_history_for_prompt(self, max_messages: int = 10) -> str:
        """
        Retorna o histórico formatado para incluir no prompt.
        
        Args:
            max_messages: Número máximo de mensagens a incluir
            
        Returns:
            Histórico formatado como string
        """
        # Pegar as últimas N mensagens (excluindo a última do user, que é a pergunta atual)
        recent = self.messages[-(max_messages + 1):-1] if len(self.messages) > 1 else []
        
        if not recent:
            return ""
        
        history_parts = []
        for msg in recent:
            role_label = "Usuário" if msg.role == "user" else "Assistente"
            history_parts.append(f"{role_label}: {msg.content}")
        
        return "\n".join(history_parts)
    
    def get_last_exchange(self) -> tuple[Optional[str], Optional[str]]:
        """
        Retorna a última troca (pergunta e resposta).
        
        Returns:
            Tupla (última pergunta do user, última resposta do assistant)
        """
        last_user = None
        last_assistant = None
        
        for msg in reversed(self.messages):
            if msg.role == "assistant" and last_assistant is None:
                last_assistant = msg.content
            elif msg.role == "user" and last_user is None:
                last_user = msg.content
            
            if last_user and last_assistant:
                break
        
        return last_user, last_assistant
    
    def to_dict(self) -> dict:
        """Converte a conversa para dicionário."""
        return {
            "session_id": self.session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp
                }
                for msg in self.messages
            ],
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_activity": datetime.fromtimestamp(self.last_activity).isoformat(),
            "message_count": len(self.messages)
        }


class ConversationManager:
    """
    Gerenciador de conversas em memória.
    
    Mantém sessões de conversa ativas e limpa sessões antigas automaticamente.
    """
    
    def __init__(self, session_timeout_minutes: int = 30, max_sessions: int = 1000):
        """
        Inicializa o gerenciador.
        
        Args:
            session_timeout_minutes: Tempo em minutos para expirar sessões inativas
            max_sessions: Número máximo de sessões simultâneas
        """
        self._sessions: dict[str, Conversation] = {}
        self._lock = threading.RLock()
        self._session_timeout = session_timeout_minutes * 60  # Converter para segundos
        self._max_sessions = max_sessions
        
        rag_logger.info(
            f"ConversationManager initialized: timeout={session_timeout_minutes}min, "
            f"max_sessions={max_sessions}"
        )
    
    def create_session(self) -> str:
        """
        Cria uma nova sessão de conversa.
        
        Returns:
            ID da sessão criada
        """
        session_id = str(uuid.uuid4())
        
        with self._lock:
            # Limpar sessões antigas se necessário
            self.cleanup_expired_sessions()
            
            # Verificar limite de sessões
            if len(self._sessions) >= self._max_sessions:
                self._remove_oldest_session()
            
            self._sessions[session_id] = Conversation(session_id=session_id)
        
        rag_logger.info(f"New conversation session created: {session_id[:8]}...")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Conversation]:
        """
        Obtém uma sessão existente.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Conversa ou None se não existir/expirada
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None:
                return None
            
            # Verificar se expirou
            if time.time() - session.last_activity > self._session_timeout:
                del self._sessions[session_id]
                rag_logger.info(f"Session expired: {session_id[:8]}...")
                return None
            
            return session
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> tuple[str, Conversation]:
        """
        Obtém uma sessão existente ou cria uma nova.
        
        Args:
            session_id: ID da sessão (opcional)
            
        Returns:
            Tupla (session_id, Conversation)
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session_id, session
        
        # Criar nova sessão
        new_id = self.create_session()
        return new_id, self._sessions[new_id]
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Adiciona uma mensagem a uma sessão.
        
        Args:
            session_id: ID da sessão
            role: "user" ou "assistant"
            content: Conteúdo da mensagem
            
        Returns:
            True se adicionou, False se sessão não existe
        """
        session = self.get_session(session_id)
        if session is None:
            return False
        
        session.add_message(role, content)
        rag_logger.debug(f"Message added to session {session_id[:8]}...: {role}")
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        Remove uma sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            True se removeu, False se não existia
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                rag_logger.info(f"Session deleted: {session_id[:8]}...")
                return True
            return False
    
    def list_sessions(self) -> list[dict]:
        """
        Lista todas as sessões ativas.
        
        Returns:
            Lista de dicionários com informações das sessões
        """
        with self._lock:
            self.cleanup_expired_sessions()
            return [
                {
                    "session_id": session.session_id,
                    "message_count": len(session.messages),
                    "created_at": datetime.fromtimestamp(session.created_at).isoformat(),
                    "last_activity": datetime.fromtimestamp(session.last_activity).isoformat()
                }
                for session in self._sessions.values()
            ]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove sessões expiradas. Public method to be called by background task.
        
        Returns:
            Número de sessões removidas
        """
        now = time.time()
        with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if now - session.last_activity > self._session_timeout
            ]
            
            for sid in expired:
                del self._sessions[sid]
            
            if expired:
                rag_logger.info(f"Cleaned up {len(expired)} expired sessions")
            
            return len(expired)
    
    def _remove_oldest_session(self) -> None:
        """Remove a sessão mais antiga."""
        if not self._sessions:
            return
        
        oldest_id = min(
            self._sessions.keys(),
            key=lambda sid: self._sessions[sid].last_activity
        )
        del self._sessions[oldest_id]
        rag_logger.info(f"Removed oldest session to free space: {oldest_id[:8]}...")


# Instância global do gerenciador de conversas
conversation_manager = ConversationManager()
