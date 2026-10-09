"""Local assets for the interactive audit figure."""
from pathlib import Path

from plotly.offline import get_plotlyjs


def coverage_assets(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
