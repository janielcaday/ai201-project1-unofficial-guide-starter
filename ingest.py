#!/usr/bin/env python3
"""
ingest.py — Document ingestion and chunking pipeline.

Loads all .md files from documents/, strips markdown formatting, and produces
chunks of ~1000 chars with 200-char overlap using recursive splitting.

Outputs:
  - chunks.json   : list of {text, source, chunk_id} dicts
  - Console       : summary stats + 5 random chunks for inspection

Usage:
    python ingest.py
"""

import json
import random
import re
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

DOCUMENTS_DIR = Path(__file__).parent / "documents"
OUTPUT_FILE = Path(__file__).parent / "chunks.json"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MIN_CHUNK_SIZE = 100  # drop fragments shorter than this

# Separators tried in order: section breaks → paragraphs → sentences → words → chars
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


# ── Cleaning ──────────────────────────────────────────────────────────────────

def clean_markdown(text: str) -> str:
    """Remove markdown formatting; keep substantive text."""
    # Horizontal rules
    text = re.sub(r"^-{3,}\s*$", "", text, flags=re.MULTILINE)
    # Heading markers — strip ##+ but keep the heading text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Bold / italic
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text, flags=re.DOTALL)
    # Markdown links → keep link text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Blockquote markers
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # Collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def _split_by_separator(text: str, sep: str) -> list[str]:
    """Split and strip, drop empties."""
    parts = text.split(sep) if sep else list(text)
    return [p.strip() for p in parts if p.strip()]


def _merge_splits(parts: list[str], sep: str, chunk_size: int) -> list[str]:
    """
    Greedily merge adjacent parts into chunks up to chunk_size.
    Any part that already exceeds chunk_size is returned as-is for further splitting.
    """
    chunks: list[str] = []
    current = ""

    for part in parts:
        joiner = sep if (sep and current) else ""
        candidate = current + joiner + part

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # Part itself may still be too large — caller will recurse
            current = part

    if current:
        chunks.append(current)

    return chunks


def split_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """
    Recursively split text into pieces each <= chunk_size chars.
    Tries SEPARATORS in order; falls back to hard char split.
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    for sep in SEPARATORS:
        if sep and sep not in text:
            continue

        parts = _split_by_separator(text, sep)
        if len(parts) == 1:
            continue  # This separator didn't actually split anything useful

        merged = _merge_splits(parts, sep, chunk_size)
        result: list[str] = []
        for chunk in merged:
            if len(chunk) > chunk_size:
                result.extend(split_text(chunk, chunk_size))
            else:
                result.append(chunk)
        return [r for r in result if r.strip()]

    # Hard split as last resort
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size) if text[i : i + chunk_size].strip()]


def add_overlap(chunks: list[str], overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Prepend the tail of the previous chunk to each chunk (word-boundary aligned).
    Ensures facts split across a boundary are present in at least one full chunk.
    """
    if len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        tail = chunks[i - 1][-overlap:]
        # Align to word boundary
        space = tail.find(" ")
        if 0 < space < len(tail) - 1:
            tail = tail[space + 1 :]
        result.append(tail + " " + chunks[i])

    return result


def chunk_document(text: str, source: str) -> list[dict]:
    """Clean, split, overlap, and annotate a single document."""
    cleaned = clean_markdown(text)
    raw_chunks = split_text(cleaned, CHUNK_SIZE)
    overlapped = add_overlap(raw_chunks, CHUNK_OVERLAP)
    return [
        {"text": chunk, "source": source, "chunk_id": idx}
        for idx, chunk in enumerate(overlapped)
        if len(chunk.strip()) >= MIN_CHUNK_SIZE
    ]


# ── Loading ───────────────────────────────────────────────────────────────────

def load_all_documents(docs_dir: Path) -> list[dict]:
    """Load every .md file in docs_dir and return a flat list of chunks."""
    md_files = sorted(docs_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No .md files found in {docs_dir}")

    all_chunks: list[dict] = []
    for path in md_files:
        raw = path.read_text(encoding="utf-8")
        chunks = chunk_document(raw, source=path.name)
        print(f"  {path.name}: {len(raw):,} chars → {len(chunks)} chunks")
        all_chunks.extend(chunks)

    return all_chunks


# ── Inspection ────────────────────────────────────────────────────────────────

def inspect_chunks(chunks: list[dict], n: int = 5) -> None:
    """Print n random chunks for manual review."""
    sample = random.sample(chunks, min(n, len(chunks)))
    print(f"\n{'='*70}")
    print(f"RANDOM CHUNK SAMPLE (n={len(sample)})")
    print(f"{'='*70}")
    for i, chunk in enumerate(sample, 1):
        text = chunk["text"]
        print(f"\n-- Chunk {i} | source={chunk['source']} | id={chunk['chunk_id']} | {len(text)} chars")
        print(text)
        print()

    lengths = [len(c["text"]) for c in chunks]
    print(f"{'='*70}")
    print(f"STATS: {len(chunks)} total chunks")
    print(f"  min={min(lengths)}  max={max(lengths)}  avg={sum(lengths)//len(lengths)} chars")
    print(f"  target range: 200-{CHUNK_SIZE} chars")
    outliers_small = sum(1 for l in lengths if l < 200)
    max_allowed = CHUNK_SIZE + CHUNK_OVERLAP
    outliers_large = sum(1 for l in lengths if l > max_allowed)
    if outliers_small:
        print(f"  WARNING: {outliers_small} chunk(s) under 200 chars -- may be too small")
    if outliers_large:
        print(f"  WARNING: {outliers_large} chunk(s) over {max_allowed} chars (chunk_size + overlap) -- splitter may need tuning")
    print(f"{'='*70}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> list[dict]:
    print(f"Loading documents from {DOCUMENTS_DIR}/")
    chunks = load_all_documents(DOCUMENTS_DIR)

    OUTPUT_FILE.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {len(chunks)} chunks -> {OUTPUT_FILE}")

    inspect_chunks(chunks, n=5)
    return chunks


if __name__ == "__main__":
    main()
