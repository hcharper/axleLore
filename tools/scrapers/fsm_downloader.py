"""FSM PDF download helper for AxleLore.

Downloads the FZJ80 Factory Service Manual PDF from Google Drive using
gdown, then invokes the existing FSM processor to generate JSONL.

Usage:
    python -m tools.scrapers.fsm_downloader
    python -m tools.scrapers.fsm_downloader --skip-process   # download only
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Google Drive file ID extracted from sharing URL
GDRIVE_FILE_ID = "1j5JLgWUA0VZXCxdB7lPE25PnK6lN6mn_"
GDRIVE_URL = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}"

DEFAULT_OUTPUT_DIR = Path("data/raw/fsm")
DEFAULT_PDF_NAME = "fzj80_fsm_1996.pdf"


def download_fsm(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    pdf_name: str = DEFAULT_PDF_NAME,
) -> Path:
    """Download the FSM PDF from Google Drive.

    Returns the path to the downloaded PDF.
    """
    try:
        import gdown
    except ImportError:
        logger.error("gdown is required.  Install with: pip install 'gdown>=5.0.0'")
        raise

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / pdf_name

    if pdf_path.exists():
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        logger.info("FSM PDF already exists: %s (%.1f MB)", pdf_path, size_mb)
        return pdf_path

    logger.info("Downloading FSM PDF from Google Drive ...")
    gdown.download(GDRIVE_URL, str(pdf_path), quiet=False)

    if pdf_path.exists():
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        logger.info("Downloaded: %s (%.1f MB)", pdf_path, size_mb)
    else:
        logger.error("Download failed — file not found at %s", pdf_path)

    return pdf_path


def download_and_process(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    jsonl_path: Path | None = None,
) -> Path | None:
    """Download the FSM PDF and run the processor.

    Returns the JSONL output path, or None on failure.
    """
    pdf_path = download_fsm(output_dir)
    if not pdf_path.exists():
        return None

    from tools.processors.fsm import process_pdf

    project_root = Path(__file__).resolve().parent.parent.parent
    jsonl = jsonl_path or project_root / "data" / "fzj80_fsm.jsonl"

    docs = process_pdf(pdf_path, vehicle_type="fzj80", output_jsonl=jsonl)
    logger.info("FSM processor produced %d documents -> %s", len(docs), jsonl)
    return jsonl


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Download FZJ80 FSM PDF and process to JSONL")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="PDF save directory")
    parser.add_argument("--skip-process", action="store_true", help="Download only, skip JSONL processing")
    parser.add_argument("--jsonl", type=Path, default=None, help="Output JSONL path")
    args = parser.parse_args()

    if args.skip_process:
        path = download_fsm(args.output_dir)
        print(f"FSM PDF: {path}")
    else:
        jsonl = download_and_process(args.output_dir, args.jsonl)
        if jsonl:
            print(f"FSM processing complete -> {jsonl}")
        else:
            print("FSM download/processing failed.")


if __name__ == "__main__":
    main()
