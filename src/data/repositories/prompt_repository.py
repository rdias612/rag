"""
Repository para operações com prompts.
"""
import logging
import time
from typing import Optional

from src.data.repositories.base import BaseRepository

# Standard logger for repository operations
repo_logger = logging.getLogger("rag.repositories")

# Cache em memória para prompts
PROMPT_CACHE = {}
PROMPT_CACHE_TTL = 300
PROMPT_CACHE_LAST_UPDATE = 0

# Categorias críticas
CRITICAL_CATEGORIES = {
    'rag_main': 'Prompt principal para RAG',
    'hyde': 'Geração de documentos hipotéticos',
    'query_expansion': 'Expansão de queries'
}


class PromptRepository(BaseRepository):
    """Gerencia prompts no banco de dados."""
    
    def create(self, name: str, template: str, category: str,
               description: str = None, priority: int = 100,
               tags: list[str] = None, use_case: str = None,
               created_by: str = 'user') -> tuple[bool, int, str]:
        """
        Cria um novo prompt.
        
        Returns:
            (success, prompt_id, error_message)
        """
        try:
            with self._get_cursor() as cur:
                # Verificar nome único
                cur.execute("SELECT id FROM prompts WHERE name = %s", (name,))
                if cur.fetchone():
                    return False, 0, f"Já existe um prompt com o nome '{name}'"
                
                cur.execute("""
                    INSERT INTO prompts (name, template, category, description,
                                        priority, tags, use_case, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (name, template, category, description, priority, tags or [], use_case, created_by))
                prompt_id = cur.fetchone()[0]
            
            repo_logger.info("Created prompt '%s' with ID %d", name, prompt_id)
            return True, prompt_id, ""
        except Exception as e:
            repo_logger.error("Error creating prompt: %s", e, exc_info=True)
            return False, 0, str(e)
    
    def find_by_id(self, id: int) -> Optional[dict]:
        """Busca prompt por ID."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT id, name, template, category, priority, tags,
                       description, use_case, is_active, created_at,
                       updated_at, created_by, version
                FROM prompts WHERE id = %s
            """, (id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def find_by_name(self, name: str, use_cache: bool = True) -> Optional[str]:
        """Busca template de prompt pelo nome."""
        global PROMPT_CACHE, PROMPT_CACHE_LAST_UPDATE
        
        current_time = time.time()
        
        if use_cache and name in PROMPT_CACHE:
            if current_time - PROMPT_CACHE_LAST_UPDATE < PROMPT_CACHE_TTL:
                return PROMPT_CACHE[name]
        
        try:
            with self._get_cursor() as cur:
                cur.execute(
                    "SELECT template FROM prompts WHERE name = %s AND is_active = TRUE",
                    (name,)
                )
                row = cur.fetchone()
                if row:
                    template = row[0]
                    PROMPT_CACHE[name] = template
                    PROMPT_CACHE_LAST_UPDATE = current_time
                    return template
                return None
        except Exception as e:
            repo_logger.error("Error fetching prompt '%s': %s", name, e, exc_info=True)
            return None
    
    def list_all(self) -> list[dict]:
        """Lista todos os prompts."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT id, name, category, priority, tags, description,
                       use_case, is_active, updated_at, created_by
                FROM prompts
                ORDER BY category, priority DESC, name
            """)
            return [dict(row) for row in cur.fetchall()]
    
    def find_by_category(self, category: str, include_inactive: bool = False) -> list[dict]:
        """Busca prompts por categoria."""
        with self._get_cursor(dict_cursor=True) as cur:
            query = """
                SELECT id, name, template, priority, tags, is_active
                FROM prompts WHERE category = %s
            """
            params = [category]
            
            if not include_inactive:
                query += " AND is_active = TRUE"
            
            query += " ORDER BY priority DESC"
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    
    def update(self, prompt_id: int, template: str = None, description: str = None,
               priority: int = None, tags: list[str] = None, use_case: str = None,
               is_active: bool = None) -> tuple[bool, str]:
        """
        Atualiza um prompt existente.
        
        Returns:
            (success, error_message)
        """
        global PROMPT_CACHE
        
        try:
            with self._get_cursor() as cur:
                # Verificar se existe
                cur.execute("SELECT name FROM prompts WHERE id = %s", (prompt_id,))
                row = cur.fetchone()
                if not row:
                    return False, "Prompt não encontrado"
                
                prompt_name = row[0]
                
                # Construir update dinâmico
                updates = []
                params = []
                
                if template is not None:
                    updates.append("template = %s")
                    params.append(template)
                
                if description is not None:
                    updates.append("description = %s")
                    params.append(description)
                
                if priority is not None:
                    updates.append("priority = %s")
                    params.append(priority)
                
                if tags is not None:
                    updates.append("tags = %s")
                    params.append(tags)
                
                if use_case is not None:
                    updates.append("use_case = %s")
                    params.append(use_case)
                
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)
                
                if not updates:
                    return True, "Nada para atualizar"
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                updates.append("version = version + 1")
                
                query = f"UPDATE prompts SET {', '.join(updates)} WHERE id = %s"
                params.append(prompt_id)
                
                cur.execute(query, params)
            
            # Invalidar cache
            if prompt_name in PROMPT_CACHE:
                del PROMPT_CACHE[prompt_name]
            
            repo_logger.info("Updated prompt %d", prompt_id)
            return True, ""
        except Exception as e:
            repo_logger.error("Error updating prompt %d: %s", prompt_id, e, exc_info=True)
            return False, str(e)
    
    def can_delete(self, prompt_id: int) -> tuple[bool, str]:
        """Verifica se prompt pode ser deletado."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT id, category, is_active FROM prompts WHERE id = %s
            """, (prompt_id,))
            row = cur.fetchone()
            
            if not row:
                return False, "Prompt não encontrado"
            
            prompt = dict(row)
            
            # Verificar se é categoria crítica
            if prompt["category"] in CRITICAL_CATEGORIES and prompt["is_active"]:
                cur.execute("""
                    SELECT COUNT(*) FROM prompts
                    WHERE category = %s AND is_active = TRUE
                """, (prompt["category"],))
                count = cur.fetchone()[0]
                
                if count <= 1:
                    return False, f"Não é possível deletar o único prompt ativo da categoria '{prompt['category']}'"
            
            return True, ""
    
    def delete(self, prompt_id: int) -> tuple[bool, str]:
        """Deleta um prompt após validação."""
        can_del, reason = self.can_delete(prompt_id)
        if not can_del:
            return False, reason
        
        try:
            with self._get_cursor() as cur:
                cur.execute("DELETE FROM prompts WHERE id = %s", (prompt_id,))
                if cur.rowcount == 0:
                    return False, "Prompt não encontrado"
            
            repo_logger.info("Deleted prompt %d", prompt_id)
            return True, ""
        except Exception as e:
            repo_logger.error("Error deleting prompt %d: %s", prompt_id, e, exc_info=True)
            return False, str(e)
    
    def count_active_in_category(self, category: str) -> int:
        """Conta prompts ativos em uma categoria."""
        with self._get_cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM prompts
                WHERE category = %s AND is_active = TRUE
            """, (category,))
            return cur.fetchone()[0]
