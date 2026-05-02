#!/usr/bin/env python3
"""
᛭ Midgard Finanzas — Tracker de Finanzas Personales ᛭
CLI con estética dark fantasy nórdica para el reino de Midgard.
"""

import argparse
import csv
import io
import json
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from finanzas_db import FinanzasDB, CATEGORIAS_PREDEFINIDAS, get_db

# ─── Consola Rich ─────────────────────────────────────────────────────────────

console = Console()

# ─── Constants ─────────────────────────────────────────────────────────────────

RUNE_HEADER = "᛭"
INGRESO = "bold green"
GASTO = "bold red"
WARNING = "bold yellow"
SUBTLE = "dim"


def _runic_title(text: str) -> str:
    return RUNE_HEADER + " " + text + " " + RUNE_HEADER


def _money(amount: float) -> str:
    return "${:,.2f}".format(amount)


# ─── Validaciones ─────────────────────────────────────────────────────────────

def _validate_category(category: str) -> str:
    cat = category.lower().strip()
    if cat not in CATEGORIAS_PREDEFINIDAS:
        console.print(
            "[{}]Categoría '{}' no es predefinida.[/{}] "
            "Categorías válidas: {}".format(WARNING, category, WARNING,
            ", ".join(CATEGORIAS_PREDEFINIDAS))
        )
        console.print("[{}]Se registrará de todas formas.[/]".format(SUBTLE))
    return cat


def _validate_date(date_str: str) -> str:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        console.print("[{}]Fecha inválida: {}. Use YYYY-MM-DD.[/]".format(GASTO, date_str, GASTO))
        sys.exit(1)


def _validate_month(month_str: str) -> str:
    try:
        datetime.strptime(month_str, "%Y-%m")
        return month_str
    except ValueError:
        console.print("[{}]Mes inválido: {}. Use YYYY-MM.[/]".format(GASTO, month_str, GASTO))
        sys.exit(1)


# ─── Comandos ─────────────────────────────────────────────────────────────────

def cmd_add(args: argparse.Namespace) -> None:
    """Agrega un gasto."""
    db = get_db()
    cat = _validate_category(args.categoria)
    fecha = _validate_date(args.fecha) if args.fecha else None
    tx_id = db.add_transaction(
        tx_type="gasto",
        amount=args.monto,
        category=cat,
        description=args.desc or "",
        date=fecha,
    )
    fecha_display = fecha or datetime.now().strftime("%Y-%m-%d")
    desc_display = args.desc or "—"
    content = (
        "[{}]Gasto registrado[/{}]\n\n"
        "  ᛭ [bold]Monto:[/bold]      {}\n"
        "  ᛭ [bold]Categoría:[/bold]  {}\n"
        "  ᛭ [bold]Desc:[/bold]       {}\n"
        "  ᛭ [bold]Fecha:[/bold]      {}\n\n"
        "  [dim]ID #{tx_id}[/dim]"
    ).format(GASTO, GASTO, _money(args.monto), cat, desc_display, fecha_display, tx_id=tx_id)
    console.print(Panel(content, title=_runic_title("Registro de Gasto"), border_style="red"))


def cmd_income(args: argparse.Namespace) -> None:
    """Agrega un ingreso."""
    db = get_db()
    cat = _validate_category(args.categoria)
    fecha = _validate_date(args.fecha) if args.fecha else None
    tx_id = db.add_transaction(
        tx_type="ingreso",
        amount=args.monto,
        category=cat,
        description=args.desc or "",
        date=fecha,
    )
    fecha_display = fecha or datetime.now().strftime("%Y-%m-%d")
    desc_display = args.desc or "—"
    content = (
        "[{}]Ingreso registrado[/{}]\n\n"
        "  ᛭ [bold]Monto:[/bold]      {}\n"
        "  ᛭ [bold]Categoría:[/bold]  {}\n"
        "  ᛭ [bold]Desc:[/bold]       {}\n"
        "  ᛭ [bold]Fecha:[/bold]      {}\n\n"
        "  [dim]ID #{tx_id}[/dim]"
    ).format(INGRESO, INGRESO, _money(args.monto), cat, desc_display, fecha_display, tx_id=tx_id)
    console.print(Panel(content, title=_runic_title("Registro de Ingreso"), border_style="green"))


def cmd_balance(args: argparse.Namespace) -> None:
    """Muestra balance del mes."""
    db = get_db()
    month = args.mes or datetime.now().strftime("%Y-%m")
    _validate_month(month)
    bal = db.get_balance(month)

    if bal["balance"] >= 0:
        balance_color = "green"
        sign = "+"
    else:
        balance_color = "red"
        sign = ""

    content = (
        "  [{}]Ingresos:[/{}]   {}\n"
        "  [{}]Gastos:[/{}]     {}\n"
        "  ─────────────────────────\n"
        "  [{}]Balance:[/{}]    {}{}"
    ).format(
        INGRESO, INGRESO, _money(bal["ingresos"]),
        GASTO, GASTO, _money(bal["gastos"]),
        balance_color, balance_color, sign, _money(bal["balance"]),
    )
    console.print(Panel(content, title=_runic_title("Balance — " + month), border_style="cyan"))


def cmd_report(args: argparse.Namespace) -> None:
    """Reporte mensual por categoría."""
    db = get_db()
    month = args.mes or datetime.now().strftime("%Y-%m")
    _validate_month(month)
    fmt = args.format or "table"
    rows = db.get_report_by_category(month)

    if not rows:
        console.print("[{}]Sin transacciones para {}.[/]".format(WARNING, month, WARNING))
        return

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["category", "type", "total", "count"])
        writer.writeheader()
        writer.writerows(rows)
        console.print(output.getvalue())
        return

    # ── Table format ────────────────────────────────────────────────────
    table = Table(
        title=_runic_title("Reporte — " + month),
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        title_style="bold cyan",
    )
    table.add_column("Categoría", style="bold")
    table.add_column("Tipo", justify="center")
    table.add_column("Total", justify="right")
    table.add_column("# Txns", justify="center", style="dim")

    for r in rows:
        tipo = r["type"]
        if tipo == "ingreso":
            tipo_str = "[{}]⬆ Ingreso[/{}]".format(INGRESO, INGRESO)
            money_s = INGRESO
        else:
            tipo_str = "[{}]⬇ Gasto[/{}]".format(GASTO, GASTO)
            money_s = GASTO
        money_str = "[{}]{}[/{}]".format(money_s, _money(r["total"]), money_s)
        table.add_row(r["category"], tipo_str, money_str, str(r["count"]))

    console.print(table)


def cmd_budget(args: argparse.Namespace) -> None:
    """Subcomandos de presupuesto."""
    if args.budget_action == "set":
        db = get_db()
        db.set_budget(args.categoria, args.monto)
        content = (
            "Presupuesto mensual para [{}]{}[/{}] "
            "establecido en [{}]{}[/{}]"
        ).format(INGRESO, args.categoria, INGRESO, INGRESO, _money(args.monto), INGRESO)
        console.print(Panel(content, title=_runic_title("Presupuesto Definido"), border_style="green"))

    elif args.budget_action == "check":
        db = get_db()
        month = args.mes or datetime.now().strftime("%Y-%m")
        _validate_month(month)
        results = db.check_budget(month)

        if not results:
            console.print(
                "[{}]No hay presupuestos configurados. "
                "Use 'budget set <categoria> <monto>'.[/{}]".format(WARNING, WARNING)
            )
            return

        table = Table(
            title=_runic_title("Presupuestos — " + month),
            show_header=True,
            header_style="bold cyan",
            border_style="bright_black",
            title_style="bold cyan",
        )
        table.add_column("Categoría", style="bold")
        table.add_column("Límite", justify="right")
        table.add_column("Gastado", justify="right")
        table.add_column("Restante", justify="right")
        table.add_column("%", justify="center")

        for r in results:
            rem_style = GASTO if r["over"] else INGRESO
            if r["pct"] > 90:
                pct_style = GASTO
            elif r["pct"] > 70:
                pct_style = WARNING
            else:
                pct_style = INGRESO
            over_mark = " ⚠" if r["over"] else ""
            table.add_row(
                r["category"],
                _money(r["limit"]),
                "[{}]{}[/{}]".format(GASTO, _money(r["spent"]), GASTO),
                "[{}]{}[/{}]".format(rem_style, _money(r["remaining"]), rem_style),
                "[{}]{}{}[/{}]".format(pct_style, r["pct"], "%", pct_style) + over_mark,
            )

        console.print(table)
    else:
        console.print("[{}]Acción de presupuesto no reconocida. Use 'set' o 'check'.[/{}]".format(WARNING, WARNING))


def cmd_export(args: argparse.Namespace) -> None:
    """Exporta datos a CSV o JSON."""
    db = get_db()
    month = args.mes or datetime.now().strftime("%Y-%m")
    _validate_month(month)
    fmt = args.format or "csv"

    transactions = db.get_transactions(month=month)
    budgets = db.get_all_budgets()
    balance = db.get_balance(month)

    if fmt == "json":
        data = {
            "month": month,
            "balance": balance,
            "transactions": transactions,
            "budgets": budgets,
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=["id", "type", "amount", "category", "description", "date"])
        writer.writeheader()
        writer.writerows(transactions)


# ─── CLI Parser ───────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="midgard-finanzas",
        description="᛭ Midgard Finanzas — Tracker de Finanzas Personales ᛭",
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # add <monto> <categoria>
    p_add = subparsers.add_parser("add", help="Agregar un gasto")
    p_add.add_argument("monto", type=float, help="Monto del gasto")
    p_add.add_argument("categoria", help="Categoría del gasto")
    p_add.add_argument("--desc", help="Descripción del gasto")
    p_add.add_argument("--fecha", help="Fecha YYYY-MM-DD (default: hoy)")

    # income <monto> <categoria>
    p_inc = subparsers.add_parser("income", help="Agregar un ingreso")
    p_inc.add_argument("monto", type=float, help="Monto del ingreso")
    p_inc.add_argument("categoria", help="Categoría del ingreso")
    p_inc.add_argument("--desc", help="Descripción del ingreso")
    p_inc.add_argument("--fecha", help="Fecha YYYY-MM-DD (default: hoy)")

    # balance [--mes]
    p_bal = subparsers.add_parser("balance", help="Mostrar balance del mes")
    p_bal.add_argument("--mes", help="Mes YYYY-MM (default: mes actual)")

    # report [--mes] [--format]
    p_rep = subparsers.add_parser("report", help="Reporte mensual por categoría")
    p_rep.add_argument("--mes", help="Mes YYYY-MM (default: mes actual)")
    p_rep.add_argument("--format", choices=["table", "csv"], default="table", help="Formato de salida")

    # budget set/check
    p_bud = subparsers.add_parser("budget", help="Gestión de presupuestos")
    bud_sub = p_bud.add_subparsers(dest="budget_action", help="Acciones de presupuesto")

    p_bset = bud_sub.add_parser("set", help="Definir presupuesto mensual")
    p_bset.add_argument("categoria", help="Categoría")
    p_bset.add_argument("monto", type=float, help="Límite mensual")

    p_bcheck = bud_sub.add_parser("check", help="Verificar presupuestos vs gasto real")
    p_bcheck.add_argument("--mes", help="Mes YYYY-MM (default: mes actual)")

    # export
    p_exp = subparsers.add_parser("export", help="Exportar datos")
    p_exp.add_argument("--mes", help="Mes YYYY-MM (default: mes actual)")
    p_exp.add_argument("--format", choices=["csv", "json"], default="csv", help="Formato de exportación")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        console.print("\n[{}]Runas iluminan el camino de tus finanzas.[/]".format(SUBTLE))
        return

    commands = {
        "add": cmd_add,
        "income": cmd_income,
        "balance": cmd_balance,
        "report": cmd_report,
        "budget": cmd_budget,
        "export": cmd_export,
    }

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()