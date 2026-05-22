"""Generate tests/fixtures/sample.pdf (2+ pages, 500+ words)."""

from pathlib import Path

from fpdf import FPDF

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample.pdf"

PARAGRAPH = (
    "Artificial intelligence document assistants help users query PDF content through "
    "retrieval augmented generation pipelines. Local models via Ollama enable offline "
    "embeddings and chat without cloud APIs. ChromaDB stores vector indexes per document. "
    "FastAPI exposes upload and streaming chat endpoints for developers. "
    "PyMuPDF extracts text from each page before chunking with overlap. "
    "Recursive character splitters preserve paragraph boundaries when possible. "
    "Semantic search retrieves the most relevant passages for each user question. "
    "Conversation memory keeps recent turns for contextual follow up questions. "
    "Graceful degradation returns clear errors when Ollama is not running locally. "
)


def generate() -> None:
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    effective_width = pdf.w - pdf.l_margin - pdf.r_margin
    for page in range(2):
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        words = 0
        while words < 280:
            pdf.multi_cell(effective_width, 6, PARAGRAPH)
            words += len(PARAGRAPH.split())

    pdf.output(str(FIXTURE_PATH))
    print(f"Wrote {FIXTURE_PATH}")


if __name__ == "__main__":
    generate()
