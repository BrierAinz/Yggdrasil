#!/usr/bin/env python3
"""
᛭ Midgard Habits — Tracker de Hábitos Personal ᛭
CLI con estética dark fantasy nórdica para el reino de Midgard.
"""

import argparse
import sys
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from habits_db import HabitsDB, get_db


# ─── Consola Rich ─────────────────────────────────────────────────────────────

console = Console()

# ─── Constants ─────────────────────────────────────────────────────────────────

RUNE_HEADER = "᛭"
COMPLETED = "bold green"
PENDING = "bold yellow"
FAILED = "bold red"
SUBTLE = "dim"
RUNIC_FIRE = "ᚠ"  # Fehu — fuego rúnico para rachas
RUNIC_ICE = "ᛁ"   # Isa — hielo para hábitos pendientes
RUNIC_DEATH = "ᛦ"  # Yr — para hábitos fallidos/archivados

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _runic_title(text: str) -> str:
    return f"{RUNE_HEADER} {text} {RUNE_HEADER}"


def _runic_fire_bar(count: int) -> str:
    """Barra de fuego rúnico para rachas."""
    if count == 0:
        return f"[{FAILED}]sin llama[{FAILED}]"
    return f"[{COMPLETED}]{RUNIC_FIRE * count}[/{COMPLETED}] ({count})"


def _progress_bar(habit_id: int, days: int = 7) -> str:
    """Barra de progreso rúnica para los últimos N días."""
    db = get_db()
    progress = db.get_habit_progress(habit_id, days)
    bar_parts = []
    for day in progress:
        if day["checked"]:
            bar_parts.append(f"[{COMPLETED}]ᚹ[/{COMPLETED}]")
        else:
            bar_parts.append(f"[{PENDING}]᛬[/{PENDING}]")
    
    # Fecha del primer y último día
    first_date = progress[0]["date"][5:] if progress else ""  # MM-DD
    last_date = progress[-1]["date"][5:] if progress else ""
    
    return " ".join(bar_parts)


def _resolve_habit(name_or_id: str | int) -> dict:
    """Resuelve un hábito por nombre o ID, lanza error si no existe."""
    db = get_db()
    habit = db.get_habit(name_or_id)
    if not habit:
        console.print(f"[{FAILED}]Hábito '{name_or_id}' no encontrado.[/{FAILED}]")
        sys.exit(1)
    return habit


def _validate_date(date_str: str) -> str:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        console.print(f"[{FAILED}]Fecha inválida: {date_str}. Use YYYY-MM-DD.[/{FAILED}]")
        sys.exit(1)


# ─── Comandos ─────────────────────────────────────────────────────────────────

def cmd_add(args: argparse.Namespace) -> None:
    """Crea un nuevo hábito."""
    db = get_db()
    name = args.nombre
    freq = args.freq or "diario"
    icon = args.icon or "]"
    
    try:
        habit_id = db.add_habit(name=name, frequency=freq, icon=icon)
    except ValueError as e:
        console.print(f"[{FAILED}]{e}[/{FAILED}]")
        sys.exit(1)
    
    # Mostrar frecuencia legible
    freq_display = freq if freq in ("diario", "semanal") else freq
    
    content = (
        f"[{COMPLETED}]Hábito forjado en las runas[/{COMPLETED}]\n\n"
        f"  ᛭ [bold]Nombre:[/bold]      {icon} {name}\n"
        f"  ᛭ [bold]Frecuencia:[/bold]  {freq_display}\n"
        f"  ᛭ [bold]Icono:[/bold]       {icon}\n\n"
        f"  [{SUBTLE}]ID #{habit_id}[/{SUBTLE}]"
    )
    console.print(Panel(content, title=_runic_title("Nuevo Hábito"), border_style="green"))


def cmd_check(args: argparse.Namespace) -> None:
    """Marca un hábito como completado."""
    db = get_db()
    habit = _resolve_habit(args.nombre_o_id)
    date = _validate_date(args.fecha) if args.fecha else None
    
    inserted = db.check_habit(habit["id"], date)
    
    fecha_display = date or datetime.now().strftime("%Y-%m-%d")
    icon = habit["icon"]
    
    if inserted:
        streak_info = db.get_streak(habit["id"])
        content = (
            f"[{COMPLETED}]{icon} {habit['name']} — Marcado como completado[/{COMPLETED}]\n\n"
            f"  ᛭ [bold]Fecha:[/bold]        {fecha_display}\n"
            f"  ᛭ [bold]Racha actual:[/bold] {_runic_fire_bar(streak_info['current_streak'])}\n"
            f"  ᛭ [bold]Mejor racha:[/bold]   {_runic_fire_bar(streak_info['best_streak'])}\n"
        )
        console.print(Panel(content, title=_runic_title("Hábito Completado"), border_style="green"))
    else:
        console.print(
            f"[{PENDING}]{icon} {habit['name']} ya estaba completado para {fecha_display}.[/{PENDING}]"
        )


def cmd_uncheck(args: argparse.Namespace) -> None:
    """Desmarca un hábito."""
    db = get_db()
    habit = _resolve_habit(args.nombre_o_id)
    date = _validate_date(args.fecha) if args.fecha else None
    
    removed = db.uncheck_habit(habit["id"], date)
    
    fecha_display = date or datetime.now().strftime("%Y-%m-%d")
    icon = habit["icon"]
    
    if removed:
        content = (
            f"[{PENDING}]{icon} {habit['name']} — Desmarcado[/{PENDING}]\n"
            f"  ᛭ [bold]Fecha:[/bold] {fecha_display}\n"
        )
        console.print(Panel(content, title=_runic_title("Hábito Desmarcado"), border_style="yellow"))
    else:
        console.print(
            f"[{FAILED}]No se encontró registro de {icon} {habit['name']} para {fecha_display}.[/{FAILED}]"
        )


def cmd_list(args: argparse.Namespace) -> None:
    """Lista hábitos con progreso."""
    db = get_db()
    active_only = not args.all
    habits = db.list_habits(active_only=active_only)
    
    if not habits:
        console.print(f"[{SUBTLE}]No hay hábitos para mostrar. Crea uno con 'add'.[/{SUBTLE}]")
        return
    
    title_suffix = "Activos" if active_only else "Todos"
    table = Table(
        title=_runic_title(f"Hábitos — {title_suffix}"),
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        title_style="bold cyan",
    )
    table.add_column("ID", justify="center", style="dim", width=4)
    table.add_column("Icono", justify="center", width=6)
    table.add_column("Nombre", style="bold")
    table.add_column("Frecuencia", justify="center")
    table.add_column("Estado", justify="center")
    table.add_column("Progreso (7 días)", min_width=15)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    for h in habits:
        icon = h["icon"]
        name = h["name"]
        freq = h["frequency"]
        h_id = str(h["id"])
        active = h["active"]
        
        # Verificar si está completado hoy
        is_checked_today = bool(db.conn.execute(
            "SELECT 1 FROM habit_checks WHERE habit_id = ? AND date = ?",
            (h["id"], today),
        ).fetchone())
        
        # Barra de progreso
        progress = db.get_habit_progress(h["id"], 7)
        bar_parts = []
        for day in progress:
            d_short = day["date"][8:]  # DD
            if day["checked"]:
                bar_parts.append(f"[{COMPLETED}]ᚹ[/{COMPLETED}]")
            else:
                bar_parts.append(f"[{PENDING}]᛬[/{PENDING}]")
        progress_str = " ".join(bar_parts)
        
        if active:
            status = f"[{COMPLETED}]ᚠ[/{COMPLETED}]" if is_checked_today else f"[{PENDING}]ᛁ[/{PENDING}]"
        else:
            status = f"[{FAILED}]ᛦ[/{FAILED}]"
        
        # Color del nombre según estado
        if not active:
            name_str = f"[{FAILED}]{icon} {name}[/{FAILED}]"
        elif is_checked_today:
            name_str = f"[{COMPLETED}]{icon} {name}[/{COMPLETED}]"
        else:
            name_str = f"[{PENDING}]{icon} {name}[/{PENDING}]"
        
        table.add_row(h_id, icon, name_str, freq, status, progress_str)
    
    console.print(table)


def cmd_streak(args: argparse.Namespace) -> None:
    """Muestra racha actual y mejor racha."""
    db = get_db()
    habit = _resolve_habit(args.nombre_o_id)
    icon = habit["icon"]
    
    streak_info = db.get_streak(habit["id"])
    
    current = streak_info["current_streak"]
    best = streak_info["best_streak"]
    last = streak_info["last_check"]
    
    # Determinar estado de la racha y colores
    if current == 0:
        status_color = FAILED
        status_icon = "ᛦ"
        status_text = "Racha rota — las llamas se han extinguido"
    elif current >= 7:
        status_color = COMPLETED
        status_icon = "🔥"
        status_text = "¡Racha legendaria! Las runas arden con fuerza"
    elif current >= 3:
        status_color = COMPLETED
        status_icon = "ᚠ"
        status_text = "Las llamas crecen — la disciplina prevalece"
    else:
        status_color = PENDING
        status_icon = "ᛁ"
        status_text = "La llama es joven — aliméntala con constancia"
    
    # Calcular días hasta la mejor racha
    days_to_beat = best - current if best > current else 0
    
    content = (
        f"[bold][{status_color}]{status_icon}[/{status_color}] {icon} {habit['name']}[/bold]\n\n"
        f"  ᛭ [bold]Racha actual:[/bold]  {_runic_fire_bar(current)}\n"
        f"  ᛭ [bold]Mejor racha:[/bold]    {_runic_fire_bar(best)}\n"
        f"  ᛭ [bold]Último check:[/bold]   {last or '—'}\n\n"
        f"  [{status_color}]{status_icon}[/{status_color}] {status_text}\n"
    )
    
    if days_to_beat > 0:
        content += f"\n  [{SUBTLE}]Faltan {days_to_beat} días para superar tu mejor racha.[/{SUBTLE}]"
    elif current > 0 and current == best:
        content += f"\n  [{COMPLETED}]¡Estás en tu mejor racha![/{COMPLETED}]"
    
    console.print(Panel(content, title=_runic_title("Racha"), border_style="cyan"))


def cmd_stats(args: argparse.Namespace) -> None:
    """Estadísticas generales."""
    db = get_db()
    period = "semana" if args.semana else "mes"
    stats = db.get_stats(period=period)
    
    period_label = "última semana" if period == "semana" else "último mes"
    
    # Completion rate color
    rate = stats["completion_rate"]
    if rate >= 80:
        rate_color = COMPLETED
        rate_icon = "ᚹ"
    elif rate >= 50:
        rate_color = PENDING
        rate_icon = "ᛁ"
    else:
        rate_color = FAILED
        rate_icon = "ᛦ"
    
    # Completed today
    active_habits = stats["active_habits"]
    completed_today = stats["completed_today"]
    
    if active_habits > 0 and completed_today == active_habits:
        today_status = f"[{COMPLETED}]¡Todos los hábitos completados hoy! ᚠ[/{COMPLETED}]"
    elif active_habits > 0:
        today_status = f"[{PENDING}]{completed_today}/{active_habits} completados hoy[/{PENDING}]"
    else:
        today_status = f"[{SUBTLE}]Sin hábitos activos[/{SUBTLE}]"
    
    # Best streak habit
    best_h = stats["best_streak_habit"]
    if best_h:
        best_streak_text = f"{best_h['icon']} {best_h['name']} — {_runic_fire_bar(best_h['best_streak'])}"
    else:
        best_streak_text = f"[{SUBTLE}]Sin datos de racha[/{SUBTLE}]"
    
    content = (
        f"  ᛭ [bold]Hábitos totales:[/bold]    {stats['total_habits']}\n"
        f"  ᛭ [bold]Hábitos activos:[/bold]    {active_habits}\n"
        f"  ᛭ [bold]Hoy:[/bold]                {today_status}\n\n"
        f"  ᛭ [bold]Tasa de cumpl.[/bold]      [{rate_color}]{rate_icon} {rate}%[/{rate_color}] ({period_label})\n"
        f"  ᛭ [bold]Checks en {period_label}:[/bold]    {stats['period_checks']}\n\n"
        f"  ᛭ [bold]Mejor racha:[/bold]        {best_streak_text}\n"
    )
    
    console.print(Panel(content, title=_runic_title(f"Estadísticas — {period_label.title()}"), border_style="cyan"))


def cmd_archive(args: argparse.Namespace) -> None:
    """Archiva un hábito."""
    db = get_db()
    habit = _resolve_habit(args.nombre_o_id)
    icon = habit["icon"]
    
    success = db.archive_habit(habit["id"])
    if success:
        content = (
            f"[{PENDING}]{icon} {habit['name']} — Archivado[/{PENDING}]\n\n"
            f"  [{SUBTLE}]El hábito ha sido enviado al reino de Helheim.[/{SUBTLE}]\n"
            f"  [{SUBTLE}]Las runas recuerdan tu esfuerzo.[/{SUBTLE}]"
        )
        console.print(Panel(content, title=_runic_title("Hábito Archivado"), border_style="yellow"))
    else:
        console.print(f"[{FAILED}]No se pudo archivar '{habit['name']}'.[/{FAILED}]")


# ─── CLI Parser ───────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="midgard-habits",
        description="᛭ Midgard Habits — Tracker de Hábitos Personal ᛭",
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # add <nombre>
    p_add = subparsers.add_parser("add", help="Crear un nuevo hábito")
    p_add.add_argument("nombre", help="Nombre del hábito")
    p_add.add_argument(
        "--freq",
        default="diario",
        help="Frecuencia: diario, semanal, o N/semana (default: diario)",
    )
    p_add.add_argument(
        "--icon",
        default="]",
        help="Icono/símbolo del hábito (default: ])",
    )

    # check <nombre|id>
    p_check = subparsers.add_parser("check", help="Marcar hábito como completado")
    p_check.add_argument("nombre_o_id", help="Nombre o ID del hábito")
    p_check.add_argument("--fecha", help="Fecha YYYY-MM-DD (default: hoy)")

    # uncheck <nombre|id>
    p_uncheck = subparsers.add_parser("uncheck", help="Desmarcar hábito")
    p_uncheck.add_argument("nombre_o_id", help="Nombre o ID del hábito")
    p_uncheck.add_argument("--fecha", help="Fecha YYYY-MM-DD (default: hoy)")

    # list
    p_list = subparsers.add_parser("list", help="Listar hábitos con progreso")
    p_list.add_argument("--active", action="store_true", default=True, help="Solo activos (default)")
    p_list.add_argument("--all", action="store_true", help="Mostrar todos incluyendo archivados")

    # streak <nombre|id>
    p_streak = subparsers.add_parser("streak", help="Mostrar racha actual y mejor racha")
    p_streak.add_argument("nombre_o_id", help="Nombre o ID del hábito")

    # stats
    p_stats = subparsers.add_parser("stats", help="Estadísticas generales")
    p_stats.add_argument("--semana", action="store_true", help="Estadísticas semanales (default)")
    p_stats.add_argument("--mes", action="store_true", help="Estadísticas mensuales")

    # archive <nombre|id>
    p_archive = subparsers.add_parser("archive", help="Archivar hábito")
    p_archive.add_argument("nombre_o_id", help="Nombre o ID del hábito")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        console.print(f"\n[{SUBTLE}]Las runas iluminan el camino de tus hábitos.[/{SUBTLE}]")
        return

    commands = {
        "add": cmd_add,
        "check": cmd_check,
        "uncheck": cmd_uncheck,
        "list": cmd_list,
        "streak": cmd_streak,
        "stats": cmd_stats,
        "archive": cmd_archive,
    }

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()