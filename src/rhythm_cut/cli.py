"""Small CLI surface for the first development loop."""

from pathlib import Path

import typer

from rhythm_cut.domain.models import EditPlan

app = typer.Typer(help="Rhythm Cut: constraint-aware beat editing")


@app.command()
def validate(plan: Path) -> None:
    """Validate an Edit Plan JSON file."""
    parsed = EditPlan.model_validate_json(plan.read_text())
    typer.echo(f"valid {parsed.schema_version}: {len(parsed.shots)} shots, {parsed.duration_s:.3f}s")


@app.command()
def version() -> None:
    """Print the package version."""
    from rhythm_cut import __version__

    typer.echo(__version__)
