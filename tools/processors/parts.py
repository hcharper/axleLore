"""Parts catalog normalizer for AxleLore.

Reads raw SOR JSON from data/raw/sor/ and produces data/fzj80_parts.jsonl
for the knowledge-base builder.

Usage:
    python -m tools.processors.parts
    python -m tools.processors.parts --input data/raw/sor --output data/fzj80_parts.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


def process_parts(
    raw_path: Path = Path("data/raw/sor"),
    output_jsonl: Path | None = None,
) -> list[dict]:
    """Process raw SOR JSON into normalized JSONL documents.

    Groups related parts by system (all front axle parts in one doc, etc.)
    and deduplicates by part number.
    """
    # Collect all parts grouped by system
    by_system: dict[str, list[dict]] = defaultdict(list)
    seen_pn: set[str] = set()

    for json_file in sorted(raw_path.glob("*.json")):
        with open(json_file) as f:
            data = json.load(f)

        for part in data.get("parts", []):
            pn = part.get("part_number", "").strip()
            if pn and pn in seen_pn:
                continue
            if pn:
                seen_pn.add(pn)

            system = part.get("system", "general")
            by_system[system].append(part)

    all_docs: list[dict] = []

    for system, parts in sorted(by_system.items()):
        if not parts:
            continue

        # Build a document for this system group
        lines = [f"SOR Parts Catalog — {system.replace('_', ' ').title()}"]
        lines.append(f"{len(parts)} parts\n")

        for part in parts:
            pn = part.get("part_number", "N/A")
            desc = part.get("description", "")
            price = part.get("price", "")
            cat = part.get("category", "")

            entry = f"- {pn}: {desc}"
            if price:
                entry += f"  ({price})"
            if cat:
                entry += f"  [{cat}]"
            lines.append(entry)

        content = "\n".join(lines)

        all_docs.append({
            "source": "sor",
            "source_id": f"parts_{system}",
            "title": f"SOR Parts: {system.replace('_', ' ').title()}",
            "content": content,
            "category": "parts",
            "url": "https://www.sor.com/80serieslandcruiser/",
            "date": "",
            "quality_score": 0.8,
            "metadata": {
                "vehicle_type": "fzj80",
                "system": system,
                "part_count": len(parts),
            },
        })

    logger.info("Parts: %d documents from %d systems (%d unique parts)",
                len(all_docs), len(by_system), len(seen_pn))

    if output_jsonl:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with open(output_jsonl, "w") as f:
            for doc in all_docs:
                f.write(json.dumps(doc) + "\n")
        logger.info("Wrote %d documents to %s", len(all_docs), output_jsonl)

    return all_docs


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Normalize SOR parts data into JSONL for AxleLore KB")
    parser.add_argument("--input", type=Path, default=Path("data/raw/sor"), help="Raw SOR data directory")
    parser.add_argument("--output", type=Path, default=None, help="Output JSONL path")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    output = args.output or project_root / "data" / "fzj80_parts.jsonl"

    docs = process_parts(args.input, output)
    print(f"Processed {len(docs)} parts documents -> {output}")


if __name__ == "__main__":
    main()
