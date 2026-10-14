#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import fitz


# ============================================================
# NORMALIZATION
# ============================================================

def clean(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")
    text = text.replace("\u2212", "-")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_number(value: str) -> str:
    value = clean(str(value)).lower()

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    return value


def normalize_heading_text(value: str) -> str:
    value = clean(str(value)).lower()

    # PDF frequently inserts spaces around punctuation.
    value = re.sub(
        r"\s*/\s*",
        " / ",
        value,
    )

    value = re.sub(
        r"\s*-\s*",
        " - ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def heading_tokens(value: str) -> list[str]:
    value = normalize_heading_text(value)

    return [
        x.lower()
        for x in re.findall(
            r"[a-z0-9]+",
            value,
        )
        if len(x) >= 3
    ]


def normalize_for_match(value: str) -> str:
    """
    More tolerant normalization for PDF heading matching.

    Examples:

        Sub-division Layout Plan
        Sub-division / Layout plan

    become effectively comparable.
    """

    value = str(value or "").lower()

    value = value.replace("\u00a0", " ")

    # Normalize common punctuation.
    value = value.replace("–", "-")
    value = value.replace("—", "-")
    value = value.replace("−", "-")

    # Slash is often used differently in PDF/index.
    value = re.sub(
        r"\s*/\s*",
        " ",
        value,
    )

    # Remove punctuation.
    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    # Normalize common wording variation.
    value = value.replace(
        "sub division",
        "subdivision",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# NUMBER MATCHING
# ============================================================

def number_regex(number: str) -> re.Pattern:
    """
    Accept:

        2.2.5(a)
        2.2.5 (a)
        2.2.5(a)
        2.2.5
        (a)

    where appropriate.
    """

    number = normalize_number(number)

    escaped = re.escape(number)

    escaped = escaped.replace(
        r"\.",
        r"\s*\.\s*",
    )

    escaped = escaped.replace(
        r"\(",
        r"\s*\(\s*",
    )

    escaped = escaped.replace(
        r"\)",
        r"\s*\)\s*",
    )

    return re.compile(
        rf"(?<![A-Za-z0-9])"
        rf"{escaped}"
        rf"(?![A-Za-z0-9])",
        re.IGNORECASE,
    )


# ============================================================
# PDF TEXT
# ============================================================

def get_page_text(
    doc: fitz.Document,
    page_number: int,
) -> str:

    if page_number < 1:
        return ""

    if page_number > len(doc):
        return ""

    page = doc[
        page_number - 1
    ]

    return page.get_text(
        "text",
        sort=True,
    )


def get_page_blocks(
    doc: fitz.Document,
    page_number: int,
) -> list[str]:

    if page_number < 1:
        return []

    if page_number > len(doc):
        return []

    page = doc[
        page_number - 1
    ]

    blocks = page.get_text(
        "blocks",
        sort=True,
    )

    result = []

    for block in blocks:
        if len(block) < 5:
            continue

        text = clean(
            block[4]
        )

        if text:
            result.append(text)

    return result


# ============================================================
# HEADING DETECTION
# ============================================================

def find_heading_candidates(
    doc: fitz.Document,
    number: str,
    title: str,
    page_start: int,
    page_end: int,
) -> list[dict[str, Any]]:

    number_re = number_regex(
        number
    )

    canonical_title = normalize_for_match(
        title
    )

    canonical_tokens = heading_tokens(
        title
    )

    candidates = []

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Search ALL pages in the canonical range.
    #
    # Previously this was effectively restricted to
    # pdf_page_start, which incorrectly failed 2.2.5(b).
    # --------------------------------------------------------

    for page_number in range(
        page_start,
        page_end + 1,
    ):

        blocks = get_page_blocks(
            doc,
            page_number,
        )

        if not blocks:
            continue

        # ----------------------------------------------------
        # Individual blocks
        # ----------------------------------------------------

        for block_index, block in enumerate(
            blocks
        ):

            block_normalized = normalize_for_match(
                block
            )

            number_match = number_re.search(
                block
            )

            if not number_match:
                continue

            title_score = 0

            if canonical_title:
                if canonical_title in block_normalized:
                    title_score = 1.0
                else:
                    tokens_present = sum(
                        1
                        for token in canonical_tokens
                        if token in block_normalized
                    )

                    if canonical_tokens:
                        title_score = (
                            tokens_present
                            / len(canonical_tokens)
                        )

            candidates.append(
                {
                    "pdf_page": page_number,
                    "block_index": block_index,
                    "text": block,
                    "number_found": True,
                    "title_score": title_score,
                    "match_type": "single_block",
                }
            )

        # ----------------------------------------------------
        # Adjacent blocks
        #
        # Handles PDF structures such as:
        #
        # 2.2.5
        # (a) Sub-division / Layout plan
        #
        # and:
        #
        # 2.2.5
        # (b) Amalgamation Plan
        # ----------------------------------------------------

        for i in range(
            len(blocks)
        ):

            combined = " ".join(
                blocks[
                    max(0, i - 2):
                    min(len(blocks), i + 3)
                ]
            )

            if not number_re.search(
                combined
            ):
                continue

            combined_normalized = normalize_for_match(
                combined
            )

            title_score = 0

            if canonical_title:
                if canonical_title in combined_normalized:
                    title_score = 1.0
                else:
                    tokens_present = sum(
                        1
                        for token in canonical_tokens
                        if token in combined_normalized
                    )

                    if canonical_tokens:
                        title_score = (
                            tokens_present
                            / len(canonical_tokens)
                        )

            if title_score >= 0.60:

                candidates.append(
                    {
                        "pdf_page": page_number,
                        "block_index": i,
                        "text": combined,
                        "number_found": True,
                        "title_score": title_score,
                        "match_type": "adjacent_blocks",
                    }
                )

        # ----------------------------------------------------
        # Whole-page fallback
        #
        # Important for OCR/PDF extraction where heading and
        # number are separated by layout structures.
        # ----------------------------------------------------

        page_text = get_page_text(
            doc,
            page_number,
        )

        if number_re.search(
            page_text
        ):

            page_normalized = normalize_for_match(
                page_text
            )

            title_score = 0

            if canonical_title:
                if canonical_title in page_normalized:
                    title_score = 1.0
                else:
                    tokens_present = sum(
                        1
                        for token in canonical_tokens
                        if token in page_normalized
                    )

                    if canonical_tokens:
                        title_score = (
                            tokens_present
                            / len(canonical_tokens)
                        )

            if title_score >= 0.60:

                candidates.append(
                    {
                        "pdf_page": page_number,
                        "block_index": None,
                        "text": page_text[:2000],
                        "number_found": True,
                        "title_score": title_score,
                        "match_type": "whole_page",
                    }
                )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    unique = {}

    for candidate in candidates:

        key = (
            candidate["pdf_page"],
            candidate["match_type"],
            candidate["block_index"],
        )

        existing = unique.get(
            key
        )

        if (
            existing is None
            or candidate["title_score"]
            > existing["title_score"]
        ):
            unique[key] = candidate

    candidates = list(
        unique.values()
    )

    candidates.sort(
        key=lambda x: (
            -x["title_score"],
            x["pdf_page"],
        )
    )

    return candidates


# ============================================================
# TEXT COVERAGE
# ============================================================

def normalize_text_for_coverage(
    text: str,
) -> str:

    text = str(text or "").lower()

    text = text.replace(
        "\u00a0",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def calculate_text_coverage(
    canonical_text: str,
    pdf_text: str,
) -> float:

    canonical = normalize_text_for_coverage(
        canonical_text
    )

    actual = normalize_text_for_coverage(
        pdf_text
    )

    if not canonical:
        return 1.0

    if not actual:
        return 0.0

    # Remove generated table placeholders.
    canonical = canonical.replace(
        "[TABLE]",
        " ",
    )

    words = re.findall(
        r"[a-z0-9]+",
        canonical,
    )

    if not words:
        return 1.0

    actual_words = set(
        re.findall(
            r"[a-z0-9]+",
            actual,
        )
    )

    matched = sum(
        1
        for word in words
        if word in actual_words
    )

    return matched / len(words)


# ============================================================
# PAGE RANGE VALIDATION
# ============================================================

def validate_page_range(
    chunk: dict[str, Any],
    pdf_page_count: int,
) -> tuple[bool, str | None]:

    start = chunk.get(
        "pdf_page_start"
    )

    end = chunk.get(
        "pdf_page_end"
    )

    if not isinstance(
        start,
        int,
    ):
        return (
            False,
            "pdf_page_start is not an integer",
        )

    if not isinstance(
        end,
        int,
    ):
        return (
            False,
            "pdf_page_end is not an integer",
        )

    if start < 1:
        return (
            False,
            "pdf_page_start < 1",
        )

    if end < start:
        return (
            False,
            "pdf_page_end < pdf_page_start",
        )

    if end > pdf_page_count:
        return (
            False,
            "pdf_page_end exceeds PDF page count",
        )

    return (
        True,
        None,
    )


# ============================================================
# TABLE METADATA
# ============================================================

def validate_tables(
    chunk: dict[str, Any],
) -> tuple[bool, list[str]]:

    warnings = []

    tables = chunk.get(
        "tables",
        [],
    )

    table_count = chunk.get(
        "table_count",
        0,
    )

    if tables is None:
        tables = []

    if not isinstance(
        tables,
        list,
    ):
        return (
            False,
            ["tables is not a list"],
        )

    if not isinstance(
        table_count,
        int,
    ):
        return (
            False,
            ["table_count is not an integer"],
        )

    if table_count != len(
        tables
    ):
        warnings.append(
            "table_count does not equal len(tables)"
        )

    return (
        True,
        warnings,
    )


# ============================================================
# MAIN VERIFICATION
# ============================================================

def verify(
    pdf_path: str,
    chunks_path: str,
    report_path: str,
) -> int:

    print(
        "=" * 120
    )
    print(
        "UDCPR CANONICAL CHUNKS vs ACTUAL PDF VERIFICATION"
    )
    print(
        "=" * 120
    )
    print()

    print(
        f"PDF    : {pdf_path}"
    )

    print(
        f"CHUNKS : {chunks_path}"
    )

    print(
        f"REPORT : {report_path}"
    )

    print()

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    with open(
        chunks_path,
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    if isinstance(
        data,
        dict,
    ):
        chunks = data.get(
            "chunks",
            [],
        )
    elif isinstance(
        data,
        list,
    ):
        chunks = data
    else:
        raise ValueError(
            "Unsupported chunks JSON structure"
        )

    doc = fitz.open(
        pdf_path
    )

    pdf_page_count = len(
        doc
    )

    print(
        "=" * 120
    )
    print(
        "SOURCE"
    )
    print(
        "=" * 120
    )

    print(
        f"Canonical chunks: {len(chunks)}"
    )

    print(
        f"PDF pages: {pdf_page_count}"
    )

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    valid_ranges = 0
    headings_found = 0
    good_text = 0
    table_valid = 0

    warnings = []
    failures = []

    results = []

    # --------------------------------------------------------
    # Verify chunks
    # --------------------------------------------------------

    for index, chunk in enumerate(
        chunks
    ):

        number = str(
            chunk.get(
                "number",
                "",
            )
        )

        title = str(
            chunk.get(
                "title",
                "",
            )
        )

        key = chunk.get(
            "key",
            f"{number}@{index}",
        )

        page_start = chunk.get(
            "pdf_page_start"
        )

        page_end = chunk.get(
            "pdf_page_end"
        )

        # ----------------------------------------------------
        # Range
        # ----------------------------------------------------

        range_ok, range_error = validate_page_range(
            chunk,
            pdf_page_count,
        )

        if range_ok:
            valid_ranges += 1
        else:
            failures.append(
                {
                    "key": key,
                    "number": number,
                    "type": "invalid_pdf_range",
                    "message": range_error,
                }
            )

        # ----------------------------------------------------
        # Heading
        # ----------------------------------------------------

        heading_candidates = []

        if range_ok:

            heading_candidates = find_heading_candidates(
                doc=doc,
                number=number,
                title=title,
                page_start=page_start,
                page_end=page_end,
            )

        best_heading = (
            heading_candidates[0]
            if heading_candidates
            else None
        )

        heading_found = (
            best_heading is not None
        )

        if heading_found:
            headings_found += 1

        # ----------------------------------------------------
        # Text coverage
        #
        # Search the ENTIRE canonical PDF range.
        # ----------------------------------------------------

        canonical_text = chunk.get(
            "regulation_text",
            "",
        )

        actual_parts = []

        if range_ok:

            for page_number in range(
                page_start,
                page_end + 1,
            ):

                actual_parts.append(
                    get_page_text(
                        doc,
                        page_number,
                    )
                )

        actual_text = "\n".join(
            actual_parts
        )

        coverage = calculate_text_coverage(
            canonical_text,
            actual_text,
        )

        coverage_ok = (
            coverage >= 0.75
        )

        if coverage_ok:
            good_text += 1

        # ----------------------------------------------------
        # Tables
        # ----------------------------------------------------

        tables_ok, table_warnings = validate_tables(
            chunk
        )

        if tables_ok:
            table_valid += 1

        for warning in table_warnings:
            warnings.append(
                {
                    "key": key,
                    "number": number,
                    "type": "table_metadata",
                    "message": warning,
                }
            )

        # ----------------------------------------------------
        # Heading warnings/failures
        # ----------------------------------------------------

        if not heading_found:

            failures.append(
                {
                    "key": key,
                    "number": number,
                    "title": title,
                    "type": "heading_not_found",
                    "message": (
                        "canonical heading not found "
                        "within pdf_page_start..pdf_page_end"
                    ),
                    "pdf_page_start": page_start,
                    "pdf_page_end": page_end,
                }
            )

        elif best_heading["title_score"] < 0.80:

            warnings.append(
                {
                    "key": key,
                    "number": number,
                    "title": title,
                    "type": "weak_heading_match",
                    "message": (
                        "heading number found but title "
                        "match is below 0.80"
                    ),
                    "title_score": best_heading[
                        "title_score"
                    ],
                    "pdf_page": best_heading[
                        "pdf_page"
                    ],
                    "match_type": best_heading[
                        "match_type"
                    ],
                }
            )

        # ----------------------------------------------------
        # Coverage warning
        # ----------------------------------------------------

        if not coverage_ok:

            warnings.append(
                {
                    "key": key,
                    "number": number,
                    "title": title,
                    "type": "low_text_coverage",
                    "coverage": round(
                        coverage,
                        4,
                    ),
                    "pdf_page_start": page_start,
                    "pdf_page_end": page_end,
                }
            )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        result = {
            "key": key,
            "number": number,
            "title": title,
            "pdf_page_start": page_start,
            "pdf_page_end": page_end,
            "range_valid": range_ok,
            "heading_found": heading_found,
            "heading": best_heading,
            "heading_candidates": heading_candidates[:10],
            "text_coverage": round(
                coverage,
                4,
            ),
            "text_coverage_good": coverage_ok,
            "table_metadata_valid": tables_ok,
            "table_warnings": table_warnings,
        }

        results.append(
            result
        )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if (
            index + 1
        ) % 25 == 0:

            print(
                f"Verified {index + 1} / {len(chunks)}"
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = {
        "canonical_chunks": len(chunks),
        "pdf_pages": pdf_page_count,
        "valid_pdf_ranges": valid_ranges,
        "headings_found": headings_found,
        "good_text_coverage": good_text,
        "table_metadata_valid": table_valid,
        "warnings": len(warnings),
        "failures": len(failures),
    }

    report = {
        "source": {
            "pdf": str(
                Path(pdf_path)
            ),
            "chunks": str(
                Path(chunks_path)
            ),
            "pdf_pages": pdf_page_count,
            "canonical_chunks": len(chunks),
        },
        "summary": summary,
        "results": results,
        "warnings": warnings,
        "failures": failures,
    }

    # --------------------------------------------------------
    # Write report
    # --------------------------------------------------------

    report_parent = Path(
        report_path
    ).parent

    report_parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        report_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()

    print(
        "=" * 120
    )

    print(
        "VERIFICATION SUMMARY"
    )

    print(
        "=" * 120
    )

    print(
        f"Canonical chunks       : {len(chunks)}"
    )

    print(
        f"Valid PDF ranges       : {valid_ranges}"
    )

    print(
        f"Headings found         : {headings_found}"
    )

    print(
        f"Good text coverage     : {good_text}"
    )

    print(
        f"Table metadata valid   : {table_valid}"
    )

    print(
        f"Warnings               : {len(warnings)}"
    )

    print(
        f"Failures               : {len(failures)}"
    )

    print()

    # --------------------------------------------------------
    # Failures
    # --------------------------------------------------------

    if failures:

        print(
            "FAIL: canonical chunks do not completely match "
            "the actual PDF."
        )

        print()

        print(
            "First failures:"
        )

        for failure in failures[:20]:

            print(
                f"  {failure.get('key')}|"
                f"{failure.get('title', '')}"
            )

            print(
                f"       - {failure.get('message')}"
            )

        print()

        print(
            f"Detailed report: {report_path}"
        )

        return 1

    # --------------------------------------------------------
    # Success
    # --------------------------------------------------------

    print(
        "PASS: all canonical chunks match the actual PDF."
    )

    print()

    print(
        f"Detailed report: {report_path}"
    )

    return 0


# ============================================================
# CLI
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Verify canonical UDCPR source chunks "
            "against the actual UDCPR PDF."
        )
    )

    parser.add_argument(
        "--pdf",
        required=True,
    )

    parser.add_argument(
        "--chunks",
        required=True,
    )

    parser.add_argument(
        "--report",
        required=True,
    )

    args = parser.parse_args()

    return verify(
        pdf_path=args.pdf,
        chunks_path=args.chunks,
        report_path=args.report,
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
