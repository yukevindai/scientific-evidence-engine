"""Local scientific evidence tools. Coordinates and uncertainty are always explicit."""
__version__ = "0.2.0"

from .papers import ingest_paper, render_figure
from .digitize import digitize
from .exports import export_dataset, verify_export, import_dataset
from .evidence import add_evidence, add_claim, index_paper, propose_link, review_link
from .research import search, research, assess_claim, import_draft
from .reports import export_report, verify_report

__all__ = ["ingest_paper", "render_figure", "digitize", "export_dataset", "verify_export", "import_dataset",
           "add_evidence", "add_claim", "index_paper", "propose_link", "review_link", "search", "research",
           "assess_claim", "import_draft", "export_report", "verify_report"]
