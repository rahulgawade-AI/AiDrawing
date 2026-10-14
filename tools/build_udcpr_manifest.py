#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import fitz


# ============================================================
# VERIFIED UDCPR DOCUMENT STRUCTURE
# ============================================================

INDEX_PDF_START = 5
INDEX_PDF_END = 14

MAIN_PRINTED_START = 1
MAIN_PRINTED_END = 423

PDF_FRONT_MATTER = 16

MAIN_PDF_START = 17
MAIN_PDF_END = 439


# ============================================================
# HELPERS
# ============================================================

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(text: str) -> str:
    text = clean(text)

    # Remove index annotation markers.
    text = re.sub(
        r"^(?:\*+\s*)+",
        "",
        text,
    )

    text = re.sub(
        r"^(?:#+\s*)+",
        "",
        text,
    )

    return clean(text)


def detect_chapter(text: str) -> str | None:
    m = re.search(
        r"CHAPTER\s*[-–—]\s*(\d+)",
        text,
        re.IGNORECASE,
    )

    if m:
        return m.group(1)

    return None


# ============================================================
# INDEX PARSER
# ============================================================

def parse_index_block(
    text: str,
    chapter: str,
    pdf_page: int,
):
    """
    Parse a single actual UDCPR index block.

    Examples:

        1.0 Short Title, Extent and Commencement 1

        2.2.5 (a) Sub-division Layout Plan 25

        2.2.5 (b) Amalgamation Plan 25
    """

    text = clean(text)

    # Regulation number.
    #
    # Supports:
    #
    # 1.0
    # 2.2.5
    # 2.2.5 (a)
    # 10.14
    #
    m = re.match(
        r"^"
        r"(?P<number>\d+(?:\.\d+)*)"
        r"\s*"
        r"(?P<variant>\([a-z]\))?"
        r"\s+"
        r"(?P<title>.+?)"
        r"\s+"
        r"(?P<page>\d+)"
        r"$",
        text,
        re.IGNORECASE,
    )

    if not m:
        return None

    number = m.group("number")

    variant = m.group("variant")

    if variant:
        number += variant.lower()

    title = normalize_title(
        m.group("title")
    )

    if not title:
        return None

    return {
        "number": number,
        "chapter": chapter,
        "title": title,
        "printed_page_start": int(
            m.group("page")
        ),
        "index_pdf_page": pdf_page,
    }


def read_index(
    doc: fitz.Document,
):
    """
    Read the canonical UDCPR index.

    Index pages are PDF pages 5-14.
    """

    entries = []

    chapter = ""

    for pdf_page_no in range(
        INDEX_PDF_START,
        INDEX_PDF_END + 1,
    ):

        page = doc[
            pdf_page_no - 1
        ]

        blocks = page.get_text(
            "blocks",
            sort=True,
        )

        for block in blocks:

            text = clean(
                block[4]
            )

            if not text:
                continue

            detected = detect_chapter(
                text
            )

            if detected:
                chapter = detected
                continue

            upper = text.upper()

            if upper in {
                "INDEX",
                "REGULATION",
                "NO.",
                "PARTICULARS",
                "PAGE NO.",
                "PARTICULARS PAGE NO.",
            }:
                continue

            entry = parse_index_block(
                text,
                chapter,
                pdf_page_no,
            )

            if entry is not None:

                entries.append(
                    entry
                )

    # Sequence and occurrence.
    occurrences = Counter()

    for sequence, entry in enumerate(
        entries,
        start=1,
    ):

        number = entry["number"]

        occurrences[number] += 1

        entry["sequence"] = sequence

        entry["occurrence"] = occurrences[
            number
        ]

        entry["key"] = (
            f'{number}@'
            f'{entry["printed_page_start"]}'
            f'#{entry["occurrence"]}'
        )

    return entries


# ============================================================
# VERIFIED PRINTED PAGE → PDF PAGE MAP
# ============================================================

def build_page_map(
    doc: fitz.Document,
):
    """
    Verified from the supplied UDCPR PDF.

    PDF page 17 = printed page 1.

    Therefore:

        PDF page = printed page + 16

    Main document:

        printed 1-423
        PDF     17-439
    """

    page_map = {}

    for printed_page in range(
        MAIN_PRINTED_START,
        MAIN_PRINTED_END + 1,
    ):

        pdf_page = (
            printed_page
            + PDF_FRONT_MATTER
        )

        if pdf_page > len(doc):
            raise RuntimeError(
                "Calculated PDF page "
                f"{pdf_page} exceeds PDF "
                f"length {len(doc)}"
            )

        page_map[
            printed_page
        ] = [
            pdf_page
        ]

    return page_map


# ============================================================
# BASIC INDEX VALIDATION
# ============================================================

def validate_index(
    entries,
    page_map,
):
    errors = []

    if not entries:
        errors.append(
            "No regulation entries found."
        )

    for entry in entries:

        number = entry[
            "number"
        ]

        printed = entry[
            "printed_page_start"
        ]

        if printed not in page_map:

            errors.append(
                f"{number}: printed page "
                f"{printed} is outside "
                "main UDCPR range 1-423"
            )

    return errors


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Build canonical UDCPR "
            "index manifest."
        )
    )

    parser.add_argument(
        "--pdf",
        required=True,
    )

    parser.add_argument(
        "--output",
        default=(
            "data/regulations/"
            "udcpr_canonical_manifest.json"
        ),
    )

    args = parser.parse_args()

    pdf = Path(
        args.pdf
    )

    if not pdf.exists():

        raise FileNotFoundError(
            pdf
        )

    print("=" * 100)
    print("UDCPR CANONICAL MANIFEST")
    print("=" * 100)

    print(
        "PDF:",
        pdf,
    )

    doc = fitz.open(
        str(pdf)
    )

    try:

        print(
            "PDF pages:",
            len(doc),
        )

        # ----------------------------------------------------
        # Read canonical index.
        # ----------------------------------------------------

        print(
            f"Reading index PDF pages "
            f"{INDEX_PDF_START}-{INDEX_PDF_END}"
        )

        entries = read_index(
            doc
        )

        print(
            "Index entries:",
            len(entries),
        )

        # ----------------------------------------------------
        # Verified pagination.
        # ----------------------------------------------------

        page_map = build_page_map(
            doc
        )

        print(
            "Main printed pages:",
            len(page_map),
        )

        # ----------------------------------------------------
        # Validate.
        # ----------------------------------------------------

        errors = validate_index(
            entries,
            page_map,
        )

        # ----------------------------------------------------
        # Add deterministic PDF page.
        #
        # IMPORTANT:
        #
        # This is only the START page.
        #
        # We intentionally DO NOT calculate a regulation
        # end page here because multiple regulations can share
        # the same printed page.
        #
        # The full extractor will determine the exact end
        # from the next regulation heading.
        # ----------------------------------------------------

        for entry in entries:

            printed = entry[
                "printed_page_start"
            ]

            pdf_pages = page_map[
                printed
            ]

            entry[
                "pdf_page_start"
            ] = pdf_pages[0]

            entry[
                "pdf_page_end"
            ] = None

            entry[
                "printed_page_end"
            ] = None

        # ----------------------------------------------------
        # Duplicate numbers.
        # ----------------------------------------------------

        counts = Counter(
            entry["number"]
            for entry in entries
        )

        duplicates = []

        for number, count in counts.items():

            if count > 1:

                duplicates.append(
                    {
                        "number": number,
                        "count": count,
                        "entries": [
                            {
                                "key": x["key"],
                                "title": x["title"],
                                "printed_page_start":
                                    x[
                                        "printed_page_start"
                                    ],
                                "chapter":
                                    x["chapter"],
                            }
                            for x in entries
                            if x["number"] == number
                        ],
                    }
                )

        # ----------------------------------------------------
        # Statistics.
        # ----------------------------------------------------

        statistics = {
            "regulation_count":
                len(entries),

            "appendix_count":
                0,

            "duplicate_number_count":
                len(duplicates),

            "validation_error_count":
                len(errors),

            "main_printed_page_start":
                MAIN_PRINTED_START,

            "main_printed_page_end":
                MAIN_PRINTED_END,

            "main_pdf_page_start":
                MAIN_PDF_START,

            "main_pdf_page_end":
                MAIN_PDF_END,
        }

        manifest = {
            "source_document": {
                "filename":
                    pdf.name,

                "path":
                    str(pdf),

                "version":
                    "UDCPR-2020",
            },

            "document_structure": {
                "pdf_pages":
                    len(doc),

                "front_matter_pdf_pages":
                    list(
                        range(
                            1,
                            PDF_FRONT_MATTER + 1,
                        )
                    ),

                "index_pdf_pages":
                    list(
                        range(
                            INDEX_PDF_START,
                            INDEX_PDF_END + 1,
                        )
                    ),

                "main_printed_pages": [
                    MAIN_PRINTED_START,
                    MAIN_PRINTED_END,
                ],

                "main_pdf_pages": [
                    MAIN_PDF_START,
                    MAIN_PDF_END,
                ],

                "regional_material_pdf_start":
                    MAIN_PDF_END + 1,
            },

            "pagination": {
                "verified":
                    True,

                "offset":
                    PDF_FRONT_MATTER,

                "formula":
                    "pdf_page = printed_page + 16",
            },

            "statistics":
                statistics,

            "validation_errors":
                errors,

            "duplicates":
                duplicates,

            "regulations":
                entries,

            "printed_page_map": {
                str(k): v
                for k, v in page_map.items()
            },
        }

        output = Path(
            args.output
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # ----------------------------------------------------
        # Output summary.
        # ----------------------------------------------------

        print()
        print("=" * 100)
        print("RESULT")
        print("=" * 100)

        print(
            "Regulations:",
            len(entries),
        )

        print(
            "Validation errors:",
            len(errors),
        )

        print(
            "Duplicate numbers:",
            len(duplicates),
        )

        print(
            "Manifest:",
            output,
        )

        if errors:

            print()
            print(
                "VALIDATION ERRORS"
            )
            print("-" * 100)

            for error in errors:

                print(
                    error
                )

            raise RuntimeError(
                "UDCPR index validation failed."
            )

        print()
        print(
            "PAGINATION:"
        )
        print(
            "  printed 1  -> PDF 17"
        )
        print(
            "  printed 23 -> PDF 39"
        )
        print(
            "  printed 24 -> PDF 40"
        )
        print(
            "  printed 423 -> PDF 439"
        )

        print()
        print(
            "DUPLICATES:"
        )

        for duplicate in duplicates:

            print(
                f'  {duplicate["number"]}: '
                f'{duplicate["count"]}'
            )

            for item in duplicate[
                "entries"
            ]:

                print(
                    "     ",
                    item["key"],
                    item["title"],
                )

        print()
        print("=" * 100)
        print(
            "MANIFEST BUILD SUCCESSFUL"
        )
        print("=" * 100)

    finally:

        doc.close()


if __name__ == "__main__":
    main()
