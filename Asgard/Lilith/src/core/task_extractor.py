"""
Task Extractor - Detección automática de subtareas

Identifica subtareas en mensajes usando:
1. Listas numeradas (1. 2. 3.)
2. Bullets (-, *, •)
3. Keywords secuenciales (primero, luego, finalmente)
4. Conjunciones (y también, además)
"""

import logging
import re
from dataclasses import dataclass
from typing import List, NamedTuple, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTask:
    """Tarea extraída de un mensaje"""

    description: str
    confidence: float  # 0.0 - 1.0
    priority: int  # 1-5
    order: int  # Orden en el que apareció


class TaskExtractor:
    """
    Extrae subtareas de mensajes en lenguaje natural

    Métodos de extracción (de mayor a menor confianza):
    1. Listas numeradas: "1. Hacer X\n2. Hacer Y"
    2. Bullets: "- Configurar\n- Instalar"
    3. Keywords secuenciales: "Primero X, luego Y, finalmente Z"
    4. Conjunciones: "Haz X y también Y"
    """

    # Patterns para detección
    NUMBERED_LIST = re.compile(r"^\s*(\d+)[\.)]\s+(.+)$", re.MULTILINE)
    BULLET_LIST = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)

    # Pattern mejorado para keywords secuenciales
    SEQUENTIAL_PATTERN = re.compile(
        r"(?:^|\s|,|;)"  # Inicio de línea, espacio, coma o punto y coma
        r"(primero|primero que nada|en primer lugar|para empezar|lo primero|antes que nada|"  # Inicios
        r"luego|después|después de eso|entonces|a continuación|seguidamente|más tarde|"  # Medios
        r"finalmente|al final|por último|para terminar|para finalizar|concluyendo)"  # Finales
        r"[:\s,]+"  # Separador
        r"([^,;\.]+?(?=,(?:\s*(?:luego|después|finalmente|por último|y también|además)|$)|;|\.|$))",  # Contenido hasta siguiente keyword o fin
        re.IGNORECASE | re.MULTILINE,
    )

    CONJUNCTION_KEYWORDS = ["y también", "además", "así como", "y luego", "y después"]

    def extract_tasks(self, message: str) -> List[ExtractedTask]:
        """
        Extraer todas las subtareas del mensaje

        Args:
            message: Mensaje del usuario

        Returns:
            Lista de ExtractedTask
        """
        tasks = []

        # Método 1: Listas numeradas (confidence: 0.95)
        numbered_tasks = self._extract_numbered_list(message)
        if numbered_tasks:
            return numbered_tasks

        # Método 2: Bullets (confidence: 0.90)
        bullet_tasks = self._extract_bullet_list(message)
        if bullet_tasks:
            return bullet_tasks

        # Método 3: Keywords secuenciales (confidence: 0.75)
        sequential_tasks = self._extract_sequential_keywords(message)
        if sequential_tasks:
            return sequential_tasks

        # Método 4: Conjunciones (confidence: 0.60)
        conjunction_tasks = self._extract_conjunctions(message)
        if conjunction_tasks:
            return conjunction_tasks

        # No se encontraron subtareas explícitas
        return []

    def _extract_numbered_list(self, message: str) -> List[ExtractedTask]:
        """Extraer lista numerada (1. 2. 3.)"""
        matches = self.NUMBERED_LIST.findall(message)

        if len(matches) < 2:
            return []

        tasks = []
        for idx, (num, description) in enumerate(matches):
            tasks.append(
                ExtractedTask(
                    description=description.strip(),
                    confidence=0.95,
                    priority=3,  # Default medium
                    order=int(num),
                )
            )

        logger.debug(f"Extracted {len(tasks)} tasks from numbered list")
        return tasks

    def _extract_bullet_list(self, message: str) -> List[ExtractedTask]:
        """Extraer lista con bullets (- * •)"""
        matches = self.BULLET_LIST.findall(message)

        if len(matches) < 2:
            return []

        tasks = []
        for idx, description in enumerate(matches, 1):
            tasks.append(
                ExtractedTask(
                    description=description.strip(),
                    confidence=0.90,
                    priority=3,
                    order=idx,
                )
            )

        logger.debug(f"Extracted {len(tasks)} tasks from bullet list")
        return tasks

    def _extract_sequential_keywords(self, message: str) -> List[ExtractedTask]:
        """
        Extraer usando keywords secuenciales

        Ejemplo: "Primero haz X, luego Y, finalmente Z"
        """
        # Keywords por categoría
        start_keywords = [
            "primero",
            "primero que nada",
            "en primer lugar",
            "para empezar",
            "lo primero",
            "antes que nada",
            "inicialmente",
        ]
        middle_keywords = [
            "luego",
            "después",
            "después de eso",
            "entonces",
            "a continuación",
            "seguidamente",
            "más tarde",
            "posteriormente",
            "después",
            "segundo",
        ]
        end_keywords = [
            "finalmente",
            "al final",
            "por último",
            "para terminar",
            "para finalizar",
            "concluyendo",
            "por fin",
            "tercero",
        ]

        all_keywords = start_keywords + middle_keywords + end_keywords

        # Encontrar todas las ocurrencias de keywords en orden
        message_lower = message.lower()
        found = []  # Lista de (posición, keyword_original)

        for keyword in all_keywords:
            # Buscar keyword como palabra completa
            pattern = r"\b" + re.escape(keyword) + r"\b"
            for match in re.finditer(pattern, message_lower):
                found.append((match.start(), keyword, match.end()))

        if len(found) < 2:
            return []

        # Ordenar por posición
        found.sort(key=lambda x: x[0])

        tasks = []
        for idx, (start_pos, keyword, end_pos) in enumerate(found):
            # Determinar dónde termina esta tarea
            if idx < len(found) - 1:
                next_start = found[idx + 1][0]
                task_text = message[end_pos:next_start]
            else:
                task_text = message[end_pos:]

            # Limpiar: quitar puntuación inicial y conectores finales
            task_text = task_text.strip()
            task_text = re.sub(r"^[\s:;,]+", "", task_text)
            task_text = re.sub(r"[,;\.\s]+$", "", task_text)
            task_text = re.sub(r"\s+(?:y|e|o)\s*$", "", task_text, flags=re.IGNORECASE)

            if len(task_text) >= 1:
                tasks.append(
                    ExtractedTask(
                        description=task_text,
                        confidence=0.75,
                        priority=3,
                        order=idx + 1,
                    )
                )

        if tasks:
            logger.debug(f"Extracted {len(tasks)} tasks from sequential keywords")

        return tasks

    def _extract_conjunctions(self, message: str) -> List[ExtractedTask]:
        """
        Extraer usando conjunciones

        Ejemplo: "Configura el servidor y también instala las dependencias"
        """
        message_lower = message.lower()

        # Buscar conjunciones
        found_conj = []
        for conj in self.CONJUNCTION_KEYWORDS:
            if conj in message_lower:
                pos = message_lower.index(conj)
                found_conj.append((pos, conj))

        if not found_conj:
            return []

        # Ordenar por posición
        found_conj.sort()

        tasks = []

        # Primera tarea: texto antes de la primera conjunción
        first_conj_pos = found_conj[0][0]
        first_text = message[:first_conj_pos].strip()

        if len(first_text) > 5:
            tasks.append(
                ExtractedTask(
                    description=first_text, confidence=0.60, priority=3, order=1
                )
            )

        # Tareas intermedias
        for idx, (pos, conj) in enumerate(found_conj):
            start = pos + len(conj)

            if idx < len(found_conj) - 1:
                next_pos = found_conj[idx + 1][0]
                end = next_pos
            else:
                end = len(message)

            text = message[start:end].strip()
            text = re.sub(r"^[,:\s]+", "", text)
            text = re.sub(r"[,;\.\s]+$", "", text)

            if len(text) > 5:
                tasks.append(
                    ExtractedTask(
                        description=text, confidence=0.60, priority=3, order=idx + 2
                    )
                )

        if len(tasks) >= 2:
            logger.debug(f"Extracted {len(tasks)} tasks from conjunctions")
            return tasks

        return []

    def should_extract(self, message: str) -> bool:
        """
        Verificar si el mensaje probablemente contiene subtareas

        Heurística rápida antes de extracción completa
        """
        if not message:
            return False

        # Contiene números al inicio de línea seguidos de texto (lista numerada)
        if re.search(r"^\s*\d+[\.)]\s+\S", message, re.MULTILINE):
            return True

        # Contiene bullets seguidos de texto significativo
        if re.search(r"^\s*[-*•]\s+\S", message, re.MULTILINE):
            return True

        # Contiene múltiples keywords secuenciales (al menos 2 diferentes)
        message_lower = message.lower()
        found_keywords = set()
        for kw in [
            "primero",
            "luego",
            "después",
            "finalmente",
            "por último",
            "segundo",
            "tercero",
        ]:
            if kw in message_lower:
                found_keywords.add(kw)
        if len(found_keywords) >= 2:
            return True

        return False


# Singleton global
_task_extractor: Optional[TaskExtractor] = None


def get_task_extractor() -> TaskExtractor:
    """Obtener instancia singleton del extractor"""
    global _task_extractor
    if _task_extractor is None:
        _task_extractor = TaskExtractor()
    return _task_extractor


def extract_tasks(message: str) -> List[ExtractedTask]:
    """
    Función de conveniencia para extraer tareas

    Args:
        message: Mensaje del usuario

    Returns:
        Lista de ExtractedTask
    """
    extractor = get_task_extractor()
    return extractor.extract_tasks(message)


# Alias para compatibilidad
extract_tasks_simple = extract_tasks
