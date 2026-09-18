#!/usr/bin/env python3
"""PasarGuard CLI"""

from pathlib import Path
from typing import Annotated

import typer

from cli import console
from cli.admin import generate_temp_key
from cli.node import pair_node

app = typer.Typer(
    name="PasarGuard",
    help="PasarGuard CLI",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.command("generate-temp-key")
def cmd_generate_temp_key():
    """Generate a one-time temp key for owner setup (create/reset/delete)."""
    generate_temp_key()


@app.command("pair-node")
def cmd_pair_node(
    node_id: int,
    file: Annotated[Path, typer.Option("--file", exists=True, dir_okay=False, readable=True)],
):
    """Update an existing node from a root-only pairing JSON file."""
    status = pair_node(node_id, file)
    console.print(f"[green]Node {node_id} pairing updated.[/green] Status: {status}")


@app.command()
def version():
    """Show PasarGuard version."""
    from app import __version__

    console.print(f"[bold blue]PasarGuard[/bold blue] version [bold green]{__version__}[/bold green]")


if __name__ == "__main__":
    app()
