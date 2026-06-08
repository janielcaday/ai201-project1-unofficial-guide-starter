#!/usr/bin/env python3
"""
pdf_to_md_txt.py
----------------
Convert a PDF to both a Markdown (.md) and plain text (.txt) file.

Markdown output uses font-size heuristics to detect headings:
  - Largest font sizes become #, ##, ###, etc.
  - Body text is written as plain paragraphs
  - Blank lines between blocks are preserved

Plain text output strips all formatting and writes clean prose.

Usage:
    python pdf_to_md_txt.py input.pdf
    python pdf_to_md_txt.py input.pdf --out-dir ./output
    python pdf_to_md_txt.py input.pdf --md-only
    python pdf_to_md_txt.py input.pdf --txt-only
    python pdf_to_md_txt.py input.pdf --h1 18 --h2 15 --h3 14

Dependencies:
    pip install pdfplumber
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:
    sys.exit("Missing dependency: pip install pdfplumber")


# ---------------------------------------------------------------------------
# Heading threshold detection
# ---------------------------------------------------------------------------

def detect_heading_thresholds(pdf, sample_pages: int = 10) -> list:
    """
    Inspect font sizes across the first N pages and return a sorted list
    of sizes that are likely headings (anything meaningfully above body text).

    Returns up to 4 heading levels, largest first.
    """
    sizes = []
    pages = list(pdf.pages)[:sample_pages]

    for page in pages:
        for char in page.chars:
            s = char.get("size")
            if s:
                sizes.append(round(s, 1))

    if not sizes:
        return []

    counts = Counter(sizes)
    # Body text = most common size
    body_size = counts.most_common(1)[0][0]

    # Collect sizes that are clearly larger than body text (> 10% bigger)
    # and appear at least a handful of times (avoids stray decorative chars)
    heading_sizes = sorted(
        {s for s, count in counts.items() if s > body_size * 1.08 and count >= 3},
        reverse=True,
    )

    # Cap at 4 heading levels
    return heading_sizes[:4]


# ---------------------------------------------------------------------------
# Line / block extraction
# ---------------------------------------------------------------------------

def extract_lines(page) -> list[dict]:
    """
    Group characters on a page into lines, preserving their dominant font size.
    Returns a list of {"text": str, "size": float} dicts.
    """
    if not page.chars:
        return []

    # Sort characters by vertical position (top), then horizontal (x0)
    chars = sorted(page.chars, key=lambda c: (round(c["top"], 1), c["x0"]))

    lines = []
    current_line_chars = []
    current_top = None
    TOLERANCE = 3  # points — chars within this vertical band are the same line

    for char in chars:
        top = round(char["top"], 1)
        if current_top is None or abs(top - current_top) <= TOLERANCE:
            current_top = top
            current_line_chars.append(char)
        else:
            if current_line_chars:
                lines.append(_chars_to_line(current_line_chars))
            current_line_chars = [char]
            current_top = top

    if current_line_chars:
        lines.append(_chars_to_line(current_line_chars))

    return lines


def _chars_to_line(chars: list) -> dict:
    """Convert a list of char dicts into a single line dict."""
    text = "".join(c.get("text", "") for c in chars).strip()
    sizes = [c["size"] for c in chars if c.get("size")]
    dominant_size = Counter(sizes).most_common(1)[0][0] if sizes else 0.0
    return {"text": text, "size": round(dominant_size, 1)}


# ---------------------------------------------------------------------------
# Markdown conversion
# ---------------------------------------------------------------------------

def line_to_markdown(line: dict, heading_thresholds: list) -> str:
    """
    Convert a single line to its Markdown representation.
    heading_thresholds is a list of font sizes (largest first) that map to
    #, ##, ###, #### respectively.
    """
    text = line["text"]
    size = line["size"]

    if not text:
        return ""

    for level, threshold in enumerate(heading_thresholds, start=1):
        if size >= threshold:
            prefix = "#" * level
            return f"{prefix} {text}"

    return text


def build_markdown(pages_lines: list, heading_thresholds: list) -> str:
    """
    Assemble all page lines into a full Markdown string.
    Collapses consecutive blank lines and adds paragraph spacing.
    """
    md_lines = []
    prev_was_blank = False

    for page_lines in pages_lines:
        for line in page_lines:
            md = line_to_markdown(line, heading_thresholds)

            if not md:
                if not prev_was_blank:
                    md_lines.append("")
                prev_was_blank = True
            else:
                md_lines.append(md)
                prev_was_blank = False

        # Page break → blank line between pages
        if not prev_was_blank:
            md_lines.append("")
            prev_was_blank = True

    return "\n".join(md_lines).strip()


# ---------------------------------------------------------------------------
# Plain text conversion
# ---------------------------------------------------------------------------

def build_plaintext(pages_lines: list) -> str:
    """
    Assemble all page lines into plain text.
    Merges short lines into paragraphs, preserves blank line separators.
    """
    txt_lines = []
    prev_was_blank = False

    for page_lines in pages_lines:
        for line in page_lines:
            text = line["text"]
            if not text:
                if not prev_was_blank:
                    txt_lines.append("")
                prev_was_blank = True
            else:
                txt_lines.append(text)
                prev_was_blank = False

        if not prev_was_blank:
            txt_lines.append("")
            prev_was_blank = True

    raw = "\n".join(txt_lines).strip()

    # Collapse 3+ consecutive blank lines down to 2
    raw = re.sub(r"\n{3,}", "\n\n", raw)

    return raw


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def convert(
    pdf_path: Path,
    out_dir: Path,
    write_md: bool = True,
    write_txt: bool = True,
    custom_thresholds: Optional[list] = None,
) -> dict[str, Path]:
    """
    Convert a PDF to .md and/or .txt.

    Returns a dict with keys "md" and/or "txt" pointing to output paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem
    outputs = {}

    print(f"Opening: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        print(f"  Pages: {len(pdf.pages)}")

        # Determine heading thresholds
        if custom_thresholds:
            thresholds = sorted(custom_thresholds, reverse=True)
            print(f"  Using custom heading thresholds: {thresholds}")
        else:
            thresholds = detect_heading_thresholds(pdf)
            print(f"  Auto-detected heading thresholds: {thresholds}")

        # Extract lines from every page
        print("  Extracting text...")
        pages_lines = []
        for i, page in enumerate(pdf.pages):
            lines = extract_lines(page)
            pages_lines.append(lines)
            if (i + 1) % 10 == 0:
                print(f"    ...processed {i + 1}/{len(pdf.pages)} pages")

    # Write Markdown
    if write_md:
        md_path = out_dir / f"{stem}.md"
        md_content = build_markdown(pages_lines, thresholds)
        md_path.write_text(md_content, encoding="utf-8")
        outputs["md"] = md_path
        print(f"  Wrote Markdown → {md_path}")

    # Write plain text
    if write_txt:
        txt_path = out_dir / f"{stem}.txt"
        txt_content = build_plaintext(pages_lines)
        txt_path.write_text(txt_content, encoding="utf-8")
        outputs["txt"] = txt_path
        print(f"  Wrote plain text → {txt_path}")

    print("Done.")
    return outputs


def main():
    parser = argparse.ArgumentParser(
        description="Convert a PDF to Markdown (.md) and/or plain text (.txt).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # Accept either a single file or a directory (but not both)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("pdf", nargs="?", help="Path to a single input PDF file")
    source.add_argument(
        "--dir",
        default=None,
        help="Directory of PDFs — converts every .pdf file found inside it",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: same folder as the PDF, or --dir folder)",
    )
    parser.add_argument(
        "--md-only", action="store_true", help="Only write the .md file"
    )
    parser.add_argument(
        "--txt-only", action="store_true", help="Only write the .txt file"
    )
    parser.add_argument(
        "--h1", type=float, default=None, help="Font size to treat as H1"
    )
    parser.add_argument(
        "--h2", type=float, default=None, help="Font size to treat as H2"
    )
    parser.add_argument(
        "--h3", type=float, default=None, help="Font size to treat as H3"
    )
    parser.add_argument(
        "--h4", type=float, default=None, help="Font size to treat as H4"
    )

    args = parser.parse_args()

    write_md = not args.txt_only
    write_txt = not args.md_only
    custom_thresholds = [
        t for t in [args.h1, args.h2, args.h3, args.h4] if t is not None
    ] or None

    # ── Batch mode: --dir ──────────────────────────────────────────────────
    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            sys.exit(f"Not a directory: {dir_path}")

        pdfs = sorted(dir_path.glob("*.pdf"))
        if not pdfs:
            sys.exit(f"No PDF files found in: {dir_path}")

        out_dir = Path(args.out_dir) if args.out_dir else dir_path
        print(f"Found {len(pdfs)} PDF(s) in {dir_path}")
        print(f"Output directory: {out_dir}\n")

        failed = []
        for i, pdf_path in enumerate(pdfs, 1):
            print(f"[{i}/{len(pdfs)}] {pdf_path.name}")
            try:
                convert(
                    pdf_path=pdf_path,
                    out_dir=out_dir,
                    write_md=write_md,
                    write_txt=write_txt,
                    custom_thresholds=custom_thresholds,
                )
            except Exception as e:
                print(f"  ERROR: {e}")
                failed.append(pdf_path.name)
            print()

        print(f"Finished. {len(pdfs) - len(failed)}/{len(pdfs)} converted successfully.")
        if failed:
            print("Failed files:")
            for name in failed:
                print(f"  - {name}")

    # ── Single file mode ───────────────────────────────────────────────────
    else:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            sys.exit(f"File not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            sys.exit(f"Expected a .pdf file, got: {pdf_path}")

        out_dir = Path(args.out_dir) if args.out_dir else pdf_path.parent

        convert(
            pdf_path=pdf_path,
            out_dir=out_dir,
            write_md=write_md,
            write_txt=write_txt,
            custom_thresholds=custom_thresholds,
        )


if __name__ == "__main__":
    main()