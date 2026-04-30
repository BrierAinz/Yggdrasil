"""
Response Generator - Converts tool outputs to natural language responses

Transforms structured tool outputs into conversational responses suitable for
natural language interfaces with context awareness and personalization.
"""

import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.llm.grok_client import GrokClient
from src.llm.ollama_client import OllamaClient


class ResponseGenerator:
    """
    Converts tool outputs into natural language responses

    Handles different response types:
    - Success responses with results
    - Error responses with explanations
    - Streamed responses for long-running tasks
    - Clarification requests
    """

    def __init__(self, primary_provider="grok"):
        self.providers = {"ollama": OllamaClient(), "grok": GrokClient()}
        self.current_provider = primary_provider
        self.response_templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        import datetime

        now = datetime.datetime.now()
        current_hour = now.hour

        if 6 <= current_hour < 12:
            time_period = "morning"
        elif 12 <= current_hour < 18:
            time_period = "afternoon"
        elif 18 <= current_hour < 23:
            time_period = "evening"
        else:
            time_period = "late_night"

        return {
            "identity_query": {
                "morning": f"Buenos dias! Soy Lilith, tu asistente. Que necesitas esta {time_period}?",
                "afternoon": f"Hola! Soy Lilith. En que puedo ayudarte esta {time_period}?",
                "evening": f"Buenas noches! Soy Lilith. Que necesitas esta {time_period}?",
                "late_night": f"Soy Lilith. A estas horas ({time_period}) sigo aqui para ayudarte.",
            },
            "greeting": {
                "success": f"Hola! Como estas? Que puedo hacer esta {time_period}?",
            },
            "farewell": {
                "success": "Hasta luego! Aqui estoy si me necesitas otra vez.",
            },
            # Templates adicionales para mantener compatibilidad
            "general_conversation": {
                "thanks": "Â¡Con gusto! ðŸ˜Š Para mÃ­ es un placer ayudarte. Â¿Necesitas algo mÃ¡s?",
                "please": "Â¡Claro! ðŸ‘ Dame un momento y te ayudo con eso.",
                "confirmation": "Perfecto, entendido. âœ“",
                "great": "Â¡Genial! ðŸŽ‰ Me alegra haber podido ayudar.",
                "success": "Claro, estoy aquÃ­ para conversar. Â¿QuÃ© te gustarÃ­a hablar?",
            },
            "CodeAnalyzer": {
                "success": "RevisÃ© el cÃ³digo en {target}. EncontrÃ© {issue_count} problemas que deberÃ­amos corregir.",
                "error": "No pude analizar el cÃ³digo en {target}. Error: {error_message}",
                "no_issues": "RevisÃ© el cÃ³digo en {target} y no encontrÃ© problemas importantes. Â¡El cÃ³digo se ve bien!",
                "critical": "URGENTE: EncontrÃ© problemas crÃ­ticos en {target}. Recomiendo corregirlos antes de continuar.",
            },
            "Research": {
                "success": "EncontrÃ© informaciÃ³n sobre '{query}'. AquÃ­ estÃ¡n los hallazgos principales:\n\n{summary}",
                "error": "No pude encontrar informaciÃ³n confiable sobre '{query}'. Error: {error_message}",
                "multiple_sources": "InvestiguÃ© '{query}' y encontrÃ© {source_count} fuentes relevantes.\n\n{summary}",
            },
            "WebBrowser": {
                "success": "VisitÃ© {url} y extraje la informaciÃ³n que necesitabas.\n\n{summary}",
                "error": "No pude acceder a {url}. Error: {error_message}",
                "navigation": "NaveguÃ© a {url}. Carga completa y listo para interactuar.",
                "screenshot": "CapturÃ© la pÃ¡gina {url} y guardÃ© la imagen en {file_path}.",
            },
            "ImageProcessor": {
                "success": "GenerÃ© una imagen con tu solicitud: '{prompt}'. Archivo guardado en: {file_path}",
                "error": "No pude generar la imagen para '{prompt}'. Error: {error_message}",
                "processing": "Generando imagen... Esto puede tomar unos momentos.",
                "complete": "Â¡Imagen generada exitosamente! Guardada en: {file_path}",
            },
            "GitTools": {
                "success": "Comando git completado: {action}",
                "error": "Error ejecutando git {action}: {error_message}",
                "needs_push": "Commit creado exitosamente. Recuerda hacer push cuando estÃ©s listo.",
                "status_clean": "Tu repositorio estÃ¡ limpio. No hay cambios sin commit.",
            },
            "SystemExecutor": {
                "success": "Comando ejecutado exitosamente:\n\n```\n{command}\n```\n\nSalida:\n{output}",
                "error": "Error ejecutando el comando: {error_message}",
                "timeout": "El comando tomÃ³ demasiado tiempo y fue detenido.",
                "large_output": "Comando completado. Salida fue muy larga, mostrando los primeros {length} caracteres:\n\n{output}",
            },
            "CodeEditor": {
                "success": "He modificado el archivo con Ã©xito. Se creÃ³ un respaldo en `{backup}` por seguridad.",
                "error": "No pude modificar el archivo. {error_message}",
                "write": "He creado/sobrescrito el archivo con Ã©xito. Respaldo: `{backup}`",
                "insert": "He insertado el cÃ³digo en la lÃ­nea {line_number} correctamente.",
            },
            "GrepTool": {
                "success": "EncontrÃ© {match_count} coincidencias para '{pattern}' en el proyecto.",
                "error": "Hubo un error al realizar la bÃºsqueda: {error_message}",
                "no_matches": "No encontrÃ© ninguna coincidencia para '{pattern}' en los archivos especificados.",
                "files": "EncontrÃ© {file_count} archivos que coinciden con tu criterio.",
            },
            "PlanningEngine": {
                "success": "CreÃ© un plan para tu tarea: '{task}'.\n\nPasos:\n{steps}\n\nDuraciÃ³n estimada: {duration}",
                "error": "No pude crear un plan para '{task}'. Error: {error_message}",
                "complex_task": "Esta tarea es compleja. He dividido en {step_count} pasos principales.\n\n{summary}",
            },
            # NUEVOS: Templates para skills autÃ³nomas
            "FileManager": {
                "success": "OperaciÃ³n de archivo completada exitosamente.",
                "error": "Error en operaciÃ³n de archivo: {error_message}",
                "read": "LeÃ­ el archivo `{path}`. Contiene {lines} lÃ­neas:\n\n```\n{content_preview}\n```",
                "write": "Archivo `{path}` creado exitosamente ({size_human}).",
                "list": "EncontrÃ© {total_files} archivos y {total_dirs} directorios en `{path}`:\n\n{file_list}",
                "search": "BÃºsqueda completada. EncontrÃ© {total_name_matches} coincidencias por nombre y {total_content_matches} en contenido.",
                "info": "InformaciÃ³n de `{path}`:\n- Tipo: {type}\n- TamaÃ±o: {size_human}\n- Es texto: {is_text}",
                "mkdir": "Directorio `{path}` creado exitosamente.",
                "delete": "Eliminado exitosamente: `{path}`",
            },
            "ProjectScanner": {
                "success": "AnÃ¡lisis de proyecto completado.",
                "error": "Error analizando proyecto: {error_message}",
                "scan_summary": "Proyecto: **{project_name}**\n\nðŸ“‹ **InformaciÃ³n General**\n- Tipo: {project_type} (confianza: {confidence}%)\n- Lenguajes: {languages}\n- Frameworks: {frameworks}\n\nðŸ“Š **EstadÃ­sticas**\n- Total archivos: {total_files}\n- Archivos de cÃ³digo: {source_files}\n- Archivos de test: {test_files}\n- Entry points: {entry_point_count}\n\nðŸ’¡ **Recomendaciones**\n{recommendations}",
                "scan_simple": "DetectÃ© un proyecto **{project_type}** con {total_files} archivos. Principales tecnologÃ­as: {languages}.",
            },
            "TaskTracker": {
                "success": "OperaciÃ³n de planificaciÃ³n completada.",
                "error": "Error en planificaciÃ³n: {error_message}",
                "plan_created": "Plan creado: **{name}**\nID: `{plan_id}`\nDescripciÃ³n: {description}",
                "task_added": "Tarea agregada al plan: **{task_name}** (Prioridad: {priority})",
                "plan_executed": "Plan ejecutado exitosamente.\nâœ“ Tareas completadas: {completed_tasks}\nâ± DuraciÃ³n: {duration:.2f}s",
                "summary": "Resumen del plan **{name}**:\n- Total tareas: {total_tasks}\n- Progreso: {progress}%\n- Estado: {status}",
                "streaming_progress": "Ejecutando plan... {progress}% completado.",
            },
            # NUEVO: CodeRefactor templates
            "CodeRefactor": {
                "success": "RefactorizaciÃ³n completada exitosamente.",
                "error": "Error en refactorizaciÃ³n: {error_message}",
                "rename": "SÃ­mbolo **{old_name}** renombrado a **{new_name}** exitosamente.\n- Tipo: {symbol_type}\n- LÃ­nea: {line}\n- Usos actualizados: {usages_count}",
                "extract_method": "MÃ©todo **{method_name}** extraÃ­do exitosamente.\n- LÃ­neas: {start_line}-{end_line}\n- Variables usadas: {variables_used}",
                "optimize_imports": "Imports optimizados.\n- Eliminados: {unused_removed}\n- Total: {total_imports}",
                "convert_to_async": "FunciÃ³n **{function_name}** convertida a async/await.",
                "add_type_hints": "Type hints agregados a {functions_modified} funciones.",
                "diff_preview": "Cambios realizados:\n```diff\n{diff_preview}\n```",
            },
            # NUEVO: TestRunner templates
            "TestRunner": {
                "success": "Tests ejecutados exitosamente.",
                "error": "Error ejecutando tests: {error_message}",
                "run_tests": "Resultados de tests:\n**Framework:** {framework}\n**Total:** {total_tests}\n**âœ“ Pasaron:** {passed}\n**âœ— Fallaron:** {failed}\n**â—‹ Skipped:** {skipped}\n**â± DuraciÃ³n:** {duration:.2f}s",
                "coverage": "**Cobertura de CÃ³digo**\n**Overall:** {overall_coverage}%\n**LÃ­neas cubiertas:** {covered_lines}/{total_lines}\n\nArchivos con baja cobertura:\n{low_coverage_files}",
                "missing_tests": "**Tests Faltantes**\n**MÃ³dulos analizados:** {total_source_files}\n**Con tests:** {tested_modules}\n**Sin tests:** {missing_tests_count}\n\nEjemplos:\n{missing_tests}",
                "test_details": "Detalles:\n{test_results}",
            },
            "clarify": {
                "request": "Necesito aclaraciÃ³n: {question}",
                "follow_up": "Gracias por la aclaraciÃ³n. ProcederÃ© con tu solicitud.",
                "parameter_needed": "Para continuar, necesito que me proporciones: {parameter}.",
            },
            "default": {
                "success": "Tarea completada exitosamente.",
                "error": "OcurriÃ³ un error: {error_message}",
                "processing": "Procesando tu solicitud...",
                "complete": "Proceso completado.",
            },
        }

    def generate_response(
        self, tool_name: str, tool_output: Dict, context: Optional[Dict] = None
    ) -> str:
        """
        Generate natural language response from tool output

        Args:
            tool_name: Name of the tool that produced output
            tool_output: Structured output from the tool
            context: Session context for personalization

        Returns:
            Natural language response string
        """
        try:
            # Extract basic info
            success = tool_output.get("success", False)
            error_message = tool_output.get("error_message", "")
            data = tool_output.get("data", {})

            # Get tool-specific template
            templates = self.response_templates.get(
                tool_name, self.response_templates["default"]
            )

            if not success:
                # Error response
                return self._generate_error_response(
                    templates, data, error_message, context, tool_name
                )

            # Success response
            return self._generate_success_response(tool_name, templates, data, context)

        except Exception as e:
            # Fallback response on generation error
            return f"Tuve problemas procesando el resultado: {str(e)}. Pero la tarea fue completada."

    def _generate_success_response(
        self,
        tool_name: str,
        templates: Dict,
        data: Dict,
        context: Optional[Dict] = None,
    ) -> str:
        """Generate success response using templates or LLM"""

        # Check for time-contextual templates (greeting, identity, etc.)
        if context and "time_context" in context:
            period = context["time_context"].get("period", "morning")
            if period in templates:
                return templates[period]

        # Try standard template
        template_response = self._apply_template(
            templates, data, success=True, tool_name=tool_name
        )

        if template_response and "{undefined" not in template_response:
            return template_response

        # Fallback to LLM for complex responses
        return self._llm_generate_response(
            tool_name, data, success=True, context=context
        )

    def _generate_error_response(
        self,
        templates: Dict,
        data: Dict,
        error_message: str,
        context: Optional[Dict] = None,
        tool_name: str = None,
    ) -> str:
        """Generate error response"""
        # Try template first
        data_with_error = {**data, "error_message": error_message}
        template_response = self._apply_template(
            templates, data_with_error, success=False, tool_name=tool_name
        )

        if template_response and "{undefined" not in template_response:
            return template_response

        # Fallback to generic error
        return f"Ocurri un error al procesar tu solicitud: {error_message}. Por favor, intenta de nuevo o reformula tu peticion."

    def _apply_template(
        self, templates: Dict, data: Dict, success: bool = True, tool_name: str = None
    ) -> Optional[str]:
        """Apply response template with data interpolation"""
        template_key = "success" if success else "error"

        # Handle special cases based on data content and tool
        if tool_name or data.get("tool"):
            tn = tool_name or data.get("tool")

            if tn == "CodeAnalyzer" and success:
                issue_count = len(data.get("issues", []))
                severity = data.get("max_severity", "low")

                if issue_count == 0:
                    template_key = "no_issues"
                elif severity in ["critical", "high"]:
                    template_key = "critical"

            elif tn == "SystemExecutor" and success:
                output_length = len(data.get("output", ""))
                if output_length > 2000:
                    template_key = "large_output"

            # NUEVOS: Casos especiales para skills autÃ³nomas
            elif tn == "FileManager" and success:
                action = data.get("action", "")
                if action in templates:
                    template_key = action
                # Preparar preview de contenido para lecturas
                if action == "read" and "content" in data:
                    content = data["content"]
                    if content:
                        lines = content.split("\n")
                        data["content_preview"] = "\n".join(
                            lines[:20]
                        )  # Primeras 20 lÃ­neas
                        if len(lines) > 20:
                            data["content_preview"] += "\n... (truncado)"
                    else:
                        data["content_preview"] = "[Archivo vacÃ­o]"
                # Formatear lista de archivos
                if action == "list" and "files" in data:
                    files = data.get("files", [])
                    file_list = []
                    for f in files[:10]:  # Mostrar primeros 10
                        file_list.append(
                            f"- {f['name']} ({f.get('size_human', 'N/A')})"
                        )
                    if len(files) > 10:
                        file_list.append(f"... y {len(files) - 10} mÃ¡s")
                    data["file_list"] = (
                        "\n".join(file_list) if file_list else "[Directorio vacÃ­o]"
                    )

            elif tn == "ProjectScanner" and success:
                # Usar template resumido o completo segÃºn el contexto
                if data.get("total_files", 0) > 0:
                    # Formatear datos para mejor legibilidad
                    languages = ", ".join(
                        data.get("summary", {}).get("languages", [])[:5]
                    )
                    frameworks = ", ".join(
                        data.get("summary", {}).get("frameworks", [])[:5]
                    )
                    data["languages"] = languages if languages else "No detectados"
                    data["frameworks"] = frameworks if frameworks else "No detectados"
                    data["total_files"] = data.get("summary", {}).get("total_files", 0)
                    data["source_files"] = data.get("summary", {}).get(
                        "source_files", 0
                    )
                    data["test_files"] = data.get("summary", {}).get("test_files", 0)
                    data["entry_point_count"] = len(data.get("entry_points", []))
                    # Formatear recomendaciones
                    recommendations = data.get("recommendations", [])
                    if recommendations:
                        data["recommendations"] = "\n".join(
                            f"- {r}" for r in recommendations[:5]
                        )
                    else:
                        data["recommendations"] = "_Sin recomendaciones_"
                    # Elegir template
                    template_key = (
                        "scan_summary" if "scan_summary" in templates else "success"
                    )

            elif tn == "TaskTracker" and success:
                action = data.get("action", "")
                # Mapear acciones a templates especÃ­ficos
                action_to_template = {
                    "create_plan": "plan_created",
                    "add_task": "task_added",
                    "execute_plan": "plan_executed",
                    "get_summary": "summary",
                }
                if (
                    action in action_to_template
                    and action_to_template[action] in templates
                ):
                    template_key = action_to_template[action]

        # Get template
        template = templates.get(
            template_key, templates.get("success" if success else "error", "")
        )

        if not template:
            return None

        # Simple string interpolation
        try:
            # Prepare data for interpolation
            interpolation_data = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    interpolation_data[key] = self._format_complex_data(value)
                else:
                    interpolation_data[key] = str(value) if value is not None else ""

            # Interpolate
            import string

            return string.Formatter().vformat(template, (), interpolation_data)

        except Exception:
            return None

    def _format_complex_data(self, data: Any) -> str:
        """Format complex data structures for natural language"""
        if isinstance(data, dict):
            # Format key findings
            if "findings" in data or "results" in data:
                items = data.get("findings", data.get("results", []))
                return self._format_list_summary(items[:3])  # Top 3

            # Format simple dict
            formatted = ", ".join([f"{k}: {v}" for k, v in list(data.items())[:3]])
            if len(data) > 3:
                formatted += " y mas..."
            return formatted

        elif isinstance(data, list):
            return self._format_list_summary(data[:5])  # Top 5 items

        return str(data)[:200]  # Truncate long strings

    def _format_list_summary(self, items: List) -> str:
        """Format list as natural language summary"""
        if not items:
            return "nada encontrado"

        if len(items) == 1:
            return str(items[0])

        if len(items) == 2:
            return f"{items[0]} y {items[1]}"

        return ", ".join(str(item) for item in items[:-1]) + f" y {items[-1]}"

    def _llm_generate_response(
        self,
        tool_name: str,
        data: Dict,
        success: bool,
        context: Optional[Dict] = None,
        model_override: str = None,
    ) -> str:
        """Use LLM to generate response for complex cases"""
        prompt = self._build_response_prompt(tool_name, data, success, context)

        # Decide which client to use based on model_override
        client = self.providers.get("grok")  # Default
        target_model = None

        if model_override:
            if "grok" in model_override.lower():
                client = self.providers.get("grok")
            elif (
                "qwen" in model_override.lower() or "deepseek" in model_override.lower()
            ):
                client = self.providers.get("ollama")
                target_model = model_override

        try:
            response = client.generate_text(
                prompt, max_tokens=300, temperature=0.3, model=target_model
            )
            return (
                response.strip() if response else self._get_fallback_response(success)
            )
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            return self._get_fallback_response(success)

    def _build_response_prompt(
        self, tool_name: str, data: Dict, success: bool, context: Optional[Dict] = None
    ) -> str:
        """Build prompt for LLM response generation"""
        base_prompt = f"Eres Lilith, un asistente AI amigable y profesional. El usuario me acaba de pedir que use la herramienta '{tool_name}'. {'La tarea se complet con exito.' if success else 'Ocurri un error durante la ejecucin.'} Datos de salida de la herramienta: {json.dumps(data, indent=2, ensure_ascii=False)} Por favor, proporciona una respuesta natural y conversacional en ESPAOL que: {'- Informe al usuario que la tarea se complet con exito' if success else '- Explique el error de forma clara y amigable'} {'- Incluya los hallazgos o resultados relevantes' if success else ''} - Sea concisa pero informativa - Use un tono profesional pero accesible - Evite tecnicismos innecesarios si no son relevantes Respuesta:"

        # Add context if available
        if context:
            history = context.get("conversation_history", [])
            if history:
                recent_messages = history[-3:]  # Last 3 messages
                context_section = f"\n\nContexto reciente:\n{json.dumps(recent_messages, indent=2, ensure_ascii=False)}"
                base_prompt = base_prompt.replace(
                    "Respuesta:", f"{context_section}\n\nRespuesta:"
                )

        return base_prompt

    def _get_fallback_response(self, success: bool) -> str:
        """Get generic fallback response"""
        if success:
            return "Tuve problemas generando una respuesta detallada, pero la tarea se complet exitosamente."
        else:
            return (
                "Tuve problemas procesando la solicitud. Por favor, intenta de nuevo."
            )

    def generate_streaming_response(
        self, tool_name: str, stream_data: Dict
    ) -> Optional[str]:
        """
        Generate response for streaming tool updates

        Args:
            tool_name: Tool generating the stream
            stream_data: Current stream data

        Returns:
            Streaming message or None if no update needed
        """
        status = stream_data.get("status", "")
        progress = stream_data.get("progress", 0)

        streaming_messages = {
            "ImageProcessor": {
                "processing": f"Generando imagen... {progress}% completado.",
                "downloading_model": f"Descargando modelos necesarios... {progress}%.",
                "preprocessing": "Preprocesando imagen...",
                "generating": "Generando imagen (esto puede tomar 30-60 segundos)...",
                "postprocessing": "Finalizando imagen...",
                "complete": "Imagen generada exitosamente!",
            },
            "Research": {
                "searching": f"Buscando informacion... {progress}% completado.",
                "analyzing": "Analizando resultados...",
                "synthesizing": "Sintetizando hallazgos...",
                "complete": "Investigacion completada!",
            },
            "WebBrowser": {
                "loading": f"Cargando pagina... {progress}%.",
                "rendering": "Renderizando contenido...",
                "extracting": "Extrayendo informacion...",
                "complete": "Navegacion completada!",
            },
            "CodeAnalyzer": {
                "reading": "Leyendo archivos de codigo...",
                "parsing": "Analizando sintaxis...",
                "analyzing": f"Buscando problemas... {progress}% completado.",
                "formatting": "Formatando resultados...",
                "complete": "Analisis de codigo completado!",
            },
            "PlanningEngine": {
                "analyzing": "Analizando tu solicitud...",
                "generating": f"Generando pasos... {progress}%.",
                "validating": "Validando plan...",
                "complete": "Plan creado exitosamente!",
            },
            # NUEVOS: Streaming messages para skills autÃ³nomas
            "FileManager": {
                "reading": "Leyendo archivo...",
                "writing": "Escribiendo archivo... {progress}%",
                "listing": "Listando directorio...",
                "searching": "Buscando archivos... {progress}% completado",
                "complete": "OperaciÃ³n de archivo completada!",
            },
            "ProjectScanner": {
                "scanning": "Escaneando proyecto... {progress}%",
                "analyzing": "Analizando estructura...",
                "detecting_languages": "Detectando lenguajes...",
                "finding_entrypoints": "Buscando puntos de entrada...",
                "complete": "AnÃ¡lisis de proyecto completado!",
            },
            "TaskTracker": {
                "creating_plan": "Creando plan...",
                "adding_tasks": "Agregando tareas...",
                "executing": "Ejecutando tarea {current}/{total}...",
                "progress": "Progreso del plan: {progress}%",
                "retrying": "Reintentando tarea fallida ({retry_count}/{max_retries})...",
                "complete": "Plan ejecutado exitosamente!",
            },
            # NUEVO: CodeRefactor streaming messages
            "CodeRefactor": {
                "analyzing": "Analizando cÃ³digo...",
                "renaming": "Renombrando sÃ­mbolo...",
                "extracting": "Extrayendo mÃ©todo...",
                "optimizing": "Optimizando imports...",
                "converting": "Convirtiendo cÃ³digo...",
                "adding_hints": "Agregando type hints...",
                "creating_backup": "Creando backup...",
                "complete": "RefactorizaciÃ³n completada!",
            },
            # NUEVO: TestRunner streaming messages
            "TestRunner": {
                "detecting": "Detectando framework de testing...",
                "running": "Ejecutando tests... {progress}%",
                "collecting": "Recolectando resultados...",
                "analyzing_coverage": "Analizando cobertura...",
                "finding_missing": "Buscando tests faltantes...",
                "complete": "Tests completados!",
            },
        }

        tool_messages = streaming_messages.get(tool_name, {})
        return tool_messages.get(status)

    def generate_clarification_response(
        self, question: str, context: Optional[Dict] = None
    ) -> str:
        """Generate response for clarification question"""
        return f"Necesito aclarar algo: {question}"

    def format_code_output(
        self, code: str, language: str = "python", max_length: int = 500
    ) -> str:
        """Format code output for display in conversation"""
        if not code:
            return ""

        if len(code) > max_length:
            code = code[:max_length] + "... (truncado por longitud)"

        return f"```{language}\n{code}\n```"

    def format_list_output(self, items: List[str], title: str = "Resultados:") -> str:
        """Format list as conversational bullet points"""
        if not items:
            return "No se encontraron resultados."

        formatted = f"{title}\n"
        for i, item in enumerate(items, 1):
            # Add emoji indicators for visual appeal
            if "error" in item.lower() or "fail" in item.lower():
                prefix = "[FAIL]"
            elif "warning" in item.lower():
                prefix = "[WARN]"
            elif "success" in item.lower() or "ok" in item.lower():
                prefix = "[OK]"
            else:
                prefix = f"{i}."

            formatted += f"{prefix} {item}\n"

        return formatted.strip()

    def generate_conversational_response(
        self, intent_type: str, user_message: str, tool_suggestions: List[str] = None
    ) -> str:
        """
        Generate natural conversational response based on detected intent

        Args:
            intent_type: The detected intent (greeting, farewell, etc.)
            user_message: The original user message
            tool_suggestions: Optional list of suggested tools

        Returns:
            Natural language response string
        """
        import datetime

        now = datetime.datetime.now()
        hour = now.hour

        # Determine time period
        if 6 <= hour < 12:
            time_greeting = "Buenos días"
            time_period = "mañana"
        elif 12 <= hour < 18:
            time_greeting = "Buenas tardes"
            time_period = "tarde"
        else:
            time_greeting = "Buenas noches"
            time_period = "noche"

        # Intent-specific responses
        responses = {
            "greeting": [
                f"{time_greeting}! Soy Lilith. ¿En qué puedo ayudarte hoy?",
                f"¡Hola! {time_greeting}. ¿Qué necesitas?",
                f"{time_greeting}. Estoy lista para ayudarte. ¿Qué tienes en mente?",
            ],
            "farewell": [
                "¡Hasta luego! Estaré aquí si me necesitas.",
                "Adiós. Que tengas un buen día.",
                "Nos vemos. No dudes en llamarme cuando necesites ayuda.",
            ],
            "identity_query": [
                f"{time_greeting}! Soy Lilith, tu asistente de desarrollo. Puedo ayudarte con código, análisis de proyectos, tests, git y mucho más. ¿Qué necesitas?",
                "Soy Lilith, una asistente AI diseñada para ayudarte con tareas de desarrollo de software. ¿En qué puedo ayudarte?",
                f"{time_greeting}! Lilith a tu servicio. Tengo 19 herramientas listas para ayudarte con tu proyecto. ¿Qué necesitas?",
            ],
            "general_conversation": [
                "Entendido. ¿Hay algo específico en lo que pueda ayudarte con tu proyecto?",
                "¡Perfecto! Estoy aquí para lo que necesites. ¿Qué quieres hacer?",
                "Claro. ¿Necesitas ayuda con código, análisis, o algo más?",
            ],
            "code_review": [
                "Voy a revisar el código. Dame un momento...",
                "Analizando el código en busca de problemas y mejoras...",
                "Revisando la calidad del código y posibles optimizaciones...",
            ],
            "code_security": [
                "Escaneando el código en busca de vulnerabilidades de seguridad...",
                "Analizando posibles problemas de seguridad...",
                "Revisando el código con enfoque en seguridad...",
            ],
            "research": [
                "Voy a investigar eso para ti. Un momento...",
                "Buscando información relevante...",
                "Investigando el tema. Esto puede tomar unos segundos...",
            ],
            "web_visit": [
                "Abriendo la página web...",
                "Navegando al sitio solicitado...",
                "Accediendo a la página...",
            ],
            "generate": [
                "Generando el contenido solicitado...",
                "Creando la imagen/archivo...",
                "Procesando tu solicitud de generación...",
            ],
            "system_execute": [
                "Ejecutando el comando...",
                "Procesando la instrucción...",
                "Ejecutando...",
            ],
            "memory_query": [
                "Dejame revisar lo que recuerdo sobre eso...",
                "Buscando en mi memoria...",
                "Revisando información previa...",
            ],
            "code_edit": [
                "Editando el archivo...",
                "Realizando los cambios solicitados...",
                "Modificando el código...",
            ],
            "code_search": [
                "Buscando en el código...",
                "Escaneando los archivos...",
                "Buscando coincidencias...",
            ],
            "file_read": [
                "Leyendo el archivo...",
                "Cargando el contenido...",
                "Abriendo el archivo...",
            ],
            "file_write": [
                "Creando el archivo...",
                "Escribiendo el contenido...",
                "Guardando el archivo...",
            ],
            "file_list": [
                "Listando archivos...",
                "Obteniendo el contenido del directorio...",
                "Escaneando archivos...",
            ],
            "project_scan": [
                "Analizando el proyecto...",
                "Escaneando la estructura del proyecto...",
                "Obteniendo información del proyecto...",
            ],
            "git_status": [
                "Verificando el estado del repositorio...",
                "Consultando git...",
                "Revisando cambios...",
            ],
            "run_tests": [
                "Ejecutando los tests...",
                "Corriendo las pruebas...",
                "Ejecutando el suite de tests...",
            ],
            "unknown": [
                "No estoy segura de entender. ¿Podrías reformular o ser más específico?",
                "¿Podrías darme más detalles sobre lo que necesitas?",
                "No entendí bien. ¿Quieres que analice código, busque algo, o hagas otra cosa?",
            ],
        }

        # Select response based on intent
        import random

        intent_responses = responses.get(intent_type, responses["unknown"])
        response = random.choice(intent_responses)

        # Add tool suggestions if available (for relevant intents)
        if tool_suggestions and intent_type not in [
            "greeting",
            "farewell",
            "identity_query",
        ]:
            if len(tool_suggestions) == 1:
                response += f" Usaré {tool_suggestions[0]} para esto."
            elif len(tool_suggestions) > 1:
                tools_str = ", ".join(tool_suggestions[:3])
                response += f" Puedo usar: {tools_str}."

        return response


# Test harness for development
if __name__ == "__main__":

    def test_response_generator():
        """Test the response generator"""
        print("Testing Response Generator")
        print("=" * 60)

        generator = ResponseGenerator()

        # Test cases
        test_cases = [
            {
                "name": "CodeAnalyzer - Issues found",
                "tool": "CodeAnalyzer",
                "output": {
                    "success": True,
                    "data": {
                        "target": "test.py",
                        "issues": ["variable no usada", "import redundante"],
                        "issue_count": 2,
                        "max_severity": "medium",
                    },
                },
            },
            {
                "name": "Research - Results found",
                "tool": "Research",
                "output": {
                    "success": True,
                    "data": {
                        "query": "async Python",
                        "results": [
                            "async/await disponible desde Python 3.5",
                            "Ideal para I/O bound operations",
                            "Necesita event loop",
                        ],
                        "source_count": 3,
                    },
                },
            },
            {
                "name": "SystemExecutor - Command output",
                "tool": "SystemExecutor",
                "output": {
                    "success": True,
                    "data": {
                        "command": "dir",
                        "output": "archivo1.txt  archivo2.py  carpeta/",
                        "exit_code": 0,
                    },
                },
            },
            {
                "name": "ImageProcessor - Generation complete",
                "tool": "ImageProcessor",
                "output": {
                    "success": True,
                    "data": {
                        "prompt": "un gato astronauta",
                        "file_path": "D:/output/cat_astronaut.png",
                    },
                },
            },
            {
                "name": "Error case",
                "tool": "WebBrowser",
                "output": {
                    "success": False,
                    "error_message": "Connection timeout",
                    "data": {"url": "https://ejemplo.com"},
                },
            },
        ]

        for test in test_cases:
            print(f"\n[Test] {test['name']}")

            response = generator.generate_response(test["tool"], test["output"])

            print(f"  Response: {response[:150]}...")

        print("\n[Test] Streaming responses")
        streaming_cases = [
            {"tool": "ImageProcessor", "status": "processing", "progress": 50},
            {"tool": "Research", "status": "searching", "progress": 75},
            {"tool": "CodeAnalyzer", "status": "complete", "progress": 100},
        ]

        for case in streaming_cases:
            stream_response = generator.generate_streaming_response(case["tool"], case)
            print(f"  {case['tool']} ({case['status']}): {stream_response}")

        print("\n[OK] Tests completed!")

    # Run tests
    test_response_generator()
