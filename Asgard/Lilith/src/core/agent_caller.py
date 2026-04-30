"""
Lilith 3.5 B.3 — AgentCaller: capa de delegación a herramientas/agentes.
Ejecuta un paso (tool) vía el registro. A.2: respuestas proactivas a errores (FileNotFound → sugerencias).
4.0 Fase 1: si se inyecta AgentRegistry, los pasos delegate_* se ejecutan vía el agente registrado.
"""
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .planner import Step
from .tools_v3.protocol import ToolResult
from .tools_v3.registry import ToolRegistryV3

if TYPE_CHECKING:
    from .agent_registry import AgentRegistry

logger = logging.getLogger("AgentCaller")


def _suggest_similar_paths(
    base_path: Path, failed_path: str, limit: int = 5
) -> List[str]:
    """A.2: busca archivos o carpetas con nombre similar al path que falló (misma carpeta o raíz)."""
    if not base_path.exists() or not failed_path or not failed_path.strip():
        return []
    name = Path(failed_path).name.lower()
    if not name:
        return []
    suggestions: List[str] = []
    try:
        # Buscar en el directorio del path fallido y en la raíz
        candidate_dir = (base_path / failed_path).resolve().parent
        if not candidate_dir.exists():
            candidate_dir = base_path
        for p in candidate_dir.iterdir():
            if len(suggestions) >= limit:
                break
            if name in p.name.lower() or (len(name) > 2 and p.name.lower() in name):
                try:
                    rel = p.relative_to(base_path)
                    suggestions.append(str(rel))
                except ValueError:
                    pass
    except Exception:
        pass
    return suggestions[:limit]


class AgentCaller:
    """
    Delega la ejecución de un paso al ToolRegistryV3 o al AgentRegistry (4.0 Fase 1).
    Si agent_registry está definido y el step.tool_name corresponde a un agente, ejecuta vía el agente.
    A.2: convierte FileNotFoundError en respuesta con sugerencias de archivos similares.
    """

    def __init__(
        self,
        base_path: Optional[Path] = None,
        agent_registry: Optional["AgentRegistry"] = None,
    ):
        self.base_path = Path(base_path) if base_path else None
        self.agent_registry = agent_registry

    def execute(
        self, step: Step, registry: ToolRegistryV3, skip_cache: bool = False
    ) -> ToolResult:
        """Ejecuta el paso y devuelve el ToolResult. B.1: cache para delegate_*; 3.7: skip_cache desactiva caché."""
        import time as _time

        _t0 = _time.monotonic()
        try:
            from .agent_response_cache import CACHE_AGENT_KEYS
            from .agent_response_cache import get as cache_get
            from .agent_response_cache import set as cache_set
            from .agent_yield import AgentYieldException

            if (
                not skip_cache
                and step.tool_name in CACHE_AGENT_KEYS
                and self.base_path
                and self.base_path.exists()
            ):
                cached = cache_get(self.base_path, step.tool_name, step.params)
                if cached is not None:
                    try:
                        from .agent_metrics import get_metrics

                        get_metrics().record_call(
                            step.tool_name, 0, success=True, cache_hit=True
                        )
                    except Exception:
                        pass
                    return cached
            # 3.6: truncar task si supera 4000 caracteres para evitar rechazo de API
            tool_name = step.tool_name
            params = dict(step.params)
            if tool_name in (
                "delegate_eva",
                "delegate_adan",
                "delegate_lucifer",
                "delegate_odin",
                "delegate_kimi_cli",
                "delegate_albedo",
                "delegate_local_irreverent",
                "delegate_web_scraper",
                "delegate_content_cleaner",
                "delegate_quality_filter",
                "delegate_data_structurer",
            ):
                task_val = (params.get("task") or "").strip()
                if len(task_val) > 4000:
                    params["task"] = task_val[:3990].rstrip() + "\n… (truncado)"

            # C.1: si es delegate_eva y la tarea es "sencilla", usar Lucifer
            if tool_name == "delegate_eva":
                from .delegation_classifier import should_use_lucifer

                if should_use_lucifer(
                    params.get("task") or "", params.get("context") or ""
                ):
                    logger.info(
                        "DelegationClassifier: tarea sencilla → delegate_lucifer en lugar de delegate_eva"
                    )
                    tool_name = "delegate_lucifer"

            # Mejora-4: si es delegate_adan y la tarea es compleja, escalar a delegate_eva
            if tool_name == "delegate_adan" and self.base_path:
                try:
                    from .agents.complexity_router import route_code_task

                    _routed = route_code_task(
                        params.get("task") or "", params.get("context") or ""
                    )
                    if _routed != "delegate_adan":
                        logger.info(
                            "complexity_router: delegate_adan → %s por complejidad",
                            _routed,
                        )
                        tool_name = _routed
                except Exception:
                    pass

            # ── Métricas en tiempo real: inicio de llamada ─────────────────────────────
            _success = False
            try:
                from .agent_metrics import get_metrics

                get_metrics().record_call_start(tool_name)
            except Exception:
                pass
            try:
                from .traffic_tracker import get_traffic_tracker

                if tool_name.startswith("delegate_"):
                    get_traffic_tracker().record_flow("lilith", tool_name, "direct")
            except Exception:
                pass
            # ───────────────────────────────────────────────────────────────────────────

            # 4.0 Fase 1: ejecutar vía AgentRegistry si el paso es un agente registrado
            if self.agent_registry:
                agent = self.agent_registry.get_by_tool_name(tool_name)
                if agent is not None:
                    try:
                        result = agent.execute(params)
                        if (
                            not skip_cache
                            and tool_name in CACHE_AGENT_KEYS
                            and self.base_path
                            and result
                            and not result.get("error")
                        ):
                            cache_set(self.base_path, tool_name, params, result)
                        _lat = (_time.monotonic() - _t0) * 1000
                        _success = not (
                            isinstance(result, dict) and result.get("error")
                        )
                        try:
                            from .agent_metrics import get_metrics

                            get_metrics().record_call(
                                tool_name,
                                _lat,
                                success=_success,
                                error_msg=str(result.get("error", ""))
                                if isinstance(result, dict)
                                else "",
                            )
                        except Exception:
                            pass
                        return result
                    finally:
                        try:
                            from .agent_metrics import get_metrics

                            get_metrics().record_call_end(tool_name, _success)
                        except Exception:
                            pass

            try:
                result = registry.execute(tool_name, params)
                if (
                    not skip_cache
                    and tool_name in CACHE_AGENT_KEYS
                    and self.base_path
                    and result
                    and not result.get("error")
                ):
                    cache_set(self.base_path, tool_name, params, result)
                _lat_ms = (_time.monotonic() - _t0) * 1000
                _err_msg = (
                    str(result.get("error", "")) if isinstance(result, dict) else ""
                )
                _success = not bool(_err_msg)
                try:
                    from .agent_metrics import get_metrics

                    get_metrics().record_call(
                        tool_name, _lat_ms, success=_success, error_msg=_err_msg
                    )
                except Exception:
                    pass
            finally:
                try:
                    from .agent_metrics import get_metrics

                    get_metrics().record_call_end(tool_name, _success)
                except Exception:
                    pass

            # Mejora-6: revisión inter-agente (Albedo centinela) para delegate_*
            if (
                _success
                and self.base_path
                and tool_name in ("delegate_adan", "delegate_eva", "delegate_odin")
            ):
                try:
                    from .agents.review_chain import get_review_chain

                    _response_text = (
                        result.get("response", "") if isinstance(result, dict) else ""
                    )
                    if _response_text:
                        _annotated = get_review_chain(
                            self.base_path
                        ).annotate_if_low_quality(
                            tool_name, params.get("task", ""), _response_text
                        )
                        if _annotated != _response_text and isinstance(result, dict):
                            result = dict(result)
                            result["response"] = _annotated
                except Exception as _re:
                    logger.debug("review_chain integration error: %s", _re)

            # Mejora-5: validación heurística de salida
            if _success:
                try:
                    from .agents.output_validator import get_validator

                    _response_text = (
                        result.get("response", "")
                        if isinstance(result, dict)
                        else str(result)
                    )
                    _vr = get_validator().validate(
                        _response_text, tool_name, params.get("task", "")
                    )
                    if not _vr.valid:
                        logger.warning(
                            "output_validator: %s → issues=%s score=%.2f suggestion=%s",
                            tool_name,
                            _vr.issues,
                            _vr.score,
                            _vr.suggestion,
                        )
                        # Registrar como éxito parcial en métricas
                        try:
                            from .agent_metrics import get_metrics

                            get_metrics().record_call(
                                tool_name + ":quality_warn",
                                0,
                                success=False,
                                error_msg=",".join(_vr.issues),
                            )
                        except Exception:
                            pass
                except Exception:
                    pass

            # Mejora-3: fallback chain si el resultado tiene error
            if not _success and self.base_path:
                try:
                    from .agents.fallback_chain import FallbackChain

                    _chain = FallbackChain(self.base_path)
                    _tried = [tool_name]
                    _fb_tool = _chain.next_after(step.tool_name, _err_msg, tried=_tried)
                    while _fb_tool:
                        _fb_result = registry.execute(_fb_tool, params)
                        _fb_err = (
                            str(_fb_result.get("error", ""))
                            if isinstance(_fb_result, dict)
                            else ""
                        )
                        _fb_ok = not bool(_fb_err)
                        try:
                            from .agent_metrics import get_metrics

                            get_metrics().record_call(
                                _fb_tool,
                                (_time.monotonic() - _t0) * 1000,
                                success=_fb_ok,
                                error_msg=_fb_err,
                            )
                        except Exception:
                            pass
                        if _fb_ok:
                            logger.info(
                                "fallback_chain: %s → %s OK", tool_name, _fb_tool
                            )
                            return _fb_result
                        _tried.append(_fb_tool)
                        _fb_tool = _chain.next_after(
                            step.tool_name, _fb_err, tried=_tried
                        )
                except Exception as _fe:
                    logger.debug("fallback_chain error: %s", _fe)
            return result
        except AgentYieldException:
            raise
        except FileNotFoundError as e:
            logger.warning(
                "AgentCaller: FileNotFound %s (%s): %s", step.tool_name, step.params, e
            )
            try:
                from .agent_metrics import get_metrics

                get_metrics().record_call(
                    step.tool_name,
                    (_time.monotonic() - _t0) * 1000,
                    success=False,
                    error_msg=str(e),
                )
            except Exception:
                pass
            path = (step.params.get("path") or "").strip() or str(e)
            if self.base_path and self.base_path.exists():
                similar = _suggest_similar_paths(self.base_path, path)
                if similar:
                    lines = [
                        "No encontré ese archivo o ruta. Posibles alternativas similares:"
                    ]
                    for s in similar:
                        lines.append(f"  · {s}")
                    return {"response": "\n".join(lines), "error": str(e)}
            return {
                "response": f"No encontré el archivo o ruta: {path}. Comprueba que exista y la ruta sea correcta.",
                "error": str(e),
            }
        except KeyError as e:
            logger.warning(
                "AgentCaller: KeyError %s (%s): %s", step.tool_name, step.params, e
            )
            try:
                from .agent_metrics import get_metrics

                get_metrics().record_call(
                    step.tool_name,
                    (_time.monotonic() - _t0) * 1000,
                    success=False,
                    error_msg=str(e),
                )
            except Exception:
                pass
            return {
                "response": f"Faltó un dato necesario para esta acción: {e}. Indica el parámetro correcto y lo intento de nuevo.",
                "error": str(e),
            }
        except Exception as e:
            logger.warning(
                "AgentCaller: %s (%s) failed: %s", step.tool_name, step.params, e
            )
            try:
                from .agent_metrics import get_metrics

                get_metrics().record_call(
                    step.tool_name,
                    (_time.monotonic() - _t0) * 1000,
                    success=False,
                    error_msg=str(e),
                )
            except Exception:
                pass
            return {"response": "", "error": str(e)}
