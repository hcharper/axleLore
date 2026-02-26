"""YAML-to-ChromaDB seeder for RigSherpa.

Extracts structured data from vehicle YAML configs (specs, torque values,
fluid capacities, part numbers, common issues, mods) into ChromaDB chunks.
This provides immediate RAG value without any PDFs or forum scrapes.

Usage:
    python -m tools.processors.yaml_seeder                     # seed default vehicle
    python -m tools.processors.yaml_seeder --vehicle fzj80     # explicit vehicle
    python -m tools.processors.yaml_seeder --dry-run            # preview JSONL only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Iterator

import yaml

logger = logging.getLogger(__name__)

# Category mapping: YAML section → ChromaDB collection
_SECTION_CATEGORY = {
    "engine": "engine",
    "transmission": "drivetrain",
    "transfer_case": "drivetrain",
    "axles": "drivetrain",
    "brakes": "chassis",
    "suspension": "chassis",
    "steering": "chassis",
    "electrical": "electrical",
    "dimensions": "general",
    "weights": "general",
    "capacities": "general",
    "tires": "chassis",
    "common_issues": "forum_troubleshoot",
    "modifications": "forum_mods",
}


def _chunk_id(text: str, prefix: str) -> str:
    h = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"yaml_{prefix}_{h}"


def _fmt_value(v) -> str:
    if isinstance(v, list):
        return ", ".join(str(i) for i in v)
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_fmt_value(val)}" for k, val in v.items())
    return str(v)


def _flatten_dict(d: dict, parent_key: str = "", sep: str = " > ") -> list[tuple[str, str]]:
    """Flatten nested dicts into (label, value) pairs."""
    items: list[tuple[str, str]] = []
    for k, v in d.items():
        label = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, label, sep))
        else:
            items.append((label, _fmt_value(v)))
    return items


# ---------------------------------------------------------------------------
# Chunk generators — one per major YAML section
# ---------------------------------------------------------------------------


def _seed_engine(data: dict, vehicle_name: str) -> Iterator[dict]:
    """Generate chunks from the engine section."""
    engine = data.get("engine", {})
    if not engine:
        return

    # Core specs chunk
    code = engine.get("code", "")
    lines = [
        f"{vehicle_name} Engine Specifications ({code})",
        f"Type: {engine.get('type', '')}",
        f"Displacement: {engine.get('displacement_l', '')}L ({engine.get('displacement_cc', '')}cc)",
        f"Fuel system: {engine.get('fuel_system', '')}",
        f"Horsepower: {engine.get('horsepower', '')} hp",
        f"Torque: {engine.get('torque_lb_ft', '')} lb-ft",
        f"Compression ratio: {engine.get('compression_ratio', '')}",
        f"Firing order: {engine.get('firing_order', '')}",
        f"Bore: {engine.get('bore_mm', '')} mm, Stroke: {engine.get('stroke_mm', '')} mm",
    ]
    text = "\n".join(lines)
    yield {
        "source": "yaml",
        "source_id": "engine_specs",
        "title": f"{code} Engine Specifications",
        "content": text,
        "category": "engine",
    }

    # Fluids
    fluids = engine.get("fluids", {})
    for fluid_name, fluid_data in fluids.items():
        flat = _flatten_dict(fluid_data)
        lines = [f"{vehicle_name} Engine {fluid_name.title()} Specifications"]
        for label, value in flat:
            nice_label = label.replace("_", " ").title()
            lines.append(f"{nice_label}: {value}")
        text = "\n".join(lines)
        yield {
            "source": "yaml",
            "source_id": f"engine_fluid_{fluid_name}",
            "title": f"Engine {fluid_name.title()} Specs",
            "content": text,
            "category": "engine",
        }

    # Maintenance schedules
    maint = engine.get("maintenance", {})
    for item_name, item_data in maint.items():
        lines = [f"{vehicle_name} Maintenance: {item_name.replace('_', ' ').title()}"]
        for k, v in item_data.items():
            nice = k.replace("_", " ").title()
            lines.append(f"{nice}: {_fmt_value(v)}")
        text = "\n".join(lines)
        yield {
            "source": "yaml",
            "source_id": f"engine_maint_{item_name}",
            "title": f"Maintenance Schedule: {item_name.replace('_', ' ').title()}",
            "content": text,
            "category": "engine",
        }


def _seed_transmission(data: dict, vehicle_name: str) -> Iterator[dict]:
    trans = data.get("transmission", {})
    if not trans:
        return

    for trans_type in ("automatic", "manual"):
        td = trans.get(trans_type, {})
        if not td:
            continue
        code = td.get("code", trans_type)
        lines = [f"{vehicle_name} {trans_type.title()} Transmission ({code})"]
        for k, v in td.items():
            if k == "gears":
                lines.append("Gear Ratios:")
                for gear, ratio in v.items():
                    lines.append(f"  {gear.title()}: {ratio}")
            else:
                lines.append(f"{k.replace('_', ' ').title()}: {_fmt_value(v)}")
        text = "\n".join(lines)
        yield {
            "source": "yaml",
            "source_id": f"trans_{trans_type}",
            "title": f"{code} {trans_type.title()} Transmission",
            "content": text,
            "category": "drivetrain",
        }


def _seed_transfer_case(data: dict, vehicle_name: str) -> Iterator[dict]:
    tc = data.get("transfer_case", {})
    if not tc:
        return
    code = tc.get("code", "")
    lines = [f"{vehicle_name} Transfer Case ({code})"]
    for k, v in tc.items():
        if k == "ratios":
            lines.append("Ratios:")
            for gear, ratio in v.items():
                lines.append(f"  {gear.title()}: {ratio}")
        else:
            lines.append(f"{k.replace('_', ' ').title()}: {_fmt_value(v)}")
    text = "\n".join(lines)
    yield {
        "source": "yaml",
        "source_id": "transfer_case",
        "title": f"{code} Transfer Case",
        "content": text,
        "category": "drivetrain",
    }


def _seed_axles(data: dict, vehicle_name: str) -> Iterator[dict]:
    axles = data.get("axles", {})
    for position in ("front", "rear"):
        axle = axles.get(position, {})
        if not axle:
            continue
        lines = [f"{vehicle_name} {position.title()} Axle"]
        for k, v in axle.items():
            lines.append(f"{k.replace('_', ' ').title()}: {_fmt_value(v)}")
        text = "\n".join(lines)
        yield {
            "source": "yaml",
            "source_id": f"axle_{position}",
            "title": f"{position.title()} Axle Specifications",
            "content": text,
            "category": "drivetrain",
        }


def _seed_brakes(data: dict, vehicle_name: str) -> Iterator[dict]:
    brakes = data.get("brakes", {})
    if not brakes:
        return

    for section in ("front", "rear"):
        bd = brakes.get(section, {})
        if not bd:
            continue
        lines = [f"{vehicle_name} {section.title()} Brakes"]
        for k, v in bd.items():
            lines.append(f"{k.replace('_', ' ').title()}: {_fmt_value(v)}")
        text = "\n".join(lines)
        yield {
            "source": "yaml",
            "source_id": f"brakes_{section}",
            "title": f"{section.title()} Brake Specifications",
            "content": text,
            "category": "chassis",
        }

    # Brake fluid, ABS, parking brake
    extra_lines = [f"{vehicle_name} Brake System Info"]
    if "abs" in brakes:
        extra_lines.append(f"ABS: {'Yes' if brakes['abs'] else 'No'}")
    if "abs_module" in brakes:
        extra_lines.append(f"ABS Module: {brakes['abs_module']}")
    fluid = brakes.get("fluid", {})
    for k, v in fluid.items():
        extra_lines.append(f"Brake Fluid {k.replace('_', ' ').title()}: {v}")
    pb = brakes.get("parking_brake", {})
    for k, v in pb.items():
        extra_lines.append(f"Parking Brake {k.replace('_', ' ').title()}: {v}")
    if len(extra_lines) > 1:
        yield {
            "source": "yaml",
            "source_id": "brakes_system",
            "title": "Brake System Overview",
            "content": "\n".join(extra_lines),
            "category": "chassis",
        }


def _seed_suspension(data: dict, vehicle_name: str) -> Iterator[dict]:
    susp = data.get("suspension", {})
    if not susp:
        return
    for section in ("front", "rear"):
        sd = susp.get(section, {})
        if not sd:
            continue
        lines = [f"{vehicle_name} {section.title()} Suspension"]
        for k, v in sd.items():
            lines.append(f"{k.replace('_', ' ').title()}: {_fmt_value(v)}")
        text = "\n".join(lines)
        yield {
            "source": "yaml",
            "source_id": f"suspension_{section}",
            "title": f"{section.title()} Suspension",
            "content": text,
            "category": "chassis",
        }

    sway = susp.get("sway_bars", {})
    if sway:
        lines = [f"{vehicle_name} Sway Bars"]
        for k, v in sway.items():
            lines.append(f"{k.replace('_', ' ').title()}: {_fmt_value(v)}")
        yield {
            "source": "yaml",
            "source_id": "sway_bars",
            "title": "Sway Bars",
            "content": "\n".join(lines),
            "category": "chassis",
        }


def _seed_steering(data: dict, vehicle_name: str) -> Iterator[dict]:
    steer = data.get("steering", {})
    if not steer:
        return
    lines = [f"{vehicle_name} Steering"]
    for k, v in steer.items():
        lines.append(f"{k.replace('_', ' ').title()}: {_fmt_value(v)}")
    yield {
        "source": "yaml",
        "source_id": "steering",
        "title": "Steering Specifications",
        "content": "\n".join(lines),
        "category": "chassis",
    }


def _seed_electrical(data: dict, vehicle_name: str) -> Iterator[dict]:
    elec = data.get("electrical", {})
    if not elec:
        return
    for section_name, section_data in elec.items():
        if not isinstance(section_data, dict):
            continue
        lines = [f"{vehicle_name} Electrical: {section_name.replace('_', ' ').title()}"]
        for k, v in section_data.items():
            lines.append(f"{k.replace('_', ' ').title()}: {_fmt_value(v)}")
        yield {
            "source": "yaml",
            "source_id": f"electrical_{section_name}",
            "title": f"Electrical: {section_name.replace('_', ' ').title()}",
            "content": "\n".join(lines),
            "category": "electrical",
        }


def _seed_dimensions_weights(data: dict, vehicle_name: str) -> Iterator[dict]:
    dims = data.get("dimensions", {})
    weights = data.get("weights", {})
    caps = data.get("capacities", {})

    if dims or weights or caps:
        lines = [f"{vehicle_name} Dimensions, Weights & Capacities"]
        if dims:
            lines.append("\nDimensions:")
            for k, v in dims.items():
                lines.append(f"  {k.replace('_', ' ').title()}: {v}")
        if weights:
            lines.append("\nWeights:")
            for k, v in weights.items():
                lines.append(f"  {k.replace('_', ' ').title()}: {v}")
        if caps:
            lines.append("\nCapacities:")
            for k, v in caps.items():
                lines.append(f"  {k.replace('_', ' ').title()}: {v}")
        yield {
            "source": "yaml",
            "source_id": "dims_weights_caps",
            "title": "Dimensions, Weights & Capacities",
            "content": "\n".join(lines),
            "category": "general",
        }


def _seed_tires(data: dict, vehicle_name: str) -> Iterator[dict]:
    tires = data.get("tires", {})
    if not tires:
        return
    lines = [f"{vehicle_name} Tire Specifications"]
    lines.append(f"OEM Size: {tires.get('oem_size', 'N/A')}")
    lines.append(f"Rotation Interval: {tires.get('rotation_interval_miles', 'N/A')} miles")
    lines.append(f"Front Pressure: {tires.get('pressure_front_psi', 'N/A')} psi")
    lines.append(f"Rear Pressure: {tires.get('pressure_rear_psi', 'N/A')} psi")
    lines.append(f"Spare Location: {tires.get('spare_location', 'N/A')}")

    alts = tires.get("alternatives", [])
    if alts:
        lines.append("\nAlternative Tire Sizes:")
        for alt in alts:
            lines.append(f"  {alt.get('size', '?')}: {alt.get('notes', '')}")

    yield {
        "source": "yaml",
        "source_id": "tires",
        "title": "Tire Specifications & Alternatives",
        "content": "\n".join(lines),
        "category": "chassis",
    }


def _seed_common_issues(data: dict, vehicle_name: str) -> Iterator[dict]:
    issues = data.get("common_issues", [])
    for issue in issues:
        code = issue.get("code", "UNKNOWN")
        lines = [f"{vehicle_name} Common Issue: {issue.get('description', code)}"]
        lines.append(f"Severity: {issue.get('severity', 'unknown')}")
        if "affected_years" in issue:
            lines.append(f"Affected Years: {_fmt_value(issue['affected_years'])}")
        if "typical_cost_range" in issue:
            r = issue["typical_cost_range"]
            lines.append(f"Typical Cost: ${r[0]:,} - ${r[1]:,}")
        if "symptoms" in issue:
            lines.append("Symptoms:")
            for s in issue["symptoms"]:
                lines.append(f"  - {s}")
        if "causes" in issue:
            lines.append("Causes:")
            for c in issue["causes"]:
                lines.append(f"  - {c}")
        if "prevention" in issue:
            lines.append("Prevention:")
            for p in issue["prevention"]:
                lines.append(f"  - {p}")
        if "fix" in issue:
            lines.append(f"Fix: {issue['fix']}")

        yield {
            "source": "yaml",
            "source_id": f"issue_{code.lower()}",
            "title": f"Common Issue: {code.replace('_', ' ').title()}",
            "content": "\n".join(lines),
            "category": "forum_troubleshoot",
        }


def _seed_modifications(data: dict, vehicle_name: str) -> Iterator[dict]:
    mods = data.get("modifications", {})
    for group_name, mod_list in mods.items():
        if not isinstance(mod_list, list):
            continue
        for mod in mod_list:
            name = mod.get("name", "Unknown Mod")
            lines = [f"{vehicle_name} Modification: {name}"]
            lines.append(f"Category: {group_name.replace('_', ' ').title()}")
            if "description" in mod:
                lines.append(f"Description: {mod['description']}")
            if "lift_height" in mod:
                lines.append(f"Lift Height: {mod['lift_height']}")
            if "vendor" in mod:
                lines.append(f"Vendor: {mod['vendor']}")
            if "notes" in mod:
                lines.append(f"Notes: {mod['notes']}")
            if "part_numbers" in mod:
                lines.append("Part Numbers:")
                for pn_label, pn_val in mod["part_numbers"].items():
                    lines.append(f"  {pn_label.replace('_', ' ').title()}: {pn_val}")
            if "locations" in mod:
                lines.append(f"Locations: {_fmt_value(mod['locations'])}")
            if "install_difficulty" in mod:
                lines.append(f"Install Difficulty: {mod['install_difficulty']}")

            yield {
                "source": "yaml",
                "source_id": f"mod_{group_name}_{name.lower().replace(' ', '_')[:30]}",
                "title": f"Mod: {name}",
                "content": "\n".join(lines),
                "category": "forum_mods",
            }


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------


def seed_from_yaml(
    yaml_path: Path,
    output_jsonl: Path | None = None,
) -> list[dict]:
    """Parse a vehicle YAML and return a list of document dicts.

    Each dict has keys: source, source_id, title, content, category — ready
    for the knowledge-base builder's ``add_documents_from_file()``.

    If *output_jsonl* is given, documents are also written to that file.
    """
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    vehicle_name = data.get("name", data.get("vehicle_type", "Unknown"))

    generators = [
        _seed_engine,
        _seed_transmission,
        _seed_transfer_case,
        _seed_axles,
        _seed_brakes,
        _seed_suspension,
        _seed_steering,
        _seed_electrical,
        _seed_dimensions_weights,
        _seed_tires,
        _seed_common_issues,
        _seed_modifications,
    ]

    documents: list[dict] = []
    for gen in generators:
        for doc in gen(data, vehicle_name):
            documents.append(doc)

    if output_jsonl:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with open(output_jsonl, "w") as f:
            for doc in documents:
                f.write(json.dumps(doc) + "\n")
        logger.info("Wrote %d documents to %s", len(documents), output_jsonl)

    return documents


def seed_to_chromadb(
    yaml_path: Path,
    chromadb_dir: Path,
    vehicle_type: str | None = None,
) -> int:
    """Seed ChromaDB directly from a vehicle YAML config.

    Returns the number of chunks added.
    """
    from tools.kb_builder.builder import KnowledgeBaseBuilder, Chunk

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    vtype = vehicle_type or data.get("vehicle_type", "fzj80")

    builder = KnowledgeBaseBuilder(chromadb_dir)
    collections = builder.create_collections(vtype)

    documents = seed_from_yaml(yaml_path)
    total = 0

    for doc in documents:
        cat = doc["category"]
        if cat not in collections:
            logger.warning("Skipping unknown category: %s", cat)
            continue

        chunk = Chunk(
            id=_chunk_id(doc["content"], doc["source_id"]),
            text=doc["content"],
            source=doc["source"],
            source_id=doc["source_id"],
            category=cat,
            metadata={"title": doc.get("title", "")},
        )
        builder.add_chunks(collections[cat], [chunk])
        total += 1

    logger.info("Seeded %d chunks into ChromaDB for %s", total, vtype)
    return total


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Seed ChromaDB from vehicle YAML config")
    parser.add_argument("--vehicle", default="fzj80", help="Vehicle type code")
    parser.add_argument("--config-dir", default=None, help="Vehicle config directory")
    parser.add_argument("--chromadb-dir", default=None, help="ChromaDB persist directory")
    parser.add_argument("--dry-run", action="store_true", help="Write JSONL only, don't touch ChromaDB")
    parser.add_argument("--output", default=None, help="Output JSONL path (default: data/<vehicle>_yaml.jsonl)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    config_dir = Path(args.config_dir) if args.config_dir else project_root / "config" / "vehicles"
    chromadb_dir = Path(args.chromadb_dir) if args.chromadb_dir else project_root / "data" / "chromadb"
    yaml_path = config_dir / f"{args.vehicle}.yaml"

    if not yaml_path.exists():
        logger.error("YAML config not found: %s", yaml_path)
        return

    output = Path(args.output) if args.output else project_root / "data" / f"{args.vehicle}_yaml.jsonl"

    documents = seed_from_yaml(yaml_path, output_jsonl=output)
    print(f"Generated {len(documents)} documents from {yaml_path.name}")

    if not args.dry_run:
        count = seed_to_chromadb(yaml_path, chromadb_dir, args.vehicle)
        print(f"Seeded {count} chunks into ChromaDB")
    else:
        print(f"Dry run — JSONL written to {output}")


if __name__ == "__main__":
    main()
