"""Master pipeline orchestrator for AxleLore knowledge-base population.

Runs the full scrape → process → build → export pipeline, or individual stages.

Usage:
    python -m tools.orchestrate all                             # full pipeline
    python -m tools.orchestrate scrape                          # scraping only
    python -m tools.orchestrate process                         # processing only
    python -m tools.orchestrate build                           # ChromaDB loading only
    python -m tools.orchestrate status                          # progress + collection counts
    python -m tools.orchestrate scrape --source ih8mud --max-threads 500
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CHROMADB_DIR = DATA_DIR / "chromadb"
VEHICLE = "fzj80"


# ---------------------------------------------------------------------------
# Scrape stage
# ---------------------------------------------------------------------------

async def _scrape_yaml() -> None:
    """YAML seed — no network needed, just run the processor directly."""
    logger.info("[scrape] YAML seed (instant, no network)")
    from tools.processors.yaml_seeder import seed_from_yaml

    yaml_path = PROJECT_ROOT / "config" / "vehicles" / f"{VEHICLE}.yaml"
    output = DATA_DIR / f"{VEHICLE}_yaml.jsonl"

    if not yaml_path.exists():
        logger.warning("Vehicle YAML not found: %s", yaml_path)
        return

    docs = seed_from_yaml(yaml_path, output_jsonl=output)
    logger.info("  YAML seed: %d documents -> %s", len(docs), output)


async def _scrape_nhtsa() -> None:
    logger.info("[scrape] NHTSA API ...")
    from tools.scrapers.nhtsa import run_scraper
    await run_scraper()


async def _scrape_web() -> None:
    logger.info("[scrape] Web articles ...")
    from tools.scrapers.web_articles import run_scraper
    await run_scraper()


async def _scrape_fsm() -> None:
    logger.info("[scrape] FSM PDF download ...")
    from tools.scrapers.fsm_downloader import download_fsm
    download_fsm()


async def _scrape_sor(max_pages: int = 50) -> None:
    logger.info("[scrape] SOR parts catalog ...")
    from tools.scrapers.sor import run_scraper
    await run_scraper(max_pages=max_pages)


async def _scrape_ih8mud(max_threads: int | None = None, index_only: bool = False) -> None:
    logger.info("[scrape] IH8MUD forums ...")
    from tools.scrapers.ih8mud import run_scraper
    await run_scraper(max_threads=max_threads, index_only=index_only)


async def scrape_all(
    source: str | None = None,
    max_threads: int | None = None,
    index_only: bool = False,
) -> None:
    """Run all scrapers (or a single one if --source is given)."""
    if source:
        dispatch = {
            "yaml": _scrape_yaml,
            "nhtsa": lambda: _scrape_nhtsa(),
            "web": lambda: _scrape_web(),
            "fsm": lambda: _scrape_fsm(),
            "sor": lambda: _scrape_sor(),
            "ih8mud": lambda: _scrape_ih8mud(max_threads=max_threads, index_only=index_only),
        }
        fn = dispatch.get(source)
        if fn is None:
            logger.error("Unknown source: %s  (choices: %s)", source, ", ".join(dispatch))
            return
        await fn()
        return

    # Run in priority order: fast sources first, slow last
    await _scrape_yaml()

    # These can run concurrently (different network targets)
    await asyncio.gather(
        _scrape_nhtsa(),
        _scrape_web(),
        _scrape_fsm(),
        _scrape_sor(),
    )

    # IH8MUD is slowest — run last, resumable
    await _scrape_ih8mud(max_threads=max_threads, index_only=index_only)


# ---------------------------------------------------------------------------
# Process stage
# ---------------------------------------------------------------------------

def _process_nhtsa() -> int:
    from tools.processors.nhtsa import process_nhtsa

    raw = RAW_DIR / "nhtsa"
    output = DATA_DIR / f"{VEHICLE}_nhtsa.jsonl"
    if not raw.exists():
        logger.warning("No NHTSA raw data at %s — skipping", raw)
        return 0
    docs = process_nhtsa(raw, output)
    return len(docs)


def _process_web() -> int:
    from tools.processors.web_article import process_web_articles

    raw = RAW_DIR / "web"
    output = DATA_DIR / f"{VEHICLE}_web.jsonl"
    if not raw.exists():
        logger.warning("No web raw data at %s — skipping", raw)
        return 0
    docs = process_web_articles(raw, output)
    return len(docs)


def _process_fsm() -> int:
    from tools.processors.fsm import process_pdf

    pdf = RAW_DIR / "fsm" / "fzj80_fsm_1996.pdf"
    output = DATA_DIR / f"{VEHICLE}_fsm.jsonl"
    if not pdf.exists():
        logger.warning("No FSM PDF at %s — skipping", pdf)
        return 0
    docs = process_pdf(pdf, vehicle_type=VEHICLE, output_jsonl=output)
    return len(docs)


def _process_parts() -> int:
    from tools.processors.parts import process_parts

    raw = RAW_DIR / "sor"
    output = DATA_DIR / f"{VEHICLE}_parts.jsonl"
    if not raw.exists():
        logger.warning("No SOR raw data at %s — skipping", raw)
        return 0
    docs = process_parts(raw, output)
    return len(docs)


def _process_forum() -> int:
    from tools.processors.forum import process_forum_directory

    raw = RAW_DIR / "forum" / "threads"
    output = DATA_DIR / f"{VEHICLE}_forum.jsonl"
    if not raw.exists():
        logger.warning("No forum raw data at %s — skipping", raw)
        return 0
    docs = process_forum_directory(raw, output)
    return len(docs)


def process_all() -> dict[str, int]:
    """Run all processors and return doc counts."""
    results: dict[str, int] = {}

    # YAML seed is already JSONL from the scrape stage
    yaml_jsonl = DATA_DIR / f"{VEHICLE}_yaml.jsonl"
    if yaml_jsonl.exists():
        with open(yaml_jsonl) as f:
            results["yaml"] = sum(1 for _ in f)
    else:
        results["yaml"] = 0

    processors = [
        ("nhtsa", _process_nhtsa),
        ("web", _process_web),
        ("fsm", _process_fsm),
        ("parts", _process_parts),
        ("forum", _process_forum),
    ]

    for name, fn in processors:
        logger.info("[process] %s ...", name)
        try:
            results[name] = fn()
        except Exception as e:
            logger.error("  %s failed: %s", name, e)
            results[name] = 0

    return results


# ---------------------------------------------------------------------------
# Build stage
# ---------------------------------------------------------------------------

def build_all() -> dict[str, int]:
    """Load all JSONL files into ChromaDB."""
    from tools.kb_builder.builder import KnowledgeBaseBuilder

    builder = KnowledgeBaseBuilder(CHROMADB_DIR)
    results: dict[str, int] = {}

    jsonl_files = sorted(DATA_DIR.glob(f"{VEHICLE}_*.jsonl"))
    if not jsonl_files:
        logger.warning("No JSONL files found in %s", DATA_DIR)
        return results

    for jsonl_path in jsonl_files:
        name = jsonl_path.stem.replace(f"{VEHICLE}_", "")
        logger.info("[build] Loading %s ...", jsonl_path.name)
        try:
            count = builder.add_documents_from_file(VEHICLE, jsonl_path)
            results[name] = count
            logger.info("  %s: %d chunks", name, count)
        except Exception as e:
            logger.error("  %s failed: %s", name, e)
            results[name] = 0

    return results


def export_pack() -> Path | None:
    """Export the knowledge pack."""
    from tools.kb_builder.builder import KnowledgeBaseBuilder

    builder = KnowledgeBaseBuilder(CHROMADB_DIR)
    pack_dir = DATA_DIR / "knowledge_packs"
    pack_dir.mkdir(parents=True, exist_ok=True)
    output = pack_dir / f"{VEHICLE}_knowledge_pack.tar.gz"

    stats = builder.get_stats(VEHICLE)
    if stats["total_chunks"] == 0:
        logger.warning("ChromaDB is empty — nothing to export")
        return None

    builder.export(VEHICLE, output)
    return output


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def show_status() -> None:
    """Print pipeline status: raw data, JSONL counts, ChromaDB collections."""
    print(f"=== AxleLore KB Pipeline Status ({VEHICLE}) ===\n")

    # Raw data
    print("Raw data (data/raw/):")
    raw_sources = {
        "nhtsa": RAW_DIR / "nhtsa",
        "web": RAW_DIR / "web",
        "sor": RAW_DIR / "sor",
        "fsm": RAW_DIR / "fsm",
        "forum": RAW_DIR / "forum",
    }
    for name, path in raw_sources.items():
        if path.exists():
            files = list(path.glob("**/*"))
            file_count = sum(1 for f in files if f.is_file())
            print(f"  {name:20s}  {file_count} files")
        else:
            print(f"  {name:20s}  (not scraped)")

    # Scrape state
    state_db = RAW_DIR / "scrape_state.db"
    if state_db.exists():
        from tools.scrapers.state import ScrapeStateManager
        with ScrapeStateManager(state_db) as sm:
            stats = sm.get_stats()
            if stats:
                print("\nScrape state:")
                for name, info in stats.items():
                    print(f"  {name:30s}  page={info['last_page']:>5}  items={info['completed_items']:>6}  status={info['status']}")

    # JSONL files
    print("\nProcessed JSONL (data/):")
    for jsonl in sorted(DATA_DIR.glob(f"{VEHICLE}_*.jsonl")):
        with open(jsonl) as f:
            count = sum(1 for _ in f)
        size_kb = jsonl.stat().st_size / 1024
        print(f"  {jsonl.name:30s}  {count:>6} docs  ({size_kb:.1f} KB)")

    # ChromaDB
    print("\nChromaDB collections:")
    if CHROMADB_DIR.exists():
        try:
            from tools.kb_builder.builder import KnowledgeBaseBuilder
            builder = KnowledgeBaseBuilder(CHROMADB_DIR)
            stats = builder.get_stats(VEHICLE)
            for cat, count in sorted(stats["collections"].items()):
                marker = "  " if count > 0 else "!!"
                print(f"  {marker} {cat:25s}  {count:>6} chunks")
            print(f"\n  Total: {stats['total_chunks']} chunks")
        except Exception as e:
            print(f"  (error reading ChromaDB: {e})")
    else:
        print("  (not built yet)")

    # Knowledge pack
    pack = DATA_DIR / "knowledge_packs" / f"{VEHICLE}_knowledge_pack.tar.gz"
    if pack.exists():
        size_mb = pack.stat().st_size / (1024 * 1024)
        print(f"\nKnowledge pack: {pack} ({size_mb:.1f} MB)")
    else:
        print("\nKnowledge pack: (not exported yet)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="AxleLore KB pipeline orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  all       Run full pipeline: scrape -> process -> build -> export
  scrape    Run scrapers only
  process   Run processors only (raw -> JSONL)
  build     Load JSONL into ChromaDB
  export    Export knowledge pack
  status    Show pipeline progress
        """,
    )
    parser.add_argument("command", choices=["all", "scrape", "process", "build", "export", "status"])
    parser.add_argument("--source", type=str, default=None,
                        help="Scrape a single source (yaml, nhtsa, web, fsm, sor, ih8mud)")
    parser.add_argument("--max-threads", type=int, default=None,
                        help="Max IH8MUD threads to scrape")
    parser.add_argument("--index-only", action="store_true",
                        help="IH8MUD index pass only")
    args = parser.parse_args()

    t0 = time.time()

    if args.command == "status":
        show_status()
        return

    if args.command in ("all", "scrape"):
        await scrape_all(
            source=args.source,
            max_threads=args.max_threads,
            index_only=args.index_only,
        )

    if args.command in ("all", "process"):
        results = process_all()
        print("\nProcessing results:")
        for name, count in results.items():
            print(f"  {name}: {count} documents")

    if args.command in ("all", "build"):
        results = build_all()
        print("\nBuild results:")
        for name, count in results.items():
            print(f"  {name}: {count} chunks")

    if args.command in ("all", "export"):
        pack = export_pack()
        if pack:
            print(f"\nExported: {pack}")

    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s")


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
