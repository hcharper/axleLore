"""Forum post normalizer for RigSherpa.

Normalizes scraped IH8MUD (and other forum) JSON data into
builder-compatible JSONL.  Filters by quality score, deduplicates,
and maps to the correct ChromaDB collection categories.

Input format (one JSON object per file, or a JSON array):
    {
        "thread_id": "123456",
        "title": "Head gasket replacement tips",
        "url": "https://forum.ih8mud.com/threads/...",
        "author": "username",
        "date": "2023-01-15",
        "category": "80-Series Tech",
        "posts": [
            {
                "author": "user1",
                "date": "2023-01-15",
                "content": "...",
                "votes": 12,
                "is_op": true
            },
            ...
        ],
        "views": 5000,
        "replies": 25,
        "tags": ["head gasket", "1fz-fe"]
    }

Usage:
    python -m tools.processors.forum /path/to/scraped_data/ -o data/forum_output.jsonl
    python -m tools.processors.forum thread.json --min-score 0.3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------

# Maps IH8MUD forum section names → ChromaDB categories
_FORUM_SECTION_MAP: dict[str, str] = {
    "80-series tech": "forum_troubleshoot",
    "80 series tech": "forum_troubleshoot",
    "newbie tech": "forum_troubleshoot",
    "general tech": "forum_troubleshoot",
    "80-series build threads": "forum_mods",
    "80 series build threads": "forum_mods",
    "build threads": "forum_mods",
    "modifications": "forum_mods",
    "mods": "forum_mods",
    "maintenance": "forum_maintenance",
    "vendors": "parts",
    "for sale": "parts",
    "parts": "parts",
    "classifieds": "parts",
}

# Keyword-based category detection for unmapped sections
_KEYWORD_CATEGORIES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"install|mod|lift|build|upgrade|swap", re.I), "forum_mods"),
    (re.compile(r"oil\s*change|maintain|service|filter|flush", re.I), "forum_maintenance"),
    (re.compile(r"part\s*number|for\s*sale|buy|price|vendor|order", re.I), "parts"),
    (re.compile(r"fix|problem|issue|help|trouble|broken|leak|noise", re.I), "forum_troubleshoot"),
    (re.compile(r"wiring|fuse|relay|ecu|sensor|electrical", re.I), "forum_troubleshoot"),
]


def map_category(forum_section: str, title: str = "") -> str:
    """Map a forum section name to a ChromaDB collection category."""
    key = forum_section.strip().lower()
    if key in _FORUM_SECTION_MAP:
        return _FORUM_SECTION_MAP[key]

    # Try keyword detection from title
    for pattern, cat in _KEYWORD_CATEGORIES:
        if pattern.search(title):
            return cat

    return "forum_troubleshoot"  # default


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

def compute_quality_score(thread: dict) -> float:
    """Compute a 0.0–1.0 quality score for a forum thread.

    Factors:
    - Number of replies (engagement)
    - Total votes across posts (peer validation)
    - Views (popularity)
    - Content length (substance)
    - Has accepted/high-vote answers
    """
    replies = thread.get("replies", len(thread.get("posts", [])) - 1)
    views = thread.get("views", 0)
    posts = thread.get("posts", [])

    total_votes = sum(p.get("votes", 0) for p in posts)
    max_votes = max((p.get("votes", 0) for p in posts), default=0)
    total_content = sum(len(p.get("content", "")) for p in posts)

    # Normalize each factor to 0–1
    reply_score = min(replies / 20.0, 1.0) if replies else 0
    view_score = min(views / 10000.0, 1.0) if views else 0
    vote_score = min(total_votes / 50.0, 1.0)
    max_vote_score = min(max_votes / 20.0, 1.0)
    content_score = min(total_content / 3000.0, 1.0)

    # Weighted combination
    score = (
        reply_score * 0.20
        + view_score * 0.15
        + vote_score * 0.20
        + max_vote_score * 0.20
        + content_score * 0.25
    )
    return round(min(score, 1.0), 3)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _clean_post_content(content: str) -> str:
    """Clean up raw forum post content."""
    # Remove excessive quoting
    content = re.sub(r"(?:^>.*\n?)+", "", content, flags=re.MULTILINE)
    # Remove common forum artifacts
    content = re.sub(r"\[/?(?:quote|img|url|b|i|u|code|size|color|font)[^\]]*\]", "", content, flags=re.I)
    # Collapse whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r" {2,}", " ", content)
    return content.strip()


def normalize_thread(thread: dict, min_post_length: int = 50) -> dict | None:
    """Normalize a single forum thread into a builder-compatible document.

    Returns None if the thread doesn't meet quality thresholds.
    """
    title = thread.get("title", "").strip()
    posts = thread.get("posts", [])

    if not title or not posts:
        return None

    # Extract OP (original post)
    op_posts = [p for p in posts if p.get("is_op", False)]
    op = op_posts[0] if op_posts else posts[0]
    op_content = _clean_post_content(op.get("content", ""))

    if len(op_content) < min_post_length:
        return None

    # Build the combined content: question + best responses
    response_posts = [p for p in posts if p != op and len(_clean_post_content(p.get("content", ""))) >= min_post_length]

    # Sort by votes (best answers first)
    response_posts.sort(key=lambda p: p.get("votes", 0), reverse=True)

    # Take top responses (limit to keep chunk size reasonable)
    top_responses = response_posts[:5]

    content_parts = [f"Question: {title}\n\n{op_content}"]
    for resp in top_responses:
        cleaned = _clean_post_content(resp.get("content", ""))
        votes = resp.get("votes", 0)
        author = resp.get("author", "anonymous")
        content_parts.append(f"Response (by {author}, {votes} votes):\n{cleaned}")

    content = "\n\n".join(content_parts)
    category = map_category(thread.get("category", ""), title)
    quality = compute_quality_score(thread)

    return {
        "source": "ih8mud",
        "source_id": str(thread.get("thread_id", "")),
        "title": title,
        "content": content,
        "category": category,
        "url": thread.get("url", ""),
        "date": thread.get("date"),
        "quality_score": quality,
        "metadata": {
            "vehicle_type": "fzj80",
            "forum_section": thread.get("category", ""),
            "replies": thread.get("replies", 0),
            "views": thread.get("views", 0),
            "author": thread.get("author", ""),
        },
    }


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(documents: list[dict]) -> list[dict]:
    """Remove near-duplicate documents based on content similarity."""
    seen: set[str] = set()
    unique: list[dict] = []

    for doc in documents:
        # Use first 200 chars + title as fingerprint
        fingerprint = hashlib.md5(
            (doc.get("title", "") + doc.get("content", "")[:200]).encode()
        ).hexdigest()

        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(doc)

    removed = len(documents) - len(unique)
    if removed:
        logger.info("Deduplicated: removed %d duplicates", removed)
    return unique


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_forum_file(
    input_path: Path,
    min_quality: float = 0.1,
) -> list[dict]:
    """Process a single forum JSON file into normalized documents."""
    with open(input_path) as f:
        data = json.load(f)

    # Handle both single thread and array of threads
    threads = data if isinstance(data, list) else [data]

    documents: list[dict] = []
    for thread in threads:
        doc = normalize_thread(thread)
        if doc is None:
            continue
        if doc["quality_score"] < min_quality:
            logger.debug("Skipping low-quality thread: %s (%.2f)", doc["title"][:50], doc["quality_score"])
            continue
        documents.append(doc)

    return documents


def process_forum_directory(
    input_dir: Path,
    output_jsonl: Path,
    min_quality: float = 0.1,
) -> list[dict]:
    """Process all forum JSON files in a directory."""
    all_docs: list[dict] = []

    for json_path in sorted(input_dir.glob("**/*.json")):
        try:
            docs = process_forum_file(json_path, min_quality)
            all_docs.extend(docs)
            logger.info("  %s: %d documents", json_path.name, len(docs))
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Skipping %s: %s", json_path.name, exc)

    # Deduplicate
    all_docs = deduplicate(all_docs)

    # Sort by quality (best first)
    all_docs.sort(key=lambda d: d.get("quality_score", 0), reverse=True)

    # Write output
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with open(output_jsonl, "w") as f:
        for doc in all_docs:
            f.write(json.dumps(doc) + "\n")

    logger.info("Wrote %d documents to %s", len(all_docs), output_jsonl)
    return all_docs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Normalize forum data into JSONL for RigSherpa KB")
    parser.add_argument("input", type=Path, help="JSON file or directory of scraped forum data")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output JSONL path")
    parser.add_argument("--min-score", type=float, default=0.1, help="Minimum quality score (0.0-1.0)")
    parser.add_argument("--vehicle", default="fzj80", help="Vehicle type code")
    args = parser.parse_args()

    if not args.input.exists():
        logger.error("Input not found: %s", args.input)
        return

    project_root = Path(__file__).resolve().parent.parent.parent
    output = args.output or project_root / "data" / f"{args.vehicle}_forum.jsonl"

    if args.input.is_dir():
        docs = process_forum_directory(args.input, output, args.min_score)
    else:
        docs = process_forum_file(args.input, args.min_score)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            for doc in docs:
                f.write(json.dumps(doc) + "\n")

    print(f"Processed {len(docs)} documents -> {output}")

    # Category summary
    cats: dict[str, int] = {}
    for d in docs:
        cats[d["category"]] = cats.get(d["category"], 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")

    # Quality distribution
    if docs:
        scores = [d["quality_score"] for d in docs]
        print(f"\nQuality: min={min(scores):.2f} avg={sum(scores)/len(scores):.2f} max={max(scores):.2f}")


if __name__ == "__main__":
    main()
