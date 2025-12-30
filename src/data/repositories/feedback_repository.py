"""
Repository para operações de feedback.
"""
import json
from typing import Optional

from src.data.repositories.base import BaseRepository
from src.core.logger import db_logger
from src.config import ENABLE_ENCRYPTION, ENCRYPT_FEEDBACK_COMMENTS, ENCRYPT_METADATA

# Importar funções de criptografia
try:
    from src.core.encryption import encrypt_data, encrypt_metadata
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


class FeedbackRepository(BaseRepository):
    """Gerencia feedback de usuários."""
    
    def create(self, session_id: str, message_index: int, rating: int,
               comment: Optional[str] = None, metadata: Optional[dict] = None) -> bool:
        """Insere um feedback do usuário."""
        try:
            encrypted_comment = comment
            if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION and ENCRYPT_FEEDBACK_COMMENTS and comment:
                try:
                    encrypted_comment = encrypt_data(comment)
                except Exception as e:
                    db_logger.warning(f"Failed to encrypt comment: {e}")
            
            encrypted_metadata = None
            if metadata:
                if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION and ENCRYPT_METADATA:
                    try:
                        encrypted_metadata = encrypt_metadata(metadata)
                    except Exception:
                        encrypted_metadata = json.dumps(metadata)
                else:
                    encrypted_metadata = json.dumps(metadata)
            
            with self._get_cursor() as cur:
                cur.execute("""
                    INSERT INTO feedback (session_id, message_index, rating, comment, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                """, (session_id, message_index, rating, encrypted_comment, encrypted_metadata))
            
            return True
        except Exception as e:
            db_logger.error(f"Error inserting feedback: {e}")
            return False
    
    def find_by_id(self, id: int) -> Optional[dict]:
        """Busca feedback por ID."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT * FROM feedback WHERE id = %s", (id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def find_by_session(self, session_id: str) -> list[dict]:
        """Lista feedback de uma sessão."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT * FROM feedback
                WHERE session_id = %s
                ORDER BY created_at DESC
            """, (session_id,))
            return [dict(row) for row in cur.fetchall()]
    
    def count(self) -> int:
        """Conta total de feedbacks."""
        with self._get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM feedback")
            return cur.fetchone()[0]
