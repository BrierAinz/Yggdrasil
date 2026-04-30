"""
Tool Call Parser - Parser de llamadas a funciones

v5.0: Parsea tool_calls de diferentes formatos (OpenAI, Anthropic, Kimi).
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.functions.parser")


@dataclass
class ParsedToolCall:
    """Tool call parseado."""

    id: str
    name: str
    arguments: Dict[str, Any]
    raw: str = ""  # JSON original


class ToolCallParser:
    """
    Parser de tool calls de diferentes formatos.

    Soporta:
    - OpenAI / Kimi: message.tool_calls
    - Anthropic: content blocks con tool_use
    - Formato JSON explícito en mensaje
    """

    # Regex para detectar tool calls en texto plano
    TOOL_CALL_REGEX = re.compile(
        r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL | re.IGNORECASE
    )

    def __init__(self):
        self.parsed_count = 0

    def parse(
        self,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        provider: str = "openai",
    ) -> List[ParsedToolCall]:
        """
        Parsea tool calls de la respuesta del modelo.

        Args:
            content: Contenido del mensaje (para formato JSON/texto)
            tool_calls: Lista de tool_calls si viene estructurado
            provider: Proveedor del modelo

        Returns:
            Lista de tool calls parseados
        """
        results = []

        # 1. Intentar parsear tool_calls estructurados (OpenAI/Kimi)
        if tool_calls:
            for tc in tool_calls:
                try:
                    parsed = self._parse_structured(tc)
                    if parsed:
                        results.append(parsed)
                except Exception as e:
                    logger.warning(f"Error parseando tool_call estructurado: {e}")

        # 2. Si no hay tool_calls estructurados, buscar en contenido
        if not results and content:
            # Buscar tags <tool_call>
            tag_calls = self._parse_tag_format(content)
            results.extend(tag_calls)

            # Buscar JSON en markdown code blocks
            if not results:
                json_calls = self._parse_json_in_markdown(content)
                results.extend(json_calls)

        return results

    def _parse_structured(self, tool_call: Dict) -> Optional[ParsedToolCall]:
        """Parsea tool_call en formato OpenAI/Kimi."""
        try:
            call_id = tool_call.get("id", f"call_{self.parsed_count}")
            function = tool_call.get("function", {})
            name = function.get("name", "")

            # Arguments puede ser string JSON o dict
            args_raw = function.get("arguments", "{}")
            if isinstance(args_raw, str):
                arguments = json.loads(args_raw)
            else:
                arguments = args_raw

            self.parsed_count += 1

            return ParsedToolCall(
                id=call_id, name=name, arguments=arguments, raw=json.dumps(tool_call)
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error parseando tool_call estructurado: {e}")
            return None

    def _parse_tag_format(self, content: str) -> List[ParsedToolCall]:
        """Parsea formato <tool_call>{...}</tool_call>."""
        results = []

        for match in self.TOOL_CALL_REGEX.finditer(content):
            try:
                json_str = match.group(1)
                data = json.loads(json_str)

                parsed = ParsedToolCall(
                    id=data.get("id", f"call_{self.parsed_count}"),
                    name=data.get("name", ""),
                    arguments=data.get("arguments", {}),
                    raw=json_str,
                )
                results.append(parsed)
                self.parsed_count += 1

            except json.JSONDecodeError as e:
                logger.warning(f"Error parseando JSON en tag: {e}")

        return results

    def _parse_json_in_markdown(self, content: str) -> List[ParsedToolCall]:
        """Busca JSON en bloques de código markdown."""
        results = []

        # Buscar bloques ```json ... ```
        json_blocks = re.findall(r"```(?:json)?\s*({[\s\S]*?})\s*```", content)

        for block in json_blocks:
            try:
                data = json.loads(block)

                # Verificar si parece un tool call
                if "name" in data and ("arguments" in data or "parameters" in data):
                    parsed = ParsedToolCall(
                        id=data.get("id", f"call_{self.parsed_count}"),
                        name=data["name"],
                        arguments=data.get("arguments") or data.get("parameters", {}),
                        raw=block,
                    )
                    results.append(parsed)
                    self.parsed_count += 1

            except json.JSONDecodeError:
                continue

        return results

    def parse_anthropic_content(
        self, content_blocks: List[Dict]
    ) -> List[ParsedToolCall]:
        """
        Parsea content blocks de Anthropic.

        Args:
            content_blocks: Lista de content blocks

        Returns:
            Lista de tool calls
        """
        results = []

        for block in content_blocks:
            if block.get("type") == "tool_use":
                try:
                    parsed = ParsedToolCall(
                        id=block.get("id", f"call_{self.parsed_count}"),
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                        raw=json.dumps(block),
                    )
                    results.append(parsed)
                    self.parsed_count += 1

                except Exception as e:
                    logger.warning(f"Error parseando tool_use de Anthropic: {e}")

        return results

    def extract_tool_calls_from_text(
        self, text: str
    ) -> tuple[str, List[ParsedToolCall]]:
        """
        Extrae tool calls del texto y retorna texto limpio + tool calls.

        Args:
            text: Texto que puede contener tool calls

        Returns:
            Tuple de (texto_limpio, tool_calls)
        """
        tool_calls = []

        # Extraer tags <tool_call>
        for match in self.TOOL_CALL_REGEX.finditer(text):
            try:
                json_str = match.group(1)
                data = json.loads(json_str)

                parsed = ParsedToolCall(
                    id=data.get("id", f"call_{self.parsed_count}"),
                    name=data.get("name", ""),
                    arguments=data.get("arguments", {}),
                    raw=json_str,
                )
                tool_calls.append(parsed)
                self.parsed_count += 1

            except json.JSONDecodeError:
                continue

        # Limpiar texto
        clean_text = self.TOOL_CALL_REGEX.sub("", text).strip()

        return clean_text, tool_calls
