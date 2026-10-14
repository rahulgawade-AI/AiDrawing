#!/usr/bin/env python3
"""
Build canonical, page-aware UDCPR regulation chunks.

Design:
- Uses udcpr_canonical_manifest.json as the ONLY source of canonical
  regulation numbers/titles/page starts.
- Uses the verified pagination mapping in the manifest.
- Extracts PDF text page-by-page with PyMuPDF.
- Preserves every source page verbatim-ish as normalized page text.
- Creates two representations:
    1. source_pages_text: complete text of every page in the regulation's
       index-defined page range, including neighboring regulations/tables.
    2. regulation_text: boundary-extracted text beginning at the canonical
       regulation heading and ending immediately before the next canonical
       regulation heading.
- Does NOT treat arbitrary numbers in tables/body text as regulations.
- Handles duplicate regulation numbers such as 10.14 by using a stable key
  (number + printed page + occurrence).
- Does not modify the database. It writes a JSONL/JSON artifact for review.

Usage:
    python tools/build_udcpr_canonical_chunks.py \
      --pdf /home/ubuntu/llmproject/ai-town-planning/data/regulations/UDCPR.pdf

Optional:
    --manifest data/regulations/udcpr_canonical_manifest.json
    --out data/regulations/udcpr_canonical_chunks.json
    --jsonl data/regulations/udcpr_canonical_chunks.jsonl
    --report data/regulations/udcpr_chunk_validation.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import fitz


LOG = logging.getLogger("udcpr_chunks")

DEFAULT_PDF = Path(
    "/home/ubuntu/llmproject/ai-town-planning/"
    "data/regulations/UDCPR.pdf"
)
DEFAULT_MANIFEST = Path(
    "data/regulations/udcpr_canonical_manifest.json"
)
DEFAULT_OUT = Path(
    "data/regulations/udcpr_canonical_chunks.json"
)
DEFAULT_JSONL = Path(
    "data/regulations/udcpr_canonical_chunks.jsonl"
)
DEFAULT_REPORT = Path(
    "data/regulations/udcpr_chunk_validation.json"
)

# Canonical heading number:
#   1.0
#   2.1.1
#   2.2.5(a)
#   10.14
# Avoid matching decimal measurements such as 0.305 or arbitrary table values.
REG_NO_RE = re.compile(
    r"(?<![\w.])"
    r"(?P<number>\d+(?:\.\d+)+(?:\([a-z]\))?)"
    r"(?![\w.])",
    re.IGNORECASE,
)

# A heading is much more likely when the regulation number is near the
# beginning of a line/block. This is deliberately stricter than REG_NO_RE.
LINE_HEADING_RE = re.compile(
    r"^\s*"
    r"(?P<number>\d+(?:\.\d+)+(?:\([a-z]\))?)"
    r"(?:\s+|\s*[-–—:]\s*)"
    r"(?P<title>.+?)"
    r"\s*$",
    re.IGNORECASE,
)

FOOTER_RE = re.compile(r"^\s*\d{1,3}\s*$")


def normalize_space(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    return text.strip()


def normalize_for_compare(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\u00ad", "")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    p.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return p.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Accept the current manifest format.

    Expected:
      manifest["canonical"]["detected"] = [
          {
             "number": "2.1.1",
             "title": "...",
             "index_printed_page": 21,
             "index_pdf_page": 37,
             ...
          }
      ]

    Also tolerates a top-level "regulations" list.
    """
    if isinstance(manifest.get("canonical"), dict):
        entries = manifest["canonical"].get("detected")
        if isinstance(entries, list):
            return entries

    for key in ("regulations", "entries", "detected"):
        if isinstance(manifest.get(key), list):
            return manifest[key]

    raise RuntimeError(
        "Cannot find canonical regulation list in manifest. "
        "Expected canonical.detected."
    )


def stable_key(entry: dict[str, Any], occurrence: int) -> str:
    number = str(entry["number"])
    printed = entry.get("index_printed_page")
    if printed is None:
        printed = entry.get("printed_page_start")
    if printed is None:
        printed = 0
    return f"{number}@{printed}#{occurrence}"


def entry_start_pdf_page(entry: dict[str, Any]) -> int:
    """
    Prefer manifest's verified index_pdf_page.

    The manifest already established:
        pdf_page = printed_page + 16

    We do NOT rediscover pagination by scanning arbitrary footer numbers.
    """
    for key in ("index_pdf_page", "pdf_page_start"):
        value = entry.get(key)
        if isinstance(value, int) and value > 0:
            return value

    printed = entry.get("index_printed_page")
    if printed is None:
        printed = entry.get("printed_page_start")

    if isinstance(printed, int):
        return printed + 16

    raise RuntimeError(f"No page start for manifest entry: {entry}")


def entry_start_printed_page(entry: dict[str, Any]) -> int | None:
    for key in ("index_printed_page", "printed_page_start"):
        value = entry.get(key)
        if isinstance(value, int):
            return value
    return None


def page_text(page: fitz.Page) -> str:
    """
    Return page text while removing only the isolated page footer.

    We intentionally do NOT remove:
    - tables
    - headings
    - body numbers
    - footnotes
    - amendments
    - appendix references
    """
    blocks = page.get_text("blocks", sort=True)
    lines: list[str] = []

    for block in blocks:
        raw = block[4]
        if not raw:
            continue

        # Keep block line structure because tables and numbered clauses
        # depend on line boundaries.
        for line in raw.splitlines():
            line = line.rstrip()
            if not line.strip():
                continue
            lines.append(line)

    # Remove isolated numeric footer when it is the final line.
    if lines and FOOTER_RE.fullmatch(lines[-1].strip()):
        lines.pop()

    return "\n".join(lines).strip()


def extract_pages(doc: fitz.Document) -> dict[int, str]:
    result: dict[int, str] = {}
    total = len(doc)

    for pdf_page in range(1, total + 1):
        result[pdf_page] = page_text(doc[pdf_page - 1])

        if pdf_page % 25 == 0 or pdf_page == total:
            LOG.info("Extracted PDF page %d/%d", pdf_page, total)

    return result


def title_tokens(title: str) -> list[str]:
    title = normalize_for_compare(title)
    title = re.sub(r"^[*#()a-z0-9\s.-]+(?=\b)", "", title)
    tokens = re.findall(r"[a-z0-9]+", title)
    # Very short/common tokens are not useful for heading validation.
    return [x for x in tokens if len(x) >= 3]


def title_score(candidate_title: str, canonical_title: str) -> float:
    a = set(title_tokens(candidate_title))
    b = set(title_tokens(canonical_title))
    if not a or not b:
        return 0.0
    return len(a & b) / len(b)


def find_heading_occurrences(
    text: str,
    canonical_by_number: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    Find only line-start candidates for canonical regulation numbers.

    This prevents values such as:
        0.305
        2.6
        1.6
        15.0
    inside tables/body text from becoming regulation headings.

    Multi-line headings are supported when the first line contains the
    canonical number and subsequent lines contain title text.
    """
    lines = text.splitlines()
    occurrences: list[dict[str, Any]] = []

    for i, line in enumerate(lines):
        m = LINE_HEADING_RE.match(line)
        if not m:
            continue

        number = m.group("number")
        if number not in canonical_by_number:
            continue

        title = m.group("title").strip()

        # Look ahead for continuation of a wrapped heading.
        combined_title = title
        j = i + 1
        while j < len(lines):
            nxt = lines[j].strip()

            if not nxt:
                j += 1
                continue

            if LINE_HEADING_RE.match(nxt):
                break

            # Stop at obvious paragraph/body content after a reasonably
            # long heading. For short headings, allow a few continuation
            # lines because PDF extraction can wrap them.
            if len(combined_title) < 180 and j <= i + 3:
                combined_title += " " + nxt
                j += 1
                continue

            break

        occurrences.append(
            {
                "number": number,
                "line_index": i,
                "end_line_index": j - 1,
                "title": combined_title,
            }
        )

    return occurrences


def build_canonical_occurrence_map(
    entries: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}

    for entry in entries:
        result.setdefault(str(entry["number"]), []).append(entry)

    for number in result:
        result[number].sort(
            key=lambda e: (
                entry_start_pdf_page(e),
                entry_start_printed_page(e) or 0,
            )
        )

    return result


def choose_entry_for_occurrence(
    occurrence: dict[str, Any],
    candidates: list[dict[str, Any]],
    pdf_page: int,
) -> dict[str, Any]:
    """
    Usually there is exactly one canonical entry for a number.

    For duplicate numbers such as 10.14, choose the occurrence whose
    manifest page is closest to the actual PDF page.
    """
    if len(candidates) == 1:
        return candidates[0]

    return min(
        candidates,
        key=lambda e: abs(entry_start_pdf_page(e) - pdf_page),
    )


def locate_canonical_headings(
    page_texts: dict[int, str],
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_number = build_canonical_occurrence_map(entries)
    located: list[dict[str, Any]] = []

    # Search only the page indicated by the canonical manifest, plus one
    # neighboring page on each side. This is both faster and safer than
    # scanning all 511 pages for every regulation.
    for entry in entries:
        start_page = entry_start_pdf_page(entry)

        found: list[dict[str, Any]] = []

        for pdf_page in range(
            max(1, start_page - 1),
            min(max(page_texts), start_page + 1) + 1,
        ):
            text = page_texts[pdf_page]
            occurrences = find_heading_occurrences(text, by_number)

            for occ in occurrences:
                if occ["number"] != str(entry["number"]):
                    continue

                score = title_score(
                    occ["title"],
                    str(entry.get("title", "")),
                )

                # The manifest page is authoritative. A heading on another
                # page is accepted only when it is a very good title match.
                if pdf_page == start_page:
                    if score >= 0.15 or not entry.get("title"):
                        found.append(
                            {
                                "pdf_page": pdf_page,
                                "score": score,
                                **occ,
                            }
                        )
                elif score >= 0.60:
                    found.append(
                        {
                            "pdf_page": pdf_page,
                            "score": score,
                            **occ,
                        }
                    )

        if not found:
            located.append(
                {
                    "entry": entry,
                    "found": False,
                    "reason": "canonical heading not located",
                }
            )
            continue

        # Prefer the manifest page, then highest title score.
        found.sort(
            key=lambda x: (
                x["pdf_page"] == start_page,
                x["score"],
            ),
            reverse=True,
        )

        best = found[0]

        located.append(
            {
                "entry": entry,
                "found": True,
                "pdf_page": best["pdf_page"],
                "line_index": best["line_index"],
                "end_line_index": best["end_line_index"],
                "detected_title": best["title"],
                "title_score": best["score"],
            }
        )

    return located


def build_page_ranges(
    entries: list[dict[str, Any]],
) -> list[tuple[int, int]]:
    """
    Index-defined page ranges.

    For a regulation:
      start = its canonical index page
      end   = page immediately before the next canonical regulation's
              index page.

    This is the page range the user asked us to preserve completely.

    The final regulation ends at the end of the main UDCPR body (printed
    page 423 / PDF page 439), not at the end of appendices.
    """
    ordered = sorted(
        entries,
        key=lambda e: (
            entry_start_pdf_page(e),
            entry_start_printed_page(e) or 0,
        ),
    )

    main_end = 439

    ranges: list[tuple[int, int]] = []

    for i, entry in enumerate(ordered):
        start = entry_start_pdf_page(entry)

        if i + 1 < len(ordered):
            next_start = entry_start_pdf_page(ordered[i + 1])
            end = next_start - 1
        else:
            end = main_end

        if end < start:
            end = start

        ranges.append((start, end))

    return ranges


def extract_boundary_text(
    page_texts: dict[int, str],
    located: list[dict[str, Any]],
    entry: dict[str, Any],
    next_located: dict[str, Any] | None,
) -> str:
    """
    Boundary text is the precise regulation text, unlike source_pages_text.

    It starts at the located canonical heading and stops immediately before
    the next located canonical heading when both occur on the same page.

    If the next regulation begins on a later page, all remaining text on
    the current regulation's page and all intermediate pages are included.
    """
    current_page = next(
        x["pdf_page"]
        for x in located
        if x.get("found") and x["entry"] is entry
    )

    start_line = next(
        x["line_index"]
        for x in located
        if x.get("found") and x["entry"] is entry
    )

    parts: list[str] = []

    if next_located and next_located.get("found"):
        next_page = next_located["pdf_page"]
        next_line = next_located["line_index"]
    else:
        next_page = None
        next_line = None

    max_page = next_page if next_page is not None else 439

    for pdf_page in range(current_page, max_page + 1):
        text = page_texts.get(pdf_page, "")
        lines = text.splitlines()

        if pdf_page == current_page:
            begin = start_line
        else:
            begin = 0

        end = len(lines)

        if (
            next_page is not None
            and pdf_page == next_page
            and next_line is not None
        ):
            end = next_line

        if begin < end:
            parts.append("\n".join(lines[begin:end]).strip())

        if next_page is not None and pdf_page == next_page:
            break

    return "\n\n".join(x for x in parts if x).strip()


def build_chunks(
    doc: fitz.Document,
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    entries = get_entries(manifest)
    page_texts = extract_pages(doc)

    located = locate_canonical_headings(page_texts, entries)

    # Preserve canonical order, not accidental PDF detection order.
    located.sort(
        key=lambda x: (
            entry_start_pdf_page(x["entry"]),
            entry_start_printed_page(x["entry"]) or 0,
        )
    )

    ranges = build_page_ranges(entries)

    # Map stable identity -> page range.
    range_by_key: dict[str, tuple[int, int]] = {}
    occurrence_counter: dict[str, int] = {}

    for entry, page_range in zip(
        sorted(
            entries,
            key=lambda e: (
                entry_start_pdf_page(e),
                entry_start_printed_page(e) or 0,
            ),
        ),
        ranges,
    ):
        number = str(entry["number"])
        occurrence_counter[number] = occurrence_counter.get(number, 0) + 1
        key = stable_key(entry, occurrence_counter[number])
        range_by_key[key] = page_range

    chunks: list[dict[str, Any]] = []

    # Use canonical order.
    canonical_order = sorted(
        entries,
        key=lambda e: (
            entry_start_pdf_page(e),
            entry_start_printed_page(e) or 0,
        ),
    )

    for idx, entry in enumerate(canonical_order):
        number = str(entry["number"])

        same_number_before = [
            e for e in canonical_order[:idx] if str(e["number"]) == number
        ]
        occurrence = len(same_number_before) + 1
        key = stable_key(entry, occurrence)

        start_page, end_page = range_by_key[key]

        source_pages: list[dict[str, Any]] = []

        for pdf_page in range(start_page, end_page + 1):
            text = page_texts.get(pdf_page, "")
            printed_page = pdf_page - 16 if 17 <= pdf_page <= 439 else None

            source_pages.append(
                {
                    "pdf_page": pdf_page,
                    "printed_page": printed_page,
                    "text": text,
                    "sha256": sha256_text(text),
                }
            )

        current_loc = next(
            (
                x
                for x in located
                if x.get("entry") is entry
            ),
            None,
        )

        next_loc = None
        if idx + 1 < len(canonical_order):
            next_entry = canonical_order[idx + 1]
            next_loc = next(
                (
                    x
                    for x in located
                    if x.get("entry") is next_entry
                ),
                None,
            )

        if current_loc and current_loc.get("found"):
            regulation_text = extract_boundary_text(
                page_texts,
                located,
                entry,
                next_loc,
            )
        else:
            regulation_text = ""

        source_pages_text = "\n\n".join(
            f"===== PDF PAGE {p['pdf_page']}"
            f" / PRINTED {p['printed_page']} =====\n"
            f"{p['text']}"
            for p in source_pages
        ).strip()

        chunk = {
            "key": key,
            "order": idx + 1,
            "number": number,
            "title": entry.get("title"),
            "chapter": entry.get("chapter"),
            "index_printed_page": entry.get("index_printed_page"),
            "index_pdf_page": entry.get("index_pdf_page"),
            "pdf_page_start": start_page,
            "pdf_page_end": end_page,
            "printed_page_start": (
                start_page - 16 if 17 <= start_page <= 439 else None
            ),
            "printed_page_end": (
                end_page - 16 if 17 <= end_page <= 439 else None
            ),
            "heading_detected": bool(
                current_loc and current_loc.get("found")
            ),
            "detected_heading_page": (
                current_loc.get("pdf_page")
                if current_loc and current_loc.get("found")
                else None
            ),
            "detected_heading_title": (
                current_loc.get("detected_title")
                if current_loc and current_loc.get("found")
                else None
            ),
            "heading_title_score": (
                current_loc.get("title_score")
                if current_loc and current_loc.get("found")
                else None
            ),
            "regulation_text": regulation_text,
            "regulation_text_sha256": sha256_text(regulation_text),
            "source_pages_text": source_pages_text,
            "source_pages_text_sha256": sha256_text(source_pages_text),
            "source_pages": source_pages,
        }

        chunks.append(chunk)

    report = validate_chunks(chunks, entries, page_texts)

    return chunks, report


def validate_chunks(
    chunks: list[dict[str, Any]],
    entries: list[dict[str, Any]],
    page_texts: dict[int, str],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if len(chunks) != len(entries):
        errors.append(
            f"chunk count {len(chunks)} != canonical count {len(entries)}"
        )

    seen_keys: set[str] = set()

    for chunk in chunks:
        key = chunk["key"]
        if key in seen_keys:
            errors.append(f"duplicate chunk key: {key}")
        seen_keys.add(key)

        if not chunk["heading_detected"]:
            errors.append(
                f"{key}: canonical heading not detected at manifest page"
            )

        if chunk["pdf_page_start"] > chunk["pdf_page_end"]:
            errors.append(f"{key}: invalid page range")

        if not chunk["source_pages_text"]:
            errors.append(f"{key}: empty source_pages_text")

        if not chunk["regulation_text"]:
            errors.append(f"{key}: empty regulation_text")

    # Verify every source page exists and has text.
    referenced_pages: set[int] = set()

    for chunk in chunks:
        for p in range(
            chunk["pdf_page_start"],
            chunk["pdf_page_end"] + 1,
        ):
            referenced_pages.add(p)

    missing_pages = sorted(
        p for p in referenced_pages
        if p not in page_texts
    )

    if missing_pages:
        errors.append(
            f"missing extracted pages: {missing_pages[:20]}"
        )

    # Check that the first page of every chunk corresponds to its
    # canonical manifest page.
    for chunk in chunks:
        if chunk["pdf_page_start"] != chunk["index_pdf_page"]:
            errors.append(
                f"{chunk['key']}: range start "
                f"{chunk['pdf_page_start']} != index PDF page "
                f"{chunk['index_pdf_page']}"
            )

    # Empty page count for the main body.
    empty_main = [
        p for p in range(17, 440)
        if not page_texts.get(p, "").strip()
    ]

    if empty_main:
        errors.append(
            f"empty main-body PDF pages: {empty_main[:20]}"
        )

    # Duplicate regulation numbers are legal in this document when the
    # manifest distinguishes them by page/occurrence.
    number_counts: dict[str, int] = {}
    for e in entries:
        n = str(e["number"])
        number_counts[n] = number_counts.get(n, 0) + 1

    duplicates = {
        n: c for n, c in number_counts.items()
        if c > 1
    }

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "statistics": {
            "canonical_count": len(entries),
            "chunk_count": len(chunks),
            "heading_detected_count": sum(
                1 for c in chunks if c["heading_detected"]
            ),
            "heading_missing_count": sum(
                1 for c in chunks if not c["heading_detected"]
            ),
            "empty_regulation_text_count": sum(
                1 for c in chunks if not c["regulation_text"]
            ),
            "duplicate_canonical_numbers": duplicates,
            "main_pdf_pages": 423,
            "main_pdf_start": 17,
            "main_pdf_end": 439,
            "pdf_pages_total": len(page_texts),
        },
    }


def write_outputs(
    chunks: list[dict[str, Any]],
    report: dict[str, Any],
    out: Path,
    jsonl: Path,
    report_path: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "format": "udcpr-canonical-regulation-chunks-v1",
        "source": str(DEFAULT_PDF),
        "pagination": {
            "verified": True,
            "formula": "pdf_page = printed_page + 16",
            "main_pdf_start": 17,
            "main_pdf_end": 439,
            "printed_start": 1,
            "printed_end": 423,
        },
        "statistics": report["statistics"],
        "validation": report,
        "chunks": chunks,
    }

    with out.open("w", encoding="utf-8") as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
        )

    with jsonl.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(
                json.dumps(
                    chunk,
                    ensure_ascii=False,
                )
                + "\n"
            )

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    LOG.info("=" * 90)
    LOG.info("BUILDING UDCPR CANONICAL REGULATION CHUNKS")
    LOG.info("=" * 90)
    LOG.info("PDF      : %s", args.pdf)
    LOG.info("MANIFEST : %s", args.manifest)

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    if not args.manifest.exists():
        raise SystemExit(f"Manifest not found: {args.manifest}")

    manifest = load_manifest(args.manifest)

    entries = get_entries(manifest)
    LOG.info("Canonical regulations: %d", len(entries))

    if len(entries) != 329:
        LOG.warning(
            "Expected 329 canonical regulations, found %d",
            len(entries),
        )

    doc = fitz.open(args.pdf)

    try:
        chunks, report = build_chunks(doc, manifest)
    finally:
        doc.close()

    write_outputs(
        chunks,
        report,
        args.out,
        args.jsonl,
        args.report,
    )

    print()
    print("=" * 90)
    print("UDCPR CANONICAL CHUNK BUILD")
    print("=" * 90)
    print("Canonical regulations :", report["statistics"]["canonical_count"])
    print("Chunks created        :", report["statistics"]["chunk_count"])
    print(
        "Headings detected     :",
        report["statistics"]["heading_detected_count"],
    )
    print(
        "Headings missing      :",
        report["statistics"]["heading_missing_count"],
    )
    print(
        "Empty regulation text :",
        report["statistics"]["empty_regulation_text_count"],
    )
    print("VALID                  :", report["valid"])
    print()
    print("JSON:")
    print(args.out)
    print("JSONL:")
    print(args.jsonl)
    print("REPORT:")
    print(args.report)
    print()

    if report["errors"]:
        print("ERRORS")
        print("-" * 90)
        for error in report["errors"][:100]:
            print(error)
        print()

        raise SystemExit(2)


if __name__ == "__main__":
    main()
