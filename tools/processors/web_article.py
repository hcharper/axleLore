"""Web article normalizer for AxleLore.

Reads raw article JSON from data/raw/web/ and produces data/fzj80_web.jsonl
for the knowledge-base builder.

Usage:
    python -m tools.processors.web_article
    python -m tools.processors.web_article --input data/raw/web --output data/fzj80_web.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Heading keyword patterns → category (reuse FSM heading logic)
_HEADING_CATEGORY: list[tuple[re.Pattern, str]] = [
    (re.compile(r"engine|1fz|cylinder|piston|oil|coolant|fuel|exhaust", re.I), "engine"),
    (re.compile(r"transmission|clutch|transfer|axle|diff|drivetrain|gear", re.I), "drivetrain"),
    (re.compile(r"electrical|wiring|fuse|relay|ecu|sensor|battery", re.I), "electrical"),
    (re.compile(r"brake|suspension|steering|chassis|wheel|tire", re.I), "chassis"),
    (re.compile(r"body|door|window|paint|rust|interior|hvac|seat", re.I), "body"),
    (re.compile(r"mod|upgrade|lift|build|swap|install", re.I), "forum_mods"),
    (re.compile(r"maintain|service|interval|change", re.I), "forum_maintenance"),
    (re.compile(r"troubleshoot|problem|fix|diagnos", re.I), "forum_troubleshoot"),
]


def _classify_heading(heading: str, fallback: str = "general") -> str:
    """Classify a section heading into a ChromaDB category."""
    for pattern, category in _HEADING_CATEGORY:
        if pattern.search(heading):
            return category
    return fallback


def process_web_articles(
    raw_path: Path = Path("data/raw/web"),
    output_jsonl: Path | None = None,
) -> list[dict]:
    """Process all raw web article JSON into normalized JSONL documents.

    Returns the list of documents.
    """
    all_docs: list[dict] = []

    for json_file in sorted(raw_path.glob("*.json")):
        with open(json_file) as f:
            data = json.load(f)

        url = data.get("url", "")
        title = data.get("title", json_file.stem)
        categories = data.get("categories", ["general"])
        sections = data.get("sections", [])
        full_text = data.get("full_text", "")

        if sections:
            # Split into section-level documents
            for i, section in enumerate(sections):
                heading = section.get("heading", "")
                content = section.get("content", "")
                if len(content) < 50:
                    continue

                # Classify section by heading, falling back to article-level category
                category = _classify_heading(heading, categories[0])

                # Prefix section content with context
                section_title = f"{title} — {heading}" if heading else title
                prefixed = f"{section_title}\n\n{content}"

                all_docs.append({
                    "source": "web",
                    "source_id": f"{json_file.stem}_s{i}",
                    "title": section_title,
                    "content": prefixed,
                    "category": category,
                    "url": url,
                    "date": "",
                    "quality_score": 0.7,
                    "metadata": {
                        "vehicle_type": "fzj80",
                        "original_title": title,
                        "section_heading": heading,
                    },
                })
        elif full_text and len(full_text) >= 100:
            # No sections detected — use full text as a single document
            all_docs.append({
                "source": "web",
                "source_id": json_file.stem,
                "title": title,
                "content": f"{title}\n\n{full_text}",
                "category": categories[0],
                "url": url,
                "date": "",
                "quality_score": 0.7,
                "metadata": {"vehicle_type": "fzj80"},
            })

    logger.info("Web articles: %d documents from %d files",
                len(all_docs), len(list(raw_path.glob("*.json"))))

    if output_jsonl:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with open(output_jsonl, "w") as f:
            for doc in all_docs:
                f.write(json.dumps(doc) + "\n")
        logger.info("Wrote %d documents to %s", len(all_docs), output_jsonl)

    return all_docs


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Normalize web articles into JSONL for AxleLore KB")
    parser.add_argument("--input", type=Path, default=Path("data/raw/web"), help="Raw web data directory")
    parser.add_argument("--output", type=Path, default=None, help="Output JSONL path")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    output = args.output or project_root / "data" / "fzj80_web.jsonl"

    docs = process_web_articles(args.input, output)
    print(f"Processed {len(docs)} web article documents -> {output}")


if __name__ == "__main__":
    main()
