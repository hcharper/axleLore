"""FSM (Factory Service Manual) PDF processor for RigSherpa.

Extracts text from Toyota FSM PDFs (scanned or digital) using PyMuPDF
with Tesseract OCR fallback.  Classifies sections by heading patterns,
extracts procedures and specifications, and outputs JSONL for the
knowledge-base builder.

Usage:
    python -m tools.processors.fsm /path/to/fsm.pdf -o data/fsm_output.jsonl
    python -m tools.processors.fsm /path/to/fsm_dir/ --vehicle fzj80
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section classification
# ---------------------------------------------------------------------------

# Maps FSM section heading patterns → ChromaDB categories
_HEADING_CATEGORY_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"engine|1fz|cylinder|piston|crankshaft|camshaft|timing|valve", re.I), "engine"),
    (re.compile(r"oil|lubrication|coolant|cooling|radiator|thermostat|water pump", re.I), "engine"),
    (re.compile(r"fuel|injection|efi|throttle|intake|exhaust|emission|evap", re.I), "engine"),
    (re.compile(r"transmission|clutch|shift|gear|torque converter", re.I), "drivetrain"),
    (re.compile(r"transfer\s*case|t-case|center\s*diff", re.I), "drivetrain"),
    (re.compile(r"axle|differential|birfield|cv\s*joint|driveshaft|propeller", re.I), "drivetrain"),
    (re.compile(r"brake|abs|hydraulic|master\s*cylinder|caliper|drum|rotor", re.I), "chassis"),
    (re.compile(r"suspension|spring|shock|strut|bushing|sway\s*bar", re.I), "chassis"),
    (re.compile(r"steering|power\s*steer|tie\s*rod|knuckle|pitman", re.I), "chassis"),
    (re.compile(r"wheel|hub|bearing|tire|alignment", re.I), "chassis"),
    (re.compile(r"wiring|electrical|fuse|relay|ecu|sensor|connector|harness", re.I), "electrical"),
    (re.compile(r"alternator|starter|battery|ignition|charging", re.I), "electrical"),
    (re.compile(r"lighting|headl|tail\s*light|turn\s*signal|gauge|instrument", re.I), "electrical"),
    (re.compile(r"body|door|window|trim|seat|mirror|paint|rust|panel", re.I), "body"),
    (re.compile(r"hvac|heat|air\s*condition|blower|defrost", re.I), "body"),
]


def classify_section(heading: str) -> str:
    """Return the ChromaDB category for an FSM section heading."""
    for pattern, category in _HEADING_CATEGORY_MAP:
        if pattern.search(heading):
            return category
    return "general"


# ---------------------------------------------------------------------------
# Page data
# ---------------------------------------------------------------------------

@dataclass
class FSMPage:
    page_num: int
    text: str
    heading: str = ""
    is_ocr: bool = False


@dataclass
class FSMSection:
    heading: str
    category: str
    pages: list[FSMPage] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_pages(pdf_path: Path, ocr_threshold: int = 50) -> list[FSMPage]:
    """Extract text from a PDF, falling back to OCR for scanned pages.

    Args:
        pdf_path: Path to the PDF file.
        ocr_threshold: Minimum characters of native text before OCR is tried.

    Returns:
        List of FSMPage objects.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) is required. Install with: pip install pymupdf")
        raise

    pages: list[FSMPage] = []
    doc = fitz.open(str(pdf_path))

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        is_ocr = False

        # If native text is too short, try OCR
        if len(text) < ocr_threshold:
            ocr_text = _ocr_page(page)
            if ocr_text and len(ocr_text) > len(text):
                text = ocr_text
                is_ocr = True

        if text:
            pages.append(FSMPage(
                page_num=page_num + 1,
                text=text,
                heading=_extract_heading(text),
                is_ocr=is_ocr,
            ))

    doc.close()
    logger.info(
        "Extracted %d pages from %s (%d OCR)",
        len(pages),
        pdf_path.name,
        sum(1 for p in pages if p.is_ocr),
    )
    return pages


def _ocr_page(page) -> str:
    """Run Tesseract OCR on a PDF page rendered as an image."""
    try:
        import pytesseract
        from PIL import Image
        import io

        # Render page at 300 DPI
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="eng")
        return text.strip()
    except ImportError:
        logger.debug("pytesseract/PIL not available, skipping OCR")
        return ""
    except Exception as exc:
        logger.debug("OCR failed for page: %s", exc)
        return ""


def _extract_heading(text: str) -> str:
    """Try to extract the first heading-like line from page text."""
    for line in text.split("\n")[:5]:
        line = line.strip()
        # FSM headings are typically ALL CAPS or have section numbers
        if re.match(r"^[A-Z][A-Z\s\-/]{5,}$", line):
            return line
        if re.match(r"^\d{1,2}[\.\-]\d{1,2}\s+\w", line):
            return line
    return ""


# ---------------------------------------------------------------------------
# Section grouping
# ---------------------------------------------------------------------------

def group_into_sections(pages: list[FSMPage]) -> list[FSMSection]:
    """Group pages into sections based on heading changes."""
    if not pages:
        return []

    sections: list[FSMSection] = []
    current_heading = pages[0].heading or "General"
    current_section = FSMSection(
        heading=current_heading,
        category=classify_section(current_heading),
    )

    for page in pages:
        if page.heading and page.heading != current_heading:
            if current_section.pages:
                sections.append(current_section)
            current_heading = page.heading
            current_section = FSMSection(
                heading=current_heading,
                category=classify_section(current_heading),
            )
        current_section.pages.append(page)

    if current_section.pages:
        sections.append(current_section)

    return sections


# ---------------------------------------------------------------------------
# Document generation
# ---------------------------------------------------------------------------

def sections_to_documents(
    sections: list[FSMSection],
    pdf_name: str,
    vehicle_type: str = "fzj80",
    max_content_len: int = 3000,
) -> Iterator[dict]:
    """Convert FSM sections into builder-compatible document dicts."""
    for section in sections:
        text = section.text
        if not text or len(text.strip()) < 50:
            continue

        page_range = f"{section.pages[0].page_num}-{section.pages[-1].page_num}"

        # Split very long sections into chunks
        if len(text) > max_content_len:
            parts = _split_long_text(text, max_content_len)
            for i, part in enumerate(parts):
                yield {
                    "source": "fsm",
                    "source_id": f"{pdf_name}_p{page_range}_pt{i}",
                    "title": section.heading,
                    "content": part,
                    "category": section.category,
                    "metadata": {
                        "vehicle_type": vehicle_type,
                        "pdf": pdf_name,
                        "pages": page_range,
                        "part": i + 1,
                    },
                }
        else:
            yield {
                "source": "fsm",
                "source_id": f"{pdf_name}_p{page_range}",
                "title": section.heading,
                "content": text,
                "category": section.category,
                "metadata": {
                    "vehicle_type": vehicle_type,
                    "pdf": pdf_name,
                    "pages": page_range,
                },
            }


def _split_long_text(text: str, max_len: int) -> list[str]:
    """Split long text at paragraph boundaries."""
    paragraphs = re.split(r"\n{2,}", text)
    parts: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_len and current:
            parts.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        parts.append(current.strip())

    return parts if parts else [text[:max_len]]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_pdf(
    pdf_path: Path,
    vehicle_type: str = "fzj80",
    output_jsonl: Path | None = None,
) -> list[dict]:
    """Process a single FSM PDF into document dicts.

    Returns the list of documents.  If *output_jsonl* is provided, also
    appends to that file.
    """
    pages = extract_pages(pdf_path)
    sections = group_into_sections(pages)
    documents = list(sections_to_documents(sections, pdf_path.stem, vehicle_type))

    if output_jsonl:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with open(output_jsonl, "a") as f:
            for doc in documents:
                f.write(json.dumps(doc) + "\n")
        logger.info("Appended %d documents to %s", len(documents), output_jsonl)

    return documents


def process_directory(
    pdf_dir: Path,
    vehicle_type: str = "fzj80",
    output_jsonl: Path | None = None,
) -> list[dict]:
    """Process all PDFs in a directory."""
    all_docs: list[dict] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        logger.info("Processing: %s", pdf_path.name)
        docs = process_pdf(pdf_path, vehicle_type, output_jsonl)
        all_docs.extend(docs)
        logger.info("  -> %d documents", len(docs))
    return all_docs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Process FSM PDFs into JSONL for RigSherpa KB")
    parser.add_argument("input", type=Path, help="PDF file or directory of PDFs")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output JSONL path")
    parser.add_argument("--vehicle", default="fzj80", help="Vehicle type code")
    args = parser.parse_args()

    if not args.input.exists():
        logger.error("Input not found: %s", args.input)
        return

    project_root = Path(__file__).resolve().parent.parent.parent
    output = args.output or project_root / "data" / f"{args.vehicle}_fsm.jsonl"

    if args.input.is_dir():
        docs = process_directory(args.input, args.vehicle, output)
    else:
        docs = process_pdf(args.input, args.vehicle, output)

    print(f"Processed {len(docs)} documents -> {output}")

    # Print category summary
    cats: dict[str, int] = {}
    for d in docs:
        cats[d["category"]] = cats.get(d["category"], 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
