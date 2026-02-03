"""Rich terminal output formatting."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import Any

console = Console()


def format_duration(minutes: int) -> str:
    """Format minutes as Xh Ym string."""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"


def show_schedule(schedule: dict[str, Any], title: str = "Predicted Schedule for Today") -> None:
    """Display schedule as a Rich table."""
    table = Table(title=f"[bold cyan]{title}[/bold cyan]", show_header=True)

    table.add_column("Event", style="bold")
    table.add_column("Start", justify="center")
    table.add_column("End", justify="center")
    table.add_column("Duration", justify="center")
    table.add_column("Status", justify="center")

    table.add_row(
        "Wake",
        schedule["wake_time"],
        "-",
        "-",
        "[green]Actual[/green]"
    )

    for i, nap in enumerate(schedule["naps"], 1):
        status = "[yellow]Predicted[/yellow]" if nap.get("predicted", True) else "[green]Actual[/green]"
        table.add_row(
            f"Nap {i}",
            nap["start"],
            nap["end"],
            format_duration(nap["duration_minutes"]),
            status
        )

    table.add_row(
        "Night",
        schedule["night_sleep"],
        "-",
        "-",
        "[yellow]Predicted[/yellow]"
    )

    console.print()
    console.print(table)
    console.print()


def show_history(days: list[dict[str, Any]], limit: int = 7) -> None:
    """Display history of recent days."""
    if not days:
        console.print("[yellow]No historical data found.[/yellow]")
        return

    recent = sorted(days, key=lambda d: d["date"], reverse=True)[:limit]

    table = Table(title="[bold cyan]Sleep History[/bold cyan]", show_header=True)

    table.add_column("Date", style="bold")
    table.add_column("Wake", justify="center")
    table.add_column("Naps", justify="center")
    table.add_column("Night", justify="center")

    for day in recent:
        naps_str = ""
        if day.get("naps"):
            naps_str = ", ".join(
                f"{n['start']}-{n['end']}"
                for n in day["naps"]
            )

        table.add_row(
            day["date"],
            day.get("morning_wake", "-"),
            naps_str or "-",
            day.get("night_sleep", "-")
        )

    console.print()
    console.print(table)
    console.print()


def show_model_info(model: dict[str, Any]) -> None:
    """Display model information."""
    text = Text()
    text.append("Model Information\n", style="bold cyan")
    text.append(f"Trained on: {model.get('trained_on', 'Never')}\n")
    text.append(f"Training days: {model.get('days_count', 0)}\n")
    text.append(f"Typical naps: {model.get('typical_naps_count', 'N/A')}\n\n")

    text.append("Wake Windows: ", style="bold")
    windows = model.get("wake_windows", [])
    text.append(", ".join(f"{w}min" for w in windows) + "\n")

    text.append("Nap Durations: ", style="bold")
    durations = model.get("nap_durations", [])
    text.append(", ".join(f"{d}min" for d in durations) + "\n")

    text.append("Night Window: ", style="bold")
    text.append(f"{model.get('night_sleep_window', 'N/A')}min\n")

    console.print()
    console.print(Panel(text))
    console.print()


def success(message: str) -> None:
    """Display success message."""
    console.print(f"[green]{message}[/green]")


def error(message: str) -> None:
    """Display error message."""
    console.print(f"[red]Error: {message}[/red]")


def warning(message: str) -> None:
    """Display warning message."""
    console.print(f"[yellow]{message}[/yellow]")


def info(message: str) -> None:
    """Display info message."""
    console.print(f"[cyan]{message}[/cyan]")
