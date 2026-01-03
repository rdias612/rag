"""
Repository para operações com instruções de tipos de perguntas (few-shot).
"""
import time
from typing import Optional

from src.data.repositories.base import BaseRepository

# Cache em memória para instruções
INSTRUCTION_CACHE = {}
INSTRUCTION_CACHE_TTL = 300
INSTRUCTION_CACHE_LAST_UPDATE = 0


class QuestionTypeInstructionRepository(BaseRepository):
    """Gerencia instruções de tipos de perguntas no banco de dados."""
    
    def find_by_id(self, id: int) -> Optional[dict]:
        """
        Busca instrução por ID.
        
        Args:
            id: ID da instrução
            
        Returns:
            Dicionário com os dados da instrução, ou None se não encontrado
        """
        try:
            with self._get_cursor(dict_cursor=True) as cur:
                cur.execute("""
                    SELECT id, question_type, template, description, 
                           is_active, version, created_at, updated_at
                    FROM question_type_instructions 
                    WHERE id = %s
                """, (id,))
                row = cur.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            print(f"Error fetching instruction by ID {id}: {e}")
            return None
    
    def find_by_question_type(self, question_type: str, use_cache: bool = True) -> Optional[str]:
        """
        Busca template de instruções pelo tipo de pergunta.
        
        Args:
            question_type: Tipo da pergunta (ex: 'definition', 'comparison')
            use_cache: Se deve usar cache em memória
            
        Returns:
            Template com instruções + exemplos few-shot, ou None se não encontrado
        """
        global INSTRUCTION_CACHE, INSTRUCTION_CACHE_LAST_UPDATE
        
        current_time = time.time()
        
        # Tentar cache
        if use_cache and question_type in INSTRUCTION_CACHE:
            if current_time - INSTRUCTION_CACHE_LAST_UPDATE < INSTRUCTION_CACHE_TTL:
                return INSTRUCTION_CACHE[question_type]
        
        try:
            with self._get_cursor() as cur:
                cur.execute("""
                    SELECT template 
                    FROM question_type_instructions 
                    WHERE question_type = %s AND is_active = TRUE
                """, (question_type,))
                row = cur.fetchone()
                
                if row:
                    template = row[0]
                    INSTRUCTION_CACHE[question_type] = template
                    INSTRUCTION_CACHE_LAST_UPDATE = current_time
                    print(f"Found instruction for type '{question_type}' in DB")
                    return template
                
                print(f"No instruction found for type '{question_type}'")
                return None
                
        except Exception as e:
            print(f"Error fetching instruction for type '{question_type}': {e}")
            return None
    
    def create(self, entity: dict) -> int:
        """
        Cria uma nova instrução (implementação do método abstrato).
        
        Args:
            entity: Dicionário com 'question_type', 'template', 'description'
            
        Returns:
            ID da instrução criada
        """
        question_type = entity.get('question_type')
        template = entity.get('template')
        description = entity.get('description')
        
        try:
            with self._get_cursor() as cur:
                # Verificar se já existe
                cur.execute(
                    "SELECT id FROM question_type_instructions WHERE question_type = %s",
                    (question_type,)
                )
                if cur.fetchone():
                    raise ValueError(f"Já existe instrução para tipo '{question_type}'")
                
                cur.execute("""
                    INSERT INTO question_type_instructions 
                    (question_type, template, description, version)
                    VALUES (%s, %s, %s, 1)
                    RETURNING id
                """, (question_type, template, description))
                instruction_id = cur.fetchone()[0]
            
            print(f"Created instruction '{question_type}' with ID {instruction_id}")
            return instruction_id
            
        except Exception as e:
            print(f"Error creating instruction: {e}")
            raise
    
    def create_instruction(self, question_type: str, template: str, description: str = None) -> tuple[bool, int, str]:
        """
        Cria uma nova instrução (método de conveniência).
        
        Returns:
            (success, instruction_id, error_message)
        """
        try:
            with self._get_cursor() as cur:
                # Verificar se já existe
                cur.execute(
                    "SELECT id FROM question_type_instructions WHERE question_type = %s",
                    (question_type,)
                )
                if cur.fetchone():
                    return False, 0, f"Já existe instrução para tipo '{question_type}'"
                
                cur.execute("""
                    INSERT INTO question_type_instructions 
                    (question_type, template, description, version)
                    VALUES (%s, %s, %s, 1)
                    RETURNING id
                """, (question_type, template, description))
                instruction_id = cur.fetchone()[0]
            
            print(f"Created instruction '{question_type}' with ID {instruction_id}")
            return True, instruction_id, ""
            
        except Exception as e:
            print(f"Error creating instruction: {e}")
            return False, 0, str(e)
    
    def update(self, question_type: str, template: str = None, description: str = None, 
               is_active: bool = None) -> tuple[bool, str]:
        """
        Atualiza uma instrução existente.
        
        Returns:
            (success, error_message)
        """
        global INSTRUCTION_CACHE
        
        try:
            with self._get_cursor() as cur:
                # Verificar se existe
                cur.execute(
                    "SELECT id FROM question_type_instructions WHERE question_type = %s",
                    (question_type,)
                )
                if not cur.fetchone():
                    return False, f"Instrução não encontrada para tipo '{question_type}'"
                
                # Construir update dinâmico
                updates = []
                params = []
                
                if template is not None:
                    updates.append("template = %s")
                    params.append(template)
                
                if description is not None:
                    updates.append("description = %s")
                    params.append(description)
                
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)
                
                if not updates:
                    return True, "Nada para atualizar"
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                updates.append("version = version + 1")
                
                query = f"""
                    UPDATE question_type_instructions 
                    SET {', '.join(updates)} 
                    WHERE question_type = %s
                """
                params.append(question_type)
                
                cur.execute(query, params)
            
            # Invalidar cache
            if question_type in INSTRUCTION_CACHE:
                del INSTRUCTION_CACHE[question_type]
            
            print(f"Updated instruction '{question_type}'")
            return True, ""
            
        except Exception as e:
            print(f"Error updating instruction '{question_type}': {e}")
            return False, str(e)
    
    def list_all(self) -> list[dict]:
        """Lista todas as instruções."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT id, question_type, description, is_active, 
                       version, created_at, updated_at
                FROM question_type_instructions
                ORDER BY question_type
            """)
            return [dict(row) for row in cur.fetchall()]

# Instância global para uso
_question_type_instruction_repo = QuestionTypeInstructionRepository()
