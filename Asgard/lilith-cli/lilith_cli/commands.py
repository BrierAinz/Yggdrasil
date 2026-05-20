"""Slash command registry for Yggdrasil CLI v6.0.

Each command is a class with ``name``, ``description``, and an async
``execute(args)`` method.  The registry discovers and manages all commands
and provides routing by command name.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .render import (
    console,
    get_theme,
    list_themes,
    render_error,
    render_status,
    set_theme,
)


if TYPE_CHECKING:
    from .agent import AgentSession


# ── Base command ────────────────────────────────────────────────────


class BaseCommand:
    """Abstract base for a slash command."""

    name: str = ""
    description: str = ""
    aliases: list[str] = []

    def __init__(self, session: AgentSession) -> None:
        self.session = session

    async def execute(self, args: str) -> None:
        """Run the command. *args* is everything after the command name."""
        raise NotImplementedError


# ── Command implementations ─────────────────────────────────────────


class HelpCommand(BaseCommand):
    name = "help"
    description = "Mostrar comandos disponibles"
    aliases = ["h", "?"]

    async def execute(self, _args: str) -> None:
        from .commands import CommandRegistry

        registry = CommandRegistry(self.session)
        registry.discover()

        console.print("\n[bold realm]᛭ Comandos de Yggdrasil[/]\n")
        for cmd in sorted(registry._commands.values(), key=lambda c: c.name):
            aliases = f" ({', '.join(f'/{a}' for a in cmd.aliases)})" if cmd.aliases else ""
            console.print(f"  [bold cyan]/{cmd.name}[/]{aliases}  [dim]— {cmd.description}[/]")
        console.print()


class ToolsCommand(BaseCommand):
    name = "tools"
    description = "Listar herramientas disponibles"

    async def execute(self, _args: str) -> None:
        tools = self.session.get_tool_descriptions()
        if not tools:
            console.print("[warning]No hay herramientas disponibles.[/]")
            return

        console.print("\n[bold realm]᛭ Herramientas[/]\n")
        for tool in tools:
            console.print(
                f"  [tool.name]{tool['name']}[/]  [dim]— {tool.get('description', '')}[/]",
            )
        console.print()


class ModelCommand(BaseCommand):
    name = "model"
    description = "Mostrar o cambiar el modelo activo"

    async def execute(self, args: str) -> None:
        if not args.strip():
            console.print(f"[info]Modelo actual: [model]{self.session.config.model}[/]")
            console.print(f"[info]Proveedor: [model]{self.session.config.provider}[/]")
            return

        new_model = args.strip()
        self.session.config.model = new_model
        # Re-initialise provider with the new model.
        from .providers import create_provider

        self.session.provider = create_provider(self.session.config)
        console.print(f"[success]✓ Modelo cambiado a: [model]{new_model}[/]")


class ProviderCommand(BaseCommand):
    name = "provider"
    description = "Mostrar o cambiar el proveedor LLM"

    async def execute(self, args: str) -> None:
        if not args.strip():
            console.print(f"[info]Proveedor actual: [model]{self.session.config.provider}[/]")
            providers = (
                ", ".join(self.session.config.providers.keys())
                if self.session.config.providers
                else "(ninguno configurado)"
            )
            console.print(f"[info]Perfiles: {providers}")
            return

        new_provider = args.strip()
        self.session.config.provider = new_provider
        # Update model from profile if available.
        profile = self.session.config.providers.get(new_provider.lower())
        if profile and profile.model:
            self.session.config.model = profile.model
            console.print(f"[success]✓ Modelo del perfil: [model]{profile.model}[/]")
        if profile and profile.api_key:
            self.session.config.api_key = profile.api_key
        if profile and profile.base_url:
            self.session.config.base_url = profile.base_url

        from .providers import create_provider

        self.session.provider = create_provider(self.session.config)
        console.print(f"[success]✓ Proveedor cambiado a: [model]{new_provider}[/]")


class MemoryCommand(BaseCommand):
    name = "memory"
    description = "Buscar en la memoria del agente"
    aliases = ["m"]

    async def execute(self, args: str) -> None:
        if not self.session.memory:
            render_error("Memoria no disponible (deshabilitada en configuración).")
            return

        query = args.strip()
        if not query:
            # Show recent memories.
            results = self.session.memory.recent(limit=5)
        else:
            results = self.session.memory.search(query, limit=5)

        if not results:
            console.print("[dim]Sin resultados en memoria.[/]")
            return

        console.print(f"\n[bold realm]᛭ Memoria: {query or 'recientes'}[/]\n")
        for entry in results:
            content = entry.get("content", "")
            ts = entry.get("timestamp", "")
            console.print(f"  [dim][{ts}][/] {content[:120]}{'…' if len(content) > 120 else ''}")
        console.print()


class ClearCommand(BaseCommand):
    name = "clear"
    description = "Limpiar historial de conversación"
    aliases = ["cls"]

    async def execute(self, _args: str) -> None:
        self.session.clear_history()
        console.print("[success]✓ Historial limpiado.[/]")


class StatusCommand(BaseCommand):
    name = "status"
    description = "Estado del ecosistema Yggdrasil"

    async def execute(self, _args: str) -> None:
        # Try importing from yggdrasil_cli for realm status.
        try:
            # Add root to sys.path if needed.
            root = str(Path(__file__).resolve().parents[3])  # /mnt/d/Proyectos/Yggdrasil
            if root not in sys.path:
                sys.path.insert(0, root)
            from yggdrasil_cli import (
                REALMS,
                SERVICES,
                YGGDRASIL_ROOT,
                get_service_status,
            )

            realm_data: dict[str, Any] = {}
            for realm in REALMS:
                rdf = YGGDRASIL_ROOT / realm
                if rdf.exists():
                    projects = [
                        d for d in rdf.iterdir() if d.is_dir() and not d.name.startswith(".")
                    ]
                    realm_data[realm] = {"exists": True, "projects": len(projects)}
                else:
                    realm_data[realm] = {"exists": False, "projects": 0}

            status_dict: dict[str, Any] = {
                "Modelo": self.session.config.model,
                "Proveedor": self.session.config.provider,
                "Memoria": self.session.memory is not None,
            }
            # Add service statuses.
            for key in SERVICES:
                svc = get_service_status(key)
                status_dict[f"{svc['emoji']} {svc['name']}"] = svc.get("running", False)

            # Add realm info.
            for realm, data in realm_data.items():
                status_dict[f"Realm: {realm}"] = (
                    data.get("projects", 0) if data["exists"] else "NO EXISTE"
                )

            render_status(status_dict)
        except ImportError:
            # Fallback: just show local status.
            render_status(
                {
                    "Modelo": self.session.config.model,
                    "Proveedor": self.session.config.provider,
                    "Memoria": self.session.memory is not None,
                    "Herramientas": len(self.session.get_tool_descriptions()),
                },
            )


class ConfigCommand(BaseCommand):
    name = "config"
    description = "Mostrar configuración actual"

    async def execute(self, _args: str) -> None:
        data = self.session.config.model_dump()
        # Mask API keys.
        if data.get("api_key"):
            key = data["api_key"]
            data["api_key"] = key[:8] + "…" + key[-4:] if len(key) > 12 else "***"

        console.print(
            Panel(
                Syntax(
                    json.dumps(data, indent=2, ensure_ascii=False, default=str),
                    "json",
                    theme="monokai",
                ),
                title="[bold realm]⚙ Configuración[/]",
                border_style="gold1",
                expand=False,
            ),
        )


class QuitCommand(BaseCommand):
    name = "quit"
    description = "Salir del agente"
    aliases = ["exit", "q"]

    async def execute(self, _args: str) -> None:
        console.print("[dim]Odin te guíe. Hasta la próxima.[/]")
        raise SystemExit(0)


class SaveCommand(BaseCommand):
    name = "save"
    description = "Guardar la conversación a un archivo"

    async def execute(self, _args: str) -> None:
        from .repl import _auto_save_conversation

        filepath = _auto_save_conversation(self.session)
        if filepath:
            console.print(f"[success]✓ Conversación guardada en: {filepath.resolve()}[/]")
        else:
            render_error("No hay mensajes para guardar.")


# ── New QoL commands (inspired by Hermes Agent) ───────────────────────


class RedoCommand(BaseCommand):
    """Re-send the last user message (like Hermes /retry)."""

    name = "redo"
    description = "Reenviar el último mensaje al modelo"
    aliases = ["retry"]

    async def execute(self, _args: str) -> None:
        last_msg = getattr(self.session, "_last_user_message", "") or ""
        if not last_msg:
            render_error("No hay mensaje anterior para reenviar.")
            return

        # Pop last user message from history if it matches.
        if (
            self.session.history
            and self.session.history[-1].get("role") == "user"
            and self.session.history[-1].get("content", "") == last_msg
        ):
            self.session.history.pop()

        # Pop any trailing assistant messages too.
        while self.session.history and self.session.history[-1].get("role") == "assistant":
            self.session.history.pop()

        console.print(
            f"[dim]⟳ Reenviando: [model]{last_msg[:80]}{'…' if len(last_msg) > 80 else ''}[/][/]",
        )
        # Import here to avoid circular imports.
        from .repl import _process_with_streaming, render_turn_start

        render_turn_start(999)  # We don't track turn number in commands — use placeholder
        await _process_with_streaming(self.session, last_msg)


class CopyCommand(BaseCommand):
    """Copy the last assistant response to clipboard (like Hermes /copy)."""

    name = "copy"
    description = "Copiar última respuesta al portapapeles"
    aliases = ["cp"]

    async def execute(self, args: str) -> None:
        from .repl import _copy_to_clipboard

        # Find assistant messages.
        assistant_msgs = [
            m for m in self.session.history if m.get("role") == "assistant" and m.get("content")
        ]
        if not assistant_msgs:
            render_error("No hay respuesta para copiar.")
            return

        # Support /copy <n> for Nth response (1-based).
        idx = -1  # Default: last
        if args.strip():
            try:
                n = int(args.strip())
                idx = n - 1  # Convert to 0-based
                if idx < 0 or idx >= len(assistant_msgs):
                    render_error(f"Índice fuera de rango. Hay {len(assistant_msgs)} respuestas.")
                    return
            except ValueError:
                render_error(
                    "Uso: /copy [número]  — donde número es el índice de respuesta (1-based)",
                )
                return

        text = assistant_msgs[idx].get("content", "")
        # Strip reasoning tags for clean copy.
        import re

        text = re.sub(
            r"<(?:reasoning|thinking|thought)>.*?</(?:reasoning|thinking|thought)>",
            "",
            text,
            flags=re.DOTALL,
        ).strip()

        if _copy_to_clipboard(text):
            preview = text[:60] + "…" if len(text) > 60 else text
            console.print(f"[success]✓ Copiado al portapapeles: [dim]{preview}[/]")
        else:
            render_error("No se pudo copiar al portapapeles. Intenta instalar xclip o wl-paste.")


class SystemCommand(BaseCommand):
    """Show or modify the system prompt (like Hermes /system)."""

    name = "system"
    description = "Mostrar o modificar el system prompt"

    async def execute(self, args: str) -> None:
        if not args.strip():
            # Show current system prompt.
            sp = self.session.system_prompt or "(sin system prompt)"
            console.print(
                Panel(
                    sp,
                    title="[bold realm]⚙ System Prompt[/]",
                    border_style="gold1",
                    expand=False,
                    padding=(0, 1),
                ),
            )
        else:
            # Set new system prompt.
            self.session.system_prompt = args.strip()
            console.print("[success]✓ System prompt actualizado.[/]")


class HistoryCommand(BaseCommand):
    """Show conversation history (like Hermes /history)."""

    name = "history"
    description = "Mostrar historial de conversación"
    aliases = ["hist"]

    async def execute(self, args: str) -> None:
        if not self.session.history:
            console.print("[dim]El historial está vacío.[/]")
            return

        # Parse optional limit.
        limit = len(self.session.history)
        if args.strip():
            with contextlib.suppress(ValueError):
                limit = min(int(args.strip()), len(self.session.history))

        # Show the last N messages.
        messages = self.session.history[-limit:]
        console.print(f"\n[bold realm]᛭ Historial ({len(messages)} mensajes)[/]\n")

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            role_styles = {
                "user": ("bold gold1", "᛭ Tú"),
                "assistant": ("bold cyan", "✦ Asistente"),
                "system": ("dim italic", "⚙ Sistema"),
                "tool": ("bold green", "⟡ Herramienta"),
            }
            style, label = role_styles.get(role, ("dim", role))

            # Truncate long messages.
            display = content[:200] + "…" if len(content) > 200 else content
            console.print(f"  [{style}]{i}. {label}[/]  [dim]{display}[/]")

        console.print()


class CompactCommand(BaseCommand):
    """Compress conversation history by summarizing older messages.

    Like Hermes Agent's /compact — asks the LLM to summarize the
    conversation so far, then replaces older messages with the summary
    while keeping recent exchanges intact. Frees up context tokens.
    """

    name = "compact"
    description = "Comprimir historial resumiendo mensajes antiguos"
    aliases = ["summarize"]

    async def execute(self, args: str) -> None:
        history = self.session.history
        if not history:
            render_error("El historial está vacío — no hay nada que compactar.")
            return

        # Parse optional keep_recent count.
        keep_recent = 2
        if args.strip():
            try:
                keep_recent = max(1, int(args.strip()))
            except ValueError:
                render_error(
                    "Uso: /compact [n]  — donde n es el número de "
                    "turnos recientes a conservar (default: 2)",
                )
                return

        before = len(history)
        console.print(f"[dim]Compactando {before} mensajes…[/]")

        try:
            # Generate summary from LLM with a thinking spinner.
            from .render import Timer, make_thinking_spinner

            timer = Timer()
            timer.__enter__()
            spinner_info = make_thinking_spinner()
            spinner_info["set_label"]("Resumiendo historial")
            spinner_info["status"].__enter__()
            try:
                summary = await self.session.generate_compact_summary()
            finally:
                spinner_info["status"].__exit__(None, None, None)
            timer.__exit__(None, None, None)

            if not summary:
                render_error("No se pudo generar el resumen. Intenta de nuevo.")
                return

            # Compact the history.
            self.session.compact_history(summary, keep_recent=keep_recent)
            after = len(self.session.history)

            # Show result.
            console.print()
            console.print(
                Panel(
                    summary[:500] + ("…" if len(summary) > 500 else ""),
                    title="[bold realm]᛭ Historial Compactado[/]",
                    border_style="frost",
                    expand=False,
                    padding=(0, 1),
                ),
            )
            console.print(
                f"[success]✓ {before} mensajes → {after} "
                f"(1 resumen + {keep_recent} turnos recientes)[/]",
            )
            console.print(f"[dim]{timer.elapsed:.1f}s para generar resumen[/]")

        except Exception as exc:
            render_error(f"Error al compactar: {exc}")


class ResumeCommand(BaseCommand):
    """Resume a previously saved conversation.

    Lists saved conversations from ``~/.yggdrasil/conversations/`` and
    lets the user pick one to restore into the current session history.
    Supports selecting by index (``/resume 3``) or searching by name.
    Without arguments, shows the list of recent conversations.
    """

    name = "resume"
    description = "Reanudar una conversación guardada"
    aliases = ["load"]

    async def execute(self, args: str) -> None:
        from .repl import _list_saved_conversations, _load_conversation

        conversations = _list_saved_conversations()

        if not conversations:
            render_error("No hay conversaciones guardadas en ~/.yggdrasil/conversations/")
            return

        # ── No args: show list ───────────────────────────────────
        if not args.strip():
            from rich.table import Table

            table = Table(
                title="[bold gold1]᛭ Conversaciones Guardadas[/]",
                show_lines=False,
                border_style="cyan",
                header_style="bold dim",
            )
            table.add_column("#", style="bold gold1", width=3)
            table.add_column("Fecha", style="bright_white")
            table.add_column("Modelo", style="cyan")
            table.add_column("Mensajes", style="green", justify="right")
            table.add_column("Vista previa", style="dim", max_width=50)

            for i, conv in enumerate(conversations[:15], start=1):
                ts = conv["timestamp"]
                # Format timestamp nicely.
                try:
                    date_str = f"{ts[:4]}-{ts[6:8]}-{ts[4:6]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"
                except (ValueError, IndexError):
                    date_str = ts
                table.add_row(
                    str(i),
                    date_str,
                    conv["model"],
                    str(conv["message_count"]),
                    conv["preview"] or "(sin mensajes de usuario)",
                )

            console.print(table)
            console.print("[dim]Usa /resume <número> para reanudar una conversación[/]")
            return

        # ── Select by index or search ────────────────────────────
        selection = args.strip()

        # Try numeric index.
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(conversations):
                conv = conversations[idx]
            else:
                render_error(
                    f"Índice fuera de rango: {selection} (hay {len(conversations)} conversaciones)",
                )
                return
        except ValueError:
            # Search by name/preview substring.
            matches = [
                c
                for c in conversations
                if selection.lower() in c["name"].lower()
                or selection.lower() in c["preview"].lower()
            ]
            if not matches:
                render_error(f"No se encontró ninguna conversación que coincida con '{selection}'")
                return
            if len(matches) > 1:
                render_error(
                    f"Múltiples coincidencias para '{selection}'. "
                    f"Usa /resume <número> para seleccionar una específica.",
                )
                return
            conv = matches[0]

        # ── Load and restore ─────────────────────────────────────
        filepath = conv["file"]
        data = _load_conversation(filepath)
        if data is None:
            return

        messages = data.get("messages", [])
        if not messages:
            render_error("La conversación seleccionada está vacía.")
            return

        # Preserve current system prompt, restore history.
        old_count = len(self.session.history)
        self.session.history = messages

        # Merge usage if available.
        loaded_usage = data.get("usage", {})
        if loaded_usage:
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if key in loaded_usage:
                    self.session._total_usage[key] += loaded_usage.get(key, 0)

        console.print()
        console.print(
            Panel(
                f"[bright_white]{conv['message_count']} mensajes[/] · "
                f"[cyan]{conv.get('model', '?')}[/] · "
                f"[dim]{conv.get('timestamp', '')}[/]\n\n"
                f"[dim]{conv.get('preview', '(sin preview)')}[/]",
                title="[bold gold1]᛭ Conversación Reanudada[/]",
                border_style="green",
                expand=False,
                padding=(0, 1),
            ),
        )
        console.print(
            f"[success]✓ Restaurados {conv['message_count']} mensajes (antes: {old_count})[/]",
        )


# ── Registry ────────────────────────────────────────────────────────

# We need a late import for render in ConfigCommand's Panel.

from rich.panel import Panel
from rich.syntax import Syntax


class ThemeCommand(BaseCommand):
    """Switch or preview CLI themes.

    Without arguments, lists available themes with a preview of the
    current selection highlighted.  With a theme name, switches
    immediately — the Rich Console and prompt_toolkit style update
    on the next prompt cycle.
    """

    name = "theme"
    description = "Cambiar o listar temas visuales"
    aliases = ["themes"]

    async def execute(self, args: str) -> None:
        from rich.table import Table

        theme_name = args.strip().lower()

        # ── List themes ───────────────────────────────────
        if not theme_name:
            current = get_theme()
            table = Table(
                title="[bold]᛭ Temas Disponibles[/]",
                show_lines=False,
                border_style=current.border_style,
                header_style=f"bold {current.border_style}",
            )
            table.add_column("Nombre", style="bold", min_width=10)
            table.add_column("Descripción", min_width=30)
            table.add_column("Prefijo", min_width=4)

            for t in list_themes():
                marker = " ◄" if t.name == current.name else ""
                table.add_row(
                    f"{t.name}{marker}",
                    t.description,
                    t.prompt_prefix,
                )

            console.print()
            console.print(table)
            console.print(
                f"\n[dim]Tema actual: [bold]{current.label}[/]. "
                f"Usa /theme <nombre> para cambiar.[/]",
            )
            return

        # ── Switch theme ──────────────────────────────────
        available_names = [t.name for t in list_themes()]
        if theme_name not in available_names:
            available = ", ".join(available_names)
            render_error(f"Tema desconocido: {theme_name}. Disponibles: {available}")
            return

        new_theme = set_theme(theme_name)

        # Persist to config.
        try:
            import yaml

            from .config import CONFIG_FILE

            raw = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
            raw["theme"] = theme_name
            CONFIG_FILE.write_text(
                yaml.dump(raw, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
        except Exception:
            pass  # Best-effort — don't crash on config save.

        console.print()
        console.print(
            Panel(
                f"{_THEME_DISPLAYS.get(theme_name, '')}\n\n"
                f"Prefijo: {new_theme.prompt_prefix}\n"
                f"Bordes: {new_theme.border_style}",
                title=f"[bold {new_theme.border_style}]{new_theme.label}[/]",
                border_style=new_theme.border_style,
                expand=False,
                padding=(0, 1),
            ),
        )
        console.print(f"[success]✓ Tema cambiado a {new_theme.label}[/]")
        console.print("[dim]Los cambios se reflejan en el siguiente prompt.[/]")


# Theme preview snippets for the switch confirmation.
_THEME_DISPLAYS: dict[str, str] = {
    "norse": ("᛭ Runas doradas sobre fondo oscuro\n   Árboles ancestrales y mitología nórdica"),
    "cyberpunk": (
        "⟐ Neon cian y magenta sobre fondo negro\n   Señales digitales desde los nodos periféricos"
    ),
    "minimal": ("› Líneas limpias y silencio\n   Máxima legibilidad, cero decoración"),
}


class FileCommand(BaseCommand):
    """Attach a local file to the conversation context.

    Reads the file contents and injects it as a user message so the LLM
    can see it.  Supports text files, code, JSON, YAML, etc.

    Usage::

        /file path/to/file.py          — attach file
        /file path/to/file.py describe — attach with a prompt
    """

    name = "file"
    description = "Adjuntar archivo al contexto del chat"
    aliases = ["f"]

    # Max file size to read (5 MB).
    MAX_SIZE = 5 * 1024 * 1024

    async def execute(self, args: str) -> None:
        from rich.panel import Panel

        parts = args.strip().split(maxsplit=1)
        if not parts:
            render_error("Uso: /file <ruta> [prompt]  — adjunta un archivo al contexto")
            return

        file_path = Path(parts[0]).expanduser()
        user_prompt = parts[1].strip() if len(parts) > 1 else ""

        # Resolve path: relative to CWD, support ~
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        # Check existence.
        if not file_path.exists():
            render_error(f"Archivo no encontrado: {file_path}")
            return

        # Check size.
        size = file_path.stat().st_size
        if size > self.MAX_SIZE:
            render_error(
                f"Archivo demasiado grande ({size / 1024 / 1024:.1f} MB). "
                f"Máximo: {self.MAX_SIZE // 1024 // 1024} MB",
            )
            return

        # Read content.
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            render_error(f"Error leyendo archivo: {exc}")
            return

        # Detect language for syntax highlighting.
        suffix_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".rb": "ruby",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".toml": "toml",
            ".ini": "ini",
            ".cfg": "ini",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".xml": "xml",
        }
        lang = suffix_map.get(file_path.suffix.lower(), "")

        # Show preview.
        line_count = content.count("\n") + 1
        preview_lines = content.split("\n")[:10]
        preview = "\n".join(preview_lines)
        if line_count > 10:
            preview += f"\n... ({line_count - 10} más líneas)"

        console.print(
            Panel(
                preview,
                title=f"[bold gold1]📄 {file_path.name}[/] ({line_count} líneas, {size:,} bytes)",
                border_style="frost",
                expand=False,
            ),
        )

        # Build context message.
        file_message = f"📄 Archivo: `{file_path}`\n\n```{lang}\n{content}\n```"
        if user_prompt:
            file_message = f"{user_prompt}\n\n{file_message}"

        # Add to history and show confirmation.
        self.session.history.append({"role": "user", "content": file_message})
        console.print(f"[success]✓ Archivo adjuntado al contexto ({line_count} líneas)[/]")


class ExportCommand(BaseCommand):
    """Export the current conversation to a file.

    Supports Markdown (human-readable) and JSON (raw data) formats.

    Usage::

        /export              — export to Markdown (default)
        /export md           — same as above
        /export json         — export as JSON
        /export md filename   — custom filename (saved to ~/.yggdrasil/exports/)
    """

    name = "export"
    description = "Exportar conversación a Markdown o JSON"
    aliases = ["exp"]

    def _format_markdown(self, messages: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
        """Format conversation as Markdown."""
        lines = [
            "# Conversación Yggdrasil",
            "",
            f"- **Fecha**: {metadata.get('timestamp', 'N/A')}",
            f"- **Modelo**: {metadata.get('model', 'N/A')}",
            f"- **Provider**: {metadata.get('provider', 'N/A')}",
        ]
        usage = metadata.get("usage", {})
        if usage and any(v > 0 for v in usage.values()):
            lines.append(
                f"- **Tokens**: {usage.get('prompt_tokens', 0)}↑ "
                f"{usage.get('completion_tokens', 0)}↓ "
                f"{usage.get('total_tokens', 0)}Σ",
            )
        lines.append("")
        lines.append("---")
        lines.append("")

        role_icons = {"user": "🧑", "assistant": "🤖", "system": "⚙️"}
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            icon = role_icons.get(role, "💬")

            if role == "system":
                lines.append(f"> ⚙️ **System**: {content}")
                lines.append("")
                continue

            lines.append(f"### {icon} {role.capitalize()}")
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _format_json(self, messages: list[dict[str, Any]], metadata: dict[str, Any]) -> str:
        """Format conversation as JSON."""
        data = {
            **metadata,
            "messages": messages,
        }
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    async def execute(self, args: str) -> None:
        from rich.panel import Panel

        parts = args.strip().split(maxsplit=1)
        fmt = parts[0].lower() if parts else "md"
        custom_name = parts[1].strip() if len(parts) > 1 else ""

        if fmt not in ("md", "markdown", "json"):
            render_error(f"Formato desconocido: '{fmt}'. Usa 'md' o 'json'.")
            return

        fmt_ext = "json" if fmt == "json" else "md"

        # Prepare export data.
        messages = self.session.history
        if not messages:
            render_error("No hay mensajes para exportar.")
            return

        from datetime import UTC, datetime

        metadata = {
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "model": self.session.config.model,
            "provider": self.session.config.provider,
            "usage": self.session.total_usage,
        }

        # Generate content.
        if fmt_ext == "json":
            content = self._format_json(messages, metadata)
        else:
            content = self._format_markdown(messages, metadata)

        # Determine output path.
        exports_dir = Path("~/.yggdrasil/exports").expanduser()
        exports_dir.mkdir(parents=True, exist_ok=True)

        if custom_name:
            if not custom_name.endswith(f".{fmt_ext}"):
                custom_name += f".{fmt_ext}"
            filepath = exports_dir / custom_name
        else:
            timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
            filepath = exports_dir / f"export_{timestamp}.{fmt_ext}"

        # Write file.
        try:
            filepath.write_text(content, encoding="utf-8")
        except Exception as exc:
            render_error(f"Error escribiendo archivo: {exc}")
            return

        # Show confirmation.
        msg_count = len(messages)
        user_msgs = sum(1 for m in messages if m.get("role") == "user")
        asst_msgs = sum(1 for m in messages if m.get("role") == "assistant")

        console.print(
            Panel(
                f"[success]✓ Exportado a {filepath}[/]\n\n"
                f"Messages: {msg_count} ({user_msgs} user, {asst_msgs} assistant)\n"
                f"Format: {fmt_ext.upper()}",
                title="[bold gold1]📦 Exportación Completa[/]",
                border_style="frost",
                expand=False,
            ),
        )


class CommandRegistry:
    """Discovers, registers, and routes slash commands."""

    def __init__(self, session: AgentSession) -> None:
        self.session = session
        self._commands: dict[str, BaseCommand] = {}
        self._aliases: dict[str, str] = {}

    def discover(self) -> None:
        """Register all built-in command classes."""
        builtin: list[type[BaseCommand]] = [
            HelpCommand,
            ToolsCommand,
            ModelCommand,
            ProviderCommand,
            MemoryCommand,
            ClearCommand,
            StatusCommand,
            ConfigCommand,
            QuitCommand,
            SaveCommand,
            RedoCommand,
            CopyCommand,
            SystemCommand,
            HistoryCommand,
            CompactCommand,
            ResumeCommand,
            ThemeCommand,
            FileCommand,
            ExportCommand,
        ]
        for cmd_cls in builtin:
            cmd = cmd_cls(self.session)
            self._commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self._aliases[alias] = cmd.name

    def get(self, name: str) -> BaseCommand | None:
        """Look up a command by name or alias."""
        real_name = self._aliases.get(name, name)
        return self._commands.get(real_name)

    def list_commands(self) -> list[BaseCommand]:
        """Return all registered commands."""
        return list(self._commands.values())

    async def dispatch(self, raw_input: str) -> bool:
        """Try to dispatch a slash command.

        Returns True if the input was a command (and was handled),
        False otherwise.
        """
        text = raw_input.strip()
        if not text.startswith("/"):
            return False

        parts = text[1:].split(maxsplit=1)
        cmd_name = parts[0].lower()
        cmd_args = parts[1] if len(parts) > 1 else ""

        cmd = self.get(cmd_name)
        if cmd is None:
            render_error(
                f"Comando desconocido: /{cmd_name}  — escribe /help para ver los disponibles",
            )
            return True

        await cmd.execute(cmd_args)
        return True
