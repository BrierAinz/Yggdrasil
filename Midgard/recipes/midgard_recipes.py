#!/usr/bin/env python3
"""
🪵 Yggdrasil — Midgard Recipe Manager CLI
A dark-fantasy recipe manager forged in the fires of Muspelheim.
"""

import argparse
import json
import sys
import os

# Add parent dir for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recipes_db import RecipeDB

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ── Theme Constants ──────────────────────────────────────────
FIRE = "🔥"
RUNE_EASY = "ᚱ"     # Raido — journey
RUNE_MED = "ᛏᛏ"     # Tiwaz x2 — warrior
RUNE_HARD = "ᛏᛏᛏ"   # Tiwaz x3 — battle
SCROLL_TOP = "╔══════════════════════════════════════════════════════════╗"
SCROLL_BOT = "╚══════════════════════════════════════════════════════════╝"
SCROLL_SEP = "╠══════════════════════════════════════════════════════════╣"

DIFFICULTY_RUNES = {
    "facil": RUNE_EASY,
    "medio": RUNE_MED,
    "dificil": RUNE_HARD,
}

SLOT_ICONS = {
    "desayuno": "☀️",
    "comida": "🗡️",
    "cena": "🌙",
}

db = RecipeDB()

if RICH_AVAILABLE:
    console = Console()


# ── Helpers ─────────────────────────────────────────────────
def difficulty_display(diff: str) -> str:
    rune = DIFFICULTY_RUNES.get(diff, "?")
    if RICH_AVAILABLE:
        colors = {"facil": "green", "medio": "yellow", "dificil": "red"}
        return f"[{colors.get(diff, 'white')}]{rune} {diff}[/{colors.get(diff, 'white')}]"
    return f"{rune} {diff}"


def fire_display(minutes: int) -> str:
    fires = min(minutes // 15, 5) + (1 if minutes > 0 else 0)
    fires = min(fires, 5)
    icon = FIRE * fires if fires > 0 else "—"
    if RICH_AVAILABLE:
        return f"[bold red]{icon}[/bold red] {minutes} min"
    return f"{icon} {minutes} min"


def parchment_line(text: str, width: int = 58) -> str:
    pad = max(width - len(text) - 2, 0)
    return f"║ {text}{' ' * pad} ║"


def format_parchment(title: str, sections: list) -> str:
    """Build a scroll-style display for a recipe."""
    lines = [SCROLL_TOP]
    lines.append(parchment_line(f"📜  {title}"))
    lines.append(SCROLL_SEP)
    for label, value in sections:
        lines.append(parchment_line(f"{label}: {value}"))
    lines.append(SCROLL_BOT)
    return "\n".join(lines)


# ── Subcommand Handlers ─────────────────────────────────────
def cmd_add(args):
    """Add a new recipe to the grimoire."""
    name = args.nombre

    # Collect ingredients
    ingredients = []
    if args.ingredient:
        for ing_str in args.ingredient:
            # Parse "2 tazas harina" → amount=2, unit=tazas, name=harina
            parts = ing_str.split()
            if len(parts) >= 3:
                ing = {"amount": parts[0], "unit": parts[1], "name": " ".join(parts[2:])}
            elif len(parts) == 2:
                ing = {"amount": parts[0], "unit": "", "name": parts[1]}
            else:
                ing = {"amount": "", "unit": "", "name": parts[0]}
            ingredients.append(ing)
    else:
        print("🗡️  Ingrese ingredientes (formato: '2 tazas harina'). Línea vacía para terminar:")
        while True:
            try:
                line = input("   > ").strip()
            except EOFError:
                break
            if not line:
                break
            parts = line.split()
            if len(parts) >= 3:
                ing = {"amount": parts[0], "unit": parts[1], "name": " ".join(parts[2:])}
            elif len(parts) == 2:
                ing = {"amount": parts[0], "unit": "", "name": parts[1]}
            else:
                ing = {"amount": "", "unit": "", "name": parts[0]}
            ingredients.append(ing)

    steps = []
    if args.step:
        steps = list(args.step)
    else:
        print("🗡️  Ingrese instrucciones paso a paso. Línea vacía para terminar:")
        i = 1
        while True:
            try:
                line = input(f"   Paso {i}: ").strip()
            except EOFError:
                break
            if not line:
                break
            steps.append(line)
            i += 1

    tags = args.tags.split(",") if args.tags else []

    recipe_id = db.add_recipe(
        name=name,
        cook_time=args.time or 0,
        difficulty=args.difficulty or "medio",
        servings=args.servings or 2,
        tags=tags,
        ingredients=ingredients,
        instructions=steps,
    )

    if RICH_AVAILABLE:
        console.print(Panel(f"[bold green]⚔️ Receta '{name}' inscrita en el grimorio (ID: {recipe_id})[/bold green]", title="🪵 Midgard Recipes"))
    else:
        print(f"⚔️ Receta '{name}' inscrita en el grimorio (ID: {recipe_id})")


def cmd_list(args):
    """List recipes from the grimoire."""
    recipes = db.list_recipes(tag=args.tag, difficulty=args.difficulty, time_max=args.time_max)

    if not recipes:
        if RICH_AVAILABLE:
            console.print("[dim]El grimorio está vacío. No se encontraron recetas.[/dim]")
        else:
            print("El grimorio está vacío. No se encontraron recetas.")
        return

    if RICH_AVAILABLE:
        table = Table(title="📜 Grimorio de Recetas", show_lines=True)
        table.add_column("ID", style="cyan", width=4)
        table.add_column("Nombre", style="bold white", min_width=20)
        table.add_column("Tiempo", style="red")
        table.add_column("Dificultad", style="yellow")
        table.add_column("Porciones", style="green")
        table.add_column("Tags", style="dim")

        for r in recipes:
            diff = DIFFICULTY_RUNES.get(r["difficulty"], "?")
            time_str = fire_display(r["cook_time"])
            table.add_row(
                str(r["id"]),
                r["name"],
                time_str,
                f"{diff} {r['difficulty']}",
                str(r["servings"]),
                ", ".join(r["tags"]) if r["tags"] else "—",
            )
        console.print(table)
    else:
        print(f"\n📜 Grimorio de Recetas ({len(recipes)} recetas)")
        print("─" * 60)
        for r in recipes:
            diff = DIFFICULTY_RUNES.get(r["difficulty"], "?")
            print(f"  [{r['id']}] {r['name']}")
            print(f"      {FIRE} {r['cook_time']} min | {diff} {r['difficulty']} | {r['servings']} porciones")
            if r["tags"]:
                print(f"      Tags: {', '.join(r['tags'])}")
        print("─" * 60)


def cmd_show(args):
    """Show full recipe details as a parchment scroll."""
    recipe = db.get_recipe(args.nombre_or_id)
    if not recipe:
        if RICH_AVAILABLE:
            console.print(f"[bold red]⚔️ No se encontró la receta '{args.nombre_or_id}'[/bold red]")
        else:
            print(f"⚔️ No se encontró la receta '{args.nombre_or_id}'")
        return

    sections = []
    sections.append(("Tiempo de cocción", fire_display(recipe["cook_time"])))
    sections.append(("Dificultad", f"{DIFFICULTY_RUNES.get(recipe['difficulty'], '?')} {recipe['difficulty']}"))
    sections.append(("Porciones", str(recipe["servings"])))
    sections.append(("Tags", ", ".join(recipe["tags"]) if recipe["tags"] else "—"))

    ingredients_lines = []
    for ing in recipe["ingredients"]:
        amt = f"{ing['amount']} {ing['unit']}".strip()
        ingredients_lines.append(f"  • {amt} {ing['name']}" if amt else f"  • {ing['name']}")
    sections.append(("Ingredientes", "\n" + "\n".join(ingredients_lines) if ingredients_lines else "—"))

    steps_lines = []
    for inst in recipe["instructions"]:
        steps_lines.append(f"  {inst['step_num']}. {inst['text']}")
    sections.append(("Instrucciones", "\n" + "\n".join(steps_lines) if steps_lines else "—"))

    # Build rich parchment
    if RICH_AVAILABLE:
        content = Text()
        for label, value in sections[:-2]:  # single-line sections
            content.append(f"{label}: ", style="bold cyan")
            content.append(f"{value}\n")
        content.append("\n")
        content.append("Ingredientes:\n", style="bold yellow")
        for ing in recipe["ingredients"]:
            amt = f"{ing['amount']} {ing['unit']}".strip()
            content.append(f"  • {amt} {ing['name']}\n")
        content.append("\n")
        content.append("Instrucciones:\n", style="bold yellow")
        for inst in recipe["instructions"]:
            content.append(f"  {inst['step_num']}. {inst['text']}\n")

        console.print(Panel(content, title=f"📜 {recipe['name']}", border_style="bright_yellow", subtitle=f"ID: {recipe['id']} | {recipe['created']}"))
    else:
        print(format_parchment(recipe["name"], sections))


def cmd_search(args):
    """Search recipes by name, ingredient, or tag."""
    results = db.search(args.query)

    if not results:
        if RICH_AVAILABLE:
            console.print(f"[dim]🔮 No se encontraron recetas para '{args.query}'[/dim]")
        else:
            print(f"🔮 No se encontraron recetas para '{args.query}'")
        return

    if RICH_AVAILABLE:
        console.print(f"[bold]🔍 Resultados para '{args.query}'[/bold] ({len(results)} recetas):")
        for r in results:
            diff = DIFFICULTY_RUNES.get(r["difficulty"], "?")
            console.print(f"  [{r['id']}] [cyan]{r['name']}[/cyan] — {FIRE}{r['cook_time']}min {diff}{r['difficulty']} | Tags: {', '.join(r['tags']) or '—'}")
    else:
        print(f"\n🔍 Resultados para '{args.query}' ({len(results)} recetas):")
        for r in results:
            diff = DIFFICULTY_RUNES.get(r["difficulty"], "?")
            print(f"  [{r['id']}] {r['name']} — {FIRE}{r['cook_time']}min {diff}{r['difficulty']} | Tags: {', '.join(r['tags']) or '—'}")


def cmd_edit(args):
    """Edit an existing recipe."""
    tags = args.tags.split(",") if args.tags else None
    success = db.edit_recipe(
        args.nombre_or_id,
        name=args.name,
        cook_time=args.time,
        difficulty=args.difficulty,
        servings=args.servings,
        tags=tags,
    )
    if success:
        if RICH_AVAILABLE:
            console.print(f"[bold green]✏️ Receta actualizada en el grimorio[/bold green]")
        else:
            print("✏️ Receta actualizada en el grimorio")
    else:
        if RICH_AVAILABLE:
            console.print(f"[bold red]⚔️ No se encontró la receta '{args.nombre_or_id}'[/bold red]")
        else:
            print(f"⚔️ No se encontró la receta '{args.nombre_or_id}'")


def cmd_delete(args):
    """Delete a recipe from the grimoire."""
    success = db.delete_recipe(args.nombre_or_id)
    if success:
        if RICH_AVAILABLE:
            console.print(f"[bold red]🗡️ Receta '{args.nombre_or_id}' eliminada del grimorio[/bold red]")
        else:
            print(f"🗡️ Receta '{args.nombre_or_id}' eliminada del grimorio")
    else:
        if RICH_AVAILABLE:
            console.print(f"[bold red]⚔️ No se encontró la receta '{args.nombre_or_id}'[/bold red]")
        else:
            print(f"⚔️ No se encontró la receta '{args.nombre_or_id}'")


def cmd_plan(args):
    """Generate a weekly meal plan."""
    days = args.days or 7
    plan = db.generate_meal_plan(days=days)

    if not plan:
        if RICH_AVAILABLE:
            console.print("[dim]El grimorio está vacío. Agregue recetas primero.[/dim]")
        else:
            print("El grimorio está vacío. Agregue recetas primero.")
        return

    meal_plan = db.get_meal_plan()

    if RICH_AVAILABLE:
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        current_day = 0
        for entry in meal_plan:
            if entry["day"] != current_day:
                current_day = entry["day"]
                day_name = day_names[(current_day - 1) % 7]
                console.print(f"\n[bold bright_cyan]═══ Día {current_day} — {day_name} ═══[/bold bright_cyan]")
            slot_icon = SLOT_ICONS.get(entry["slot"], "•")
            diff = DIFFICULTY_RUNES.get(entry["difficulty"] or "medio", "?")
            console.print(f"  {slot_icon} {entry['slot'].title():12} → [bold]{entry['recipe_name']}[/bold] ({FIRE}{entry['cook_time']}min {diff})")
        console.print()
    else:
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        current_day = 0
        for entry in meal_plan:
            if entry["day"] != current_day:
                current_day = entry["day"]
                day_name = day_names[(current_day - 1) % 7]
                print(f"\n═══ Día {current_day} — {day_name} ═══")
            slot_icon = SLOT_ICONS.get(entry["slot"], "•")
            diff = DIFFICULTY_RUNES.get(entry["difficulty"] or "medio", "?")
            print(f"  {slot_icon} {entry['slot'].title():12} → {entry['recipe_name']} ({FIRE}{entry['cook_time']}min {diff})")
        print()


def cmd_shopping(args):
    """Generate shopping list from meal plan."""
    days = args.days or 7
    items = db.get_shopping_list(days=days)

    if not items:
        if RICH_AVAILABLE:
            console.print("[dim]No hay plan de comidas. Use 'plan' primero.[/dim]")
        else:
            print("No hay plan de comidas. Use 'plan' primero.")
        return

    if RICH_AVAILABLE:
        console.print(Panel("[bold]👜 Pergamino de Compras[/bold]", border_style="bright_yellow"))
        table = Table(show_lines=True)
        table.add_column("Cantidad", style="cyan", width=10)
        table.add_column("Unidad", style="green", width=12)
        table.add_column("Ingrediente", style="bold white")

        for item in items:
            table.add_row(item["amount"], item["unit"], item["name"])
        console.print(table)
        console.print(f"[dim]{len(items)} ingredientes para {days} días[/dim]")
    else:
        print(f"\n👜 Pergamino de Compras ({len(items)} ingredientes para {days} días)")
        print("─" * 50)
        for item in items:
            amt = f"{item['amount']} {item['unit']}".strip()
            print(f"  • {amt:20} {item['name']}")


def cmd_export(args):
    """Export a recipe as Markdown or JSON."""
    recipe = db.get_recipe(args.nombre_or_id)
    if not recipe:
        if RICH_AVAILABLE:
            console.print(f"[bold red]⚔️ No se encontró la receta '{args.nombre_or_id}'[/bold red]")
        else:
            print(f"⚔️ No se encontró la receta '{args.nombre_or_id}'")
        return

    fmt = args.format or "md"

    if fmt == "json":
        output = json.dumps(recipe, indent=2, ensure_ascii=False)
    else:
        # Markdown scroll format
        lines = [f"# 📜 {recipe['name']}", ""]
        lines.append(f"**Tiempo de cocción:** {recipe['cook_time']} min {FIRE}")
        lines.append(f"**Dificultad:** {DIFFICULTY_RUNES.get(recipe['difficulty'], '?')} {recipe['difficulty']}")
        lines.append(f"**Porciones:** {recipe['servings']}")
        if recipe["tags"]:
            lines.append(f"**Tags:** {', '.join(recipe['tags'])}")
        lines.append("")
        lines.append("## Ingredientes")
        for ing in recipe["ingredients"]:
            amt = f"{ing['amount']} {ing['unit']}".strip()
            lines.append(f"- {amt} {ing['name']}" if amt else f"- {ing['name']}")
        lines.append("")
        lines.append("## Instrucciones")
        for inst in recipe["instructions"]:
            lines.append(f"{inst['step_num']}. {inst['text']}")
        lines.append("")
        output = "\n".join(lines)

    print(output)
    return output


# ── CLI Setup ───────────────────────────────────────────────
def build_parser():
    parser = argparse.ArgumentParser(
        prog="midgard-recipes",
        description="⚔️ Midgard Recipe Manager — Grimorio de Recetas del Yggdrasil",
    )
    sub = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # add
    p_add = sub.add_parser("add", help="Agregar receta al grimorio")
    p_add.add_argument("nombre", help="Nombre de la receta")
    p_add.add_argument("--time", type=int, default=0, help="Tiempo de cocción en minutos")
    p_add.add_argument("--difficulty", choices=["facil", "medio", "dificil"], default="medio", help="Dificultad")
    p_add.add_argument("--tags", default="", help="Tags separados por coma")
    p_add.add_argument("--servings", type=int, default=2, help="Porciones")
    p_add.add_argument("--ingredient", action="append", help='Ingrediente: "2 tazas harina"')
    p_add.add_argument("--step", action="append", help="Paso de instrucción")

    # list
    p_list = sub.add_parser("list", help="Listar recetas del grimorio")
    p_list.add_argument("--tag", help="Filtrar por tag")
    p_list.add_argument("--difficulty", choices=["facil", "medio", "dificil"], help="Filtrar por dificultad")
    p_list.add_argument("--time-max", type=int, help="Tiempo máximo en minutos")

    # show
    p_show = sub.add_parser("show", help="Mostrar receta completa")
    p_show.add_argument("nombre_or_id", help="Nombre o ID de la receta")

    # search
    p_search = sub.add_parser("search", help="Buscar recetas")
    p_search.add_argument("query", help="Término de búsqueda")

    # edit
    p_edit = sub.add_parser("edit", help="Editar receta")
    p_edit.add_argument("nombre_or_id", help="Nombre o ID de la receta")
    p_edit.add_argument("--name", help="Nuevo nombre")
    p_edit.add_argument("--time", type=int, help="Nuevo tiempo de cocción")
    p_edit.add_argument("--difficulty", choices=["facil", "medio", "dificil"], help="Nueva dificultad")
    p_edit.add_argument("--servings", type=int, help="Nueva porciones")
    p_edit.add_argument("--tags", help="Nuevos tags separados por coma")

    # delete
    p_del = sub.add_parser("delete", help="Eliminar receta")
    p_del.add_argument("nombre_or_id", help="Nombre o ID de la receta")

    # plan
    p_plan = sub.add_parser("plan", help="Generar plan de comidas semanal")
    p_plan.add_argument("--days", type=int, default=7, help="Número de días")

    # shopping
    p_shop = sub.add_parser("shopping", help="Generar lista de compras del plan semanal")
    p_shop.add_argument("--days", type=int, default=7, help="Número de días")

    # export
    p_exp = sub.add_parser("export", help="Exportar receta como Markdown o JSON")
    p_exp.add_argument("nombre_or_id", help="Nombre o ID de la receta")
    p_exp.add_argument("--format", choices=["md", "json"], default="md", help="Formato de exportación")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "add": cmd_add,
        "list": cmd_list,
        "show": cmd_show,
        "search": cmd_search,
        "edit": cmd_edit,
        "delete": cmd_delete,
        "plan": cmd_plan,
        "shopping": cmd_shopping,
        "export": cmd_export,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()