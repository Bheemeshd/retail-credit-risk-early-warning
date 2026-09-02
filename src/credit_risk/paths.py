"""Repository paths and small filesystem helpers."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"
DEFAULT_PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports"


def ensure_directories(root: Path) -> None:
    """Create the generated-output directories below *root*."""
    for relative in ("data/raw", "data/processed", "artifacts/charts", "reports"):
        (root / relative).mkdir(parents=True, exist_ok=True)

