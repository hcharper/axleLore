"""NHTSA data normalizer for RigSherpa.

Reads raw NHTSA JSON files (recalls and complaints) from data/raw/nhtsa/
and produces data/fzj80_nhtsa.jsonl for the knowledge-base builder.

Usage:
    python -m tools.processors.nhtsa
    python -m tools.processors.nhtsa --input data/raw/nhtsa --output data/fzj80_nhtsa.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# NHTSA component name → ChromaDB category
_COMPONENT_CATEGORY: dict[str, str] = {
    "ENGINE AND ENGINE COOLING": "engine",
    "ENGINE": "engine",
    "FUEL SYSTEM": "engine",
    "EXHAUST SYSTEM": "engine",
    "AIR BAGS": "chassis",
    "SERVICE BRAKES": "chassis",
    "SERVICE BRAKES, HYDRAULIC": "chassis",
    "SERVICE BRAKES, AIR": "chassis",
    "PARKING BRAKE": "chassis",
    "SUSPENSION": "chassis",
    "STEERING": "chassis",
    "WHEELS": "chassis",
    "TIRES": "chassis",
    "ELECTRICAL SYSTEM": "electrical",
    "LIGHTING": "electrical",
    "POWER TRAIN": "drivetrain",
    "VEHICLE SPEED CONTROL": "drivetrain",
    "SEAT BELTS": "body",
    "SEATS": "body",
    "STRUCTURE": "body",
    "EXTERIOR LIGHTING": "electrical",
    "INTERIOR LIGHTING": "electrical",
    "VISIBILITY": "body",
    "LATCHES/LOCKS/LINKAGES": "body",
}


def _component_to_category(component: str) -> str:
    """Map an NHTSA component name to a ChromaDB category."""
    key = component.strip().upper()
    if key in _COMPONENT_CATEGORY:
        return _COMPONENT_CATEGORY[key]
    # Partial match
    for nhtsa_name, cat in _COMPONENT_CATEGORY.items():
        if nhtsa_name in key or key in nhtsa_name:
            return cat
    return "general"


def _process_recalls(raw_path: Path) -> list[dict]:
    """Process recall JSON files into JSONL documents."""
    docs: list[dict] = []
    seen_ids: set[str] = set()

    for json_file in sorted(raw_path.glob("*_recalls.json")):
        with open(json_file) as f:
            data = json.load(f)

        for item in data.get("results", []):
            nhtsa_id = item.get("NHTSACampaignNumber", "")
            if not nhtsa_id or nhtsa_id in seen_ids:
                continue
            seen_ids.add(nhtsa_id)

            component = item.get("Component", "")
            summary = item.get("Summary", "")
            consequence = item.get("Consequence", "")
            remedy = item.get("Remedy", "")

            content_parts = [
                f"NHTSA Recall {nhtsa_id}",
                f"Component: {component}",
                f"Summary: {summary}",
            ]
            if consequence:
                content_parts.append(f"Consequence: {consequence}")
            if remedy:
                content_parts.append(f"Remedy: {remedy}")

            docs.append({
                "source": "nhtsa",
                "source_id": f"recall_{nhtsa_id}",
                "title": f"NHTSA Recall {nhtsa_id}: {component}",
                "content": "\n".join(content_parts),
                "category": "tsb",
                "url": "",
                "date": item.get("ReportReceivedDate", ""),
                "quality_score": 1.0,
                "metadata": {
                    "vehicle_type": "fzj80",
                    "nhtsa_type": "recall",
                    "component": component,
                    "model_year": item.get("ModelYear", ""),
                },
            })

    return docs


def _quality_from_complaint(item: dict) -> float:
    """Score a complaint 0.0-1.0 based on severity indicators."""
    score = 0.3  # baseline
    if item.get("Crash", "N") == "Y":
        score += 0.3
    if item.get("Injury", "N") == "Y":
        score += 0.2
    if item.get("Fire", "N") == "Y":
        score += 0.2
    return min(round(score, 2), 1.0)


def _process_complaints(raw_path: Path) -> list[dict]:
    """Process complaint JSON files into JSONL documents."""
    docs: list[dict] = []
    seen_ids: set[str] = set()

    for json_file in sorted(raw_path.glob("*_complaints.json")):
        with open(json_file) as f:
            data = json.load(f)

        for item in data.get("results", []):
            odi_number = str(item.get("odiNumber", ""))
            if not odi_number or odi_number in seen_ids:
                continue
            seen_ids.add(odi_number)

            component = item.get("components", "")
            summary = item.get("summary", "")
            category = _component_to_category(component)

            content_parts = [
                f"NHTSA Complaint {odi_number}",
                f"Component: {component}",
                f"Year: {item.get('modelYear', '')}",
                f"Summary: {summary}",
            ]

            crash = item.get("crash", "N")
            injury = item.get("injuries", "N")
            fire = item.get("fire", "N")
            if crash == "Y":
                content_parts.append("Crash reported: Yes")
            if injury == "Y":
                content_parts.append("Injury reported: Yes")
            if fire == "Y":
                content_parts.append("Fire reported: Yes")

            docs.append({
                "source": "nhtsa",
                "source_id": f"complaint_{odi_number}",
                "title": f"NHTSA Complaint: {component}",
                "content": "\n".join(content_parts),
                "category": category,
                "url": "",
                "date": item.get("dateComplaintFiled", ""),
                "quality_score": _quality_from_complaint(item),
                "metadata": {
                    "vehicle_type": "fzj80",
                    "nhtsa_type": "complaint",
                    "component": component,
                    "model_year": item.get("modelYear", ""),
                    "crash": crash,
                    "injury": injury,
                    "fire": fire,
                },
            })

    return docs


def process_nhtsa(
    raw_path: Path = Path("data/raw/nhtsa"),
    output_jsonl: Path | None = None,
) -> list[dict]:
    """Process all raw NHTSA data into normalized documents.

    Returns the list of documents.  If *output_jsonl* is given, writes to that path.
    """
    recalls = _process_recalls(raw_path)
    complaints = _process_complaints(raw_path)
    all_docs = recalls + complaints

    logger.info("NHTSA: %d recalls, %d complaints", len(recalls), len(complaints))

    if output_jsonl:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with open(output_jsonl, "w") as f:
            for doc in all_docs:
                f.write(json.dumps(doc) + "\n")
        logger.info("Wrote %d documents to %s", len(all_docs), output_jsonl)

    return all_docs


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Normalize NHTSA data into JSONL for RigSherpa KB")
    parser.add_argument("--input", type=Path, default=Path("data/raw/nhtsa"), help="Raw NHTSA data directory")
    parser.add_argument("--output", type=Path, default=None, help="Output JSONL path")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    output = args.output or project_root / "data" / "fzj80_nhtsa.jsonl"

    docs = process_nhtsa(args.input, output)
    print(f"Processed {len(docs)} NHTSA documents -> {output}")

    cats: dict[str, int] = {}
    for d in docs:
        cats[d["category"]] = cats.get(d["category"], 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
